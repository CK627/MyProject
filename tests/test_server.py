import unittest
import sys
import os
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, socketio

class TestWebServer(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.app = app.test_client()
        self.socketio_test_client = socketio.test_client(app)

    def test_index_route(self):
        """Test if index page loads."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Smart Campus Chat", response.data)

    def test_scan_api(self):
        """Test scan API endpoint."""
        response = self.app.get('/scan')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('hosts', data)
        self.assertIsInstance(data['hosts'], list)

    def test_socket_connection(self):
        """Test SocketIO connection."""
        self.assertTrue(self.socketio_test_client.is_connected())
        
        # Test sending a message (simulating client send)
        # Note: This requires the event handler to be set up correctly
        # In app.py: @socketio.on('send_message')
        # We need to mock the target_ip check or expect it to fail sending to remote
        
        # Testing local echo/processing might be complex without a real second client
        # But we can check if it acknowledges or emits error
        
        self.socketio_test_client.emit('send_message', {
            'target_ip': '127.0.0.1',
            'content': 'Hello Test',
            'type': 'text'
        })
        
        received = self.socketio_test_client.get_received()
        # We might expect an 'error' event because 127.0.0.1:5000/api/receive_message might not be reachable 
        # (since we are in test mode, not running full server in this process, 
        # though the real server IS running in another terminal... wait.
        # This test runs in a separate process. The 'requests.post' in app.py will try to hit 127.0.0.1:8080.
        # If the real server is running on 8080, it might actually work!)
        
        print(f"Socket events received: {received}")
        self.assertTrue(len(received) > 0)

if __name__ == '__main__':
    unittest.main()
