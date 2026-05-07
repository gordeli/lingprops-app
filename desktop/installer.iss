; -------------------------------------------------------------------
; Inno Setup script for the LingProps desktop installer.
;
; Build the .exe first:    pyinstaller lingprops_app.spec --noconfirm
; Then build the installer: ISCC.exe installer.iss
;
; The build.bat in this folder runs both in sequence.
;
; Output:  Output\LingProps_Setup.exe
; -------------------------------------------------------------------

#define MyAppName       "LingProps"
#define MyAppVersion    "1.1.0"
#define MyAppPublisher  "Ivan Gordeliy"
#define MyAppURL        "https://github.com/gordeli/lingprops-app"
#define MyAppExeName    "LingProps.exe"

[Setup]
AppId={{6A2DB5C9-4A3F-4F74-9B6C-4D7A3A3B4C5D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=LingProps_Setup_v{#MyAppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; \
    Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; \
    Description: "Launch {#MyAppName} now"; \
    Flags: nowait postinstall skipifsilent
