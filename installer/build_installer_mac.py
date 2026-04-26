"""
路径智慧库 - macOS 安装包构建脚本

用法: python installer/build_installer_mac.py [--version 1.0.0] [--skip-dmg]

前置条件:
  - 在 macOS 上运行
  - Python 3.10+
  - 网络连接 (首次下载 Python standalone)
  - hdiutil (macOS 内置, 用于 DMG 生成)
"""
import argparse
import os
import plistlib
import shutil
import subprocess
import sys
import tarfile
import urllib.request

# ── 配置 ──
PYTHON_VERSION = '3.13.3'
# python-build-standalone release for macOS aarch64
PYTHON_STANDALONE_URL = (
    f'https://github.com/indygreg/python-build-standalone/releases/download/'
    f'20241219/cpython-{PYTHON_VERSION}+20241219-aarch64-apple-darwin-install_only.tar.gz'
)
PYTHON_STANDALONE_FILENAME = f'cpython-{PYTHON_VERSION}-aarch64-apple-darwin.tar.gz'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BUILD_DIR = os.path.join(SCRIPT_DIR, 'build_mac')
CACHE_DIR = os.path.join(SCRIPT_DIR, 'cache')

APP_NAME = '路径智慧库'
APP_BUNDLE_NAME = 'PathMind'
BUNDLE_IDENTIFIER = 'com.pathmind.app'

# 需要复制到 build 的应用文件/目录 (与 Windows 版共享)
APP_COPY_LIST = [
    ('app', 'app'),
    ('run.py', 'run.py'),
    ('config.yaml.example', 'config.yaml.example'),
]


def log(msg):
    print(f'[BUILD-MAC] {msg}')


def download_file(url, dest):
    """下载文件，带进度显示"""
    log(f'下载: {url}')
    if os.path.exists(dest):
        log(f'  已缓存: {dest}')
        return

    os.makedirs(os.path.dirname(dest), exist_ok=True)

    def progress(block, block_size, total):
        downloaded = block * block_size
        if total > 0:
            pct = min(100, downloaded * 100 // total)
            print(f'\r  进度: {pct}% ({downloaded // 1024}KB / {total // 1024}KB)',
                  end='', flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=progress)
    print()
    log(f'  完成: {dest}')


def clean_build():
    """清理构建目录"""
    if os.path.exists(BUILD_DIR):
        log('清理旧的构建目录...')
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    os.makedirs(BUILD_DIR)


def setup_python():
    """下载解压 python-build-standalone"""
    archive = os.path.join(CACHE_DIR, PYTHON_STANDALONE_FILENAME)
    download_file(PYTHON_STANDALONE_URL, archive)

    python_dir = os.path.join(BUILD_DIR, 'python')
    log(f'解压 Python standalone 到 {python_dir}')

    # python-build-standalone extracts to python/
    with tarfile.open(archive, 'r:gz') as tf:
        tf.extractall(BUILD_DIR)

    if not os.path.exists(python_dir):
        # Some archives extract to a different name
        extracted = [d for d in os.listdir(BUILD_DIR)
                     if os.path.isdir(os.path.join(BUILD_DIR, d))]
        if extracted:
            os.rename(os.path.join(BUILD_DIR, extracted[0]), python_dir)

    python_exe = os.path.join(python_dir, 'bin', 'python3')
    if not os.path.exists(python_exe):
        log(f'错误: Python 可执行文件不存在: {python_exe}')
        sys.exit(1)

    log(f'Python 已就绪: {python_exe}')
    return python_dir


def install_dependencies(python_dir):
    """安装项目依赖"""
    python_exe = os.path.join(python_dir, 'bin', 'python3')
    requirements = os.path.join(PROJECT_ROOT, 'requirements.txt')

    log('安装项目依赖...')
    subprocess.run(
        [python_exe, '-m', 'pip', 'install',
         '-r', requirements,
         'pystray',
         '--no-warn-script-location',
         '--disable-pip-version-check'],
        check=True,
    )
    log('依赖安装完成')


def copy_app_files(resources_dir):
    """复制应用文件到 Resources 目录"""
    log('复制应用文件...')

    def ignore_patterns(directory, files):
        return [f for f in files if f == '__pycache__' or f.endswith('.pyc')]

    for src_name, dest_name in APP_COPY_LIST:
        src = os.path.join(PROJECT_ROOT, src_name)
        dest = os.path.join(resources_dir, dest_name)
        if os.path.isdir(src):
            shutil.copytree(src, dest, ignore=ignore_patterns)
            log(f'  目录: {src_name}/')
        else:
            shutil.copy2(src, dest)
            log(f'  文件: {src_name}')

    # 复制 launcher
    launcher_src = os.path.join(SCRIPT_DIR, 'launcher.pyw')
    if os.path.exists(launcher_src):
        shutil.copy2(launcher_src, os.path.join(resources_dir, 'launcher.pyw'))
        log('  文件: launcher.pyw')


def create_app_bundle(version):
    """创建 macOS .app 包"""
    app_dir = os.path.join(BUILD_DIR, f'{APP_BUNDLE_NAME}.app')
    contents_dir = os.path.join(app_dir, 'Contents')
    macos_dir = os.path.join(contents_dir, 'MacOS')
    resources_dir = os.path.join(contents_dir, 'Resources')

    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)

    # 1. Info.plist
    plist = {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': BUNDLE_IDENTIFIER,
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'CFBundleExecutable': APP_BUNDLE_NAME,
        'CFBundlePackageType': 'APPL',
        'CFBundleSignature': '????',
        'CFBundleIconFile': 'icon.icns',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'LSUIElement': True,  # Menu bar app (no dock icon)
        'NSScreenCaptureUsageDescription': '需要屏幕录制权限来截取应用窗口截图',
        'NSAppleEventsUsageDescription': '需要控制权限来显示错误对话框',
    }
    plist_path = os.path.join(contents_dir, 'Info.plist')
    with open(plist_path, 'wb') as f:
        plistlib.dump(plist, f)
    log(f'  Info.plist 已生成')

    # 2. 启动脚本
    launcher_script = f'''#!/bin/bash
# {APP_NAME} - macOS Launcher
DIR="$(cd "$(dirname "$0")/../Resources" && pwd)"
exec "$DIR/python/bin/python3" "$DIR/launcher.pyw" "$@"
'''
    launcher_path = os.path.join(macos_dir, APP_BUNDLE_NAME)
    with open(launcher_path, 'w') as f:
        f.write(launcher_script)
    os.chmod(launcher_path, 0o755)
    log(f'  启动脚本已生成')

    # 3. 移动 Python 到 Resources
    python_src = os.path.join(BUILD_DIR, 'python')
    python_dest = os.path.join(resources_dir, 'python')
    if os.path.exists(python_src):
        shutil.move(python_src, python_dest)
        log(f'  Python 已移动到 Resources/')

    # 4. 复制应用文件到 Resources
    copy_app_files(resources_dir)

    # 5. 复制图标
    icon_src = os.path.join(SCRIPT_DIR, 'icon.icns')
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, os.path.join(resources_dir, 'icon.icns'))
        log(f'  图标已复制')
    else:
        log(f'  警告: icon.icns 不存在，跳过图标')

    log(f'.app 包已生成: {app_dir}')
    return app_dir


def create_dmg(app_dir, version):
    """创建 DMG 安装镜像"""
    dmg_name = f'{APP_BUNDLE_NAME}_v{version}.dmg'
    dmg_path = os.path.join(SCRIPT_DIR, dmg_name)

    # Remove old DMG
    if os.path.exists(dmg_path):
        os.remove(dmg_path)

    log(f'创建 DMG: {dmg_name}')

    # Create a temporary directory with the .app and a symlink to /Applications
    staging_dir = os.path.join(BUILD_DIR, 'dmg_staging')
    os.makedirs(staging_dir, exist_ok=True)

    # Copy .app to staging
    staged_app = os.path.join(staging_dir, os.path.basename(app_dir))
    if os.path.exists(staged_app):
        shutil.rmtree(staged_app)
    shutil.copytree(app_dir, staged_app, symlinks=True)

    # Create Applications symlink
    apps_link = os.path.join(staging_dir, 'Applications')
    if not os.path.exists(apps_link):
        os.symlink('/Applications', apps_link)

    # Build DMG
    result = subprocess.run(
        [
            'hdiutil', 'create',
            '-volname', APP_NAME,
            '-srcfolder', staging_dir,
            '-ov',
            '-format', 'UDZO',
            dmg_path,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log(f'DMG 创建失败: {result.stderr}')
        return None

    size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
    log(f'DMG 生成成功: {dmg_path}')
    log(f'文件大小: {size_mb:.1f} MB')
    return dmg_path


def main():
    if sys.platform != 'darwin':
        log('错误: 此脚本仅在 macOS 上运行')
        log('当前平台: ' + sys.platform)
        sys.exit(1)

    parser = argparse.ArgumentParser(description='构建路径智慧库 macOS 安装包')
    parser.add_argument('--version', default='1.0.0', help='版本号 (默认: 1.0.0)')
    parser.add_argument('--skip-dmg', action='store_true', help='跳过 DMG 生成，仅构建 .app')
    args = parser.parse_args()

    log(f'开始构建 macOS v{args.version}')
    log(f'项目根目录: {PROJECT_ROOT}')
    log(f'构建目录: {BUILD_DIR}')
    log('=' * 50)

    # Step 1: 清理
    clean_build()

    # Step 2: 下载并配置 Python
    python_dir = setup_python()

    # Step 3: 安装依赖
    install_dependencies(python_dir)

    # Step 4: 创建 .app 包 (同时复制应用文件)
    app_dir = create_app_bundle(args.version)

    log('=' * 50)
    log(f'.app 包已就绪: {app_dir}')

    # Step 5: 生成 DMG (可选)
    if args.skip_dmg:
        log(f'跳过 DMG 生成。.app 包在: {app_dir}')
    else:
        result = create_dmg(app_dir, args.version)
        if result:
            log('=' * 50)
            log('macOS 构建完成！')


if __name__ == '__main__':
    main()
