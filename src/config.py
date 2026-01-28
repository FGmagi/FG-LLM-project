"""
配置模块：从环境变量读取 DeepSeek/OpenAI 兼容 API 的配置, 以及数据路径和 prompt 模板
在生产环境中请通过 .env 或 CI/CD 注入 API_KEY
"""
import os
import yaml
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))  # 项目根目录

# 用于本地测试窗口切分的参考时间（可在调用时覆盖）
REFERENCE_TIMESTAMP = "2025-01-18 15:00:00"

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

PROMPT_FILE_PATH = os.getenv("PROMPT_FILE_PATH", os.path.join(PROJECT_ROOT, "prompts/system.yaml"))

# 伪数据默认路径（可通过环境变量覆盖）
DATA_FILE_PATH = os.getenv("DATA_FILE_PATH", os.path.join(PROJECT_ROOT, "output/pseudo_data/test.json"))


def _load_system_prompt(file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data['system_prompt']
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt文件未找到: {file_path}")
    except KeyError:
        raise KeyError(f"Prompt文件格式错误，缺少 'system_prompt' 字段: {file_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Prompt文件YAML格式错误: {e}")


SYSTEM_PROMPT_TEMPLATE = _load_system_prompt(PROMPT_FILE_PATH)


MOCK_THRESHOLDS = {
    "soil_water_high": 40.0,
    "soil_water_low": 20.0,
    "rain_heavy_total_mm": 10.0,
    "temp_hot": 30.0
}
