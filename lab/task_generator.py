# -*- coding: utf-8 -*-
"""题目生成器：通过 SSH 连接远程 Windows 机器生成 CTF 取证题目

功能：
- 生成 pcap 抓包题目
- 生成 evtx 事件日志题目
- 生成 registry 注册表题目
- 生成 memory 内存取证题目
- 生成 file_forensics 文件取证题目
- 每道题一个独立子文件夹
"""

import json
import os
import random
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path


class TaskGenerator:
    """题目生成器"""
    
    def __init__(self, config):
        self.config = config
        self.ssh_cmd = [
            "ssh",
            f"{config['ssh_user']}@{config['ssh_host']}",
        ]
    
    def generate_tasks(self):
        """生成题目（从 SSH 远程执行）"""
        tasks = []
        
        # 选择题目类型
        task_types = self.config.get("task_types", [
            "pcap", "evtx", "registry", "memory", "file_forensics"
        ])
        
        for task_type in task_types:
            try:
                task_dir = self._create_remote_task_dir(task_type)
                if task_dir:
                    tasks.append(task_dir)
                    print(f"  ✓ 生成 {task_type} 题目: {task_dir}")
            except Exception as e:
                print(f"  [ERROR] 生成 {task_type} 题目失败: {e}")
        
        return tasks
    
    def _create_remote_task_dir(self, task_type):
        """在远程创建题目目录"""
        base_dir = self.config["ssh_base_dir"]
        task_name = f"task_{task_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        task_dir = f"{base_dir}/{task_name}"
        
        # 在远程创建目录
        create_cmd = f"mkdir -p '{task_dir}'"
        self._ssh_run(create_cmd)
        
        # 生成题目内容
        generators = {
            "pcap": self._generate_pcap_task,
            "evtx": self._generate_evtx_task,
            "registry": self._generate_registry_task,
            "memory": self._generate_memory_task,
            "file_forensics": self._generate_file_forensics_task,
        }
        
        if task_type in generators:
            generators[task_type](task_dir)
        
        return task_dir
    
    def _generate_pcap_task(self, task_dir):
        """生成 pcap 抓包题目"""
        # 使用 Python 脚本生成模拟 pcap（通过 SSH 远程执行）
        script = """
import struct
import random
import time

# 创建简单的 pcap 文件（模拟 HTTP 流量）
packets = []

# 模拟 HTTP GET 请求
http_get = b"GET /flag.php HTTP/1.1\\r\\nHost: target.com\\r\\n\\r\\n"

# 模拟 HTTP 响应（包含 flag）
http_response = b"HTTP/1.1 200 OK\\r\\nContent-Type: text/html\\r\\n\\r\\n<html>flag{pcap_test_12345}</html>"

# 模拟 DNS 查询
dns_query = b"\\x00\\x01\\x01\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x05flag\\x03com\\x00\\x00\\x01\\x00\\x01"

# 模拟 Base64 编码数据
import base64
flag_b64 = base64.b64encode(b"flag{base64_in_pcap_12345}").decode()
base64_data = f"Data: {flag_b64}\\r\\n\\r\\n".encode()

# 写入 pcap 文件（简化版，实际需要使用 scapy）
with open("task_pcap.pcap", "wb") as f:
    # PCAP 全局头
    f.write(struct.pack("<IHHIIII", 
        0xa1b23c4d,  # magic
        2, 4,         # version
        0,            # thiszone
        0,            # sigfigs
        65535,        # snaplen
        1             # linktype (Ethernet)
    ))
    
    # 添加数据包
    for data in [http_get, http_response, dns_query, base64_data]:
        ts = int(time.time())
        ts_usec = random.randint(0, 999999)
        # 数据包头
        f.write(struct.pack("<IIII", ts, ts_usec, len(data), len(data)))
        f.write(data)

print("PCAP 题目生成完成")
"""
        
        self._ssh_run(f'cd "{task_dir}" && python3 -c "{script}"')
    
    def _generate_evtx_task(self, task_dir):
        """生成 evtx 事件日志题目"""
        # 生成模拟 evtx 内容（JSON 格式，实际应使用真实 evtx 格式）
        events = []
        for i in range(50):
            event = {
                "EventID": random.choice([4624, 4625, 4634, 4672, 4688, 4689, 4698, 4699]),
                "TimeCreated": datetime.now().isoformat(),
                "UserName": random.choice(["Administrator", "student", "user"]),
                "Message": f"事件日志模拟数据 #{i}",
            }
            
            # 注入 flag
            if i == 25:
                event["Message"] += " flag{evtx_test_12345}"
            
            events.append(event)
        
        evtx_path = Path(task_dir) / "task_evtx.json"
        with open(evtx_path, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ EVTX 题目生成完成: {evtx_path}")
    
    def _generate_registry_task(self, task_dir):
        """生成 registry 注册表题目"""
        # 生成模拟注册表内容
        registry_data = {
            "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run": {
                "Malware": "C:\\Malware\\payload.exe",
                "Backup": "C:\\Backup\\backup.exe",
            },
            "HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Services": {
                "SuspiciousService": "C:\\Suspicious\\service.exe",
            },
            "HKEY_CURRENT_USER\\Software\\CTF\\Flag": {
                "FlagValue": "flag{registry_test_12345}",
            },
        }
        
        reg_path = Path(task_dir) / "task_registry.reg"
        with open(reg_path, "w", encoding="utf-8") as f:
            f.write("Windows Registry Editor Version 5.00\\n\\n")
            for key, values in registry_data.items():
                f.write(f"[{key}]\\n")
                for k, v in values.items():
                    f.write(f'"{k}"="{v}"\\n')
                f.write("\\n")
        
        print(f"  ✓ Registry 题目生成完成: {reg_path}")
    
    def _generate_memory_task(self, task_dir):
        """生成 memory 内存取证题目"""
        # 生成模拟内存dump（简化版）
        memory_data = b"\\x00" * 1024  # 1KB 模拟内存
        
        # 注入 flag
        flag_pos = random.randint(100, 900)
        memory_data = memory_data[:flag_pos] + b"flag{memory_test_12345}" + memory_data[flag_pos+30:]
        
        mem_path = Path(task_dir) / "task_memory.raw"
        with open(mem_path, "wb") as f:
            f.write(memory_data)
        
        print(f"  ✓ Memory 题目生成完成: {mem_path}")
    
    def _generate_file_forensics_task(self, task_dir):
        """生成 file_forensics 文件取证题目"""
        # 生成模拟文件（包含隐藏信息）
        doc_content = """
这是模拟的文档内容。
包含一些敏感信息：
- 用户名: admin
- 密码: secret123
- Flag: flag{file_forensics_test_12345}
"""
        
        doc_path = Path(task_dir) / "task_document.docx"
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(doc_content)
        
        print(f"  ✓ File Forensics 题目生成完成: {doc_path}")
    
    def _ssh_run(self, command):
        """通过 SSH 执行命令"""
        try:
            full_cmd = self.ssh_cmd + [command]
            result = subprocess.run(
                full_cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"  [WARN] SSH 命令执行失败: {result.stderr}")
            
            return result
            
        except subprocess.TimeoutExpired:
            print(f"  [ERROR] SSH 命令超时: {command[:100]}")
        except Exception as e:
            print(f"  [ERROR] SSH 执行失败: {e}")
        
        return None


# ---------------------------------------------------------------- 辅助函数
def search_online_tasks():
    """从网络搜索 CTF 题目（预留接口）"""
    # 这里可以集成 WebSearch 或 domain_search
    # 搜索关键词：CTF 取证题目、forensics challenge、pcap challenge 等
    print("[INFO] 网络题目搜索功能预留")
    return []


if __name__ == "__main__":
    config = {
        "ssh_host": "ck-win",
        "ssh_user": "student",
        "ssh_base_dir": "C:/Users/student/Desktop/CTFLearn",
        "task_types": ["pcap", "evtx", "registry", "memory", "file_forensics"],
    }
    
    generator = TaskGenerator(config)
    tasks = generator.generate_tasks()
    print(f"\n[STATS] 共生成 {len(tasks)} 道题目")
