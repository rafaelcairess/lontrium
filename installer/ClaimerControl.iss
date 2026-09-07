#define MyAppName "Lontrium Control"
#define MyAppVersion "1.0.1"
#define MyAppPublisher "Rafael Caires"
#define MyAppURL "https://github.com/rafaelcairess/lontrium"

[Setup]
AppId={{28DAA8F0-B66F-40AB-A903-2FF4EC61A32B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases/latest
DefaultDirName={localappdata}\Programs\Lontrium Control
DefaultGroupName=Lontrium Control
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=output
OutputBaseFilename=Lontrium-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=Lontrium Control
LicenseFile=..\LICENSE
SetupIconFile=Lontrium.ico
UninstallDisplayIcon={app}\Lontrium.ico

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "security-en.txt"
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"; InfoBeforeFile: "security-pt-BR.txt"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"; InfoBeforeFile: "security-es.txt"

[CustomMessages]
en.AutoStartTask=Start Lontrium Control when I sign in to Windows
en.EconomyModeTask=Economy mode — run claims, then stop Docker and release WSL memory
en.DashboardModeTask=Dashboard mode — keep Lontrium Control and Docker running
en.AutomationGroup=Automation
en.StartAfterInstall=Start Lontrium Control
ptbr.AutoStartTask=Iniciar o Lontrium Control ao entrar no Windows
ptbr.EconomyModeTask=Modo econômico — coletar e depois fechar o Docker e liberar a memória WSL
ptbr.DashboardModeTask=Modo painel — manter o Lontrium Control e o Docker ligados
ptbr.AutomationGroup=Automação
ptbr.StartAfterInstall=Iniciar o Lontrium Control
es.AutoStartTask=Iniciar Lontrium Control al entrar en Windows
es.EconomyModeTask=Modo económico — ejecutar y luego cerrar Docker y liberar la memoria WSL
es.DashboardModeTask=Modo panel — mantener Lontrium Control y Docker activos
es.AutomationGroup=Automatización
es.StartAfterInstall=Iniciar Lontrium Control

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "autostart"; Description: "{cm:AutoStartTask}"; GroupDescription: "{cm:AutomationGroup}"; Flags: checkedonce
Name: "autostart\economy"; Description: "{cm:EconomyModeTask}"; Flags: exclusive checkedonce
Name: "autostart\dashboard"; Description: "{cm:DashboardModeTask}"; Flags: exclusive

[Files]
Source: "Start-ClaimerControl.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "Start-ClaimerControl.cmd"; DestDir: "{app}"; Flags: ignoreversion
Source: "docker-compose.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "claimer.env"; DestDir: "{app}"; Flags: ignoreversion onlyifdoesntexist
Source: "Lontrium.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Lontrium Control"; Filename: "{app}\Start-ClaimerControl.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\Lontrium.ico"
Name: "{autodesktop}\Lontrium Control"; Filename: "{app}\Start-ClaimerControl.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\Lontrium.ico"; Tasks: desktopicon
Name: "{userstartup}\Lontrium Control"; Filename: "powershell.exe"; Parameters: "-NoLogo -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File ""{app}\Start-ClaimerControl.ps1"" -Action economy"; WorkingDir: "{app}"; IconFilename: "{app}\Lontrium.ico"; Tasks: autostart\economy
Name: "{userstartup}\Lontrium Control"; Filename: "{app}\Start-ClaimerControl.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\Lontrium.ico"; Tasks: autostart\dashboard
Name: "{group}\Uninstall Lontrium Control"; Filename: "{uninstallexe}"

[InstallDelete]
Type: files; Name: "{userstartup}\Lontrium Control.lnk"
Type: files; Name: "{autodesktop}\Claimer Control.lnk"
Type: files; Name: "{userstartup}\Claimer Control.lnk"
Type: files; Name: "{group}\Claimer Control.lnk"
Type: files; Name: "{group}\Uninstall Claimer Control.lnk"

[Registry]
Root: HKCU; Subkey: "Software\Classes\lontrium"; ValueType: string; ValueName: ""; ValueData: "URL:Lontrium Control"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\lontrium"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\lontrium\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """powershell.exe"" -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\Start-ClaimerControl.ps1"" -Action update"; Flags: uninsdeletekey
; Keep the former protocol as a compatibility alias for installed dashboards.
Root: HKCU; Subkey: "Software\Classes\claimer-control"; ValueType: string; ValueName: ""; ValueData: "URL:Lontrium Control"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\claimer-control"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\claimer-control\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """powershell.exe"" -NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\Start-ClaimerControl.ps1"" -Action update"; Flags: uninsdeletekey

[Run]
Filename: "{app}\Start-ClaimerControl.cmd"; Description: "{cm:StartAfterInstall}"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\Start-ClaimerControl.ps1"" -Action uninstall"; Flags: runhidden waituntilterminated; Check: KeepLocalData
Filename: "powershell.exe"; Parameters: "-NoLogo -NoProfile -ExecutionPolicy Bypass -File ""{app}\Start-ClaimerControl.ps1"" -Action uninstall -RemoveData"; Flags: runhidden waituntilterminated; Check: RemoveLocalData

[Code]
var
  DeleteLocalData: Boolean;

function LocalDataQuestion: String;
begin
  if ActiveLanguage = 'ptbr' then
    Result := 'Deseja apagar também as contas, sessões do navegador e histórico salvos localmente? O padrão seguro é Não.'
  else if ActiveLanguage = 'es' then
    Result := '¿También quieres eliminar las cuentas, sesiones del navegador y el historial guardados localmente? La opción segura predeterminada es No.'
  else
    Result := 'Also delete locally saved accounts, browser sessions and history? The safe default is No.';
end;

function InitializeUninstall(): Boolean;
begin
  DeleteLocalData := MsgBox(LocalDataQuestion, mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES;
  Result := True;
end;

function KeepLocalData(): Boolean;
begin
  Result := not DeleteLocalData;
end;

function RemoveLocalData(): Boolean;
begin
  Result := DeleteLocalData;
end;
