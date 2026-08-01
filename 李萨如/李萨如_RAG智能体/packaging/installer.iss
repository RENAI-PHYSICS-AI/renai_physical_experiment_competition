#ifndef SourceDir
  #define SourceDir "dist\LissajousExperimentTutor"
#endif
#ifndef OutputDir
  #define OutputDir "dist\installer"
#endif

[Setup]
AppId={{E459E72C-13C9-4CAA-B0D5-0D5EA17DFA48}
AppName=李萨如图形实验智能助教
AppVersion=1.0.1
AppPublisher=仁爱物理竞赛
DefaultDirName={localappdata}\Programs\LissajousExperimentTutor
DefaultGroupName=李萨如图形实验智能助教
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#OutputDir}
OutputBaseFilename=李萨如图形实验智能助教_Setup_1.0.1
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\李萨如图形实验智能助教.exe
SetupLogging=no

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\李萨如图形实验智能助教"; Filename: "{app}\李萨如图形实验智能助教.exe"
Name: "{autodesktop}\李萨如图形实验智能助教"; Filename: "{app}\李萨如图形实验智能助教.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加快捷方式："; Flags: unchecked

[Run]
Filename: "{app}\李萨如图形实验智能助教.exe"; Description: "启动李萨如图形实验智能助教"; Flags: nowait postinstall skipifsilent
