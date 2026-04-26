@echo off
chcp 65001 >nul
echo ================================
echo   路径智慧库 - 停止服务
echo ================================
echo.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000" ^| findstr "LISTENING"') do (
    echo 发现进程 PID: %%a，正在终止...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo 服务已停止。
timeout /t 2 >nul
