from S001 import *
class AgricultureAISystem:
    """农业AI系统主控制器"""
    def __init__(self):
        self.data_collector = IoTDataCollector()
        self.model_a = SensorDataModel()
        self.model_b = LanguageTranslationModel()
        self.evaluator = ResultEvaluator()
        self.is_trained = False
    
    def setup_iot_sensors(self, sensor_configs):
        """配置物联网传感器"""
        for config in sensor_configs:
            self.data_collector.add_sensor(
                config['type'], config['id'], config
            )
    
    def training_pipeline(self):
        """训练流水线"""
        print("开始训练模型...")
        
        # 收集训练数据
        sensor_data = self.collect_training_data()
        
        # 训练model_A
        self.model_a.train(sensor_data)
        self.model_a.save_model('model_a.pkl')
        
        # 训练model_B
        language_data = self.load_language_training_data()
        self.model_b.train(language_data)
        self.model_b.save_model('model_b.pkl')
        
        self.is_trained = True
        print("模型训练完成")
    
    def inference_pipeline(self, real_time_data):
        """推理流水线"""
        if not self.is_trained:
            self.model_a.load_model('model_a.pkl')
            self.model_b.load_model('model_b.pkl')
            self.is_trained = True
        
        # Model A 预测
        model_a_output = self.model_a.predict(real_time_data)
        
        # Model B 翻译
        human_readable_output = self.model_b.predict(model_a_output)
        
        return human_readable_output
    
    def evaluate_results(self, predictions, ground_truth=None):
        """结果评估"""
        return self.evaluator.evaluate(predictions, ground_truth)

class ResultEvaluator:
    """结果评估器"""
    def __init__(self):
        self.llm_apis = {
            'gpt4': GPT4Evaluator(),
            'deepseek': DeepSeekEvaluator(),
            'qwen': QWenEvaluator(),
            'gemini': GeminiEvaluator()
        }
    
    def evaluate(self, predictions, ground_truth=None):
        """多模型评估"""
        evaluations = {}
        
        for name, evaluator in self.llm_apis.items():
            score = evaluator.evaluate_agriculture_output(
                predictions, ground_truth
            )
            evaluations[name] = score
        
        return self.aggregate_evaluations(evaluations)