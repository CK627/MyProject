# -*- coding: utf-8 -*-
"""`python3 -m startupctl` 入口（未安装时在项目目录里直跑）。"""
import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
