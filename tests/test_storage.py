import unittest
import os
import shutil
import time
import sys

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from storage import StorageManager

class TestStorageManager(unittest.TestCase):
    def setUp(self):
        self.test_user_id = "test_user_123"
        self.storage = StorageManager(user_id=self.test_user_id)
        # Ensure we start with a clean slate for this user in tests
        # Note: Be careful not to delete real data if user_id was real.
        if os.path.exists(self.storage.base_path):
            shutil.rmtree(self.storage.base_path)
        self.storage.setup_directories()

    def tearDown(self):
        # Cleanup after tests
        if os.path.exists(self.storage.base_path):
            shutil.rmtree(self.storage.base_path)

    def test_directory_creation(self):
        """Test if directories are created correctly."""
        self.assertTrue(os.path.exists(self.storage.file_storage_path))
        self.assertTrue(os.path.exists(self.storage.msg_path))
        self.assertTrue(os.path.exists(self.storage.trash_path))
        self.assertTrue(os.path.exists(self.storage.cache_path))

    def test_save_file(self):
        """Test saving a file (copy/link)."""
        # Create a dummy source file
        source_file = "test_source.txt"
        with open(source_file, "w") as f:
            f.write("Test content")
        
        try:
            saved_path = self.storage.save_file(os.path.abspath(source_file))
            self.assertTrue(os.path.exists(saved_path))
            self.assertEqual(os.path.basename(saved_path), source_file)
            
            # Check content
            with open(saved_path, "r") as f:
                content = f.read()
            self.assertEqual(content, "Test content")
        finally:
            if os.path.exists(source_file):
                os.remove(source_file)

    def test_async_delete(self):
        """Test async delete (move to trash)."""
        # Create a file in storage
        file_path = os.path.join(self.storage.file_storage_path, "to_delete.txt")
        with open(file_path, "w") as f:
            f.write("Delete me")
            
        self.assertTrue(os.path.exists(file_path))
        
        # Delete it
        self.storage.async_delete(file_path)
        
        # Check if gone from original location
        self.assertFalse(os.path.exists(file_path))
        
        # Check if in trash (trash filename has timestamp appended)
        trash_files = os.listdir(self.storage.trash_path)
        self.assertTrue(len(trash_files) > 0)
        self.assertTrue(trash_files[0].startswith("to_delete.txt"))

    def test_save_message(self):
        """Test message logging."""
        msg = "Hello World"
        self.storage.save_message(msg)
        
        log_file = os.path.join(self.storage.msg_path, "chat_history.log")
        self.assertTrue(os.path.exists(log_file))
        
        with open(log_file, "r") as f:
            content = f.read()
        self.assertIn(msg, content)

if __name__ == '__main__':
    unittest.main()
