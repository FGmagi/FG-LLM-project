
"""
数据加载与整理
功能：
 - 支持从 pseudo data JSON (list 或 {"data": [...] })读取记录
 - 支持通过 config 中的 REFERENCE_TIMESTAMP 指定一个时间点(用于测试)
 - 提取 reference_time 前后各若干小时的窗口(默认各 24h)
 - 删除可能泄露场景/标签的列
 - 以最小 token 成本的紧凑 CSV(短列名)和简短英文 summary 输出, 供 DeepSeek/LLM 使用
 - 返回 (data_context_str, summary_str, df_window)
"""

import os
import json
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
import numpy as np


try:
    # 兼容直接运行或包内导入
    from config import DATA_FILE_PATH, REFERENCE_TIMESTAMP  
except Exception:
    
    try:
        from config import DATA_FILE_PATH  
    except Exception:
        raise ImportError("请在 config.py 中定义 DATA_FILE_PATH(和可选的 REFERENCE_TIMESTAMP)")
    REFERENCE_TIMESTAMP = None




TRUSTED_COLS = ['timestamp', 'temp', 'humidity', 'rain', 'solar', 'soil_water']

SHORT_COL_MAP = {
    'timestamp': 'time',
    'temp': 'T',
    'humidity': 'H',
    'rain': 'R',
    'solar': 'S',
    'soil_water': 'VWC'
}

SPOIL_COLS = ["scene_tag", "scenario", "label", "season"]



def _load_raw_records(path: str):
    if not os.path.exists(path):
        raise FileNotFoundError(f"data file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    
    # 支持 list 或 {"data": [...]} 两种顶层结构
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, dict) and 'data' in raw and isinstance(raw['data'], list):
        records = raw['data']
    else:
        raise TypeError('JSON 顶层应为 list 或 dict 且包含 `data` 字段')

    if len(records) == 0:
        raise ValueError('data JSON 为空')

    return records


def _clean_spoilers(df: pd.DataFrame) -> pd.DataFrame:
    drop_cols = [c for c in SPOIL_COLS if c in df.columns]
    if drop_cols:
        return df.drop(columns=drop_cols)
    return df


def _ensure_timestamp_sorted(df: pd.DataFrame) -> pd.DataFrame:
    if 'timestamp' not in df.columns:
        return df

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def _select_window_by_time(df: pd.DataFrame, reference_time: Optional[datetime], hours: int = 24, direction: str = 'past') -> pd.DataFrame:
    if 'timestamp' not in df.columns:
        # 无时间戳时，默认按行视作小时序列
        if direction == 'past':
            return df.tail(hours).copy().reset_index(drop=True)
        else:
            return pd.DataFrame(columns=df.columns)

    
    if reference_time is None:
        # 未给参考时间，则默认取最新窗口
        if direction == 'past':
            return df.tail(hours).copy().reset_index(drop=True)
        else:
            return pd.DataFrame(columns=df.columns)

    
    
    if direction == 'past':
        mask = df['timestamp'] <= reference_time
        df_past = df[mask]
        if df_past.empty:
            return pd.DataFrame(columns=df.columns)
        return df_past.tail(hours).copy().reset_index(drop=True)
    else:
        mask = df['timestamp'] > reference_time
        df_future = df[mask]
        if df_future.empty:
            return pd.DataFrame(columns=df.columns)
        return df_future.head(hours).copy().reset_index(drop=True)


def _compact_csv_from_df(df: pd.DataFrame, cols: list) -> str:
    if df.empty:
        return ''

    
    # 仅保留可信的列，避免泄露场景标签
    valid_cols = [c for c in cols if c in df.columns]
    if not valid_cols:
        return ''

    dfc = df[valid_cols].copy()

    
    if 'timestamp' in dfc.columns:
        dfc['timestamp'] = pd.to_datetime(dfc['timestamp']).dt.strftime('%m-%d %H:%M')

    
    def fmt_num(x):
        if pd.isna(x):
            return ''
        if isinstance(x, (int, np.integer)):
            return str(int(x))
        try:
            # 保留两位小数，去掉尾部 0
            s = f"{float(round(float(x), 2)):.2f}"
            
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        except Exception:
            return str(x)

    for c in dfc.columns:
        if c != 'timestamp' and pd.api.types.is_numeric_dtype(dfc[c].dtype):
            dfc[c] = dfc[c].map(fmt_num)

    
    header = [SHORT_COL_MAP.get(c, c) for c in dfc.columns]
    rows = [','.join(header)]
    for _, row in dfc.iterrows():
        vals = [str(row[c]) if not pd.isna(row[c]) else '' for c in dfc.columns]
        rows.append(','.join(vals))
    return '\n'.join(rows)


def _summarize_window(df: pd.DataFrame) -> str:
    if df.empty:
        return 'No data available.'

    lines = []
    
    if 'temp' in df.columns and pd.api.types.is_numeric_dtype(df['temp'].dtype):
        s = df['temp'].dropna()
        if not s.empty:
            lines.append(f"Mean temp: {round(float(s.mean()),1)} C over {len(df)} records")
    
    if 'rain' in df.columns and pd.api.types.is_numeric_dtype(df['rain'].dtype):
        s = df['rain'].dropna()
        if not s.empty:
            lines.append(f"Total rain: {round(float(s.sum()),2)} mm")
    
    if 'soil_water' in df.columns and pd.api.types.is_numeric_dtype(df['soil_water'].dtype):
        s = df['soil_water'].dropna()
        if not s.empty:
            lines.append(f"Latest soil VWC: {round(float(s.iloc[-1]),2)} %")

    return ' | '.join(lines) if lines else 'No numeric summary.'




def _get_reference_time_from_config_or_arg(reference_time: Optional[str or datetime]) -> Optional[datetime]:
    if reference_time is None and REFERENCE_TIMESTAMP is None:
        return None

    rt = reference_time if reference_time is not None else REFERENCE_TIMESTAMP
    if isinstance(rt, datetime):
        return rt
    try:
        return pd.to_datetime(str(rt))
    except Exception:
        raise ValueError('reference_time 无法解析为 datetime')


def load_recent_window(pre_hours: int = 24, reference_time: Optional[str or datetime] = None) -> Tuple[str, str, pd.DataFrame]:
    records = _load_raw_records(DATA_FILE_PATH)
    df = pd.DataFrame(records)
    df = _clean_spoilers(df)
    df = _ensure_timestamp_sorted(df)

    ref_dt = _get_reference_time_from_config_or_arg(reference_time)
    df_window = _select_window_by_time(df, ref_dt, hours=pre_hours, direction='past')

    
    compact = _compact_csv_from_df(df_window, TRUSTED_COLS)
    summary = _summarize_window(df_window)
    data_context = compact + ('\n' + summary if summary else '')
    return data_context, summary, df_window


def load_forecast_window(post_hours: int = 24, reference_time: Optional[str or datetime] = None) -> Tuple[str, str, pd.DataFrame]:
    records = _load_raw_records(DATA_FILE_PATH)
    df = pd.DataFrame(records)
    df = _clean_spoilers(df)
    df = _ensure_timestamp_sorted(df)

    ref_dt = _get_reference_time_from_config_or_arg(reference_time)
    df_window = _select_window_by_time(df, ref_dt, hours=post_hours, direction='future')

    compact = _compact_csv_from_df(df_window, TRUSTED_COLS)
    summary = _summarize_window(df_window)
    data_context = compact + ('\n' + summary if summary else '')
    return data_context, summary, df_window


def load_both_windows(pre_hours: int = 24, post_hours: int = 24, reference_time: Optional[str or datetime] = None) -> dict:
    pre = load_recent_window(pre_hours, reference_time)
    post = load_forecast_window(post_hours, reference_time)
    return {'pre': pre, 'post': post}



if __name__ == '__main__':
    
    try:
        dc_pre, s_pre, df_pre = load_recent_window()
        print('=== PRE WINDOW ===')
        print(dc_pre[:1000])
    except Exception as e:
        print('Error while loading pre window:', e)

    try:
        dc_post, s_post, df_post = load_forecast_window()
        print('\n=== POST WINDOW ===')
        print(dc_post[:1000])
    except Exception as e:
        print('Error while loading post window:', e)
