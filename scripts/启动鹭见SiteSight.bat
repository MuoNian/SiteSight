@echo off
chcp 936 >nul
cd /d %~dp0..\app
echo ============================================
echo    鹭见 SiteSight 正在启动，请稍候...
echo ============================================
echo 若浏览器未自动打开，请手动访问 http://127.0.0.1:8765
where py >nul 2>nul
if %errorlevel%==0 (
    start "SiteSight" cmd /k "py -3 server.py"
) else (
    start "SiteSight" cmd /k "python server.py"
)
