import logging
import os
import sys

# Setup logging
log_file = os.path.expanduser("~/Documents/ChatRoomData/app.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(filename=log_file, level=logging.DEBUG, 
                    format='%(asctime)s %(levelname)s: %(message)s')

# Force requests to use charset_normalizer
try:
    import charset_normalizer
except ImportError:
    pass

# Redirect stderr to log
class LogFile:
    def write(self, message):
        if message.strip():
            logging.error(f"STDERR: {message.strip()}")
    def flush(self):
        pass

sys.stderr = LogFile()

try:
    from flask import Flask, render_template, request, jsonify, send_from_directory, abort
    from flask_socketio import SocketIO, emit
    import threading
    import socket
    import requests
    import time
    import os
    import json
    from storage import StorageManager
    from scanner import NetworkScanner
    import sys
    import tkinter as tk
    from tkinter import messagebox
    import webbrowser
    import multiprocessing
except Exception as e:
    logging.critical(f"Import error: {e}")
    sys.exit(1)

# Freeze compatibility
if getattr(sys, 'frozen', False):
    # PyInstaller
    if hasattr(sys, '_MEIPASS'):
        base_dir = sys._MEIPASS
    else:
        # py2app
        base_dir = os.environ.get('RESOURCEPATH', os.path.dirname(os.path.abspath(__file__)))
        
    template_folder = os.path.join(base_dir, 'templates')
    static_folder = os.path.join(base_dir, 'static')
    
    # Log paths for debugging
    logging.info(f"Base dir: {base_dir}")
    logging.info(f"Template folder: {template_folder}")
    logging.info(f"Static folder: {static_folder}")
    
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    
    # Adjust config file path if frozen
    # Use Documents folder for config as well
    CONFIG_FILE = os.path.join(os.path.expanduser("~/Documents/ChatRoomData"), 'config.json')
else:
    app = Flask(__name__)
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

logging.info(f"Starting app with config: {CONFIG_FILE}")

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

def load_nickname_from_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('nickname', '')
        except:
            pass
    return ''

def save_nickname_to_config(nickname):
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except:
            pass
    
    config['nickname'] = nickname
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")

# Initialize modules
# Default nickname logic: try to get IP suffix, but initially might be unknown until interface is picked or default route used
def get_default_nickname():
    # 1. Try config first
    saved_nickname = load_nickname_from_config()
    if saved_nickname:
        return saved_nickname

    # 2. Fallback to IP suffix
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip.split('.')[-1]
    except:
        return "Unknown"

USER_NICKNAME = get_default_nickname()
USER_ID = f"user_{int(time.time())}" # Internal ID

DISCOVERY_PORT = "<DISCOVERY_PORT>" # Default: 5555
WEB_PORT = "<WEB_PORT>" # Default: 8080

storage = StorageManager(user_id=USER_ID)
scanner = NetworkScanner(port=DISCOVERY_PORT)

# Global state
active_chats = {} # IP -> list of messages

def discovery_listener():
    """
    Listens for discovery pings from other clients.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(('0.0.0.0', DISCOVERY_PORT))
        s.listen(5)
        print(f"Discovery listener started on port {DISCOVERY_PORT}")
        while True:
            conn, addr = s.accept()
            try:
                data = conn.recv(1024)
                if b"CHAT_DISCOVERY" in data:
                    # Respond with ACK and Nickname
                    response = f"CHAT_ACK:{USER_NICKNAME}".encode('utf-8')
                    conn.send(response)
            except:
                pass
            finally:
                conn.close()
    except Exception as e:
        print(f"Discovery listener failed: {e}")

@app.route('/')
def index():
    return render_template('index.html', user_id=USER_ID, nickname=USER_NICKNAME)

@app.route('/scan')
def scan_network():
    target_cidr = request.args.get('cidr')
    hosts = scanner.scan_network(target_cidr=target_cidr)
    return jsonify({"hosts": hosts})

@app.route('/stop_scan')
def stop_scan():
    scanner.stop_scan()
    return jsonify({"status": "ok"})

@app.route('/api/history')
def get_history():
    peer_ip = request.args.get('peer')
    if not peer_ip:
        return jsonify({"history": []})
        
    history = storage.get_history(peer_ip)
    return jsonify({"history": history})

@app.route('/api/download/<path:filename>')
def download_file(filename):
    """
    Serve files from the FileStorage directory.
    """
    try:
        return send_from_directory(storage.file_storage_path, filename, as_attachment=True)
    except FileNotFoundError:
        abort(404)

@app.route('/api/interfaces')
def get_interfaces():
    interfaces = scanner.get_interfaces()
    return jsonify({"interfaces": interfaces})

@app.route('/api/update_nickname', methods=['POST'])
def update_nickname():
    global USER_NICKNAME
    new_nickname = request.json.get('nickname')
    if new_nickname:
        USER_NICKNAME = new_nickname
        save_nickname_to_config(USER_NICKNAME)
        return jsonify({"status": "ok", "nickname": USER_NICKNAME})
    return jsonify({"status": "error"}), 400

@app.route('/api/upload_file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part"}), 400
    
    file = request.files['file']
    target_ip = request.form.get('target_ip')
    
    if file.filename == '':
        return jsonify({"status": "error", "message": "No selected file"}), 400
        
    if file and target_ip:
        # 1. Save locally (using our storage manager to save a copy in FileStorage)
        # We need to save it temporarily to send it? Or save permanently as "sent file"
        # Let's save it to FileStorage
        # But wait, storage.save_file expects a source path. 
        # We can save the uploaded file directly to storage.file_storage_path
        
        filename = file.filename
        safe_filename = os.path.basename(filename) # Basic sanitization
        local_path = os.path.join(storage.file_storage_path, safe_filename)
        
        # Avoid overwrite
        if os.path.exists(local_path):
            base, ext = os.path.splitext(safe_filename)
            local_path = os.path.join(storage.file_storage_path, f"{base}_{int(time.time())}{ext}")
            
        file.save(local_path)
        
        # 2. Send to remote peer
        # We need to upload this file to the remote peer's receive endpoint
        try:
            # Re-open the file to stream it
            with open(local_path, 'rb') as f:
                files = {'file': (safe_filename, f, file.content_type)}
                data = {'nickname': USER_NICKNAME}
                
                url = f"http://{target_ip}:{WEB_PORT}/api/receive_file"
                requests.post(url, files=files, data=data, timeout=10) # Longer timeout for files
                
            return jsonify({"status": "ok"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500
            
    return jsonify({"status": "error", "message": "Missing target or file"}), 400

@app.route('/api/receive_file', methods=['POST'])
def receive_file():
    if 'file' not in request.files:
        return jsonify({"status": "error"}), 400
        
    file = request.files['file']
    sender_ip = request.remote_addr
    nickname = request.form.get('nickname', 'Unknown')
    
    if file:
        filename = file.filename
        safe_filename = os.path.basename(filename)
        local_path = os.path.join(storage.file_storage_path, safe_filename)
        
        # Avoid overwrite
        if os.path.exists(local_path):
            base, ext = os.path.splitext(safe_filename)
            local_path = os.path.join(storage.file_storage_path, f"{base}_{int(time.time())}{ext}")
            
        file.save(local_path)
        
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        
        # Notify frontend
        socketio.emit('new_message', {
            'sender': sender_ip,
            'nickname': nickname,
            'content': f"[File] {filename}",
            'type': 'file',
            'timestamp': timestamp,
            'is_self': False,
            'file_path': local_path # Optional: if we want to allow opening it
        })
        
        # Log to history
        storage.save_message(f"FROM:{sender_ip}|TYPE:file|CONTENT:{local_path}")
        
        return jsonify({"status": "ok"})
        
    return jsonify({"status": "error"}), 400
@app.route('/api/receive_message', methods=['POST'])
def receive_message():
    """
    Endpoint to receive messages from other peers.
    """
    data = request.json
    sender_ip = request.remote_addr
    nickname = data.get('nickname', 'Unknown')
    content = data.get('content')
    msg_type = data.get('type', 'text')
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Save to storage
    storage.save_message(f"FROM:{sender_ip}|TYPE:{msg_type}|CONTENT:{content}")
    
    # Push to frontend
    socketio.emit('new_message', {
        'sender': sender_ip,
        'nickname': nickname,
        'content': content,
        'type': msg_type,
        'timestamp': timestamp,
        'is_self': False
    })
    
    return jsonify({"status": "ok"})

@socketio.on('send_message')
def handle_send_message(data):
    """
    Handle message sent from frontend.
    """
    target_ip = data['target_ip']
    content = data['content']
    msg_type = data.get('type', 'text')
    
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # 1. Save locally
    storage.save_message(f"TO:{target_ip}|TYPE:{msg_type}|CONTENT:{content}")
    
    # 2. Send to remote peer
    try:
        # Assuming remote peer is running on same port 5000
        url = f"http://{target_ip}:{WEB_PORT}/api/receive_message"
        requests.post(url, json={'content': content, 'type': msg_type, 'nickname': USER_NICKNAME}, timeout=2)
        
        # 3. Ack to frontend
        emit('message_sent', {
            'target': target_ip,
            'content': content,
            'timestamp': timestamp,
            'is_self': True
        })
    except Exception as e:
        emit('error', {'message': f"Failed to send to {target_ip}: {str(e)}"})

@socketio.on('update_settings')
def handle_settings(data):
    path = data.get('path')
    if path and os.path.exists(path):
        storage.set_custom_path(path)
        emit('settings_updated', {'path': storage.base_path})

@app.route('/api/shutdown', methods=['POST'])
def shutdown():
    """Shutdown the server."""
    socketio.stop()
    logging.info("Server shutting down...")
    return jsonify({"status": "ok"})

def run_app():
    logging.info("run_app started")
    # Start discovery thread
    t = threading.Thread(target=discovery_listener, daemon=True)
    t.start()
    
    # Start Web Server
    # Using 0.0.0.0 so it is accessible on the network
    try:
        logging.info("Starting SocketIO server")
        socketio.run(app, host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        print(f"Failed to start server: {e}")

# ... existing imports ...
import tkinter as tk
from tkinter import messagebox
import webbrowser
import multiprocessing
import sys
import os

# ... existing code ...

class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("智慧校园聊天室控制台")
        self.root.geometry("300x250")
        
        # Center the window
        self.center_window()
        
        self.process = None
        
        # Status Label
        self.status_label = tk.Label(root, text="状态: 已停止", fg="red", font=("Helvetica", 12, "bold"))
        self.status_label.pack(pady=20)
        
        # Buttons Frame
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        
        self.start_btn = tk.Button(btn_frame, text="启动服务", command=self.start_server, width=12)
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.stop_btn = tk.Button(btn_frame, text="停止服务", command=self.stop_server, width=12, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=1, padx=5)
        
        self.browser_btn = tk.Button(root, text="打开浏览器", command=self.open_browser, width=20)
        self.browser_btn.pack(pady=10)

        self.exit_btn = tk.Button(root, text="退出程序", command=self.on_close, width=20, fg="red")
        self.exit_btn.pack(pady=5)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))

    def start_server(self):
        if self.process and self.process.is_alive():
            return
            
        logging.info("Starting server thread...")
        self.process = threading.Thread(target=run_app, daemon=True)
        self.process.start()
        
        self.status_label.config(text="状态: 运行中", fg="green")
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL, text="停止服务")
        
    def stop_server(self):
        try:
            logging.info("Stopping server...")
            requests.post(f"http://localhost:{WEB_PORT}/api/shutdown", timeout=1)
        except Exception as e:
            logging.error(f"Error stopping server: {e}")
            
        # Wait for thread to finish (optional, but good for UI update)
        if self.process:
            self.process.join(timeout=2)
            
        self.status_label.config(text="状态: 已停止", fg="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def open_browser(self):
        webbrowser.open("http://localhost:8080")
        
    def on_close(self):
        self.root.destroy()
        sys.exit(0)

if __name__ == '__main__':
    try:
        logging.info("Entering main block")
        # Needed for PyInstaller with multiprocessing
        multiprocessing.freeze_support()
        
        logging.info("Initializing Tkinter root")
        root = tk.Tk()
        logging.info("Initializing ServerGUI")
        gui = ServerGUI(root)
        logging.info("Starting mainloop")
        root.mainloop()
    except Exception as e:
        logging.critical(f"Crash in main block: {e}", exc_info=True)
        try:
            messagebox.showerror("Error", f"Application crashed:\n{e}")
        except:
            pass
        sys.exit(1)
