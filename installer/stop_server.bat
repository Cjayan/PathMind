@echo off
chcp 65001 >nul
echo ================================
echo   路径智慧库 - 停止服务
echo ================================
echo.

set "PID_FILE=%APPDATA%\路径智慧库\data\server.pid"

if exist "%PID_FILE%" (
    set /p PID=<"%PID_FILE%"
    echo 发现服务进程 PID: %PID%，正在终止...
    taskkill /F /PID %PID% >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    echo 服务已停止。
) else (
    echo 未找到 PID 文件，尝试按端口查找...
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
        echo 发现进程 PID: %%a，正在终止...
        taskkill /F /PID %%a >nul 2>&1
    )
    echo 完成。
)

timeout /t 2 >nul
