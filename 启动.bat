@echo off
echo ==========================================
echo   绩效评价审计智能体 — 启动中...
echo ==========================================
cd /d "D:\绩效评价审计智能体"
REM 清理占用5199端口的僵尸进程
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5199.*LISTENING"') do taskkill /F /PID %%a >nul 2>&1
REM 用 py launcher 而非 python，避免 WindowsApps 商店 stub 静默失败(exit 49)
py app\app.py
pause
