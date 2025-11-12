import http.server
import socketserver
import webbrowser
import json
from datetime import datetime
import os
from S001 import *

# ===========================================
# 前端功能模式流程
# 用户输入消息 → 前端发送 POST 请求 → do_POST 被调用 → 处理消息 → 返回AI回复 → 前端显示回复
# ===========================================
def checkFilesWholeness() -> bool:
    required_files = ['index.html', 'style.css']
    b = True
    for f in required_files:
        if not os.path.exists(f):
            printLog(f"缺少必要文件:{f}")
            b = False
    if (b == True):
        printLog(f"文件完整性检查 通过")
    else:
        printLog(f"文件完整性检查 失败")
    return b

def startWeb(port=3000):
    if not checkFilesWholeness():
        printLog("启动失败，文件不完整\n请确保所有必要文件存在")
        return
    
    print("=" * 50)
    print("启动农业AI助手前端服务")
    print(f"服务地址: http://localhost:{port}")
    print("=" * 50)
    printLog("启动农业AI助手前端 成功")
    try:
        with socketserver.TCPServer(("", port), SimpleChatHandler) as httpd:
            print(f"服务器启动成功! 端口: {port}")
            webbrowser.open(f"http://localhost:{port}")
            print("按 Ctrl+C 停止服务器")
            httpd.serve_forever()
    except OSError as e:
        print(f"端口 {port} 被占用，尝试其他端口...")
        printLog(f"端口 {port} 被占用，尝试其他端口...")
        startWeb(port + 1)
    except KeyboardInterrupt:
        print("\n服务器已停止")
        printLog(f"服务器已停止")

def chat(input_text):
    if not DEMO:
        return releaseIO(input_text)
    else:
        return demoIO(input_text)

def getWelcomeMessage():
    msg = """
    欢迎使用果农助手！我可以为您提供柑橘种植的智能建议。
        您可以使用：
        "浇水灌溉"
        "如何施肥？"
        "温度怎么样？"
        "病虫害防治"
        系统消息
    """
    return msg

class SimpleChatHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # 提供HTML文件
            self.serve_html_file()
        elif self.path == '/style.css':
            # 提供CSS文件
            self.serve_css_file()
        elif self.path == '/welcome':
            # 提供欢迎消息
            self.serveWelcomeMessage()
        elif self.path == '/chat':
            # 处理聊天请求（GET方式返回错误）
            self.send_error(405, "Method Not Allowed")
        else:
            # 其他静态文件
            super().do_GET()
    
    def serve_html_file(self):
        """提供HTML文件"""
        try:
            with open('index.html', 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html_content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "HTML file not found")
    
    def serve_css_file(self):
        """提供CSS文件"""
        try:
            with open('style.css', 'r', encoding='utf-8') as f:
                css_content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/css; charset=utf-8')
            self.end_headers()
            self.wfile.write(css_content.encode('utf-8'))
        except FileNotFoundError:
            self.send_error(404, "CSS file not found")
    
    def serveWelcomeMessage(self):
        """提供欢迎消息"""
        welcome_message = getWelcomeMessage()
        
        response_data = {
            "response": welcome_message,
            "timestamp": datetime.now().isoformat(),
            "type": "welcome"
        }
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
    
    def do_POST(self):
        if self.path == '/chat':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            user_message = request_data.get('message', '')
            response = chat(user_message)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response_data = {
                "response": response,
                "timestamp": datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response_data, ensure_ascii=False).encode('utf-8'))
        else:
            self.send_error(404)

def demoIO(input_text):
    """通过字符串识别，提供固定反馈字符串"""
    input_lower = input_text.lower()
    
    # 问候识别
    if any(word in input_lower for word in ['你好', '您好', 'hello', 'hi', '嗨']):
        return "🌱 您好！我是果农助手，专门为柑橘种植提供智能建议。请问您想了解什么？"
    
    # 感谢识别
    if any(word in input_lower for word in ['谢谢', '感谢', '多谢']):
        return "🙏 不客气！随时为您提供农业咨询服务。"
    
    # 浇水相关
    if any(word in input_lower for word in ['浇水', '灌溉', '水分', '湿度']):
        return "💧 **浇水建议**:\n柑橘在开花期需要保持土壤湿度30-40%，果实膨大期需要40-50%。当前建议每周浇水2-3次，根据天气情况调整。"
    
    # 施肥相关
    if any(word in input_lower for word in ['施肥', '肥料', '营养', 'npk']):
        return "🌿 **施肥建议**:\n春季追施氮肥，夏季增施磷钾肥，NPK比例建议2:1:1。当前建议使用柑橘专用复合肥，每亩施用30-40公斤。"
    
    # 病虫害相关
    if any(word in input_lower for word in ['病虫害', '虫害', '病害', '防治']):
        return "🐛 **病虫害防治**:\n注意防治红蜘蛛、蚜虫，保持果园通风透光。推荐使用生物农药进行预防，发现病害及时处理。"
    
    # 温度相关
    if any(word in input_lower for word in ['温度', '气温', '天气']):
        return "🌡️ **温度管理**:\n柑橘生长最适温度为15-30℃。高温时注意遮阴，低温时注意防冻。当前季节建议关注夜间低温。"
    
    # 土壤相关
    if any(word in input_lower for word in ['土壤', 'ph', '酸碱']):
        return "🧪 **土壤管理**:\n柑橘适宜土壤pH为5.5-7.5。建议定期检测土壤酸碱度，使用有机肥改良土壤结构。"
    
    # 状态查询
    if any(word in input_lower for word in ['怎么样', '情况', '状态', '如何']):
        return "📊 **当前状态**:\n根据模拟数据，您的柑橘园整体状况良好。建议关注土壤湿度和营养平衡，定期检查病虫害情况。"
    
    # 默认回复
    return f"🤔 您问的是 '{input_text}' 吗？我可以帮您分析浇水、施肥、病虫害、温度、土壤等问题，请具体说明您想了解的内容。"