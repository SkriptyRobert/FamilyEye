[Setup]
AppName=FamilyEye Agent
AppVersion=2.1.4
AppVerName=FamilyEye Agent 2.1.4
AppPublisher=FamilyEye s.r.o.
AppPublisherURL=https://familyeye.cz
AppSupportURL=https://familyeye.cz/podpora
AppUpdatesURL=https://familyeye.cz/aktualizace

DefaultDirName={commonpf}\FamilyEye\Agent
DefaultGroupName=FamilyEye Agent
DisableProgramGroupPage=yes

OutputDir=output
OutputBaseFilename=FamilyEyeAgent_Setup_2.1.4
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
VersionInfoVersion=2.0.0

CreateUninstallRegKey=yes
Uninstallable=yes
[Dirs]
; Create ProgramData data directories with specific permissions
; 1. Agent root: Configs and Caches. 
;    SECURITY: Users have Read & Execute only. Admins/System have Full.
;    Prevents child from modifying config.json or rules_cache.json
Name: "{commonappdata}\FamilyEye\Agent"; Permissions: users-readexec admins-full system-full

; 2. Logs directory: ChildAgent needs to write here.
;    SECURITY: Users have Modify permissions.
Name: "{commonappdata}\FamilyEye\Agent\Logs"; Permissions: users-modify admins-full system-full

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
czech.WelcomeLabel1=Instalace FamilyEye
czech.WelcomeLabel2=Tento průvodce nainstaluje agenta FamilyEye a pomůže vám nastavit bezpečný dětský účet.%n%nCo průvodce udělá:%n• Nainstaluje agenta FamilyEye%n• Spáruje počítač s rodičovským dashboardem%n• Vytvoří dětský účet bez administrátorských práv%n• Nastaví firewall pro ochranu
czech.ServerURL=Adresa serveru:
czech.PairingToken=Párovací token:
czech.DeviceName=Název tohoto zařízení:
czech.ServerConfig=Připojení k serveru
czech.ServerConfigDesc=Zadejte adresu rodičovského serveru
czech.PairingConfig=Párování zařízení
czech.PairingConfigDesc=Zadejte párovací token z rodičovského dashboardu
czech.TestConnection=Testovat připojení
czech.ConnectionOK=✓ Připojení OK
czech.ConnectionFailed=✗ Server nedostupný
czech.PairingOK=✓ Párování úspěšné!
czech.PairingFailed=✗ Párování selhalo
czech.ChildAccountSetup=Nastavení dětského účtu
czech.ChildAccountSetupDesc=Vytvořte bezpečný účet pro dítě bez administrátorských práv
czech.CreateChildAccount=Vytvořit dětský účet (doporučeno)
czech.ChildUsername=Uživatelské jméno:
czech.ChildPassword=Heslo pro dítě:
czech.ChildPasswordConfirm=Potvrzení hesla:
czech.SecuritySetup=Zabezpečení systému
czech.SecuritySetupDesc=Nastavení firewallu a ochranných pravidel
czech.ConfigureFirewall=Nastavit firewall pravidla
czech.BlockTaskManager=Zakázat Správce úloh pro dětský účet
czech.BlockControlPanel=Omezit přístup k Ovládacím panelům
czech.BlockRegistry=Zakázat přístup k registrům

[Files]
; Main Executable (Service)
Source: "dist\agent_service.exe"; DestDir: "{app}"; Flags: ignoreversion

; UI Agent (Child)
Source: "dist\FamilyEyeAgent.exe"; DestDir: "{app}"; Flags: ignoreversion

; Icon
Source: "..\..\clients\windows\agent\familyeye_icon.png"; DestDir: "{app}\agent"; Flags: ignoreversion skipifsourcedoesntexist

; Generated config file from pairing step
Source: "{tmp}\config.json"; DestDir: "{commonappdata}\FamilyEye\Agent"; Flags: external ignoreversion skipifsourcedoesntexist

[UninstallDelete]
; Clean up ProgramData files and folders
Type: files; Name: "{commonappdata}\FamilyEye\Agent\Logs\service_core.log"
Type: files; Name: "{commonappdata}\FamilyEye\Agent\Logs\ui_agent.log"
Type: files; Name: "{commonappdata}\FamilyEye\Agent\Logs\service_wrapper.log"
Type: dirifempty; Name: "{commonappdata}\FamilyEye\Agent\Logs"
Type: files; Name: "{commonappdata}\FamilyEye\Agent\config.json"
Type: files; Name: "{commonappdata}\FamilyEye\Agent\rules_cache.json"
Type: files; Name: "{commonappdata}\FamilyEye\Agent\usage_cache.json"
Type: dirifempty; Name: "{commonappdata}\FamilyEye\Agent"
Type: dirifempty; Name: "{commonappdata}\FamilyEye"

; Use {app} just for cleaning remaining bin folder binaries if any
Type: filesandordirs; Name: "{app}\logs"
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\rules_cache.json"
Type: files; Name: "{app}\child_agent.log"
Type: dirifempty; Name: "{app}"

[Registry]
; ChildAgent auto-start via HKLM Run key (works for all users)
; Note: WPF issue was caused by SERVICE spawning, not Registry. Registry provides proper user context.
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FamilyEyeAgent"; ValueData: """{app}\FamilyEyeAgent.exe"""; Flags: uninsdeletevalue

[Run]
; Service registration is done in second [Run] section below


[UninstallRun]
; (Scheduled Task no longer used - using Registry Run key instead)
; Stop and delete service (New Name)
Filename: "net"; Parameters: "stop FamilyEyeAgent"; Flags: runhidden waituntilterminated
Filename: "sc"; Parameters: "delete FamilyEyeAgent"; Flags: runhidden waituntilterminated
; Stop and delete service (Old Name - just in case)
Filename: "net"; Parameters: "stop ParentalControlAgent"; Flags: runhidden waituntilterminated
Filename: "sc"; Parameters: "delete ParentalControlAgent"; Flags: runhidden waituntilterminated
; Kill processes if still running
Filename: "taskkill"; Parameters: "/F /IM agent_service.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM FamilyEyeAgent.exe"; Flags: runhidden
; Remove Firewall Rules
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEyeAgent_Allow"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_BlockAll"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowAgent"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowDNS"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowBackend"""; Flags: runhidden
; LAN ranges (0-3)
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_0"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_1"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_2"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_3"""; Flags: runhidden
; Cleanup legacy rules
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""ParentalControl_BlockAll"""; Flags: runhidden

[Run]
; Registrovat a spustit službu
Filename: "sc"; Parameters: "create FamilyEyeAgent binPath= ""{app}\agent_service.exe"" start= auto DisplayName= ""FamilyEye Agent"""; Flags: runhidden
Filename: "sc"; Parameters: "description FamilyEyeAgent ""Monitorování a ochrana FamilyEye"""; Flags: runhidden
Filename: "sc"; Parameters: "failure FamilyEyeAgent reset= 60 actions= restart/5000"; Flags: runhidden
Filename: "net"; Parameters: "start FamilyEyeAgent"; Flags: runhidden

[Code]
var
  ServerPage: TInputQueryWizardPage;
  PairingPage: TInputQueryWizardPage;
  ChildAccountPage: TInputQueryWizardPage;
  SecurityPage: TInputOptionWizardPage;
  StatusLabel: TNewStaticText;
  TestButton: TNewButton;
  ServerURL: String;
  PairingToken: String;
  DeviceName: String;
  PairingSuccess: Boolean;
  CreateChildAccountCheckbox: TNewCheckBox;

function GetPCName: String;
begin
  Result := GetEnv('COMPUTERNAME');
  if Result = '' then
    Result := 'Počítač';
end;

procedure TestConnectionClick(Sender: TObject);
var
  WinHttpReq: Variant;
  URL: String;
begin
  StatusLabel.Caption := 'Testuji připojení...';
  StatusLabel.Font.Color := clGray;
  WizardForm.Refresh;
  
  URL := ServerPage.Values[0] + '/api/health';
  
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('GET', URL, False);
    WinHttpReq.SetTimeouts(5000, 5000, 5000, 5000);
    // Accept self-signed certificates - using brackets for indexed property
    try
      WinHttpReq.Option[4] := 256 + 512 + 4096 + 8192;
    except
    end;
    WinHttpReq.Send('');
    
    if WinHttpReq.Status = 200 then
    begin
      StatusLabel.Caption := ExpandConstant('{cm:ConnectionOK}');
      StatusLabel.Font.Color := clGreen;
    end
    else
    begin
      StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}') + ' (HTTP ' + IntToStr(WinHttpReq.Status) + ')';
      StatusLabel.Font.Color := clRed;
    end;
  except
    StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}');
    StatusLabel.Font.Color := clRed;
  end;
end;

function InitializeSetup: Boolean;
var
  ResultCode: Integer;
begin
  // Stop and remove service if running before installation (handle both old and new names)
  Exec('net', 'stop ParentalControlAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc', 'delete ParentalControlAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('net', 'stop FamilyEyeAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc', 'delete FamilyEyeAgent', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Also try to kill the process if stuck
  Exec('taskkill', '/F /IM agent_service.exe', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  Result := True;
end;

procedure InitializeWizard;
var
  HelpLabel: TNewStaticText;
begin
  // Stránka pro server URL
  ServerPage := CreateInputQueryPage(wpSelectDir,
    ExpandConstant('{cm:ServerConfig}'),
    ExpandConstant('{cm:ServerConfigDesc}'),
    'Zadejte adresu serveru, kde běží rodičovský dashboard.' + #13#10 +
    'Tuto adresu najdete na dashboardu v sekci "Přidat zařízení".' + #13#10#13#10 +
    'Příklad: https://monitor.familyeye.cz');
  ServerPage.Add(ExpandConstant('{cm:ServerURL}'), False);
  ServerPage.Values[0] := 'https://';
  
  // Tlačítko pro test připojení
  TestButton := TNewButton.Create(WizardForm);
  TestButton.Parent := ServerPage.Surface;
  TestButton.Left := 0;
  TestButton.Top := 120;  // Moved down to avoid overlapping input field
  TestButton.Width := 150;
  TestButton.Height := 30;
  TestButton.Caption := ExpandConstant('{cm:TestConnection}');
  TestButton.OnClick := @TestConnectionClick;
  
  // Status label
  StatusLabel := TNewStaticText.Create(WizardForm);
  StatusLabel.Parent := ServerPage.Surface;
  StatusLabel.Left := 160;
  StatusLabel.Top := 126; // Moved down to align with button
  StatusLabel.Caption := '';
  StatusLabel.Font.Style := [fsBold];
  
  // Stránka pro párování
  PairingPage := CreateInputQueryPage(ServerPage.ID,
    ExpandConstant('{cm:PairingConfig}'),
    ExpandConstant('{cm:PairingConfigDesc}'),
    'Párovací token získáte na rodičovském dashboardu:' + #13#10 +
    '1. Přihlaste se na dashboard' + #13#10 +
    '2. Klikněte na "Přidat zařízení"' + #13#10 +
    '3. Vygenerujte nový párovací kód' + #13#10 +
    '4. Zkopírujte token a vložte sem');
  PairingPage.Add(ExpandConstant('{cm:PairingToken}'), False);
  PairingPage.Add(ExpandConstant('{cm:DeviceName}'), False);
  PairingPage.Values[0] := '';
  PairingPage.Values[1] := GetPCName + ' - Dětský počítač';
  
  // Stránka pro dětský účet
  ChildAccountPage := CreateInputQueryPage(PairingPage.ID,
    ExpandConstant('{cm:ChildAccountSetup}'),
    ExpandConstant('{cm:ChildAccountSetupDesc}'),
    'Pro maximální bezpečnost doporučujeme vytvořit dětský účet bez administrátorských práv.' + #13#10 +
    'Dítě pak nebude moci odinstalovat agenta ani měnit systémová nastavení.' + #13#10#13#10 +
    'Pokud účet již existuje, nechte pole prázdná.');
  ChildAccountPage.Add(ExpandConstant('{cm:ChildUsername}'), False);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPassword}'), True);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPasswordConfirm}'), True);
  ChildAccountPage.Values[0] := 'Dite';
  
  // Stránka pro zabezpečení
  SecurityPage := CreateInputOptionPage(ChildAccountPage.ID,
    ExpandConstant('{cm:SecuritySetup}'),
    ExpandConstant('{cm:SecuritySetupDesc}'),
    'Vyberte nastavení zabezpečení:',
    False, False);
  SecurityPage.Add(ExpandConstant('{cm:ConfigureFirewall}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockTaskManager}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockControlPanel}'));
  SecurityPage.Add(ExpandConstant('{cm:BlockRegistry}'));
  SecurityPage.Values[0] := True;  // Firewall checked by default
  SecurityPage.Values[1] := True;  // Task Manager
  SecurityPage.Values[2] := True;  // Control Panel
  SecurityPage.Values[3] := True;  // Registry
  
  PairingSuccess := False;
end;

function CreateChildAccount(Username, Password: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if (Username = '') or (Password = '') then
    Exit;
  
  if Exec('net', 'user "' + Username + '" "' + Password + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      Exec('net', 'localgroup Users "' + Username + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      // Save username to registry for uninstaller
      RegWriteStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\FamilyEyeAgent', 'ChildAccount', Username);
      Result := True;
    end;
  end;
end;

// UNINSTALLATION LOGIC
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ChildUser: String;
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Check if we created a child account
    if RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\FamilyEyeAgent', 'ChildAccount', ChildUser) then
    begin
      if ChildUser <> '' then
      begin
        if MsgBox('Chcete smazat vytvořený dětský účet "' + ChildUser + '"?' + #13#10 + 
                  'Pokud zvolíte Ano, účet a všechna jeho data budou smazána.', mbConfirmation, MB_YESNO) = IDYES then
        begin
          if MsgBox('OPRAVDU SMAZAT? ⚠️' + #13#10#13#10 + 
                    'Všechna data uživatele "' + ChildUser + '" budou nenávratně ztracena!' + #13#10 +
                    'Tuto akci nelze vzít zpět.', mbCriticalError, MB_YESNO) = IDYES then
          begin
            Exec('net', 'user "' + ChildUser + '" /delete', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
            MsgBox('Dětský účet byl odstraněn.', mbInformation, MB_OK);
          end;
        end;
      end;
    end;
  end;
end;

procedure ConfigureFirewallRules;
var
  ResultCode: Integer;
begin
  Exec('netsh', 'advfirewall firewall add rule name="FamilyEyeAgent_Allow" dir=out action=allow program="' + ExpandConstant('{app}') + '\agent_service.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('netsh', 'advfirewall firewall add rule name="FamilyEye_BlockTemplate" dir=out action=block enable=no program="C:\placeholder.exe"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure ApplySecurityRestrictions(Username: String);
var
  ResultCode: Integer;
begin
  if Username = '' then
    Exit;
  
  if SecurityPage.Values[1] then
  begin
    RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableTaskMgr', 1);
  end;
  
  if SecurityPage.Values[2] then
  begin
    RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer', 'NoControlPanel', 1);
  end;
  
  if SecurityPage.Values[3] then
  begin
    RegWriteDWordValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableRegistryTools', 1);
  end;
end;

function DoPairing: Boolean;
var
  WinHttpReq: Variant;
  URL: String;
  PostData: String;
  Response: String;
  TempS: String;
  MacAddress: String;
  DeviceID: String;
  ApiKey: String;
  RandomPart: String;
  i, p1, p2: Integer;
  ResultCode: Integer;
  ConfigFile: String;
begin
  Result := False;
  
  RandomPart := '';
  for i := 1 to 8 do
    RandomPart := RandomPart + Chr(Ord('a') + Random(26));
  
  MacAddress := 'auto-detected';
  DeviceID := 'windows-' + GetPCName + '-' + RandomPart;
  
  URL := ServerURL + '/api/devices/pairing/pair';
  PostData := '{"token":"' + PairingToken + '","device_name":"' + DeviceName + '","device_type":"windows","mac_address":"' + MacAddress + '","device_id":"' + DeviceID + '"}';
  
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('POST', URL, False);
    WinHttpReq.SetRequestHeader('Content-Type', 'application/json');
    WinHttpReq.SetTimeouts(10000, 10000, 10000, 10000);
    
    try
      WinHttpReq.Option[4] := 256 + 512 + 4096 + 8192;
    except
    end;
    
    WinHttpReq.Send(PostData);
    
    if WinHttpReq.Status = 200 then
    begin
      Response := WinHttpReq.ResponseText;
      
      ApiKey := '';
      p1 := Pos('"api_key":', Response);
      if p1 > 0 then
      begin
        TempS := Copy(Response, p1 + 10, Length(Response));
        p1 := Pos('"', TempS);
        if p1 > 0 then
        begin
          TempS := Copy(TempS, p1 + 1, Length(TempS));
          p2 := Pos('"', TempS);
          if p2 > 0 then
            ApiKey := Copy(TempS, 1, p2 - 1);
        end;
      end;
      
      DeviceID := '';
      p1 := Pos('"device_id":', Response);
      if p1 > 0 then
      begin
        TempS := Copy(Response, p1 + 12, Length(Response));
        p1 := Pos('"', TempS);
        if p1 > 0 then
        begin
          TempS := Copy(TempS, p1 + 1, Length(TempS));
          p2 := Pos('"', TempS);
          if p2 > 0 then
            DeviceID := Copy(TempS, 1, p2 - 1);
        end;
      end;
      
      if ApiKey = '' then
      begin
        MsgBox('Chyba: Server nevrátil api_key v odpovědi.', mbError, MB_OK);
        Exit;
      end;
      
      if DeviceID = '' then
        DeviceID := 'windows-' + GetPCName + '-' + RandomPart;
      
      // SAVE TO TEMP FIRST - {app} might not exist yet
      ConfigFile := ExpandConstant('{tmp}\config.json');
      SaveStringToFile(ConfigFile,
        '{' + #13#10 +
        '  "backend_url": "' + ServerURL + '",' + #13#10 +
        '  "device_id": "' + DeviceID + '",' + #13#10 +
        '  "api_key": "' + ApiKey + '",' + #13#10 +
        '  "polling_interval": 30,' + #13#10 +
        '  "reporting_interval": 60,' + #13#10 +
        '  "cache_duration": 300,' + #13#10 +
        '  "ssl_verify": false' + #13#10 +
        '}' + #13#10,
        False);
        
      // SECURE THE FILE IMMEDIATELY
      // Grant Full Control to Administrators (S-1-5-32-544) and SYSTEM (S-1-5-18)
      // Remove inheritance so Users don't get access
      if FileExists(ConfigFile) then
      begin
        Exec('icacls', '"' + ConfigFile + '" /inheritance:r /grant *S-1-5-32-544:F /grant *S-1-5-18:F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      end;
      
      Result := True;
    end
    else
    begin
      MsgBox('Server vrátil chybu: ' + IntToStr(WinHttpReq.Status) + #13#10 + WinHttpReq.ResponseText, mbError, MB_OK);
    end;
  except
    Result := False;
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ChildUsername, ChildPassword, ChildPasswordConfirm: String;
begin
  Result := True;
  
  if CurPageID = ServerPage.ID then
  begin
    ServerURL := ServerPage.Values[0];
    
    if (Pos('http://', ServerURL) <> 1) and (Pos('https://', ServerURL) <> 1) then
    begin
      MsgBox('Adresa serveru musí začínat http:// nebo https://', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if ServerURL[Length(ServerURL)] = '/' then
      ServerURL := Copy(ServerURL, 1, Length(ServerURL) - 1);
  end;
  
  if CurPageID = PairingPage.ID then
  begin
    PairingToken := PairingPage.Values[0];
    DeviceName := PairingPage.Values[1];
    
    if Length(PairingToken) < 10 then
    begin
      MsgBox('Párovací token je příliš krátký. Zkopírujte celý token z dashboardu.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if Length(DeviceName) < 3 then
    begin
      MsgBox('Zadejte název zařízení (alespoň 3 znaky).', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    WizardForm.NextButton.Enabled := False;
    WizardForm.BackButton.Enabled := False;
    WizardForm.Refresh;
    
    if DoPairing then
    begin
      PairingSuccess := True;
      MsgBox('Párování úspěšné! Zařízení je nyní připojeno k rodičovskému dashboardu.', mbInformation, MB_OK);
    end
    else
    begin
      WizardForm.NextButton.Enabled := True;
      WizardForm.BackButton.Enabled := True;
      MsgBox('Párování selhalo. Zkontrolujte:' + #13#10 +
             '• Je server spuštěný a dostupný?' + #13#10 +
             '• Je párovací token správný a platný?' + #13#10 +
             '• Máte připojení k síti?', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    WizardForm.NextButton.Enabled := True;
    WizardForm.BackButton.Enabled := True;
  end;
  
  if CurPageID = ChildAccountPage.ID then
  begin
    ChildUsername := ChildAccountPage.Values[0];
    ChildPassword := ChildAccountPage.Values[1];
    ChildPasswordConfirm := ChildAccountPage.Values[2];
    
    if ChildUsername <> '' then
    begin
      if ChildPassword <> ChildPasswordConfirm then
      begin
        MsgBox('Hesla se neshodují!', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      if Length(ChildPassword) < 4 then
      begin
        MsgBox('Heslo musí mít alespoň 4 znaky.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ChildUsername, ChildPassword: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Cleanup old Scheduled Tasks if they exist (from previous versions)
    // Note: Agent restart now uses CreateProcessAsUser, not schtasks
    Exec('schtasks.exe', '/Delete /TN "FamilyEye\ChildAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('schtasks.exe', '/Delete /TN "FamilyEye\FamilyEyeAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // FamilyEyeAgent auto-start at login is handled by Registry Run key (see [Registry] section)
    
    ChildUsername := ChildAccountPage.Values[0];
    ChildPassword := ChildAccountPage.Values[1];
    
    if (ChildUsername <> '') and (ChildPassword <> '') then
    begin
      if CreateChildAccount(ChildUsername, ChildPassword) then
      begin
        ApplySecurityRestrictions(ChildUsername);
        MsgBox('Dětský účet "' + ChildUsername + '" byl úspěšně vytvořen.' + #13#10 +
               'Po přihlášení na tento účet bude dítě monitorováno.', mbInformation, MB_OK);
      end
      else
      begin
        MsgBox('Nepodařilo se vytvořit dětský účet.' + #13#10 +
               'Účet možná již existuje nebo nemáte dostatečná oprávnění.', mbError, MB_OK);
      end;
    end;
    
    if SecurityPage.Values[0] then
    begin
      ConfigureFirewallRules;
    end;
    
    if not PairingSuccess then
    begin
      MsgBox('UPOZORNĚNÍ: Párování nebylo dokončeno.' + #13#10 +
             'Agent nebude fungovat, dokud ho nespárujete.' + #13#10 +
             'Kontaktujte rodiče pro získání párovacího tokenu.', mbError, MB_OK);
    end;
  end;
end;

function InitializeUninstall: Boolean;
var
  Password: String;
begin
  // Result := InputQuery('Parental Control', 'Zadejte administrátorské heslo pro odinstalaci:', Password);
  Result := MsgBox('Opravdu chcete odinstalovat rodičovskou kontrolu?', mbConfirmation, MB_YESNO) = IDYES;
end;


