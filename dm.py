"""
dm.py - 农业专业模型（DataModule）
功能：从农业知识库中检索相关信息，生成专业回答
训练数据来源：downloader 下载的历史数据
"""

from typing import List, Dict, Any
import json
from pathlib import Path
import time

# 尝试导入基类，适配现有项目
try:
    from S001 import AgricultureAIModel
except ImportError:
    # 如果没有基类，创建一个简单的
    class AgricultureAIModel:
        def __init__(self, model_name="", model_type=""):
            self.model_name = model_name
            self.model_type = model_type
        
        def train(self, train_data, **kwargs):
            pass
        
        def predict(self, input_data, **kwargs):
            pass
        
        def save_model(self, path=""):
            pass
        
        def load_model(self, path=""):
            pass


class DataModule(AgricultureAIModel):
    """
    农业专业模型 (dm)
    
    功能：
    1. 从 downloader 获取历史数据并训练
    2. 根据用户问题检索知识库
    3. 生成专业的农业回答
    """
    
    def __init__(self):
        """初始化模型"""
        super().__init__("dm_agriculture_model", "knowledge_retrieval")
        
        # 知识库
        self.knowledge_base = []
        self.keywords_weights = {}
        self.is_trained = False
        
        # 模型保存路径
        self.model_path = "models/dm_model.pkl"
        
        # 特征列和目标列
        self.feature_columns = ['question_keywords', 'question_length', 'category']
        self.target_column = "answer"
    
    def _print_log(self, message: str):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[DM] {timestamp} - {message}")
    
    def train_from_downloader(self, downloader, user_id: str, device_key: str, 
                              begin_time: str, end_time: str):
        """
        从 downloader 下载历史数据并训练
        
        Args:
            downloader: 数据下载器实例
            user_id: 用户ID
            device_key: 设备编号
            begin_time: 开始时间 (YYYY-MM-DD HH:mm:ss)
            end_time: 结束时间 (YYYY-MM-DD HH:mm:ss)
        """
        self._print_log("开始从 downloader 获取数据...")
        
        try:
            # 1. 登录
            self._print_log("登录 downloader...")
            # downloader.logIn("username", "password")  # 需要实际账号密码
            
            # 2. 获取历史数据
            self._print_log(f"获取 {device_key} 的历史数据...")
            # history_data = downloader.get_history_data(
            #     device_key=device_key,
            #     begin_time=begin_time,
            #     end_time=end_time
            # )
            
            # 3. 将传感器数据转换为训练数据
            # 这里需要根据实际数据格式进行转换
            training_data = self._convert_sensor_data_to_training([])
            
            # 4. 训练模型
            self.train(training_data)
            
            self._print_log("从 downloader 训练完成")
            
        except Exception as e:
            self._print_log(f"从 downloader 训练失败: {e}")
            # 如果失败，使用示例数据
            self._init_example_data()
    
    def _convert_sensor_data_to_training(self, sensor_data: List[Dict]) -> List[Dict]:
        """
        将传感器数据转换为训练数据
        
        Args:
            sensor_data: 传感器历史数据
        
        Returns:
            训练数据列表
        """
        # 这里需要根据实际的传感器数据格式进行转换
        # 示例转换逻辑：
        training_data = []
        
        # 如果有真实数据，这里进行处理
        # for data in sensor_data:
        #     # 提取关键信息
        #     question = f"{data['crop']}的{data['parameter']}如何处理？"
        #     answer = self._generate_answer_from_sensor(data)
        #     keywords = self._extract_keywords(question)
        #     category = data.get('category', '管理')
        #     
        #     training_data.append({
        #         'question': question,
        #         'answer': answer,
        #         'keywords': keywords,
        #         'category': category
        #     })
        
        return training_data
    
    def _init_example_data(self):
        """初始化示例数据"""
        self._print_log("使用示例数据初始化...")
        example_data = self._get_example_training_data()
        self.train(example_data)
    
    def train(self, training_data: List[Dict[str, Any]], **kwargs):
        """
        训练农业模型
        
        Args:
            training_data: 训练数据列表
                - question: 问题描述
                - answer: 专业回答
                - keywords: 关键词列表
                - category: 农业类别
            **kwargs: 额外参数（适配基类接口）
        """
        self._print_log(f"开始训练，训练数据量: {len(training_data)}")
        
        # 构建知识库
        self.knowledge_base = []
        
        for item in training_data:
            if not all(key in item for key in ['question', 'answer']):
                continue
                
            # 提取关键词
            keywords = item.get('keywords', [])
            if isinstance(keywords, str):
                keywords = [keywords]
            
            # 计算关键词权重
            for kw in keywords:
                if kw not in self.keywords_weights:
                    self.keywords_weights[kw] = 0
                self.keywords_weights[kw] += 1
            
            knowledge_item = {
                'question': item['question'],
                'answer': item['answer'],
                'keywords': keywords,
                'category': item.get('category', '通用'),
                'relevance_score': len(keywords)
            }
            self.knowledge_base.append(knowledge_item)
        
        # 归一化权重
        total = sum(self.keywords_weights.values()) or 1
        for kw in self.keywords_weights:
            self.keywords_weights[kw] = self.keywords_weights[kw] / total
        
        self.is_trained = True
        self._print_log("训练完成")
    
    def _get_example_training_data(self) -> List[Dict]:
        """获取示例训练数据"""
        return [
            {
                'question': '小麦什么时候播种？',
                'answer': '小麦一般适宜在秋季播种，北方地区通常在9-10月，南方地区在10-11月。播种深度3-5cm，行距15-20cm，每亩播种量约15-20公斤。播种时土壤温度应稳定在10℃以上。',
                'keywords': ['小麦', '播种', '时间', '种植'],
                'category': '种植'
            },
            {
                'question': '玉米缺肥怎么处理？',
                'answer': '玉米缺氮肥表现为叶片发黄，应追施尿素每亩10-15公斤；缺磷表现为根系发育不良，植株矮小，可追施过磷酸钙每亩20-30公斤；缺钾表现为边缘焦枯，可追施硫酸钾每亩10-15公斤。',
                'keywords': ['玉米', '缺肥', '施肥', '营养'],
                'category': '施肥'
            },
            {
                'question': '水稻病虫害防治方法？',
                'answer': '水稻常见病虫害包括稻瘟病、纹枯病、稻飞虱等。预防措施：1）选用抗病品种；2）合理密植，避免过密；3）科学施肥，增强植株抗性。发病初期可使用三环唑防治稻瘟病，井冈霉素防治纹枯病，噻嗪酮防治稻飞虱。',
                'keywords': ['水稻', '病虫害', '防治', '病害'],
                'category': '病虫害'
            },
            {
                'question': '如何进行水稻施肥？',
                'answer': '水稻施肥分为基肥、分蘖肥、穗肥三个阶段。基肥在整地时施入，占总施肥量的40-50%；分蘖肥在移栽后7-10天施入，促进分蘖；穗肥在幼穗分化期施入，提高结实率。氮磷钾比例一般为2:1:1。',
                'keywords': ['水稻', '施肥', '营养', '肥料'],
                'category': '施肥'
            },
            {
                'question': '小麦病虫害怎么防治？',
                'answer': '小麦主要病虫害有纹枯病、白粉病、蚜虫等。防治方法：1）选用抗病品种；2）合理轮作，避免连作；3）适时播种，避开病虫害高发期；4）发病初期可用三唑酮、多菌灵等药剂防治，蚜虫可用吡虫啉防治。',
                'keywords': ['小麦', '病虫害', '防治', '病害'],
                'category': '病虫害'
            },
            {
                'question': '玉米什么时候播种最好？',
                'answer': '玉米一般春播在4-5月，夏播在6-7月。播种深度3-5cm，行距50-60cm，株距25-30cm，每亩种植密度3000-4500株。土壤温度稳定在10℃以上时适宜播种。春播玉米产量较高，夏播玉米成熟快。',
                'keywords': ['玉米', '播种', '时间', '种植'],
                'category': '种植'
            },
            {
                'question': '农作物怎么灌溉最合理？',
                'answer': '合理灌溉是农作物高产的重要措施。原则是"少量多次"，避免大水漫灌。一般作物在播种后、分蘖期、抽穗期、灌浆期需水量较大，应及时灌溉。建议采用滴灌、喷灌等节水技术，可节水30-50%。',
                'keywords': ['灌溉', '浇水', '水', '旱'],
                'category': '管理'
            },
            {
                'question': '什么时间施肥效果最好？',
                'answer': '施肥时间应根据作物生长周期确定。基肥在播种前施入；追肥在作物生长期分次施入，一般在分蘖期、拔节期、抽穗期等关键时期。清晨或傍晚施肥效果较好，避免高温时段，可提高肥料利用率。',
                'keywords': ['施肥', '时间', '肥料', '营养'],
                'category': '施肥'
            },
            {
                'question': '作物缺水会有什么表现？',
                'answer': '作物缺水表现为叶片萎蔫、卷曲、颜色变深，生长缓慢，茎秆细弱。严重时叶片干枯脱落，果实发育不良，产量下降。应及时灌溉，补充水分。有条件的可采用土壤湿度监测设备，适时灌溉。',
                'keywords': ['缺水', '干旱', '浇水', '症状'],
                'category': '管理'
            },
            {
                'question': '如何预防作物病虫害？',
                'answer': '预防病虫害的关键是：1）选用抗病品种；2）合理轮作倒茬，打破病虫害循环；3）适时播种，避开病虫害高发期；4）科学施肥，增强植株抗性；5）及时清除病残体，减少病原；6）加强田间管理，保持通风透光；7）定期巡查，早发现早防治。',
                'keywords': ['病虫害', '预防', '防治', '管理'],
                'category': '病虫害'
            }
        ]
    
    def predict(self, input_data, context: List[Dict] = None, **kwargs):
        """
        预测：根据输入问题生成专业回答
        
        Args:
            input_data: 用户输入的问题（字符串或字典）
            context: 来自知识库的相关上下文（如果已经检索过）
            **kwargs: 额外参数
        
        Returns:
            包含专业回答的字典
        """
        # 处理输入格式
        if isinstance(input_data, dict):
            input_text = input_data.get('question', str(input_data))
        else:
            input_text = str(input_data)
        
        self._print_log(f"预测输入: {input_text}")
        
        if not self.is_trained and not self.knowledge_base:
            return {
                'professional_answer': '由于缺少训练数据，我暂时无法提供专业的农业建议。请先训练模型。',
                'confidence': 0.0,
                'matched_knowledge': None
            }
        
        # 如果提供了上下文，直接使用
        if context and len(context) > 0:
            best_match = context[0]
            return {
                'professional_answer': best_match.get('answer', ''),
                'confidence': best_match.get('similarity', 0.8),
                'matched_knowledge': best_match
            }
        
        # 在知识库中搜索
        input_lower = input_text.lower()
        matches = []
        
        for knowledge in self.knowledge_base:
            score = 0.0
            
            # 关键词匹配（权重最高）
            for kw in knowledge['keywords']:
                if kw.lower() in input_lower:
                    score += self.keywords_weights.get(kw, 0.5) * 2.0
            
            # 问题描述模糊匹配
            question_lower = knowledge['question'].lower()
            if any(word in question_lower for word in input_lower.split()):
                score += 0.5
            
            # 长度相似度
            length_ratio = min(len(input_text), len(knowledge['question'])) / max(len(input_text), len(knowledge['question']))
            score += length_ratio * 0.3
            
            if score > 0:
                knowledge['similarity'] = min(score, 1.0)
                matches.append(knowledge)
        
        # 按相似度排序
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        if matches and matches[0]['similarity'] > 0.3:
            best_match = matches[0]
            return {
                'professional_answer': best_match['answer'],
                'confidence': best_match['similarity'],
                'matched_knowledge': best_match
            }
        else:
            return {
                'professional_answer': '根据现有知识库，我暂时没有找到相关的专业农业信息。建议您咨询农业专家或查阅更专业的资料。',
                'confidence': 0.0,
                'matched_knowledge': None
            }
    
    def save_model(self, path: str = None):
        """保存模型"""
        save_path = path or self.model_path
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'knowledge_base': self.knowledge_base,
            'keywords_weights': self.keywords_weights,
            'is_trained': self.is_trained,
            'model_name': self.model_name,
            'model_type': self.model_type
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        self._print_log(f"模型已保存到: {save_path}")
    
    def load_model(self, path: str = None):
        """加载模型"""
        load_path = path or self.model_path
        load_path = Path(load_path)
        
        if not load_path.exists():
            self._print_log(f"模型文件不存在: {load_path}")
            return False
        
        with open(load_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        
        self.knowledge_base = model_data.get('knowledge_base', [])
        self.keywords_weights = model_data.get('keywords_weights', {})
        self.is_trained = model_data.get('is_trained', False)
        self.model_name = model_data.get('model_name', 'dm_agriculture_model')
        self.model_type = model_data.get('model_type', 'knowledge_retrieval')
        
        self._print_log(f"模型已从 {load_path} 加载")
        return True
    
    def feature_engineering(self, data):
        """特征工程（适配基类）"""
        pass


if __name__ == "__main__":
    # 测试代码
    dm = DataModule()
    
    # 训练
    dm.train(dm._get_example_training_data())
    
    # 预测
    result = dm.predict('小麦应该什么时候播种？')
    print("\n=== 测试预测 ===")
    print(f"专业回答: {result['professional_answer']}")
    print(f"置信度: {result['confidence']:.2f}")
    
    # 保存
    dm.save_model()
    print("\n=== 保存完成 ===")
