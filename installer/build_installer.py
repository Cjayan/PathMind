"""
路径智慧库 - 安装包构建脚本

用法: python installer/build_installer.py [--version 1.0.0] [--skip-nsis]

前置条件:
  - Python 3.10+
  - NSIS 3.x (makensis.exe 在 PATH 中，或用 --skip-nsis 跳过)
  - 网络连接 (首次下载 Python embeddable)
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

# ── 配置 ──
PYTHON_VERSION = '3.13.3'
PYTHON_EMBED_URL = f'https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip'
PYTHON_EMBED_FILENAME = f'python-{PYTHON_VERSION}-embed-amd64.zip'
GET_PIP_URL = 'https://bootstrap.pypa.io/get-pip.py'

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
BUILD_DIR = os.path.join(SCRIPT_DIR, 'build')
CACHE_DIR = os.path.join(SCRIPT_DIR, 'cache')

APP_NAME = '路径智慧库'

# 需要复制到 build 的应用文件/目录
APP_COPY_LIST = [
    ('app', 'app'),
    ('run.py', 'run.py'),
    ('config.yaml.example', 'config.yaml.example'),
]


def log(msg):
    print(f'[BUILD] {msg}')


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
            print(f'\r  进度: {pct}% ({downloaded // 1024}KB / {total // 1024}KB)', end='', flush=True)

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
    """下载解压嵌入式 Python 并启用 pip"""
    embed_zip = os.path.join(CACHE_DIR, PYTHON_EMBED_FILENAME)
    download_file(PYTHON_EMBED_URL, embed_zip)

    python_dir = os.path.join(BUILD_DIR, 'python')
    log(f'解压 Python embeddable 到 {python_dir}')
    os.makedirs(python_dir, exist_ok=True)
    with zipfile.ZipFile(embed_zip, 'r') as zf:
        zf.extractall(python_dir)

    # 修改 ._pth 文件启用 import site
    pth_files = glob.glob(os.path.join(python_dir, 'python*._pth'))
    if not pth_files:
        log('错误: 未找到 ._pth 文件')
        sys.exit(1)

    pth_file = pth_files[0]
    log(f'修改 {os.path.basename(pth_file)} 启用 site-packages')
    with open(pth_file, 'r') as f:
        content = f.read()

    content = content.replace('#import site', 'import site')
    if 'Lib\\site-packages' not in content:
        content += '\nLib\\site-packages\n'

    with open(pth_file, 'w') as f:
        f.write(content)

    return python_dir


def install_pip(python_dir):
    """安装 pip"""
    python_exe = os.path.join(python_dir, 'python.exe')
    get_pip = os.path.join(CACHE_DIR, 'get-pip.py')
    download_file(GET_PIP_URL, get_pip)

    log('安装 pip...')
    subprocess.run(
        [python_exe, get_pip, '--no-warn-script-location'],
        check=True,
        capture_output=True,
    )
    log('pip 安装完成')


def install_dependencies(python_dir):
    """安装项目依赖"""
    python_exe = os.path.join(python_dir, 'python.exe')
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


def copy_app_files():
    """复制应用文件到构建目录"""
    log('复制应用文件...')

    def ignore_patterns(directory, files):
        return [f for f in files if f == '__pycache__' or f.endswith('.pyc')]

    for src_name, dest_name in APP_COPY_LIST:
        src = os.path.join(PROJECT_ROOT, src_name)
        dest = os.path.join(BUILD_DIR, dest_name)
        if os.path.isdir(src):
            shutil.copytree(src, dest, ignore=ignore_patterns)
            log(f'  目录: {src_name}/')
        else:
            shutil.copy2(src, dest)
            log(f'  文件: {src_name}')

    # 复制 installer 专属文件
    for fname in ['launcher.pyw', 'stop_server.bat', 'debug_launch.bat', 'icon.ico']:
        src = os.path.join(SCRIPT_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BUILD_DIR, fname))
            log(f'  文件: installer/{fname}')
        else:
            log(f'  警告: installer/{fname} 不存在，跳过')


def compile_nsis(version):
    """编译 NSIS 安装包 (使用 compile_nsis.py 子脚本)"""
    compile_script = os.path.join(SCRIPT_DIR, 'compile_nsis.py')
    if not os.path.exists(compile_script):
        log('错误: compile_nsis.py 不存在')
        return None

    log('调用 compile_nsis.py 编译安装包...')
    result = subprocess.run(
        [sys.executable, compile_script, '--version', version],
        cwd=SCRIPT_DIR,
    )

    if result.returncode != 0:
        log('NSIS 编译失败')
        return None

    output_name = f'PathMind_Setup_v{version}.exe'
    output_path = os.path.join(SCRIPT_DIR, output_name)
    if os.path.exists(output_path):
        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        log(f'安装包生成成功: {output_path}')
        log(f'文件大小: {size_mb:.1f} MB')
        return output_path

    log('安装包文件未找到')
    return None


def main():
    parser = argparse.ArgumentParser(description='构建路径智慧库安装包')
    parser.add_argument('--version', default='1.0.0', help='版本号 (默认: 1.0.0)')
    parser.add_argument('--skip-nsis', action='store_true', help='跳过 NSIS 编译，仅准备构建文件')
    args = parser.parse_args()

    log(f'开始构建 v{args.version}')
    log(f'项目根目录: {PROJECT_ROOT}')
    log(f'构建目录: {BUILD_DIR}')
    log('=' * 50)

    # Step 1: 清理
    clean_build()

    # Step 2: 下载并配置嵌入式 Python
    python_dir = setup_python()

    # Step 3: 安装 pip
    install_pip(python_dir)

    # Step 4: 安装依赖
    install_dependencies(python_dir)

    # Step 5: 复制应用文件
    copy_app_files()

    log('=' * 50)
    log('构建文件准备完成')

    # Step 6: 编译 NSIS (可选)
    if args.skip_nsis:
        log(f'跳过 NSIS 编译。构建文件在: {BUILD_DIR}')
    else:
        result = compile_nsis(args.version)
        if result:
            log('=' * 50)
            log('构建完成！')


if __name__ == '__main__':
    main()
