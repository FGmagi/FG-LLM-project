"""
LLM 服务模块
职责: 
 - 把 system prompt (含数据) 与用户消息组合成 messages
 - 调用 DeepSeek/OpenAI-compatible chat/completions endpoint
 - 若未配置 API_KEY, 使用内置启发式 mock 策略快速返回 (便于离线测试) 
注意: 生产请务必配置真实 API_KEY, 并使用安全存储方式。
"""

import os
import re
import json
import requests
from typing import Tuple, Optional
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, SYSTEM_PROMPT_TEMPLATE, MOCK_THRESHOLDS


REQUEST_TIMEOUT = 20

def _extract_numbers_from_summary(summary_str: str) -> dict:
    res = {}
    if not summary_str:
        return res
    # summary 由 data_loader 生成，格式固定
    m = re.search(r"Mean\s+temp[:\s]*([0-9.+-]+)\s*C", summary_str, flags=re.IGNORECASE)
    if m:
        try:
            res['mean_temp'] = float(m.group(1))
        except:
            pass
    m = re.search(r"Total\s+rain[:\s]*([0-9.+-]+)\s*mm", summary_str, flags=re.IGNORECASE)
    if m:
        try:
            res['total_rain'] = float(m.group(1))
        except:
            pass
    m = re.search(r"Latest\s+soil\s+VWC[:\s]*([0-9.+-]+)\s*%?", summary_str, flags=re.IGNORECASE)
    if m:
        try:
            res['last_vwc'] = float(m.group(1))
        except:
            pass

    return res


def get_ai_response(user_message: str, data_context: str, summary_str: str, system_prompt_template: Optional[str] = None) -> str:
    """
    将 user_message 与 data_context 组合到 prompt
    调用远端 LLM
    如果没有 DEEPSEEK_API_KEY, 就使用本地 _mock_response
    """
    template = system_prompt_template if system_prompt_template is not None else SYSTEM_PROMPT_TEMPLATE
    system_prompt = template.format(data_context=data_context)

    
    if not DEEPSEEK_API_KEY:
        return _mock_response(user_message, summary_str)

    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 500
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    url = DEEPSEEK_BASE_URL.rstrip("/") + "/chat/completions"
    try:
        resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        j = resp.json()
        
        if 'choices' in j and len(j['choices']) > 0:
            c = j['choices'][0]
            if isinstance(c, dict):
                # 兼容 OpenAI/DeepSeek 的返回格式
                if 'message' in c and isinstance(c['message'], dict) and 'content' in c['message']:
                    return c['message']['content']
                
                if 'text' in c:
                    return c['text']
        
        return json.dumps(j, ensure_ascii=False, indent=2)
    except Exception as e:
        # 远端异常时回退到本地启发式
        return f"LLM API 调用失败: {e}\n\n (已使用本地启发式建议代替) \n\n" + _mock_response(user_message, summary_str)


def _mock_response(user_message: str, summary_str: str) -> str:
    nums = _extract_numbers_from_summary(summary_str)
    mean_temp = nums.get('mean_temp')
    total_rain = nums.get('total_rain')
    last_vwc = nums.get('last_vwc')

    tips = []
    
    if last_vwc is not None:
        if last_vwc >= MOCK_THRESHOLDS['soil_water_high']:
            tips.append("土壤已经很湿了, 不要浇水, 必要时检查田间排水, 避免烂根。")
        elif last_vwc <= MOCK_THRESHOLDS['soil_water_low']:
            tips.append("土壤偏干, 建议尽快补水 (小水多次或早晚灌溉) , 注意避免正午直接灌水导致蒸发过快。")
        else:
            tips.append("土壤水分在可接受范围, 保持常规管理。")
    
    if total_rain is not None and total_rain >= MOCK_THRESHOLDS['rain_heavy_total_mm']:
        tips.append("近期累计降雨较多, 注意检查排水沟与果园低洼处, 必要时启动抽水或疏导。")
    if mean_temp is not None and mean_temp >= MOCK_THRESHOLDS['temp_hot']:
        tips.append("近期温度偏高, 建议白天遮阳、补充灌溉和喷薄叶面水以降温。")

    if not tips:
        tips = ["数据不足以自动判断, 请提供更多观测 (例如近 24 小时的温度/土壤水分/降雨数值) 或允许连接云端模型。"]

    
    # 简单关键词命中，给出更直接的“要不要浇水”回答
    q = user_message.lower()
    if "浇水" in q or "要浇水" in q or "灌溉" in q:
        if last_vwc is not None:
            if last_vwc >= MOCK_THRESHOLDS['soil_water_high']:
                direct = "不要浇水, 现在土壤已经很湿, 先排水。"
            elif last_vwc <= MOCK_THRESHOLDS['soil_water_low']:
                direct = "应该浇水, 推荐早晚各小量补水或持续滴灌至土壤水分回升。"
            else:
                direct = "目前可以按常规管理, 如若有干点可适量补水。"
            tips.insert(0, direct)

    
    resp = "我看了你给的观测数据, 给你几点建议: \n\n"
    for t in tips:
        resp += f"- {t}\n"
    resp += "\n如果你能告诉我: 田间是否有积水? 是否已经有遮阴设施? 我可以进一步给出更具体的操作步骤。"
    return resp
