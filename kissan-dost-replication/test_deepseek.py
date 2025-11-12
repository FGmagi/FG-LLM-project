#!/usr/bin/env python3
"""
测试DeepSeek API连接 - 诊断版本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from deepseek_service import DeepSeekService
from config import Config

def test_deepseek_connection():
    """测试DeepSeek API连接"""
    print("🧪 测试DeepSeek API连接...")
    
    # 检查配置
    print(f"🔑 API密钥状态: {'✅ 已设置' if Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here' else '❌ 未设置'}")
    if Config.DEEPSEEK_API_KEY:
        print(f"   API密钥: {Config.DEEPSEEK_API_KEY[:10]}...{Config.DEEPSEEK_API_KEY[-5:]}")
    print(f"🌐 模型: {Config.DEEPSEEK_MODEL}")
    
    deepseek = DeepSeekService()
    deepseek.set_api_key(Config.DEEPSEEK_API_KEY)
    
    # 测试一个简单的问题
    print("\n🔍 测试简单API调用...")
    test_question = "你好，请简单回复'API测试成功'四个字"
    sensor_data = {
        'soil_moisture': 45,
        'temperature': 25,
        'soil_ph': 6.5
    }
    
    response = deepseek.generate_agriculture_response(test_question, sensor_data)
    
    print(f"❓ 测试问题: {test_question}")
    print(f"🤖 回答: {response}")
    
    # 判断是否使用了模拟模式
    if "API测试成功" in response:
        print("\n✅ API调用正常 - 检测到正确响应")
        return True
    elif "浇水建议分析" in response:
        print("\n❌ 检测到系统在使用模拟模式，API调用失败")
        return False
    else:
        print("\n⚠️  不确定API调用状态")
        return None

def debug_api_call():
    """调试API调用"""
    print("\n🔧 开始调试API调用...")
    
    deepseek = DeepSeekService()
    deepseek.set_api_key(Config.DEEPSEEK_API_KEY)
    
    # 直接测试API调用
    if deepseek.api_key and deepseek.api_key != 'your_deepseek_api_key_here':
        print("✅ API密钥存在且有效")
        
        # 测试直接API调用
        try:
            import requests
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {deepseek.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {
                        "role": "user", 
                        "content": "请简单回复'API测试成功'"
                    }
                ],
                "max_tokens": 50
            }
            
            print("🔄 发送API请求...")
            response = requests.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            print(f"📡 响应状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                print(f"✅ API调用成功: {answer}")
                return True
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"   错误信息: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ API调用异常: {e}")
            return False
    else:
        print("❌ API密钥为空或无效")
        return False

def test_comprehensive_questions():
    """测试综合问题"""
    print("\n" + "=" * 60)
    print("🧪 测试综合农业问题")
    print("=" * 60)
    
    deepseek = DeepSeekService()
    deepseek.set_api_key(Config.DEEPSEEK_API_KEY)
    
    test_questions = [
        "柑橘叶子发黄怎么办？",
        "土壤湿度25%需要浇水吗？",
        "如何防治柑橘红蜘蛛？",
        "NPK肥料怎么配比？",
        "最近温度很高，对柑橘有什么影响？"
    ]
    
    sensor_data = {
        'soil_moisture': 25,
        'temperature': 32,
        'soil_ph': 6.2,
        'npk_nitrogen': 28,
        'npk_phosphorus': 32,
        'npk_potassium': 35
    }
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n{'='*60}")
        print(f"❓ 问题 {i}: {question}")
        print(f"{'='*60}")
        response = deepseek.generate_agriculture_response(question, sensor_data)
        print(f"🤖 回答:\n{response}")
        
        # 检查是否为模拟模式
        if "浇水建议分析" in response and i > 1:
            print("⚠️  检测到模拟模式响应")
        
        print(f"{'='*60}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 DeepSeek API连接诊断")
    print("=" * 60)
    
    # 测试配置
    api_configured = test_deepseek_connection()
    
    if api_configured is False:
        print("\n" + "=" * 60)
        print("🔄 尝试直接API调用调试...")
        debug_api_call()
    
    # 测试综合问题
    test_comprehensive_questions()
    
    print("\n" + "=" * 60)
    print("💡 解决方案:")
    if api_configured:
        print("✅ 系统运行正常，可以开始使用!")
    else:
        print("1. 检查 .env 文件中的 DEEPSEEK_API_KEY 配置")
        print("2. 确认API密钥有效且未过期") 
        print("3. 检查网络连接")
        print("4. 验证DeepSeek服务状态")
        print("5. 系统将使用智能模拟模式继续运行")
    print("=" * 60)