# 伪数据生成器

用于生成小时级气象/土壤水分序列，给后端与 LLM 进行本地测试。

## 快速使用

在项目根目录执行：

```bash
python -m test.gen_data
```

自定义情景与起始日期：

```bash
python -m test.gen_data --story rainy_season 3 normal_spring 2 --start 2025-01-10
```

## 输出文件

默认输出到 `output/pseudo_data/`：
- `{TAG}.json`：JSON 观测序列
- `{TAG}.csv`：CSV 观测序列
- `plots/{TAG}.pdf`、`plots/{TAG}.png`：时序图

`TAG` 与路径等配置见 `test/gen_data_config.py`。

## 主要变量

- `temp`：气温（°C）
- `humidity`：相对湿度（%）
- `rain`：小时降雨量（mm/h）
- `solar`：太阳辐射（W/m²）
- `soil_water`：土壤体积含水量（%）

## 模型简述（物理近似）

- 温度：日周期 + 慢周期 + AR(1) 平滑
- 光照：白天日周期 + 云遮蔽
- 降雨：马尔可夫过程决定有无雨，雨强用 Gamma 分布采样
- 土壤水分：入渗 + 蒸散的桶模型（含干旱胁迫）

## 场景配置

在 `test/gen_data_config.py` 中调整：
- `SCENARIOS`：场景参数
- `DEFAULT_STORYLINE`：默认剧情
- `SOIL/ET/RAIN_MODEL/MEMORY`：物理与统计参数
