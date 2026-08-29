#define MyAppName "鹭见 SiteSight"
#define MyAppVersion "1.0.0"
#define MyAppExeName "SiteSight.exe"

[Setup]
AppId={{8D5F2E7A-1C3B-4E2F-9A6D-B1C2D3E4F5A6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=MuoNian
DefaultDirName={autopf}\SiteSight
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=output
OutputBaseFilename=LuJianSiteSight_Setup
Compression=none
SolidCompression=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务:"; Flags: checkedonce

[Files]
Source: "dist\SiteSight\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 {#MyAppName}"; Flags: nowait postinstall skipifsilent
