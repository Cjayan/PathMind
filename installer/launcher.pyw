"""
路径智慧库 - 启动器
由 pythonw.exe 执行，无控制台窗口。
功能：启动 Flask 服务 → 打开浏览器 → 系统托盘图标管理。
"""
import os
import sys
import logging
import traceback

# ── 路径 (提前初始化，用于错误日志) ──
INSTALL_DIR = os.path.dirname(os.path.abspath(__file__))
APP_NAME = '路径智慧库'
if sys.platform == 'darwin':
    DATA_DIR = os.path.join(os.path.expanduser('~/Library/Application Support'), APP_NAME)
else:
    DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), APP_NAME)
LOG_DIR = os.path.join(DATA_DIR, 'data')

# ── 错误日志 (最先初始化，确保所有异常都能被记录) ──
os.makedirs(LOG_DIR, exist_ok=True)
_launcher_log = os.path.join(LOG_DIR, 'launcher.log')
logging.basicConfig(
    filename=_launcher_log,
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    encoding='utf-8',
)
log = logging.getLogger('launcher')

# 同时捕获 pythonw.exe 下被丢弃的 stderr
try:
    sys.stderr = open(os.path.join(LOG_DIR, 'launcher_stderr.log'), 'w', encoding='utf-8')
except Exception:
    pass

log.info('=' * 40)
log.info('Launcher starting')
log.info(f'INSTALL_DIR = {INSTALL_DIR}')
log.info(f'DATA_DIR    = {DATA_DIR}')
log.info(f'Python      = {sys.executable}')
log.info(f'sys.path    = {sys.path}')

import socket
import subprocess
import time
import webbrowser
import shutil

# ── 路径 ──
if sys.platform == 'darwin':
    PYTHON_EXE = os.path.join(INSTALL_DIR, 'python', 'bin', 'python3')
else:
    PYTHON_EXE = os.path.join(INSTALL_DIR, 'python', 'python.exe')

# Fallback: if embedded Python doesn't exist, use the current interpreter
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable
    log.info(f'Embedded Python not found, falling back to sys.executable')

RUN_PY = os.path.join(INSTALL_DIR, 'run.py')

# Fallback: if run.py doesn't exist in INSTALL_DIR, look in parent (dev layout)
if not os.path.exists(RUN_PY):
    RUN_PY = os.path.join(os.path.dirname(INSTALL_DIR), 'run.py')
    log.info(f'run.py not found in INSTALL_DIR, trying parent: {RUN_PY}')

# Ensure the project root (directory containing run.py) is in sys.path
# so that `from app.floating_window...` imports work in dev mode
_project_root = os.path.dirname(os.path.abspath(RUN_PY))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
    log.info(f'Added to sys.path: {_project_root}')
ICON_PATH = os.path.join(INSTALL_DIR, 'icon.icns' if sys.platform == 'darwin' else 'icon.ico')
CONFIG_EXAMPLE = os.path.join(INSTALL_DIR, 'config.yaml.example')

log.info(f'PYTHON_EXE  = {PYTHON_EXE} (exists: {os.path.exists(PYTHON_EXE)})')
log.info(f'RUN_PY      = {RUN_PY} (exists: {os.path.exists(RUN_PY)})')
log.info(f'ICON_PATH   = {ICON_PATH} (exists: {os.path.exists(ICON_PATH)})')

# ── 工具函数 ──

def port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0


def find_available_port(start=5000, end=5099):
    for p in range(start, end):
        if not port_in_use(p):
            return p
    return start


def read_pid():
    pid_file = os.path.join(DATA_DIR, 'data', 'server.pid')
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                return int(f.read().strip())
        except (ValueError, OSError):
            pass
    return None


def write_pid(pid):
    pid_dir = os.path.join(DATA_DIR, 'data')
    os.makedirs(pid_dir, exist_ok=True)
    with open(os.path.join(pid_dir, 'server.pid'), 'w') as f:
        f.write(str(pid))


def clear_pid():
    pid_file = os.path.join(DATA_DIR, 'data', 'server.pid')
    if os.path.exists(pid_file):
        try:
            os.remove(pid_file)
        except OSError:
            pass


def is_process_running(pid):
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def init_data_dir():
    # Migrate data from old app name if needed
    _OLD_NAME = '产品使用路径知识库'
    if sys.platform == 'darwin':
        _old_dir = os.path.join(os.path.expanduser('~/Library/Application Support'), _OLD_NAME)
    else:
        _old_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), _OLD_NAME)
    if os.path.isdir(_old_dir) and not os.path.exists(DATA_DIR):
        try:
            os.rename(_old_dir, DATA_DIR)
            log.info(f'Migrated data directory: {_old_dir} -> {DATA_DIR}')
        except OSError as e:
            log.warning(f'Failed to migrate data directory: {e}')

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, 'data'), exist_ok=True)
    config_dest = os.path.join(DATA_DIR, 'config.yaml')
    if not os.path.exists(config_dest) and os.path.exists(CONFIG_EXAMPLE):
        shutil.copy2(CONFIG_EXAMPLE, config_dest)


def wait_for_server(port, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if port_in_use(port):
            return True
        time.sleep(0.5)
    return False


# ── 主逻辑 ──

class AppLauncher:
    def __init__(self):
        self.process = None
        self.port = 5000
        self.tray_icon = None

    def start_server(self):
        init_data_dir()

        # 检查是否已有实例在运行
        existing_pid = read_pid()
        if is_process_running(existing_pid):
            # 已有实例，直接打开浏览器
            log.info(f'Existing instance found (pid={existing_pid}), opening browser.')
            webbrowser.open(f'http://127.0.0.1:{self.port}/')
            return False

        clear_pid()
        self.port = find_available_port()
        log.info(f'Using port {self.port}')

        env = os.environ.copy()
        env['PATHMIND_DATA_DIR'] = DATA_DIR
        env['PATHMIND_PORT'] = str(self.port)
        env['FLASK_ENV'] = 'production'

        log_path = os.path.join(DATA_DIR, 'data', 'server.log')
        log_file = open(log_path, 'w', encoding='utf-8')

        creation_flags = 0
        if sys.platform == 'win32':
            creation_flags = subprocess.CREATE_NO_WINDOW

        cmd = [PYTHON_EXE, RUN_PY]
        log.info(f'Starting server: {cmd}')

        # cwd should be the directory containing run.py
        server_cwd = os.path.dirname(RUN_PY)

        self.process = subprocess.Popen(
            cmd,
            cwd=server_cwd,
            env=env,
            stdout=log_file,
            stderr=log_file,
            creationflags=creation_flags,
        )
        write_pid(self.process.pid)
        log.info(f'Server process started, pid={self.process.pid}')

        if wait_for_server(self.port):
            log.info('Server is ready, opening browser.')
            webbrowser.open(f'http://127.0.0.1:{self.port}/')
            return True
        else:
            log.warning('Server did not become ready within timeout, continuing anyway.')
        return True  # 继续运行即使超时

    def stop_server(self):
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            except OSError:
                pass
            self.process = None
        clear_pid()

    def open_browser(self):
        webbrowser.open(f'http://127.0.0.1:{self.port}/')

    def quit_app(self):
        self.stop_server()
        if self.tray_icon:
            self.tray_icon.stop()

    def run_with_pyqt6(self):
        """Use PyQt6 for system tray + floating window support."""
        try:
            from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
            from PyQt6.QtGui import QIcon, QAction, QPixmap
            log.info('PyQt6 imported successfully.')
        except ImportError as e:
            log.warning(f'PyQt6 import failed: {e}, falling back to pystray.')
            return False

        app = QApplication(sys.argv)
        app.setQuitOnLastWindowClosed(False)

        # System tray icon
        if os.path.exists(ICON_PATH):
            icon = QIcon(ICON_PATH)
        else:
            pm = QPixmap(64, 64)
            pm.fill()
            icon = QIcon(pm)

        tray = QSystemTrayIcon(icon, app)
        tray.setToolTip(APP_NAME)

        # Floating window (lazy-created)
        floating_win = None

        def open_floating():
            nonlocal floating_win
            try:
                from app.floating_window.main_window import FloatingWindow
                if floating_win is None or not floating_win.isVisible():
                    floating_win = FloatingWindow(port=self.port)
                    floating_win.show()
                    log.info('Floating window opened.')
                else:
                    floating_win.activateWindow()
                    floating_win.raise_()
            except Exception as e:
                log.error(f'Failed to open floating window: {e}')

        def quit_all():
            if floating_win and floating_win.isVisible():
                floating_win.close()
            tray.hide()
            self.stop_server()
            app.quit()

        menu = QMenu()
        act_browser = QAction('打开浏览器', app)
        act_browser.triggered.connect(lambda: self.open_browser())
        menu.addAction(act_browser)

        act_float = QAction('悬浮窗录制', app)
        act_float.triggered.connect(open_floating)
        menu.addAction(act_float)

        menu.addSeparator()
        act_quit = QAction('停止并退出', app)
        act_quit.triggered.connect(quit_all)
        menu.addAction(act_quit)

        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: (
            self.open_browser() if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
        ))
        tray.show()
        log.info('PyQt6 system tray running.')

        app.exec()
        return True

    def run_with_pystray(self):
        """Fallback: use pystray for system tray (no floating window)."""
        try:
            import pystray
            from PIL import Image
            log.info('pystray and PIL imported successfully.')
        except ImportError as e:
            log.warning(f'pystray/PIL import failed: {e}, running without tray.')
            self.run_without_tray()
            return

        if os.path.exists(ICON_PATH):
            icon_image = Image.open(ICON_PATH)
        else:
            icon_image = Image.new('RGB', (64, 64), color=(66, 133, 244))

        menu = pystray.Menu(
            pystray.MenuItem('打开浏览器', lambda: self.open_browser()),
            pystray.MenuItem('停止并退出', lambda: self.quit_app()),
        )

        self.tray_icon = pystray.Icon(APP_NAME, icon_image, APP_NAME, menu)
        self.tray_icon.run()

    def run_with_tray(self):
        """Try PyQt6 first, fall back to pystray."""
        if not self.run_with_pyqt6():
            self.run_with_pystray()

    def run_without_tray(self):
        # 无托盘模式：等待进程结束
        if self.process:
            try:
                self.process.wait()
            except KeyboardInterrupt:
                self.stop_server()


def main():
    launcher = AppLauncher()

    should_wait = launcher.start_server()
    if should_wait is False:
        # 已有实例在运行，已打开浏览器，直接退出
        log.info('Another instance is running, exiting.')
        return

    launcher.run_with_tray()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        log.error(f'Fatal error:\n{traceback.format_exc()}')
        # 在非 pythonw 模式下也尝试打印到控制台
        traceback.print_exc()
        # 弹出错误提示框让用户知道出了问题
        try:
            msg = (
                f'启动失败，请查看日志文件：\n{_launcher_log}\n\n'
                f'{traceback.format_exc()[-500:]}'
            )
            if sys.platform == 'darwin':
                esc_msg = msg.replace('"', '\\"').replace('\n', '\\n')
                subprocess.run([
                    'osascript', '-e',
                    f'display dialog "{esc_msg}" with title "{APP_NAME}" buttons "OK" with icon stop',
                ], timeout=30)
            else:
                import ctypes
                ctypes.windll.user32.MessageBoxW(0, msg, APP_NAME, 0x10)
        except Exception:
            pass
