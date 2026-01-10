# src/data_loader.py
"""
数据加载与整理模块（针对 LLM prompt 优化的版本）
功能：
 - 支持从 pseudo data JSON （list 或 {"data": [...] }）读取记录
 - 支持通过 config 中的 REFERENCE_TIMESTAMP 指定一个时间点（用于测试）
 - 提取 reference_time 前后各若干小时的窗口（默认各 24h）
 - 删除可能泄露场景/标签的列
 - 以最小 token 成本的紧凑 CSV（短列名）和简短英文 summary 输出，供 DeepSeek/LLM 使用
 - 返回 (data_context_str, summary_str, df_window)

返回值说明：
 - data_context_str: 英文、紧凑的 CSV（含 header）+ 一行 summary（用于直接拼接到 prompt）
 - summary_str: 单独的英文摘要字符串
 - df_window: pandas.DataFrame，便于后端进一步处理/绘图

注意：代码内部以宽容但明确的方式处理错误（会抛异常以便上游捕获），便于早期发现协议错误。
"""

import os
import json
from datetime import datetime
from typing import Optional, Tuple

import pandas as pd
import numpy as np

# 从 config 读取 DATA_FILE_PATH 和可选的 REFERENCE_TIMESTAMP（测试用）
try:
    from config import DATA_FILE_PATH, REFERENCE_TIMESTAMP  # type: ignore
except Exception:
    # 如果 config 中没有 REFERENCE_TIMESTAMP，则默认为 None
    try:
        from config import DATA_FILE_PATH  # type: ignore
    except Exception:
        raise ImportError("请在 config.py 中定义 DATA_FILE_PATH（和可选的 REFERENCE_TIMESTAMP）")
    REFERENCE_TIMESTAMP = None


# 可配置的候选列（后端内部使用英文短名）
TRUSTED_COLS = ['timestamp', 'air_temp', 'humidity', 'rainfall', 'solar_rad', 'soil_vwc']
# 为节省 token 使用短列名喂给 LLM
SHORT_COL_MAP = {
    'timestamp': 'time',
    'air_temp': 'T',
    'humidity': 'H',
    'rainfall': 'R',
    'solar_rad': 'S',
    'soil_vwc': 'VWC'
}
# 用于去掉潜在剧透列
SPOIL_COLS = ["scene_tag", "scenario", "label", "season"]


# ---------- 工具函数 ----------

def _load_raw_records(path: str):
    """从 path 读取 JSON，并返回 records（list of dict）。
    支持两种格式：list 或 {"data": [...]}。其他情况会抛错。
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"data file not found: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        raw = json.load(f)

    # 兼容两种顶层格式
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
    """删除可能泄露的列（mutates -> returns new df）"""
    drop_cols = [c for c in SPOIL_COLS if c in df.columns]
    if drop_cols:
        return df.drop(columns=drop_cols)
    return df


def _ensure_timestamp_sorted(df: pd.DataFrame) -> pd.DataFrame:
    """将 timestamp 转为 datetime 并按时间升序排序。若没有 timestamp，直接返回原 df。
    若转换失败会抛出异常以暴露数据问题。
    """
    if 'timestamp' not in df.columns:
        return df

    df = df.copy()
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp').reset_index(drop=True)
    return df


def _select_window_by_time(df: pd.DataFrame, reference_time: Optional[datetime], hours: int = 24, direction: str = 'past') -> pd.DataFrame:
    """选择窗口：
    - direction == 'past'：返回 reference_time 及之前的 hours 条（按时间顺序）
    - direction == 'future'：返回 reference_time 之后的 hours 条（严格未来）
    如果 reference_time 为 None，则：
      - 'past' -> 返回 df 的最后 hours 行
      - 'future' -> 返回空 DataFrame
    返回的 df 保证为按时间升序排列的子集（index 重置）。
    """
    if 'timestamp' not in df.columns:
        # 没有时间列，按行数直接 tail/head
        if direction == 'past':
            return df.tail(hours).copy().reset_index(drop=True)
        else:
            return pd.DataFrame(columns=df.columns)

    # reference_time 是 datetime
    if reference_time is None:
        if direction == 'past':
            return df.tail(hours).copy().reset_index(drop=True)
        else:
            return pd.DataFrame(columns=df.columns)

    # 找到 reference_time 在 df 中的位置
    # past: 包含 <= reference_time 的最近 hours 条；future: > reference_time 的前 hours 条
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
    """将 df 转为紧凑 CSV 字符串，使用 SHORT_COL_MAP 中的短列名作为 header。
    为了节省 token：
      - 时间格式化为 MM-DD HH:MM
      - 数值保留最多 2 位小数并去除无意义的末尾 0
      - 使用最短列名（例如 T, H, VWC）
    返回的字符串示例：
      time,T,H,R,S,VWC\n05-01 00:00,17.6,66,0,0,27.99\n...
    """
    if df.empty:
        return ''

    # 选择可信列并重命名
    valid_cols = [c for c in cols if c in df.columns]
    if not valid_cols:
        return ''

    dfc = df[valid_cols].copy()

    # 时间格式
    if 'timestamp' in dfc.columns:
        dfc['timestamp'] = pd.to_datetime(dfc['timestamp']).dt.strftime('%m-%d %H:%M')

    # 数值格式化：保留最多 2 位小数并去掉末尾无意义 0
    def fmt_num(x):
        if pd.isna(x):
            return ''
        if isinstance(x, (int, np.integer)):
            return str(int(x))
        try:
            # 四舍五入到 2 位
            s = f"{float(round(float(x), 2)):.2f}"
            # 去掉末尾 .00 或 .10 -> .1
            if '.' in s:
                s = s.rstrip('0').rstrip('.')
            return s
        except Exception:
            return str(x)

    for c in dfc.columns:
        if c != 'timestamp' and pd.api.types.is_numeric_dtype(dfc[c].dtype):
            dfc[c] = dfc[c].map(fmt_num)

    # 重命名为短列名
    header = [SHORT_COL_MAP.get(c, c) for c in dfc.columns]
    rows = [','.join(header)]
    for _, row in dfc.iterrows():
        vals = [str(row[c]) if not pd.isna(row[c]) else '' for c in dfc.columns]
        rows.append(','.join(vals))
    return '\n'.join(rows)


def _summarize_window(df: pd.DataFrame) -> str:
    """生成英文简短 summary，用于 prompt 的独立行（易于 LLM 快速抓取）"""
    if df.empty:
        return 'No data available.'

    lines = []
    # mean temperature
    if 'air_temp' in df.columns and pd.api.types.is_numeric_dtype(df['air_temp'].dtype):
        s = df['air_temp'].dropna()
        if not s.empty:
            lines.append(f"Mean air temp: {round(float(s.mean()),1)} C over {len(df)} records")
    # total rainfall
    if 'rainfall' in df.columns and pd.api.types.is_numeric_dtype(df['rainfall'].dtype):
        s = df['rainfall'].dropna()
        if not s.empty:
            lines.append(f"Total rainfall: {round(float(s.sum()),2)} mm")
    # soil latest
    if 'soil_vwc' in df.columns and pd.api.types.is_numeric_dtype(df['soil_vwc'].dtype):
        s = df['soil_vwc'].dropna()
        if not s.empty:
            lines.append(f"Latest soil VWC: {round(float(s.iloc[-1]),2)} %")

    return ' | '.join(lines) if lines else 'No numeric summary.'


# ---------- 对外 API ----------

def _get_reference_time_from_config_or_arg(reference_time: Optional[str or datetime]) -> Optional[datetime]:
    """如果用户传入了 reference_time（str 或 datetime），优先使用；否则尝试从 REFERENCE_TIMESTAMP 读取；都没有则返回 None"""
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
    """读取 reference_time 前 pre_hours 小时数据（包括 reference_time 当点），返回 (compact_csv, summary, df_window)
    - data_context (compact_csv + "\n" + summary)
    - summary 为英文短句
    - df_window 为 pandas.DataFrame（按时间升序）
    """
    records = _load_raw_records(DATA_FILE_PATH)
    df = pd.DataFrame(records)
    df = _clean_spoilers(df)
    df = _ensure_timestamp_sorted(df)

    ref_dt = _get_reference_time_from_config_or_arg(reference_time)
    df_window = _select_window_by_time(df, ref_dt, hours=pre_hours, direction='past')

    # 生成紧凑 CSV 和 summary（英文）
    compact = _compact_csv_from_df(df_window, TRUSTED_COLS)
    summary = _summarize_window(df_window)
    data_context = compact + ('\n' + summary if summary else '')
    return data_context, summary, df_window


def load_forecast_window(post_hours: int = 24, reference_time: Optional[str or datetime] = None) -> Tuple[str, str, pd.DataFrame]:
    """读取 reference_time 后 post_hours 小时的数据（严格未来），同样返回 (compact_csv, summary, df_window)"""
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
    """同时获取 pre/post 两个窗口，返回字典便于一次性拼接 prompt。
    返回结构：{
      'pre': (data_context, summary, df),
      'post': (data_context, summary, df)
    }
    """
    pre = load_recent_window(pre_hours, reference_time)
    post = load_forecast_window(post_hours, reference_time)
    return {'pre': pre, 'post': post}


# 如果作为脚本直接运行，打印示例输出（方便本地测试）
if __name__ == '__main__':
    # 仅演示：请在 config.py 中设置 DATA_FILE_PATH，并可选设置 REFERENCE_TIMESTAMP
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
