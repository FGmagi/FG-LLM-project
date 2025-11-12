#!/usr/bin/env python3
"""
Kissan-Dost 系统启动脚本 - DeepSeek AI版本
"""
import subprocess
import sys
import os
import time
import webbrowser

def start_backend():
    print("🔧 启动后端服务...")
    try:
        if not os.path.exists('main.py'):
            print("❌ main.py 不存在")
            return None
            
        process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("✅ 后端服务启动命令已执行")
        return process
    except Exception as e:
        print(f"❌ 后端启动失败: {e}")
        return None

def start_frontend():
    print("🌐 启动前端服务...")
    time.sleep(3)
    
    try:
        process = subprocess.Popen(
            [sys.executable, 'simple_server.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print("✅ 前端服务启动命令已执行")
        return process
    except Exception as e:
        print(f"❌ 前端启动失败: {e}")
        return None

def start_simulator():
    print("📡 启动传感器模拟器...")
    time.sleep(5)
    
    try:
        if os.path.exists('simulate.py'):
            process = subprocess.Popen(
                [sys.executable, 'simulate.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("✅ 模拟器启动命令已执行")
            return process
        else:
            print("⚠️  simulate.py 不存在，跳过模拟器")
            return None
    except Exception as e:
        print(f"❌ 模拟器启动失败: {e}")
        return None

def main():
    print("🚀 Kissan-Dost 系统启动中...")
    print("=" * 60)
    
    # 检查DeepSeek配置
    try:
        from config import Config
        if Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here':
            print("🎮 AI智能模式 (DeepSeek驱动)")
            ai_mode = "智能AI"
        else:
            print("🎮 模拟数据模式 (智能降级)")
            ai_mode = "模拟降级"
    except:
        print("🎮 模拟数据模式 (配置加载失败)")
        ai_mode = "模拟降级"
    
    required_files = ['main.py', 'simple_server.py', 'index.html', 'S000.py', 'S001.py', 'S002.py']
    missing_files = [f for f in required_files if not os.path.exists(f)]
    
    if missing_files:
        print("❌ 缺少必要文件:")
        for f in missing_files:
            print(f"  - {f}")
        return
    
    print("✅ 所有必要文件存在")
    
    processes = []
    
    try:
        backend_proc = start_backend()
        if backend_proc:
            processes.append(backend_proc)
        
        frontend_proc = start_frontend()
        if frontend_proc:
            processes.append(frontend_proc)
        
        simulator_proc = start_simulator()
        if simulator_proc:
            processes.append(simulator_proc)
        
        print("\n" + "=" * 60)
        print("✅ 所有服务启动命令已执行!")
        print("=" * 60)
        print("🌐 重要访问地址:")
        print("  前端界面: http://localhost:3000")
        print("  后端API:  http://localhost:8000")
        print("=" * 60)
        print("🤖 AI模式:", ai_mode)
        print("💡 使用说明:")
        print("   数据模式: 模拟数据")
        print("   AI引擎: DeepSeek")
        print("=" * 60)
        print("🛑 按 Ctrl+C 停止所有服务")
        print("=" * 60)
        
        # 打开浏览器
        time.sleep(3)
        webbrowser.open("http://localhost:3000")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 正在停止服务...")
        for proc in processes:
            try:
                proc.terminate()
            except:
                pass
        print("✅ 服务已停止")

if __name__ == "__main__":
    main()