import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """系统配置"""
    
    # DeepSeek配置
    DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
    DEEPSEEK_MODEL = os.getenv('DEEPSEEK_MODEL', 'deepseek-chat')
    
    # LLM配置
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
    
    # 服务器配置
    BACKEND_PORT = int(os.getenv('BACKEND_PORT', 8000))
    FRONTEND_PORT = int(os.getenv('FRONTEND_PORT', 3000))
    
    # 农业配置
    DEFAULT_CROP = os.getenv('DEFAULT_CROP', 'citrus')
    DEFAULT_LOCATION = os.getenv('DEFAULT_LOCATION', 'field_3')
    
    # 传感器配置
    SENSOR_UPDATE_INTERVAL = int(os.getenv('SENSOR_UPDATE_INTERVAL', 30))
    
    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate_config(cls):
        """验证配置"""
        if not cls.DEEPSEEK_API_KEY or cls.DEEPSEEK_API_KEY == 'your_deepseek_api_key_here':
            print("⚠️  警告: DEEPSEEK_API_KEY 未设置，将使用模拟模式")
            return False
        else:
            print("✅ DeepSeek API配置就绪")
            return True
    
    @classmethod
    def get_backend_url(cls):
        return f"http://localhost:{cls.BACKEND_PORT}"
    
    @classmethod
    def get_frontend_url(cls):
        return f"http://localhost:{cls.FRONTEND_PORT}"

# 验证配置
config_valid = Config.validate_config()