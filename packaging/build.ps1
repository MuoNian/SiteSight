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
# server.py / site_report.py 会在 _internal 目录里找 config.json（AI 报告密钥）
if (Test-Path "app\config.json") {
    Copy-Item "app\config.json" "$dist\_internal\config.json" -Force
    Write-Host "已复制 app\config.json -> _internal\config.json"
}
# 演示数据：server.py 按“_internal 的上级目录/data”查找
if (-not (Test-Path "$dist\data")) {
    robocopy "data" "$dist\data" /E /NFL /NDL /NJH /NJS | Out-Null
}
if (-not (Test-Path "$dist\ODM")) {
    Write-Host "复制 ODM 引擎（4-6 GB，需要几分钟）..."
    robocopy "D:\WebODM（OpenDroneMap）\ODM" "$dist\ODM" /E /R:1 /W:1 /MT:8 /NFL /NDL /NJH /NJS
}
Copy-Item "LICENSE" "$dist\LICENSE.txt" -Force
Copy-Item "README.md" "$dist\README.txt" -Force
if (Test-Path "D:\WebODM（OpenDroneMap）\ODM\licenses") {
    robocopy "D:\WebODM（OpenDroneMap）\ODM\licenses" "$dist\ODM_LICENSES" /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "==== 6/6 Compile installer ===="
& $iscc "packaging\SiteSight.iss"
Write-Host "DONE! Installer is in packaging\output\"
