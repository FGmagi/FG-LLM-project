"""
FastAPI 后端应用（负责静态页面、/chat 接口与启动）
- 提供 / 返回静态 index.html（前端）
- 提供 POST /chat 接收 {message: "...", reference_time: "<可选>", include_forecast: bool}, 返回 {"response": "..."}
- start_server()：用于 main.py 启动 uvicorn
"""

import os
import uvicorn
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .data_loader import load_recent_window, load_forecast_window, load_both_windows
from .llm_service import get_ai_response
from .config import DATA_FILE_PATH, SYSTEM_PROMPT_TEMPLATE

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
    请求体：
      {
        "message": "<农民的问题>",
        "reference_time": "<可选时间字符串，例如 2025-05-01 00:00:00>",
        "include_forecast": true/false (可选，默认 True)
      }
    返回： {"response": "<LLM 回复文本>"}
    """
    payload = await req.json()
    user_message = payload.get("message", "").strip()
    if not user_message:
        return JSONResponse({"response": "请提供问题描述，例如：'我的果树要不要浇水？' "}, status_code=400)

    try:
        reference_time = payload.get("reference_time", None)
        include_forecast = bool(payload.get("include_forecast", True))

        pre_context, pre_summary, pre_df = load_recent_window(pre_hours=24, reference_time=reference_time)
        post_context = post_summary = post_df = None
        if include_forecast:
            post_context, post_summary, post_df = load_forecast_window(post_hours=24, reference_time=reference_time)

    except Exception as e:
        # 若数据加载失败：返回 mock 建议并携带错误信息，便于前端展示调试信息
        err = f"数据加载失败: {e}"
        ai_text = get_ai_response(user_message=user_message, data_context="", summary_str=err)
        return JSONResponse({"response": ai_text, "error": err}, status_code=200)

    # 组合 context：把 pre 放前面，若 post 存在则追加（并合并 summary）
    if post_context:
        combined_context = f"PRE_WINDOW:\n{pre_context}\n\nPOST_WINDOW:\n{post_context}"
        combined_summary = f"PRE: {pre_summary} || POST: {post_summary}"
    else:
        combined_context = pre_context
        combined_summary = pre_summary

    # 调用 LLM（或本地 mock）
    ai_text = get_ai_response(user_message=user_message, data_context=combined_context, summary_str=combined_summary, system_prompt_template=SYSTEM_PROMPT_TEMPLATE)
    return JSONResponse({"response": ai_text})

# start_server（保持和以前一致，供 main.py 调用）
def start_server(host: str = "0.0.0.0", port: int = 3000, open_browser: bool = True):
    url = f"http://localhost:{port}"
    print("启动服务：", url)
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    uvicorn.run("src.app:app", host=host, port=port, reload=False, log_level="info")
