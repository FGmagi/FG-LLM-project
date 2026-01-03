"""
lm.py - 语言模型（LanguageModule）
功能：将专业农业知识转化为农民易懂的语言
数据来源：可使用 ds 或 Qwen 模型进行微调
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import re

# 尝试导入基类
try:
    from S001 import AgricultureAIModel
except ImportError:
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


class LanguageModule(AgricultureAIModel):
    """
    语言模型 (lm)
    
    功能：
    1. 将专业农业表述转换为农民易懂的通俗语言
    2. 可使用 Qwen 或 DeepSpeed 进行微调
    3. 内置专业术语到通俗语言的映射规则
    """
    
    def __init__(self):
        """初始化语言模型"""
        super().__init__("lm_translation_model", "language_translation")
        
        # 专业术语到通俗语言的映射
        self.term_dict = {}
        self.sentence_templates = []
        self.is_trained = False
        
        # 模型保存路径
        self.model_path = "models/lm_model.pkl"
        
        # 特征列和目标列
        self.feature_columns = ['professional_terms', 'sentence_structure']
        self.target_column = "colloquial_answer"
        
        # 是否使用 Qwen/DeepSpeed
        self.use_llm = False
        self.llm_model = None
        
        # 初始化默认规则
        self._init_default_rules()
    
    def _print_log(self, message: str):
        """记录日志"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"[LM] {timestamp} - {message}")
    
    def _init_default_rules(self):
        """初始化默认的转换规则"""
        # 专业术语映射（根据 ds 或 Qwen 模型输出优化）
        self.term_dict = {
            # 时间单位
            '秋季': '秋天', '春季': '春天', '夏季': '夏天', '冬季': '冬天',
            '适宜': '适合', '9-10月': '九十月', '10-11月': '十到十一月',
            '4-5月': '四五月份', '6-7月': '六七月份', '一般': '通常',
            
            # 农业术语
            '播种深度': '种多深', '行距': '行与行的距离', '株距': '株与株的距离',
            '每亩': '每块地', '尿素': '氮肥', '过磷酸钙': '磷肥',
            '硫酸钾': '钾肥', '追施': '再加', '施加': '加上',
            '纹枯病': '茎秆生病', '稻瘟病': '稻子长斑病',
            '白粉病': '叶子长白粉病', '稻飞虱': '小虫子', '蚜虫': '小虫子',
            '三环唑': '治斑药', '井冈霉素': '治茎药',
            '三唑酮': '杀菌药', '多菌灵': '杀菌药',
            '吡虫啉': '杀虫药', '噻嗪酮': '治虫药',
            
            # 状态描述
            '叶片发黄': '叶子黄了', '叶片萎蔫': '叶子蔫了',
            '根系发育不良': '根长不好', '边缘焦枯': '叶边干枯',
            '植株矮小': '苗长得矮', '表现为': '看起来',
            '预防措施': '预防方法', '建议': '最好', '主要': '主要是',
            
            # 其他
            '抗病品种': '不容易生病的种子', '合理密植': '种得疏密合适',
            '科学施肥': '按规矩施肥', '发病初期': '刚看到有病的时候',
            '合理轮作': '轮换着种', '避免连作': '不要老种一样的',
            '适时播种': '选好时间播种', '避开病虫害高发期': '躲开虫子多的时间',
            '土壤温度稳定': '地温稳定了', '增强植株抗性': '让庄稼更壮',
            '及时清除病残体': '把病叶子清理掉', '加强田间管理': '把地里管好',
            '保持通风透光': '让地里透风透气', '定期巡查': '常去地里看看',
            '早发现早防治': '早发现早治', '高产': '长得好产量高',
            '大水漫灌': '大水灌', '滴灌': '滴水浇', '喷灌': '喷水浇',
            '节水技术': '省水方法', '结实率': '结籽率', '拔节期': '长节的时候',
            '幼穗分化期': '长穗的时候', '结实率': '结籽率'
        }
        
        # 句式转换模板（适合农民语言习惯）
        self.sentence_templates = [
            {'pattern': r'一般适宜在(.*)', 'replacement': r'一般在\\1种最好'},
            {'pattern': r'每亩播种量约(.*)', 'replacement': r'每块地大概用\\1种子'},
            {'pattern': r'可追施(.*)', 'replacement': r'可以加点\\1'},
            {'pattern': r'表现为(.*)', 'replacement': r'看起来\\1'},
            {'pattern': r'建议(.*)', 'replacement': r'最好\\1'},
            {'pattern': r'主要(.*)', 'replacement': r'主要是\\1'},
            {'pattern': r'应(.*)', 'replacement': r'要\\1'},
            {'pattern': r'原则是(.*)', 'replacement': r'按\\1做'}
        ]
    
    def enable_qwen_model(self, model_path: str = None):
        """
        启用 Qwen 模型（可选）
        
        Args:
            model_path: Qwen 模型路径
        """
        self._print_log("启用 Qwen 模型模式")
        self.use_llm = True
        # 这里可以加载实际的 Qwen 模型
        # self.llm_model = load_qwen_model(model_path)
    
    def enable_deepspeed(self, model_path: str = None):
        """
        启用 DeepSpeed（可选）
        
        Args:
            model_path: 模型路径
        """
        self._print_log("启用 DeepSpeed 模式")
        self.use_llm = True
        # 这里可以初始化 DeepSpeed
        # self.llm_model = initialize_deepspeed(model_path)
    
    def train(self, training_data: List[Dict], **kwargs):
        """
        训练语言模型
        
        Args:
            training_data: 训练数据列表
                - professional: 专业表述
                - colloquial: 通俗表述
            **kwargs: 额外参数（可传入 qwen_model、deepspeed_config 等）
        """
        self._print_log(f"开始训练语言模型，训练数据量: {len(training_data)}")
        
        # 检查是否使用 LLM
        use_llm = kwargs.get('use_llm', False)
        qwen_model = kwargs.get('qwen_model', None)
        
        if use_llm and qwen_model:
            # 使用 Qwen 或 DeepSpeed 进行微调
            self._train_with_llm(training_data, qwen_model)
        else:
            # 使用规则和统计方法
            self._train_with_rules(training_data)
        
        self.is_trained = True
        self._print_log("语言模型训练完成")
    
    def _train_with_llm(self, training_data: List[Dict], llm_model):
        """
        使用 LLM（Qwen/DeepSpeed）进行训练
        
        Args:
            training_data: 训练数据
            llm_model: LLM 模型
        """
        self._print_log("使用 LLM 进行微调...")
        
        # 这里可以调用 Qwen 或 DeepSpeed 的微调接口
        # 示例伪代码：
        # for item in training_data:
        #     prompt = f"将以下专业农业知识转化为农民易懂的语言：{item['professional']}"
        #     target = item['colloquial']
        #     llm_model.fine_tune(prompt, target)
        
        self._print_log("LLM 微调完成（实际实现需要调用具体模型）")
    
    def _train_with_rules(self, training_data: List[Dict]):
        """
        使用规则方法训练
        
        Args:
            training_data: 训练数据
        """
        for item in training_data:
            if 'professional' not in item or 'colloquial' not in item:
                continue
            
            prof = item['professional']
            col = item['colloquial']
            
            # 提取专业术语映射
            words_prof = prof.split()
            words_col = col.split()
            
            # 简单的对齐和映射学习
            min_len = min(len(words_prof), len(words_col))
            for i in range(min_len):
                w1 = words_prof[i].strip('，。、；：？！""''（）【】')
                w2 = words_col[i].strip('，。、；：？！""''（）【】')
                if w1 and w2 and w1 != w2:
                    if w1 not in self.term_dict:
                        self.term_dict[w1] = w2
                    elif len(w2) < len(self.term_dict[w1]):
                        self.term_dict[w1] = w2
    
    def predict(self, input_data, context: Optional[Dict] = None, **kwargs):
        """
        预测：将专业表述转化为农民易懂的语言
        
        Args:
            input_data: 专业表述文本（字符串或字典）
            context: 上下文信息（可选）
            **kwargs: 额外参数
        
        Returns:
            包含通俗表述的字典
        """
        # 处理输入格式
        if isinstance(input_data, dict):
            professional_text = input_data.get('professional_answer', str(input_data))
        else:
            professional_text = str(input_data)
        
        self._print_log(f"输入专业文本: {professional_text[:50]}...")
        
        if not professional_text:
            return {
                'colloquial_answer': '',
                'confidence': 0.0,
                'conversions': []
            }
        
        # 如果启用了 LLM，使用 LLM 进行转换
        if self.use_llm and self.llm_model:
            return self._predict_with_llm(professional_text)
        else:
            return self._predict_with_rules(professional_text)
    
    def _predict_with_llm(self, professional_text: str) -> Dict[str, Any]:
        """
        使用 LLM 进行预测
        
        Args:
            professional_text: 专业文本
        
        Returns:
            预测结果
        """
        self._print_log("使用 LLM 进行转换...")
        
        # 调用 Qwen 或 DeepSpeed 模型
        # 示例伪代码：
        # prompt = f"将以下农业专业知识转化为农民易懂的通俗语言：{professional_text}"
        # colloquial = self.llm_model.generate(prompt)
        
        # 暂时使用规则方法
        return self._predict_with_rules(professional_text)
    
    def _predict_with_rules(self, professional_text: str) -> Dict[str, Any]:
        """
        使用规则方法预测
        
        Args:
            professional_text: 专业文本
        
        Returns:
            预测结果
        """
        colloquial = professional_text
        conversions = []
        confidence = 0.8 if self.is_trained else 0.6
        
        # 第一步：替换专业术语
        for prof_term, col_term in sorted(self.term_dict.items(), 
                                          key=lambda x: len(x[0]), reverse=True):
            if prof_term in colloquial:
                colloquial = colloquial.replace(prof_term, col_term)
                conversions.append({
                    'professional': prof_term,
                    'colloquial': col_term
                })
        
        # 第二步：应用句式转换
        for template in self.sentence_templates:
            pattern = template['pattern']
            replacement = template['replacement']
            if re.search(pattern, colloquial):
                colloquial = re.sub(pattern, replacement, colloquial)
        
        # 第三步：简化长句，添加口语化连接词
        colloquial = self._simplify_sentences(colloquial)
        
        # 第四步：移除过长的技术细节
        colloquial = self._simplify_technical_details(colloquial)
        
        return {
            'colloquial_answer': colloquial,
            'confidence': confidence,
            'conversions': conversions
        }
    
    def _simplify_sentences(self, text: str) -> str:
        """简化句子结构，更口语化"""
        # 将过长的句子拆分
        sentences = re.split(r'[。；；]', text)
        simplified = []
        
        for sent in sentences:
            sent = sent.strip()
            if len(sent) > 50:  # 超过50字就拆分
                parts = sent.split('，')
                for part in parts[:3]:  # 最多保留前3部分
                    if part.strip():
                        simplified.append(part.strip())
            else:
                if sent:
                    simplified.append(sent)
        
        # 用更自然的连接词重新组合
        result = []
        for i, sent in enumerate(simplified):
            if i == 0:
                result.append(sent)
            else:
                if sent.startswith('可') or sent.startswith('应'):
                    result.append('，' + sent)
                elif sent.startswith('比如') or sent.startswith('例如'):
                    result.append(sent)
                else:
                    result.append('，' + sent)
        
        # 合并成完整文本
        final_text = '。'.join(result[:5])  # 最多5句话
        if final_text and not final_text.endswith('。'):
            final_text += '。'
        
        return final_text
    
    def _simplify_technical_details(self, text: str) -> str:
        """简化技术细节"""
        # 移除括号内的技术说明
        text = re.sub(r'（[^）]*）', '', text)
        text = re.sub(r'\\([^)]*\\)', '', text)
        
        # 简化数字范围
        text = re.sub(r'(\\d+)-(\\d+)(cm|公斤|斤|克)', r'约\\1到\\2\\3', text)
        
        return text.strip()
    
    def save_model(self, path: str = None):
        """保存模型"""
        save_path = path or self.model_path
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        model_data = {
            'term_dict': self.term_dict,
            'sentence_templates': self.sentence_templates,
            'is_trained': self.is_trained,
            'model_name': self.model_name,
            'model_type': self.model_type,
            'use_llm': self.use_llm
        }
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(model_data, f, ensure_ascii=False, indent=2)
        
        self._print_log(f"语言模型已保存到: {save_path}")
    
    def load_model(self, path: str = None):
        """加载模型"""
        load_path = path or self.model_path
        load_path = Path(load_path)
        
        if not load_path.exists():
            self._print_log(f"模型文件不存在: {load_path}")
            return False
        
        with open(load_path, 'r', encoding='utf-8') as f:
            model_data = json.load(f)
        
        self.term_dict = model_data.get('term_dict', {})
        self.sentence_templates = model_data.get('sentence_templates', [])
        self.is_trained = model_data.get('is_trained', False)
        self.model_name = model_data.get('model_name', 'lm_translation_model')
        self.model_type = model_data.get('model_type', 'language_translation')
        self.use_llm = model_data.get('use_llm', False)
        
        self._print_log(f"语言模型已从 {load_path} 加载")
        return True
    
    def feature_engineering(self, data):
        """特征工程（适配基类）"""
        pass
    
    def translate_to_natural_language(self, ai_output):
        """
        翻译为自然语言（适配 S001 的 LanguageTranslationModel 接口）
        
        Args:
            ai_output: AI 输出的专业文本
        
        Returns:
            通俗语言文本
        """
        result = self.predict(ai_output)
        return result['colloquial_answer']


if __name__ == "__main__":
    # 测试代码
    lm = LanguageModule()
    
    # 测试转换
    test_input = "小麦一般适宜在秋季播种，北方地区通常在9-10月，南方地区在10-11月。播种深度3-5cm，行距15-20cm，每亩播种量约15-20公斤。"
    
    result = lm.predict(test_input)
    print("\n=== 语言模型测试 ===")
    print(f"专业表述: {test_input}")
    print(f"通俗表述: {result['colloquial_answer']}")
    print(f"置信度: {result['confidence']:.2f}")
    print(f"转换的术语: {result['conversions'][:5]}...")
    
    # 保存
    lm.save_model()
    print("\n=== 保存完成 ===")
