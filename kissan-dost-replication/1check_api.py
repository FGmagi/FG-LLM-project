#!/usr/bin/env python3
"""
DeepSeek API连接状态检测脚本 - 最终修复版
"""
import sys
import os
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 首先加载配置
from config import Config
from deepseek_service import deepseek_service

def comprehensive_api_check():
    print("=" * 60)
    print("🔍 DeepSeek API 综合检测")
    print("=" * 60)
    
    # 0. 显式设置API密钥
    print("0. 🔑 设置API密钥...")
    deepseek_service.set_api_key(Config.DEEPSEEK_API_KEY)
    
    # 1. 检查配置
    print("1. 🔑 API配置检查...")
    if Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here':
        print("   ✅ API密钥已配置")
        print(f"   密钥: {Config.DEEPSEEK_API_KEY[:8]}...{Config.DEEPSEEK_API_KEY[-4:]}")
        print(f"   密钥长度: {len(Config.DEEPSEEK_API_KEY)} 字符")
    else:
        print("   ❌ API密钥未配置")
        print("   💡 请在 .env 文件中设置 DEEPSEEK_API_KEY")
        return False
    
    # 2. 健康检查
    print("2. 🩺 API健康检查...")
    start_time = time.time()
    try:
        health = deepseek_service.health_check()
        if health is None:
            print("   ❌ 健康检查返回了None")
            health = {
                "api_configured": True,
                "network_connected": False,
                "authentication_valid": False,
                "service_available": False,
                "balance_sufficient": False,
                "response_time": None,
                "error_message": "健康检查返回None"
            }
    except Exception as e:
        print(f"   ❌ 健康检查异常: {e}")
        health = {
            "api_configured": True,
            "network_connected": False,
            "authentication_valid": False,
            "service_available": False,
            "balance_sufficient": False,
            "response_time": None,
            "error_message": f"健康检查异常: {e}"
        }
    
    check_time = time.time() - start_time
    
    # 安全地访问health字典
    network_connected = health.get('network_connected', False)
    authentication_valid = health.get('authentication_valid', False)
    service_available = health.get('service_available', False)
    balance_sufficient = health.get('balance_sufficient', True)
    response_time = health.get('response_time')
    error_message = health.get('error_message')
    
    print(f"   网络连接: {'✅' if network_connected else '❌'}")
    print(f"   认证有效: {'✅' if authentication_valid else '❌'}")
    print(f"   服务可用: {'✅' if service_available else '❌'}")
    print(f"   余额充足: {'✅' if balance_sufficient else '❌'}")
    
    if response_time:
        print(f"   响应时间: {response_time}秒")
    
    if error_message:
        print(f"   错误信息: {error_message}")
    
    print(f"   检查耗时: {check_time:.2f}秒")
    
    # 3. 测试调用
    if service_available and balance_sufficient:
        print("3. 🧪 测试API调用...")
        start_time = time.time()
        try:
            test_response = deepseek_service.generate_agriculture_response(
                "请回复'API测试成功'", 
                {'soil_moisture': 50}
            )
            call_time = time.time() - start_time
            
            if "API测试成功" in test_response:
                print("   ✅ API调用测试成功")
                print(f"   调用耗时: {call_time:.2f}秒")
                print(f"   响应内容: {test_response}")
                success = True
            else:
                print("   ❌ API调用测试失败")
                print(f"   实际响应: {test_response}")
                success = False
        except Exception as e:
            print(f"   ❌ API调用异常: {e}")
            success = False
    else:
        print("3. 🧪 跳过API调用测试（服务不可用或余额不足）")
        success = False
    
    # 4. 显示统计信息
    print("4. 📊 API调用统计...")
    try:
        stats = deepseek_service.get_api_status()
        print(f"   总调用次数: {stats.get('total_calls', 0)}")
        print(f"   成功次数: {stats.get('successful_calls', 0)}")
        print(f"   成功率: {stats.get('success_rate', 0) * 100:.1f}%")
        print(f"   连续失败: {stats.get('consecutive_failures', 0)}")
        
        if stats.get('last_success'):
            print(f"   最后成功: {stats['last_success']}")
        if stats.get('last_failure'):
            print(f"   最后失败: {stats['last_failure']}")
    except Exception as e:
        print(f"   ❌ 获取统计信息失败: {e}")
    
    print("=" * 60)
    if success:
        print("🎉 所有检测通过！DeepSeek API工作正常")
        print("💡 系统将以智能AI模式运行")
    else:
        print("🔧 检测到问题，系统将使用模拟模式运行")
        if not balance_sufficient:
            print("💡 主要问题: API余额不足")
            print("   解决方案:")
            print("   1. 访问 https://platform.deepseek.com/")
            print("   2. 登录您的账户") 
            print("   3. 查看余额并充值")
        elif not service_available:
            print("💡 主要问题: API服务不可用")
            print("   解决方案:")
            print("   1. 检查网络连接")
            print("   2. 验证API密钥有效性")
            print("   3. 检查DeepSeek服务状态")
    
    print("=" * 60)
    return success

if __name__ == "__main__":
    success = comprehensive_api_check()
    sys.exit(0 if success else 1)