"""UI Overlay - Lock screen and notification overlays for ChildAgent.

Creates full-screen WPF overlays that cannot be easily closed by the user.
Falls back to native Windows MessageBox if PowerShell/WPF fails.
"""
import subprocess
import threading
import time
import ctypes
from typing import Optional, Callable

# Windows MessageBox constants
MB_OK = 0x0
MB_ICONWARNING = 0x30
MB_ICONERROR = 0x10
MB_ICONINFORMATION = 0x40
MB_TOPMOST = 0x40000


# Vector icons (Material Design)
ICON_LOCK = "M18,8H17V6A5,5 0 0,0 7,6V8H6A2,2 0 0,0 4,10V20A2,2 0 0,0 6,22H18A2,2 0 0,0 20,20V10A2,2 0 0,0 18,8M12,17A2,2 0 1,1 14,15A2,2 0 0,1 12,17M15,8H9V6A3,3 0 0,1 15,6V8Z"
ICON_ALERT = "M13,14H11V10H13M13,18H11V16H13M1,21H23L12,2L1,21Z"
ICON_EYE = "M12,9A3,3 0 0,0 9,12A3,3 0 0,0 12,15A3,3 0 0,0 15,12A3,3 0 0,0 12,9M12,17A5,5 0 0,1 7,12A5,5 0 0,1 12,7A5,5 0 0,1 17,12A5,5 0 0,1 12,17M12,4.5C7,4.5 2.73,7.61 1,12C2.73,16.39 7,19.5 12,19.5C17,19.5 21.27,16.39 23,12C21.27,7.61 17,4.5 12,4.5Z"
ICON_CLOCK = "M12,20A8,8 0 0,0 20,12A8,8 0 0,0 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20M12,2A10,10 0 0,1 22,12A10,10 0 0,1 12,22C6.47,22 2,17.5 2,12A10,10 0 0,1 12,2M12.5,7V12.25L17,14.92L16.25,16.15L11,13V7H12.5Z"
ICON_MOON = "M17.75,4.09L15.22,6.03L16.13,9.09L13.5,7.28L10.87,9.09L11.78,6.03L9.25,4.09L12.44,4L13.5,1L14.56,4L17.75,4.09M21.25,11L19.61,12.25L20.2,14.23L18.5,13.06L16.8,14.23L17.39,12.25L15.75,11L17.81,10.95L18.5,9L19.19,10.95L21.25,11M18.97,15.95C19.8,15.87 20.69,17.05 20.16,17.80C19.84,18.25 19.5,18.67 19.08,19.07C15.17,23 8.84,23 4.94,19.07C1.03,15.17 1.03,8.83 4.94,4.93C5.34,4.53 5.76,4.17 6.21,3.85C6.96,3.32 8.14,4.21 8.06,5.04C7.79,7.9 8.75,10.87 10.95,13.06C13.14,15.26 16.1,16.22 18.97,15.95Z"


def _show_messagebox(title: str, message: str, is_error: bool = False):
    """Show message to user session using WTSSendMessage (works from Session 0).
    
    Falls back to regular MessageBox if WTS fails.
    """
    try:
        # Try WTSSendMessage first - designed for cross-session messaging
        wtsapi32 = ctypes.windll.wtsapi32
        kernel32 = ctypes.windll.kernel32
        
        WTS_CURRENT_SERVER_HANDLE = 0
        WTS_CURRENT_SESSION = 0xFFFFFFFF  # Use current session
        
        # Get active console session
        session_id = kernel32.WTSGetActiveConsoleSessionId()
        
        # Prepare strings as wide strings
        title_w = ctypes.create_unicode_buffer(title)
        message_w = ctypes.create_unicode_buffer(message)
        
        style = MB_OK | (MB_ICONERROR if is_error else MB_ICONWARNING)
        response = ctypes.c_ulong()
        
        # WTSSendMessageW
        result = wtsapi32.WTSSendMessageW(
            WTS_CURRENT_SERVER_HANDLE,  # hServer
            session_id,                  # SessionId
            title_w,                     # pTitle
            len(title) * 2,             # TitleLength (bytes)
            message_w,                   # pMessage
            len(message) * 2,           # MessageLength (bytes)
            style,                       # Style
            0,                          # Timeout (0 = wait forever)
            ctypes.byref(response),     # pResponse
            True                        # bWait
        )
        
        if result:
            return  # Success
            
    except Exception:
        pass
    
    # Fallback to regular MessageBox with TOPMOST
    try:
        icon = MB_ICONERROR if is_error else MB_ICONWARNING
        ctypes.windll.user32.MessageBoxW(0, message, title, MB_OK | icon | MB_TOPMOST)
    except Exception:
        pass  # Last resort failed


def _run_powershell_async(script: str, log_callback: Callable = None, fallback_title: str = None, fallback_message: str = None, fallback_is_error: bool = False):
    """Run PowerShell script in background thread with MessageBox fallback.
    
    Uses Base64 encoding to avoid command-line escaping issues.
    """
    import base64
    
    def _run():
        try:
            # Encode script to Base64 (UTF-16LE required for PowerShell)
            encoded_script = base64.b64encode(script.encode('utf-16le')).decode('utf-8')
            
            result = subprocess.run(
                ["powershell", "-WindowStyle", "Hidden", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded_script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=60  # 60 seconds for user to click button
            )
            
            # If PowerShell returned error and we have fallback info, show MessageBox
            if result.returncode != 0:
                error_output = result.stderr.decode('utf-8', errors='ignore') if result.stderr else "Unknown error"
                if log_callback:
                    log_callback(f"PowerShell failed (code {result.returncode}): {error_output}")
                    log_callback("Switching to MessageBox fallback")
                
                if fallback_title:
                    _show_messagebox(fallback_title, fallback_message or "", fallback_is_error)
        except Exception as e:
            if log_callback:
                log_callback(f"PowerShell execution error: {e}")
            # Use fallback on exception
            if fallback_title:
                _show_messagebox(fallback_title, fallback_message or str(e), fallback_is_error)
    threading.Thread(target=_run, daemon=True).start()


def _escape_xaml(text: str) -> str:
    """Escape text for XAML."""
    return text.replace(chr(10), '&#x0a;').replace('"', '&quot;').replace("'", "&apos;")


class UIOverlay:
    """Manages UI overlays and notifications for ChildAgent."""
    
    def __init__(self):
        self._lock_screen_active = False
        self._countdown_thread: Optional[threading.Thread] = None
        self._log_callback = None
    
    def set_log_callback(self, callback):
        self._log_callback = callback
    
    def _log(self, msg: str):
        if self._log_callback:
            self._log_callback(msg)
        else:
            print(f"[UI] {msg}")
    
    def show_toast(self, title: str, message: str, icon: str = "ℹ️"):
        """Show native Windows toast notification.
        
        Note: Toast notifications accept plain text, no XAML escaping needed.
        """
        # Escape only characters problematic for PowerShell strings
        safe_title = title.replace('"', '`"').replace("'", "''")
        safe_message = message.replace('"', '`"').replace("'", "''")
        
        ps_script = f'''
$ErrorActionPreference = 'SilentlyContinue'
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName("text")
$textNodes.Item(0).InnerText = "{icon} {safe_title}"
$textNodes.Item(1).InnerText = "{safe_message}"
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("FamilyEye")
$notifier.Show([Windows.UI.Notifications.ToastNotification]::new($template))
'''
        _run_powershell_async(ps_script, self._log)
        self._log(f"Toast: {title}")

    
    def show_popup(self, title: str, message: str, is_error: bool = False):
        """Show modern WPF popup dialog with FamilyEye branding."""
        color = "#e74c3c" if is_error else "#f1c40f"
        icon_path = ICON_LOCK if is_error else ICON_ALERT
        escaped_msg = _escape_xaml(message)
        
        ps_script = f'''
try {{
    Add-Type -AssemblyName PresentationFramework
    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="{_escape_xaml(title)}" Height="280" Width="480" WindowStyle="None" ResizeMode="NoResize"
        AllowsTransparency="True" Background="Transparent" Topmost="True" WindowStartupLocation="CenterScreen">
    <Border CornerRadius="12" Background="#1e1e1e" BorderBrush="{color}" BorderThickness="2">
        <Border.Effect><DropShadowEffect BlurRadius="20" ShadowDepth="0" Opacity="0.5" Color="Black"/></Border.Effect>
        <Grid Margin="25">
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/>
            </Grid.RowDefinitions>
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Left">
                <Viewbox Width="32" Height="32" Margin="0,0,15,0">
                    <Path Data="{icon_path}" Fill="{color}" Stretch="Uniform"/>
                </Viewbox>
                <TextBlock Text="{_escape_xaml(title)}" Foreground="White" FontSize="22" FontWeight="SemiBold" VerticalAlignment="Center" FontFamily="Segoe UI"/>
            </StackPanel>
            <TextBlock Grid.Row="1" Text="{escaped_msg}" Foreground="#cccccc" FontSize="15" TextWrapping="Wrap" LineHeight="22"
                     HorizontalAlignment="Left" VerticalAlignment="Center" Margin="0,15,0,20"/>
            <Grid Grid.Row="2">
                <StackPanel Orientation="Horizontal" HorizontalAlignment="Left" VerticalAlignment="Center" Opacity="0.7">
                    <Viewbox Width="18" Height="18" Margin="0,0,8,0">
                        <Path Data="{ICON_EYE}" Fill="#6366f1" Stretch="Uniform">
                            <Path.Effect><DropShadowEffect BlurRadius="8" ShadowDepth="0" Opacity="0.4" Color="#6366f1"/></Path.Effect>
                        </Path>
                    </Viewbox>
                    <TextBlock Text="FamilyEye" Foreground="#6366f1" FontSize="13" FontWeight="SemiBold" VerticalAlignment="Center" FontFamily="Segoe UI"/>
                </StackPanel>
                <Button Content="Rozum&#xed;m" Width="140" Height="40" Background="{color}" Foreground="White"
                        FontSize="15" FontWeight="Bold" Cursor="Hand" IsDefault="True" IsCancel="True" HorizontalAlignment="Right">
                    <Button.Template>
                        <ControlTemplate TargetType="Button">
                            <Border Background="{{TemplateBinding Background}}" CornerRadius="6" x:Name="border">
                                <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                            </Border>
                            <ControlTemplate.Triggers>
                                <Trigger Property="IsMouseOver" Value="True">
                                    <Setter TargetName="border" Property="Opacity" Value="0.9"/>
                                </Trigger>
                            </ControlTemplate.Triggers>
                        </ControlTemplate>
                    </Button.Template>
                </Button>
            </Grid>
        </Grid>
    </Border>
</Window>
"@
    $reader = (New-Object System.Xml.XmlNodeReader $xaml)
    [Windows.Markup.XamlReader]::Load($reader).ShowDialog() | Out-Null
    exit 0
}} catch {{
    Write-Error $_
    exit 1
}}
'''
        _run_powershell_async(ps_script, self._log, fallback_title=title, fallback_message=message, fallback_is_error=is_error)
        self._log(f"Popup: {title}")
    
    def show_branded_notification(self, message: str):
        """Show branded FamilyEye notification."""
        bg = "#151b2b"
        accent = "#6366f1"
        
        ps_script = f'''
try {{
    Add-Type -AssemblyName PresentationFramework
    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="FamilyEye" Height="180" Width="400" WindowStyle="None" ResizeMode="NoResize"
        AllowsTransparency="True" Background="Transparent" Topmost="True" WindowStartupLocation="CenterScreen">
    <Border CornerRadius="16" Background="{bg}" BorderBrush="#334155" BorderThickness="1">
        <Border.Effect><DropShadowEffect BlurRadius="30" ShadowDepth="0" Opacity="0.6" Color="Black"/></Border.Effect>
        <Grid Margin="20">
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/><RowDefinition Height="*"/><RowDefinition Height="Auto"/>
            </Grid.RowDefinitions>
            <StackPanel Grid.Row="0" Orientation="Horizontal" HorizontalAlignment="Center" Margin="0,5,0,15">
                <Viewbox Width="36" Height="36" Margin="0,0,12,0">
                    <Path Data="{ICON_EYE}" Fill="{accent}" Stretch="Uniform">
                        <Path.Effect><DropShadowEffect BlurRadius="12" ShadowDepth="0" Opacity="0.6" Color="{accent}"/></Path.Effect>
                    </Path>
                </Viewbox>
                <TextBlock Text="FamilyEye" Foreground="{accent}" FontSize="28" FontWeight="Bold" VerticalAlignment="Center" FontFamily="Segoe UI">
                    <TextBlock.Effect><DropShadowEffect BlurRadius="15" ShadowDepth="0" Opacity="0.4" Color="{accent}"/></TextBlock.Effect>
                </TextBlock>
            </StackPanel>
            <TextBlock Grid.Row="1" Text="{_escape_xaml(message)}" Foreground="#94a3b8" FontSize="14" HorizontalAlignment="Center" TextAlignment="Center" Margin="0,0,0,15"/>
            <Button Grid.Row="2" Content="Rozumím" Width="100" Height="32" Background="{accent}" Foreground="White"
                    FontSize="13" FontWeight="SemiBold" Cursor="Hand" IsDefault="True" IsCancel="True" HorizontalAlignment="Center">
                <Button.Template>
                    <ControlTemplate TargetType="Button">
                        <Border Background="{{TemplateBinding Background}}" CornerRadius="16" x:Name="border">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="border" Property="Opacity" Value="0.9"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Button.Template>
            </Button>
        </Grid>
    </Border>
</Window>
"@
    $reader = (New-Object System.Xml.XmlNodeReader $xaml)
    [Windows.Markup.XamlReader]::Load($reader).ShowDialog() | Out-Null
    exit 0
}} catch {{
    Write-Error $_
    exit 1
}}
'''
        _run_powershell_async(ps_script, self._log, fallback_title="FamilyEye", fallback_message=message, fallback_is_error=False)
        self._log(f"Branded notification: {message}")
    
    def show_lock_screen(self, message: str):
        """Show full-screen lock overlay.
        
        Creates a semi-transparent dark overlay with FamilyEye branding
        that covers the entire screen and cannot be closed easily.
        """
        if self._lock_screen_active:
            self._log("Lock screen already active")
            return
        
        self._lock_screen_active = True
        escaped_msg = _escape_xaml(message)
        
        # This creates a TopMost fullscreen window
        ps_script = f'''
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName System.Windows.Forms

# Get screen dimensions
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds

[xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="FamilyEye Lock" WindowStyle="None" ResizeMode="NoResize"
        AllowsTransparency="True" Background="#E0000000" Topmost="True"
        WindowState="Maximized" ShowInTaskbar="False">
    <Window.Resources>
        <Style TargetType="Window">
            <Setter Property="WindowChrome.WindowChrome">
                <Setter.Value>
                    <WindowChrome CaptionHeight="0" ResizeBorderThickness="0"/>
                </Setter.Value>
            </Setter>
        </Style>
    </Window.Resources>
    <Grid>
        <StackPanel VerticalAlignment="Center" HorizontalAlignment="Center">
            <Viewbox Width="80" Height="80" Margin="0,0,0,20">
                <Path Data="{ICON_LOCK}" Fill="#e74c3c" Stretch="Uniform">
                    <Path.Effect><DropShadowEffect BlurRadius="20" ShadowDepth="0" Opacity="0.8" Color="#e74c3c"/></Path.Effect>
                </Path>
            </Viewbox>
            <TextBlock Text="Zařízení je zamčeno" Foreground="White" FontSize="36" FontWeight="Bold" 
                       HorizontalAlignment="Center" FontFamily="Segoe UI">
                <TextBlock.Effect><DropShadowEffect BlurRadius="10" ShadowDepth="0" Opacity="0.5" Color="Black"/></TextBlock.Effect>
            </TextBlock>
            <TextBlock Text="{escaped_msg}" Foreground="#aaaaaa" FontSize="18" 
                       HorizontalAlignment="Center" Margin="0,20,0,0" TextWrapping="Wrap" MaxWidth="600" TextAlignment="Center"/>
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Center" Margin="0,40,0,0" Opacity="0.5">
                <Viewbox Width="20" Height="20" Margin="0,0,8,0">
                    <Path Data="{ICON_EYE}" Fill="#6366f1" Stretch="Uniform"/>
                </Viewbox>
                <TextBlock Text="FamilyEye" Foreground="#6366f1" FontSize="14" FontWeight="SemiBold" VerticalAlignment="Center"/>
            </StackPanel>
        </StackPanel>
    </Grid>
</Window>
"@

$reader = (New-Object System.Xml.XmlNodeReader $xaml)
$window = [Windows.Markup.XamlReader]::Load($reader)

# Block Alt+F4
$window.Add_KeyDown({{
    if ($_.Key -eq 'System' -and $_.SystemKey -eq 'F4') {{
        $_.Handled = $true
    }}
}})

# Block closing
$window.Add_Closing({{
    $_.Cancel = $true
}})

$window.ShowDialog() | Out-Null
'''
        _run_powershell_async(ps_script, self._log)
        self._log("Lock screen shown")
    
    def show_countdown(self, seconds: int, reason: str):
        """Show countdown overlay before shutdown/lock.
        
        Displays a countdown timer with the reason for shutdown.
        """
        escaped_reason = _escape_xaml(reason)
        
        ps_script = f'''
try {{
    Add-Type -AssemblyName PresentationFramework
    Add-Type -AssemblyName System.Windows.Forms

    $countdownSeconds = {seconds}

    [xml]$xaml = @"
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        Title="FamilyEye" Height="300" Width="500" WindowStyle="None" ResizeMode="NoResize"
        AllowsTransparency="True" Background="Transparent" Topmost="True" WindowStartupLocation="CenterScreen">
    <Border CornerRadius="16" Background="#1a1a2e" BorderBrush="#e74c3c" BorderThickness="3">
        <Border.Effect><DropShadowEffect BlurRadius="30" ShadowDepth="0" Opacity="0.7" Color="Black"/></Border.Effect>
        <Grid Margin="30">
            <Grid.RowDefinitions>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="*"/>
                <RowDefinition Height="Auto"/>
            </Grid.RowDefinitions>
            <StackPanel Orientation="Horizontal" HorizontalAlignment="Center">
                <Viewbox Width="36" Height="36" Margin="0,0,12,0">
                    <Path Data="{ICON_CLOCK}" Fill="#e74c3c" Stretch="Uniform"/>
                </Viewbox>
                <TextBlock Text="{escaped_reason}" Foreground="White" FontSize="22" FontWeight="SemiBold" VerticalAlignment="Center"/>
            </StackPanel>
            <StackPanel Grid.Row="1" VerticalAlignment="Center" HorizontalAlignment="Center">
                <TextBlock x:Name="CountdownText" Text="{seconds}" Foreground="#e74c3c" FontSize="72" FontWeight="Bold" HorizontalAlignment="Center">
                    <TextBlock.Effect><DropShadowEffect BlurRadius="15" ShadowDepth="0" Opacity="0.5" Color="#e74c3c"/></TextBlock.Effect>
                </TextBlock>
                <TextBlock Text="sekund" Foreground="#888888" FontSize="16" HorizontalAlignment="Center"/>
            </StackPanel>
            <TextBlock Grid.Row="2" Text="Ulož si práci!" Foreground="#f1c40f" FontSize="14" HorizontalAlignment="Center" FontWeight="SemiBold"/>
        </Grid>
    </Border>
</Window>
"@

    $reader = (New-Object System.Xml.XmlNodeReader $xaml)
    $window = [Windows.Markup.XamlReader]::Load($reader)
    $countdownText = $window.FindName("CountdownText")

    # Create timer for countdown
    $timer = New-Object System.Windows.Threading.DispatcherTimer
    $timer.Interval = [TimeSpan]::FromSeconds(1)
    $script:remaining = $countdownSeconds

    $timer.Add_Tick({{
        $script:remaining--
        $countdownText.Text = $script:remaining.ToString()
        if ($script:remaining -le 0) {{
            $timer.Stop()
            $window.Close()
        }}
    }})

    $timer.Start()
    $window.ShowDialog() | Out-Null
    exit 0
}} catch {{
    Write-Error $_
    exit 1
}}
'''
        _run_powershell_async(ps_script, self._log)
        self._log(f"Countdown shown: {seconds}s - {reason}")
    
    def hide_lock_screen(self):
        """Hide the lock screen overlay.
        
        Note: This kills the PowerShell process running the lock screen.
        """
        if not self._lock_screen_active:
            return
        
        # Kill any PowerShell processes running lock screens
        ps_script = '''
Get-Process powershell | Where-Object { $_.MainWindowTitle -like "*FamilyEye Lock*" } | Stop-Process -Force -ErrorAction SilentlyContinue
'''
        _run_powershell_async(ps_script, self._log)
        self._lock_screen_active = False
        self._log("Lock screen hidden")


# Convenience functions matching NotificationManager interface
def create_ui_overlay():
    """Create a new UI overlay instance."""
    return UIOverlay()
