# FG-LLM Project

基于传感器数据与大语言模型的果园管理咨询系统（FastAPI 后端 + 轻量 Web 前端 + 传感器接口）。系统会把近 24 小时观测与可选的未来 24 小时预测窗口整理为紧凑数据上下文，交给 LLM 生成建议；未配置 API Key 时自动回退到本地启发式规则。

本软件仅限用于学习与研究目的，严禁将本软件用于任何非法或违反相关法律法规的行为。

## 项目结构

```
FG-LLM-project/
├── src/                 # 后端与推理逻辑
│   ├── main.py           # 服务入口
│   ├── app.py            # FastAPI 应用与路由
│   ├── config.py         # 环境配置与提示词读取
│   ├── data_loader.py    # 数据加载/窗口切分/紧凑格式化
│   └── llm_service.py    # LLM 调用与离线回退
│   └── downloader.py	 # 网关数据接口
├── test/                # demo测试数据
│   ├── gen_data.py
│   ├── gen_data_config.py
│   └── plot_utils.py
├── prompts/             # 系统提示词模板
├── static/              # Web 前端
├── output/              # 生成的数据与图表
└── requirements.txt
```

## 安装

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 快速开始

### 1) 使用downloader下载传感器json数据（推荐）

配置账户、密码，启动服务后即可从网关处获取传感器信息。

启动服务后，通过Downloade.logIn()提交账户密码，根据需要选择获取的设备、数据方式。

```
    # 获取设备分组列表
    def getDeviceGroups(self, **kwargs) -> JsonType:...
  
    # 获取某分组下设备列表
    def getDevicesInGroup(self, group_id: str = "", **kwargs) -> JsonType:...
  
    # 获取设备软件参数
    def getDeviceSoftwareParams(self, device_key: str, **kwargs) -> JsonType:...
  
    # 获取历史传感器数据
    def getHistoricalSensorData(self, device_key:str,begin_time:DateTime,end_time:DateTime) -> JsonType:...
```

可使用以下程序获取demo信息以供调试。

```bash
python -m test.gen_data
```

默认生成到 `output/pseudo_data/test.json`（也是默认的数据读取路径）。

### 2) 配置环境变量（可选）

在项目根目录创建 `.env`：

```env
DEEPSEEK_API_KEY=your_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
DATA_FILE_PATH=output/pseudo_data/test.json
PROMPT_FILE_PATH=prompts/system.yaml
```

未提供 `DEEPSEEK_API_KEY` 时将自动走本地启发式规则。

### 3) 启动服务

```bash
python -m src.main
```

访问 `http://localhost:3000` 查看 Web 界面；接口支持：

- `GET /status`：检查数据文件是否存在
- `POST /chat`：提交问题并获取建议

`POST /chat` 请求体：

```json
{
  "message": "我需要给树浇水吗？",
  "reference_time": "2025-01-18 15:00:00",
  "include_forecast": true
}
```

## 数据格式

系统读取 JSON 格式，可为数组或 `{ "data": [...] }`：

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

字段含义：

- `timestamp`：时间戳（`YYYY-MM-DD HH:MM:SS`）
- `temp`：气温（°C）
- `humidity`：相对湿度（%）
- `rain`：降雨量（mm/h）
- `solar`：太阳辐射（W/m²）
- `soil_water`：土壤体积含水量（%）

额外字段如 `scene_tag/label` 会在发送给 LLM 前被移除。

## 配置说明

- `DEEPSEEK_API_KEY`：OpenAI/DeepSeek 兼容 API 的密钥
- `DEEPSEEK_BASE_URL`：API Base URL（默认 `https://api.deepseek.com`）
- `DEEPSEEK_MODEL`：模型名称（默认 `deepseek-chat`）
- `DATA_FILE_PATH`：传感器数据 JSON 文件路径
- `PROMPT_FILE_PATH`：系统提示词 YAML 文件路径

提示词模板默认在 `prompts/system.yaml`，可复制并修改后通过 `PROMPT_FILE_PATH` 指向新文件。

## 许可证

BSD 3-Clause License
