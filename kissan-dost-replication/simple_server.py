#!/usr/bin/env python3
"""
修复版前端服务器
"""
import http.server
import socketserver
import os
import webbrowser
import time

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        print(f"🌐 前端访问 - {self.client_address[0]} - {format % args}")

def find_available_port(start_port=3000, max_attempts=10):
    import socket
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', port))
                return port
        except OSError:
            continue
    return None

def start_server():
    print("=" * 50)
    print("🚀 启动修复版前端服务器")
    print("=" * 50)
    
    # 检查必要文件
    if not os.path.exists('index.html'):
        print("❌ index.html 文件不存在")
        return
    
    # 切换到当前目录
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 查找可用端口
    port = find_available_port(3000)
    if port is None:
        print("❌ 找不到可用端口")
        return
    
    try:
        with socketserver.TCPServer(("", port), CORSHTTPRequestHandler) as httpd:
            print(f"✅ 服务器启动成功!")
            print(f"📡 服务地址: http://localhost:{port}")
            print(f"📂 服务目录: {os.getcwd()}")
            print("=" * 50)
            print("💡 重要提示:")
            print("   请确保后端服务也在运行: http://localhost:8000")
            print("=" * 50)
            print("🛑 按 Ctrl+C 停止服务器")
            print("=" * 50)
            
            # 打开浏览器
            webbrowser.open(f"http://localhost:{port}")
            
            httpd.serve_forever()
            
    except OSError as e:
        print(f"❌ 服务器启动失败: {e}")
        print("💡 尝试使用其他端口...")
        # 尝试其他端口
        port = find_available_port(8080)
        if port:
            print(f"🔄 尝试在端口 {port} 启动...")
            with socketserver.TCPServer(("", port), CORSHTTPRequestHandler) as httpd:
                print(f"✅ 服务器在端口 {port} 启动成功!")
                print(f"📡 访问地址: http://localhost:{port}")
                webbrowser.open(f"http://localhost:{port}")
                httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")

if __name__ == "__main__":
    start_server()