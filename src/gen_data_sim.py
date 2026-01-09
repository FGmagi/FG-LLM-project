#!/usr/bin/env python3
"""
gen_sim_optimized.py

针对猕猴桃（湖南气候）优化的轻量级农业数据生成器。
特点：
1. 使用“水桶模型”模拟土壤水分，物理意义明确。
2. 强耦合气象参数（降雨直接压制光照和温度）。
3. 简化场景配置，专注生成 LLM 易于识别的特征。
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- 全局配置 ----------
OUT_DIR = "scenarios_opt"
PLOTS_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)
np.random.seed(2025)

# ---------- 猕猴桃生长的物理常数 (针对壤土/粘壤土) ----------
# 土壤含水率 (Volumetric Water Content, %)
VWC_SAT = 45.0   # 饱和含水量 (烂根风险)
VWC_FC  = 32.0   # 田间持水量 (最佳上限)
VWC_REF = 20.0   # 灌溉警戒线 (开始受旱)
VWC_WILT= 12.0   # 凋萎系数 (树死)

# 蒸腾系数 (每小时水分下降速率 %/h)
ET_RATE_DAY = 0.15   # 白天强光下蒸发快
ET_RATE_NIGHT = 0.02 # 晚上蒸发极慢

# 降雨入渗系数 (多少雨水能变成土壤水，其余流失)
INFILTRATION_RATE = 0.6 

# ---------- 场景定义 ----------
# 这是一个“配置表”，想要什么场景改这里即可
SCENARIOS = {
    "normal_spring": { 
        "desc": "春季正常生长，偶尔小雨",
        "base_temp": 18, "temp_swing": 8,  # 14~26度
        "rain_prob": 0.1, "rain_intensity": 2.0, # 偶尔小雨
        "init_vwc": 28.0
    },
    "summer_heatwave": {
        "desc": "夏季持续高温热害，极度干旱",
        "base_temp": 30, "temp_swing": 10, # 25~40度 (危险!)
        "rain_prob": 0.0, "rain_intensity": 0.0,
        "init_vwc": 22.0 # 初始水分一般，随后迅速下降
    },
    "rainy_season_flood": {
        "desc": "梅雨季节，连续阴雨，渍水烂根风险",
        "base_temp": 22, "temp_swing": 4,  # 温差小
        "rain_prob": 0.6, "rain_intensity": 8.0, # 经常中大雨
        "init_vwc": 38.0
    },
    "sudden_cooling": {
        "desc": "倒春寒，气温骤降",
        "base_temp": 8, "temp_swing": 6, 
        "rain_prob": 0.2, "rain_intensity": 3.0,
        "init_vwc": 30.0
    }
}

def generate_series(scene_key, days=7):
    """核心生成逻辑"""
    cfg = SCENARIOS[scene_key]
    hours = days * 24
    dates = pd.date_range(start="2025-05-01", periods=hours, freq="h")
    
    # 1. 初始化数组
    temp = np.zeros(hours)
    rain = np.zeros(hours)
    solar = np.zeros(hours)
    rh = np.zeros(hours)
    vwc = np.zeros(hours)
    
    # 初始状态
    current_vwc = cfg['init_vwc']
    is_raining = False # 降雨状态机
    
    for i in range(hours):
        hour_of_day = i % 24
        
        # --- A. 降雨生成 (马尔可夫链: 昨天下了，今天大概率继续) ---
        # 基础概率来自于配置
        p_rain = cfg['rain_prob']
        
        # 如果上个小时在下雨，这个小时继续下的概率增加
        if is_raining:
            p_curr = 0.7 
        else:
            p_curr = p_rain * 0.3 # 起雨比较难，但一旦开始容易持续
            
        if np.random.rand() < p_curr:
            is_raining = True
            # 生成降雨量 (Gamma分布模拟忽大忽小)
            rain_amount = np.random.gamma(shape=2.0, scale=cfg['rain_intensity']/2.0)
        else:
            is_raining = False
            rain_amount = 0.0
        
        rain[i] = round(rain_amount, 2)
        
        # --- B. 基础气象 (温度 & 光照) ---
        # 理想状态下的正弦波
        # 14:00 最热，02:00 最冷
        diurnal_factor = np.sin(2 * np.pi * (hour_of_day - 8) / 24) 
        base_t = cfg['base_temp'] + diurnal_factor * (cfg['temp_swing'] / 2)
        
        # 理想光照 (只在 6:00 - 18:00 有)
        if 6 <= hour_of_day <= 18:
            base_solar = 800 * np.sin(np.pi * (hour_of_day - 6) / 12)
        else:
            base_solar = 0.0

        # --- C. 物理耦合修正 ---
        if rain[i] > 0.1:
            # 下雨时：降温、无光、高湿
            temp[i] = base_t - 2.0 # 雨冷
            solar[i] = base_solar * 0.1 # 乌云遮蔽
            rh[i] = np.random.uniform(90, 100) # 极湿
        else:
            # 没下雨：可能有云
            cloud_cover = np.random.uniform(0, 0.3) # 随机云
            temp[i] = base_t + np.random.normal(0, 0.5)
            solar[i] = base_solar * (1 - cloud_cover)
            
            # 湿度与温度反相关 (Clausius-Clapeyron近似逻辑)
            # 温度越高，相对湿度通常越低
            base_rh = 85 - 2.5 * (temp[i] - 15) 
            rh[i] = np.clip(base_rh + np.random.normal(0, 3), 30, 95)

        # 修正边界
        solar[i] = max(0, solar[i])
        
        # --- D. 土壤水分 (水桶模型) ---
        # 1. 收入：降雨 * 入渗率
        inflow = rain[i] * INFILTRATION_RATE
        
        # 2. 支出：蒸腾 (与光照和温度正相关)
        # 光照越强，蒸发越快；土壤越干，蒸发越慢(变难)
        stress_factor = (current_vwc - VWC_WILT) / (VWC_FC - VWC_WILT)
        stress_factor = np.clip(stress_factor, 0.1, 1.0)
        
        current_et = (ET_RATE_DAY if solar[i] > 100 else ET_RATE_NIGHT) * stress_factor
        
        # 3. 结算
        current_vwc = current_vwc + inflow - current_et
        
        # 4. 物理边界 (不能超过饱和，不能低于0)
        # 如果超过饱和，多余的水变成“径流”流走了，或者逐渐排掉
        if current_vwc > VWC_SAT:
            current_vwc = VWC_SAT # 假设排水良好，不会无限积水
        
        vwc[i] = round(current_vwc, 2)
    
    # 构建 DataFrame
    df = pd.DataFrame({
        "timestamp": dates,
        "scene": scene_key,
        "air_temp": np.round(temp, 1),
        "humidity": np.round(rh, 1),
        "rainfall": np.round(rain, 1),
        "solar_rad": np.round(solar, 0),
        "soil_vwc": np.round(vwc, 1)
    })
    return df

# ---------- 辅助函数：保存与绘图 ----------
def save_and_plot(df, scene_name):
    # 保存 JSON
    json_path = os.path.join(OUT_DIR, f"{scene_name}.json")
    # 转换时间格式
    out_df = df.copy()
    out_df['timestamp'] = out_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    data_dict = {
        "meta": SCENARIOS[scene_name],
        "data": out_df.to_dict(orient="records")
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data_dict, f, ensure_ascii=False, indent=2)
    
    # 绘图
    fig, axes = plt.subplots(4, 1, figsize=(10, 12), sharex=True)
    
    # 1. 温度与湿度
    ax0 = axes[0]
    ax0.plot(df['timestamp'], df['air_temp'], color='tab:red', label='Temp (°C)')
    ax0.set_ylabel('Temp')
    ax0b = ax0.twinx()
    ax0b.plot(df['timestamp'], df['humidity'], color='tab:blue', alpha=0.5, label='Humidity (%)')
    ax0b.set_ylabel('RH %')
    ax0.set_title(f"Scenario: {scene_name} - Temp & Humidity")
    
    # 2. 降雨
    ax1 = axes[1]
    ax1.bar(df['timestamp'], df['rainfall'], color='tab:cyan', label='Rain (mm)')
    ax1.set_ylabel('Rain (mm)')
    ax1.legend(loc='upper left')
    
    # 3. 土壤水分 (关键)
    ax2 = axes[2]
    ax2.plot(df['timestamp'], df['soil_vwc'], color='tab:brown', linewidth=2)
    # 画几条参考线
    ax2.axhline(y=VWC_SAT, color='r', linestyle='--', alpha=0.5, label='Saturation')
    ax2.axhline(y=VWC_FC, color='g', linestyle='--', alpha=0.5, label='Field Capacity')
    ax2.axhline(y=VWC_REF, color='orange', linestyle='--', alpha=0.5, label='Stress Onset')
    ax2.set_ylabel('Soil VWC (%)')
    ax2.legend()
    
    # 4. 光照
    ax3 = axes[3]
    ax3.plot(df['timestamp'], df['solar_rad'], color='tab:orange', alpha=0.8)
    ax3.set_ylabel('Solar (W/m²)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(PLOTS_DIR, f"{scene_name}.png"))
    plt.close()
    print(f"Generated {scene_name}")

# ---------- 主程序 ----------
if __name__ == "__main__":
    for scene in SCENARIOS.keys():
        df = generate_series(scene, days=5)
        save_and_plot(df, scene)
    print("All done.")