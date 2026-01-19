# 果农助手 - 智能农业咨询系统

基于传感器数据和AI大模型的智能农业决策支持系统，专为果农提供实时的田间管理建议。

## 🌟 主要功能

- **智能问答**: 基于传感器数据提供浇水、施肥、病虫害防治等农业建议
- **实时数据分析**: 集成温度、湿度、降雨、土壤水分等多维度传感器数据
- **AI驱动**: 采用DeepSeek/OpenAI大模型进行专业农业分析
- **Web界面**: 简洁易用的前端界面，支持移动端访问
- **离线模式**: 内置启发式算法，无API密钥时也能提供基础建议

## 🚀 快速开始

### 环境要求

- Python 3.8+
- pip 或 conda

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd FG-LLM-project
```

2. **创建虚拟环境**
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或
.venv\Scripts\activate     # Windows
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，添加你的API密钥
```

环境变量配置：
```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATA_FILE_PATH=output/pseudo_data/test.json
```

5. **启动服务**
```bash
python src/main.py
```

6. **访问应用**
打开浏览器访问 `http://localhost:3000`

## 📁 项目结构

```
FG-LLM-project/
├── src/                    # 源代码目录
│   ├── app.py             # FastAPI主应用
│   ├── main.py            # 程序入口
│   ├── config.py          # 配置管理
│   ├── llm_service.py     # AI服务模块
│   ├── data_loader.py     # 数据加载处理
│   └── downloader.py      # 传感器数据下载
├── static/                 # 前端静态文件
│   ├── index.html         # 主页面
│   └── style.css          # 样式文件
├── output/                 # 数据输出目录
├── test/                   # 测试文件
├── requirements.txt        # Python依赖
├── .env                   # 环境变量配置
└── README.md              # 项目说明
```

## 🔧 核心模块

### 数据处理 (data_loader.py)
- 支持JSON格式传感器数据加载
- 时间窗口数据提取（前后24小时）
- 数据清洗和格式化
- 紧凑CSV输出，优化token使用

### AI服务 (llm_service.py)
- DeepSeek/OpenAI API集成
- 智能prompt构建
- 离线mock响应机制
- 专业的农业建议生成

### Web应用 (app.py)
- FastAPI后端服务
- RESTful API接口
- 静态文件服务
- CORS跨域支持

## 📊 数据格式

传感器数据应包含以下字段：
```json
{
  "data": [
    {
      "timestamp": "2025-01-18 15:00:00",
      "temp": 25.5,
      "humidity": 70.2,
      "rain": 0.0,
      "solar": 450.0,
      "soil_water": 35.8
    }
  ]
}
```

字段说明：
- `timestamp`: 时间戳
- `temp`: 温度 (°C)
- `humidity`: 湿度 (%)
- `rain`: 降雨量 (mm)
- `solar`: 太阳辐射 (W/m²)
- `soil_water`: 土壤含水率 (%)

## 🤖 AI建议系统

系统基于以下原则提供农业建议：

1. **数据驱动**: 优先使用传感器数据进行分析
2. **经验补充**: 数据不足时提供基于经验的建议
3. **紧急预警**: 检测极端条件并给出紧急处理建议
4. **趋势分析**: 关注数据变化趋势，提前预警风险

### 紧急情况检测
- 土壤过湿 (VWC ≥ 45%)
- 土壤过干 (VWC ≤ 15%)
- 高温风险 (≥ 38°C)
- 强降雨预警

## 🛠️ API接口

### POST /chat
接收用户问题并返回AI建议

**请求体:**
```json
{
  "message": "我的果树要不要浇水？",
  "reference_time": "2025-01-18 15:00:00",
  "include_forecast": true
}
```

**响应:**
```json
{
  "response": "浇水：不要\n\n- 先别浇, 检查并疏通排水沟。\n- 若有积水, 24小时内排干。\n- 6小时后再测土壤含水。"
}
```

### GET /status
检查系统状态和数据文件可用性

## 🧪 测试

运行测试：
```bash
python -m pytest test/
```

或使用内置的数据加载测试：
```bash
python src/data_loader.py
```

## 🔒 安全注意事项

- API密钥请通过环境变量配置，不要硬编码在代码中
- 生产环境请使用HTTPS协议
- 定期更新依赖包，修复安全漏洞

## 🤝 贡献指南

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 🆘 支持

如有问题或建议，请：
1. 查看本文档的常见问题
2. 搜索已有的 Issues
3. 创建新的 Issue 描述问题

## 🌾 致谢

感谢所有为农业智能化发展做出贡献的开发者和农业专家。

---

**果农助手** - 让科技助力农业，让AI服务果农 🍎