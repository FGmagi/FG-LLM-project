#!/usr/bin/env python3
"""
融合版（改进）：
对温度、光照、湿度增加慢周期与随机性，并与降雨耦合同时保留时间记忆（AR(1)）。
改善点：
 - 温度/光照/湿度包含两层动力：快的日变化（diurnal） + 慢的多日周期（slow_cycle）
 - 引入 cloud（云量）记忆，cloud 控制光照削弱，且在降雨时快速上升
 - 降雨入渗考虑强度相关的径流（大雨入渗比例下降），防止暴雨导致土壤 VWC 过度瞬时飙升
 - 蒸腾率 ET 受光照和温度共同调节，使土壤对温度更敏感
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# ---------- 1. 全局配置 ----------
OUT_DIR = "output/psudo_data"
PLOTS_DIR = os.path.join(OUT_DIR, "plots")
os.makedirs(PLOTS_DIR, exist_ok=True)
np.random.seed(2026)

# ---------- 2. 猕猴桃生长的物理常数 (针对壤土/粘壤土) ----------
VWC_SAT = 45.0   # 饱和含水量 (%) - 超过此值会积水烂根
VWC_FC  = 32.0   # 田间持水量 (%) - 最佳含水量上限
VWC_REF = 20.0   # 灌溉警戒线 (%) - 建议开始灌溉
VWC_WILT= 12.0   # 凋萎系数 (%)   - 植株永久受损死亡线

ET_RATE_DAY       = 0.15 # 白天基准蒸散率 (%/h)
ET_RATE_NIGHT     = 0.02 # 夜间蒸散率 (%/h)
INFILTRATION_RATE = 0.20 # 降雨入渗系数基准 (fraction)

# ---------- 3. 场景模板定义 ----------
SCENARIOS = {
    "normal_spring": {
        "desc": "春季正常生长，偶尔小雨",
        "base_temp": 18, "temp_swing": 8,
        "rain_prob": 0.2, "rain_intensity": 2.0,
        "init_vwc": 28.0
    },
    "summer_heatwave": {
        "desc": "夏季持续高温热害，极度干旱",
        "base_temp": 35, "temp_swing": 10, # 极端高温
        "rain_prob": 0.0, "rain_intensity": 0.0,
        "init_vwc": 20.0
    },
    "rainy_season_flood": {
        "desc": "梅雨季节，连续阴雨，渍水烂根风险",
        "base_temp": 22, "temp_swing": 4,
        "rain_prob": 0.6, "rain_intensity": 5.0,
        "init_vwc": 38.0
    },
    "sudden_cooling": {
        "desc": "倒春寒，气温骤降",
        "base_temp": 8, "temp_swing": 6,
        "rain_prob": 0.2, "rain_intensity": 3.0,
        "init_vwc": 30.0
    }
}

# ---------- 4. 核心生成逻辑：连续时间轴生成器 ----------
def generate_integrated_series(timeline_config, start_date="2025-05-01"):
    """
    timeline_config: 场景序列列表，例如 [("normal_spring", 3), ("summer_heatwave", 5)]
    返回：按小时的 DataFrame，包含 timestamp, scene_tag, air_temp, humidity, rainfall, solar_rad, soil_vwc

    设计说明（要点）：
      - 温度、光照、湿度使用 AR(1) 平滑（current_*），目标值由：日变化(diurnal) + 慢周期(slow) + 降雨耦合 + 随机扰动 组成;
      - 光照严格仅在 06-18 点非零，由 cloud(有记忆) 和日照角度共同决定；
      - 降雨使用带惯性的马尔可夫链决定是否下雨，并用 Gamma 采样事件强度；对小时强度做平滑；
      - 入渗考虑强度相关的径流（大雨时入渗比例下降），ET 同时依赖光照与温度；
    """
    hourly_configs = []
    scene_tags = []

    # 步骤 1: 展开时间轴配置
    for scene_key, days in timeline_config:
        if scene_key not in SCENARIOS:
            raise ValueError(f"未知场景: {scene_key}")
        hours = int(days * 24)
        hourly_configs.extend([SCENARIOS[scene_key]] * hours)
        scene_tags.extend([scene_key] * hours)

    tot_hours = len(hourly_configs)
    dates = pd.date_range(start=start_date, periods=tot_hours, freq="h")

    # 初始化输出缓冲区
    temp = np.zeros(tot_hours)
    rain = np.zeros(tot_hours)
    solar = np.zeros(tot_hours)
    rh = np.zeros(tot_hours)
    vwc = np.zeros(tot_hours)

    # 初始慢变量：土壤含水量（继承第一个场景）
    current_vwc = hourly_configs[0]['init_vwc']

    # 降雨状态与强度（带记忆）
    is_raining = False
    current_rain = 0.0

    # 气象量的记忆变量（AR(1) 初始）
    current_temp = hourly_configs[0]['base_temp']
    current_solar = 0.0
    current_rh = 60.0  # 初始相对湿度

    # 云量（cloud）记忆：0..1，影响光照（cloud 越大，solar 被削弱越多）
    current_cloud = 0.1

    # 平滑系数（0..1），越接近1记忆越强
    alpha_temp = 0.88   # 温度记忆（较强，但允许慢周期与扰动）
    alpha_solar = 0.82  # 光照记忆
    alpha_rh = 0.78     # 湿度记忆
    alpha_cloud = 0.75  # 云量记忆（cloud 随降雨快速上升，晴时缓慢衰减）

    # 降雨马尔可夫参数（可调）
    base_p_stop = 0.05  # 已下雨时停止的基础概率

    # 慢周期参数（单位：小时），示例使用 14 天周期（14*24 小时）
    slow_period_hours = 14 * 24
    slow_amp_temp = 1.5   # 慢周期对温度的振幅（°C）
    slow_amp_solar = 150  # 慢周期对日间最大光照的影响（W/m2）
    slow_amp_rh = 3.0     # 慢周期对湿度基线的影响（%）

    # 循环逐小时演化
    for i in range(tot_hours):
        cfg = hourly_configs[i]
        hour_of_day = i % 24
        day_index = i // 24

        # ---------- A. 降雨：带惯性的马尔可夫链 + 事件强度 ----------
        p_rain = cfg['rain_prob']
        p_start = p_rain * 0.1  # 不下雨时开始的概率（与场景 rain_prob 成比例）
        p_stop  = base_p_stop    # 已下雨时停止概率（可适当调小以延长雨持续）

        if is_raining:
            # 在下雨：小概率停止，否则继续并平滑雨强
            if np.random.rand() < p_stop:
                is_raining = False
                # 停雨：current_rain 归零（或可设为逐步衰减）
                current_rain = 0.0
                rain[i] = 0.0
            else:
                is_raining = True
                # 事件级目标强度（Gamma），scale 根据场景 rain_intensity
                target_rain = np.random.gamma(shape=2, scale=cfg['rain_intensity']/2)
                # 小时平滑：AR(1) 让小时雨强缓慢变化
                current_rain = 0.7 * current_rain + 0.3 * target_rain if current_rain > 0 else target_rain
                rain[i] = round(current_rain, 2)
        else:
            # 不下雨：小概率启动新事件
            if np.random.rand() < p_start:
                is_raining = True
                current_rain = np.random.gamma(shape=2, scale=cfg['rain_intensity']/2)
                rain[i] = round(current_rain, 2)
            else:
                is_raining = False
                rain[i] = 0.0

        # ---------- B. 理想背景天气（快速日变化 + 慢周期） ----------
        # 快日变化（昼夜正弦，温度在 14 点附近略滞后）
        diurnal_factor = np.sin(2 * np.pi * (hour_of_day - 8) / 24)  # 峰值在 ~14点
        diurnal_temp = diurnal_factor * (cfg['temp_swing'] / 2)

        # 慢周期（例如 14 天）引入温度 / 光照 / 湿度的缓慢起伏，增加随机性
        slow_cycle = np.sin(2 * np.pi * (i / slow_period_hours))
        slow_temp = slow_amp_temp * slow_cycle
        slow_solar = slow_amp_solar * slow_cycle
        slow_rh = slow_amp_rh * slow_cycle

        # 基线温度由场景 base_temp + 日变化 + 慢周期组成（还会有小噪声）
        base_t = cfg['base_temp'] + diurnal_temp + slow_temp
        # 基线光照（日间）由正弦刻画 + 慢周期放大，光照严格仅在 6-18 点产生
        if 6 <= hour_of_day <= 18:
            base_solar_day = max(0.0, 800 * np.sin(np.pi * (hour_of_day - 6) / 12))  # 0..800
            base_solar = base_solar_day + slow_solar  # 加上慢周期分量（可为正或负）
            base_solar = max(0.0, base_solar)
        else:
            base_solar = 0.0

        # 基线湿度（由温度给出一个基线，再加慢周期与场景影响）
        base_rh_from_temp = 85 - 2.5 * (base_t - 15)  # 工程化线性近似
        base_rh = base_rh_from_temp + slow_rh

        # ---------- C. 云量（cloud）记忆：云量影响光照并与降雨耦合 ----------
        # 如果在下雨，云量迅速升高；若不下雨，云量逐步衰减回晴值
        # cloud 范围 [0, 1]
        # 当下雨时，cloud_target 接近 0.9；不下雨时 cloud_target 由随机云扰动决定（0..0.4）
        if rain[i] > 0.1:
            cloud_target = 0.85 + np.random.uniform(-0.05, 0.05)  # 雨时高云量
        else:
            # 晴时云量受场景与随机性影响
            cloud_base = 0.05  # 基线晴
            cloud_random = np.random.uniform(0.0, 0.35)
            cloud_target = np.clip(cloud_base + cloud_random, 0.0, 0.6)

        # cloud 使用 AR(1) 平滑，保证云量不会瞬间跳变
        current_cloud = alpha_cloud * current_cloud + (1.0 - alpha_cloud) * cloud_target
        current_cloud = float(np.clip(current_cloud, 0.0, 0.99))

        # 光照目标受 cloud 因素强烈抑制（cloud 越大，光照越弱）
        # 采用 (1 - cloud^p) 型非线性削弱，以便 cloud 接近 1 时几乎没光
        cloud_power = 1.5
        S_target = base_solar * max(0.0, (1.0 - current_cloud**cloud_power))

        # ---------- D. 湿度与温度目标的耦合 ----------
        # 如果在下雨，RH_target 高（90-100）；否则 RH_target 由温度、土壤湿度和慢周期共同决定
        if rain[i] > 0.1:
            RH_target = float(np.clip(np.random.uniform(90, 100), 90, 100))
            # 同时雨会对温度有冷却效应，冷却幅度随雨强略增
            cooling = 2.0 + min(3.0, current_rain / max(0.1, cfg['rain_intensity'] + 1e-6) * 2.0)
            T_target = base_t - cooling
        else:
            # 无雨时的 T_target 主要是基线 plus 小扰动（这里不强制依赖雨）
            # 给温度加入小随机扰动项，且允许慢周期继续影响
            T_target = base_t + np.random.normal(0, 0.3)
            # 湿度目标：基于温度的基线加上土壤湿度的弱耦合（湿土会提高局地 RH）
            # 我们让 soil_effect 随 current_vwc 非线性增加（超过 FC 时更明显）
            if current_vwc > VWC_FC:
                soil_effect = 0.05 * (current_vwc - VWC_FC)  # 每超 1% VWC 增加 0.05 在 RH 基线上的幅度（小量）
            else:
                soil_effect = 0.02 * (current_vwc - VWC_FC)  # 干土时负影响较小（可能降低蒸发）
            # 温度与土壤耦合后的 RH_target（clip 到合理区间）
            RH_target = np.clip(base_rh + soil_effect, 10.0, 99.0)

        # ---------- E. 带记忆更新：AR(1) 平滑，使温度/光照/湿度滞后于目标值 ----------
        # 温度平滑（current_temp 追随 T_target）
        temp_noise = np.random.normal(0, 0.2)
        current_temp = alpha_temp * current_temp + (1.0 - alpha_temp) * T_target + temp_noise

        # 光照平滑（current_solar 追随 S_target），并严格保证夜间为 0
        solar_noise = np.random.normal(0, 4.0)
        current_solar = alpha_solar * current_solar + (1.0 - alpha_solar) * S_target + solar_noise
        # 夜间强制为 0
        if not (6 <= hour_of_day <= 18):
            current_solar = 0.0
        current_solar = max(0.0, current_solar)

        # 湿度平滑（current_rh 追随 RH_target）
        rh_noise = np.random.normal(0, 1.0)
        current_rh = alpha_rh * current_rh + (1.0 - alpha_rh) * RH_target + rh_noise
        current_rh = float(np.clip(current_rh, 5.0, 100.0))

        # 将平滑后的状态写入输出缓冲
        temp[i] = round(current_temp, 1)
        solar[i] = round(current_solar, 0)
        rh[i] = round(current_rh, 1)

        # ---------- F. 土壤水分积分 (水桶模型 - 改进入渗与 ET 模型) ----------
        # 入渗：考虑大雨时产生径流，入渗比例随小时雨强降低
        # runoff_factor 随雨强上升，取值 [0, 0.7]
        if rain[i] > 0.0:
            runoff_factor = np.clip(current_rain / (current_rain + 10.0), 0.0, 0.7)
            effective_infiltration = INFILTRATION_RATE * (1.0 - 0.5 * runoff_factor)  # 大雨时入渗减半
            inflow = rain[i] * effective_infiltration
        else:
            inflow = 0.0

        # 蒸腾（ET）现在依赖于光照与温度：白天随光照线性放大，温度高时进一步放大
        # 计算光照对 ET 的缩放（solar_scale 在光照 100 W/m2 时接近 1）
        solar_scale = (current_solar / 200.0) if current_solar > 0 else 0.0
        # 温度放大因子（以 20°C 为参考）
        temp_scale = 1.0 + 0.05 * (current_temp - 20.0)  # 每升 1°C 增加 3% ET
        temp_scale = max(0.5, temp_scale)  # 限制下界

        # 基础 ET（白天/夜间）
        base_et = ET_RATE_DAY if current_solar > 100 else ET_RATE_NIGHT
        current_et = base_et * (0.6 + 0.4 * solar_scale) * temp_scale  # 将光照与温度共同作用到 ET 上

        # 干旱胁迫抑制（干土会降低蒸腾）
        stress_factor = np.clip((current_vwc - VWC_WILT) / (VWC_FC - VWC_WILT), 0.05, 1.0)
        current_et = current_et * stress_factor

        # 更新土壤含水量（积分）
        current_vwc = np.clip(current_vwc + inflow - current_et, 0.0, VWC_SAT)
        vwc[i] = round(current_vwc, 2)

    # 返回 DataFrame
    return pd.DataFrame({
        "timestamp": dates,
        "scene_tag": scene_tags,
        "air_temp": np.round(temp, 1),
        "humidity": np.round(rh, 1),
        "rainfall": np.round(rain, 1),
        "solar_rad": np.round(solar, 0),
        "soil_vwc": np.round(vwc, 1)
    })

# ---------- 5. 辅助函数：保存与 4 面板组合绘图 ----------
def save_and_plot_sequence(df, filename="data"):
    # 保存 JSON 记录
    json_path = os.path.join(OUT_DIR, f"{filename}.json")
    out_df = df.copy()
    out_df['timestamp'] = out_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(out_df.to_dict(orient="records"), f, ensure_ascii=False, indent=2)

    # 组合绘图 (4 面板)
    fig, axes = plt.subplots(4, 1, figsize=(12, 14), sharex=True)

    # 1. 温度与湿度 (双 Y 轴)
    ax0 = axes[0]
    ax0.plot(df['timestamp'], df['air_temp'], color='tab:red', label='Temp (°C)')
    ax0.set_ylabel('Air Temp (°C)', color='tab:red')
    ax0b = ax0.twinx()
    ax0b.plot(df['timestamp'], df['humidity'], color='tab:blue', alpha=0.6, label='RH (%)')
    ax0b.set_ylabel('Humidity (%)', color='tab:blue')
    ax0.set_title("1. Environment: Air Temp & Relative Humidity")

    # 2. 降雨量 (柱状图)
    ax1 = axes[1]
    ax1.bar(df['timestamp'], df['rainfall'], color='tab:cyan', width=0.03, label='Rainfall (mm)')
    ax1.set_ylabel('Rain (mm)')
    ax1.set_title("2. Precipitation Events")

    # 3. 土壤水分 (带关键阈值线)
    ax2 = axes[2]
    ax2.plot(df['timestamp'], df['soil_vwc'], color='tab:brown', linewidth=2.0, label='Soil VWC %')
    ax2.axhline(y=VWC_SAT, color='r', linestyle='--', alpha=0.6, label='Saturation (Flood)')
    ax2.axhline(y=VWC_FC, color='g', linestyle='--', alpha=0.6, label='Field Capacity (Ideal)')
    ax2.axhline(y=VWC_REF, color='orange', linestyle='--', alpha=0.6, label='Irrigation Ref')
    ax2.set_ylabel('Soil VWC (%)')
    ax2.set_ylim(0, 50)
    ax2.legend(loc='lower left', fontsize='small', ncol=2)
    ax2.set_title("3. Soil Water Content (Bucket Model)")

    # 4. 光照强度
    ax3 = axes[3]
    ax3.plot(df['timestamp'], df['solar_rad'], color='tab:orange', alpha=0.9)
    ax3.set_ylabel('Solar (W/m²)')
    ax3.set_title("4. Solar Radiation")

    # 标注场景切换点
    changes = df['scene_tag'].ne(df['scene_tag'].shift()).cumsum()
    for change_idx in df.groupby(changes).head(1).index[1:]:
        t_point = df.loc[change_idx, 'timestamp']
        for ax in axes:
            ax.axvline(x=t_point, color='black', linestyle=':', alpha=0.5)
            if ax == axes[0]:
                ax.text(t_point, ax.get_ylim()[1], f" Switch to: {df.loc[change_idx, 'scene_tag']}",
                        rotation=0, verticalalignment='bottom', fontsize=9, fontweight='bold')

    plt.tight_layout()
    plot_path = os.path.join(PLOTS_DIR, f"{filename}.pdf")
    plt.savefig(plot_path)
    plt.close()
    print(f"Outputs: {json_path} and {plot_path}")

# ---------- 6. 主程序：测试剧情流程 ----------
if __name__ == "__main__":
    # 定义测试剧情：正常 -> 酷暑干旱 -> 暴雨积水 -> 倒春寒
    storyline = [
        ("normal_spring", 3),
        ("summer_heatwave", 10),
        ("rainy_season_flood", 2),
        ("sudden_cooling", 2)
    ]

    print("Start...")
    df_result = generate_integrated_series(storyline)

    save_and_plot_sequence(df_result, filename="data")

    df_result.to_csv(os.path.join(OUT_DIR, "data.csv"), index=False)
