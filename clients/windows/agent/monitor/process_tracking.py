"""Process identification and tracking logic."""
import os
import psutil
from typing import Dict, Set, Optional, List
from ..logger import get_logger

class ProcessTracker:
    """Handles process identification and metadata."""
    
    # CLI Tools - Applications without windows that developers/users use
    CLI_TOOLS = {
        'cmd', 'powershell', 'pwsh', 'windowsterminal', 
        'python', 'pythonw', 'py', 
        'node', 'npm', 'git', 'java', 'javac',
        'code', 'cursor', 'vim', 'nvim',
        'ssh', 'ftp', 'bash', 'wsl'
    }

    # Helper processes to consolidate under main app
    HELPER_TO_MAIN = {
        'steamwebhelper': 'steam',
        'steamservice': 'steam',
        'discordptb': 'discord',
        'discordcanary': 'discord',
        'discord_voice': 'discord',
        'chromedriver': 'chrome',
        'chrome_crashpad': 'chrome',
        'msedgewebview2': 'msedge',
        'firefoxprivatebridge': 'firefox',
        'epicwebhelper': 'epicgameslauncher',
        'riotclientservices': 'riotclient',
        'leagueclientux': 'leagueclient',
        'battlenet_helper': 'battle.net',
    }

    # Ignored system processes
    IGNORED_PROCESSES = {
        'idle', 'system', 'registry', 'smss', 'csrss', 'wininit', 'services', 'lsass',
        'svchost', 'fontdrvhost', 'winlogon', 'spoolsv', 'dwm', 'ctfmon', 'taskhostw',
        'shellexperiencehost', 'searchhost', 'startmenuexperiencehost', 'userinit',
        'identityhost', 'backgroundtaskhost', 'mobsync', 'hxtsr', 'runonce', 'smartscreen',
        'onedrive', 'taskmgr', 'mmc', 'regedit', 'cmd', 'runtime', 'runtimebroker',
        'applicationframehost', 'textinputhost', 'lockapp', 'securityhealthsystray',
        'phoneexperiencehost', 'searchapp', 'widgets', 'audiodg', 'spoolsv',
        'dllhost', 'conhost', 'sihost', 'dashost' 
    }
    
    IGNORED_WINDOWS = IGNORED_PROCESSES
    
    def __init__(self):
        self.logger = get_logger("monitor.process")
        self.metadata_cache: Dict[str, str] = {} # path -> original_filename
        
    def get_original_filename(self, path: str) -> Optional[str]:
        """Read 'OriginalFilename' from PE metadata of an executable."""
        if not path or not os.path.exists(path):
            return None
        
        if path in self.metadata_cache:
            return self.metadata_cache[path]
            
        try:
            import win32api
            # Try to get language and codepage
            try:
                lang, codepage = win32api.GetFileVersionInfo(path, '\\VarFileInfo\\Translation')[0]
                str_info = u'\\StringFileInfo\\%04X%04X\\OriginalFilename' % (lang, codepage)
                orig_name = win32api.GetFileVersionInfo(path, str_info)
                if orig_name:
                    if orig_name.lower().endswith('.exe'):
                        orig_name = orig_name[:-4]
                    res = orig_name.lower()
                    self.metadata_cache[path] = res
                    return res
            except Exception:
                pass
                
            # Default fallbacks or if above fails
            name = os.path.basename(path).lower()
            if name.endswith('.exe'): name = name[:-4]
            self.metadata_cache[path] = name
            return name
        except Exception:
            return None
            
    def get_app_name(self, proc: psutil.Process) -> Optional[str]:
        """Get application name from process, consolidating helpers to main app."""
        try:
            name = proc.name()
            if name.endswith('.exe'):
                name = name[:-4]
            name = name.lower()
            
            # 1. First check explicit mapping for known apps
            if name in self.HELPER_TO_MAIN:
                return self.HELPER_TO_MAIN[name]
            
            # 2. Auto-detect helper processes by common suffixes
            helper_suffixes = [
                'webhelper', 'helper', 'service', 'launcher', 'crashpad',
                'webview', 'renderer', 'gpu', 'utility', 'broker',
                'updater', 'update', 'tray', 'agent', 'daemon',
                'background', 'worker', 'child', 'subprocess'
            ]
            
            for suffix in helper_suffixes:
                if name.endswith(suffix) and len(name) > len(suffix):
                    main_name = name[:-len(suffix)]
                    if len(main_name) >= 3:
                        return main_name
            
            # 3. Handle numbered suffixes like 'chrome32', 'discord64'
            import re
            match = re.match(r'^(.+?)(32|64|x86|x64)$', name)
            if match:
                return match.group(1)
            
            return name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
            
    def is_ignored(self, app_name: str) -> bool:
        """Check if process should be ignored."""
        return app_name in self.IGNORED_PROCESSES or app_name in self.IGNORED_WINDOWS
        
    def is_cli_tool(self, app_name: str) -> bool:
        """Check if app is a known CLI tool."""
        return app_name in self.CLI_TOOLS
