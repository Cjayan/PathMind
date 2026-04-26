@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   路径智慧库 - 调试启动
echo ============================================
echo.

set "INSTALL_DIR=%~dp0"
set "PYTHON_EXE=%INSTALL_DIR%python\python.exe"
set "LAUNCHER=%INSTALL_DIR%launcher.pyw"

echo Install Dir : %INSTALL_DIR%
echo Python      : %PYTHON_EXE%
echo Launcher    : %LAUNCHER%
echo.

if not exist "%PYTHON_EXE%" (
    echo [ERROR] python.exe not found: %PYTHON_EXE%
    echo.
    pause
    exit /b 1
)

if not exist "%LAUNCHER%" (
    echo [ERROR] launcher.pyw not found: %LAUNCHER%
    echo.
    pause
    exit /b 1
)

echo [INFO] Testing Python...
"%PYTHON_EXE%" -c "import sys; print(f'Python {sys.version}'); print(f'Prefix: {sys.prefix}')"
echo.

echo [INFO] Testing imports...
"%PYTHON_EXE%" -c "import flask; print(f'Flask {flask.__version__}')"
if errorlevel 1 (
    echo [ERROR] Flask import failed!
    echo.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import pystray; print('pystray OK')" 2>&1
"%PYTHON_EXE%" -c "from PIL import Image; print('Pillow OK')" 2>&1
echo.

echo [INFO] Starting launcher with console output...
echo ============================================
"%PYTHON_EXE%" "%LAUNCHER%"

echo.
echo ============================================
echo Launcher exited with code: %errorlevel%
echo.
echo Check logs at: %APPDATA%\路径智慧库\data\launcher.log
echo.
pause
