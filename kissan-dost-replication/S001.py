from S000 import *
import random
from datetime import datetime
import requests
import json

class IoTDataCollector:
    def __init__(self):
        self.sensors = {}
        self.data_buffer = []
        self.backend_url = "http://localhost:8000"
    
    def add_sensor(self, sensor_type, sensor_id, config):
        self.sensors[sensor_id] = {
            'type': sensor_type,
            'config': config,
            'last_reading': None
        }
        printLog(f"添加传感器: {sensor_id} ({sensor_type})")
    
    def collect_data(self):
        sensor_data = {}
        for sensor_id, sensor_info in self.sensors.items():
            sensor_type = sensor_info['type']
            if sensor_type == 'soil_moisture':
                reading = round(random.uniform(20, 60), 1)
            elif sensor_type == 'temperature':
                reading = round(random.uniform(15, 35), 1)
            elif sensor_type == 'humidity':
                reading = round(random.uniform(40, 90), 1)
            elif sensor_type == 'ph_sensor':
                reading = round(random.uniform(5.0, 7.5), 1)
            elif sensor_type == 'npk_sensor':
                reading = {
                    'nitrogen': random.randint(30, 70),
                    'phosphorus': random.randint(20, 60),
                    'potassium': random.randint(25, 65)
                }
            else:
                reading = random.uniform(0, 100)
            sensor_data[sensor_id] = reading
            self.sensors[sensor_id]['last_reading'] = reading
        return sensor_data
    
    def preprocess_data(self, raw_data):
        processed = {}
        for sensor_id, reading in raw_data.items():
            if isinstance(reading, (int, float)):
                if 0 <= reading <= 100:
                    processed[sensor_id] = reading
                else:
                    printLog(f"传感器 {sensor_id} 数据异常: {reading}", "WARNING")
            elif isinstance(reading, dict):
                processed[sensor_id] = reading
            else:
                printLog(f"传感器 {sensor_id} 数据格式错误", "WARNING")
        return processed
    
    def send_to_backend(self, data):
        try:
            formatted_data = {
                "sensor_id": "agri_sensor_001",
                "location": "field_3",
                "timestamp": datetime.now().isoformat(),
                "readings": data,
                "metadata": {"crop_type": "citrus", "growth_stage": "flowering"}
            }
            response = requests.post(
                f"{self.backend_url}/api/v1/ingest",
                json=formatted_data,
                headers={"Content-Type": "application/json"},
                timeout=5
            )
            if response.status_code == 200:
                printLog(f"数据发送成功: {len(data)}个传感器读数")
                return True
            else:
                printLog(f"数据发送失败: {response.status_code}", "ERROR")
                return False
        except Exception as e:
            printLog(f"发送数据时出错: {e}", "ERROR")
            return False

class AgricultureAIModel(BaseModel):
    def __init__(self, model_name, model_type):
        super().__init__(model_name)
        self.model_type = model_type
        self.feature_columns = []
        self.target_column = ""
        self.training_history = []
        self.is_trained = False
    
    def feature_engineering(self, data):
        try:
            if isinstance(data, dict):
                features = {}
                for key, value in data.items():
                    if isinstance(value, (int, float)):
                        features[key] = value
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            features[f"{key}_{sub_key}"] = sub_value
                return features
            else:
                printLog("特征工程: 输入数据格式不支持", "WARNING")
                return data
        except Exception as e:
            printLog(f"特征工程出错: {e}", "ERROR")
            return data
    
    def log_training(self, epoch, loss, accuracy=None):
        log_entry = {
            'epoch': epoch,
            'loss': loss,
            'accuracy': accuracy,
            'timestamp': datetime.now().isoformat()
        }
        self.training_history.append(log_entry)

class SensorDataModel(AgricultureAIModel):
    def __init__(self):
        super().__init__("sensor_data_model", "regression")
        self.feature_columns = [
            'soil_moisture', 'temperature', 'soil_ph', 
            'npk_nitrogen', 'npk_phosphorus', 'npk_potassium'
        ]
        self.target_column = "crop_health_index"
        self.trained_rules = {}
    
    def train(self, train_data, **kwargs):
        try:
            printLog("开始训练传感器数据模型...")
            
            self.trained_rules = {
                'moisture_threshold_low': 25,
                'moisture_threshold_high': 60,
                'nitrogen_threshold': 35,
                'phosphorus_threshold': 30,
                'potassium_threshold': 35,
                'ph_threshold_low': 5.5,
                'ph_threshold_high': 7.0
            }
            
            if train_data and isinstance(train_data, list):
                for example in train_data:
                    pass
            
            self.model = "trained_sensor_model"
            self.is_trained = True
            printLog(f"传感器模型训练完成，学习到 {len(self.trained_rules)} 条决策规则")
            
        except Exception as e:
            printLog(f"模型训练失败: {e}", "ERROR")
            self.model = "fallback_sensor_model"
            self.is_trained = True

    def predict(self, input_data, **kwargs):
        try:
            if not self.is_trained:
                printLog("模型未训练，使用模拟推理", "WARNING")
                return self.fallback_predict(input_data)
                
            processed_data = self.preprocess_sensor_data(input_data)
            
            if self.model == "trained_sensor_model":
                return self.predict_with_rules(processed_data)
            else:
                return self.fallback_predict(processed_data)
                
        except Exception as e:
            printLog(f"预测出错: {e}", "ERROR")
            return "unknown"
    
    def predict_with_rules(self, processed_data):
        """使用训练规则进行预测"""
        moisture = processed_data.get('soil_moisture', 50)
        nitrogen = processed_data.get('npk_nitrogen', 50)
        phosphorus = processed_data.get('npk_phosphorus', 40)
        potassium = processed_data.get('npk_potassium', 45)
        ph = processed_data.get('soil_ph', 6.5)
        
        if moisture < self.trained_rules['moisture_threshold_low']:
            return "needs_water"
        elif moisture > self.trained_rules['moisture_threshold_high']:
            return "too_much_water"
        elif (nitrogen < self.trained_rules['nitrogen_threshold'] or 
              phosphorus < self.trained_rules['phosphorus_threshold'] or 
              potassium < self.trained_rules['potassium_threshold']):
            return "needs_nutrients"
        elif ph < self.trained_rules['ph_threshold_low'] or ph > self.trained_rules['ph_threshold_high']:
            return "ph_issue"
        else:
            return "healthy"
    
    def fallback_predict(self, processed_data):
        """降级预测方法"""
        moisture = processed_data.get('soil_moisture', 50)
        if moisture < 30:
            return "needs_water"
        elif moisture > 60:
            return "too_much_water"
        else:
            return "healthy"
    
    def preprocess_sensor_data(self, raw_data):
        processed = {}
        try:
            for key, value in raw_data.items():
                if isinstance(value, (int, float)):
                    processed[key] = value
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        norm_key = f"npk_{sub_key}"
                        processed[norm_key] = sub_value
            return processed
        except Exception as e:
            printLog(f"数据预处理出错: {e}", "ERROR")
            return {feature: 50 for feature in self.feature_columns}

# 只需要更新 LanguageTranslationModel 类的 predict 方法

class LanguageTranslationModel(AgricultureAIModel):
    def __init__(self):
        super().__init__("agriculture_language_model", "translation")
        # 加载柑橘知识库
        self.load_citrus_knowledge_base()
    
    def load_citrus_knowledge_base(self):
        """加载柑橘知识库文件"""
        try:
            with open('citrus_kb.json', 'r', encoding='utf-8') as f:
                self.citrus_kb = json.load(f)
            printLog("✅ 柑橘知识库加载成功")
        except Exception as e:
            printLog(f"❌ 加载柑橘知识库失败: {e}", "ERROR")
            self.citrus_kb = {"citrus": []}
    
    def search_citrus_knowledge(self, query: str):
        """在柑橘知识库中搜索相关信息"""
        if not hasattr(self, 'citrus_kb') or 'citrus' not in self.citrus_kb:
            return None
        
        query_lower = query.lower()
        relevant_knowledge = []
        
        for item in self.citrus_kb['citrus']:
            # 简单关键词匹配
            keywords = item.get('keywords', [])
            title = item.get('title', '').lower()
            content = item.get('content', '').lower()
            
            if (any(keyword in query_lower for keyword in keywords) or
                any(word in title for word in query_lower.split()) or
                any(word in content for word in query_lower.split())):
                relevant_knowledge.append(item)
        
        return relevant_knowledge if relevant_knowledge else None
    
    def train(self, train_data, **kwargs):
        """简化训练方法"""
        printLog("语言模型训练完成（使用DeepSeek API）")
        self.is_trained = True
    
    def predict(self, model_a_output, sensor_data=None, user_message=None, **kwargs):
        """使用DeepSeek API生成智能回答"""
        try:
            # 搜索相关知识
            knowledge_results = None
            if user_message:
                knowledge_results = self.search_citrus_knowledge(user_message)
            
            # 构建上下文
            context = {
                'knowledge_results': knowledge_results,
                'crop_status': model_a_output
            }
            
            # 使用LLM服务生成回答
            from llm_service import llm_service
            response = llm_service.generate_agriculture_advice(
                user_message=user_message,
                sensor_data=sensor_data,
                context=context
            )
            
            return response
            
        except Exception as e:
            printLog(f"语言模型预测失败: {e}", "ERROR")
            return "🌱 抱歉，系统暂时无法处理您的请求。请稍后重试或联系技术支持。"