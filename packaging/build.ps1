# 鹭见 SiteSight 打包脚本（PyInstaller + Inno Setup）
# 用法：在仓库根目录执行  powershell -ExecutionPolicy Bypass -File packaging\build.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==== 1/5 安装依赖（pywebview / pyinstaller / Pillow）===="
python -m pip install --quiet pywebview pyinstaller Pillow

Write-Host "==== 2/5 检查 / 安装 Inno Setup 6 ===="
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) {
    $setup = "$env:TEMP\innosetup.exe"
    Invoke-WebRequest -Uri "https://jrsoftware.org/download.php/is.exe" -OutFile $setup
    Start-Process -FilePath $setup -ArgumentList "/VERYSILENT","/SUPPRESSMSGBOXES","/NORESTART" -Wait
}
if (-not (Test-Path $iscc)) { throw "Inno Setup 安装失败" }

Write-Host "==== 3/5 生成应用图标 ===="
python packaging\make_icon.py

Write-Host "==== 4/5 PyInstaller 打包 ===="
python -m PyInstaller --noconfirm --clean --onedir --name SiteSight `
    --add-data "app\static;static" `
    --add-data "data;data" `
    --add-data "app\config.example.json;." `
    --icon "packaging\assets\sitesight.ico" `
    app\launcher.py

Write-Host "==== 5/5 组装分发目录 + 打包 ODM 引擎 ===="
$dist = "dist\SiteSight"
if (-not (Test-Path "$dist\ODM")) {
    Write-Host "正在复制 ODM 引擎（约 4-6 GB，需几分钟）..."
    robocopy "D:\WebODM（OpenDroneMap）\ODM" "$dist\ODM" /E /R:1 /W:1 /MT:8 /NFL /NDL /NJH /NJS
}
Copy-Item "LICENSE" "$dist\LICENSE.txt" -Force
Copy-Item "README.md" "$dist\README.txt" -Force
if (Test-Path "D:\WebODM（OpenDroneMap）\ODM\licenses") {
    robocopy "D:\WebODM（OpenDroneMap）\ODM\licenses" "$dist\ODM_LICENSES" /E /NFL /NDL /NJH /NJS | Out-Null
}

Write-Host "==== 编译安装包 ===="
& $iscc "packaging\SiteSight.iss"
Write-Host "完成！安装包在 packaging\output\ 下"
