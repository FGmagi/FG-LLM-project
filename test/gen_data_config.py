# gen_data_config.py
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]

TAG = "test"

OUTPUT = {
    "out_dir": BASE_DIR / "output" / "pseudo_data",
    "plots_dir": BASE_DIR / "output" / "pseudo_data" / "plots",

    "json_path": BASE_DIR / "output" / "pseudo_data" / f"{TAG}.json",
    "csv_path": BASE_DIR / "output" / "pseudo_data" / f"{TAG}.csv",
    "pdf_path": BASE_DIR / "output" / "pseudo_data" / "plots" / f"{TAG}.pdf",
    "png_path": BASE_DIR / "output" / "pseudo_data" / "plots" / f"{TAG}.png",
}

RNG = {
    "seed": 2026
}

SOIL = {
    "soil_water_sat": 45.0,   # 饱和含水量（超过可能积水）
    "soil_water_fc": 32.0,    # 田间持水量（理想上限）
    "soil_water_ref": 20.0,   # 灌溉建议阈值
    "soil_water_wilt": 12.0,  # 休眠/永久损伤阈值
}

ET = {
    "day": 0.15,
    "night": 0.02,
}

INFILTRATION = {
    "base_rate": 0.60  # 基准入渗率（大雨时会按模型减少）
}

MEMORY = {
    "alpha_temp": 0.6,
    "alpha_solar": 0.6,
    "alpha_humidity": 0.8,
    "alpha_cloud": 0.8,
}

SLOW_CYCLE = {
    "slow_period": 14 * 24,  # 14 天尺度
    "slow_amp_temp": 0.0,   # 慢周期对温度振幅 (°C)
    "slow_amp_solar": 150.0,       # 慢周期对日间最大光照 (W/m2)
    "slow_amp_humidity": 3.0,      # 慢周期对湿度基线 (%)
}

RAIN_MODEL = {
    "base_stop_prob": 0.05,   # 已下雨时基本停止概率
    "start_scale": 0.1,       # p_start = rain_prob * start_scale
    "gamma_shape": 2.0,       # Gamma 分布 shape
    # 大雨时径流分量的平滑尺度（公式中用）
    "runoff_scale": 10.0,
    "max_runoff_frac": 0.7,
}

PLOT_SETTINGS = {
    "figsize": (12, 14),
    "dpi": 150,
    "palette": {
        "temp": "#d73027",     # 红
        "humidity": "#4575b4",       # 蓝
        "rain": "#1f78b4",     # 水蓝
        "soil_water": "#8c510a",      # 棕
        "solar": "#f39c12"     # 橙
    }
}

SCENARIOS = {
    "normal_spring": {
        "desc": "春季：日夜有明显摆动，偶有小阵雨",
        "temp_base": 18.0,
        "temp_amp": 4.0,
        "rain_prob": 0.20,
        "rain_intensity": 0.5,
        "init_soil_water": 28.0
    },
    "summer_heatwave": {
        "desc": "夏季高温干旱（短时高温）",
        "temp_base": 34.0,
        "temp_amp": 4.0,
        "rain_prob": 0.02,
        "rain_intensity": 0.5,
        "init_soil_water": 20.0
    },
    "rainy_season": {
        "desc": "梅雨/主汛期：长时多雨，累积水分高",
        "temp_base": 23.0,
        "temp_amp": 2.0,
        "rain_prob": 0.55,
        "rain_intensity": 1.5,
        "init_soil_water": 36.0
    },
    "sudden_cooling": {
        "desc": "倒春寒：短时大幅降温",
        "temp_base": 8.0,
        "temp_amp": 3.0,
        "rain_prob": 0.20,
        "rain_intensity": 0.5,
        "init_soil_water": 30.0
    },
    "typhoon_heavy": {
        "desc": "台风外环/残余：短时暴雨、强风",
        "temp_base": 26.0,
        "temp_amp": 2.0,
        "rain_prob": 0.80,
        "rain_intensity": 4.0,
        "init_soil_water": 34.0
    },
    "short_heavy": {
        "desc": "短时强对流：短时间内高强度降雨",
        "temp_base": 28.0,
        "temp_amp": 4.0,
        "rain_prob": 0.50,
        "rain_intensity": 4.0,
        "init_soil_water": 30.0
    },
    "today": {
        "desc": "today",
        "temp_base": 9.0,
        "temp_amp": 7.0,
        "rain_prob": 0.0,
        "rain_intensity": 0.0,
        "init_soil_water": 30.0
    }

}

DEFAULT_STORYLINE = [
    ("normal_spring", 2),
    ("summer_heatwave", 2),
    ("rainy_season", 2),
    ("short_heavy", 1),
    ("sudden_cooling", 1),
    ("typhoon_heavy", 1),
    ("today", 4)
]