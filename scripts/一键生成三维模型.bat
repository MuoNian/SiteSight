@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   鹭见 SiteSight - 一键三维建模（大疆 Lito X1 适用）
echo ============================================
echo.

REM ---------- 1. 获取照片文件夹 ----------
set "SRC=%~1"
if "%SRC%"=="" (
    echo 请把要处理的照片文件夹，拖到本文件图标上。即可运行
    echo 或直接输入文件夹路径后按回车：
    set /p SRC=路径：
)

if not exist "%SRC%" (
    echo [错误] 找不到文件夹：%SRC%
    pause
    exit /b 1
)

REM ---------- 2. 定位 JPG 照片 ----------
set "PHOTODIR=%SRC%"
if exist "%SRC%\images\*.jpg" set "PHOTODIR=%SRC%\images"
if not exist "%PHOTODIR%\*.jpg" (
    echo [错误] 该文件夹里没有 JPG 照片：%PHOTODIR%
    pause
    exit /b 1
)

set /a N=0
for %%f in ("%PHOTODIR%\*.jpg") do set /a N+=1
if %N% LSS 2 (
    echo [错误] 至少需要 2 张照片才能建模
    pause
    exit /b 1
)

REM ---------- 3. 建立项目目录 ----------
REM 注意：ODM 不支持中文路径，成果目录固定用英文 SiteSight_Results
set "PROJROOT=%USERPROFILE%\Desktop\SiteSight_Results"
if defined ODM_PROJROOT set "PROJROOT=%ODM_PROJROOT%"
if not exist "%PROJROOT%" mkdir "%PROJROOT%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "NAME=project_%%i"
set "PROJ=%PROJROOT%\%NAME%"
mkdir "%PROJ%\images" 2>nul

echo 照片来源：%PHOTODIR%
echo 照片数量：%N% 张
echo 成果目录：%PROJ%
echo.
echo 正在复制照片...
copy "%PHOTODIR%\*.jpg" "%PROJ%\images\" >nul
echo 复制完成，开始建模（预计 10-40 分钟，请勿关闭本窗口）...
echo 处理日志会同时显示在窗口里并保存到 processing.log
echo.

REM ---------- 4. 启动 ODM ----------
cd /d "D:\WebODM（OpenDroneMap）\ODM"
set "EXTRA="
if "%ODM_FAST%"=="1" set "EXTRA=--fast"
call winrun.bat --project-path "%PROJROOT%" "%NAME%" --dsm %EXTRA% 2>&1 | powershell -NoProfile -Command "$input | Tee-Object -FilePath '%PROJ%\processing.log'"

echo.
echo ============ 处理结果 ============
powershell -NoProfile -Command "if (Select-String -Quiet -Path '%PROJ%\processing.log' -Pattern 'ODM app finished') { exit 0 } else { exit 1 }"
if %errorlevel%==0 (
    echo 处理成功！全部成果在：%PROJ%
) else (
    echo [失败] ODM 没有正常完成，请打开 processing.log 查看原因
    echo 常见原因：照片模糊、重叠率不够、照片不是 JPG。
)
if not "%ODM_NO_EXPLORER%"=="1" start "" explorer "%PROJ%"
if not "%ODM_NO_PAUSE%"=="1" pause
