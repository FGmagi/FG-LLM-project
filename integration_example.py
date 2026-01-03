"""
农业知识大语言模型 - 完整集成示例
演示如何在现有项目中集成 dm、lm 和 releaseIO
"""

# ============================================================================
# 示例 1: 在 S003.py 中使用 releaseIO
# ============================================================================

# S003.py 修改示例
from releaseIO import releaseIO, AgricultureQASystem

# 初始化问答系统
qa_system = AgricultureQASystem()
qa_system.load_models()

def chat(input_text):
    """
    对话函数 - 直接使用 releaseIO
    
    Args:
        input_text: 用户输入（问题）
    
    Returns:
        AI回答（字符串）
    """
    # 接口形式：输入是问题，输出是回答
    return releaseIO(input_text)

# 或使用 AgricultureQASystem
def chat_with_system(input_text):
    """
    对话函数 - 使用 AgricultureQASystem
    """
    return qa_system.query(input_text)


# ============================================================================
# 示例 2: 在 S002.py 中集成
# ============================================================================

# S002.py 修改示例
from dm import DataModule
from lm import LanguageModule
from releaseIO import AgricultureQASystem

class AgricultureAISystem:
    """农业AI系统"""
    
    def __init__(self):
        # 原有代码保留
        # self.model_a = SensorDataModel()
        # self.model_b = LanguageTranslationModel()
        
        # 使用新的模型
        self.model_a = DataModule()  # dm
        self.model_b = LanguageModule()  # lm
        
        # 问答系统
        self.qa_system = AgricultureQASystem()
        
        # downloader
        self.downloader = None
    
    def training_pipeline(self):
        """训练流水线"""
        print("开始训练流水线...")
        
        # 训练 dm（从 downloader 或示例数据）
        if self.downloader:
            self.model_a.train_from_downloader(
                downloader=self.downloader,
                user_id="your_user_id",
                device_key="device_key",
                begin_time="2025-01-01 00:00:00",
                end_time="2025-01-31 23:59:59"
            )
        else:
            # 使用示例数据
            self.model_a.train(self.model_a._get_example_training_data())
        
        # 训练 lm
        lm_training_data = [
            {'professional': '小麦一般适宜在秋季播种', 'colloquial': '小麦一般在秋天种最好'},
            {'professional': '玉米缺氮肥表现为叶片发黄', 'colloquial': '玉米缺氮叶子会变黄'},
        ]
        self.model_b.train(lm_training_data)
        
        # 保存模型
        self.model_a.save_model()
        self.model_b.save_model()
        
        # 加载到问答系统
        self.qa_system.load_models()
        
        print("训练流水线完成！")
    
    def inference_pipeline(self, user_question):
        """
        推理流水线 - 问答接口
        
        Args:
            user_question: 用户问题
        
        Returns:
            系统回答
        """
        # 使用问答系统
        return self.qa_system.query(user_question, downloader=self.downloader)
    
    # 兼容原有接口
    def get_answer(self, question):
        """获取答案（兼容原有接口）"""
        return self.inference_pipeline(question)


# ============================================================================
# 示例 3: 使用 Downloader 训练
# ============================================================================

def train_with_downloader_example(downloader):
    """使用 downloader 训练的完整示例"""
    
    from dm import DataModule
    from lm import LanguageModule
    from releaseIO import releaseIO
    
    print("=== 开始使用 Downloader 训练 ===\n")
    
    # 步骤1: 训练 dm
    print("步骤1: 训练 dm 模型")
    dm = DataModule()
    dm.train_from_downloader(
        downloader=downloader,
        user_id="your_user_id",
        device_key="your_device_key",
        begin_time="2025-01-01 00:00:00",
        end_time="2025-01-31 23:59:59"
    )
    dm.save_model()
    print("dm 训练完成！\n")
    
    # 步骤2: 训练 lm
    print("步骤2: 训练 lm 模型")
    lm = LanguageModule()
    lm_training_data = [
        # 这里可以添加更多专业-通俗对照数据
    ]
    lm.train(lm_training_data)
    lm.save_model()
    print("lm 训练完成！\n")
    
    # 步骤3: 测试问答
    print("步骤3: 测试问答功能")
    test_questions = [
        "小麦什么时候播种？",
        "玉米缺肥了怎么办？",
        "水稻怎么防治病虫害？"
    ]
    
    for question in test_questions:
        answer = releaseIO(question, dm_model=dm, lm_model=lm, downloader=downloader)
        print(f"问: {question}")
        print(f"答: {answer}\n")
    
    print("=== Downloader 训练完成 ===")


# ============================================================================
# 示例 4: 使用 Qwen/DeepSpeed（高级功能）
# ============================================================================

def train_with_qwen_example():
    """使用 Qwen 模型训练 lm 的示例"""
    
    from lm import LanguageModule
    
    print("=== 开始使用 Qwen 训练 lm ===\n")
    
    # 初始化 lm
    lm = LanguageModule()
    
    # 启用 Qwen 模型（需要安装 Qwen）
    # lm.enable_qwen_model("path/to/qwen/model")
    
    # 准备训练数据
    training_data = [
        {
            'professional': '小麦一般适宜在秋季播种',
            'colloquial': '小麦一般在秋天种最好'
        },
        {
            'professional': '玉米缺氮肥表现为叶片发黄',
            'colloquial': '玉米缺氮叶子会变黄'
        },
        # ... 更多数据
    ]
    
    # 使用 Qwen 训练
    lm.train(training_data, use_llm=True)
    
    # 保存模型
    lm.save_model()
    
    print("=== Qwen 训练完成 ===")


# ============================================================================
# 示例 5: 完整的问答流程
# ============================================================================

def complete_example():
    """完整的问答流程示例"""
    
    from dm import DataModule
    from lm import LanguageModule
    from releaseIO import releaseIO
    
    print("=== 完整问答流程示例 ===\n")
    
    # 1. 训练 dm
    print("1. 训练 dm 模型")
    dm = DataModule()
    dm.train(dm._get_example_training_data())
    dm.save_model()
    print("   dm 训练完成！\n")
    
    # 2. 训练 lm
    print("2. 训练 lm 模型")
    lm = LanguageModule()
    lm_training_data = [
        {'professional': '小麦一般适宜在秋季播种', 'colloquial': '小麦一般在秋天种最好'},
        {'professional': '玉米缺氮肥表现为叶片发黄', 'colloquial': '玉米缺氮叶子会变黄'},
        {'professional': '水稻常见病虫害包括稻瘟病', 'colloquial': '水稻常见病有稻子长斑病'},
    ]
    lm.train(lm_training_data)
    lm.save_model()
    print("   lm 训练完成！\n")
    
    # 3. 问答测试
    print("3. 问答测试")
    test_questions = [
        "小麦什么时候播种？",
        "玉米缺肥了怎么办？",
        "水稻怎么防治病虫害？",
        "请问怎么给庄稼浇水？"
    ]
    
    for i, question in enumerate(test_questions, 1):
        print(f"\n问题 {i}: {question}")
        answer = releaseIO(question, dm_model=dm, lm_model=lm)
        print(f"回答: {answer}")
    
    print("\n=== 示例完成 ===")


# ============================================================================
# 示例 6: 自定义训练数据
# ============================================================================

def custom_training_data_example():
    """使用自定义训练数据的示例"""
    
    from dm import DataModule
    from lm import LanguageModule
    
    print("=== 自定义训练数据示例 ===\n")
    
    # dm 自定义训练数据
    dm_data = [
        {
            'question': '你的作物出现什么问题？',
            'answer': '根据监测数据，作物土壤湿度偏低，建议及时灌溉。',
            'keywords': ['作物', '湿度', '灌溉'],
            'category': '管理'
        },
        {
            'question': '如何提高产量？',
            'answer': '提高产量需要合理施肥、及时灌溉、防治病虫害等多个方面配合。',
            'keywords': ['产量', '施肥', '灌溉', '病虫害'],
            'category': '管理'
        }
    ]
    
    # lm 自定义训练数据
    lm_data = [
        {
            'professional': '根据监测数据，作物土壤湿度偏低',
            'colloquial': '地里有点干了'
        },
        {
            'professional': '建议及时灌溉',
            'colloquial': '赶紧浇浇水'
        },
        {
            'professional': '提高产量需要合理施肥',
            'colloquial': '要想产量高，得按规矩施肥'
        }
    ]
    
    # 训练
    dm = DataModule()
    dm.train(dm_data)
    
    lm = LanguageModule()
    lm.train(lm_data)
    
    print("自定义训练数据训练完成！\n")
    
    # 测试
    from releaseIO import releaseIO
    answer = releaseIO("地里的庄稼咋了？", dm_model=dm, lm_model=lm)
    print(f"测试问题: 地里的庄稼咋了？")
    print(f"测试回答: {answer}")


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    print("\n" + "="*70)
    print("农业知识大语言模型 - 集成示例")
    print("="*70 + "\n")
    
    # 运行完整示例
    complete_example()
    
    print("\n" + "="*70)
    print("所有示例运行完成！")
    print("="*70)
