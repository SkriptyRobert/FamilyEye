"""Network enforcement (VPN detection, website blocking, network block)."""
import time
import re
from typing import Set, Optional
from ..logger import get_logger


class NetworkEnforcer:
    """Handles network-related enforcement (VPN, websites, full block)."""
    
    def __init__(self, network_controller, logger=None):
        self.logger = logger or get_logger('ENFORCER.NET')
        self.network_controller = network_controller
        
        # VPN detection
        self.last_vpn_check = 0
        self.vpn_check_interval = 60  # Check every 60 seconds
        
        # Network block state
        self._network_currently_blocked = False
        
    def enforce_vpn_detection(self) -> None:
        """Detect and handle VPN/proxy usage."""
        current_time = time.monotonic()
        if current_time - self.last_vpn_check < self.vpn_check_interval:
            return
        
        self.last_vpn_check = current_time
        
        # Check for VPN
        if self.network_controller.detect_vpn():
            self.logger.warning("VPN detected - network access may be restricted")
            # Could implement network blocking here
        
        # Check for proxy
        if self.network_controller.detect_proxy():
            self.logger.warning("Proxy detected - network access may be restricted")
            
    def enforce_network_block(self, is_network_blocked: bool, backend_url: str = "") -> None:
        """Enforce network block if active.
        
        Args:
            is_network_blocked: Whether network should be blocked
            backend_url: Backend URL to whitelist
        """
        if is_network_blocked:
            if not self._network_currently_blocked:
                self.logger.warning("Internet access paused - blocking all outbound traffic")
                
                # Basic LAN whitelist
                whitelist = ["127.0.0.1", "192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]
                
                self.logger.info(f"Blocking network (allowed: LAN + Backend: {backend_url})")
                
                # Pass backend_url for robust resolution and whitelisting
                result = self.network_controller.block_all_outbound(whitelist, backend_url=backend_url)
                
                if result:
                    self._network_currently_blocked = True
                    self.logger.info("Network block applied successfully")
                else:
                    self.logger.error("Failed to apply network block - will retry")
        else:
            if self._network_currently_blocked:
                self.logger.info("Internet access resumed - removing block")
                if self.network_controller.unblock_all_outbound():
                    self._network_currently_blocked = False
                    self.logger.info("Network block removed successfully")
                    
    def sync_blocked_websites(self, new_blocked: Set[str], current_blocked: Set[str]) -> Set[str]:
        """Sync website blocks with new rule set.
        
        Args:
            new_blocked: New set of websites to block
            current_blocked: Currently blocked websites
            
        Returns:
            Updated set of blocked websites
        """
        # Find websites that are currently blocked but NOT in the new list
        websites_to_unblock = current_blocked - new_blocked
        for domain in websites_to_unblock:
            self.network_controller.unblock_website(domain)
            self.logger.info("Unblocking website (rule removed)", domain=domain)
            
        # Find websites that are in the new list but NOT currently blocked
        websites_to_block = new_blocked - current_blocked
        for domain in websites_to_block:
            self.network_controller.block_website(domain)
            self.logger.info("Blocking website (new rule)", domain=domain)
            
        return new_blocked
        
    @staticmethod
    def extract_domain(url: str) -> str:
        """Extract domain from URL.
        
        Args:
            url: URL or domain string
            
        Returns:
            Cleaned domain name
        """
        # Remove protocol
        # Remove protocol (http, https, ws, wss)
        url = re.sub(r'^(https?|wss?)://', '', url)
        # Remove path
        url = url.split('/')[0]
        # Remove port
        url = url.split(':')[0]
        return url.lower().strip()
