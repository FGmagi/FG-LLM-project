#!/usr/bin/env python3
"""
主模块：按小时产生伪气象与土壤水分序列（面向测试）。
逻辑被拆为多个小函数，变量与参数放在 gen_data_config.py 中。
"""

import json
from pathlib import Path
import numpy as np
import pandas as pd
import argparse

# 兼容相对/绝对导入（便于直接运行或用 -m）
try:
    from .gen_data_config import SCENARIOS, DEFAULT_STORYLINE, OUTPUT, RNG, SOIL, ET, INFILTRATION, MEMORY, SLOW_CYCLE, RAIN_MODEL, PLOT_SETTINGS
except Exception:
    from gen_data_config import SCENARIOS, DEFAULT_STORYLINE, OUTPUT, RNG, SOIL, ET, INFILTRATION, MEMORY, SLOW_CYCLE, RAIN_MODEL, PLOT_SETTINGS

from .plot_utils import plot_sequence

# -------------------- 辅助函数（物理量子模块化） --------------------

def diurnal_temp(hour, amplitude, phase_shift=8):
    """
    日变化：用正弦表示
    diurnal(t) = amplitude/2 * sin(2π*(hour - phase_shift)/24)
    amplitude 为日摆幅（峰到峰）
    """
    return np.sin(2 * np.pi * (hour - phase_shift) / 24.0) * (amplitude / 2.0)

def slow_cycle_component(index, period_hours, amp):
    """
    慢周期成分（例如 14 天）：slow = amp * sin(2π * index / period)
    """
    return amp * np.sin(2 * np.pi * (index / period_hours))

def rain_markov_step(is_raining, current_rain, cfg, rain_model_params):
    """
    马尔可夫降雨：决定是否开始/停止并返回小时雨强（mm/h）
    - 当启动时，从 Gamma(scale=cfg['rain_intensity']/2, shape=rain_model_params['gamma_shape']) 采样
    - 已下雨时以 p_stop 停雨，否则让 current_rain 平滑追随 target
    """
    p_rain = cfg['rain_prob']
    p_start = p_rain * rain_model_params.get("start_scale", 0.1)
    p_stop = rain_model_params.get("base_stop_prob", 0.05)

    if is_raining:
        if np.random.rand() < p_stop:
            return False, 0.0
        else:
            # 事件级目标强度
            target = float(np.random.gamma(shape=rain_model_params.get("gamma_shape", 2.0),
                                           scale=cfg['rain_intensity'] / 2.0))
            # 小时平滑：AR(1)-style (这里固定系数 0.7/0.3 保持和原逻辑一致)
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
    cloud 的更新（0..1）：
    - 雨时 cloud_target ~ 0.85
    - 晴时 cloud_target 在小范围内随机
    使用 AR(1)： cloud_{t+1} = alpha_cloud * cloud_t + (1-alpha_cloud) * cloud_target
    """
    if rain_rate > 0.1:
        cloud_target = 0.85 + np.random.uniform(-0.05, 0.05)
    else:
        cloud_target = np.clip(0.05 + np.random.uniform(0.0, 0.35), 0.0, 0.6)
    new_cloud = alpha_cloud * current_cloud + (1.0 - alpha_cloud) * cloud_target
    return float(np.clip(new_cloud, 0.0, 0.99))

def solar_target_from_angle(hour, slow_solar):
    """
    日间光照模型（近似）：
    base_solar_day = 800 * sin(pi * (hour - 6) / 12), 6..18 点
    base_solar = max(0, base_solar_day + slow_solar)
    最终光照再被 cloud 抑制。
    """
    if 6 <= hour <= 18:
        base_solar_day = max(0.0, 800.0 * np.sin(np.pi * (hour - 6) / 12.0))
        return max(0.0, base_solar_day + slow_solar)
    else:
        return 0.0

def apply_cloud_mask(solar, cloud, cloud_power=1.5):
    """
    非线性云遮蔽：S = solar * (1 - cloud^p)
    """
    return solar * max(0.0, (1.0 - cloud ** cloud_power))

def update_AR1(current, target, alpha, noise_std=0.0):
    """
    通用 AR(1) 更新：x_{t+1} = alpha * x_t + (1-alpha) * target + noise
    返回标量
    """
    noise = np.random.normal(0, noise_std) if noise_std > 0 else 0.0
    return alpha * current + (1.0 - alpha) * target + noise

def infiltration_from_rain(rain_rate, current_rain, infil_base, runoff_scale, max_runoff_frac):
    """
    入渗模型：考虑大雨时径流
    - runoff_factor = clip(current_rain/(current_rain + runoff_scale), 0, max_runoff_frac)
    - effective_infiltration = infil_base * (1 - 0.5 * runoff_factor)
    - inflow = rain_rate * effective_infiltration
    """
    if rain_rate <= 0.0:
        return 0.0
    runoff_factor = np.clip(current_rain / (current_rain + runoff_scale), 0.0, max_runoff_frac)
    effective = infil_base * (1.0 - 0.5 * runoff_factor)
    return rain_rate * effective

def compute_et(current_solar, current_temp, et_day, et_night):
    """
    蒸腾/蒸散率 ET 模型（%/h）
    公式说明：
      solar_scale = current_solar / 200 (solar=100 时接近 0.5)
      temp_scale = max(0.5, 1 + 0.05*(T - 20))
      base_et = et_day if current_solar > 100 else et_night
      ET = base_et * (0.6 + 0.4*solar_scale) * temp_scale
    返回 ET（%/h）
    """
    solar_scale = (current_solar / 200.0) if current_solar > 0 else 0.0
    temp_scale = 1.0 + 0.05 * (current_temp - 20.0)
    temp_scale = max(0.5, temp_scale)
    base_et = et_day if current_solar > 100 else et_night
    et = base_et * (0.6 + 0.4 * solar_scale) * temp_scale
    return et

# -------------------- 主生成函数 --------------------

def generate_integrated_series(timeline_config, start_date="2025-05-01"):
    """
    按小时生成序列，返回 DataFrame（timestamp, scene_tag, air_temp, humidity, rainfall, solar_rad, soil_vwc）
    """
    # 1. 展开剧情到逐小时配置
    hourly_cfgs = []
    scene_tags = []
    for scene_key, days in timeline_config:
        if scene_key not in SCENARIOS:
            raise ValueError(f"未知场景: {scene_key}")
        hours = int(days * 24)
        hourly_cfgs.extend([SCENARIOS[scene_key]] * hours)
        scene_tags.extend([scene_key] * hours)

    tot_hours = len(hourly_cfgs)
    dates = pd.date_range(start=start_date, periods=tot_hours, freq="h")

    # 2. 初始化输出 buffer
    temp_arr = np.zeros(tot_hours)
    rain_arr = np.zeros(tot_hours)
    solar_arr = np.zeros(tot_hours)
    rh_arr = np.zeros(tot_hours)
    vwc_arr = np.zeros(tot_hours)

    # 3. 初始状态
    current_vwc = hourly_cfgs[0]['init_vwc']
    is_raining = False
    current_rain = 0.0
    current_temp = hourly_cfgs[0]['base_temp']
    current_solar = 0.0
    current_rh = 60.0
    current_cloud = 0.1

    # 4. 本地参数快捷引用（避免长名）
    alpha_temp = MEMORY["alpha_temp"]
    alpha_solar = MEMORY["alpha_solar"]
    alpha_rh = MEMORY["alpha_rh"]
    alpha_cloud = MEMORY["alpha_cloud"]

    # 慢周期参数
    slow_period = SLOW_CYCLE["period_hours"]
    slow_amp_temp = SLOW_CYCLE["amp_temp"]
    slow_amp_solar = SLOW_CYCLE["amp_solar"]
    slow_amp_rh = SLOW_CYCLE["amp_rh"]

    # 降雨模型参数
    rain_params = {
        "base_stop_prob": RAIN_MODEL["base_stop_prob"],
        "start_scale": RAIN_MODEL["start_scale"],
        "gamma_shape": RAIN_MODEL["gamma_shape"]
    }
    runoff_scale = RAIN_MODEL["runoff_scale"]
    max_runoff_frac = RAIN_MODEL["max_runoff_frac"]

    # 5. 时序循环
    for i in range(tot_hours):
        cfg = hourly_cfgs[i]
        hour_of_day = i % 24

        # A. 降雨（马尔可夫）
        is_raining, current_rain = rain_markov_step(is_raining, current_rain, cfg, rain_params)
        rain_arr[i] = round(current_rain, 2)

        # B. 背景日变化 + 慢周期
        diurnal_t = diurnal_temp(hour_of_day, cfg["temp_swing"])
        slow_t = slow_cycle_component(i, slow_period, slow_amp_temp)
        base_t = cfg["base_temp"] + diurnal_t + slow_t

        slow_s = slow_cycle_component(i, slow_period, slow_amp_solar)
        base_solar = solar_target_from_angle(hour_of_day, slow_s)

        slow_rh = slow_cycle_component(i, slow_period, slow_amp_rh)
        base_rh_from_temp = 85.0 - 2.5 * (base_t - 15.0)
        base_rh = base_rh_from_temp + slow_rh

        # C. 云量
        current_cloud = update_cloud(current_cloud, current_rain, alpha_cloud)
        S_target = apply_cloud_mask(base_solar, current_cloud)

        # D. 湿度 & 温度 目标耦合（雨会显著提高 RH 并冷却温度）
        if current_rain > 0.1:
            RH_target = float(np.clip(np.random.uniform(90, 100), 90, 100))
            cooling = 2.0 + min(3.0, current_rain / max(0.1, cfg['rain_intensity'] + 1e-6) * 2.0)
            T_target = base_t - cooling
        else:
            T_target = base_t + np.random.normal(0, 0.3)  # 小噪声
            if current_vwc > SOIL["VWC_FC"]:
                soil_effect = 0.05 * (current_vwc - SOIL["VWC_FC"])
            else:
                soil_effect = 0.02 * (current_vwc - SOIL["VWC_FC"])
            RH_target = float(np.clip(base_rh + soil_effect, 5.0, 99.0))

        # E. AR(1) 更新：温度/光照/湿度 滞后于目标
        current_temp = update_AR1(current_temp, T_target, alpha_temp, noise_std=0.2)
        # 光照白天才有效，夜间强制为0
        current_solar = update_AR1(current_solar, S_target, alpha_solar, noise_std=4.0)
        if not (6 <= hour_of_day <= 18):
            current_solar = 0.0
        current_solar = max(0.0, current_solar)
        current_rh = float(np.clip(update_AR1(current_rh, RH_target, alpha_rh, noise_std=1.0), 5.0, 100.0))

        temp_arr[i] = round(current_temp, 1)
        solar_arr[i] = round(current_solar, 0)
        rh_arr[i] = round(current_rh, 1)

        # F. 土壤水分（入渗 + 蒸散）
        inflow = infiltration_from_rain(rain_arr[i], current_rain, INFILTRATION["base_rate"], runoff_scale, max_runoff_frac)
        current_et = compute_et(current_solar, current_temp, ET["day"], ET["night"])
        # 干旱胁迫：土壤过干会降低 ET（线性介于 0.05..1.0）
        stress = np.clip((current_vwc - SOIL["VWC_WILT"]) / (SOIL["VWC_FC"] - SOIL["VWC_WILT"]), 0.05, 1.0)
        current_et = current_et * stress

        current_vwc = np.clip(current_vwc + inflow - current_et, 0.0, SOIL["VWC_SAT"])
        vwc_arr[i] = round(current_vwc, 2)

    # 返回 DataFrame
    df = pd.DataFrame({
        "timestamp": dates,
        "scene_tag": scene_tags,
        "air_temp": temp_arr,
        "humidity": rh_arr,
        "rainfall": rain_arr,
        "solar_rad": solar_arr,
        "soil_vwc": vwc_arr
    })
    return df

# -------------------- 保存/绘图/CLI --------------------

def save_results(df, out_dir: Path, filename="data"):
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"{filename}.json"
    csv_path = out_dir / f"{filename}.csv"

    df_copy = df.copy()
    df_copy['timestamp'] = df_copy['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(df_copy.to_dict(orient='records'), f, ensure_ascii=False, indent=2)
    df.to_csv(csv_path, index=False)
    return json_path, csv_path

def main(argv=None):
    parser = argparse.ArgumentParser(description="生成伪气象与土壤水分时间序列（小时）")
    parser.add_argument("--story", nargs="+", help="剧情：scene_name days ...，例如 normal_spring 2 rainy_season 3", default=None)
    parser.add_argument("--start", type=str, default="2025-05-01")
    parser.add_argument("--out", type=str, default=str(OUTPUT["out_dir"]))
    parser.add_argument("--plots", type=str, default=str(OUTPUT["plots_dir"]))
    parser.add_argument("--name", type=str, default="data")
    args = parser.parse_args(argv)

    # 解析剧情参数（支持 --story scene days ... 或用默认剧情）
    if args.story:
        it = iter(args.story)
        storyline = []
        for scene in it:
            try:
                days = float(next(it))
            except StopIteration:
                raise ValueError("story 参数需成对出现：scene days")
            storyline.append((scene, days))
    else:
        storyline = DEFAULT_STORYLINE

    # RNG
    np.random.seed(RNG.get("seed", 2026))

    # 生成
    df = generate_integrated_series(storyline, start_date=args.start)

    # 输出目录
    out_dir = Path(args.out)
    plots_dir = Path(args.plots)

    # 保存数据
    json_path, csv_path = save_results(df, out_dir, filename=args.name)

    # 绘图（使用独立模块）
    plot_cfg = dict(PLOT_SETTINGS)
    # 补充土壤阈值到绘图设置，方便注线
    plot_cfg['soil_sat'] = SOIL["VWC_SAT"]
    plot_cfg['soil_fc'] = SOIL["VWC_FC"]
    plot_cfg['soil_ref'] = SOIL["VWC_REF"]
    pdf_path, png_path = plot_sequence(df, Path(plots_dir), filename=args.name, settings=plot_cfg)

    print(f"保存：{json_path}, {csv_path}")
    print(f"绘图：{pdf_path}, {png_path}")

if __name__ == "__main__":
    main()
