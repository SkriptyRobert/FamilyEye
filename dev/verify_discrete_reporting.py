import sys
import os
import time
import unittest
from unittest.mock import MagicMock, patch

# Add agent path to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from clients.windows.agent.api_client import api_client
from clients.windows.agent.reporter import UsageReporter
from clients.windows.agent.monitor import AppMonitor

class TestDiscreteReporting(unittest.TestCase):
    
    def test_discrete_queue_hunks(self):
        # Initialize components
        monitor = AppMonitor()
        reporter = UsageReporter(monitor)
        
        # Clear any existing queue
        reporter.report_queue = []
        
        # 1. Simulate Offline Usage - Hunk 1 (e.g. at T=0)
        with patch.object(monitor, 'snap_pending_usage') as mock_snap:
            mock_snap.return_value = {"App1": 60}
            with patch.object(monitor, 'get_running_processes', return_value=["App1"]):
                # Mock api_client to fail (simulate offline)
                with patch.object(api_client.session, 'post', side_effect=Exception("Offline")):
                    reporter.send_reports()
                    
        # 2. Simulate Offline Usage - Hunk 2 (e.g. at T=60)
        with patch.object(monitor, 'snap_pending_usage') as mock_snap:
            mock_snap.return_value = {"App1": 60}
            with patch.object(monitor, 'get_running_processes', return_value=["App1"]):
                with patch.object(api_client.session, 'post', side_effect=Exception("Offline")):
                    reporter.send_reports()
                    
        # Verify queue has 2 discrete hunks
        self.assertEqual(len(reporter.report_queue), 2)
        self.assertNotEqual(reporter.report_queue[0]['timestamp'], reporter.report_queue[1]['timestamp'])
        
        # 3. Simulate Reconnection and Sending
        with patch.object(api_client.session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "success", "commands": []}
            mock_post.return_value = mock_response
            
            # This should send BOTH hunks
            reporter.send_reports()
            
            # Verify queue is empty
            self.assertEqual(len(reporter.report_queue), 0)
            # Verify post was called twice (once per hunk)
            self.assertEqual(mock_post.call_count, 2)
            
        print("Discrete Reporting Test: SUCCESS")

if __name__ == '__main__':
    unittest.main()
