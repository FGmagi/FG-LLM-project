"""
FastAPI 后端应用（负责静态页面、/chat 接口与启动）
- 提供 / 返回静态 index.html（前端）
- 提供 POST /chat 接收 {message: "..."}，返回 {"response": "..."}
- start_server()：用于 main.py 启动 uvicorn
"""

import os
import uvicorn
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

# 引入内部模块
from .data_loader import load_recent_data
from .llm_service import get_ai_response
from .config import DATA_FILE_PATH

# 项目结构约定：static 文件夹并列于项目根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(ROOT_DIR, "static")

app = FastAPI(title="果农助手API")

# 允许所有来源（开发阶段），生产请限制来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态目录（前端页面、css、js）
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
else:
    print(f"警告: 未找到 static 目录: {STATIC_DIR}，请检查前端文件是否存在。")

# 简单首页路由（返回 static/index.html）
@app.get("/", response_class=FileResponse)
async def index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"error": "index.html 未找到，请检查 static 目录"}, status_code=404)

# 状态接口
@app.get("/status")
async def status():
    exists = os.path.exists(DATA_FILE_PATH)
    return {"ok": True, "data_file_exists": exists}

# 核心对话接口：接收用户消息，返回 LLM 回复
@app.post("/chat")
async def chat_endpoint(req: Request):
    """
    请求体： {"message": "<农民的问题/描述>"}
    返回： {"response": "<LLM回复文本>"}
    """
    payload = await req.json()
    user_message = payload.get("message", "").strip()
    if not user_message:
        return JSONResponse({"response": "请提供问题描述，例如：'我的果树要不要浇水？' "}, status_code=400)

    # 从数据文件读取最近观测（移除 scene_tag 等）
    data_context, summary_str, df_window = load_recent_data(hours=24)

    # 调用 LLM（或本地 mock）
    ai_text = get_ai_response(user_message=user_message, data_context=data_context, summary_str=summary_str)

    return JSONResponse({"response": ai_text})

# 在 main.py 中调用 start_server()
def start_server(host: str = "0.0.0.0", port: int = 3000, open_browser: bool = True):
    """
    启动 uvicorn 服务（阻塞）。
    在开发机上可选打开默认浏览器。
    """
    url = f"http://localhost:{port}"
    print("启动服务：", url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    uvicorn.run("src.app:app", host=host, port=port, reload=False, log_level="info")
