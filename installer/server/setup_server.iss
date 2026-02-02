#define MyAppName "FamilyEye Server"
#define MyAppVersion "2.4.1"
#define MyAppPublisher "FamilyEye"
#define MyAppURL "https://github.com/SkriptyRobert/FamilyEye"

[Setup]
AppId={{B1C2D3E4-F5G6-7890-HIJK-LM1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/podpora
AppUpdatesURL={#MyAppURL}/aktualizace

DefaultDirName={commonpf}\FamilyEye\Server
DefaultGroupName=FamilyEye
DisableProgramGroupPage=yes

OutputDir=output
OutputBaseFilename=FamilyEyeServer_Setup_{#MyAppVersion}
SetupIconFile=assets\server_icon.ico
UninstallDisplayIcon={app}\server_icon.ico
UninstallDisplayName={#MyAppName}

Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

WizardStyle=modern
WizardSizePercent=120,100
WizardImageFile=assets\wizard_image.bmp
WizardSmallImageFile=assets\wizard_small.bmp

AllowNoIcons=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no
VersionInfoVersion={#MyAppVersion}

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
czech.WelcomeLabel1=Vítejte v instalaci systému FamilyEye Server
czech.WelcomeLabel2=Tento průvodce vás provede instalací centrálního rodičovského serveru.%n%nZ tohoto počítače budete moci sledovat aktivitu a spravovat pravidla pro všechna dětská zařízení v síti.%n%nPřed pokračováním doporučujeme ukončit ostatní běžící aplikace.
czech.ServerPort=Port serveru:
czech.AdminEmail=Váš e-mail:
czech.AdminPassword=Heslo (min. 8 znaků):
czech.AdminPasswordConfirm=Potvrzení hesla:
czech.CreateAdmin=Vytvoření administrátorského účtu
czech.CreateAdminDesc=Tento účet bude sloužit pro přihlášení k ovládacímu panelu
czech.ServerConfig=Nastavení serveru
czech.ServerConfigDesc=Konfigurace síťového přístupu
czech.InstallComplete=Instalace byla dokončena!
czech.InstallCompleteDesc=Server FamilyEye je spuštěn a připraven k použití.
czech.OpenDashboard=Otevřít ovládací panel v prohlížeči
czech.StartService=Spouštět server automaticky při startu systému

[Types]
Name: "typical"; Description: "Typická instalace (doporučeno)"
Name: "custom"; Description: "Vlastní instalace"

[Components]
Name: "main"; Description: "FamilyEye Server"; Types: typical custom; Flags: fixed
Name: "dashboard"; Description: "Webový dashboard"; Types: typical custom; Flags: fixed
Name: "autostart"; Description: "Automatické spuštění při startu Windows"; Types: typical

[Files]
; Main Executable and dependencies from PyInstaller
Source: "..\..\dist\FamilyEyeServer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
; Assets (Icon) - Optional if embedded, but good for shortcuts
Source: "assets\server_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Dirs]
; Create ProgramData structure with Modify permissions for Users (so Admin/System can write, verify this logic)
Name: "{commonappdata}\FamilyEye"; Permissions: admins-full
Name: "{commonappdata}\FamilyEye\Server"; Permissions: admins-full
Name: "{commonappdata}\FamilyEye\Server\logs"; Permissions: admins-full
Name: "{commonappdata}\FamilyEye\Server\uploads"; Permissions: admins-full
Name: "{commonappdata}\FamilyEye\Server\certs"; Permissions: admins-full

[Tasks]
Name: "desktopicon"; Description: "Vytvořit zástupce na ploše"; GroupDescription: "Zástupci:"
Name: "firewall"; Description: "Přidat výjimku do firewallu"; GroupDescription: "Síť:"; Flags: checkedonce

[Icons]
Name: "{group}\Parental Control Dashboard"; Filename: "{app}\FamilyEyeServer.exe"; Parameters: "--launch-browser-only"; IconFilename: "{app}\server_icon.ico"
Name: "{group}\Spravovat Service"; Filename: "{app}\FamilyEyeServer.exe"; IconFilename: "{app}\server_icon.ico"; Parameters: "--help"
Name: "{group}\Odinstalovat"; Filename: "{uninstallexe}"; IconFilename: "{app}\server_icon.ico"
Name: "{commondesktop}\Parental Control"; Filename: "{app}\FamilyEyeServer.exe"; Parameters: "--launch-browser-only"; IconFilename: "{app}\server_icon.ico"; Tasks: desktopicon

[Run]
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""Parental Control Server"" dir=in action=allow protocol=TCP localport={code:GetServerPort}"; Flags: runhidden; Tasks: firewall
Filename: "{app}\FamilyEyeServer.exe"; Parameters: "--launch-browser-only"; Description: "Otevřít Parental Control Dashboard"; Flags: nowait postinstall skipifsilent runasoriginaluser

[UninstallRun]
Filename: "net"; Parameters: "stop FamilyEyeServer"; Flags: runhidden waituntilterminated
Filename: "{app}\FamilyEyeServer.exe"; Parameters: "remove"; Flags: runhidden waituntilterminated
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""Parental Control Server"""; Flags: runhidden
Filename: "certutil"; Parameters: "-delstore ""Root"" ""FamilyEye Root CA"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{commonappdata}\FamilyEye\Server"
Type: dirifempty; Name: "{commonappdata}\FamilyEye"

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  ServerPort: String;
  
procedure InitializeWizard;
begin
  // Stránka pro nastavení serveru (port)
  ConfigPage := CreateInputQueryPage(wpWelcome,
    ExpandConstant('{cm:ServerConfig}'),
    ExpandConstant('{cm:ServerConfigDesc}'),
    'Server se nainstaluje jako Windows služba a bude dostupný na zadaném portu v rámci lokální sítě.' + #13#10 +
    'Výchozí port 8443 je doporučený (HTTPS).');
  ConfigPage.Add(ExpandConstant('{cm:ServerPort}'), False);
  ConfigPage.Values[0] := '8443';
end;

function GetServerPort(Param: String): String;
begin
  Result := ConfigPage.Values[0];
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Port: Integer;
begin
  Result := True;
  
  if CurPageID = ConfigPage.ID then
  begin
    // Validace portu
    Port := StrToIntDef(ConfigPage.Values[0], 0);
    if (Port < 1024) or (Port > 65535) then
    begin
      MsgBox('Port musí být celé číslo v rozmezí 1024 až 65535.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    ServerPort := ConfigPage.Values[0];
  end;
end;

procedure SaveConfiguration;
var
  EnvFile: String;
begin
  // Vytvořit .env soubor pro backend v kořenovém adresáři aplikace
  EnvFile := ExpandConstant('{app}\.env');
  // UKLADAME JEN PORT. Secret Key si backend vygeneruje sam, Admina si vytvori uzivatel v browseru.
  SaveStringToFile(EnvFile,
    'BACKEND_PORT=' + ServerPort + #13#10 +
    'BACKEND_HOST=0.0.0.0' + #13#10,
    False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  CertPath: String;
begin
  if CurStep = ssPostInstall then
  begin
    SaveConfiguration;

    // Generate per-install certificates, then add CA to Root store
    Exec(ExpandConstant('{app}\FamilyEyeServer.exe'),
      '--ensure-certs',
      ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode);

    CertPath := ExpandConstant('{commonappdata}\FamilyEye\Server\certs\familyeye-ca.crt');
    Exec('certutil',
      '-addstore -f "Root" "' + CertPath + '"',
      '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode);

    Exec(ExpandConstant('{app}\FamilyEyeServer.exe'),
      '--startup auto install',
      ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode);

    Exec('sc',
      'failure FamilyEyeServer reset= 86400 actions= restart/60000/restart/60000/restart/60000',
      '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode);

    Sleep(2000);

    Exec('net',
      'start FamilyEyeServer',
      '',
      SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
