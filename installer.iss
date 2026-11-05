; Установщик Inno Setup 6. Собирается командой:  python build.py --installer
; (build.py сам собирает папку dist\XeroxZineStudio и передаёт версию через /DAppVersion=...)
#ifndef AppVersion
  #define AppVersion "2.5.0"
#endif

[Setup]
AppId={{8F3B0C52-6E0A-4D8E-9B57-2C5E1D7A4F10}
AppName=Xerox Zine Studio
AppVersion={#AppVersion}
AppPublisher=Xerox Zine Studio
DefaultDirName={autopf}\Xerox Zine Studio
DefaultGroupName=Xerox Zine Studio
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=XeroxZineStudio-Setup-{#AppVersion}
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\XeroxZineStudio.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern
ChangesAssociations=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "assoc"; Description: "Открывать файлы .zine в Xerox Zine Studio"; GroupDescription: "Файлы:"

[Files]
Source: "dist\XeroxZineStudio\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Xerox Zine Studio"; Filename: "{app}\XeroxZineStudio.exe"
Name: "{autodesktop}\Xerox Zine Studio"; Filename: "{app}\XeroxZineStudio.exe"; Tasks: desktopicon

[Registry]
Root: HKA; Subkey: "Software\Classes\.zine"; ValueType: string; ValueName: ""; ValueData: "XeroxZineStudio.Project"; Flags: uninsdeletevalue; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\XeroxZineStudio.Project"; ValueType: string; ValueName: ""; ValueData: "Проект Xerox Zine Studio"; Flags: uninsdeletekey; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\XeroxZineStudio.Project\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\XeroxZineStudio.exe,0"; Tasks: assoc
Root: HKA; Subkey: "Software\Classes\XeroxZineStudio.Project\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\XeroxZineStudio.exe"" ""%1"""; Tasks: assoc

[Run]
Filename: "{app}\XeroxZineStudio.exe"; Description: "{cm:LaunchProgram,Xerox Zine Studio}"; Flags: nowait postinstall skipifsilent
