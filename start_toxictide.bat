@echo off
REM TOXICTIDE 启动脚本（Windows）
REM 自动打开两个窗口：主程序 + 日志监控

echo Starting TOXICTIDE Trading System...
echo.

REM 启动主程序（静默版）
start "TOXICTIDE - Main" cmd /k "cd /d %~dp0 && python main.py"

REM 等待 2 秒
timeout /t 2 /nobreak >nul

REM 启动日志监控
start "TOXICTIDE - Logs" cmd /k "cd /d %~dp0 && powershell -Command Get-Content logs\system.log -Wait -Tail 20"

echo.
echo TOXICTIDE has been started!
echo - Main window: CLI interface
echo - Logs window: Real-time system logs
echo.
pause
