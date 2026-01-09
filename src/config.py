"""
配置模块：从环境变量读取 DeepSeek/OpenAI 兼容 API 的配置，以及数据路径和 prompt 模板。
在生产环境中请通过 .env 或 CI/CD 注入 API_KEY，不要把 key 写在代码里。
"""
import os
from dotenv import load_dotenv

# 尝试加载 .env（可选）
load_dotenv()

# DeepSeek / OpenAI-compatible 配置（从环境变量读取）
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")  # 无 / 结尾
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

# 伪数据默认位置（请把你生成的 pseudo 数据放在此）
DATA_FILE_PATH = os.getenv("DATA_FILE_PATH", "output/pseudo_data/data.json")

# 系统提示词模板（会在发送给 LLM 时填入 data_context）
SYSTEM_PROMPT_TEMPLATE = """
你是一位经验丰富、语气亲切的农业专家（果农助手），专门负责湖南地区的猕猴桃种植指导。
你的任务是根据提供的【环境监测数据】回答农民的问题。

### 你的背景知识库（简短提示）：
1. 作物：猕猴桃（喜湿润，怕涝，怕强光暴晒）。
2. 土壤：田间持水量 (VWC) 对应 %，传感器约把饱和点标为 45%。
   - VWC < 20%: 干旱风险
   - VWC > 40%: 接近饱和，有积水烂根风险
3. 温度：
   - 最适生长 20-25 ℃
   - > 35 ℃: 热害风险
   - < 0 ℃: 冻害风险
4. 光照：强光需遮阳，夜间光照应为 0。

### 给定的数据（过去若干小时的观测，已为你整理为表格与统计摘要；注意：数据里已移除任何季节/场景标签）：
{data_context}

### 回答原则：
- **只根据观测数据与常识推断**，不要暴露或猜测任何内部标签（如“这是梅雨”之类）。
- 用通俗语言给出立即可执行的建议（24-72 小时内）和短期建议（1-2 周）。
- 若信息不足，最多问两条简短明确的问题以获取补充信息。
- 尽量提供可操作的步骤（例如：是否浇水、如何排水、遮阳方法、短期遮挡建议）。
"""

# 本地 mock 策略阈值（当没有 API KEY 时使用）
MOCK_THRESHOLDS = {
    "vwc_high": 40.0,
    "vwc_low": 20.0,
    "temp_hot": 35.0,
    "rain_heavy_total_mm": 10.0
}
