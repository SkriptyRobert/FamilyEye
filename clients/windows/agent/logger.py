"""Enterprise-grade logging system for Parental Control Agent."""
import logging
import sys
from datetime import datetime
from typing import Optional
import colorama
from colorama import Fore, Style, Back

# Initialize colorama for Windows
colorama.init(autoreset=True)


class EnterpriseLogger:
    """Professional logging with colors, timestamps, and structured output."""
    
    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    # Component colors
    COMPONENT_COLORS = {
        'MAIN': Fore.CYAN,
        'MONITOR': Fore.GREEN,
        'ENFORCER': Fore.YELLOW,
        'REPORTER': Fore.MAGENTA,
        'NETWORK': Fore.BLUE,
        'VALIDATE': Fore.WHITE + Style.BRIGHT,
        'CONFIG': Fore.WHITE,
    }
    
    # Level colors
    LEVEL_COLORS = {
        'DEBUG': Fore.WHITE + Style.DIM,
        'INFO': Fore.WHITE,
        'WARNING': Fore.YELLOW + Style.BRIGHT,
        'ERROR': Fore.RED + Style.BRIGHT,
        'CRITICAL': Fore.RED + Back.WHITE + Style.BRIGHT,
        'SUCCESS': Fore.GREEN + Style.BRIGHT,
    }
    
    def __init__(self, component: str = 'MAIN', level: int = logging.INFO):
        self.component = component.upper()
        self.component_color = self.COMPONENT_COLORS.get(self.component, Fore.WHITE)
        self.level = level
        
        # Setup logging
        self.logger = logging.getLogger(f"ParentalControl.{self.component}")
        self.logger.setLevel(level)
        
        # Console handler with custom format
        if not self.logger.handlers:
            # Console
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
            
            # File logging
            try:
                import os
                # Get root dir (next to the executable when frozen, or next to main.py when scripts)
                if getattr(sys, 'frozen', False):
                    # Running as compiled exe
                    # Use ProgramData for logging to avoid permission issues
                    program_data = os.environ.get('ProgramData', 'C:\\ProgramData')
                    log_dir = os.path.join(program_data, 'FamilyEye', 'Agent')
                else:
                    # Dev mode
                    log_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                
                os.makedirs(log_dir, exist_ok=True)
                log_path = os.path.join(log_dir, 'agent.log')
                file_handler = logging.FileHandler(log_path, encoding='utf-8')
                file_handler.setLevel(level)
                file_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                # Silently fail if log cannot be created, but print to stderr
                sys.stderr.write(f"Logger error: {e}\n")
    
    def _format_message(self, level: str, message: str, extra: Optional[dict] = None) -> str:
        """Format log message with timestamp, component, and colors."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level_color = self.LEVEL_COLORS.get(level, Fore.WHITE)
        
        # Build message parts
        parts = [
            f"{Fore.WHITE + Style.DIM}[{timestamp}]{Style.RESET_ALL}",
            f"{self.component_color}[{self.component}]{Style.RESET_ALL}",
            f"{level_color}{level:8s}{Style.RESET_ALL}",
            message
        ]
        
        # Add extra info if provided
        if extra:
            extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
            if extra_str:
                parts.append(f"{Fore.WHITE + Style.DIM}({extra_str}){Style.RESET_ALL}")
        
        return " ".join(parts)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        if self.level <= logging.DEBUG:
            formatted = self._format_message('DEBUG', message, kwargs if kwargs else None)
            self.logger.debug(formatted)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        if self.level <= logging.INFO:
            formatted = self._format_message('INFO', message, kwargs if kwargs else None)
            self.logger.info(formatted)
    
    def success(self, message: str, **kwargs):
        """Log success message."""
        if self.level <= logging.INFO:
            formatted = self._format_message('SUCCESS', message, kwargs if kwargs else None)
            self.logger.info(formatted)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        if self.level <= logging.WARNING:
            formatted = self._format_message('WARNING', message, kwargs if kwargs else None)
            self.logger.warning(formatted)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        if self.level <= logging.ERROR:
            formatted = self._format_message('ERROR', message, kwargs if kwargs else None)
            self.logger.error(formatted)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        if self.level <= logging.CRITICAL:
            formatted = self._format_message('CRITICAL', message, kwargs if kwargs else None)
            self.logger.critical(formatted)
    
    def section(self, title: str):
        """Print a section header."""
        width = 70
        border = "=" * width
        title_line = f"{title:^{width}}"
        print(f"\n{Fore.CYAN + Style.BRIGHT}{border}")
        print(f"{title_line}")
        print(f"{border}{Style.RESET_ALL}\n")
    
    def separator(self):
        """Print a separator line."""
        print(f"{Fore.WHITE + Style.DIM}{'-' * 70}{Style.RESET_ALL}")


# Global logger instances for each component
def get_logger(component: str) -> EnterpriseLogger:
    """Get logger instance for component."""
    return EnterpriseLogger(component=component, level=logging.INFO)

