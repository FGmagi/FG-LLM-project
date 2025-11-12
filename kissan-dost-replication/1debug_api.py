#!/usr/bin/env python3
"""
DeepSeek API调试脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import Config
from deepseek_service import deepseek_service

def debug_api_config():
    print("=" * 60)
    print("🐛 DeepSeek API 配置调试")
    print("=" * 60)
    
    # 1. 检查环境变量
    print("1. 🔍 环境变量检查:")
    env_key = os.getenv('DEEPSEEK_API_KEY')
    print(f"   os.getenv('DEEPSEEK_API_KEY'): {env_key[:8]}...{env_key[-4:] if env_key else 'None'}")
    print(f"   Config.DEEPSEEK_API_KEY: {Config.DEEPSEEK_API_KEY[:8]}...{Config.DEEPSEEK_API_KEY[-4:] if Config.DEEPSEEK_API_KEY else 'None'}")
    
    # 2. 检查服务实例
    print("2. 🔍 服务实例检查:")
    print(f"   deepseek_service.api_key: {deepseek_service.api_key[:8]}...{deepseek_service.api_key[-4:] if deepseek_service.api_key else 'None'}")
    
    # 3. 设置API密钥
    print("3. 🔧 设置API密钥...")
    deepseek_service.set_api_key(Config.DEEPSEEK_API_KEY)
    print(f"   设置后 deepseek_service.api_key: {deepseek_service.api_key[:8]}...{deepseek_service.api_key[-4:] if deepseek_service.api_key else 'None'}")
    
    # 4. 测试网络连接
    print("4. 🌐 网络连接测试...")
    try:
        import socket
        socket.create_connection(("api.deepseek.com", 443), timeout=5)
        print("   ✅ 网络连接正常")
    except Exception as e:
        print(f"   ❌ 网络连接失败: {e}")
    
    # 5. 直接测试API调用
    print("5. 🧪 直接API调用测试...")
    if deepseek_service.api_key and deepseek_service.api_key != 'your_deepseek_api_key_here':
        try:
            import requests
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {deepseek_service.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": "请回复'API测试成功'"}],
                "max_tokens": 10
            }
            
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            print(f"   📡 响应状态码: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                print(f"   ✅ API调用成功: {answer}")
            else:
                print(f"   ❌ API调用失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                
        except Exception as e:
            print(f"   ❌ API调用异常: {e}")
    else:
        print("   ⚠️  API密钥无效，跳过测试")
    
    print("=" * 60)

if __name__ == "__main__":
    debug_api_config()