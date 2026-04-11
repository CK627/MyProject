#!/usr/bin/env python3
import time
import random
import threading
import requests
from datetime import datetime, timedelta
from common_lib import ConfigManager, Logger, EmailSender

# --- Monitor Logic ---

class MonitorThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.daemon = True # Allow app to exit even if thread is running
        self.is_abnormal = False # Track previous state to handle alert/recovery logic

    def run(self):
        print("Monitor started.")
        while not self.stop_event.is_set():
            # Calculate next check time (random sleep)
            sleep_time = random.randint(30, 120)
            next_check_dt = datetime.now() + timedelta(seconds=sleep_time)
            next_check_str = next_check_dt.strftime('%H:%M:%S')

            self.check_website(next_check_str)
            
            # Sleep in small chunks to allow responsive stop
            for _ in range(sleep_time):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def check_website(self, next_check_time):
        config = ConfigManager.load()
        url = config.get('url')
        try:
            expected = int(config.get('expected_code', 200))
        except:
            expected = 200
        
        try:
            response = requests.get(url, timeout=10)
            code = response.status_code
            
            if code == expected:
                Logger.log(code, "正常", next_check_time)
                print(f"Check OK: {url} -> {code}")
                
                # If previously abnormal, send recovery email
                if self.is_abnormal:
                    EmailSender.send_recovery(code)
                    self.is_abnormal = False
                    
            else:
                Logger.log(code, "不正常原因:状态码不匹配", next_check_time)
                print(f"Check Failed: {url} -> {code}")
                
                # If previously normal (or first failure), send alert email
                # If already abnormal, do NOT send another alert
                if not self.is_abnormal:
                    EmailSender.send_alert(code, "不正常原因:状态码不匹配")
                    self.is_abnormal = True
                    
        except Exception as e:
            error_msg = str(e)
            Logger.log("Error", f"不正常原因:{error_msg}", next_check_time)
            print(f"Check Error: {url} -> {e}")
            
            if not self.is_abnormal:
                EmailSender.send_alert("Error", f"不正常原因:{error_msg}")
                self.is_abnormal = True

    def stop(self):
        self.stop_event.set()
        print("Monitor stopping...")

# --- Main Console Application ---

def main():
    print("Web Monitor (Console Version)")
    print("=============================")
    print("Press Ctrl+C to stop the monitor.")
    print("To change settings, edit 'config.ini' and restart the program.")
    print("=============================")
    
    # Ensure config exists
    ConfigManager.load()
    
    monitor = MonitorThread()
    monitor.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
        monitor.join()
        print("Monitor stopped. Exiting.")

if __name__ == "__main__":
    main()
