"""
LLM 服务模块
职责：
 - 把 system prompt（含数据）与用户消息组合成 messages
 - 调用 DeepSeek/OpenAI-compatible chat/completions endpoint
 - 若未配置 API_KEY，使用内置启发式 mock 策略快速返回（便于离线测试）
注意：生产请务必配置真实 API_KEY，并使用安全存储方式。
"""

import os
import re
import json
import requests
from typing import Tuple
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL, SYSTEM_PROMPT_TEMPLATE, MOCK_THRESHOLDS

# 超时设置
REQUEST_TIMEOUT = 20

def _extract_numbers_from_summary(summary_str: str) -> dict:
    """
    从 summary_str 中提取平均气温、累计降雨、当前土壤水分等数字（若存在）。
    summary_str 是 data_loader 返回的简短统计文本。
    """
    res = {}
    if not summary_str:
        return res
    # 简单正则匹配数字
    m = re.search(r"平均气温: *([0-9.+-]+)", summary_str)
    if m:
        try:
            res['mean_temp'] = float(m.group(1))
        except:
            pass
    m = re.search(r"累计降雨: *([0-9.+-]+)", summary_str)
    if m:
        try:
            res['total_rain'] = float(m.group(1))
        except:
            pass
    m = re.search(r"当前土壤水分\(最近观测\): *([0-9.+-]+)", summary_str)
    if m:
        try:
            res['last_vwc'] = float(m.group(1))
        except:
            pass
    return res

def get_ai_response(user_message: str, data_context: str, summary_str: str) -> str:
    """
    将用户消息与 data_context 放入 system prompt，然后调用远端 LLM（DeepSeek）。
    如果 DEEPSEEK_API_KEY 未配置，则使用本地 mock 策略返回启发式建议（便于测试）。
    返回字符串（LLM 回复文本）
    """
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(data_context=data_context)

    # 如果没有配置 API KEY，使用本地 mock 策略
    if not DEEPSEEK_API_KEY:
        return _mock_response(user_message, summary_str)

    # 构造 messages（OpenAI-compatible）
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
        # 兼容不同厂商 response 结构
        if 'choices' in j and len(j['choices'])>0:
            c = j['choices'][0]
            if 'message' in c and 'content' in c['message']:
                return c['message']['content']
            if 'text' in c:
                return c['text']
        # 兜底
        return json.dumps(j, ensure_ascii=False, indent=2)
    except Exception as e:
        # 在 API 调用异常时返回错误信息（并给出 mock 作为备选）
        return f"LLM API 调用失败: {e}\n\n（已使用本地启发式建议代替）\n\n" + _mock_response(user_message, summary_str)

def _mock_response(user_message: str, summary_str: str) -> str:
    """
    简单启发式回答器：从 summary_str 中提取关键数值并给出安全、易懂的建议。
    目的是离线调试前端/后端连接逻辑以及验证 prompt 效果。
    """
    nums = _extract_numbers_from_summary(summary_str)
    mean_temp = nums.get('mean_temp')
    total_rain = nums.get('total_rain')
    last_vwc = nums.get('last_vwc')

    tips = []
    # 判断土壤水分
    if last_vwc is not None:
        if last_vwc >= MOCK_THRESHOLDS['vwc_high']:
            tips.append("土壤已经很湿了，不要浇水，必要时检查田间排水，避免烂根。")
        elif last_vwc <= MOCK_THRESHOLDS['vwc_low']:
            tips.append("土壤偏干，建议尽快补水（小水多次或早晚灌溉），注意避免正午直接灌水导致蒸发过快。")
        else:
            tips.append("土壤水分在可接受范围，保持常规管理。")
    # 综合降雨与温度
    if total_rain is not None and total_rain >= MOCK_THRESHOLDS['rain_heavy_total_mm']:
        tips.append("近期累计降雨较多，注意检查排水沟与果园低洼处，必要时启动抽水或疏导。")
    if mean_temp is not None and mean_temp >= MOCK_THRESHOLDS['temp_hot']:
        tips.append("近期温度偏高，建议白天遮阳、补充灌溉和喷薄叶面水以降温。")

    if not tips:
        tips = ["数据不足以自动判断，请提供更多观测（例如近 24 小时的温度/土壤水分/降雨数值）或允许连接云端模型。"]

    # 附加：如果用户问题明确询问“要不要浇水”，给出直接回答
    q = user_message.lower()
    if "浇水" in q or "要浇水" in q or "灌溉" in q:
        if last_vwc is not None:
            if last_vwc >= MOCK_THRESHOLDS['vwc_high']:
                direct = "不要浇水，现在土壤已经很湿，先排水。"
            elif last_vwc <= MOCK_THRESHOLDS['vwc_low']:
                direct = "应该浇水，推荐早晚各小量补水或持续滴灌至土壤水分回升。"
            else:
                direct = "目前可以按常规管理，如若有干点可适量补水。"
            tips.insert(0, direct)

    # 拼接为友好文本
    resp = "我看了你给的观测数据，给你几点建议：\n\n"
    for t in tips:
        resp += f"- {t}\n"
    resp += "\n如果你能告诉我：田间是否有积水？是否已经有遮阴设施？我可以进一步给出更具体的操作步骤。"
    return resp
