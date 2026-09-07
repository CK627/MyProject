import os
import sys

try:
    import yaml
except ImportError:  # PyYAML 未安装时仅使用内置默认值
    yaml = None

# 内置默认值,作为 config.yaml 缺失/缺键时的兜底。
# 日常修改请编辑项目根目录的 config.yaml,而非这里。
DEFAULTS = {
    'network': {
        'discovery_port': 5555,   # 局域网设备发现端口
        'web_port': 8080,         # Web 服务端口
        'host': '0.0.0.0',        # 监听地址
    },
    'storage': {
        'data_dir': '~/Documents/ChatRoomData',
    },
    'logging': {
        'log_file': '~/Documents/ChatRoomData/app.log',
    },
    'server': {
        'secret_key': 'secret!',
    },
    'scanner': {
        'timeout': 0.5,           # 单主机扫描超时(秒)
    },
    'messaging': {
        'send_timeout': 2,        # 消息发送超时(秒)
        'file_timeout': 10,       # 文件发送超时(秒)
    },
}


def _deep_merge(base, override):
    """递归合并 override 到 base(浅拷贝),返回新 dict。"""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _find_config_file():
    """按优先级返回配置文件路径,都不存在时返回 None。"""
    # 1. 用户自定义配置(打包后也可覆盖)
    user_config = os.path.expanduser('~/Documents/ChatRoomData/config.yaml')
    if os.path.exists(user_config):
        return user_config

    # 2. 项目根目录 / 打包资源内的默认模板
    if getattr(sys, 'frozen', False):
        base = (getattr(sys, '_MEIPASS', None)
                or os.environ.get('RESOURCEPATH')
                or os.path.dirname(os.path.abspath(__file__)))
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    bundled = os.path.join(base, 'config.yaml')
    if os.path.exists(bundled):
        return bundled

    return None


def load_config():
    """加载配置:默认值打底,YAML 覆盖。"""
    config = _deep_merge(DEFAULTS, {})
    path = _find_config_file()
    if path and yaml is not None:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            config = _deep_merge(config, data)
        except Exception:
            # 配置损坏时静默回退默认值,保证程序可启动
            pass
    return config


# 模块加载时读取一次,全局共享
CONFIG = load_config()


def get(*keys, default=None):
    """点路径取值,如 get('network', 'web_port')。"""
    node = CONFIG
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node
