[Setup]
AppName=FamilyEye Agent
AppVersion=2.2.0
AppVerName=FamilyEye Agent 2.2.0
AppPublisher=BertSoftware
AppPublisherURL=https://github.com/SkriptyRobert/FamilyEye
AppSupportURL=https://github.com/SkriptyRobert/FamilyEye/issues
AppUpdatesURL=https://github.com/SkriptyRobert/FamilyEye/releases

DefaultDirName={commonpf}\FamilyEye\Agent
DefaultGroupName=FamilyEye Agent
DisableProgramGroupPage=yes

OutputDir=output
OutputBaseFilename=FamilyEyeAgent_Setup_2.2.0
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
; Force-delete all FamilyEye data (aggressive cleanup)
Type: filesandordirs; Name: "{commonappdata}\FamilyEye"
Type: filesandordirs; Name: "{app}"

[Registry]
; ChildAgent auto-start via HKLM Run key (works for all users)
; Note: WPF issue was caused by SERVICE spawning, not Registry. Registry provides proper user context.
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "FamilyEyeAgent"; ValueData: """{app}\FamilyEyeAgent.exe"""; Flags: uninsdeletevalue

[Run]
; Service registration is done in second [Run] section below


[UninstallRun]
; Stop and delete service
Filename: "net"; Parameters: "stop FamilyEyeAgent"; Flags: runhidden waituntilterminated
Filename: "sc"; Parameters: "delete FamilyEyeAgent"; Flags: runhidden waituntilterminated
; Kill processes if still running
Filename: "taskkill"; Parameters: "/F /IM agent_service.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM FamilyEyeAgent.exe"; Flags: runhidden
; Remove Firewall Rules
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEyeAgent_Allow"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_BlockAll"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowAgent"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowDNS"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowBackend"""; Flags: runhidden
; Remove LAN ranges (0-3)
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_0"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_1"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_2"""; Flags: runhidden
Filename: "netsh"; Parameters: "advfirewall firewall delete rule name=""FamilyEye_AllowLAN_3"""; Flags: runhidden
; CRITICAL: Reset firewall policy to allow outbound (in case Internet was blocked)
Filename: "netsh"; Parameters: "advfirewall set allprofiles firewallpolicy blockinbound,allowoutbound"; Flags: runhidden waituntilterminated
; CRITICAL: Clean hosts file (remove any [PC-BLOCK] entries left by website blocking)
Filename: "powershell"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""$h='C:\Windows\System32\drivers\etc\hosts'; if(Test-Path $h){{$c=Get-Content $h | Where-Object {{$_ -notmatch '\[PC-BLOCK\]'}}; Set-Content $h $c -Force}}"""; Flags: runhidden waituntilterminated

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
  ParentAccountPage: TInputQueryWizardPage;
  SecurityPage: TInputOptionWizardPage;
  StatusLabel: TNewStaticText;
  TestButton: TNewButton;
  ServerURL: String;
  PairingToken: String;
  DeviceName: String;
  PairingSuccess: Boolean;
  NeedParentAccount: Boolean;
  CreateChildAccountCheckbox: TNewCheckBox;

function GetPCName: String;
begin
  Result := GetEnv('COMPUTERNAME');
  if Result = '' then
    Result := 'Počítač';
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
          Result := Result + 1;
        end;
      end;
    end;
  end;
  
  // Cleanup
  DeleteFile(TempFile);
end;

// Check if a username exists on the system
function UserExists(Username: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('net', 'user "' + Username + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    Result := (ResultCode = 0);
  end;
end;

// Check if a specific user is an Administrator
function IsUserAdmin(Username: String): Boolean;
var
  ResultCode: Integer;
  TempFile: String;
  Lines: TArrayOfString;
  i: Integer;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\admincheck.txt');
  
  // Get list of Administrators group members
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

// Get list of all non-admin user accounts (for dropdown selection)
function GetNonAdminAccounts: String;
var
  ResultCode: Integer;
  TempFile, TempAdmins: String;
  AllUsers, AdminUsers: TArrayOfString;
  i, j: Integer;
  IsAdmin: Boolean;
  UserList: String;
begin
  Result := '';
  TempFile := ExpandConstant('{tmp}\allusers.txt');
  TempAdmins := ExpandConstant('{tmp}\admins2.txt');
  
  // Get all users
  if not Exec('cmd', '/c net user > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    Exit;
    
  // Get admin users
  Exec('cmd', '/c net localgroup Administrators > "' + TempAdmins + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  
  if LoadStringsFromFile(TempFile, AllUsers) and LoadStringsFromFile(TempAdmins, AdminUsers) then
  begin
    UserList := '';
    for i := 0 to GetArrayLength(AllUsers) - 1 do
    begin
      // Skip header lines and empty lines
      if (Length(AllUsers[i]) > 0) and (Pos('---', AllUsers[i]) = 0) and 
         (Pos('User accounts', AllUsers[i]) = 0) and (Pos('command', AllUsers[i]) = 0) and
         (Pos('\\', AllUsers[i]) = 0) then
      begin
        // Check if this user is NOT an admin
        IsAdmin := False;
        for j := 0 to GetArrayLength(AdminUsers) - 1 do
        begin
          if Pos(Trim(AllUsers[i]), AdminUsers[j]) > 0 then
          begin
            IsAdmin := True;
            Break;
          end;
        end;
        
        if not IsAdmin then
        begin
          if UserList <> '' then
            UserList := UserList + ', ';
          UserList := UserList + Trim(AllUsers[i]);
        end;
      end;
    end;
    Result := UserList;
  end;
  
  DeleteFile(TempFile);
  DeleteFile(TempAdmins);
end;

// Create parent admin account
function CreateParentAccount(Username, Password: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if (Username = '') or (Password = '') then
    Exit;
  
  // Create user
  if Exec('net', 'user "' + Username + '" "' + Password + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if ResultCode = 0 then
    begin
      // Add to Administrators group
      Exec('net', 'localgroup Administrators "' + Username + '" /add', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Result := True;
    end;
  end;
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
  // Stop and remove service if running before installation
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
    'Adresa serveru propojí tento počítač s vaším rodičovským účtem.' + #13#10 +
    'Díky tomu uvidíte aktivitu dítěte na dashboardu.' + #13#10#13#10 +
    'Kde ji najdu?' + #13#10 +
    'Na dashboardu klikněte na "+ Přidat" a adresa se zobrazí.' + #13#10#13#10 +
    'Příklad: https://192.168.0.100:8000');
  ServerPage.Add(ExpandConstant('{cm:ServerURL}'), False);
  ServerPage.Values[0] := 'https://';
  
  // Tlačítko pro test připojení
  TestButton := TNewButton.Create(WizardForm);
  TestButton.Parent := ServerPage.Surface;
  TestButton.Left := 0;
  TestButton.Top := 160;  // Moved further down to avoid overlapping input field
  TestButton.Width := 150;
  TestButton.Height := 30;
  TestButton.Caption := ExpandConstant('{cm:TestConnection}');
  TestButton.OnClick := @TestConnectionClick;
  
  // Status label
  StatusLabel := TNewStaticText.Create(WizardForm);
  StatusLabel.Parent := ServerPage.Surface;
  StatusLabel.Left := 160;
  StatusLabel.Top := 166; // Aligned with button
  StatusLabel.Caption := '';
  StatusLabel.Font.Style := [fsBold];
  
  // Stránka pro párování
  PairingPage := CreateInputQueryPage(ServerPage.ID,
    ExpandConstant('{cm:PairingConfig}'),
    ExpandConstant('{cm:PairingConfigDesc}'),
    'Token je jednorázový bezpečnostní kód platný 5 minut.' + #13#10 +
    'Zajišťuje, že pouze vy můžete přidat toto zařízení.' + #13#10#13#10 +
    'Jak ho získám?' + #13#10 +
    '1. Na dashboardu klikněte "+ Přidat"' + #13#10 +
    '2. Klikněte "Vygenerovat párovací kód"' + #13#10 +
    '3. Zkopírujte kód a vložte ho sem');
  PairingPage.Add(ExpandConstant('{cm:PairingToken}'), False);
  PairingPage.Add(ExpandConstant('{cm:DeviceName}'), False);
  PairingPage.Values[0] := '';
  PairingPage.Values[1] := GetPCName + ' - Dětský počítač';
  
  // Stránka pro dětský účet - s auto-detekcí
  ChildAccountPage := CreateInputQueryPage(PairingPage.ID,
    ExpandConstant('{cm:ChildAccountSetup}'),
    ExpandConstant('{cm:ChildAccountSetupDesc}'),
    '✅ DOPORUČENÍ: Vytvořte dítěti vlastní účet bez admin práv.' + #13#10 +
    'Dítě pak nebude moci odinstalovat ochranu ani měnit nastavení.' + #13#10#13#10 +
    '💡 Pokud dětský účet již existuje (např. "Honzik"), zadejte jeho jméno' + #13#10 +
    'a pole hesla nechte PRÁZDNÁ - použijeme stávající účet.' + #13#10#13#10 +
    '⚠️ Administrátorský účet jako dětský NELZE použít!');
  ChildAccountPage.Add(ExpandConstant('{cm:ChildUsername}'), False);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPassword}'), True);
  ChildAccountPage.Add(ExpandConstant('{cm:ChildPasswordConfirm}'), True);
  ChildAccountPage.Values[0] := 'Dite';
  
  // Stránka pro rodičovský účet (zobrazí se jen pokud je potřeba)
  ParentAccountPage := CreateInputQueryPage(ChildAccountPage.ID,
    'Rodičovský administrátorský účet',
    'Zajistěte si přístup k počítači',
    'DŮLEŽITÉ: Na tomto počítači existuje jen jeden admin účet.' + #13#10 +
    'Pokud dětský účet degradujeme, potřebujete záložní admin účet.' + #13#10#13#10 +
    'BEZ TOHOTO ÚČTU ZTRATÍTE KONTROLU NAD POČÍTAČEM!' + #13#10 +
    'Vytvořte si heslo, které dítě nezná.');
  ParentAccountPage.Add('Uživatelské jméno rodiče:', False);
  ParentAccountPage.Add('Heslo:', True);
  ParentAccountPage.Add('Potvrzení hesla:', True);
  ParentAccountPage.Values[0] := 'Rodic';
  
  // Stránka pro zabezpečení
  SecurityPage := CreateInputOptionPage(ParentAccountPage.ID,
    ExpandConstant('{cm:SecuritySetup}'),
    ExpandConstant('{cm:SecuritySetupDesc}'),
    'Tato nastavení chrání před obejitím rodičovské kontroly.' + #13#10 +
    'Doporučujeme nechat vše zapnuté.' + #13#10#13#10 +
    'TIP: Pro maximální ochranu zapněte v BIOSu "Secure Boot"' + #13#10 +
    'a heslo na BIOS – zabrání bootování z USB.',
    False, False);
  SecurityPage.Add('Firewall – povolí jen nutnou komunikaci agenta');
  SecurityPage.Add('Zakázat Správce úloh – dítě nemůže ukončit agenta');
  SecurityPage.Add('Omezit Ovládací panely – zabrání změnám nastavení');
  SecurityPage.Add('Zakázat Registry – zabrání pokročilým úpravám');
  SecurityPage.Values[0] := True;  // Firewall
  SecurityPage.Values[1] := True;  // Task Manager
  SecurityPage.Values[2] := True;  // Control Panel
  SecurityPage.Values[3] := True;  // Registry
  
  PairingSuccess := False;
  NeedParentAccount := False;
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
    // 1. Undo security restrictions (remove from .DEFAULT hive)
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableTaskMgr');
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\Explorer', 'NoControlPanel');
    RegDeleteValue(HKEY_USERS, '.DEFAULT\Software\Microsoft\Windows\CurrentVersion\Policies\System', 'DisableRegistryTools');
    
    // 2. Check if we created a child account
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
    
    // 3. Delete FamilyEye registry key
    RegDeleteKeyIncludingSubkeys(HKEY_LOCAL_MACHINE, 'SOFTWARE\FamilyEyeAgent');
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
  
  // Retry loop (up to 3 attempts)
  for i := 1 to 3 do
  begin
    try
      WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
      WinHttpReq.Open('POST', URL, False);
      WinHttpReq.SetRequestHeader('Content-Type', 'application/json');
      WinHttpReq.SetTimeouts(5000, 5000, 5000, 15000);
      
      // Accept self-signed certificates
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
        
        // SAVE CONFIG TO TEMP
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
          '}', False);
          
        // SECURE THE FILE IMMEDIATELY
        if FileExists(ConfigFile) then
        begin
          Exec('icacls', '"' + ConfigFile + '" /inheritance:r /grant *S-1-5-32-544:F /grant *S-1-5-18:F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        end;
        
        Result := True;
        Exit; // Success, exit function
      end
      else
      begin
        // Non-200 response - only show error on last attempt
        if i = 3 then
          MsgBox('Server vrátil chybu: ' + IntToStr(WinHttpReq.Status) + #13#10 + WinHttpReq.ResponseText, mbError, MB_OK);
      end;
    except
      // Exception - only show error on last attempt
      if i = 3 then
        MsgBox('Nepodařilo se připojit k serveru. Zkontrolujte připojení.', mbError, MB_OK);
    end;
  end;
  
  // All retries failed
  Result := False;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ChildUsername, ChildPassword, ChildPasswordConfirm: String;
begin
  Result := True;
  
  if CurPageID = ServerPage.ID then
  begin
    ServerURL := Trim(ServerPage.Values[0]);
    
    // Normalize URL
    if (Pos('http://', LowerCase(ServerURL)) <> 1) and (Pos('https://', LowerCase(ServerURL)) <> 1) then
    begin
        // Default to https if missing
        ServerURL := 'https://' + ServerURL;
    end;
    
    // Remove trailing slash
    if (Length(ServerURL) > 0) and (ServerURL[Length(ServerURL)] = '/') then
      ServerURL := Copy(ServerURL, 1, Length(ServerURL) - 1);
      
    // Remove port if user accidentally pasted it twice or in wrong format (basic check)
    // Update the input field with cleaned value
    ServerPage.Values[0] := ServerURL;
    
    if Length(ServerURL) < 10 then
    begin
       MsgBox('Adresa serveru se zdá být neplatná.', mbError, MB_OK);
       Result := False;
       Exit;
    end;
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
      // NEW: Check if user is trying to use an admin account
      if IsUserAdmin(ChildUsername) then
      begin
        MsgBox('⛔ CHYBA: Účet "' + ChildUsername + '" je administrátor!' + #13#10#13#10 +
               'Dětský účet NESMÍ mít administrátorská práva,' + #13#10 +
               'protože by dítě mohlo odinstalovat ochranu.' + #13#10#13#10 +
               'Zadejte jiné uživatelské jméno.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      // NEW: Check if account already exists
      if UserExists(ChildUsername) then
      begin
        // Existing account - no password needed
        if (ChildPassword = '') and (ChildPasswordConfirm = '') then
        begin
          MsgBox('✅ Účet "' + ChildUsername + '" již existuje.' + #13#10 +
                 'Použijeme tento stávající účet pro dítě.' + #13#10#13#10 +
                 'Na tento účet budou aplikována bezpečnostní omezení.', mbInformation, MB_OK);
          // Skip password validation - using existing account
        end
        else
        begin
          MsgBox('⚠️ Účet "' + ChildUsername + '" již existuje!' + #13#10#13#10 +
                 'Pokud chcete použít existující účet, nechte heslo PRÁZDNÉ.' + #13#10 +
                 'Pokud chcete vytvořit NOVÝ účet, zadejte jiné uživatelské jméno.', mbInformation, MB_OK);
          Result := False;
          Exit;
        end;
      end
      else
      begin
        // New account - password required
        if ChildPassword = '' then
        begin
          MsgBox('Pro vytvoření nového účtu musíte zadat heslo.', mbError, MB_OK);
          Result := False;
          Exit;
        end;
        
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
      
      // Check if we need parent account (only 1 admin on system)
      if CountAdminAccounts <= 1 then
      begin
        NeedParentAccount := True;
        MsgBox('POZOR: Na tomto počítači je jen jeden administrátorský účet.' + #13#10 +
               'Pro zachování kontroly nad počítačem musíte vytvořit rodičovský admin účet.', 
               mbInformation, MB_OK);
      end
      else
      begin
        NeedParentAccount := False;
      end;
    end
    else
    begin
      // Empty username - show warning
      if MsgBox('⚠️ Nezadali jste dětský účet!' + #13#10#13#10 +
                'Bez vlastního dětského účtu:' + #13#10 +
                '• Dítě bude používat VÁŠE nastavení' + #13#10 +
                '• Dítě MŮŽE odinstalovat ochranu' + #13#10 +
                '• Bezpečnost bude výrazně nižší' + #13#10#13#10 +
                'Opravdu chcete pokračovat BEZ dětského účtu?', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
        Exit;
      end;
      NeedParentAccount := False;
    end;
  end;
  
  // Validate ParentAccountPage
  if CurPageID = ParentAccountPage.ID then
  begin
    if NeedParentAccount then
    begin
      if ParentAccountPage.Values[0] = '' then
      begin
        MsgBox('Musíte zadat uživatelské jméno pro rodičovský účet!', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      if ParentAccountPage.Values[1] <> ParentAccountPage.Values[2] then
      begin
        MsgBox('Hesla se neshodují!', mbError, MB_OK);
        Result := False;
        Exit;
      end;
      
      if Length(ParentAccountPage.Values[1]) < 4 then
      begin
        MsgBox('Heslo musí mít alespoň 4 znaky.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
  end;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  
  // Skip ParentAccountPage if we don't need it
  if PageID = ParentAccountPage.ID then
  begin
    Result := not NeedParentAccount;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ChildUsername, ChildPassword: String;
  ParentUsername, ParentPassword: String;
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Cleanup old Scheduled Tasks if they exist (from previous versions)
    Exec('schtasks.exe', '/Delete /TN "FamilyEye\ChildAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('schtasks.exe', '/Delete /TN "FamilyEye\FamilyEyeAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    
    // 1. Create parent admin account if needed
    if NeedParentAccount then
    begin
      ParentUsername := ParentAccountPage.Values[0];
      ParentPassword := ParentAccountPage.Values[1];
      
      if (ParentUsername <> '') and (ParentPassword <> '') then
      begin
        if CreateParentAccount(ParentUsername, ParentPassword) then
        begin
          MsgBox('Rodičovský admin účet "' + ParentUsername + '" byl vytvořen.' + #13#10 +
                 'ZAPAMATUJTE SI HESLO - bez něj ztratíte kontrolu!', mbInformation, MB_OK);
        end
        else
        begin
          MsgBox('VAROVÁNÍ: Nepodařilo se vytvořit rodičovský účet!' + #13#10 +
                 'Pokračování může vést ke ztrátě kontroly nad počítačem.', mbError, MB_OK);
        end;
      end;
    end;
    
    // 2. Handle child account (create new OR apply restrictions to existing)
    ChildUsername := ChildAccountPage.Values[0];
    ChildPassword := ChildAccountPage.Values[1];
    
    if ChildUsername <> '' then
    begin
      if (ChildPassword <> '') then
      begin
        // NEW account - create it
        if CreateChildAccount(ChildUsername, ChildPassword) then
        begin
          ApplySecurityRestrictions(ChildUsername);
          MsgBox('✅ Dětský účet "' + ChildUsername + '" byl úspěšně vytvořen.' + #13#10 +
                 'Po přihlášení na tento účet bude dítě monitorováno.', mbInformation, MB_OK);
        end
        else
        begin
          MsgBox('Nepodařilo se vytvořit dětský účet.' + #13#10 +
                 'Účet možná již existuje nebo nemáte dostatečná oprávnění.', mbError, MB_OK);
        end;
      end
      else
      begin
        // EXISTING account - just apply restrictions
        ApplySecurityRestrictions(ChildUsername);
        MsgBox('✅ Na existující účet "' + ChildUsername + '" byla aplikována bezpečnostní omezení.' + #13#10 +
               'Po přihlášení na tento účet bude dítě monitorováno.', mbInformation, MB_OK);
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


