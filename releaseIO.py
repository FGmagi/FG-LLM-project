"""
releaseIO.py - 核心处理模块
功能：实现完整的问答流程
流程：用户问题 -> 知识库检索 -> 专业库提示词 -> dm -> lm -> 输出
"""

import time
from typing import Dict, Any, List, Optional
import re
import json
from pathlib import Path


class KnowledgeRetriever:
    """知识库检索器"""
    
    def __init__(self, downloader=None):
        """初始化检索器"""
        self.downloader = downloader
        self.local_knowledge = []
        self._init_local_knowledge()
    
    def _init_local_knowledge(self):
        """初始化本地知识库"""
        self.local_knowledge = [
            {
                'id': '001',
                'question': '小麦播种时间',
                'keywords': ['小麦', '播种', '时间', '种植'],
                'answer': '小麦一般适宜在秋季播种，北方地区通常在9-10月，南方地区在10-11月。播种深度3-5cm，行距15-20cm，每亩播种量约15-20公斤。播种时土壤温度应稳定在10℃以上。',
                'category': '种植'
            },
            {
                'id': '002',
                'question': '玉米缺肥处理',
                'keywords': ['玉米', '缺肥', '施肥', '营养'],
                'answer': '玉米缺氮肥表现为叶片发黄，应追施尿素每亩10-15公斤；缺磷表现为根系发育不良，植株矮小，可追施过磷酸钙每亩20-30公斤；缺钾表现为边缘焦枯，可追施硫酸钾每亩10-15公斤。',
                'category': '施肥'
            },
            {
                'id': '003',
                'question': '水稻病虫害防治',
                'keywords': ['水稻', '病虫害', '防治', '病害'],
                'answer': '水稻常见病虫害包括稻瘟病、纹枯病、稻飞虱等。预防措施：1）选用抗病品种；2）合理密植，避免过密；3）科学施肥，增强植株抗性。发病初期可使用三环唑防治稻瘟病，井冈霉素防治纹枯病，噻嗪酮防治稻飞虱。',
                'category': '病虫害'
            },
            {
                'id': '004',
                'question': '水稻施肥方法',
                'keywords': ['水稻', '施肥', '营养', '肥料'],
                'answer': '水稻施肥分为基肥、分蘖肥、穗肥三个阶段。基肥在整地时施入，占总施肥量的40-50%；分蘖肥在移栽后7-10天施入，促进分蘖；穗肥在幼穗分化期施入，提高结实率。氮磷钾比例一般为2:1:1。',
                'category': '施肥'
            },
            {
                'id': '005',
                'question': '小麦病虫害防治',
                'keywords': ['小麦', '病虫害', '防治', '病害'],
                'answer': '小麦主要病虫害有纹枯病、白粉病、蚜虫等。防治方法：1）选用抗病品种；2）合理轮作，避免连作；3）适时播种，避开病虫害高发期；4）发病初期可用三唑酮、多菌灵等药剂防治，蚜虫可用吡虫啉防治。',
                'category': '病虫害'
            },
            {
                'id': '006',
                'question': '玉米播种时间',
                'keywords': ['玉米', '播种', '时间', '种植'],
                'answer': '玉米一般春播在4-5月，夏播在6-7月。播种深度3-5cm，行距50-60cm，株距25-30cm，每亩种植密度3000-4500株。土壤温度稳定在10℃以上时适宜播种。春播玉米产量较高，夏播玉米成熟快。',
                'category': '种植'
            },
            {
                'id': '007',
                'question': '灌溉方法',
                'keywords': ['灌溉', '浇水', '水', '旱'],
                'answer': '合理灌溉是农作物高产的重要措施。原则是"少量多次"，避免大水漫灌。一般作物在播种后、分蘖期、抽穗期、灌浆期需水量较大，应及时灌溉。建议采用滴灌、喷灌等节水技术，可节水30-50%。',
                'category': '管理'
            }
        ]
    
    def retrieve(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        从知识库检索相关内容
        
        Args:
            query: 用户查询问题
            top_k: 返回前k个最相关的结果
        
        Returns:
            相关知识列表，按相关性排序
        """
        results = []
        query_lower = query.lower()
        
        for knowledge in self.local_knowledge:
            score = 0.0
            
            # 关键词匹配（权重最高）
            keywords = knowledge.get('keywords', [])
            for kw in keywords:
                if kw.lower() in query_lower:
                    score += 2.0
            
            # 问题相似度
            question = knowledge.get('question', '')
            question_lower = question.lower()
            query_words = set(query_lower.split())
            question_words = set(question_lower.split())
            overlap = query_words & question_words
            if overlap:
                score += len(overlap) * 0.5
            
            # 类别匹配
            category = knowledge.get('category', '')
            if category.lower() in query_lower:
                score += 0.3
            
            if score > 0:
                knowledge['similarity'] = min(score / 3.0, 1.0)
                results.append(knowledge)
        
        # 按相似度排序并返回top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results[:top_k]
    
    def build_prompt(self, query: str, retrieved_knowledge: List[Dict]) -> str:
        """
        构建提示词
        
        Args:
            query: 用户问题
            retrieved_knowledge: 检索到的知识
        
        Returns:
            构建好的提示词
        """
        prompt = f"用户问题：{query}\\n\\n"
        prompt += "相关知识：\\n"
        
        for i, knowledge in enumerate(retrieved_knowledge):
            prompt += f"{i+1}. {knowledge['answer']}\\n"
        
        prompt += "\\n请基于以上知识，用专业的农业知识回答用户的问题。"
        
        return prompt
    
    def update_from_downloader(self, downloader, user_id: str, device_key: str, 
                               begin_time: str, end_time: str):
        """
        从downloader更新知识库
        
        Args:
            downloader: 数据下载器实例
            user_id: 用户ID
            device_key: 设备编号
            begin_time: 开始时间
            end_time: 结束时间
        """
        if downloader is None:
            print("[KnowledgeRetriever] downloader为None，无法更新知识库")
            return
        
        try:
            print("[KnowledgeRetriever] 从downloader更新知识库...")
            # downloader.logIn("username", "password")
            # history_data = downloader.get_history_data(device_key, begin_time, end_time)
            # 处理数据并更新知识库...
            print("[KnowledgeRetriever] 知识库更新功能（待实现）")
        except Exception as e:
            print(f"[KnowledgeRetriever] 更新知识库失败: {e}")


# 导入dm和lm
try:
    from dm import DataModule
    from lm import LanguageModule
except ImportError:
    DataModule = None
    LanguageModule = None


def releaseIO(input_text: str, 
              dm_model = None, 
              lm_model = None,
              downloader=None) -> str:
    """
    核心问答处理函数
    
    完整流程：
    1. 用户输入问题
    2. 知识库检索
    3. 构建专业提示词
    4. dm（农业模型）生成专业回答
    5. lm（语言模型）转换为通俗语言
    6. 输出最终回答
    
    接口形式：输入是问题（字符串），输出是回答（字符串）
    
    Args:
        input_text: 用户输入的问题
        dm_model: DataModule实例（可选）
        lm_model: LanguageModule实例（可选）
        downloader: 数据下载器实例（可选）
    
    Returns:
        最终回答（通俗语言）
    """
    start_time = time.time()
    
    # 打印日志
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"[releaseIO] {timestamp} - 收到用户问题: {input_text}")
    
    try:
        # 初始化模型
        if dm_model is None:
            if DataModule is not None:
                dm_model = DataModule()
                dm_model.load_model()
                print("[releaseIO] dm模型初始化完成")
            else:
                print("[releaseIO] Warning: DataModule not available")
        
        if lm_model is None:
            if LanguageModule is not None:
                lm_model = LanguageModule()
                lm_model.load_model()
                print("[releaseIO] lm模型初始化完成")
            else:
                print("[releaseIO] Warning: LanguageModule not available")
        
        # 步骤1: 知识库检索
        retriever = KnowledgeRetriever(downloader)
        retrieved_knowledge = retriever.retrieve(input_text, top_k=3)
        
        print(f"[releaseIO] 检索到 {len(retrieved_knowledge)} 条相关知识")
        
        # 步骤2: 构建专业提示词
        if retrieved_knowledge:
            prompt = retriever.build_prompt(input_text, retrieved_knowledge)
            print(f"[releaseIO] 构建提示词: {prompt[:100]}...")
        else:
            prompt = input_text
            print("[releaseIO] 未检索到相关知识，直接使用用户问题")
        
        # 步骤3: dm生成专业回答
        if dm_model is not None:
            dm_result = dm_model.predict(prompt, context=retrieved_knowledge)
            professional_answer = dm_result['professional_answer']
            confidence = dm_result['confidence']
            print(f"[releaseIO] dm专业回答: {professional_answer[:100]}... (置信度: {confidence:.2f})")
        else:
            # 如果没有dm，直接使用检索到的知识
            if retrieved_knowledge:
                professional_answer = retrieved_knowledge[0]['answer']
            else:
                professional_answer = "抱歉，我没有找到相关的农业知识。"
            print("[releaseIO] 使用检索到的知识作为专业回答")
        
        # 步骤4: lm转换为通俗语言
        if lm_model is not None:
            lm_result = lm_model.predict(professional_answer)
            colloquial_answer = lm_result['colloquial_answer']
            print(f"[releaseIO] lm通俗回答: {colloquial_answer[:100]}...")
        else:
            colloquial_answer = professional_answer
            print("[releaseIO] 直接使用专业回答（未经过lm转换）")
        
        # 计算处理时间
        elapsed = time.time() - start_time
        print(f"[releaseIO] 处理完成，耗时: {elapsed:.2f}秒")
        
        # 返回最终答案
        return colloquial_answer
    
    except Exception as e:
        error_msg = f"处理过程中出现错误: {str(e)}"
        print(f"[releaseIO] ERROR - {error_msg}")
        return f"抱歉，系统遇到了一些问题，请稍后再试。错误信息：{error_msg}"


# 向后兼容的DemoIO函数
def DemoIO(input_text: str) -> str:
    """
    演示用的占位函数（向后兼容）
    """
    responses = {
        "你好": "您好！我是农业助手，有什么可以帮您的吗？",
        "天气": "建议您关注当地天气预报，合理安排农事活动。",
        "小麦": "小麦一般在秋季播种，春季收获。需要充足的光照和适量的水分。",
        "玉米": "玉米喜温，春季或夏季播种都可以。记得及时施肥和浇水。",
        "水稻": "水稻需要充足的水分，主要在南方种植。注意防治病虫害。",
        "施肥": "合理施肥要根据作物需求进行，一般分为基肥、追肥等几个阶段。"
    }
    
    for key, value in responses.items():
        if key in input_text:
            return value
    
    return "您好！我是农业助手，请问您有什么农业方面的问题需要咨询？"


# 适配S002的AgricultureQASystem类
class AgricultureQASystem:
    """
    农业问答系统
    作为S002 AgricultureAISystem的一部分或替代
    """
    
    def __init__(self):
        self.dm_model = None
        self.lm_model = None
        self.knowledge_retriever = KnowledgeRetriever()
        self.is_trained = False
    
    def load_models(self, dm_path=None, lm_path=None):
        """加载已训练的模型"""
        if DataModule is not None:
            self.dm_model = DataModule()
            self.dm_model.load_model(dm_path)
        
        if LanguageModule is not None:
            self.lm_model = LanguageModule()
            self.lm_model.load_model(lm_path)
        
        self.is_trained = True
        print("[AgricultureQASystem] 模型加载完成")
    
    def query(self, question: str, downloader=None) -> str:
        """
        查询接口（对外提供的API）
        
        Args:
            question: 用户问题
            downloader: 数据下载器（可选）
        
        Returns:
            回答
        """
        return releaseIO(question, 
                       dm_model=self.dm_model, 
                       lm_model=self.lm_model,
                       downloader=downloader)


if __name__ == "__main__":
    # 测试代码
    print("\n" + "="*70)
    print("测试 releaseIO 功能")
    print("="*70 + "\n")
    
    test_questions = [
        "小麦什么时候播种？",
        "玉米缺肥了怎么办？",
        "水稻怎么防治病虫害？",
        "请问怎么给庄稼浇水？"
    ]
    
    for question in test_questions:
        print("\n" + "-"*60)
        print(f"用户问题: {question}")
        print("-"*60)
        
        answer = releaseIO(question)
        
        print(f"\n最终回答: {answer}")
        print()
    
    print("\n" + "="*70)
    print("测试完成")
    print("="*70)
