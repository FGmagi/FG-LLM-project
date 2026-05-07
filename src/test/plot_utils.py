# plot_utils.py
"""
独立的绘图模块。提供美观且可复用的绘图函数。
"""

from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def plot_sequence(df: pd.DataFrame, pdf_path: Path, png_path: Path, settings: dict = None):
    """
    保存并绘制 4 面板图：温度/湿度、降雨、土壤含水、光照。
    参数:
      df: 带 timestamp 列的 DataFrame
      pdf_path: 完整输出 PDF 路径
      png_path: 完整输出 PNG 路径
      settings: 来自 gen_data_config.PLOT_SETTINGS（可为空）
    """
    if settings is None:
        settings = {}

    figsize = settings.get("figsize", (12, 14))
    dpi = settings.get("dpi", 150)
    palette = settings.get("palette", {})

    fig, axes = plt.subplots(4, 1, figsize=figsize, sharex=True, dpi=dpi)

    # 1. 温度与湿度（双Y）
    ax0 = axes[0]
    ax0.plot(df['timestamp'], df['temp'], label='Temp (°C)', linewidth=1.2, color=palette.get("temp", None))
    ax0.set_ylabel('Air Temp (°C)')
    ax0b = ax0.twinx()
    ax0b.plot(df['timestamp'], df['humidity'], label='RH (%)', linewidth=1.0, linestyle='--', color=palette.get("humidity", None))
    ax0b.set_ylabel('Humidity (%)')
    ax0.set_title("1. Temperature & Relative Humidity")
    ax0.grid(alpha=0.15)

    # 2. 降雨（柱状）
    ax1 = axes[1]
    ax1.bar(df['timestamp'], df['rain'], width=0.03, label='Rainfall (mm)', color=palette.get("rain", None))
    ax1.set_ylabel('Rain (mm/h)')
    ax1.set_title("2. Precipitation")
    ax1.grid(alpha=0.15)

    # 3. 土壤含水
    ax2 = axes[2]
    ax2.plot(df['timestamp'], df['soil_water'], label='Soil VWC (%)', linewidth=1.5, color=palette.get("soil_water", None))
    ax2.axhline(y=settings.get("soil_sat", 45.0), color='r', linestyle='--', alpha=0.6, label='Saturation')
    ax2.axhline(y=settings.get("soil_fc", 32.0), color='g', linestyle='--', alpha=0.6, label='Field capacity')
    ax2.axhline(y=settings.get("soil_ref", 20.0), color='orange', linestyle='--', alpha=0.6, label='Irrigation ref')
    ax2.set_ylabel('Soil VWC (%)')
    ax2.set_ylim(0, 50)
    ax2.legend(loc='lower left', fontsize='small')
    ax2.set_title("3. Soil Water Content (Bucket)")

    # 4. 光照
    ax3 = axes[3]
    ax3.plot(df['timestamp'], df['solar'], label='Solar (W/m2)', linewidth=1.2, color=palette.get("solar", None))
    ax3.set_ylabel('Solar (W/m²)')
    ax3.set_title("4. Solar Radiation")
    ax3.grid(alpha=0.15)

    # 场景分割标注（按 scene_tag 改变处画竖线）
    if 'scene_tag' in df.columns:
        changes = df['scene_tag'].ne(df['scene_tag'].shift()).cumsum()
        for change_idx in df.groupby(changes).head(1).index[1:]:
            t_point = df.loc[change_idx, 'timestamp']
            for ax in axes:
                ax.axvline(x=t_point, color='black', linestyle=':', alpha=0.5)
                if ax is ax0:
                    ax.text(t_point, ax.get_ylim()[1]*0.95, f"{df.loc[change_idx, 'scene_tag']}", rotation=0,
                            verticalalignment='top', fontsize=9, fontweight='bold')

    plt.tight_layout()

    # 统一输出 PDF/PNG
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(pdf_path)
    fig.savefig(png_path)
    plt.close(fig)
    return pdf_path, png_path
