#!/usr/bin/env python3
"""
入口脚本：把当前项目路径加入 sys.path，然后调用 app.start_server()
"""
import sys
import os

# 将项目根目录加入 sys.path，确保 src 可被导入
ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(ROOT)

from .app import start_server

if __name__ == "__main__":
    # 检查伪数据路径（提示而不自动生成）
    from .config import DATA_FILE_PATH
    if not os.path.exists(DATA_FILE_PATH):
        print(f"警告: {DATA_FILE_PATH} 不存在。请先生成模拟数据放到该路径 (output/pseudo_data/data.json)。")
    # 启动服务（会阻塞）
    start_server()
