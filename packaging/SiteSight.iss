#define MyAppName "鹭见 SiteSight"
#define MyAppVersion "1.0.0"
#define MyAppExeName "SiteSight.exe"

[Setup]
AppId={{8D5F2E7A-1C3B-4E2F-9A6D-B1C2D3E4F5A6}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=MuoNian
SetupIconFile=assets\sitesight.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
DefaultDirName={autopf}\SiteSight
DefaultGroupName={#MyAppName}
OutputDir=output
OutputBaseFilename=LuJianSiteSight_Setup
Compression=none
SolidCompression=no
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
ShowLanguageDialog=yes

[Languages]
Name: "chinesesimp"; MessagesFile: "languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
LaunchNow=Launch {#MyAppName} now
DesktopIcon=Create a desktop shortcut
AdditionalTasks=Additional tasks:

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式 / Create desktop shortcut"; GroupDescription: "附加任务: / Additional tasks:"; Flags: checkedonce

[Files]
Source: "..\dist\SiteSight\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "立即启动 鹭见 SiteSight / Launch 鹭见 SiteSight now"; Flags: nowait postinstall skipifsilent
