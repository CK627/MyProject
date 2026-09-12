import unittest
import sys
import os
import shutil
import tempfile
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from storage import StorageManager


class TestGroupStorage(unittest.TestCase):
    """Group-history storage round-trip (isolated from real data)."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.storage = StorageManager(user_id="group_test_user")
        self.storage.base_path = self.tmp
        self.storage.setup_directories()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_group_history_roundtrip(self):
        self.storage.save_group_message("Alice", "10.0.0.2", "hello", "text")
        self.storage.save_group_message("Bob", "10.0.0.3", "hi", "text")

        history = self.storage.get_group_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["nickname"], "Alice")
        self.assertEqual(history[0]["content"], "hello")
        self.assertIn("ip", history[0])
        self.assertIn("timestamp", history[0])
        self.assertIn("id", history[0])

    def test_group_message_dedup_by_id(self):
        self.storage.save_group_message("Alice", "10.0.0.2", "hello", "text", msg_id="shared-id")
        self.storage.save_group_message("Alice", "10.0.0.2", "hello", "text", msg_id="shared-id")
        self.assertEqual(len(self.storage.get_group_history()), 1)

    def test_merge_group_history_dedup(self):
        self.storage.save_group_message("Alice", "10.0.0.2", "one", "text", msg_id="id-1")
        added = self.storage.merge_group_history([
            {'id': 'id-1', 'timestamp': time.time(), 'nickname': 'Alice', 'ip': '10.0.0.2', 'content': 'one', 'type': 'text'},
            {'id': 'id-2', 'timestamp': time.time(), 'nickname': 'Bob', 'ip': '10.0.0.3', 'content': 'two', 'type': 'text'},
        ])
        self.assertEqual(len(added), 1)  # only id-2 is new
        self.assertEqual(len(self.storage.get_group_history()), 2)


class TestGroupApi(unittest.TestCase):
    """Group HTTP endpoints via Flask test client (isolated storage + peers)."""

    def setUp(self):
        self.orig_storage = app.storage
        self.tmp = tempfile.mkdtemp()
        self.storage = StorageManager(user_id="group_api_test_user")
        self.storage.base_path = self.tmp
        self.storage.setup_directories()
        app.storage = self.storage
        app.group_peers.clear()
        self.client = app.app.test_client()

    def tearDown(self):
        app.storage = self.orig_storage
        app.group_peers.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_members_contains_self(self):
        r = self.client.get('/api/group/members')
        members = r.get_json()['members']
        self.assertTrue(any(m['uid'] == app.USER_ID for m in members))

    def test_group_history_starts_empty(self):
        r = self.client.get('/api/group/history')
        self.assertEqual(r.get_json()['history'], [])

    def test_receive_group_message_stores_history_and_peer(self):
        r = self.client.post('/api/receive_message', json={
            'scope': 'group', 'sender_ip': '10.0.0.5',
            'nickname': 'Alice', 'content': 'hello group', 'type': 'text'})
        self.assertEqual(r.status_code, 200)

        history = self.client.get('/api/group/history').get_json()['history']
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['content'], 'hello group')

        members = self.client.get('/api/group/members').get_json()['members']
        self.assertTrue(any(m['ip'] == '10.0.0.5' for m in members))

    def test_private_message_not_stored_in_group_history(self):
        self.client.post('/api/receive_message', json={
            'nickname': 'Bob', 'content': 'pm', 'type': 'text'})
        history = self.client.get('/api/group/history').get_json()['history']
        self.assertEqual(history, [])


if __name__ == '__main__':
    unittest.main()
