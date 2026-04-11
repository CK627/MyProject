import configparser
import os
from tkinter import Tk, Label, Entry, Button, messagebox, Frame

CONFIG_FILE = 'config.ini'
DEFAULT_CONFIG = {
    "url": "http://www.baidu.com",
    "expected_code": "200",
    "sender_email": "<YOUR_EMAIL@example.com>",
    "auth_code": "<YOUR_SMTP_AUTH_CODE>"
}

def load_config():
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

def save_config(new_settings):
    config = configparser.ConfigParser()
    config['Settings'] = new_settings
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        config.write(f)

def main():
    root = Tk()
    root.title("配置")
    
    # Increase window size
    window_width = 450
    window_height = 250
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    center_x = int(screen_width/2 - window_width/2)
    center_y = int(screen_height/2 - window_height/2)
    root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
    
    config = load_config()
    
    # URL
    Label(root, text="目标网站 URL:").pack(pady=(15, 5))
    url_entry = Entry(root, width=50)
    url_entry.insert(0, config.get('url', ''))
    url_entry.pack(pady=5)
    
    # Expected Code
    Label(root, text="期望状态码:").pack(pady=5)
    code_entry = Entry(root, width=50)
    code_entry.insert(0, str(config.get('expected_code', '')))
    code_entry.pack(pady=5)

    # Note about email config
    Label(root, text="注意：邮箱配置请直接修改 config.ini 文件", fg="gray").pack(pady=5)

    def on_save():
        try:
            code = int(code_entry.get())
        except ValueError:
            messagebox.showerror("错误", "状态码必须是数字")
            return
        
        # Load current config to preserve email settings
        current_config = load_config()
            
        new_settings = {
            "url": url_entry.get(),
            "expected_code": str(code),
            "sender_email": current_config.get('sender_email', DEFAULT_CONFIG['sender_email']),
            "auth_code": current_config.get('auth_code', DEFAULT_CONFIG['auth_code'])
        }
        save_config(new_settings)
        messagebox.showinfo("保存成功", "配置已保存，请重启监控脚本以生效")
        
    def on_exit():
        root.destroy()

    # Button Frame - Moved up slightly by padding logic and window resizing
    btn_frame = Frame(root)
    btn_frame.pack(pady=20)
        
    # Larger buttons
    Button(btn_frame, text="保存配置", command=on_save, width=20, height=2).pack(side='left', padx=10)
    Button(btn_frame, text="退出配置", command=on_exit, width=20, height=2).pack(side='right', padx=10)
    
    root.mainloop()

if __name__ == "__main__":
    main()
