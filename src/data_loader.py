"""
数据加载与整理模块
职责：
 - 从 output/pseudo_data/data.json 中读取原始观测（支持 list 或 {"data": [...] } 格式）
 - 截取最近 N 小时（默认 24h）
 - 移除任何可能泄露"scene_tag"或标签的列
 - 生成 LLM-friendly 的 Markdown 表格与简单统计摘要（便于放到 system prompt）
 - 返回 (markdown_table_str, summary_str, df_window) 三元组（df_window 仅在后端用于进一步逻辑）
"""

import os
import json
import pandas as pd
import numpy as np
from .config import DATA_FILE_PATH

def load_recent_data(hours: int = 24):
    """
    读取 DATA_FILE_PATH 中的最新 hours 小时数据。
    返回：
      sensor_markdown (str): Markdown 表格字符串（用于 prompt 中）
      summary_str (str): 简短统计摘要（用于 prompt）
      df_window (pd.DataFrame): 实际截取的 DataFrame（后端可复用）
    重要：会删除名为 'scene_tag' / 'scenario' 等列以防剧透
    """
    if not os.path.exists(DATA_FILE_PATH):
        return ("", "暂无传感器数据，请检查数据文件路径。", pd.DataFrame())

    with open(DATA_FILE_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # 兼容两种格式
    if isinstance(raw, dict) and "data" in raw:
        records = raw["data"]
    else:
        records = raw

    if not isinstance(records, list) or len(records) == 0:
        return ("", "数据文件为空或格式不正确。", pd.DataFrame())

    df = pd.DataFrame(records)

    # 安全清理：移除任何潜在的剧透列
    for spoil in ["scene_tag", "scenario", "label", "season"]:
        if spoil in df.columns:
            df = df.drop(columns=[spoil])

    # 保证常见列存在并按 timestamp 排序（如果存在 timestamp）
    if "timestamp" in df.columns:
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp').reset_index(drop=True)
        except Exception:
            # 若解析失败，保留原序但不抛异常
            pass

    # 采样最后 hours 行（假设每行为每小时）
    df_window = df.tail(hours).copy()

    # 只保留可信的列（不存在则跳过）
    cols_to_keep = ['timestamp', 'air_temp', 'humidity', 'rainfall', 'solar_rad', 'soil_vwc']
    valid_cols = [c for c in cols_to_keep if c in df_window.columns]
    df_window = df_window[valid_cols]

    # 为显示做列名映射（中文）
    col_map = {
        'timestamp': '时间',
        'air_temp': '气温(℃)',
        'humidity': '空气湿度(%)',
        'rainfall': '降雨量(mm)',
        'solar_rad': '光照(W/m²)',
        'soil_vwc': '土壤水分(%)'
    }
    df_display = df_window.rename(columns={c: col_map[c] for c in valid_cols if c in col_map})

    # 格式化时间列仅保留 YYYY-MM-DD HH:MM（节省 token）
    if '时间' in df_display.columns:
        try:
            df_display['时间'] = pd.to_datetime(df_display['时间']).dt.strftime('%m-%d %H:%M')
        except Exception:
            pass

    # 生成 Markdown 表（去掉 index）
    try:
        md = df_display.to_markdown(index=False)
    except Exception:
        # 若 to_markdown 不可用，手工生成简单 CSV 样式
        md = df_display.to_csv(index=False)

    # 统计摘要（尽量容错）
    def safe_col_stat(col):
        if col in df_window.columns and pd.api.types.is_numeric_dtype(df_window[col]):
            s = df_window[col].dropna()
            return {
                "mean": float(np.round(s.mean(), 2)) if len(s)>0 else None,
                "sum": float(np.round(s.sum(), 2)) if len(s)>0 else None,
                "min": float(np.round(s.min(), 2)) if len(s)>0 else None,
                "max": float(np.round(s.max(), 2)) if len(s)>0 else None,
            }
        else:
            return None

    stats = {
        "air_temp": safe_col_stat('air_temp'),
        "rainfall": safe_col_stat('rainfall'),
        "soil_vwc": safe_col_stat('soil_vwc'),
        "humidity": safe_col_stat('humidity'),
        "solar_rad": safe_col_stat('solar_rad')
    }

    # 构造可读的 summary 字符串（用于 prompt）
    summary_lines = []
    if stats["air_temp"] and stats["air_temp"]["mean"] is not None:
        summary_lines.append(f"平均气温: {stats['air_temp']['mean']:.1f} ℃ (近 {len(df_window)} 条)")
    if stats["rainfall"] and stats["rainfall"]["sum"] is not None:
        summary_lines.append(f"累计降雨: {stats['rainfall']['sum']:.1f} mm")
    if stats["soil_vwc"] and stats["soil_vwc"]["mean"] is not None:
        # 报告最新一个（尾部）土壤含水值以便更直观
        last_vwc = df_window['soil_vwc'].dropna().iloc[-1] if ('soil_vwc' in df_window.columns and len(df_window['soil_vwc'].dropna())>0) else None
        summary_lines.append(f"当前土壤水分(最近观测): {last_vwc:.1f}% " if last_vwc is not None else "")
    summary_str = "\n".join([ln for ln in summary_lines if ln])

    # 最终用于 prompt 的 data_context：表格 + 两行 summary
    data_context = f"{md}\n\n{summary_str}"

    return (data_context, summary_str, df_window)
