"""Skript pro zobrazení využití resources jednotlivých komponent."""
import psutil
import os
import sys
import json
from collections import defaultdict
from typing import Dict, List, Tuple
import time

# Nastavení UTF-8 pro Windows konzoli
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def format_bytes(bytes_value: int) -> str:
    """Formátuje bajty do čitelného formátu."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} TB"

def find_processes_by_port(port: int) -> List[psutil.Process]:
    """Najde procesy, které naslouchají na daném portu."""
    found = []
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.laddr.port == port:
                try:
                    proc = psutil.Process(conn.pid)
                    found.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
    except (psutil.AccessDenied, Exception):
        pass
    return found

def find_listening_ports_for_project(project_path: str) -> Dict[int, List[psutil.Process]]:
    """Najde všechny porty, na kterých naslouchají procesy z projektu."""
    project_path = os.path.normpath(project_path).lower()
    ports_with_processes = {}
    
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN' and conn.pid:
                try:
                    proc = psutil.Process(conn.pid)
                    cmdline = ' '.join(proc.cmdline() or []).lower()
                    exe = (proc.exe() or '').lower()
                    cwd = ''
                    try:
                        cwd = (proc.cwd() or '').lower()
                    except:
                        pass
                    
                    # Check if process belongs to project
                    all_paths = [cmdline, exe, cwd]
                    if any(project_path in p for p in all_paths if p):
                        port = conn.laddr.port
                        if port not in ports_with_processes:
                            ports_with_processes[port] = []
                        if proc not in ports_with_processes[port]:
                            ports_with_processes[port].append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
    except (psutil.AccessDenied, Exception):
        pass
    
    return ports_with_processes


def find_processes_by_keywords(keywords: List[str], exclude_keywords: List[str] = None, project_path: str = None, path_filter: str = None, port: int = None) -> List[psutil.Process]:
    """Najde procesy podle klíčových slov v názvu nebo příkazové řádce."""
    if exclude_keywords is None:
        exclude_keywords = []
    
    # Získej absolutní cestu k projektu
    if project_path is None:
        project_path = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.normpath(project_path).lower()
    
    if path_filter:
        path_filter = os.path.normpath(path_filter).lower()
    
    found = []
    found_pids = set()  # Pro sledování duplikátů podle PID
    
    # Pokud je zadán port, přidej procesy z tohoto portu
    if port:
        port_processes = find_processes_by_port(port)
        for proc in port_processes:
            try:
                if proc.pid not in found_pids:
                    found.append(proc)
                    found_pids.add(proc.pid)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'exe', 'cwd']):
        try:
            proc_info = proc.info
            name = proc_info.get('name', '').lower()
            cmdline_list = proc_info.get('cmdline') or []
            cmdline = ' '.join(cmdline_list).lower() if cmdline_list else ''
            exe = proc_info.get('exe', '').lower() if proc_info.get('exe') else ''
            cwd = proc_info.get('cwd', '').lower() if proc_info.get('cwd') else ''
            
            # Zkontroluj, zda proces patří k projektu a konkrétní komponentě
            all_paths = [exe, cwd, cmdline] + [p.lower() for p in cmdline_list if p]
            belongs_to_project = any(project_path in p for p in all_paths if p)
            belongs_to_component = True
            if path_filter:
                belongs_to_component = any(path_filter in p for p in all_paths if p)
            
            # Zkontroluj exclude keywords
            should_exclude = False
            for exclude in exclude_keywords:
                if exclude.lower() in name or exclude.lower() in cmdline or exclude.lower() in exe:
                    should_exclude = True
                    break
            if should_exclude:
                continue
            
            # Zkontroluj keywords - musí být v cmdline nebo exe a patřit k projektu/komponentě
            for keyword in keywords:
                keyword_lower = keyword.lower()
                if (keyword_lower in name or keyword_lower in cmdline or keyword_lower in exe):
                    if belongs_to_project and belongs_to_component:
                        # Přidej pouze pokud ještě není v seznamu (podle PID)
                        if proc.pid not in found_pids:
                            found.append(proc)
                            found_pids.add(proc.pid)
                        break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return found

def get_process_resources(proc: psutil.Process) -> Dict:
    """Získá informace o využití resources pro proces."""
    try:
        cpu_percent = proc.cpu_percent(interval=0.1)
        memory_info = proc.memory_info()
        memory_percent = proc.memory_percent()
        
        # Získej příkazovou řádku
        try:
            cmdline = ' '.join(proc.cmdline()[:3])  # První 3 části
            if len(proc.cmdline()) > 3:
                cmdline += '...'
        except:
            cmdline = proc.name()
        
        return {
            'pid': proc.pid,
            'name': proc.name(),
            'cmdline': cmdline,
            'cpu_percent': cpu_percent,
            'memory_bytes': memory_info.rss,
            'memory_percent': memory_percent
        }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_component_stats(component_name: str, keywords: List[str], exclude_keywords: List[str] = None, project_path: str = None, path_filter: str = None, port: int = None) -> Dict:
    """Získá statistiky pro komponentu."""
    processes = find_processes_by_keywords(keywords, exclude_keywords, project_path, path_filter, port)
    
    if not processes:
        return {
            'name': component_name,
            'processes': [],
            'total_cpu': 0.0,
            'total_memory_bytes': 0,
            'total_memory_percent': 0.0,
            'count': 0
        }
    
    total_cpu = 0.0
    total_memory_bytes = 0
    total_memory_percent = 0.0
    process_details = []
    
    for proc in processes:
        try:
            resources = get_process_resources(proc)
            if resources:
                total_cpu += resources['cpu_percent']
                total_memory_bytes += resources['memory_bytes']
                total_memory_percent += resources['memory_percent']
                process_details.append(resources)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return {
        'name': component_name,
        'processes': process_details,
        'total_cpu': total_cpu,
        'total_memory_bytes': total_memory_bytes,
        'total_memory_percent': total_memory_percent,
        'count': len(process_details)
    }

def draw_bar(value: float, max_value: float, width: int = 50, char: str = '█') -> str:
    """Vykreslí textový bar."""
    if max_value == 0:
        return ' ' * width
    filled = int((value / max_value) * width)
    return char * filled + ' ' * (width - filled)

def generate_html_report(all_stats: List[Dict], total_cpu: float, total_memory_bytes: int, 
                        total_memory_percent: float, total_processes: int, distribution: List[Dict],
                        cpu_count: int, total_memory: int, available_memory: int, system_cpu_percent: float):
    """Vygeneruje HTML report s vizualizací."""
    # Escape CSS závorky pro .format()
    html_template_raw = """<!DOCTYPE html>
<html lang="cs">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoring Resources - Parental Control System</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            padding: 30px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .timestamp {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 0.9em;
        }
        .system-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 30px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
        .system-info-item {
            text-align: center;
        }
        .system-info-item strong {
            display: block;
            color: #667eea;
            font-size: 1.2em;
            margin-bottom: 5px;
        }
        .component {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 25px;
            border-left: 5px solid #667eea;
        }
        .component-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .component-name {
            font-size: 1.8em;
            color: #333;
            font-weight: bold;
        }
        .component-status {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .status-running {
            background: #d4edda;
            color: #155724;
        }
        .status-stopped {
            background: #f8d7da;
            color: #721c24;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .stat-label {
            color: #666;
            font-size: 0.9em;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #333;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e9ecef;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
            position: relative;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #2d3748 0%, #1a202c 100%);
            min-width: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.85em;
            box-shadow: 0 2px 4px rgba(0,0,0,0.3);
            border-right: 2px solid rgba(255,255,255,0.1);
        }
        .progress-fill[data-value="0"] {
            background: #cbd5e0;
            color: #4a5568;
            min-width: 0px;
        }
        .progress-bar {
            position: relative;
        }
        .progress-bar::after {
            content: attr(data-label);
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.85em;
            color: #666;
            font-weight: 600;
        }
        .process-details {
            margin-top: 20px;
        }
        .process-details h3 {
            color: #333;
            margin-bottom: 15px;
            font-size: 1.2em;
        }
        .process-table {
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }
        .process-table th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }
        .process-table td {
            padding: 10px 12px;
            border-bottom: 1px solid #e9ecef;
        }
        .process-table tr:hover {
            background: #f8f9fa;
        }
        .summary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-top: 30px;
        }
        .summary h2 {
            margin-bottom: 20px;
            font-size: 2em;
        }
        .summary-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }
        .summary-stat {
            background: rgba(255,255,255,0.2);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        .summary-stat-label {
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 8px;
        }
        .summary-stat-value {
            font-size: 2em;
            font-weight: bold;
        }
        .distribution {
            margin-top: 25px;
        }
        .distribution h3 {
            margin-bottom: 15px;
        }
        .distribution-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .distribution-name {
            font-weight: 600;
        }
        .distribution-values {
            display: flex;
            gap: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Monitoring Využití Resources</h1>
        <div class="timestamp">Čas: {timestamp}</div>
        
        <div class="system-info">
            <div class="system-info-item">
                <strong>{cpu_cores}</strong>
                <span>CPU Jader</span>
            </div>
            <div class="system-info-item">
                <strong>{total_memory}</strong>
                <span>Celková Paměť</span>
            </div>
            <div class="system-info-item">
                <strong>{available_memory}</strong>
                <span>Dostupná Paměť</span>
            </div>
            <div class="system-info-item">
                <strong>{system_usage}%</strong>
                <span>Využití Systému</span>
            </div>
        </div>

        {components_html}

        <div class="summary">
            <h2>Využití Řešení (Frontend + Backend + Agent)</h2>
            <div class="summary-stats">
                <div class="summary-stat">
                    <div class="summary-stat-label">Počet procesů řešení</div>
                    <div class="summary-stat-value">{total_processes}</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">CPU řešení</div>
                    <div class="summary-stat-value">{total_cpu}%</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">Paměť řešení</div>
                    <div class="summary-stat-value">{total_memory_summary}</div>
                </div>
            </div>
            <div class="distribution">
                <h3>Rozdělení podle komponent</h3>
                {distribution_html}
            </div>
        </div>
        
        <div class="summary" style="margin-top: 30px; background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);">
            <h2>Celkové Využití Systému (PC)</h2>
            <div class="summary-stats">
                <div class="summary-stat">
                    <div class="summary-stat-label">Celkové CPU systému</div>
                    <div class="summary-stat-value">{system_cpu}%</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">Celková paměť systému</div>
                    <div class="summary-stat-value">{system_memory_used}</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-label">Využití paměti systému</div>
                    <div class="summary-stat-value">{system_memory_percent}%</div>
                </div>
            </div>
            <div style="margin-top: 20px; padding: 15px; background: rgba(255,255,255,0.1); border-radius: 8px;">
                <div style="margin-bottom: 10px;"><strong>Podíl řešení na systému:</strong></div>
                <div style="margin-bottom: 5px;">CPU řešení: {total_cpu}% z celkového CPU systému ({system_cpu}%)</div>
                <div>Paměť řešení: {solution_memory_share}% z celkové paměti systému ({system_memory_percent}% využíváno)</div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    # Generuj HTML pro komponenty
    components_html = ""
    for stats in all_stats:
        is_running = stats['count'] > 0
        status_class = 'status-running' if is_running else 'status-stopped'
        status_text = 'SPUŠTĚNO' if is_running else 'NENÍ SPUŠTĚNO'
        
        if is_running:
            processes_html = ""
            if stats['processes']:
                process_rows = []
                for p in stats['processes']:
                    cmdline_short = p['cmdline'][:60]
                    if len(p['cmdline']) > 60:
                        cmdline_short += '...'
                    process_rows.append(f"""
                            <tr>
                                <td>{p['pid']}</td>
                                <td>{p['cpu_percent']:.2f}%</td>
                                <td>{format_bytes(p['memory_bytes'])}</td>
                                <td>{cmdline_short}</td>
                            </tr>
                            """)
                processes_html = f"""
                <div class="process-details">
                    <h3>Detail procesů</h3>
                    <table class="process-table">
                        <thead>
                            <tr>
                                <th>PID</th>
                                <th>CPU</th>
                                <th>Paměť</th>
                                <th>Příkaz</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(process_rows)}
                        </tbody>
                    </table>
                </div>
                """
            
            cpu_percent_str = f"{stats['total_cpu']:.2f}%"
            # Pro velmi malé hodnoty použij minimální šířku 2% pro viditelnost
            cpu_width = max(min(stats['total_cpu'], 100), 2.0) if stats['total_cpu'] > 0 else 0
            cpu_display = f"{stats['total_cpu']:.1f}%"
            mem_display = format_bytes(stats['total_memory_bytes'])
            # Pro velmi malé hodnoty použij minimální šířku 2% pro viditelnost
            mem_width = max(min(stats['total_memory_percent'], 100), 2.0) if stats['total_memory_percent'] > 0 else 0
            mem_display_pct = f"{stats['total_memory_percent']:.1f}%"
            
            # Pro velmi malé hodnoty použij tmavší barvu
            cpu_data_value = "0" if stats['total_cpu'] == 0 else "1"
            mem_data_value = "0" if stats['total_memory_percent'] == 0 else "1"
            
            component_html = f"""
            <div class="component">
                <div class="component-header">
                    <div class="component-name">{stats['name']}</div>
                    <div class="component-status {status_class}">{status_text}</div>
                </div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Počet procesů</div>
                        <div class="stat-value">{stats['count']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">CPU</div>
                        <div class="stat-value">{cpu_percent_str}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {cpu_width}%" data-value="{cpu_data_value}">
                                {cpu_display}
                            </div>
                        </div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Paměť</div>
                        <div class="stat-value">{mem_display}</div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: {mem_width}%" data-value="{mem_data_value}">
                                {mem_display_pct}
                            </div>
                        </div>
                    </div>
                </div>
                {processes_html}
            </div>
            """
        else:
            component_html = f"""
            <div class="component">
                <div class="component-header">
                    <div class="component-name">{stats['name']}</div>
                    <div class="component-status {status_class}">{status_text}</div>
                </div>
            </div>
            """
        
        components_html += component_html
    
    # Generuj HTML pro rozdělení
    distribution_html = ""
    for dist in distribution:
        cpu_share_str = f"{dist['cpu_share']:.1f}%"
        mem_share_str = f"{dist['memory_share']:.1f}%"
        distribution_html += f"""
        <div class="distribution-item">
            <div class="distribution-name">{dist['name']}</div>
            <div class="distribution-values">
                <span>CPU: {cpu_share_str}</span>
                <span>RAM: {mem_share_str}</span>
            </div>
        </div>
        """
    
    # Escape CSS závorky (kromě placeholders)
    # Nahradíme { a } v CSS za {{ a }}, ale ponecháme placeholdery {timestamp}, {cpu_cores}, atd.
    import re
    # Najdeme všechny placeholdery
    placeholders = ['timestamp', 'cpu_cores', 'total_memory', 'available_memory', 'system_usage',
                    'components_html', 'total_processes', 'total_cpu', 'total_memory_summary', 'distribution_html',
                    'system_cpu', 'system_memory_used', 'system_memory_percent', 'solution_cpu_share', 'solution_memory_share']
    # Escape všechny { a } kromě těch, které jsou placeholdery
    html_template = html_template_raw
    for placeholder in placeholders:
        html_template = html_template.replace(f'{{{placeholder}}}', f'__PLACEHOLDER_{placeholder}__')
    # Escape všechny zbývající { a }
    html_template = html_template.replace('{', '{{').replace('}', '}}')
    # Vrátíme placeholdery
    for placeholder in placeholders:
        html_template = html_template.replace(f'__PLACEHOLDER_{placeholder}__', f'{{{placeholder}}}')
    
    # Vypočítej systémové statistiky
    system_memory = psutil.virtual_memory()
    system_memory_used_bytes = system_memory.total - system_memory.available
    system_memory_percent = system_memory.percent
    
    # Vypočítej podíl řešení na systému
    # CPU: řešení využívá total_cpu% z celkového CPU, což je total_cpu/system_cpu_percent * 100 z celkového využití
    solution_cpu_share = (total_cpu / system_cpu_percent * 100) if system_cpu_percent > 0 else 0
    # Paměť: řešení využívá total_memory_bytes z celkové paměti systému
    solution_memory_share = (total_memory_bytes / system_memory.total * 100) if system_memory.total > 0 else 0
    
    # Naplň template
    html_content = html_template.format(
        timestamp=time.strftime('%Y-%m-%d %H:%M:%S'),
        cpu_cores=cpu_count,
        total_memory=format_bytes(total_memory),
        available_memory=format_bytes(available_memory),
        system_usage=system_memory_percent,
        components_html=components_html,
        total_processes=total_processes,
        total_cpu=f"{total_cpu:.2f}",
        total_memory_summary=format_bytes(total_memory_bytes),
        distribution_html=distribution_html,
        system_cpu=f"{system_cpu_percent:.2f}",
        system_memory_used=format_bytes(system_memory_used_bytes),
        system_memory_percent=f"{system_memory_percent:.2f}",
        solution_cpu_share=f"{solution_cpu_share:.2f}",
        solution_memory_share=f"{solution_memory_share:.2f}"
    )
    
    # Ulož HTML soubor
    html_path = os.path.join(os.path.dirname(__file__), 'resources_report.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"  HTML report vygenerován: {html_path}")

def print_component_stats(stats: Dict, max_cpu: float, max_memory: float):
    """Vytiskne statistiky komponenty."""
    print(f"\n{'='*70}")
    print(f"  {stats['name'].upper()}")
    print(f"{'='*70}")
    
    if stats['count'] == 0:
        print("  Status: NENÍ SPUŠTĚNO")
        return
    
    print(f"  Počet procesů: {stats['count']}")
    print(f"  CPU: {stats['total_cpu']:.2f}%")
    print(f"  {draw_bar(stats['total_cpu'], max_cpu)}")
    print(f"  Paměť: {format_bytes(stats['total_memory_bytes'])} ({stats['total_memory_percent']:.2f}%)")
    print(f"  {draw_bar(stats['total_memory_percent'], max_memory)}")
    
    if stats['processes']:
        print(f"\n  Detail procesů:")
        for proc in stats['processes']:
            print(f"    PID {proc['pid']:6d} | CPU: {proc['cpu_percent']:6.2f}% | "
                  f"RAM: {format_bytes(proc['memory_bytes']):>10s} | {proc['cmdline'][:60]}")

def main():
    """Hlavní funkce."""
    print("\n" + "="*70)
    print("  MONITORING VYUŽITÍ RESOURCES - PARENTAL CONTROL SYSTEM")
    print("="*70)
    print(f"  Čas: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Získej celkové systémové statistiky
    cpu_count = psutil.cpu_count()
    total_memory = psutil.virtual_memory().total
    available_memory = psutil.virtual_memory().available
    
    print(f"\n  Systémové informace:")
    print(f"    CPU jader: {cpu_count}")
    print(f"    Celková paměť: {format_bytes(total_memory)}")
    print(f"    Dostupné paměť: {format_bytes(available_memory)}")
    print(f"    Využití systému: {psutil.virtual_memory().percent:.1f}%")
    
    # Definice komponent s přesnějšími kritérii
    project_path = os.path.dirname(os.path.abspath(__file__))
    backend_path = os.path.join(project_path, 'backend').lower()
    agent_path = os.path.join(project_path, 'clients', 'windows').lower()
    frontend_path = os.path.join(project_path, 'frontend').lower()
    
    # Auto-detect listening ports for this project
    print(f"\n  Detekce aktivních portů projektu...")
    active_ports = find_listening_ports_for_project(project_path)
    if active_ports:
        print(f"    Nalezené porty: {list(active_ports.keys())}")
    else:
        print(f"    Žádné aktivní porty nenalezeny")
    
    # Determine which ports belong to which component based on process info
    frontend_ports = []
    backend_ports = []
    
    for port, procs in active_ports.items():
        for proc in procs:
            try:
                cmdline = ' '.join(proc.cmdline() or []).lower()
                exe = (proc.exe() or '').lower()
                
                # Check if it's frontend (vite, node with frontend path)
                if 'vite' in cmdline or (frontend_path in cmdline) or (frontend_path in exe):
                    if port not in frontend_ports:
                        frontend_ports.append(port)
                        print(f"    Port {port} -> Frontend (Vite)")
                # Check if it's backend (uvicorn, fastapi)
                elif 'uvicorn' in cmdline or 'app.main:app' in cmdline or (backend_path in cmdline):
                    if port not in backend_ports:
                        backend_ports.append(port)
                        print(f"    Port {port} -> Backend (Uvicorn)")
            except:
                continue
    
    components = [
        {
            'name': 'Frontend',
            'keywords': ['vite', 'node', 'esbuild'],
            'exclude': ['npm', 'yarn', 'pnpm'],
            'path_filter': frontend_path,
            'ports': frontend_ports  # Auto-detected ports
        },
        {
            'name': 'Backend',
            'keywords': ['uvicorn', 'run_server.py', 'app.main:app', 'fastapi'],
            'exclude': [],
            'path_filter': backend_path,
            'ports': backend_ports  # Auto-detected ports
        },
        {
            'name': 'Agent',
            'keywords': ['run_agent.py', 'agent\\main.py', 'agent\\monitor.py', 'agent\\enforcer.py'],
            'exclude': [],
            'path_filter': agent_path,
            'ports': []  # Agent doesn't listen on ports
        }
    ]
    
    # Získej statistiky pro každou komponentu
    all_stats = []
    for comp in components:
        # Use the first auto-detected port if available
        port = comp['ports'][0] if comp.get('ports') else None
        stats = get_component_stats(
            comp['name'],
            comp['keywords'],
            comp['exclude'],
            project_path,
            comp.get('path_filter'),
            port
        )
        all_stats.append(stats)
    
    # Najdi maximum pro normalizaci grafů
    max_cpu = max([s['total_cpu'] for s in all_stats] + [100.0])
    max_memory = max([s['total_memory_percent'] for s in all_stats] + [100.0])
    
    # Vytiskni statistiky
    for stats in all_stats:
        print_component_stats(stats, max_cpu, max_memory)
    
    # Celkové souhrnné statistiky
    total_cpu = sum([s['total_cpu'] for s in all_stats])
    total_memory_bytes = sum([s['total_memory_bytes'] for s in all_stats])
    total_memory_percent = sum([s['total_memory_percent'] for s in all_stats])
    total_processes = sum([s['count'] for s in all_stats])
    
    print(f"\n{'='*70}")
    print(f"  CELKOVÉ VYUŽITÍ - VŠECHNY KOMPONENTY")
    print(f"{'='*70}")
    print(f"  Celkový počet procesů: {total_processes}")
    print(f"  Celkové CPU: {total_cpu:.2f}%")
    print(f"  {draw_bar(total_cpu, max_cpu)}")
    print(f"  Celková paměť: {format_bytes(total_memory_bytes)} ({total_memory_percent:.2f}%)")
    print(f"  {draw_bar(total_memory_percent, max_memory)}")
    
    # Procentuální rozdělení
    print(f"\n  Rozdělení podle komponent:")
    distribution = []
    for stats in all_stats:
        if total_memory_bytes > 0:
            mem_share = (stats['total_memory_bytes'] / total_memory_bytes) * 100
            cpu_share = (stats['total_cpu'] / total_cpu * 100) if total_cpu > 0 else 0
            print(f"    {stats['name']:10s}: CPU {cpu_share:5.1f}% | RAM {mem_share:5.1f}%")
            distribution.append({
                'name': stats['name'],
                'cpu_share': cpu_share,
                'memory_share': mem_share
            })
    
    print(f"\n{'='*70}\n")
    
    # Získej celkové systémové CPU využití
    system_cpu_percent = psutil.cpu_percent(interval=0.5)
    
    # Generuj HTML report
    generate_html_report(all_stats, total_cpu, total_memory_bytes, total_memory_percent, 
                        total_processes, distribution, cpu_count, total_memory, available_memory, system_cpu_percent)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nUkončeno uživatelem.")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nChyba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

