from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import sys
from datetime import datetime

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入配置和LLM服务
from config import Config
from llm_service import llm_service

# 初始化LLM服务
llm_service.set_provider(Config.LLM_PROVIDER, Config.DEEPSEEK_API_KEY)

try:
    from S002 import AgricultureAISystem
    agri_ai_system = AgricultureAISystem()
    AI_SYSTEM_LOADED = True
except Exception as e:
    print(f"❌ AI系统加载失败: {e}")
    AI_SYSTEM_LOADED = False

app = FastAPI(
    title="Kissan-Dost API",
    description="农业智能助手后端API - DeepSeek AI驱动",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_sensor_data = {}
chat_history = []

@app.on_event("startup")
async def startup_event():
    print("🚀 初始化农业AI系统...")
    
    # 初始化LLM服务 - 确保传递API密钥
    llm_service.set_provider(Config.LLM_PROVIDER, Config.DEEPSEEK_API_KEY)
    
    # 显式设置DeepSeek服务的API密钥
    from deepseek_service import deepseek_service
    deepseek_service.set_api_key(Config.DEEPSEEK_API_KEY)
    
    # 打印LLM服务状态
    if Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here':
        print("✅ DeepSeek API已配置 - 使用智能AI模式")
        ai_mode = "智能AI模式"
    else:
        print("⚠️  DeepSeek API未配置 - 使用智能模拟模式")
        ai_mode = "智能模拟模式"
    
    if AI_SYSTEM_LOADED:
        try:
            agri_ai_system.setup_iot_sensors(None)
            print("✅ 农业AI系统初始化完成")
                
            # 检查AI模型训练状态
            system_status = agri_ai_system.get_system_status()
            print(f"🤖 AI模型状态: 传感器模型-{'已训练' if system_status.get('model_a_trained') else '未训练'}, "
                  f"语言模型-{'已训练' if system_status.get('model_b_trained') else '未训练'}")
                  
        except Exception as e:
            print(f"❌ AI系统初始化失败: {e}")
    else:
        print("⚠️ AI系统未加载，使用降级模式")
        ai_mode = "降级模式"
    
    print(f"🎯 最终运行模式: {ai_mode}")

@app.get("/")
async def root():
    return {
        "message": "Kissan-Dost API 服务运行中 (DeepSeek AI驱动)",
        "status": "healthy",
        "data_mode": "simulated",
        "ai_provider": "deepseek",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    if AI_SYSTEM_LOADED:
        try:
            system_status = agri_ai_system.get_system_status()
        except:
            system_status = {"status": "ai_system_error"}
    else:
        system_status = {"status": "ai_system_not_loaded"}
    
    # 检查API密钥状态
    api_status = "configured" if (Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here') else "not_configured"
    
    return {
        "status": "healthy", 
        "service": "kissan-dost-backend",
        "ai_system_status": system_status,
        "api_status": api_status,
        "data_mode": "simulated",
        "ai_provider": "deepseek",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/system-status")
async def get_system_status():
    if AI_SYSTEM_LOADED:
        try:
            status = agri_ai_system.get_system_status()
            status['data_mode'] = "simulated"
            status['ai_provider'] = "deepseek"
            status['api_configured'] = bool(Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here')
            return status
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        return {
            "status": "ai_system_not_loaded",
            "ai_provider": "deepseek",
            "api_configured": bool(Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here')
        }

@app.post("/api/v1/ingest")
async def ingest_sensor_data(data: dict):
    global latest_sensor_data
    try:
        latest_sensor_data = data
        sensor_id = data.get('sensor_id', 'unknown')
        timestamp = data.get('timestamp', 'unknown')
        
        print(f"📊 收到传感器数据: {sensor_id} - {timestamp}")
        
        return {
            "status": "success", 
            "message": "数据接收成功",
            "data_received": {
                "sensor_id": sensor_id,
                "location": data.get("location"),
                "timestamp": timestamp
            }
        }
    except Exception as e:
        return {"status": "error", "message": f"数据处理失败: {str(e)}"}

@app.post("/api/v1/chat")
async def chat_endpoint(request: dict):
    global chat_history, latest_sensor_data
    try:
        user_id = request.get("user_id", "unknown")
        user_message = request.get("message", "")
        location = request.get("location", "field_3")
        language = request.get("language", "zh-CN")
        
        print(f"💬 收到用户消息: {user_message}")
        
        sensor_data_for_ai = {}
        if latest_sensor_data and 'readings' in latest_sensor_data:
            sensor_data_for_ai = latest_sensor_data['readings']
            # 处理NPK数据格式
            if 'npk' in sensor_data_for_ai and isinstance(sensor_data_for_ai['npk'], dict):
                npk_data = sensor_data_for_ai.pop('npk')
                sensor_data_for_ai.update({
                    'npk_nitrogen': npk_data.get('nitrogen', 0),
                    'npk_phosphorus': npk_data.get('phosphorus', 0),
                    'npk_potassium': npk_data.get('potassium', 0)
                })
        
        if AI_SYSTEM_LOADED:
            # 使用系统收集的模拟数据
            current_sensor_data = agri_ai_system.collect_sensor_data()
            if current_sensor_data:
                sensor_data_for_ai = current_sensor_data
            
            # 模型A分析传感器数据
            model_a_output = agri_ai_system.model_a.predict(sensor_data_for_ai)
            
            # 模型B生成自然语言回答
            ai_advice = agri_ai_system.model_b.predict(
                model_a_output, 
                sensor_data_for_ai, 
                user_message=user_message
            )
        else:
            # 降级模式 - 直接使用LLM服务
            ai_advice = llm_service.generate_agriculture_advice(user_message, sensor_data_for_ai)
        
        response_data = {
            "response": ai_advice,
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "ai_provider": "deepseek",
            "using_real_api": bool(Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here')
        }
        
        chat_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "user_message": user_message,
            "ai_response": ai_advice,
            "location": location,
            "ai_provider": "deepseek"
        }
        chat_history.append(chat_entry)
        
        # 限制聊天历史长度
        if len(chat_history) > 100:
            chat_history = chat_history[-100:]
        
        return response_data
        
    except Exception as e:
        print(f"❌ 聊天处理错误: {e}")
        return {
            "response": "抱歉，系统暂时无法处理您的请求。请稍后重试。",
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/v1/chat-history")
async def get_chat_history(limit: int = 10):
    return {
        "status": "success",
        "history": chat_history[-limit:] if chat_history else [],
        "total_messages": len(chat_history),
        "ai_provider": "deepseek"
    }

@app.get("/api/v1/sensor-data")
async def get_sensor_data():
    return {
        "status": "success",
        "sensor_data": latest_sensor_data,
        "data_mode": "simulated",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/v1/analyze")
async def analyze_farm():
    if not AI_SYSTEM_LOADED:
        return {"status": "error", "message": "AI系统未加载"}
    
    try:
        advice = agri_ai_system.inference_pipeline()
        return {
            "status": "success",
            "analysis": advice,
            "system_status": agri_ai_system.get_system_status(),
            "timestamp": datetime.now().isoformat(),
            "ai_provider": "deepseek"
        }
    except Exception as e:
        return {"status": "error", "message": f"分析失败: {str(e)}"}

@app.get("/api/v1/debug-info")
async def get_debug_info():
    """获取调试信息"""
    debug_info = {
        "system": {
            "ai_system_loaded": AI_SYSTEM_LOADED,
            "ai_provider": "deepseek",
            "api_configured": bool(Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here'),
            "backend_port": Config.BACKEND_PORT,
            "frontend_port": Config.FRONTEND_PORT
        },
        "sensors": {
            "latest_data_received": bool(latest_sensor_data),
            "data_count": len(chat_history)
        },
        "llm_service": {
            "active_provider": llm_service.active_provider,
            "available_providers": list(llm_service.providers.keys())
        },
        "timestamp": datetime.now().isoformat()
    }
    
    if AI_SYSTEM_LOADED:
        try:
            system_status = agri_ai_system.get_system_status()
            debug_info["ai_system"] = system_status
        except Exception as e:
            debug_info["ai_system"] = {"error": str(e)}
    
    return debug_info

@app.get("/api/v1/ai-status")
async def get_ai_status():
    """获取AI服务状态"""
    from deepseek_service import deepseek_service
    
    api_configured = bool(Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here')
    
    # 获取详细的API状态
    api_status = deepseek_service.get_api_status()
    
    status_info = {
        "provider": "deepseek",
        "api_configured": api_configured,
        "mode": "real_api" if api_configured else "simulation",
        "model": Config.DEEPSEEK_MODEL,
        "status": "ready" if api_status["health"]["service_available"] else "unavailable",
        "detailed_status": api_status
    }
    
    return status_info

@app.get("/api/v1/deepseek-status")
async def get_deepseek_status():
    """获取DeepSeek API详细状态"""
    from deepseek_service import deepseek_service
    
    health = deepseek_service.health_check()
    api_status = deepseek_service.get_api_status()
    
    return {
        "status": "healthy" if health["service_available"] else "unhealthy",
        "health_check": health,
        "api_statistics": api_status,
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    print("🚀 启动Kissan-Dost后端服务...")
    print("=" * 50)
    print(f"📂 工作目录: {os.getcwd()}")
    print(f"🤖 AI提供商: DeepSeek")
    print(f"🔑 API状态: {'✅ 已配置' if Config.DEEPSEEK_API_KEY and Config.DEEPSEEK_API_KEY != 'your_deepseek_api_key_here' else '⚠️ 未配置（使用模拟模式）'}")
    print(f"🌐 服务端口: {Config.BACKEND_PORT}")
    print(f"📡 数据模式: 模拟数据")
    print("=" * 50)
    
    uvicorn.run(app, host="0.0.0.0", port=Config.BACKEND_PORT, reload=False)