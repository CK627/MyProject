const socket = io();
let currentTarget = null;
let myId = null; // Will be set if needed, or we just rely on 'is_self'

// Connection events
socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('new_message', (data) => {
    // Check if sender is in the list
    let userItem = document.getElementById(`user-${data.sender}`);
    
    // If user not in list, add them dynamically
    if (!userItem) {
        addUserToList(data.sender, data.nickname || 'Unknown');
        userItem = document.getElementById(`user-${data.sender}`);
    } else {
        // If user exists but we now have a better nickname (and it was unknown before), update it
        // Or if the nickname changed.
        if (data.nickname && data.nickname !== 'Unknown') {
            const displayName = `${data.nickname} (${data.sender})`;
            // Only update if current text doesn't contain the new nickname or if it was just IP
            if (!userItem.innerText.includes(data.nickname)) {
                // Preserve (New) or (新消息) badge if present
                const hasBadge = userItem.innerText.includes('(新消息)');
                userItem.innerText = displayName + (hasBadge ? ' (新消息)' : '');
            }
        }
    }

    // If the message is from the user we are currently chatting with, show it
    if (currentTarget === data.sender) {
        appendMessage(data.content, 'received', data.timestamp);
    } else {
        // Mark user as having new messages (visual cue)
        if (userItem) {
            userItem.style.fontWeight = 'bold';
            if (!userItem.innerText.includes('(新消息)')) {
                userItem.innerText += ' (新消息)';
            }
        }
    }
});

function addUserToList(ip, nickname) {
    const list = document.getElementById('userList');
    // Check again to avoid duplicates if called rapidly
    if (document.getElementById(`user-${ip}`)) return;
    
    // Remove "No users found" if present
    const noUsers = list.querySelector('li[style*="font-style: italic"]');
    if (noUsers) {
        noUsers.remove();
    }
    
    const displayName = nickname !== 'Unknown' ? `${nickname} (${ip})` : ip;
    const li = document.createElement('li');
    li.id = `user-${ip}`;
    li.innerText = displayName;
    li.onclick = () => selectUser(ip, nickname);
    list.appendChild(li);
}

socket.on('message_sent', (data) => {
    if (currentTarget === data.target) {
        appendMessage(data.content, 'sent', data.timestamp);
    }
});

socket.on('error', (data) => {
    alert(data.message);
});

socket.on('settings_updated', (data) => {
    alert('存储路径已更新为: ' + data.path);
    toggleSettings();
});

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadInterfaces();
});

function loadInterfaces() {
    fetch('/api/interfaces')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('interfaceSelect');
            data.interfaces.forEach(iface => {
                const option = document.createElement('option');
                option.value = iface.cidr;
                option.text = `${iface.name} (${iface.ip})`;
                select.appendChild(option);
            });
            
            // Auto select the first interface if available
            if (data.interfaces.length > 0) {
                select.value = data.interfaces[0].cidr;
            }
        })
        .catch(err => console.error('加载网络接口失败:', err));
}

// UI Functions
let isScanning = false;
let scanController = null;

function scanNetwork() {
    const btn = document.getElementById('scanBtn');
    const stopBtn = document.getElementById('stopScanBtn');
    const select = document.getElementById('interfaceSelect');
    const cidr = select.value;

    if (!cidr) {
        alert("请先选择一个网络接口。");
        return;
    }

    isScanning = true;
    btn.disabled = true;
    btn.innerText = '扫描中...';
    btn.style.display = 'none';
    stopBtn.style.display = 'inline-block';
    stopBtn.disabled = false;
    select.disabled = true;
    
    // We can use AbortController if fetch supports it, but here we rely on backend stop
    // Or we just send a request to start scanning.
    
    fetch(`/scan?cidr=${encodeURIComponent(cidr)}`)
        .then(response => response.json())
        .then(data => {
            const list = document.getElementById('userList');
            list.innerHTML = '';
            if (data.hosts.length === 0) {
                list.innerHTML = '<li style="color: #666; font-style: italic;">未发现用户</li>';
            }
            data.hosts.forEach(host => {
                let ip = host.ip || host; 
                let nickname = host.nickname || 'Unknown';
                let displayName = nickname !== 'Unknown' ? `${nickname} (${ip})` : ip;
                
                const li = document.createElement('li');
                li.id = `user-${ip}`;
                li.innerText = displayName;
                li.onclick = () => selectUser(ip, nickname);
                list.appendChild(li);
            });
            resetScanUI();
        })
        .catch(err => {
            console.error(err);
            resetScanUI();
        });
}

function stopScan() {
    fetch('/stop_scan')
        .then(response => response.json())
        .then(data => {
            // Backend should stop the scan loop and return partial results or empty
            // The original /scan request will then complete.
            // But we can also force UI reset here.
            console.log("Scan stop requested");
        });
}

function resetScanUI() {
    isScanning = false;
    const btn = document.getElementById('scanBtn');
    const stopBtn = document.getElementById('stopScanBtn');
    const select = document.getElementById('interfaceSelect');
    
    btn.disabled = false;
    btn.innerText = '扫描';
    btn.style.display = 'inline-block';
    
    stopBtn.style.display = 'none';
    stopBtn.disabled = true;
    
    select.disabled = false;
}

function selectUser(ip, nickname) {
    currentTarget = ip;
    const displayName = nickname && nickname !== 'Unknown' ? `${nickname} (${ip})` : ip;
    document.getElementById('chatHeader').innerText = `正在与 ${displayName} 聊天`;
    document.getElementById('msgInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('fileBtn').disabled = false;
    
    // Clear messages or load history
    document.getElementById('messages').innerHTML = '';
    
    // Fetch and load history
    fetch(`/api/history?peer=${ip}`)
        .then(res => res.json())
        .then(data => {
            if (data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    // msg: {content, type, timestamp, direction}
                    // We need to map 'direction' to 'sent' or 'received' CSS classes if needed
                    // In storage.py we set 'direction' to 'sent' or 'received' directly
                    appendMessage(msg.content, msg.direction, msg.timestamp);
                });
            }
        })
        .catch(err => console.error("Failed to load history:", err));
    
    // Highlight active user
    document.querySelectorAll('#userList li').forEach(li => li.classList.remove('active'));
    const activeLi = document.getElementById(`user-${ip}`);
    if (activeLi) {
        activeLi.classList.add('active');
        // Remove "New" badge if present
        if (activeLi.innerText.includes('(新消息)')) {
            activeLi.innerText = displayName;
            activeLi.style.fontWeight = 'normal';
        }
    }
}

function editNickname() {
    const current = document.getElementById('myNickname').innerText;
    const newNickname = prompt("请输入新的昵称:", current);
    if (newNickname && newNickname !== current) {
        fetch('/api/update_nickname', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ nickname: newNickname })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                document.getElementById('myNickname').innerText = data.nickname;
            } else {
                alert("修改失败");
            }
        });
    }
}

function triggerFileUpload() {
    document.getElementById('fileInput').click();
}

document.getElementById('fileInput').addEventListener('change', function(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    // For large files, we might need chunking or a direct HTTP upload instead of SocketIO
    // For simplicity, let's use FileReader and send via socket if small, 
    // or implement an upload API. Given requirements, let's use HTTP upload API.
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('target_ip', currentTarget);
    
    fetch('/api/upload_file', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            appendMessage(`File sent: ${file.name}`, 'sent', new Date().toLocaleTimeString());
        } else {
            alert('File upload failed: ' + data.message);
        }
    })
    .catch(err => {
        console.error(err);
        alert('File upload error');
    });
    
    // Reset input
    this.value = '';
});

function sendMessage() {
    const input = document.getElementById('msgInput');
    const content = input.value.trim();
    if (!content || !currentTarget) return;
    
    socket.emit('send_message', {
        target_ip: currentTarget,
        content: content,
        type: 'text'
    });
    
    input.value = '';
}

function appendMessage(content, type, timestamp) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    
    // Check if content looks like a file path or file message
    // Previously we sent: "[File] filename" but content in storage was the path.
    // The history loading might return the full path or the message content.
    // Let's handle both.
    
    let displayContent = content;
    
    if (content.startsWith('[File] ')) {
        // It's a file message notification (e.g. from receive_file)
        const filename = content.substring(7);
        displayContent = `📁 文件: <a href="/api/download/${encodeURIComponent(filename)}" target="_blank">${filename}</a>`;
    } else if (content.includes('FileStorage')) {
        // It's a raw path from history (e.g. .../FileStorage/filename.ext)
        // We need to extract basename
        // Assuming path separator is / or \
        const parts = content.split(/[/\\]/);
        const filename = parts[parts.length - 1];
        displayContent = `📁 文件: <a href="/api/download/${encodeURIComponent(filename)}" target="_blank">${filename}</a>`;
    }
    
    // Also handle "File sent: filename" from sender side
    if (content.startsWith('File sent: ')) {
         const filename = content.substring(11);
         displayContent = `📁 已发送文件: <a href="/api/download/${encodeURIComponent(filename)}" target="_blank">${filename}</a>`;
    }

    div.className = `message ${type}`;
    div.innerHTML = `
        <div class="content">${displayContent}</div>
        <div class="meta">${timestamp}</div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

// Settings
function toggleSettings() {
    const modal = document.getElementById('settingsModal');
    modal.style.display = modal.style.display === 'block' ? 'none' : 'block';
}

function saveSettings() {
    const path = document.getElementById('storagePath').value;
    if (path) {
        socket.emit('update_settings', { path: path });
    }
}

// Handle Enter key
document.getElementById('msgInput').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        sendMessage();
    }
});
