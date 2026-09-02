# SiteSight packaging script (PyInstaller + Inno Setup)
# Usage: from repo root: powershell -ExecutionPolicy Bypass -File packaging\build.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==== 1/6 Install deps (pywebview / pyinstaller / Pillow) ===="
python -m pip install --quiet pywebview pyinstaller Pillow

Write-Host "==== 2/6 Check / install Inno Setup 6 (per-user) ===="
$innoCandidates = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno\ISCC.exe"),
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
)
$iscc = $innoCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
if (-not $iscc) {
    Write-Host "Inno Setup 未安装，准备下载 6.7.3 ..."
    $setup = Join-Path $env:TEMP "innosetup-6.7.3.exe"
    $urls = @(
        "https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe",
        "https://gh-proxy.com/https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe",
        "https://ghfast.top/https://github.com/jrsoftware/issrc/releases/download/is-6_7_3/innosetup-6.7.3.exe"
    )
    $downloaded = $false
    foreach ($u in $urls) {
        try {
            Write-Host "尝试下载: $u"
            curl.exe -L --connect-timeout 10 --max-time 600 -o $setup $u
            if ((Get-Item $setup -ErrorAction SilentlyContinue).Length -gt 5MB) {
                $downloaded = $true
                break
            }
        } catch {
            Write-Host "下载失败: $($_.Exception.Message)"
        }
    }
    if (-not $downloaded) { throw "无法下载 Inno Setup 安装器，请手动安装后重试" }

    $innoDir = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6"
    $argsLine = '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR="' + $innoDir + '"'
    $p = Start-Process -FilePath $setup -ArgumentList $argsLine -Wait -PassThru
    if ($p.ExitCode -ne 0) { throw "Inno Setup 安装失败 (exit $($p.ExitCode))" }
    $iscc = Join-Path $innoDir "ISCC.exe"
}
if (-not $iscc -or -not (Test-Path $iscc)) { throw "Inno Setup 安装后仍找不到 ISCC.exe" }
Write-Host "使用 Inno Setup: $iscc"

Write-Host "==== 3/6 Generate app icon ===="
if (Test-Path "app\static\assets\logo\logo_transparent.png") {
    python packaging\make_logo_icon.py
} else {
    python packaging\make_icon.py
}

Write-Host "==== 4/6 PyInstaller build ===="
python -m PyInstaller --noconfirm --clean --onedir --noconsole --name SiteSight `
    --add-data "app\static;static" `
    --add-data "app\config.example.json;." `
    --add-data "packaging\assets\sitesight.ico;." `
    --hidden-import "webview.platforms.edgechromium" `
    --icon "packaging\assets\sitesight.ico" `
    app\launcher.py

Write-Host "==== 5/6 Assemble dist + copy ODM engine ===="
$dist = "dist\SiteSight"
# ODM 引擎源目录：优先使用环境变量 ODM_SOURCE_DIR，未设置时使用通用默认 D:\ODM
$odmSource = $env:ODM_SOURCE_DIR
if (-not $odmSource) { $odmSource = "D:\ODM" }
# 说明：不再内置任何 API 密钥。AI 报告密钥由使用者在「设置 → 外部 API 接入」中自行填写，
# 仅保存在本机用户目录（~\.sitesight\config.json），不入库、不随安装包分发。
# 演示数据：server.py 按“_internal 的上级目录/data”查找
if (-not (Test-Path "$dist\data")) {
    robocopy "data" "$dist\data" /E /NFL /NDL /NJH /NJS | Out-Null
}
if (-not (Test-Path "$dist\ODM")) {
    Write-Host "复制 ODM 引擎（4-6 GB，需要几分钟）..."
    robocopy "$odmSource" "$dist\ODM" /E /R:1 /W:1 /MT:8 /NFL /NDL /NJH /NJS
}
# 修复 ODM venv 中 cv2 的绝对路径配置（避免重定位后建模报 cv2 recursion 错误）
python packaging\fix_odm_cv2.py "$dist\ODM"
Copy-Item "LICENSE" "$dist\LICENSE.txt" -Force
Copy-Item "README.md" "$dist\README.txt" -Force
if (Test-Path "$odmSource\licenses") {
    robocopy "$odmSource\licenses" "$dist\ODM_LICENSES" /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "==== 6/6 Compile installer ===="
& $iscc "packaging\SiteSight.iss"
Write-Host "DONE! Installer is in packaging\output\"
