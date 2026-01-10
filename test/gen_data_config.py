# gen_data_config.py
from pathlib import Path

# 项目根目录（根据文件位置自动计算）
BASE_DIR = Path(__file__).resolve().parents[1]

# 输出目录（可以由外部覆盖）
OUTPUT = {
    "out_dir": BASE_DIR / "output" / "pseudo_data",
    "plots_dir": BASE_DIR / "output" / "pseudo_data" / "plots",
}

# 随机数种子（可调）
RNG = {
    "seed": 2026
}

# 土壤 / 水分 阈值（%）
SOIL = {
    "VWC_SAT": 45.0,   # 饱和含水量（超过可能积水）
    "VWC_FC": 32.0,    # 田间持水量（理想上限）
    "VWC_REF": 20.0,   # 灌溉建议阈值
    "VWC_WILT": 12.0,  # 休眠/永久损伤阈值
}

# 蒸散（ET）基准速率（%/h）
ET = {
    "day": 0.15,
    "night": 0.02,
}

# 入渗基准（降雨 -> 土壤 的比例）
INFILTRATION = {
    "base_rate": 0.10  # 基准入渗率（大雨时会按模型减少）
}

# 系统记忆（AR(1)）系数 0..1，越大记忆越强
MEMORY = {
    "alpha_temp": 0.88,
    "alpha_solar": 0.82,
    "alpha_rh": 0.78,
    "alpha_cloud": 0.75,
}

# 慢周期参数（小时）
SLOW_CYCLE = {
    "period_hours": 14 * 24,  # 14 天尺度
    "amp_temp": 1.5,          # 慢周期对温度振幅 (°C)
    "amp_solar": 150.0,       # 慢周期对日间最大光照 (W/m2)
    "amp_rh": 3.0,            # 慢周期对湿度基线 (%)
}

# 降雨（马尔可夫）模型参数
RAIN_MODEL = {
    "base_stop_prob": 0.05,   # 已下雨时基本停止概率
    "start_scale": 0.1,       # p_start = rain_prob * start_scale
    "gamma_shape": 2.0,       # Gamma 分布 shape
    # 大雨时径流分量的平滑尺度（公式中用）
    "runoff_scale": 10.0,
    "max_runoff_frac": 0.7,
}

# 绘图设置（可按需调整）
PLOT_SETTINGS = {
    "figsize": (12, 14),
    "dpi": 150,
    "palette": {
        "temp": "#d73027",     # 红
        "rh": "#4575b4",       # 蓝
        "rain": "#1f78b4",     # 水蓝
        "vwc": "#8c510a",      # 棕
        "solar": "#f39c12"     # 橙
    }
}

# 场景定义（基础气候 + 逐小时统计特征）
SCENARIOS = {
    "normal_spring": {
        "desc": "春季：日夜有明显摆动，偶有小阵雨",
        "base_temp": 18.0,
        "temp_swing": 8.0,
        "rain_prob": 0.20,
        "rain_intensity": 2.0,  # 小阵雨时小时尺度平均 mm/h
        "init_vwc": 28.0
    },
    "summer_heatwave": {
        "desc": "夏季高温干旱（短时高温）",
        "base_temp": 34.0,
        "temp_swing": 9.0,
        "rain_prob": 0.02,
        "rain_intensity": 0.5,
        "init_vwc": 20.0
    },
    "rainy_season": {
        "desc": "梅雨/主汛期：长时多雨，累积水分高",
        "base_temp": 23.0,
        "temp_swing": 4.0,
        "rain_prob": 0.55,
        "rain_intensity": 6.0,   # 中到强降雨的常见尺度
        "init_vwc": 36.0
    },
    "sudden_cooling": {
        "desc": "倒春寒：短时大幅降温",
        "base_temp": 8.0,
        "temp_swing": 6.0,
        "rain_prob": 0.20,
        "rain_intensity": 3.0,
        "init_vwc": 30.0
    },
    # 新增情景：台风/极端强降雨（湖南会在夏末接台风残余）
    "typhoon_heavy": {
        "desc": "台风外环/残余：短时暴雨、强风",
        "base_temp": 26.0,
        "temp_swing": 5.0,
        "rain_prob": 0.85,
        "rain_intensity": 25.0,  # 局地小时可达几十 mm/h
        "init_vwc": 34.0
    },
    # 新增情景：短时强对流（雷暴）
    "short_heavy": {
        "desc": "短时强对流：短时间内高强度降雨",
        "base_temp": 28.0,
        "temp_swing": 8.0,
        "rain_prob": 0.35,
        "rain_intensity": 30.0,
        "init_vwc": 30.0
    }
}

# 默认剧情线（示例）
DEFAULT_STORYLINE = [
    ("normal_spring", 2),
    ("summer_heatwave", 3),
    ("rainy_season", 3),
    ("short_heavy", 1),
    ("sudden_cooling", 1),
    ("typhoon_heavy", 1)
]
