import os
from typing import Dict, Any
from S000 import printLog

class LLMService:
    """统一的LLM服务类"""
    
    def __init__(self):
        # 导入DeepSeek服务
        from deepseek_service import deepseek_service
        self.providers = {
            'deepseek': deepseek_service,  # 主要使用DeepSeek
        }
        self.active_provider = 'deepseek'
        
    def set_provider(self, provider: str, api_key: str = None):
        """设置LLM提供商"""
        if provider in self.providers:
            self.active_provider = provider
            if api_key:
                # 设置API密钥
                self.providers[provider].set_api_key(api_key)
            printLog(f"LLM提供商设置为: {provider}")
        else:
            printLog(f"不支持的LLM提供商: {provider}", "WARNING")
    
    def generate_agriculture_advice(self, user_message: str, sensor_data: Dict, context: Dict = None) -> str:
        """生成农业建议 - 核心方法"""
        try:
            return self.providers[self.active_provider].generate_agriculture_response(
                user_message=user_message,
                sensor_data=sensor_data,
                context=context
            )
        except Exception as e:
            printLog(f"LLM生成建议失败: {e}", "ERROR")
            return "🌱 系统暂时无法提供建议，请稍后重试或联系技术支持。"
    
    def get_provider_status(self) -> Dict:
        """获取当前提供商状态"""
        if self.active_provider in self.providers:
            return self.providers[self.active_provider].get_api_status()
        return {"error": "Provider not found"}

# 全局LLM服务实例
llm_service = LLMService()