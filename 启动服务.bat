@echo off
chcp 65001 >nul
title 路径智慧库
echo ================================
echo   路径智慧库 - 启动中...
echo ================================
echo.

cd /d "%~dp0"

echo 正在启动服务（含系统托盘 + 悬浮窗支持）...
echo 启动后右键系统托盘图标可打开浏览器或悬浮窗录制
echo.

:: 优先使用 pythonw 启动 launcher（带托盘，无控制台窗口）
where pythonw >nul 2>&1
if %errorlevel%==0 (
    echo [托盘模式] 使用 pythonw 启动，此窗口将自动关闭...
    start "" pythonw installer\launcher.pyw
    exit
) else (
    echo [提示] 未找到 pythonw，使用 python 启动（控制台窗口将保持打开）...
    echo 按 Ctrl+C 可停止服务器
    echo.
    python installer\launcher.pyw
    pause
)
