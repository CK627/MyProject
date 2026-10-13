#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 CTF 取证训练数据集（仓库内实验脚本，**不随安装提供**）。

覆盖不同难度、复杂度、类型、编码、格式的训练样本，用于离线训练 JudgeNet。
用法: python3 lab/data_generator.py [-o lab/synthetic_data.jsonl] [--seed N]

输出格式: JSONL 每行一条样本，包含:
- v: 特征版本
- score: 扫描器置信度
- kind: 检测类型
- val: 候选值
- tok: 匹配令牌
- file_type: 文件类型 (capture/raw)
- module_scores: 模块置信度
- meta_score: MetaJudge 评分
- feats: 128 维特征向量
- label: 1=正样本 (flag), 0=负样本 (非 flag)
- group: 分组标识
- file: 文件标识
- note: 备注
"""
import json
import math
import os
import random
import time

# 仓库根入 sys.path：包里取特征函数（离线实验脚本，不在包目录内）
import sys
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from ctfsweep.core.judge import extract_features, FEATURES  # noqa: E402


# ================================================================= 数据生成器
class DataGenerator:
    """生成 CTF 取证训练数据。"""

    def __init__(self, seed=42):
        self.rnd = random.Random(seed)
        self.samples = []
        self.group_counter = 0

    def _next_group(self):
        self.group_counter += 1
        return f'group_{self.group_counter:03d}'

    def _add_sample(self, val, label, kind='明文flag', score=None, file_type='raw',
                    module_scores=None, meta_score=None, note='', tok=None,
                    file=None):
        """添加一个训练样本。"""
        if score is None:
            score = self.rnd.uniform(0.3, 0.95) if label == 1 else self.rnd.uniform(0.0, 0.7)
        if module_scores is None:
            module_scores = {
                'router': self.rnd.uniform(0.5, 1.0),
                'scanner': self.rnd.uniform(0.3, 0.9),
            }
        if meta_score is None:
            meta_score = self.rnd.uniform(0.4, 0.9) if label == 1 else self.rnd.uniform(0.1, 0.6)

        sample = {
            'v': 2,
            'score': score,
            'kind': kind,
            'val': val,
            'tok': tok or '',
            'file_type': file_type,
            'module_scores': module_scores,
            'meta_score': meta_score,
            'feats': extract_features({
                'score': score,
                'kind': kind,
                'tok': tok,
                'val': val,
                'file_type': file_type,
                'module_scores': module_scores,
                'meta_score': meta_score,
            }),
            'label': label,
            'group': self._next_group(),
            'file': file or 'unknown',
            'note': note,
            'collected_at': time.strftime('%Y-%m-%dT%H:%M:%S'),
        }
        self.samples.append(sample)

    # ================================================================= PCAP/网络流量
    def generate_pcap_samples(self, n_pos=50, n_neg=50):
        """生成 PCAP 网络流量样本。"""
        # 正样本 - flag 格式
        flag_formats = [
            'flag{network_traffic_analysis}',
            'SUCTF{pcap_forensics}',
            'CTF{packet_capture}',
            'flag{wireshark_master}',
            'flag{dns_tunnel_detection}',
            'flag{http_parsing}',
            'flag{tcp_stream_reassembly}',
            'flag{ssl_certificate}',
            'flag{arp_spoofing}',
            'flag{dhcp_discovery}',
        ]
        for flag in flag_formats:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='capture', note='PCAP flag 格式')

        # 正样本 - 网络相关线索
        network_clues = [
            '192.168.1.100:4444',
            '10.0.0.5:8080/admin',
            'user:password@172.16.0.1',
            'ftp://anonymous:ftp@192.168.1.50',
        ]
        for clue in network_clues:
            self._add_sample(clue, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.8),
                           file_type='capture', note='PCAP 网络线索')

        # 负样本 - 普通网络数据
        normal_network = [
            'GET /index.html HTTP/1.1',
            'Host: www.example.com',
            'User-Agent: Mozilla/5.0',
            'Accept: text/html,application/xhtml+xml',
            'HTTP/1.1 200 OK',
            'Content-Type: text/html; charset=utf-8',
            '192.168.1.1 -> 192.168.1.254',
            'TCP [tcp] Flags: [P.], seq 1:1461, ack 1, win 8192',
            'UDP [udp] Src Port: 53, Dst Port: 53',
            'DNS Query: www.google.com A',
        ]
        for item in normal_network:
            self._add_sample(item, label=0, kind='短文本响应', score=self.rnd.uniform(0.2, 0.5),
                           file_type='capture', note='PCAP 普通数据')

    # ================================================================= 内存取证
    def generate_memory_samples(self, n_pos=30, n_neg=30):
        """生成内存取证样本。"""
        # 正样本 - 内存中的 flag
        memory_flags = [
            'flag{memory_dump_analysis}',
            'SUCTF{volatile_forensics}',
            'flag{process_listing}',
            'flag{network_connections}',
            'flag{registry_keys}',
        ]
        for flag in memory_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='内存取证 flag')

        # 正样本 - 进程/连接信息
        process_info = [
            'svchost.exe 1234 5678 TCP 0.0.0.0:445',
            'chrome.exe 5678 9012 UDP 192.168.1.100:53',
            'cmd.exe /c whoami > C:\\temp\\output.txt',
            'powershell -enc SQBFAgAExABUAGUA',
        ]
        for info in process_info:
            self._add_sample(info, label=1, kind='命令回显', score=self.rnd.uniform(0.6, 0.8),
                           file_type='raw', note='内存进程信息')

        # 负样本 - 普通内存数据
        normal_memory = [
            '00000000  4d 5a 64 00 03 00 00 00',
            '00400000  00 00 00 00 00 00 00 00',
            'ntdll.dll 0x7ffe0000 0x7ffe1a00',
            'kernel32.dll 0x7ffe2000 0x7ffe3a00',
            '0x0012FF24  45 6e 75 6d 65 72 61 67',
        ]
        for item in normal_memory:
            self._add_sample(item, label=0, kind='明文', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='内存普通数据')

    # ================================================================= 浏览器取证
    def generate_browser_samples(self, n_pos=30, n_neg=30):
        """生成浏览器取证样本。"""
        # 正样本 - 浏览器中的 flag
        browser_flags = [
            'flag{browser_history}',
            'SUCTF{cookie_theft}',
            'flag{download_history}',
        ]
        for flag in browser_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='浏览器取证 flag')

        # 正样本 - 浏览器线索
        browser_clues = [
            'https://evil.com/steal?cookie=',
            'http://192.168.1.100:8080/login?user=admin&pass=secret',
            'chrome://password-manager/passwords',
            'https://mail.google.com/mail/u/0/#inbox',
        ]
        for clue in browser_clues:
            self._add_sample(clue, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='浏览器线索')

        # 负样本 - 普通浏览器数据
        normal_browser = [
            'https://www.google.com/search?q=python',
            'https://github.com/user/repo',
            'https://stackoverflow.com/questions/12345',
            'chrome-extension://abcdefghij/options.html',
            'about:blank',
        ]
        for item in normal_browser:
            self._add_sample(item, label=0, kind='短文本响应', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='浏览器普通数据')

    # ================================================================= 日志分析
    def generate_log_samples(self, n_pos=30, n_neg=30):
        """生成日志分析样本。"""
        # 正样本 - 日志中的 flag
        log_flags = [
            'flag{log_analysis}',
            'SUCTF{siemaster}',
            'flag{auth_bypass}',
        ]
        for flag in log_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='日志 flag')

        # 正样本 - 攻击日志
        attack_logs = [
            '401 Unauthorized POST /admin/login',
            'SQL injection attempt: UNION SELECT * FROM users',
            'XSS payload: <script>alert(1)</script>',
            'Failed login attempt for user admin from 10.0.0.5',
            'Brute force attack detected from 192.168.1.100',
        ]
        for log in attack_logs:
            self._add_sample(log, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='攻击日志')

        # 负样本 - 普通日志
        normal_logs = [
            '2024-01-01 12:00:00 INFO Server started',
            '2024-01-01 12:00:01 INFO Listening on port 8080',
            'GET /index.html 200 0.005s',
            'POST /api/data 200 0.012s',
            'Connection from 192.168.1.50:54321',
        ]
        for log in normal_logs:
            self._add_sample(log, label=0, kind='短文本响应', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='普通日志')

    # ================================================================= 邮件取证
    def generate_email_samples(self, n_pos=20, n_neg=20):
        """生成邮件取证样本。"""
        # 正样本 - 邮件中的 flag
        email_flags = [
            'flag{email_forensics}',
            'SUCTF{phishing_detection}',
        ]
        for flag in email_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='邮件 flag')

        # 正样本 - 邮件线索
        email_clues = [
            'SPF: fail (ip: 10.0.0.5)',
            'DKIM: signature invalid',
            'DMARC: policy=reject',
            'Received: from mail.evil.com (10.0.0.5)',
            'X-Originating-IP: 192.168.1.100',
        ]
        for clue in email_clues:
            self._add_sample(clue, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='邮件线索')

        # 负样本 - 普通邮件头
        normal_emails = [
            'From: user@example.com',
            'To: admin@company.com',
            'Subject: Meeting tomorrow',
            'Date: Mon, 1 Jan 2024 12:00:00 +0000',
            'MIME-Version: 1.0',
        ]
        for item in normal_emails:
            self._add_sample(item, label=0, kind='短文本响应', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='普通邮件头')

    # ================================================================= 数据库导出
    def generate_db_samples(self, n_pos=20, n_neg=20):
        """生成数据库导出样本。"""
        # 正样本 - 数据库中的 flag
        db_flags = [
            'flag{database_forensics}',
            'SUCTF{sql_injection}',
        ]
        for flag in db_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='数据库 flag')

        # 正样本 - 数据库线索
        db_clues = [
            "INSERT INTO users VALUES (1, 'admin', 'password123')",
            "SELECT * FROM credentials WHERE user='admin'",
            "password: admin_secret_key_2024",
            "api_key: AKIAIOSFODNN7EXAMPLE",
        ]
        for clue in db_clues:
            self._add_sample(clue, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='数据库线索')

        # 负样本 - 普通数据库数据
        normal_db = [
            "INSERT INTO users VALUES (1, 'john', 'john123')",
            "SELECT id, name FROM products",
            "UPDATE orders SET status='shipped' WHERE id=12345",
            "DROP TABLE temp_data",
        ]
        for item in normal_db:
            self._add_sample(item, label=0, kind='短文本响应', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='普通数据库数据')

    # ================================================================= 配置文件/密钥
    def generate_config_samples(self, n_pos=20, n_neg=20):
        """生成配置/密钥扫描样本。"""
        # 正样本 - 配置中的 flag
        config_flags = [
            'flag{config_analysis}',
            'SUCTF{secret_leak}',
        ]
        for flag in config_flags:
            self._add_sample(flag, label=1, kind='环境/配置', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='配置 flag')

        # 正样本 - 敏感配置
        config_clues = [
            'AWS_SECRET_KEY=AKIAIOSFODNN7EXAMPLE',
            'DB_PASSWORD=super_secret_password_2024',
            'JWT_SECRET=my_jwt_secret_key',
            'REDIS_PASSWORD=redis_pass_123',
            'SSH_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----',
        ]
        for clue in config_clues:
            self._add_sample(clue, label=1, kind='环境/配置', score=self.rnd.uniform(0.7, 0.9),
                           file_type='raw', note='敏感配置')

        # 负样本 - 普通配置
        normal_configs = [
            'server.port=8080',
            'database.host=localhost',
            'logging.level=INFO',
            'app.name=MyApplication',
            'spring.datasource.url=jdbc:mysql://localhost:3306/mydb',
        ]
        for item in normal_configs:
            self._add_sample(item, label=0, kind='环境/配置', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='普通配置')

    # ================================================================= 多层压缩
    def generate_archive_samples(self, n_pos=20, n_neg=20):
        """生成多层压缩样本。"""
        # 正样本 - 压缩包中的 flag
        archive_flags = [
            'flag{archive_forensics}',
            'SUCTF{zip_parsing}',
        ]
        for flag in archive_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='raw', note='压缩包 flag')

        # 正样本 - 压缩线索
        archive_clues = [
            'password: archive_password_2024',
            'extract_to: /tmp/extracted',
            'zipfile: malware.zip',
            '7z archive detected',
        ]
        for clue in archive_clues:
            self._add_sample(clue, label=1, kind='关键词', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='压缩线索')

        # 负样本 - 普通压缩数据
        normal_archives = [
            'PK\x03\x04 archive.zip',
            '7z\xbc\xaf\x27\x1d',
            'RARD!\x1a\x07',
            'application/zip',
        ]
        for item in normal_archives:
            self._add_sample(item, label=0, kind='明文', score=self.rnd.uniform(0.2, 0.5),
                           file_type='raw', note='普通压缩数据')

    # ================================================================= DNS 分析
    def generate_dns_samples(self, n_pos=20, n_neg=20):
        """生成 DNS 分析样本。"""
        # 正样本 - DNS 中的 flag
        dns_flags = [
            'flag{dns_tunnel}',
            'SUCTF{dga_detection}',
        ]
        for flag in dns_flags:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.85, 0.98),
                           file_type='capture', note='DNS flag')

        # 正样本 - DNS 线索
        dns_clues = [
            'aW1sZGVzdG9n.data.evil.com',
            'xkcd-random-long-domain-name-that-looks-like-dga.com',
            'base64-encoded-payload.dns-tunnel.evil.com',
            'TXT record: flag{dns_txt_record}',
        ]
        for clue in dns_clues:
            self._add_sample(clue, label=1, kind='DNS查询', score=self.rnd.uniform(0.6, 0.85),
                           file_type='capture', note='DNS 线索')

        # 负样本 - 普通 DNS
        normal_dns = [
            'www.google.com A',
            'mail.yahoo.com MX',
            'api.github.com A',
            'cdn.cloudflare.com CNAME',
        ]
        for item in normal_dns:
            self._add_sample(item, label=0, kind='DNS查询', score=self.rnd.uniform(0.2, 0.5),
                           file_type='capture', note='普通 DNS')

    # ================================================================= 编码数据
    def generate_encoding_samples(self, n_pos=20, n_neg=20):
        """生成编码数据样本。"""
        # 正样本 - 编码中的 flag
        encoded_flags = [
            ('flag{base64_decode}', 'ZmxhZ3tiYmFzZTYxZGVjb2RlXQ=='),
            ('SUCTF{hex_decode}', '53554354467b6865785f6465636f64657d'),
            ('flag{rot13_decode}', 'snyr{ebhr13_qrpbirf}'),
        ]
        for flag, encoded in encoded_flags:
            self._add_sample(encoded, label=1, kind='base64' if 'base64' in flag else 'hex',
                           score=self.rnd.uniform(0.7, 0.9), file_type='raw', note='编码 flag')

        # 正样本 - 编码线索
        encoded_clues = [
            'dXJsZ3NvY3RpbGVrbm9rZW50QHNjcj0=',  # JWT-like
            '48656c6c6f20576f726c64',  # Hello World
        ]
        for clue in encoded_clues:
            self._add_sample(clue, label=1, kind='base64', score=self.rnd.uniform(0.6, 0.85),
                           file_type='raw', note='编码线索')

        # 负样本 - 普通编码
        normal_encoding = [
            'SGVsbG8gV29k',  # Hi!
            '7468697320697320612074657374',  # this is a test
            'dGVzdA==',  # test
        ]
        for item in normal_encoding:
            self._add_sample(item, label=0, kind='base64', score=self.rnd.uniform(0.3, 0.6),
                           file_type='raw', note='普通编码')

    # ================================================================= 难/简单样本
    def generate_hard_samples(self, n_pos=20, n_neg=20):
        """生成高难度/低难度样本。"""
        # 简单正样本 - 明显 flag
        easy_pos = [
            'flag{easy_flag}',
            'FLAG{THIS_IS_EASY}',
            'flag{12345}',
        ]
        for flag in easy_pos:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.95, 0.99),
                           file_type='raw', note='简单正样本')

        # 困难正样本 - 隐写/编码
        hard_pos = [
            'flag{a1b2c3d4e5f6g7h8i9j0}',
            'SUCTF{st3gn0gr4phy_m4st3r}',
            'flag{xY9#kL2$mN5@pQ8}',
        ]
        for flag in hard_pos:
            self._add_sample(flag, label=1, kind='明文flag', score=self.rnd.uniform(0.7, 0.85),
                           file_type='raw', note='困难正样本')

        # 困难负样本 - 看起来像 flag 但不是
        hard_neg = [
            'flag{this_is_not_the_flag}',
            'FLAG{fake_flag_detected}',
            'CTF{not_the_real_ctf}',
            'password: flag{fake_flag}',
        ]
        for item in hard_neg:
            self._add_sample(item, label=0, kind='关键词', score=self.rnd.uniform(0.4, 0.7),
                           file_type='raw', note='困难负样本')

    # ================================================================= 片段拼接
    def generate_fragment_samples(self, n_pos=20, n_neg=20):
        """生成片段拼接样本。"""
        # 正样本 - 片段
        fragments_pos = [
            ('flag{frag', '片段(前)', 0.7),
            ('ment}_part1', '片段(尾)', 0.7),
            ('SUCTF{par', '片段(前)', 0.7),
            ('t2_done}', '片段(尾)', 0.7),
        ]
        for frag, kind, score in fragments_pos:
            self._add_sample(frag, label=1, kind=kind, score=score,
                           file_type='raw', note='片段拼接')

        # 负样本 - 普通片段
        fragments_neg = [
            ('This is a', '片段(前)', 0.3),
            ('test string', '片段(尾)', 0.3),
            ('Lorem ipsum', '片段(前)', 0.3),
            ('dolor sit', '片段(尾)', 0.3),
        ]
        for frag, kind, score in fragments_neg:
            self._add_sample(frag, label=0, kind=kind, score=score,
                           file_type='raw', note='普通片段')

    # ================================================================= 生成全部数据
    def generate_all(self, n_pos=400, n_neg=400):
        """生成全部训练数据。"""
        print('开始生成 CTF 取证训练数据...')

        # 按类别生成
        self.generate_pcap_samples(n_pos=n_pos // 8, n_neg=n_neg // 8)
        self.generate_memory_samples(n_pos=n_pos // 8, n_neg=n_neg // 8)
        self.generate_browser_samples(n_pos=n_pos // 8, n_neg=n_neg // 8)
        self.generate_log_samples(n_pos=n_pos // 8, n_neg=n_neg // 8)
        self.generate_email_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_db_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_config_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_archive_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_dns_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_encoding_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_hard_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)
        self.generate_fragment_samples(n_pos=n_pos // 10, n_neg=n_neg // 10)

        # 统计
        n_pos_actual = sum(1 for s in self.samples if s['label'] == 1)
        n_neg_actual = sum(1 for s in self.samples if s['label'] == 0)
        print(f'生成完成: 总计 {len(self.samples)} 条（正 {n_pos_actual} / 负 {n_neg_actual}）')

        return self.samples

    def save_to_file(self, output_path, samples=None):
        """保存样本到 JSONL 文件。"""
        samples = samples or self.samples
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')
        print(f'已保存到: {output_path}')
        return output_path


# ================================================================= 主函数
def main():
    """生成训练数据并保存。"""
    import argparse
    parser = argparse.ArgumentParser(description='生成 CTF 取证训练数据')
    parser.add_argument('-o', '--output', default=os.path.join(_ROOT, 'lab', 'synthetic_data.jsonl'),
                       help='输出文件路径')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')
    args = parser.parse_args()

    gen = DataGenerator(seed=args.seed)
    samples = gen.generate_all()
    gen.save_to_file(args.output, samples)

    # 统计信息
    n_pos = sum(1 for s in samples if s['label'] == 1)
    n_neg = sum(1 for s in samples if s['label'] == 0)
    print(f'\n训练数据统计:')
    print(f'  正样本: {n_pos} 条')
    print(f'  负样本: {n_neg} 条')
    print(f'  总计: {len(samples)} 条')
    print(f'\n提示: 运行 `python3 lab/train.py --data {args.output}` 开始训练')


if __name__ == '__main__':
    main()
