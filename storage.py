import os
import sys
import shutil
import time
import threading
import platform
import logging

from config import get

class StorageManager:
    def __init__(self, user_id="default_user"):
        self.user_id = user_id
        self.base_path = self._get_default_base_path()
        self.trash_thread = None
        self.stop_trash_thread = False
        self.setup_directories()

    def _get_default_base_path(self):
        """
        Get the default storage path.
        Uses the user's Documents folder to ensure write access and persistence.
        """
        data_dir = os.path.expanduser(get('storage', 'data_dir'))
        return os.path.join(data_dir, self.user_id)

    def set_custom_path(self, path):
        """
        Allow user to customize the storage path.
        """
        self.base_path = os.path.join(path, "SmartCampusServicePlatform", self.user_id)
        self.setup_directories()

    def setup_directories(self):
        """
        Create the hierarchical directory structure.
        """
        self.file_storage_path = os.path.join(self.base_path, "FileStorage")
        self.msg_path = os.path.join(self.base_path, "Msg")
        self.cache_path = os.path.join(self.base_path, "Cache")
        self.trash_path = os.path.join(self.base_path, ".trash")

        for path in [self.file_storage_path, self.msg_path, self.trash_path, self.cache_path]:
            os.makedirs(path, exist_ok=True)
            
    # ... existing code ...

    def clean_cache(self, days=7):
        """
        Clean up cache files older than 'days'.
        """
        now = time.time()
        cutoff = now - (days * 86400)
        
        try:
            for filename in os.listdir(self.cache_path):
                file_path = os.path.join(self.cache_path, filename)
                if os.path.getmtime(file_path) < cutoff:
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                        elif os.path.isdir(file_path):
                            shutil.rmtree(file_path)
                        logging.info(f"Cleaned cache file: {file_path}")
                    except Exception as e:
                        logging.error(f"Failed to delete cache {file_path}: {e}")
        except Exception as e:
            logging.error(f"Error cleaning cache: {e}")

    def save_file(self, source_path, file_type="file"):
        """
        Save a file to the storage. 
        If file exists elsewhere in the system, try to hard link.
        """
        filename = os.path.basename(source_path)
        dest_path = os.path.join(self.file_storage_path, filename)
        
        # Avoid overwriting existing files with same name
        if os.path.exists(dest_path):
            base, ext = os.path.splitext(filename)
            timestamp = int(time.time())
            dest_path = os.path.join(self.file_storage_path, f"{base}_{timestamp}{ext}")

        try:
            # Try hard link first
            os.link(source_path, dest_path)
            logging.info(f"Hard linked {source_path} to {dest_path}")
        except OSError:
            # Fallback to copy
            shutil.copy2(source_path, dest_path)
            logging.info(f"Copied {source_path} to {dest_path}")
        
        return dest_path

    def save_message(self, message_data):
        """
        Save message to a log file (simulating database in Msg folder).
        """
        log_file = os.path.join(self.msg_path, "chat_history.log")
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{time.time()}|{message_data}\n")

    def get_history(self, peer_ip):
        """
        Retrieve chat history with a specific peer IP.
        Parses the chat_history.log file.
        """
        log_file = os.path.join(self.msg_path, "chat_history.log")
        if not os.path.exists(log_file):
            return []

        history = []
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        # Format: timestamp|FROM:ip|TYPE:type|CONTENT:content
                        # or      timestamp|TO:ip|TYPE:type|CONTENT:content
                        
                        parts = line.split('|', 1)
                        if len(parts) < 2: continue
                        
                        timestamp_str = parts[0]
                        data_str = parts[1]
                        
                        # Parse data_str
                        # It might contain multiple | separators, so we need to be careful
                        # Actually we constructed it as f"FROM:{sender_ip}|TYPE:{msg_type}|CONTENT:{content}"
                        # Let's split by | but limit splits? No, content might have |.
                        
                        # Better approach: split by specific prefixes if possible, or just standard split
                        # Given the simple format: 
                        # FROM:x.x.x.x|TYPE:text|CONTENT:hello
                        
                        # Let's verify if this line relates to peer_ip
                        if f"FROM:{peer_ip}" in data_str:
                            direction = "received"
                        elif f"TO:{peer_ip}" in data_str:
                            direction = "sent"
                        else:
                            continue
                            
                        # Extract content and type
                        # We can look for markers
                        type_start = data_str.find("TYPE:")
                        content_start = data_str.find("CONTENT:")
                        
                        if type_start == -1 or content_start == -1:
                            continue
                            
                        msg_type = data_str[type_start+5 : content_start-1] # -1 for the pipe
                        content = data_str[content_start+8:]
                        
                        # Format timestamp to readable string
                        ts = float(timestamp_str)
                        time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))
                        
                        history.append({
                            'content': content,
                            'type': msg_type,
                            'timestamp': time_str,
                            'direction': direction
                        })
                        
                    except Exception as e:
                        logging.error(f"Error parsing history line: {line} - {e}")
                        continue
        except Exception as e:
            logging.error(f"Failed to read history file: {e}")
            
        return history

    def async_delete(self, file_path):
        """
        Simulate async delete by moving to trash.
        """
        if not os.path.exists(file_path):
            return
        
        filename = os.path.basename(file_path)
        trash_dest = os.path.join(self.trash_path, f"{filename}_{int(time.time())}")
        
        try:
            shutil.move(file_path, trash_dest)
            logging.info(f"Moved {file_path} to trash")
        except Exception as e:
            logging.error(f"Error deleting file: {e}")

        # Start cleanup thread if not running
        if not self.trash_thread or not self.trash_thread.is_alive():
            self.stop_trash_thread = False
            self.trash_thread = threading.Thread(target=self._cleanup_trash)
            self.trash_thread.daemon = True
            self.trash_thread.start()

    def _cleanup_trash(self):
        """
        Background task to clean up trash when idle.
        """
        # Wait for a bit to simulate "when system is idle"
        time.sleep(10) 
        
        if self.stop_trash_thread:
            return

        try:
            for filename in os.listdir(self.trash_path):
                file_path = os.path.join(self.trash_path, filename)
                try:
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    logging.error(f"Failed to delete {file_path}: {e}")
            logging.info("Trash cleaned up")
        except Exception as e:
            logging.error(f"Error during trash cleanup: {e}")


if __name__ == "__main__":
    # Test
    sm = StorageManager(user_id="test_user")
    print(f"Base path: {sm.base_path}")
    
    # Create a dummy file to test
    dummy_file = "test_source.txt"
    with open(dummy_file, "w") as f:
        f.write("Hello World")
    
    saved_path = sm.save_file(os.path.abspath(dummy_file))
    print(f"Saved to: {saved_path}")
    
    sm.async_delete(saved_path)
    print("Deleted (moved to trash)")
    
    # Clean up dummy
    os.remove(dummy_file)
