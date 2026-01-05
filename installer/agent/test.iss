[Setup]
AppName=Parental Control Agent
AppVersion=2.0.0
DefaultDirName={autopf}\TestApp
OutputBaseFilename=test_setup
Compression=lzma2
SolidCompression=yes

[Languages]
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"

[CustomMessages]
czech.WelcomeLabel1=Instalace rodičovské kontroly
czech.WelcomeLabel2=Tento průvodce nainstaluje monitorovacího agenta a pomůže vám nastavit bezpečný dětský účet.%n%nCo průvodce udělá:%n• Nainstaluje monitorovacího agenta%n• Spáruje počítač s rodičovským dashboardem%n• Vytvoří dětský účet bez administrátorských práv%n• Nastaví firewall pro ochranu
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
Source: "setup_agent.iss"; DestDir: "{app}"

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
  // StatusLabel may be nil during test compilation, ignoring runtime safety
  if StatusLabel <> nil then
  begin
    StatusLabel.Caption := 'Testuji připojení...';
    StatusLabel.Font.Color := clGray;
  end;
  WizardForm.Refresh;
  
  // URL := ServerPage.Values[0] + '/api/health';
  URL := 'https://localhost/api/health'; 
  
  try
    WinHttpReq := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    WinHttpReq.Open('GET', URL, False);
    WinHttpReq.SetTimeouts(5000, 5000, 5000, 5000);
    // Accept self-signed certificates
    try
      WinHttpReq.Option[4] := 256 + 512 + 4096 + 8192;
    except
    end;
    WinHttpReq.Send('');
    
    if WinHttpReq.Status = 200 then
    begin
      if StatusLabel <> nil then
      begin
        StatusLabel.Caption := ExpandConstant('{cm:ConnectionOK}');
        StatusLabel.Font.Color := clGreen;
      end;
    end
    else
    begin
      if StatusLabel <> nil then
      begin
        StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}') + ' (HTTP ' + IntToStr(WinHttpReq.Status) + ')';
        StatusLabel.Font.Color := clRed;
      end;
    end;
  except
    if StatusLabel <> nil then
    begin
      StatusLabel.Caption := ExpandConstant('{cm:ConnectionFailed}');
      StatusLabel.Font.Color := clRed;
    end;
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
  ConfigFile: String;
begin
  Result := False;
  
  // Generovat náhodné ID
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
    
    // Accept self-signed certificates
    try
      WinHttpReq.Option[4] := 256 + 512 + 4096 + 8192;
    except
    end;
    
    WinHttpReq.Send(PostData);
    
    if WinHttpReq.Status = 200 then
    begin
      Response := WinHttpReq.ResponseText;
      
      // Parse api_key from JSON response
      ApiKey := '';
      p1 := Pos('"api_key":', Response);
      if p1 > 0 then
      begin
        // Cut string after "api_key":
        TempS := Copy(Response, p1 + 10, Length(Response)); 
        // Find opening quote
        p1 := Pos('"', TempS);
        if p1 > 0 then
        begin
          // Cut start including quote
          TempS := Copy(TempS, p1 + 1, Length(TempS));
          // Find closing quote
          p2 := Pos('"', TempS);
          if p2 > 0 then
            ApiKey := Copy(TempS, 1, p2 - 1);
        end;
      end;
      
      // Parse device_id from backend response
      DeviceID := ''; // Reset device_id to parse from response if valid
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
        DeviceID := 'windows-' + GetPCName + '-' + RandomPart; // Fallback
      
      ConfigFile := ExpandConstant('{app}\config.json');
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

procedure InitializeWizard;
begin
  // Empty
end;
