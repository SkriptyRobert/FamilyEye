#define MyAppVersion "2.4.0"
; Version above is overwritten by scripts/bump_version.py from root VERSION file.

[Setup]
AppName=FamilyEye Agent
AppVersion={#MyAppVersion}
AppVerName=FamilyEye Agent {#MyAppVersion}
AppPublisher=FamilyEye
AppPublisherURL=https://github.com/SkriptyRobert/FamilyEye
AppSupportURL=https://github.com/SkriptyRobert/FamilyEye/issues
AppUpdatesURL=https://github.com/SkriptyRobert/FamilyEye/releases

DefaultDirName={commonpf}\FamilyEye\Agent
DefaultGroupName=FamilyEye Agent
DisableProgramGroupPage=yes

OutputDir=output
OutputBaseFilename=FamilyEyeAgent_Setup_{#MyAppVersion}
UninstallDisplayName=FamilyEye Agent

Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

WizardStyle=modern
WizardSizePercent=130,110
WizardImageFile=assets\wizard_side.bmp
WizardSmallImageFile=assets\wizard_top.bmp
SetupIconFile=assets\setup_icon.ico

AllowNoIcons=yes
CloseApplications=yes
RestartApplications=no
ShowLanguageDialog=no
VersionInfoVersion={#MyAppVersion}.0

CreateUninstallRegKey=yes
Uninstallable=yes

[Dirs]
; -------------------------------------------------------------------------
; SECURITY HARDENING: NTFS PERMISSIONS (ACLs)
; -------------------------------------------------------------------------
; 1. Agent Root (Configs, Cache, Executables)
;    SECURITY: Users have Read & Execute ONLY. Administrators/SYSTEM have Full Control.
;    GOAL: Prevent child from modifying config.json or deleting rules.
Name: "{commonappdata}\FamilyEye\Agent"; Permissions: users-readexec admins-full system-full

; 2. Logs Directory
;    SECURITY: Users need WRITE access because FamilyEyeAgent.exe runs as the user
;    and needs to write UI logs errors here.
;    GOAL: Allow logging but keep configs secure in parent folder.
Name: "{commonappdata}\FamilyEye\Agent\Logs"; Permissions: users-modify admins-full system-full

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
; -------------------------------------------------------------------------
; BRANDING & LOCALIZATION
; Professional tone, diacritics, clear instructions.
; -------------------------------------------------------------------------
czech.WelcomeLabel1=Vítejte v instalaci FamilyEye
czech.WelcomeLabel2=Tento průvodce nainstaluje aplikaci FamilyEye Agent na tento počítač.%n%nFamilyEye pomáhá rodičům chránit digitální bezpečí jejich dětí.%n%nBěhem instalace provedeme:%n• Instalaci ochranného agenta%n• Spárování s vaším rodičovským účtem%n• Zabezpečení systému proti neoprávněné manipulaci%n%nPro pokračování klikněte na Další.
czech.ServerURL=Adresa serveru:
czech.PairingToken=Párovací kód (Token):
czech.DeviceName=Název tohoto zařízení:
czech.ServerConfig=Připojení k rodičovskému serveru
czech.ServerConfigDesc=Zadejte adresu vašeho FamilyEye serveru
czech.PairingConfig=Registrace zařízení
czech.PairingConfigDesc=Zadejte jednorázový párovací kód
czech.TestConnection=Ověřit dostupnost
czech.ConnectionOK=✓ Server je dostupný
czech.ConnectionFailed=✗ Nepodařilo se připojit k serveru
czech.PairingOK=✓ Párování úspěšné!
czech.PairingFailed=✗ Chyba párování
czech.ChildAccountSetup=Nastavení uživatelských účtů
czech.ChildAccountSetupDesc=Zvolte, který účet bude dítě používat
czech.CreateChildAccount=Vytvořit nový dětský účet (Doporučeno)
czech.ChildUsername=Jméno dětského účtu:
czech.ChildPassword=Heslo (volitelné):
czech.ChildPasswordConfirm=Potvrzení hesla:
czech.SecuritySetup=Aktivní ochrana
czech.SecuritySetupDesc=Konfigurace bezpečnostních politik systému
czech.ConfigureFirewall=Aktivovat FamilyEye Firewall (blokování neznámé komunikace)
czech.BlockTaskManager=Chránit proces agenta (Skrýt ve Správci úloh)
czech.BlockControlPanel=Omezit přístup k nastavení systému (Ovládací panely)
czech.BlockRegistry=Blokovat úpravy registrů (RegEdit)

[Files]
; Main Service Executable
Source: "dist\agent_service.exe"; DestDir: "{app}"; Flags: ignoreversion

; UI Agent (Child Interaction)
Source: "dist\FamilyEyeAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

; Assets & Icons
Source: "assets\setup_icon.ico"; DestDir: "{app}\assets"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\..\clients\windows\agent\familyeye_icon.png"; DestDir: "{app}\agent"; Flags: ignoreversion skipifsourcedoesntexist

; Dynamic Config (Generated during setup)
Source: "{tmp}\config.json"; DestDir: "{commonappdata}\FamilyEye\Agent"; Flags: external ignoreversion skipifsourcedoesntexist

[Registry]
; Auto-start UI Agent for all users (HKLM Run)
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FamilyEyeAgent"; ValueData: """{app}\FamilyEyeAgent.exe"""; Flags: uninsdeletevalue

; Security Flags Registry Key
Root: HKLM; Subkey: "SOFTWARE\FamilyEyeAgent"; ValueType: string; ValueName: "InstallDate"; ValueData: "{code:GetInstallDate}"; Flags: uninsdeletekey


[UninstallDelete]
; Cleanup all data upon explicit uninstall
Type: filesandordirs; Name: "{commonappdata}\FamilyEye"
Type: filesandordirs; Name: "{app}"

[Run]
; Service Registration & Start
Filename: "sc"; Parameters: "create FamilyEyeAgent binPath= ""{app}\agent_service.exe"" start= auto DisplayName= ""FamilyEye Agent"""; Flags: runhidden
Filename: "sc"; Parameters: "description FamilyEyeAgent ""Monitorování a ochrana FamilyEye"""; Flags: runhidden
; Configure recovery options (restart service on fail)
Filename: "sc"; Parameters: "failure FamilyEyeAgent reset= 60 actions= restart/5000"; Flags: runhidden
Filename: "net"; Parameters: "start FamilyEyeAgent"; Flags: runhidden

[UninstallRun]
; Stop Service
Filename: "net"; Parameters: "stop FamilyEyeAgent"; Flags: runhidden waituntilterminated
Filename: "sc"; Parameters: "delete FamilyEyeAgent"; Flags: runhidden waituntilterminated

; Kill Processes
Filename: "taskkill"; Parameters: "/F /IM agent_service.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM FamilyEyeAgent.exe"; Flags: runhidden

; Cleanup Firewall
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEyeAgent_Allow"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_BlockAll"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound"; Flags: runhidden waituntilterminated

; Cleanup HOSTS (PowerShell)
Filename: "powershell"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$h='C:\Windows\System32\drivers\etc\hosts'; if(Test-Path $h){{$c=Get-Content $h | Where-Object {{$_ -notmatch '\[PC-BLOCK\]'}}; Set-Content $h $c -Force}}"""; Flags: runhidden waituntilterminated

[Code]
// -------------------------------------------------------------------------
// PASCAL SCRIPT LOGIC
// -------------------------------------------------------------------------
var
  ServerPage: TInputQueryWizardPage;
  PairingPage: TInputQueryWizardPage;
  ChildAccountPage: TInputQueryWizardPage;
  ParentAccountPage: TInputQueryWizardPage;
  SecurityPage: TInputOptionWizardPage;
  StatusLabel: TNewStaticText;
  TestButton: TNewButton;
  
  // Variables to store user input
  ServerURL: String;
  PairingToken: String;
  DeviceName: String;
  PairingSuccess: Boolean;
  NeedParentAccount: Boolean;

// Helper: Get Current Date for Registry
function GetInstallDate(Param: String): String;
begin
  Result := GetDateTimeString('dd.mm.yyyy', '.', ':');
end;

// Helper: Get Computer Name
function GetPCName: String;
begin
  Result := GetEnv('COMPUTERNAME');
  if Result = '' then Result := 'Počítač';
end;

// Helper: Check if user exists
function UserExists(Username: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  // quiet execution hidden
  if Exec('net', 'user "' + Username + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := (ResultCode = 0);
  end;
end;

// Count how many admin accounts exist on the system
function CountAdminAccounts: Integer;
var
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
  i: Integer;
begin
  Result := 0;
  TempFile := ExpandConstant('{tmp}\admins.txt');
  
  // Run net localgroup and save output
  if Exec('cmd', '/c net localgroup Administrators > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if LoadStringsFromFile(TempFile, Lines) then
    begin
      // Count lines that look like usernames (skip headers)
      for i := 0 to GetArrayLength(Lines) - 1 do
      begin
        // Skip empty lines and header lines
        if (Length(Lines[i]) > 0) and (Pos('---', Lines[i]) = 0) and 
           (Pos('Alias', Lines[i]) = 0) and (Pos('Members', Lines[i]) = 0) and
           (Pos('command', Lines[i]) = 0) then
        begin
          if Trim(Lines[i]) <> '' then
             Result := Result + 1;
        end;
      end;
    end;
  end;
  
  // Cleanup
  DeleteFile(TempFile);
end;

// Helper: Check if user is Admin
function IsUserAdmin(Username: String): Boolean;
var
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
  i: Integer;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\admincheck.txt');
  
  if Exec('cmd', '/c net localgroup Administrators > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if LoadStringsFromFile(TempFile, Lines) then
    begin
      for i := 0 to GetArrayLength(Lines) - 1 do
      begin
        if Pos(Username, Lines[i]) > 0 then
        begin
          Result := True;
          Break;
        end;
      end;
    end;
  end;
  DeleteFile(TempFile);
end;

// API: Test Connection Button Click
procedure TestConnectionClick(Sender: TObject);
var
  WinHttpReq: Variant;
  URL: String;
begin
  StatusLabel.Caption := 'Testuji spojení...';
  StatusLabel.Font.Color := clGray;
  WizardForm.Refresh;
  
  URL := ServerPage.Values[0] + '/api/health';
  
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('GET', URL, False);
    WinHttpReq.SetTimeouts(2000, 2000, 2000, 2000);
    try WinHttpReq.Option[4] := 13056; except end; // Ignore SSL errors
    WinHttpReq.Send('');
    
    if WinHttpReq.Status = 200 then
    begin
      StatusLabel.Caption := ExpandConstant('{cm:ConnectionOK}');
      StatusLabel.Font.Color := clGreen;
    end
    else
    begin
      StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}') + ' (' + IntToStr(WinHttpReq.Status) + ')';
      StatusLabel.Font.Color := clRed;
    end;
  except
    StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}');
    StatusLabel.Font.Color := clRed;
  end;
end;

// API: Perform Pairing Logic
function DoPairing: Boolean;
var
  WinHttpReq: Variant;
  URL: String;
  PostData: String;
  Response: String;
  TempS: String;
  RandomPart: String;
  i, p1, p2: Integer;
  ApiKey, DeviceID: String;
  ConfigFile: String;
begin
  Result := False;
  
  // Generate random suffix for ID
  RandomPart := '';
  for i := 1 to 6 do RandomPart := RandomPart + Chr(Ord('a') + Random(26));
  DeviceID := 'win-' + GetPCName + '-' + RandomPart;
  
  URL := ServerURL + '/api/devices/pairing/pair';
  PostData := '{"token":"' + PairingToken + '","device_name":"' + DeviceName + '","device_type":"windows","mac_address":"auto","device_id":"' + DeviceID + '"}';
  
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('POST', URL, False);
    WinHttpReq.SetRequestHeader('Content-Type', 'application/json');
    WinHttpReq.SetTimeouts(5000, 5000, 5000, 5000);
    try WinHttpReq.Option[4] := 13056; except end; ; Ignore SSL
    
    WinHttpReq.Send(PostData);
    
    if WinHttpReq.Status = 200 then
    begin
      Response := WinHttpReq.ResponseText;
      
      // Basic JSON parsing (manual string manipulation to avoid dependencies)
      // Extract apiKey
      p1 := Pos('"api_key":', Response);
      if p1 > 0 then
      begin
        TempS := Copy(Response, p1 + 10, Length(Response));
        p1 := Pos('"', TempS);
        if p1 > 0 then
        begin
          TempS := Copy(TempS, p1 + 1, Length(TempS));
          p2 := Pos('"', TempS);
          if p2 > 0 then ApiKey := Copy(TempS, 1, p2 - 1);
        end;
      end;
      
      // Extract deviceID (if server assigned different one)
      p1 := Pos('"device_id":', Response);
      if p1 > 0 then
      begin
        TempS := Copy(Response, p1 + 12, Length(Response));
        p1 := Pos('"', TempS);
        if p1 > 0 then
        begin
            TempS := Copy(TempS, p1 + 1, Length(TempS));
            p2 := Pos('"', TempS);
            if p2 > 0 then DeviceID := Copy(TempS, 1, p2 - 1);
        end;
      end;
      
      if ApiKey = '' then
      begin
         MsgBox('Chyba: Server nevrátil API klíč.', mbError, MB_OK);
         Exit;
      end;
      
      // Save Config
      ConfigFile := ExpandConstant('{tmp}\config.json');
      SaveStringToFile(ConfigFile,
        '{' + #13#10 +
        '  "backend_url": "' + ServerURL + '",' + #13#10 +
        '  "device_id": "' + DeviceID + '",' + #13#10 +
        '  "api_key": "' + ApiKey + '",' + #13#10 +
        '  "polling_interval": 30,' + #13#10 +
        '  "reporting_interval": 60,' + #13#10 +
        '  "ssl_verify": false' + #13#10 +
        '}', False);
      
      // ACLs will be applied by [Dirs] section later during install
      Result := True;
    end
    else
    begin
       MsgBox('Chyba párování. Server odpověděl kódem: ' + IntToStr(WinHttpReq.Status), mbError, MB_OK);
    end;
    
  except
    MsgBox('Chyba komunikace se serverem.', mbError, MB_OK);
  end;
end;

// UNINSTALL LOGIC: Remove registry restrictions
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    // Remove policies from .DEFAULT (login screen) and currently logged in users
    // Note: This is a best-effort cleanup. 
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableTaskMgr');
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer', 'NoControlPanel');
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableRegistryTools');
  end;
end;

function InitializeSetup: Boolean;
var
    ResultCode: Integer;
begin
    // Pre-clean previous installs
    Exec('net', 'stop FamilyEyeAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('taskkill', '/F /IM agent_service.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Result := True;
end;

procedure InitializeWizard;
begin
  NeedParentAccount := False;

  // Page 1: Server Config
  ServerPage := CreateInputQueryPage(wpSelectDir,
    ExpandConstant('{cm:ServerConfig}'),
    ExpandConstant('{cm:ServerConfigDesc}'),
    'Zadejte adresu vašeho FamilyEye serveru (např. https://192.168.1.10:8000)');
  ServerPage.Add(ExpandConstant('{cm:ServerURL}'), False);
  ServerPage.Values[0] := 'https://';
  
  TestButton := TNewButton.Create(WizardForm);
  TestButton.Parent := ServerPage.Surface;
  TestButton.Left := 0; TestButton.Top := 160; TestButton.Width := 150; TestButton.Height := 25;
  TestButton.Caption := ExpandConstant('{cm:TestConnection}');
  TestButton.OnClick := @TestConnectionClick;
  
  StatusLabel := TNewStaticText.Create(WizardForm);
  StatusLabel.Parent := ServerPage.Surface;
  StatusLabel.Left := 160; StatusLabel.Top := 165;
  StatusLabel.Font.Style := [fsBold];

  // Page 2: Pairing
  PairingPage := CreateInputQueryPage(ServerPage.ID,
    ExpandConstant('{cm:PairingConfig}'),
    ExpandConstant('{cm:PairingConfigDesc}'),
    'Kód naleznete v rodičovském panelu pod tlačítkem "Přidat zařízení".');
  PairingPage.Add(ExpandConstant('{cm:PairingToken}'), False);
  PairingPage.Add(ExpandConstant('{cm:DeviceName}'), False);
  PairingPage.Values[1] := GetPCName;

  // Page 3: Child Account (Simplified)
  ChildAccountPage := CreateInputQueryPage(PairingPage.ID,
    ExpandConstant('{cm:ChildAccountSetup}'),
    ExpandConstant('{cm:ChildAccountSetupDesc}'),
    'Pokud účet neexistuje, vytvoříme ho. Pokud existuje, nastavíme ho.');
  ChildAccountPage.Add(ExpandConstant('{cm:ChildUsername}'), False);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPassword}'), True);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPasswordConfirm}'), True);
  ChildAccountPage.Values[0] := 'Dite';

  // Page 4: Parent Account (Conditional)
  ParentAccountPage := CreateInputQueryPage(ChildAccountPage.ID,
    'Záložní administrátorský účet',
    'Vytvořte účet pro správu počítače',
    'POZOR: Dětský účet bude zbaven administrátorských práv.' + #13#10 +
    'Aby nebyl počítač bez správce, musíme vytvořit záložní admin účet.' + #13#10#13#10 +
    'Toto bude jediný účet s plnými právy.');
  ParentAccountPage.Add('Uživatelské jméno rodiče:', False);
  ParentAccountPage.Add('Heslo:', True);
  ParentAccountPage.Add('Potvrzení hesla:', True);
  ParentAccountPage.Values[0] := 'Rodic';

  // Page 5: Security
  SecurityPage := CreateInputOptionPage(ParentAccountPage.ID,
    ExpandConstant('{cm:SecuritySetup}'),
    ExpandConstant('{cm:SecuritySetupDesc}'),
    'Vyberte bezpečnostní opatření:', False, False);
  SecurityPage.Add(ExpandConstant('{cm:ConfigureFirewall}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockTaskManager}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockControlPanel}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockRegistry}'));
  SecurityPage.Values[0] := True;
  SecurityPage.Values[1] := True;
  SecurityPage.Values[2] := True;
  SecurityPage.Values[3] := True;
  
  PairingSuccess := False;
end;

// SKIP LOGIC: Decide if Parent Account Page should be shown
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  if PageID = ParentAccountPage.ID then
  begin
     Result := not NeedParentAccount;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ChildUser, ChildPass, ChildPass2: String;
  ParentUser, ParentPass, ParentPass2: String;
  ResultCode: Integer;
  NumAdmins: Integer;
begin
  Result := True;
  
  // Validate Server
  if CurPageID = ServerPage.ID then
  begin
    ServerURL := ServerPage.Values[0];
    if Length(ServerURL) < 8 then
    begin
        MsgBox('Zadejte platnou URL serveru.', mbError, MB_OK);
        Result := False;
    end;
  end;
  
  // Perform Pairing
  if CurPageID = PairingPage.ID then
  begin
    PairingToken := PairingPage.Values[0];
    DeviceName := PairingPage.Values[1];
    if (Length(PairingToken) < 5) then
    begin
        MsgBox('Zadejte platný párovací token.', mbError, MB_OK);
        ResultCode := 0; // dummy
        Result := False;
        Exit;
    end;
    
    WizardForm.NextButton.Enabled := False;
    if DoPairing then 
    begin
        PairingSuccess := True;
    end
    else
    begin
        Result := False;
    end;
    WizardForm.NextButton.Enabled := True;
  end;
  
  // Handle Child Account
  if CurPageID = ChildAccountPage.ID then
  begin
    ChildUser := ChildAccountPage.Values[0];
    ChildPass := ChildAccountPage.Values[1];
    ChildPass2 := ChildAccountPage.Values[2];
    
    NeedParentAccount := False;

    if ChildUser <> '' then
    begin
        // If account exists, we check if it's admin
        if UserExists(ChildUser) then
        begin
             if IsUserAdmin(ChildUser) then
             begin
                  NumAdmins := CountAdminAccounts;
                  // Look for complex scenario: Child is Admin.
                  // If there is ONLY 1 admin (the child), OR user wants to be safe, we must force Parent ID.
                  
                  if MsgBox('Účet "' + ChildUser + '" je ADMINISTRÁTOR.' + #13#10 + 
                            'Pro bezpečnost odebereme tomuto účtu admin práva.' + #13#10#13#10 + 
                            'Přejete si vytvořit nový rodičovský admin účet?' + #13#10 + 
                            '(Pokud neexistuje jiný admin, je to NUTNÉ)', mbConfirmation, MB_YESNO) = IDYES then
                  begin
                       NeedParentAccount := True;
                  end
                  else
                  begin
                       if NumAdmins <= 1 then
                       begin
                           MsgBox('CHYBA: V systému je pouze jeden admin (' + ChildUser + ').' + #13#10 + 
                                  'Musíme vytvořit rodičovský účet, jinak se uzamknete!', mbError, MB_OK);
                           Result := False;
                           Exit;
                       end;
                  end;
             end;
        end
        else
        begin
            // New user Logic
            if ChildPass <> ChildPass2 then
            begin
                MsgBox('Hesla se neshodují.', mbError, MB_OK);
                Result := False;
                Exit;
            end;
            // Create User immediately so we can register him
            if Exec('net', 'user "' + ChildUser + '" "' + ChildPass + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
               Exec('net', 'localgroup Users "' + ChildUser + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        end;
        
        // Save targeted child username to registry for agent usage if needed
        RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\FamilyEyeAgent', 'MonitoredAccount', ChildUser);
    end;
  end;

  // Handle Parent Account Creation
  if CurPageID = ParentAccountPage.ID then
  begin
      if NeedParentAccount then
      begin
          ParentUser := ParentAccountPage.Values[0];
          ParentPass := ParentAccountPage.Values[1];
          ParentPass2 := ParentAccountPage.Values[2];

          if (ParentPass = '') or (ParentPass <> ParentPass2) then
          begin
               MsgBox('Zadejte a potvrďte heslo pro rodiče.', mbError, MB_OK);
               Result := False;
               Exit;
          end;

          if Exec('net', 'user "' + ParentUser + '" "' + ParentPass + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
          begin
              Exec('net', 'localgroup Administrators "' + ParentUser + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
              
              // DEGRADE CHILD
              ChildUser := ChildAccountPage.Values[0];
              Exec('net', 'localgroup Administrators "' + ChildUser + '" /delete', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
              
              MsgBox('Rodičovský účet vytvořen. Dětský účet byl omezen na standardního uživatele.', mbInformation, MB_OK);
          end
          else
          begin
             MsgBox('Nepodařilo se vytvořit rodičovský účet. Zkontrolujte heslo (složitost).', mbError, MB_OK);
             Result := False;
          end;
      end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
    ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
     // Disable Task Manager
     if SecurityPage.Values[1] then
         RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableTaskMgr', 1);
         
     // Disable Control Panel
     if SecurityPage.Values[2] then
         RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer', 'NoControlPanel', 1);
         
     // Disable RegEdit
     if SecurityPage.Values[3] then
         RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableRegistryTools', 1);

     // Configure Firewall
     if SecurityPage.Values[0] then
     begin
         // Allow Agent Outbound
         Exec('netsh', 'advfirewall firewall add rule name="FamilyEyeAgent_Allow" dir=out action=allow program="' + ExpandConstant('{app}') + '\agent_service.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
     end;
  end;
end;
