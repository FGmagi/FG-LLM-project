# 伪数据生成器（概要与物理说明）

## 使用方式
- 推荐在项目根目录以模块方式运行：
  ```bash
  python -m test.gen_data
  ```

## 主要变量
- `air_temp`：气温（°C）
- `humidity`：相对湿度（%）
- `rainfall`：小时降雨量（mm/h）
- `solar_rad`：表面光照（W/m²）
- `soil_vwc`：土壤体积含水量（%）

## 关键模型组件与公式说明

### 1. 温度：日变化 + 慢周期 + AR(1)
温度由三部分叠加：
- 日变化（diurnal）：
  $$
  T_{\mathrm{diurnal}}(h)=\frac{\Delta T}{2}\sin\left(\frac{2\pi(h-\phi)}{24}\right)
  $$
  其中 $h$ 为小时，$\Delta T$ 为日摆幅，$\phi$ 为相位偏移（默认 8 小时，峰值约在 14 点）。
- 慢周期：
  $$
  T_{\mathrm{slow}}(t)=A_{\mathrm{slow}}\sin\left(\frac{2\pi t}{P}\right)
  $$
  $P$ 为慢周期（默认 14 天），$A_{\mathrm{slow}}$ 为幅值。
- 温度随时间用 AR(1) 平滑：
  $$
  T_{t+1}=\alpha_T T_t + (1-\alpha_T) T_{\rm target} + \epsilon
  $$
  其中 $\alpha_T$ 为记忆系数，$\epsilon$ 为小幅高斯噪声。

### 2. 光照（solar）
- 白天（6–18 点）由半周期正弦给出最大形状，受慢周期放大/减小：
  $$
  S_{\rm base}(h)=\max\left(0,800\sin\left(\frac{\pi(h-6)}{12}\right)\right)+S_{\rm slow}
  $$
- 云遮蔽采用非线性抑制：
  $$
  S = S_{\rm base}\times(1-\mathrm{cloud}^p)
  $$
- 光照也用 AR(1) 平滑，夜间强制为 0。

### 3. 降雨（马尔可夫过程 + Gamma 强度）
- 是否下雨由带惯性的马尔可夫链决定：
  - 未下雨时以 $p_{\rm start}=p_{\rm scen}\times s$ 启动新事件；
  - 已下雨时以 $p_{\rm stop}$ 停雨。
- 降雨强度（小时尺度）用 Gamma 分布采样，随后做小时平滑（AR 风格）。

### 4. 入渗与径流
- 考虑大雨时发生径流，入渗比例随雨强下降：
  $$
  \text{runoff\_factor}=\mathrm{clip}\left(\frac{\rm rain}{\rm rain+R},0,f_{\max}\right)
  $$
  $$
  \rm infil = \rm rain \times infil_{base}\times \left(1-0.5\times \text{runoff\_factor}\right)
  $$

### 5. 蒸散（ET）
- ET 同时依赖光照和温度：
  $$
  ET = ET_{\rm base}\times\left(0.6+0.4\times\frac{S}{200}\right)\times \mathrm{temp\_scale}
  $$
  其中 $\mathrm{temp\_scale}= \max(0.5, 1+0.05(T-20))$，基于白天/夜间选择不同基线 $ET_{\rm base}$。
- 干旱胁迫用简单线性因子降低 ET：
  $$
  stress = \mathrm{clip}\left(\frac{VWC - V_{wilt}}{V_{fc}-V_{wilt}}, 0.05, 1.0\right)
  $$

### 6. 土壤水分积分（水桶模型）
- 每小时更新：
  $$
  VWC_{t+1} = \mathrm{clip}(VWC_t + infil - ET, 0, VWC_{sat})
  $$
