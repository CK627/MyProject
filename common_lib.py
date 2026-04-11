import os
import configparser
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from datetime import datetime

CONFIG_FILE = 'config.ini'
LOG_DIR = 'logs'
DEFAULT_CONFIG = {
    "url": "http://www.baidu.com",
    "expected_code": "200",
    "sender_email": "<YOUR_EMAIL@example.com>",
    "auth_code": "<YOUR_SMTP_AUTH_CODE>",
    "web_port": "2442"
}

SMTP_SERVER = '<YOUR_SMTP_SERVER>'
SMTP_PORT = 465

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
