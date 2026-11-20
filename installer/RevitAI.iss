; Inno Setup script for Revit AI.
; Installs per-user (no admin rights needed) so the self-updater can run.
; Build with: ISCC.exe /DMyAppVersion=0.1.0 installer\RevitAI.iss

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

#define MyAppName "Revit AI"
#define MyAppExe "RevitAI.exe"

[Setup]
AppId={{B7E2C1A4-6F3D-4E8A-9C21-5D0E8A1F2B3C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=Revit AI
DefaultDirName={localappdata}\Programs\RevitAI
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=RevitAI-Setup
SetupIconFile=..\app\assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked
Name: "bridge"; Description: "Install the Revit bridge into pyRevit (requires pyRevit)"; GroupDescription: "Revit:"

[Files]
Source: "..\dist\{#MyAppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\revit_bridge\AgentBridge.extension\*"; DestDir: "{userappdata}\pyRevit\Extensions\AgentBridge.extension"; Flags: ignoreversion recursesubdirs createallsubdirs; Tasks: bridge

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExe}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\RevitAI"
