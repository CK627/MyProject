import unittest
import os
import json
import threading
import time
from http.server import HTTPServer
from web_monitor_server import LogRequestHandler, LOG_DIR
import requests

# Mock config
TEST_PORT = 9998
TEST_LOG_DIR = 'test_logs'

class TestWebMonitorServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Setup test environment
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
            
        # Create dummy log file
        cls.today = time.strftime('%Y-%m-%d')
        cls.log_file = os.path.join(LOG_DIR, f"{cls.today}.log")
        
        # Write some logs
        with open(cls.log_file, 'w', encoding='utf-8') as f:
            for i in range(20):
                f.write(f"10:00:{i:02d}-200-OK-10:01:00-example.com\n")
        
        # Start server in thread
        cls.server = HTTPServer(('localhost', TEST_PORT), LogRequestHandler)
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(1) # Wait for server start

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        # Cleanup logs
        if os.path.exists(cls.log_file):
            os.remove(cls.log_file)

    def test_homepage(self):
        """Test if homepage loads and contains HTML structure"""
        response = requests.get(f'http://localhost:{TEST_PORT}/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/html', response.headers['Content-Type'])
        self.assertIn('<title>WebMailMonitor Log</title>', response.text)
        self.assertIn('log-container', response.text)

    def test_api_logs(self):
        """Test if API returns JSON logs"""
        response = requests.get(f'http://localhost:{TEST_PORT}/api/logs')
        self.assertEqual(response.status_code, 200)
        self.assertIn('application/json', response.headers['Content-Type'])
        
        data = response.json()
        self.assertIn('logs', data)
        self.assertTrue(len(data['logs']) >= 20)
        self.assertIn('example.com', data['logs'][0])

    def test_404(self):
        """Test non-existent path"""
        response = requests.get(f'http://localhost:{TEST_PORT}/nonexistent')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
