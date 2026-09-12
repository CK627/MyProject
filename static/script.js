const socket = io();
let currentTarget = null; // private chat peer IP
let isGroup = false;      // whether we are viewing the group chat
let groupUnread = 0;      // unread group messages while not viewing the group

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// Connection events
socket.on('connect', () => {
    console.log('Connected to server');
});

// ---- Group chat events ----
socket.on('group_message', (data) => {
    if (isGroup) {
        appendGroupMessage(data.nickname, data.sender, data.content, data.type, data.timestamp, data.is_self);
    } else {
        groupUnread++;
        updateGroupUnread();
    }
});

socket.on('member_list', (data) => {
    renderGroupMembers(data.members || []);
});

// ---- Private chat events ----
socket.on('new_message', (data) => {
    // Check if sender is in the list
    let userItem = document.getElementById(`user-${data.sender}`);

    // If user not in list, add them dynamically
    if (!userItem) {
        addUserToList(data.sender, data.nickname || 'Unknown');
        userItem = document.getElementById(`user-${data.sender}`);
    } else {
        if (data.nickname && data.nickname !== 'Unknown') {
            const displayName = `${data.nickname} (${data.sender})`;
            if (!userItem.innerText.includes(data.nickname)) {
                const hasBadge = userItem.innerText.includes('(新消息)');
                userItem.innerText = displayName + (hasBadge ? ' (新消息)' : '');
            }
        }
    }

    // If the message is from the user we are currently chatting with, show it
    if (!isGroup && currentTarget === data.sender) {
        appendMessage(data.content, 'received', data.timestamp);
    } else {
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
    if (document.getElementById(`user-${ip}`)) return;

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
    if (!isGroup && currentTarget === data.target) {
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

            if (data.interfaces.length > 0) {
                select.value = data.interfaces[0].cidr;
            }
        })
        .catch(err => console.error('加载网络接口失败:', err));
}

// ---- Group chat ----
function selectGroup() {
    isGroup = true;
    currentTarget = null;
    groupUnread = 0;
    updateGroupUnread();

    document.getElementById('groupEntry').classList.add('active');
    document.querySelectorAll('#userList li').forEach(li => li.classList.remove('active'));

    document.getElementById('chatHeader').innerText = '群聊';
    document.getElementById('groupMembers').style.display = 'flex';
    document.getElementById('messages').innerHTML = '';

    document.getElementById('msgInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('fileBtn').disabled = true; // group file sharing not yet supported

    // Load group history
    fetch('/api/group/history')
        .then(res => res.json())
        .then(data => {
            (data.history || []).forEach(msg => {
                const isSelf = (msg.ip && msg.ip === (window.MY_ID || null)) || false;
                appendGroupMessage(msg.nickname, msg.ip, msg.content, msg.type, msg.timestamp, isSelf);
            });
        })
        .catch(err => console.error('加载群聊历史失败:', err));

    // Load group members
    fetch('/api/group/members')
        .then(res => res.json())
        .then(data => renderGroupMembers(data.members || []))
        .catch(err => console.error('加载群成员失败:', err));
}

function renderGroupMembers(members) {
    const bar = document.getElementById('groupMembers');
    bar.innerHTML = '';

    const label = document.createElement('span');
    label.className = 'member-label';
    label.innerText = `在线 (${members.length})`;
    bar.appendChild(label);

    members.forEach(m => {
        const chip = document.createElement('span');
        chip.className = 'member-chip' + (m.uid === window.MY_ID ? ' me' : '');
        chip.innerText = m.uid === window.MY_ID ? `${m.nickname} (我)` : m.nickname;
        bar.appendChild(chip);
    });
}

function updateGroupUnread() {
    const badge = document.getElementById('groupUnread');
    if (groupUnread > 0) {
        badge.innerText = groupUnread;
        badge.style.display = 'inline-block';
    } else {
        badge.innerText = '';
        badge.style.display = 'none';
    }
}

function appendGroupMessage(nickname, ip, content, type, timestamp, isSelf) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');
    const senderLabel = isSelf ? '我' : (nickname && nickname !== 'Unknown' ? nickname : (ip || 'Unknown'));
    const displayContent = escapeHtml(content);

    div.className = `message ${isSelf ? 'sent' : 'received'} group`;
    div.innerHTML = `
        <div class="sender">${escapeHtml(senderLabel)}</div>
        <div class="content">${displayContent}</div>
        <div class="meta">${timestamp}</div>
    `;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
}

// ---- UI functions ----
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
    isGroup = false;
    currentTarget = ip;
    const displayName = nickname && nickname !== 'Unknown' ? `${nickname} (${ip})` : ip;

    document.getElementById('groupEntry').classList.remove('active');
    document.getElementById('groupMembers').style.display = 'none';
    document.getElementById('chatHeader').innerText = `正在与 ${displayName} 聊天`;
    document.getElementById('msgInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('fileBtn').disabled = false;

    // Clear messages or load history
    document.getElementById('messages').innerHTML = '';

    fetch(`/api/history?peer=${ip}`)
        .then(res => res.json())
        .then(data => {
            if (data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    appendMessage(msg.content, msg.direction, msg.timestamp);
                });
            }
        })
        .catch(err => console.error("Failed to load history:", err));

    document.querySelectorAll('#userList li').forEach(li => li.classList.remove('active'));
    const activeLi = document.getElementById(`user-${ip}`);
    if (activeLi) {
        activeLi.classList.add('active');
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

    this.value = '';
});

function sendMessage() {
    const input = document.getElementById('msgInput');
    const content = input.value.trim();
    if (!content) return;

    if (isGroup) {
        socket.emit('send_message', { scope: 'group', content: content, type: 'text' });
    } else if (currentTarget) {
        socket.emit('send_message', { target_ip: currentTarget, content: content, type: 'text' });
    } else {
        return;
    }

    input.value = '';
}

function appendMessage(content, type, timestamp) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');

    let displayContent = content;

    if (content.startsWith('[File] ')) {
        const filename = content.substring(7);
        displayContent = `📁 文件: <a href="/api/download/${encodeURIComponent(filename)}" target="_blank">${filename}</a>`;
    } else if (content.includes('FileStorage')) {
        const parts = content.split(/[/\\]/);
        const filename = parts[parts.length - 1];
        displayContent = `📁 文件: <a href="/api/download/${encodeURIComponent(filename)}" target="_blank">${filename}</a>`;
    }

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
