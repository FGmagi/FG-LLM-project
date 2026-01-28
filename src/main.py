#!/usr/bin/env python3
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

from .app import start_server

if __name__ == "__main__":
    # 入口：启动 FastAPI 服务
    start_server()
