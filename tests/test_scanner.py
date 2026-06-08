import unittest
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scanner import NetworkScanner

class TestNetworkScanner(unittest.TestCase):
    def setUp(self):
        self.scanner = NetworkScanner(port=<SCANNER_PORT>)

    def test_get_local_ip(self):
        """Test if we can get a valid local IP."""
        ip, network = self.scanner.get_local_ip_and_network()
        print(f"Detected IP: {ip}, Network: {network}")
        
        self.assertIsNotNone(ip)
        # IP should be a string and look like an IP
        self.assertEqual(len(ip.split('.')), 4)
        
        # Network might be None if no interface found, but usually should be present
        if network:
            self.assertIn('/', network)

    def test_scan_network_structure(self):
        """
        Test that scan_network returns a list.
        Actual scanning might not find hosts in test env, but should run without error.
        """
        hosts = self.scanner.scan_network()
        self.assertIsInstance(hosts, list)

if __name__ == '__main__':
    unittest.main()
