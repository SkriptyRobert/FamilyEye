; ============================================
; Parental Control SERVER - Inno Setup Script
; ============================================
; Kompletní instalátor pro rodičovský server
; S průvodcem nastavením během instalace
; ============================================

#define MyAppName "FamilyEye Server"
#define MyAppVersion "2.1.5"
#define MyAppPublisher "BertSoftware"
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
OutputBaseFilename=ParentalControlServer_Setup_{#MyAppVersion}
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
czech.WelcomeLabel1=Vítejte v instalaci Parental Control
czech.WelcomeLabel2=Tento průvodce vás provede instalací rodičovského kontrolního centra.%n%nZ tohoto počítače budete moci sledovat a řídit používání všech dětských zařízení.%n%nDoporučujeme zavřít ostatní aplikace před pokračováním.
czech.ServerPort=Port serveru:
czech.AdminEmail=Váš e-mail:
czech.AdminPassword=Heslo (min. 8 znaků):
czech.AdminPasswordConfirm=Zopakujte heslo:
czech.CreateAdmin=Vytvoření administrátorského účtu
czech.CreateAdminDesc=Tento účet použijete pro přihlášení do dashboardu
czech.ServerConfig=Nastavení serveru
czech.ServerConfigDesc=Konfigurace síťového přístupu
czech.InstallComplete=Instalace dokončena!
czech.InstallCompleteDesc=Server běží a je připraven k použití.
czech.OpenDashboard=Otevřít dashboard v prohlížeči
czech.StartService=Spustit server automaticky při startu Windows

[Types]
Name: "typical"; Description: "Typická instalace (doporučeno)"
Name: "custom"; Description: "Vlastní instalace"

[Components]
Name: "main"; Description: "FamilyEye Server"; Types: typical custom; Flags: fixed
Name: "dashboard"; Description: "Webový dashboard"; Types: typical custom; Flags: fixed
Name: "autostart"; Description: "Automatické spuštění při startu Windows"; Types: typical

[Files]
; Backend API
Source: "..\backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs; Excludes: "*.pyc,__pycache__,*.db,*.log,venv,.env"
; Frontend (pre-built)
Source: "..\frontend\dist\*"; DestDir: "{app}\frontend\dist"; Flags: ignoreversion recursesubdirs
; Python embedded
Source: "python-embed\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs
; Assets
Source: "assets\server_icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; Launcher
Source: "server_launcher.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Parental Control Dashboard"; Filename: "{app}\server_launcher.exe"; IconFilename: "{app}\server_icon.ico"; Parameters: "--open-browser"
Name: "{group}\Spravovat server"; Filename: "{app}\server_launcher.exe"; IconFilename: "{app}\server_icon.ico"; Parameters: "--admin"
Name: "{group}\Odinstalovat"; Filename: "{uninstallexe}"; IconFilename: "{app}\server_icon.ico"
Name: "{commondesktop}\Parental Control"; Filename: "{app}\server_launcher.exe"; IconFilename: "{app}\server_icon.ico"; Parameters: "--open-browser"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Vytvořit zástupce na ploše"; GroupDescription: "Zástupci:"
Name: "firewall"; Description: "Přidat výjimku do firewallu"; GroupDescription: "Síť:"; Flags: checkedonce

[Run]
; Firewall pravidlo
Filename: "netsh"; Parameters: "advfirewall firewall add rule name=""Parental Control Server"" dir=in action=allow protocol=TCP localport={code:GetServerPort}"; Flags: runhidden; Tasks: firewall
; Otevřít dashboard
Filename: "{app}\server_launcher.exe"; Parameters: "--open-browser"; Description: "Otevřít Parental Control Dashboard"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""Parental Control Server"""; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
var
  ConfigPage: TInputQueryWizardPage;
  AdminPage: TInputQueryWizardPage;
  ServerPort: String;
  AdminEmail: String;
  AdminPassword: String;
  
procedure InitializeWizard;
begin
  // Stránka pro nastavení serveru
  ConfigPage := CreateInputQueryPage(wpSelectTasks,
    ExpandConstant('{cm:ServerConfig}'),
    ExpandConstant('{cm:ServerConfigDesc}'),
    'Server bude dostupný na tomto portu z lokální sítě.' + #13#10 +
    'Výchozí port 8000 je doporučený, změňte pouze pokud je obsazený.');
  ConfigPage.Add(ExpandConstant('{cm:ServerPort}'), False);
  ConfigPage.Values[0] := '8000';
  
  // Stránka pro admin účet
  AdminPage := CreateInputQueryPage(ConfigPage.ID,
    ExpandConstant('{cm:CreateAdmin}'),
    ExpandConstant('{cm:CreateAdminDesc}'),
    'Tento účet použijete pro přihlášení do webového dashboardu.' + #13#10 +
    'E-mail musí být platný, heslo musí mít alespoň 8 znaků.');
  AdminPage.Add(ExpandConstant('{cm:AdminEmail}'), False);
  AdminPage.Add(ExpandConstant('{cm:AdminPassword}'), True);
  AdminPage.Add(ExpandConstant('{cm:AdminPasswordConfirm}'), True);
  AdminPage.Values[0] := '';
  AdminPage.Values[1] := '';
  AdminPage.Values[2] := '';
end;

function GetServerPort(Param: String): String;
begin
  Result := ConfigPage.Values[0];
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Port: Integer;
  Email: String;
begin
  Result := True;
  
  if CurPageID = ConfigPage.ID then
  begin
    // Validace portu
    Port := StrToIntDef(ConfigPage.Values[0], 0);
    if (Port < 1024) or (Port > 65535) then
    begin
      MsgBox('Port musí být číslo mezi 1024 a 65535.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    ServerPort := ConfigPage.Values[0];
  end;
  
  if CurPageID = AdminPage.ID then
  begin
    Email := AdminPage.Values[0];
    
    // Validace e-mailu
    if (Pos('@', Email) < 2) or (Pos('.', Email) < Pos('@', Email) + 2) then
    begin
      MsgBox('Zadejte platnou e-mailovou adresu.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Validace hesla
    if Length(AdminPage.Values[1]) < 8 then
    begin
      MsgBox('Heslo musí mít alespoň 8 znaků.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    // Potvrzení hesla
    if AdminPage.Values[1] <> AdminPage.Values[2] then
    begin
      MsgBox('Hesla se neshodují.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    AdminEmail := Email;
    AdminPassword := AdminPage.Values[1];
  end;
end;

procedure SaveConfiguration;
var
  ConfigFile: String;
  EnvFile: String;
begin
  // Uložit konfiguraci serveru
  ConfigFile := ExpandConstant('{app}\config.ini');
  SaveStringToFile(ConfigFile, 
    '[server]' + #13#10 +
    'port=' + ServerPort + #13#10 +
    'host=0.0.0.0' + #13#10 +
    '[admin]' + #13#10 +
    'email=' + AdminEmail + #13#10,
    False);
  
  // Vytvořit .env soubor pro backend
  EnvFile := ExpandConstant('{app}\backend\.env');
  SaveStringToFile(EnvFile,
    'PORT=' + ServerPort + #13#10 +
    'HOST=0.0.0.0' + #13#10 +
    'ADMIN_EMAIL=' + AdminEmail + #13#10 +
    'ADMIN_PASSWORD=' + AdminPassword + #13#10 +
    'DATABASE_URL=sqlite:///data/parental_control.db' + #13#10,
    False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  DataDir: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Vytvořit datový adresář
    DataDir := ExpandConstant('{app}\data');
    CreateDir(DataDir);
    
    // Uložit konfiguraci
    SaveConfiguration;
    
    // Inicializovat databázi a vytvořit admin účet
    // Spustí Python skript pro inicializaci
    Exec(ExpandConstant('{app}\python\python.exe'),
      ExpandConstant('"{app}\backend\init_admin.py" "' + AdminEmail + '" "' + AdminPassword + '"'),
      ExpandConstant('{app}'),
      SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Zastavit službu
    Exec('net', 'stop FamilyEyeServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('sc', 'delete FamilyEyeServer', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;
