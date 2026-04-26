@echo off
chcp 65001 >nul
title 路径智慧库
echo ================================
echo   路径智慧库 - 启动中...
echo ================================
echo.

cd /d "%~dp0"

echo 正在启动服务器...
echo 启动后请访问: http://127.0.0.1:5000
echo 按 Ctrl+C 可停止服务器
echo.

python run.py

pause
