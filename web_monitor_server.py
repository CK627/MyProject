#!/usr/bin/env python3
import os
import time
import random
import threading
import requests
import http.server
import socketserver
import json
from datetime import datetime, timedelta
from urllib.parse import urlparse
from common_lib import ConfigManager, Logger, EmailSender, CONFIG_FILE, LOG_DIR

# --- Web Server Logic ---

class LogRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            # Read index.html
            try:
                with open('index.html', 'r', encoding='utf-8') as f:
                    html_content = f.read()
                self.wfile.write(html_content.encode('utf-8'))
            except Exception as e:
                self.wfile.write(f"Error loading index.html: {e}".encode('utf-8'))
            
        elif parsed_path.path == '/api/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            today = datetime.now().strftime('%Y-%m-%d')
            log_file = os.path.join(LOG_DIR, f"{today}.log")
            logs = []
            
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        # Read all lines, filter empty
                        logs = [line.strip() for line in f if line.strip()]
                except:
                    pass
            
            response_data = {"logs": logs}
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
            
        else:
            self.send_error(404)

class WebServerThread(threading.Thread):
    def __init__(self, port=2442):
        super().__init__()
        self.port = port
        self.daemon = True
        self.server = None

    def run(self):
        try:
            # Allow address reuse to avoid "Address already in use" errors on quick restarts
            socketserver.TCPServer.allow_reuse_address = True
            self.server = socketserver.TCPServer(("", self.port), LogRequestHandler)
            print(f"Web server started at http://localhost:{self.port}")
            self.server.serve_forever()
        except Exception as e:
            print(f"Failed to start web server: {e}")

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

# --- Main Application ---

def main():
    print("Web Monitor Server (Monitor + Web Log View)")
    print("===========================================")
    
    # Ensure config exists and load it
    config = ConfigManager.load()
    
    # Get web port
    try:
        port = int(config.get('web_port', 2442))
    except:
        port = 2442
        
    print(f"Config File: {CONFIG_FILE}")
    print(f"Log Directory: {LOG_DIR}")
    print(f"Web View: http://localhost:{port}")
    print("Press Ctrl+C to stop.")
    print("===========================================")
    
    # Start Monitor
    monitor = MonitorThread()
    monitor.start()
    
    # Start Web Server
    web_server = WebServerThread(port)
    web_server.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping services...")
        monitor.stop()
        monitor.join()
        # Web server is daemon, will exit with main thread
        print("Stopped. Exiting.")

if __name__ == "__main__":
    main()
