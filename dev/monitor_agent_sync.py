#!/usr/bin/env python3
"""
Real-time Agent Monitoring Tool
Monitors time sync, usage tracking, and reporting.
"""
import time
import os
import re
from datetime import datetime
from collections import deque

# Configuration
LOG_FILE = r"C:\ProgramData\FamilyEye\Agent\Logs\service_core.log"
TAIL_LINES = 50

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def parse_log_line(line):
    """Extract timestamp and message from log line."""
    # Format: [2026-01-07 10:31:54,609] INFO - [2026-01-07 10:31:54] [COMPONENT] LEVEL message
    match = re.match(r'\[([^\]]+)\]\s+(\w+)\s+-\s+.*?\[([^\]]+)\]\s+\[([^\]]+)\]\s+(\w+)\s+(.*)', line)
    if match:
        return {
            'timestamp': match.group(1),
            'log_level': match.group(2),
            'component': match.group(4),
            'message': match.group(6).strip()
        }
    return None

def monitor_agent():
    """Monitor agent logs in real-time."""
    print(f"{Colors.HEADER}{Colors.BOLD}╔════════════════════════════════════════════════════════════════╗{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}║        FamilyEye Agent - Real-Time Monitor                     ║{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}╚════════════════════════════════════════════════════════════════╝{Colors.ENDC}")
    print()
    
    # Track statistics
    stats = {
        'time_syncs': 0,
        'usage_reports': 0,
        'errors': 0,
        'last_sync_time': None,
        'last_report_time': None
    }
    
    # Recent events buffer
    recent_events = deque(maxlen=10)
    
    if not os.path.exists(LOG_FILE):
        print(f"{Colors.FAIL}ERROR: Log file not found: {LOG_FILE}{Colors.ENDC}")
        return
    
    # Get file size to start from end
    with open(LOG_FILE, 'r', encoding='utf-8', errors='ignore') as f:
        f.seek(0, 2)  # Go to end
        file_size = f.tell()
        
        print(f"{Colors.OKCYAN}📡 Monitoring started at {datetime.now().strftime('%H:%M:%S')}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}📂 Log file: {LOG_FILE}{Colors.ENDC}")
        print()
        print(f"{Colors.BOLD}{'─' * 64}{Colors.ENDC}")
        print()
        
        try:
            while True:
                current_size = os.path.getsize(LOG_FILE)
                
                if current_size > file_size:
                    f.seek(file_size)
                    new_lines = f.readlines()
                    file_size = current_size
                    
                    for line in new_lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        parsed = parse_log_line(line)
                        if not parsed:
                            continue
                        
                        # Track statistics
                        msg = parsed['message']
                        component = parsed['component']
                        
                        display_line = False
                        color = ''
                        icon = ''
                        
                        # Time Sync
                        if 'Time synced' in msg:
                            stats['time_syncs'] += 1
                            stats['last_sync_time'] = parsed['timestamp']
                            display_line = True
                            color = Colors.OKGREEN
                            icon = '⏰'
                            
                        # Usage Reports
                        elif 'Usage report sent successfully' in msg:
                            stats['usage_reports'] += 1
                            stats['last_report_time'] = parsed['timestamp']
                            display_line = True
                            color = Colors.OKBLUE
                            icon = '📤'
                            
                        # Network issues
                        elif 'Network connection lost' in msg or 'offline' in msg.lower():
                            display_line = True
                            color = Colors.WARNING
                            icon = '⚠️'
                            
                        # Errors
                        elif parsed['log_level'] in ['ERROR', 'CRITICAL']:
                            stats['errors'] += 1
                            display_line = True
                            color = Colors.FAIL
                            icon = '❌'
                            
                        # Application monitoring
                        elif component == 'MONITOR' and 'Monitoring' in msg:
                            display_line = True
                            color = Colors.OKCYAN
                            icon = '👁️'
                        
                        if display_line:
                            event = f"{color}{icon} [{parsed['timestamp'].split()[1]}] [{component}] {msg}{Colors.ENDC}"
                            recent_events.append(event)
                            print(event)
                        
                        # Update stats display
                        if display_line and stats['time_syncs'] > 0:
                            print()
                            print(f"{Colors.BOLD}Statistics:{Colors.ENDC}")
                            print(f"  Time Syncs: {Colors.OKGREEN}{stats['time_syncs']}{Colors.ENDC} | Last: {stats['last_sync_time'] or 'N/A'}")
                            print(f"  Reports: {Colors.OKBLUE}{stats['usage_reports']}{Colors.ENDC} | Last: {stats['last_report_time'] or 'N/A'}")
                            print(f"  Errors: {Colors.FAIL if stats['errors'] > 0 else Colors.OKGREEN}{stats['errors']}{Colors.ENDC}")
                            print(f"{Colors.BOLD}{'─' * 64}{Colors.ENDC}")
                            print()
                
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            print()
            print(f"{Colors.WARNING}Monitoring stopped by user{Colors.ENDC}")
            print()
            print(f"{Colors.BOLD}Final Statistics:{Colors.ENDC}")
            print(f"  Total Time Syncs: {stats['time_syncs']}")
            print(f"  Total Reports: {stats['usage_reports']}")
            print(f"  Total Errors: {stats['errors']}")

if __name__ == "__main__":
    monitor_agent()
