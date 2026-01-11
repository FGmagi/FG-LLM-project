#!/usr/bin/env python3
"""
按小时产生伪气象数据用于测试。
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import argparse

from .gen_data_config import SCENARIOS, DEFAULT_STORYLINE, OUTPUT, RNG, SOIL, ET, INFILTRATION, MEMORY, SLOW_CYCLE, RAIN_MODEL, PLOT_SETTINGS
from .plot_utils import plot_sequence

# 工具函数
def diurnal_temp(hour, amp, phase_shift=8):
    """
    日周期，温度
    """
    return amp * np.sin(2 * np.pi * (hour - phase_shift) / 24.0)

def slow_cycle(index, slow_period, amp):
    """
    慢周期
    """
    return amp * np.sin(2 * np.pi * (index / slow_period))

def rain_markov_step(is_raining, current_rain, cfg, rain_model_params):
    """
    马尔可夫降雨: 决定是否开始/停止并返回小时雨强 (mm/h)
    - 有下雨则 Gamma 采样
    - 已下雨时以 p_stop 停雨，否则让 current_rain 平滑追随 target
    """
    p_rain = cfg['rain_prob']
    p_start = p_rain * rain_model_params.get("start_scale", 0.1)
    p_stop = rain_model_params.get("base_stop_prob", 0.05)

    if is_raining:
        if np.random.rand() < p_stop:
            return False, 0.0
        else:
            target = float(np.random.gamma(shape=rain_model_params.get("gamma_shape", 2.0),
                                           scale=cfg['rain_intensity'] / 2.0))
            # 平滑
            new_rain = 0.7 * current_rain + 0.3 * target if current_rain > 0 else target
            return True, round(new_rain, 2)
    else:
        if np.random.rand() < p_start:
            new_rain = float(np.random.gamma(shape=rain_model_params.get("gamma_shape", 2.0),
                                             scale=cfg['rain_intensity'] / 2.0))
            return True, round(new_rain, 2)
        else:
            return False, 0.0

def update_cloud(current_cloud, rain_rate, alpha_cloud):
    """
    cloud
    - 雨时 cloud_target ~ 0.85
    - 晴时 cloud_target 在小范围内随机
    """
    if rain_rate > 0.1:
        cloud_target = 0.85 + np.random.uniform(-0.05, 0.05)
    else:
        cloud_target = np.clip(0.05 + np.random.uniform(0.0, 0.35), 0.0, 0.6)
    # 平滑
    new_cloud = alpha_cloud * current_cloud + (1.0 - alpha_cloud) * cloud_target
    return float(np.clip(new_cloud, 0.0, 0.99))

def solar_target_from_angle(hour, slow_solar):
    """
    光照: 
    7.5-19.5有光照
    base_solar = max(0, base_solar_day + slow_solar)
    光照会再被 cloud 抑制
    """
    if 7.5 <= hour <= 19.5:
        base_solar_day = max(0.0, 800.0 * np.sin(np.pi * (hour - 7.5) / 12.0))
        return max(0.0, base_solar_day + slow_solar)
    else:
        return 0.0

def apply_cloud_mask(solar, cloud, cloud_power=1.5):
    """
    云遮蔽光:S = solar * (1 - cloud^p)
    """
    return solar * max(0.0, (1.0 - cloud ** cloud_power))

def update_AR1(current, target, alpha, noise_std=0.0):
    """
    通用 AR(1) 更新:x_{t+1} = alpha * x_t + (1-alpha) * target + noise
    """
    noise = np.random.normal(0, noise_std) if noise_std > 0 else 0.0
    return alpha * current + (1.0 - alpha) * target + noise

def infil_from_rain(rain_rate, current_rain, infil_base, runoff_scale, max_runoff_frac):
    """
    入渗
    """
    if rain_rate <= 0.0:
        return 0.0
    runoff_factor = np.clip(current_rain / (current_rain + runoff_scale), 0.0, max_runoff_frac)
    effective = infil_base * (1.0 - 0.5 * runoff_factor)
    return rain_rate * effective

def compute_et(current_solar, current_temp, et_day, et_night):
    """
    蒸腾 ET 模型(%/h)
    """
    solar_scale = (current_solar / 200.0) if current_solar > 0 else 0.0
    temp_scale = 1.0 + 0.05 * (current_temp - 20.0)
    temp_scale = max(0.5, temp_scale)
    base_et = et_day if current_solar > 100 else et_night
    et = base_et * (0.6 + 0.4 * solar_scale) * temp_scale
    return et

# 主生成函数
def gen(timeline_config, start_date="2025-01-09"):
    """
    按小时生成序列，返回 DataFrame(timestamp, scene_tag, temp, humidity, rain, solar, soil_water) 
    """
    hourly_cfgs = []
    scene_tags = []
    for scene_key, days in timeline_config:
        if scene_key not in SCENARIOS:
            raise ValueError(f"Unknown: {scene_key}")
        hours = int(days * 24)
        hourly_cfgs.extend([SCENARIOS[scene_key]] * hours)
        scene_tags.extend([scene_key] * hours)

    tot_hours = len(hourly_cfgs)
    dates = pd.date_range(start=start_date, periods=tot_hours, freq="h")

    temp_arr = np.zeros(tot_hours)
    rain_arr = np.zeros(tot_hours)
    solar_arr = np.zeros(tot_hours)
    humidity_arr = np.zeros(tot_hours)
    soil_water_arr = np.zeros(tot_hours)

    current_soil_water = hourly_cfgs[0]['init_soil_water']
    is_raining = False
    current_rain = 0.0
    current_temp = hourly_cfgs[0]['temp_base']
    current_solar = 0.0
    current_humidity = 60.0
    current_cloud = 0.1

    alpha_temp = MEMORY["alpha_temp"]
    alpha_solar = MEMORY["alpha_solar"]
    alpha_humidity = MEMORY["alpha_humidity"]
    alpha_cloud = MEMORY["alpha_cloud"]

    slow_period = SLOW_CYCLE["slow_period"]
    slow_amp_temp = SLOW_CYCLE["slow_amp_temp"]
    slow_amp_solar = SLOW_CYCLE["slow_amp_solar"]
    slow_amp_humidity = SLOW_CYCLE["slow_amp_humidity"]

    # 雨参数
    rain_params = {
        "base_stop_prob": RAIN_MODEL["base_stop_prob"],
        "start_scale": RAIN_MODEL["start_scale"],
        "gamma_shape": RAIN_MODEL["gamma_shape"]
    }
    runoff_scale = RAIN_MODEL["runoff_scale"]
    max_runoff_frac = RAIN_MODEL["max_runoff_frac"]

    # 小时循环
    for i in range(tot_hours):
        cfg = hourly_cfgs[i]
        hour_of_day = i % 24

        # 马尔可夫降雨
        is_raining, current_rain = rain_markov_step(is_raining, current_rain, cfg, rain_params)
        rain_arr[i] = round(current_rain, 2)

        # 日变化叠加慢周期
        diurnal_t = diurnal_temp(hour_of_day, cfg["temp_amp"])
        slow_t = slow_cycle(i, slow_period, slow_amp_temp)
        base_t = cfg["temp_base"] + diurnal_t + slow_t

        slow_s = slow_cycle(i, slow_period, slow_amp_solar)
        base_solar = solar_target_from_angle(hour_of_day, slow_s)

        slow_humidity = slow_cycle(i, slow_period, slow_amp_humidity)
        base_humidity_from_temp = 80 - 1.0 * (base_t - 15.0)
        base_humidity = base_humidity_from_temp + slow_humidity

        # 云
        current_cloud = update_cloud(current_cloud, current_rain, alpha_cloud)
        S_target = apply_cloud_mask(base_solar, current_cloud)

        # 湿度与温度目标耦合（雨会显著提高 humidity 并冷却温度) 
        if current_rain > 0.1:
            humidity_target = float(np.clip(np.random.uniform(85, 100), 85, 100))
            cooling = 2.0 + min(3.0, current_rain / max(0.1, cfg['rain_intensity'] + 1e-6) * 2.0)
            T_target = base_t - cooling
        else:
            T_target = base_t + np.random.normal(0, 0.3)  # 小噪声
            if current_soil_water > SOIL["soil_water_fc"]:
                soil_effect = 0.015 * (current_soil_water - SOIL["soil_water_fc"])
            else:
                soil_effect = 0.01 * (current_soil_water - SOIL["soil_water_fc"])
            humidity_target = float(np.clip(base_humidity + soil_effect, 5.0, 99.0))

        # AR(1) 更新。温度/光照/湿度 滞后于目标
        current_temp = update_AR1(current_temp, T_target, alpha_temp, noise_std=0.5)
        # 光照白天才有效，夜间为0
        current_solar = update_AR1(current_solar, S_target, alpha_solar, noise_std=5.0)
        if not (6 <= hour_of_day <= 18):
            current_solar = 0.0
        current_solar = max(0.0, current_solar)
        current_humidity = float(np.clip(update_AR1(current_humidity, humidity_target, alpha_humidity, noise_std=1.0), 5.0, 100.0))

        temp_arr[i] = round(current_temp, 1)
        solar_arr[i] = round(current_solar, 1)
        humidity_arr[i] = round(current_humidity, 1)

        # 土壤入渗与蒸散 
        inflow = infil_from_rain(rain_arr[i], current_rain, INFILTRATION["base_rate"], runoff_scale, max_runoff_frac)
        current_et = compute_et(current_solar, current_temp, ET["day"], ET["night"])
        # 干旱胁迫: 土壤过干会降低 ET
        stress = np.clip((current_soil_water - SOIL["soil_water_wilt"]) / (SOIL["soil_water_fc"] - SOIL["soil_water_wilt"]), 0.05, 1.0)
        current_et = current_et * stress

        current_soil_water = np.clip(current_soil_water + inflow - current_et, 0.0, SOIL["soil_water_sat"])
        soil_water_arr[i] = round(current_soil_water, 2)

    # 返回 df
    df = pd.DataFrame({
        "timestamp": dates,
        "scene_tag": scene_tags,
        "temp": temp_arr,
        "humidity": humidity_arr,
        "rain": rain_arr,
        "solar": solar_arr,
        "soil_water": soil_water_arr,
    })
    return df

# 保存/绘图/CLI
def save_results(df, json_path: Path, csv_path: Path):
    json_path.parent.mkdir(parents=True, exist_ok=True)
    
    df_copy = df.copy()
    df_copy['timestamp'] = df_copy['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(df_copy.to_dict(orient='records'), f, ensure_ascii=False, indent=2)
    df.to_csv(csv_path, index=False)
    return json_path, csv_path

def main(argv=None):
    parser = argparse.ArgumentParser(description="生成伪气象与土壤水分时间序列（小时) ")
    parser.add_argument("--story", nargs="+", help="剧情: scene_name days ...，例如 normal_spring 2 rainy_season 3", default=None)
    parser.add_argument("--start", type=str, default="2025-05-01")
    args = parser.parse_args(argv)

    # 解析情景
    if args.story:
        it = iter(args.story)
        storyline = []
        for scene in it:
            try:
                days = float(next(it))
            except StopIteration:
                raise ValueError("story 参数需成对出现: scene days")
            storyline.append((scene, days))
    else:
        storyline = DEFAULT_STORYLINE

    # RNG
    np.random.seed(RNG.get("seed", 2026))
    # 生成
    df = gen(storyline, start_date=args.start)

    # 从配置中获取完整路径
    json_path = OUTPUT["json_path"]
    csv_path = OUTPUT["csv_path"]
    pdf_path = OUTPUT["pdf_path"]
    png_path = OUTPUT["png_path"]

    # 保存数据
    save_results(df, json_path, csv_path)

    # 绘图配置
    plot_cfg = dict(PLOT_SETTINGS)
    plot_cfg['soil_sat'] = SOIL["soil_water_sat"]
    plot_cfg['soil_fc'] = SOIL["soil_water_fc"]
    plot_cfg['soil_ref'] = SOIL["soil_water_ref"]
    
    # 绘图
    plot_sequence(df, pdf_path, png_path, settings=plot_cfg)

    print(f"Data: {json_path}, {csv_path}")
    print(f"Plot: {pdf_path}, {png_path}")

if __name__ == "__main__":
    main()