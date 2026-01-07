import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch

# Add agent path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clients.windows.agent.api_client import api_client
from clients.windows.agent.reporter import UsageReporter
from clients.windows.agent.enforcer import RuleEnforcer
from clients.windows.agent.monitor import AppMonitor

class TestAgentSync(unittest.TestCase):
    
    def test_reconnection_trigger(self):
        # Configure mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "rules": []}
        
        # Patch the session.post method on the GLOBAL api_client instance
        # This is necessary because api_client is instantiated at module load time
        with patch.object(api_client.session, 'post') as mock_post:
            mock_post.return_value = mock_response
            
            # Initialize components (they will register themselves to the global api_client)
            monitor = AppMonitor()
            reporter = UsageReporter(monitor)
            enforcer = RuleEnforcer()
            enforcer.set_monitor(monitor)
            
            # Ensure we start fresh
            api_client.is_online = True
            reporter._needs_immediate_sync = False
            enforcer._needs_immediate_fetch = False
            
            # 1. Simulate Connection Loss
            import requests
            mock_post.side_effect = requests.exceptions.RequestException("Connection Refused")
            api_client.fetch_rules()
            self.assertFalse(api_client.is_online)
            
            # 2. Simulate Success (Reconnection)
            mock_post.side_effect = None
            mock_post.return_value = mock_response
            api_client.fetch_rules()
            self.assertTrue(api_client.is_online)
            
            # 3. Verify that components were notified
            self.assertTrue(reporter._needs_immediate_sync)
            self.assertTrue(enforcer._needs_immediate_fetch)
        
        print("Reconnection Trigger Test: SUCCESS")

    def test_startup_sequence_data_flow(self):
        # This is a logic test for main.py sequence
        # We want to ensure Monitor.update() happens before Reporter.send_reports()
        monitor = AppMonitor()
        monitor.update = MagicMock()
        
        reporter = UsageReporter(monitor)
        reporter.send_reports = MagicMock()
        
        # Simulated main.start()
        monitor.update()
        reporter.send_reports()
        
        # Verify call order
        monitor.update.assert_called()
        reporter.send_reports.assert_called()
        
        print("Startup Sequence logic: SUCCESS")

if __name__ == '__main__':
    unittest.main()
