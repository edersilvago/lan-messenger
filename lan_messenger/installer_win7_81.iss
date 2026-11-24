; Instalador LAN Messenger - Windows 7 SP1 / 8 / 8.1 (build Python 3.8):
;   C:\tools\inno\ISCC.exe lan_messenger\installer_win7_81.iss
; Saída: installer\Setup_LANMessenger_win7_81.exe
#define MyAppName "LAN Messenger"
#define MyAppVersion "1.39"
#define MyAppExe "LANMessenger.exe"

[Setup]
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\LANMessenger
DefaultGroupName={#MyAppName}
OutputDir=..\installer
OutputBaseFilename=Setup_LANMessenger_win7_81_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64os
MinVersion=6.1sp1
WizardStyle=modern
; Atualização: fecha cópias abertas antes de trocar o exe.
CloseApplications=yes
RestartApplications=no
SetupIconFile=assets\app.ico
UninstallDisplayIcon={app}\{#MyAppExe}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na área de trabalho"; Flags: unchecked

[Files]
Source: "..\\dist-win7\\{#MyAppExe}"; DestDir: "{app}"; DestName: "{#MyAppExe}"; Flags: ignoreversion
Source: "assets\\app.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "assets\\*.png"; DestDir: "{app}\\assets"; Flags: ignoreversion
Source: "assets\\sounds\\*.wav"; DestDir: "{app}\\assets\\sounds"; Flags: ignoreversion
Source: "LEIA-ME-TESTE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExe}"; Tasks: desktopicon

[Run]
; Idempotente: apaga regras antigas (inclusive de versões anteriores) antes.
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg UDP Discovery"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg TCP Chat"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg TCP Files"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""LANMsg UDP Discovery"" dir=in action=allow protocol=UDP localport=50000"; \
  Flags: runhidden; StatusMsg: "Liberando discovery (UDP 50000)..."
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""LANMsg TCP Chat"" dir=in action=allow protocol=TCP localport=50001"; \
  Flags: runhidden; StatusMsg: "Liberando chat (TCP 50001)..."
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""LANMsg TCP Files"" dir=in action=allow protocol=TCP localport=50002"; \
  Flags: runhidden; StatusMsg: "Liberando arquivos (TCP 50002)..."
Filename: "{app}\{#MyAppExe}"; Description: "Iniciar o {#MyAppName} agora"; \
  Flags: postinstall nowait skipifsilent runasoriginaluser

[UninstallRun]
; Fecha o app se estiver aberto durante a desinstalação.
Filename: "taskkill"; Parameters: "/F /IM {#MyAppExe}"; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg UDP Discovery"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg TCP Chat"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""LANMsg TCP Files"""; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\assets\sounds\*.wav"
Type: dirifempty; Name: "{app}\assets\sounds"
Type: files; Name: "{app}\assets\*.png"
Type: dirifempty; Name: "{app}\assets"
Type: dirifempty; Name: "{app}"

[Code]
{ Fecha cópias em execução antes de copiar arquivos (atualização sem erro). }
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Exec(ExpandConstant('{sys}\taskkill.exe'),
       '/F /IM {#MyAppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(1500);
  Result := '';
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    { O desinstalador roda dentro da pasta do app; remove a pasta vazia depois. }
    Exec(ExpandConstant('{cmd}'),
         '/C ping 127.0.0.1 -n 3 > nul & rmdir /S /Q "' + ExpandConstant('{app}') + '"',
         ExpandConstant('{tmp}'), SW_HIDE, ewNoWait, ResultCode);
  end;
end;
