// 服务端 async_mode='threading' 不支持 WebSocket，强制用 long-polling，
// 避免浏览器报 "Invalid frame header" 并导致消息接收不稳定。
const socket = io({ transports: ['polling'] });
let currentTarget = null; // private chat peer IP
let isGroup = false;      // whether we are viewing the group chat
let groupUnread = 0;      // unread group messages while not viewing the group

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

function formatTs(ts) {
    if (typeof ts === 'number') {
        return new Date(ts * 1000).toLocaleTimeString('zh-CN', { hour12: false });
    }
    return ts || '';
}

function escapeRegex(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function highlightMentions(content) {
    return escapeHtml(content).replace(/@([^\s@]+)/g, '<span class="mention">@$1</span>');
}

function isMentioned(content, nickname) {
    if (!content || !nickname) return false;
    const re = new RegExp('@' + escapeRegex(nickname) + '(?![\\w\\u4e00-\\u9fa5])');
    return re.test(content);
}

function notifyMentioned(sender) {
    try {
        if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
            new Notification('有人 @ 了你', { body: `${sender} 在群聊中提到了你` });
        }
    } catch (e) {}
}

function ticketTableHtml(initiator, progress, time) {
    return `
        <div class="ticket-title">📋 工单</div>
        <table class="ticket-table">
            <tr><th>时间</th><td>${escapeHtml(time)}</td></tr>
            <tr><th>发起人</th><td>${escapeHtml(initiator)}</td></tr>
            <tr><th>发送进度</th><td>${escapeHtml(progress)}</td></tr>
        </table>`;
}

function isImageFile(name) {
    return /\.(png|jpe?g|gif|webp|svg|bmp|ico)$/i.test(name);
}

function isTextFile(name) {
    return /\.(txt|md|log|json|csv|py|js|ts|css|html?|xml|yml|yaml|ini|conf|sh|bat|java|c|cpp|h|hpp|go|rs|properties)$/i.test(name);
}

function filePreviewHtml(filename, downloadUrl) {
    const downloadBtn = `<a class="file-download" href="${downloadUrl}" title="下载">⬇ 下载</a>`;
    if (isImageFile(filename)) {
        return `
            <div class="file-card">
                <div class="file-card-header">
                    <span class="file-card-name">🖼 ${escapeHtml(filename)}</span>
                    ${downloadBtn}
                </div>
                <img class="file-image" src="${downloadUrl}" alt="${escapeHtml(filename)}" title="点击放大"
                    onerror="onImageError(this)">
            </div>`;
    }
    if (isTextFile(filename)) {
        return `
            <div class="file-card">
                <div class="file-card-header">
                    <span class="file-card-name">📄 ${escapeHtml(filename)}</span>
                    ${downloadBtn}
                </div>
                <pre class="file-text-pre" data-url="${downloadUrl}">加载中…</pre>
            </div>`;
    }
    return `
        <div class="file-card">
            <div class="file-card-header">
                <span class="file-card-name">📁 ${escapeHtml(filename)}</span>
                ${downloadBtn}
            </div>
        </div>`;
}

function loadTextPreview(container) {
    const pre = container.querySelector('.file-text-pre');
    if (!pre) return;
    fetch(pre.dataset.url)
        .then(r => { if (!r.ok) throw new Error('bad'); return r.text(); })
        .then(t => { pre.textContent = t.length > 20000 ? t.slice(0, 20000) + '\n…（内容过长已截断）' : t; })
        .catch(() => { pre.textContent = '（内容加载失败，请点击文件名下载查看）'; });
}

function extractPrivateFilename(content) {
    if (content.startsWith('[File] ')) return content.substring(7);
    if (content.startsWith('File sent: ')) return content.substring(11);
    if (content.includes('FileStorage')) {
        const parts = content.split(/[/\\]/);
        return parts[parts.length - 1];
    }
    return null;
}

function onImageError(img) {
    const fallback = document.createElement('div');
    fallback.className = 'file-fallback';
    fallback.textContent = '⚠️ 图片无法加载（发送者可能已离线）';
    img.replaceWith(fallback);
}

function openImageModal(src) {
    document.getElementById('imageModalImg').src = src;
    document.getElementById('imageModal').style.display = 'block';
}

function closeImageModal() {
    document.getElementById('imageModal').style.display = 'none';
}

// 点击图片放大查看（下载走「下载」按钮）
document.getElementById('messages').addEventListener('click', (e) => {
    const img = e.target.closest('img.file-image');
    if (img) {
        openImageModal(img.src);
    }
});

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
        appendMessage(data.content, 'received', data.timestamp, data.type, data.nickname);
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
        appendMessage(data.content, 'sent', data.timestamp, data.type, data.nickname);
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
                // Prefer the default-route interface (usually the active Wi-Fi),
                // so LAN discovery targets the right subnet out of the box.
                const preferred = data.interfaces.find(i => i.is_default) || data.interfaces[0];
                select.value = preferred.cidr;
                // Auto-scan so peers are discovered and history backfills on load.
                scanNetwork();
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

    // 请求通知权限（用于 @ 提醒）
    if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
        try { Notification.requestPermission(); } catch (e) {}
    }

    document.getElementById('groupEntry').classList.add('active');
    document.querySelectorAll('#userList li').forEach(li => li.classList.remove('active'));

    document.getElementById('chatHeader').innerText = '群聊';
    document.getElementById('groupMembers').style.display = 'flex';
    document.getElementById('messages').innerHTML = '';

    document.getElementById('msgInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('ticketBtn').disabled = false;
    document.getElementById('fileBtn').disabled = false;

    // Load group history
    fetch('/api/group/history')
        .then(res => res.json())
        .then(data => {
            (data.history || []).forEach(msg => {
                appendGroupMessage(msg.nickname, msg.ip, msg.content, msg.type, msg.timestamp, !!msg.is_self);
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
        const isMe = (m.uid === window.MY_ID);
        const chip = document.createElement('span');
        chip.className = 'member-chip' + (isMe ? ' me' : ' mentionable');
        chip.innerText = isMe ? `${m.nickname} (我)` : m.nickname;
        if (!isMe) {
            chip.title = '点击 @ 提及';
            chip.onclick = () => mentionMember(m.nickname);
        }
        bar.appendChild(chip);
    });
}

function mentionMember(nickname) {
    const input = document.getElementById('msgInput');
    let val = input.value;
    if (val && !val.endsWith(' ')) {
        val += ' ';
    }
    input.value = val + `@${nickname} `;
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
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

    div.className = `message ${isSelf ? 'sent' : 'received'} group`;

    if (type === 'ticket') {
        const initiator = nickname && nickname !== 'Unknown' ? nickname : (ip || 'Unknown');
        div.innerHTML = ticketTableHtml(initiator, content, formatTs(timestamp));
    } else if (type === 'file') {
        const filename = content;
        // 自己发的文件在本机，用同源相对路径；别人发的文件用其真实来源 IP。
        const downloadUrl = isSelf
            ? `/api/download/${encodeURIComponent(filename)}`
            : `http://${ip}:${window.WEB_PORT || 8080}/api/download/${encodeURIComponent(filename)}`;
        div.innerHTML = `
            <div class="sender">${escapeHtml(senderLabel)}</div>
            <div class="content">${filePreviewHtml(filename, downloadUrl)}</div>
            <div class="meta">${formatTs(timestamp)}</div>
        `;
    } else {
        const displayContent = highlightMentions(content);
        if (isMentioned(content, window.MY_NICKNAME)) {
            div.classList.add('mentioned-me');
            notifyMentioned(senderLabel);
        }
        div.innerHTML = `
            <div class="sender">${escapeHtml(senderLabel)}</div>
            <div class="content">${displayContent}</div>
            <div class="meta">${formatTs(timestamp)}</div>
        `;
    }
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;

    // 文本文件：拉取内容内嵌显示
    loadTextPreview(div);
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
    document.getElementById('ticketBtn').disabled = false;
    document.getElementById('fileBtn').disabled = false;

    // Clear messages or load history
    document.getElementById('messages').innerHTML = '';

    fetch(`/api/history?peer=${ip}`)
        .then(res => res.json())
        .then(data => {
            if (data.history && data.history.length > 0) {
                data.history.forEach(msg => {
                    const initiator = msg.direction === 'sent' ? (window.MY_NICKNAME || '我') : (nickname && nickname !== 'Unknown' ? nickname : ip);
                    appendMessage(msg.content, msg.direction, msg.timestamp, msg.type, initiator);
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
    if (isGroup) {
        formData.append('scope', 'group');
    } else {
        formData.append('target_ip', currentTarget);
    }

    fetch('/api/upload_file', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'ok') {
            // 群聊时文件消息会通过 group_message 广播回来，无需本地追加
            if (!isGroup) {
                appendMessage(`File sent: ${file.name}`, 'sent', new Date().toLocaleTimeString());
            }
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

function sendTicket() {
    if (!isGroup && !currentTarget) return;

    // 自动填充时间与发起人（只读）
    document.getElementById('ticketTime').value = new Date().toLocaleString('zh-CN', { hour12: false });
    document.getElementById('ticketInitiator').value = window.MY_NICKNAME || 'Unknown';
    document.getElementById('ticketProgress').value = '';
    document.getElementById('ticketModal').style.display = 'block';
    document.getElementById('ticketProgress').focus();
}

function closeTicketModal() {
    document.getElementById('ticketModal').style.display = 'none';
}

function confirmSendTicket() {
    const content = document.getElementById('ticketProgress').value.trim();
    if (!content) {
        alert('请输入发送进度');
        return;
    }

    if (isGroup) {
        socket.emit('send_message', { scope: 'group', content: content, type: 'ticket' });
    } else if (currentTarget) {
        socket.emit('send_message', { target_ip: currentTarget, content: content, type: 'ticket' });
    }
    closeTicketModal();
}

function appendMessage(content, direction, timestamp, msgType, nickname) {
    const msgs = document.getElementById('messages');
    const div = document.createElement('div');

    div.className = `message ${direction}`;

    if (msgType === 'ticket') {
        const initiator = nickname || (direction === 'sent' ? (window.MY_NICKNAME || '我') : '对方');
        div.innerHTML = ticketTableHtml(initiator, content, formatTs(timestamp));
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
        return;
    }

    // 文件消息：与群聊一致的内嵌预览 + 下载按钮
    const filename = extractPrivateFilename(content);
    if (filename) {
        const downloadUrl = `/api/download/${encodeURIComponent(filename)}`;
        div.innerHTML = `
            <div class="content">${filePreviewHtml(filename, downloadUrl)}</div>
            <div class="meta">${timestamp}</div>
        `;
        msgs.appendChild(div);
        msgs.scrollTop = msgs.scrollHeight;
        loadTextPreview(div);
        return;
    }

    let displayContent = content;

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
