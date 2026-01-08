"""System noise filtering for Windows 10/11.

This module provides a modular filter for low-level system processes
that should never be tracked or shown to parents.
"""

import os


class SystemNoiseFilter:
    """
    Filters out low-level system noise (kernel processes, services, drivers).
    
    Goal: Don't send data to backend about processes the user never consciously started.
    This keeps the dashboard clean and focused on actual user activity.
    """

    def __init__(self):
        # Processes that are purely system-level and have no UI relevance for parents
        self._system_noise_set = {
            # ===== Kernel & Core System =====
            'idle', 'system', 'registry', 'smss', 'csrss', 'wininit', 'services', 
            'lsass', 'svchost', 'fontdrvhost', 'winlogon', 'spoolsv', 'dwm', 
            'memcompression', 'audiodg', 'werfault', 'wermgr', 'lsaiso',
            
            # ===== Windows 10/11 Modern Core =====
            'sihost', 'dashost', 'taskhostw', 'ctfmon', 'dllhost', 'conhost',
            'runtimebroker', 'shellexperiencehost', 'startmenuexperiencehost',
            'searchhost', 'searchindexer', 'searchapp', 'applicationframehost',
            'systemsettings', 'lockapp', 'smartscreen', 'useroobebroker',
            'textinputhost', 'inputpersonalization',
            
            # ===== Windows Update & Telemetry =====
            'musnotification', 'musnotifyicon', 'devicecensus', 'compattelrunner',
            'wuauclt', 'tiworker', 'trustedinstaller', 'msiexec',
            
            # ===== Services & Helpers =====
            'backgroundtaskhost', 'taskmgr', 'mmc', 'regedit',
            'mobsync', 'hxtsr', 'runonce', 'wanservice', 'utsvcs',
            'securityhealthsystray', 'securityhealthservice',
            
            # ===== Windows UI / Widgets (Win11) =====
            'widgets', 'widgetservice', 'phoneexperiencehost', 'yourphone',
            
            # ===== Xbox Game Bar (visible but not "app usage") =====
            'gamebar', 'gamebarftserver', 'xboxgamebar', 'gamebarpresencewriter',
            'gamelaunchhelper',
            
            # ===== OneDrive (background sync, not direct usage) =====
            'onedrive', 'onedrivesetup', 'filesyncshell64',
            
            # ===== Explorer & Shell =====
            'explorer',  # Explorer itself should not count as "app time"
            
            # ===== Hardware Drivers & GPU =====
            'nvidia share', 'nvcontainer', 'nvdisplay.container', 'nvspcaps64',
            'nvbackend', 'nvtelemetrycontainer',
            'amdow', 'radeonsoftware', 'atieclxx', 'atiesrxx',
            'igfxem', 'igfxtray', 'hkcmd',  # Intel graphics
            
            # ===== Audio Drivers =====
            'realtek', 'ravbg64', 'rtkaudioservice', 'dolbydam',
            
            # ===== Peripheral Software (mice, keyboards) =====
            'lghub', 'lghub_agent', 'lghub_updater',  # Logitech
            'razer synapse', 'rzsdkservice', 'razercentral',  # Razer
            'corsair.service', 'icue',  # Corsair
            'steelseries', 'ssenginenetwork',  # SteelSeries
            'armoury crate', 'asus_framework', 'asusoptimization',  # ASUS
            
            # ===== Antivirus & Security (background) =====
            'msmpeng', 'mpcmdrun', 'nissrv',  # Windows Defender
            'avgui', 'avgsvc', 'avastsvc',  # AVG/Avast
            'egui', 'ekrn',  # ESET
        }
        
        # Whitelist for System32 binaries that ARE relevant (CLI tools)
        self._system32_whitelist = {
            'cmd', 'powershell', 'pwsh', 'windowsterminal',
            'notepad', 'mspaint', 'calc', 'snippingtool',
        }
        
        # Substrings that indicate helper/background processes
        self._noise_substrings = (
            'crashpad', 'crashhandler', 'errorreporter',
            'updater', 'update_notifier',
            '_helper', 'helper64', 'helperservice',
            'webview2', 'cefsubprocess',
            'broker', 'host64',
        )

    def is_noise(self, process_name: str, process_path: str = None) -> bool:
        """
        Determine if a process is system noise that should be filtered.
        
        Args:
            process_name: The process executable name (e.g., 'chrome.exe')
            process_path: Optional full path to the executable
            
        Returns:
            True if the process is noise and should be ignored
        """
        if not process_name:
            return True
            
        name_clean = process_name.lower().replace('.exe', '').strip()
        
        # 1. Fast check: exact match in noise set
        if name_clean in self._system_noise_set:
            return True

        # 2. Substring check for helpers/crashpads
        for substring in self._noise_substrings:
            if substring in name_clean:
                return True

        # 3. System32/SysWOW64 heuristic (unless whitelisted)
        if process_path:
            path_lower = process_path.lower()
            if 'windows\\system32' in path_lower or 'windows\\syswow64' in path_lower:
                if name_clean not in self._system32_whitelist:
                    return True

        return False
    
    def is_cli_tool(self, process_name: str) -> bool:
        """Check if process is a CLI tool (terminal, shell, etc.)."""
        name_clean = process_name.lower().replace('.exe', '').strip()
        return name_clean in self._system32_whitelist


# Singleton instance for easy import
system_noise_filter = SystemNoiseFilter()
