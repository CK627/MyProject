import sys
import os
import time
import random
import threading
import smtplib
import requests
import subprocess
import configparser
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
import pystray
from PIL import Image, ImageDraw

# --- Configuration & Constants ---
CONFIG_FILE = 'config.ini'
LOG_DIR = 'logs'
DEFAULT_CONFIG = {
    "url": "http://www.baidu.com",
    "expected_code": "200",
    "sender_email": "<YOUR_EMAIL@example.com>",
    "auth_code": "<YOUR_SMTP_AUTH_CODE>"
}

# Email Configuration - Will be loaded from config
SMTP_SERVER = '<YOUR_SMTP_SERVER>'
SMTP_PORT = 465

# --- Helper Classes ---

class ConfigManager:
    @staticmethod
    def load():
        config = configparser.ConfigParser()
        if not os.path.exists(CONFIG_FILE):
            config['Settings'] = DEFAULT_CONFIG
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    config.write(f)
            except Exception:
                pass
            return DEFAULT_CONFIG
        
        try:
            config.read(CONFIG_FILE, encoding='utf-8')
            if 'Settings' in config:
                loaded_config = dict(config['Settings'])
                # Check for missing keys and add them
                changed = False
                for key, value in DEFAULT_CONFIG.items():
                    if key not in loaded_config:
                        config['Settings'][key] = value
                        loaded_config[key] = value
                        changed = True
                
                if changed:
                    try:
                        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                            config.write(f)
                    except Exception:
                        pass
                
                return loaded_config
            else:
                # If section missing, recreate it
                config['Settings'] = DEFAULT_CONFIG
                try:
                    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                        config.write(f)
                except Exception:
                    pass
                return DEFAULT_CONFIG
        except Exception:
            return DEFAULT_CONFIG

class Logger:
    @staticmethod
    def log(status_code, status_msg, next_check_time):
        if not os.path.exists(LOG_DIR):
            os.makedirs(LOG_DIR)
        
        config = ConfigManager.load()
        url = config.get('url', 'Unknown URL')
        
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = os.path.join(LOG_DIR, f"{today}.log")
        
        current_time = datetime.now().strftime('%H:%M:%S')
        # Format: 24小时制:分:秒-状态码-情况-下一次检测时间-域名
        log_entry = f"{current_time}-{status_code}-{status_msg}-{next_check_time}-{url}\n"
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Log error: {e}")

class EmailSender:
    @staticmethod
    def send_email(subject, content):
        config = ConfigManager.load()
        sender_email = config.get('sender_email', DEFAULT_CONFIG['sender_email'])
        auth_code = config.get('auth_code', DEFAULT_CONFIG['auth_code'])
        
        try:
            message = MIMEText(content, 'plain', 'utf-8')
            # Fix: Use formataddr for RFC compliant From/To headers
            message['From'] = formataddr(("WebMonitor", sender_email))
            message['To'] = formataddr(("Admin", sender_email))
            message['Subject'] = Header(subject, 'utf-8')
            
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
            server.login(sender_email, auth_code)
            server.sendmail(sender_email, [sender_email], message.as_string())
            server.quit()
            print(f"Email sent: {subject}")
        except Exception as e:
            print(f"Failed to send email: {e}")

    @staticmethod
    def send_alert(status_code, error_msg):
        config = ConfigManager.load()
        url = config.get('url', 'Unknown URL')
        expected = config.get('expected_code', '200')
        
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        subject = f"网站异常报备：{url}-{expected}"

        # Content format: 年-月-日-24小时制-分-秒-状态码-不正常情况
        content = f"{current_time}-{status_code}-{error_msg}"
        EmailSender.send_email(subject, content)

    @staticmethod
    def send_recovery(status_code):
        config = ConfigManager.load()
        url = config.get('url', 'Unknown URL')
        
        current_time = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        subject = f"网站恢复报备：{url}-{status_code}"
        # Content format: 年-月-日-24小时制-分-秒-状态码-已恢复
        content = f"{current_time}-{status_code}-已恢复"
        EmailSender.send_email(subject, content)

# --- Monitor Logic ---

class MonitorThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set() # Initially running (not paused)
        self.daemon = True # Allow app to exit even if thread is running
        self.is_abnormal = False # Track previous state to handle alert/recovery logic

    def run(self):
        print("Monitor started.")
        while not self.stop_event.is_set():
            self.pause_event.wait() # Block if paused
            
            if self.stop_event.is_set():
                break

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

    def pause(self):
        self.pause_event.clear()
        print("Monitor paused.")

    def resume(self):
        self.pause_event.set()
        print("Monitor resumed.")

    def stop(self):
        self.stop_event.set()
        self.pause_event.set() # Ensure it unblocks to exit
        print("Monitor stopped.")

# --- Main Application Logic ---

class App:
    def __init__(self):
        self.monitor = None
        self.state = "stopped" # stopped, running, paused
        self.icon = None

    def create_image(self):
        # Create a simple icon programmatically
        width = 64
        height = 64
        color1 = "blue"
        color2 = "white"
        image = Image.new('RGB', (width, height), color1)
        dc = ImageDraw.Draw(image)
        dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
        dc.rectangle((0, height // 2, width // 2, height), fill=color2)
        return image

    # Menu Actions
    def on_config(self, icon, item):
        # Run config_gui.py in a separate process to avoid thread conflicts
        try:
            subprocess.Popen([sys.executable, 'config_gui.py'])
        except Exception as e:
            print(f"Error launching config GUI: {e}")

    def on_start(self, icon, item):
        if self.monitor and self.monitor.is_alive():
            return
        self.monitor = MonitorThread()
        self.monitor.start()
        self.state = "running"
        self.update_menu()

    def on_pause(self, icon, item):
        if self.monitor:
            self.monitor.pause()
            self.state = "paused"
            self.update_menu()

    def on_resume(self, icon, item):
        if self.monitor:
            self.monitor.resume()
            self.state = "running"
            self.update_menu()

    def on_stop(self, icon, item):
        if self.monitor:
            self.monitor.stop()
            self.monitor.join() # Wait for it to stop
            self.monitor = None
        self.state = "stopped"
        self.update_menu()

    def on_restart(self, icon, item):
        self.on_stop(icon, item)
        self.icon.stop()
        # Use a new process to restart the script to ensure a clean state and config reload
        try:
            subprocess.Popen([sys.executable, __file__])
        except Exception as e:
            print(f"Error restarting script: {e}")
        sys.exit(0)

    def on_exit(self, icon, item):
        self.on_stop(icon, item)
        icon.stop()

    def update_menu(self):
        # Trigger icon update to refresh menu state
        if self.icon:
            self.icon.update_menu()

    def run(self):
        # Define menu structure
        # Note: pystray menu items are static, but their 'enabled' state can be dynamic
        
        menu = pystray.Menu(
            pystray.MenuItem("网站状态侦测", pystray.Menu(
                pystray.MenuItem("打开GUI配置", self.on_config),
                pystray.MenuItem("脚本启动", self.on_start, enabled=lambda i: self.state == "stopped"),
                pystray.MenuItem("脚本暂停", self.on_pause, enabled=lambda i: self.state == "running"),
                pystray.MenuItem("脚本继续", self.on_resume, enabled=lambda i: self.state == "paused"),
                pystray.MenuItem("脚本结束", self.on_stop, enabled=lambda i: self.state in ["running", "paused"])
            )),
            pystray.MenuItem("程序进程", pystray.Menu(
                pystray.MenuItem("重启脚本", self.on_restart),
                pystray.MenuItem("退出脚本", self.on_exit)
            ))
        )

        self.icon = pystray.Icon("WebMonitor", self.create_image(), "Web Monitor", menu)
        self.icon.run()

if __name__ == "__main__":
    app = App()
    app.run()
