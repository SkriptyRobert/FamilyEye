"""Network control - firewall, DNS, VPN detection."""
import subprocess
import socket
import re
from typing import List, Set, Optional
import platform


from .logger import get_logger


class NetworkController:
    """Control network access via firewall and DNS."""
    
    def __init__(self):
        self.blocked_websites: Set[str] = set()
        self.logger = get_logger('NETWORK')
        self.allowed_dns_servers: List[str] = []
        self.blocked_dns_servers: List[str] = []
        self.vpn_processes: Set[str] = {
            "openvpn", "nordvpn", "expressvpn", "surfshark",
            "protonvpn", "windscribe", "torguard", "cyberghost",
            "privateinternetaccess", "pia", "tor", "torbrowser",
            "wireguard", "strongswan", "ikev2", "ipsec"
        }
        self.proxy_processes: Set[str] = {
            "proxifier", "proxychains", "fiddler", "charles",
            "burp", "mitmproxy"
        }
        # Whitelist of legitimate processes that might contain "vpn" in name
        self.process_whitelist: Set[str] = {
            "officeclicktorun", "clicktorun", "microsoft",
            "windows", "system", "svchost", "explorer",
            "dwm", "winlogon", "csrss", "services"
        }
    
    def block_website(self, domain: str) -> bool:
        """Block website via hosts file with marker."""
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            domain_clean = domain.lower().strip()
            marker = f"# [PC-BLOCK] {domain_clean}"
            
            # Read current hosts file
            try:
                with open(hosts_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception:
                content = ""
            
            # Check if already blocked (including marker)
            if marker in content:
                return True
            
            # Add block entry with marker
            block_entry = f"\n127.0.0.1 {domain_clean} {marker}\n"
            
            try:
                with open(hosts_path, 'a', encoding='utf-8') as f:
                    f.write(block_entry)
                self.blocked_websites.add(domain_clean)
                self.logger.info(f"Blocked website: {domain_clean}")
                return True
            except PermissionError:
                return False
        except Exception as e:
            print(f"[NETWORK] Error blocking website {domain}: {e}")
            self.logger.error(f"Error blocking website {domain}: {e}")
            return False
    
    def unblock_website(self, domain: str) -> bool:
        """Unblock website from hosts file using marker."""
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            domain_clean = domain.lower().strip()
            marker = f"[PC-BLOCK] {domain_clean}"
            
            try:
                with open(hosts_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                return True
            
            filtered_lines = [line for line in lines if marker not in line]
            
            # Secondary check for direct entries we might have missed
            filtered_lines = [line for line in filtered_lines if not (f"127.0.0.1 {domain_clean}" in line and "#" not in line)]
            
            try:
                with open(hosts_path, 'w', encoding='utf-8') as f:
                    f.writelines(filtered_lines)
                self.blocked_websites.discard(domain_clean)
                self.logger.info(f"Unblocked website: {domain_clean}")
                return True
            except PermissionError:
                return False
        except Exception as e:
            self.logger.error(f"Error unblocking website {domain}: {e}")
            return False

    def clear_all_blocked_websites(self) -> bool:
        """Surgical cleanup of all websites blocked by Parental Control."""
        try:
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            try:
                with open(hosts_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            except Exception:
                return True
                
            # Remove any line that contains our block marker
            filtered_lines = [line for line in lines if "[PC-BLOCK]" not in line]
            
            with open(hosts_path, 'w', encoding='utf-8') as f:
                f.writelines(filtered_lines)
            return True
        except Exception as e:
            self.logger.error(f"Error during full website cleanup: {e}")
            return False
    
    def set_dns_servers(self, dns_servers: List[str]) -> bool:
        """Set DNS servers (requires admin)."""
        try:
            if not dns_servers:
                return False
            
            # Get active network adapter
            adapter_name = self._get_active_adapter()
            if not adapter_name:
                self.logger.warning("Could not find active network adapter")
                return False
            
            # Set DNS using netsh
            cmd = ['netsh', 'interface', 'ipv4', 'set', 'dns', 
                   f'name="{adapter_name}"', 'static', dns_servers[0]]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.allowed_dns_servers = dns_servers
                self.logger.info(f"Set DNS servers: {dns_servers}")
                
                # Set secondary DNS if provided
                if len(dns_servers) > 1:
                    cmd2 = ['netsh', 'interface', 'ipv4', 'add', 'dns',
                           f'name="{adapter_name}"', dns_servers[1], 'index=2']
                    subprocess.run(cmd2, capture_output=True, timeout=10)
                
                return True
            else:
                self.logger.error(f"Failed to set DNS: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error setting DNS servers: {e}")
            return False
    
    def _get_active_adapter(self) -> Optional[str]:
        """Get active network adapter name."""
        try:
            result = subprocess.run(
                ['netsh', 'interface', 'show', 'interface'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Connected' in line or 'Up' in line:
                        parts = line.split()
                        if len(parts) >= 4:
                            # Adapter name is usually the last part
                            adapter = ' '.join(parts[3:])
                            if adapter and adapter != 'State':
                                return adapter
        except Exception:
            pass
        
        return None
    
    def detect_vpn(self) -> bool:
        """Detect if VPN is running."""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    
                    # Skip whitelisted processes
                    proc_name_no_ext = proc_name.replace('.exe', '')
                    if any(whitelist_item in proc_name_no_ext for whitelist_item in self.process_whitelist):
                        continue
                    
                    # Check for VPN processes (exact match or contains VPN keyword)
                    for vpn_name in self.vpn_processes:
                        if vpn_name == proc_name_no_ext or (len(vpn_name) > 3 and vpn_name in proc_name_no_ext):
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error detecting VPN: {e}")
        
        return False
    
    def detect_proxy(self) -> bool:
        """Detect if proxy tools are running."""
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                try:
                    proc_name = proc.info['name'].lower()
                    # Check for proxy processes
                    for proxy_name in self.proxy_processes:
                        if proxy_name in proc_name:
                            self.logger.warning(f"Proxy detected: {proc_name}")
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.logger.error(f"Error detecting proxy: {e}")
        
        return False
    
    def block_app_network(self, app_name: str) -> bool:
        """Block network access for specific app via firewall."""
        try:
            # Create firewall rule to block app
            rule_name = f"ParentalControl_Block_{app_name}"
            
            # Check if rule exists
            check_cmd = ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 
                         f'name="{rule_name}"']
            check_result = subprocess.run(check_cmd, capture_output=True, timeout=10)
            
            if check_result.returncode == 0:
                # Rule exists, enable it
                enable_cmd = ['netsh', 'advfirewall', 'firewall', 'set', 'rule',
                             f'name="{rule_name}"', 'new', 'enable=yes']
                subprocess.run(enable_cmd, capture_output=True, timeout=10)
                return True
            
            # Create new rule
            app_path = self._find_app_path(app_name)
            if not app_path:
                self.logger.warning(f"Could not find path for {app_name}")
                return False
            
            cmd = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                f'name="{rule_name}"',
                'dir=out',
                'action=block',
                f'program="{app_path}"',
                'enable=yes'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.info(f"Blocked network access for {app_name}")
                return True
            else:
                self.logger.error(f"Failed to block network for {app_name}: {result.stderr}")
                return False
        except Exception as e:
            self.logger.error(f"Error blocking network for {app_name}: {e}")
            return False
    
    def _resolve_domain(self, url_or_domain: str) -> Optional[str]:
        """Resolve domain name to IP address."""
        try:
            # Strip protocol and path
            domain = url_or_domain.replace('https://', '').replace('http://', '').split('/')[0].split(':')[0]
            if not domain:
                return None
                
            # If it's already an IP, return it
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain):
                return domain
                
            ip = socket.gethostbyname(domain)
            self.logger.info(f"Resolved {domain} to {ip}")
            return ip
        except Exception as e:
            self.logger.error(f"Failed to resolve {url_or_domain}: {e}")
            return None

    def block_all_outbound(self, whitelist_ips: List[str] = None, backend_url: str = None) -> bool:
        """Block all outbound traffic using default policy, with explicit ALLOW rules for essentials.
        
        This approach is more reliable than 'remoteip=any except' which often fails on Windows.
        It sets the default outbound policy to BLOCK, then creates ALLOW rules for:
        - The agent executable itself
        - DNS (UDP port 53) - required to resolve backend hostname
        - LAN ranges
        - Backend server IP
        """
        try:
            self.logger.info("=== BLOCKING INTERNET (Policy-based approach) ===")
            
            # Step 0: Cleanup any old rules first
            self._cleanup_firewall_rules()
            
            # Step 1: Ensure firewall is ON
            subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 'state', 'on'], 
                          capture_output=True, text=True, timeout=10)
            
            # Step 2: Resolve backend IP BEFORE blocking (while DNS still works!)
            backend_ip = None
            if backend_url:
                backend_ip = self._resolve_domain(backend_url)
                if backend_ip:
                    self.logger.info(f"Backend IP resolved: {backend_ip}")
                else:
                    self.logger.warning(f"Could not resolve backend URL: {backend_url}")
            
            # Step 3: Get the path to agent_service.exe
            import sys
            if getattr(sys, 'frozen', False):
                agent_path = sys.executable
            else:
                agent_path = sys.executable  # python.exe when running as script
            self.logger.info(f"Agent executable: {agent_path}")
            
            # Step 4: Create ALLOW rules BEFORE changing policy
            
            # 4a. Allow agent executable
            cmd_agent = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name="FamilyEye_AllowAgent"',
                'dir=out', 'action=allow',
                f'program="{agent_path}"',
                'enable=yes', 'profile=any'
            ]
            result = subprocess.run(cmd_agent, capture_output=True, text=True, timeout=10)
            self.logger.info(f"Allow Agent rule: {result.returncode == 0}")
            
            # 4b. Allow DNS (required to resolve hostnames)
            cmd_dns = [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name="FamilyEye_AllowDNS"',
                'dir=out', 'action=allow',
                'protocol=udp', 'remoteport=53',
                'enable=yes', 'profile=any'
            ]
            subprocess.run(cmd_dns, capture_output=True, text=True, timeout=10)
            
            # 4c. Allow LAN ranges
            lan_ranges = ["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
            for i, ip_range in enumerate(lan_ranges):
                cmd_lan = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    f'name="FamilyEye_AllowLAN_{i}"',
                    'dir=out', 'action=allow',
                    f'remoteip={ip_range}',
                    'enable=yes', 'profile=any'
                ]
                subprocess.run(cmd_lan, capture_output=True, text=True, timeout=10)
            
            # 4d. Allow backend IP (if resolved)
            if backend_ip:
                cmd_backend = [
                    'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                    'name="FamilyEye_AllowBackend"',
                    'dir=out', 'action=allow',
                    f'remoteip={backend_ip}',
                    'enable=yes', 'profile=any'
                ]
                result = subprocess.run(cmd_backend, capture_output=True, text=True, timeout=10)
                self.logger.info(f"Allow Backend rule ({backend_ip}): {result.returncode == 0}")
            
            # Step 5: Now set default outbound policy to BLOCK
            # This blocks everything EXCEPT our explicit ALLOW rules
            cmd_policy = [
                'netsh', 'advfirewall', 'set', 'allprofiles',
                'firewallpolicy', 'blockinbound,blockoutbound'
            ]
            result = subprocess.run(cmd_policy, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.success("Internet blocked! Agent and backend whitelisted.")
                return True
            else:
                self.logger.error(f"Failed to set outbound policy: {result.stderr}")
                # Restore normal policy to avoid leaving system in broken state
                subprocess.run(['netsh', 'advfirewall', 'set', 'allprofiles', 
                               'firewallpolicy', 'blockinbound,allowoutbound'],
                              capture_output=True, timeout=10)
                return False
            
        except subprocess.TimeoutExpired:
            self.logger.error("Timeout while configuring firewall")
            return False
        except Exception as e:
            self.logger.error(f"Error blocking outbound: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False

    def _cleanup_firewall_rules(self):
        """Remove all FamilyEye firewall rules."""
        rules_to_delete = [
            "FamilyEye_BlockAll",
            "FamilyEye_AllowAgent",
            "FamilyEye_AllowDNS",
            "FamilyEye_AllowBackend",
            "ParentalControl_BlockAll",  # Legacy
        ]
        # Also delete LAN rules (0-3)
        for i in range(4):
            rules_to_delete.append(f"FamilyEye_AllowLAN_{i}")
        
        for rule in rules_to_delete:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', f'name="{rule}"'],
                          capture_output=True, timeout=5)

    def unblock_all_outbound(self) -> bool:
        """Restore normal internet access."""
        try:
            self.logger.info("=== RESTORING INTERNET ===")
            
            # Step 1: Restore default outbound policy to ALLOW
            cmd_policy = [
                'netsh', 'advfirewall', 'set', 'allprofiles',
                'firewallpolicy', 'blockinbound,allowoutbound'
            ]
            result = subprocess.run(cmd_policy, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                self.logger.success("Default outbound policy restored to ALLOW")
            else:
                self.logger.warning(f"Policy restore warning: {result.stderr}")
            
            # Step 2: Cleanup our allow rules (not strictly necessary but keeps things tidy)
            self._cleanup_firewall_rules()
            
            self.logger.success("Internet access restored")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unblocking outbound: {e}")
            return False
    
    def _find_app_path(self, app_name: str) -> Optional[str]:
        """Find full path to application executable."""
        try:
            import psutil
            app_name_lower = app_name.lower()
            
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    proc_name = proc.info['name'].lower()
                    if app_name_lower in proc_name or proc_name.startswith(app_name_lower):
                        exe_path = proc.info.get('exe')
                        if exe_path:
                            return exe_path
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        return None
    
    def get_current_dns(self) -> List[str]:
        """Get current DNS servers."""
        try:
            result = subprocess.run(
                ['ipconfig', '/all'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                dns_servers = []
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'DNS Servers' in line:
                        # Extract IP address
                        ip_match = re.search(r'\d+\.\d+\.\d+\.\d+', line)
                        if ip_match:
                            dns_servers.append(ip_match.group())
                return dns_servers
        except Exception as e:
            self.logger.error(f"Error getting DNS: {e}")
        
        return []

