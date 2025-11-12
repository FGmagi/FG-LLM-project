import os
import requests
import json
import time
import socket
from typing import Dict, Any, Optional
from datetime import datetime
from S000 import printLog

class DeepSeekService:
    """DeepSeek AI服务类"""
    
    def __init__(self):
        self.api_key = os.getenv('DEEPSEEK_API_KEY', '')
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.model = "deepseek-chat"
        
        # API状态监控
        self.api_status = {
            "last_success": None,
            "last_failure": None,
            "consecutive_failures": 0,
            "total_calls": 0,
            "successful_calls": 0,
            "success_rate": 1.0
        }
    
    def set_api_key(self, api_key: str):
        """设置API密钥"""
        if api_key and api_key != 'your_deepseek_api_key_here':
            self.api_key = api_key
            printLog("✅ DeepSeek API密钥已设置")
        else:
            printLog("⚠️ DeepSeek API密钥未设置，将使用模拟模式", "WARNING")
            self.api_key = ''
    
    def health_check(self) -> dict:
        """深度检测API健康状况"""
        try:
            # 直接使用实例的api_key属性，而不是重新读取环境变量
            health_status = {
                "api_configured": bool(self.api_key and self.api_key != 'your_deepseek_api_key_here'),
                "network_connected": False,
                "authentication_valid": False,
                "service_available": False,
                "balance_sufficient": True,
                "response_time": None,
                "last_check": datetime.now().isoformat(),
                "error_message": None
            }
            
            printLog(f"健康检查: api_configured={health_status['api_configured']}, api_key_length={len(self.api_key) if self.api_key else 0}", "DEBUG")
            
            if not health_status["api_configured"]:
                health_status["error_message"] = f"API密钥未配置 (密钥长度: {len(self.api_key) if self.api_key else 0})"
                return health_status
            
            # 测试网络连接
            printLog("测试网络连接...", "DEBUG")
            try:
                socket.create_connection(("api.deepseek.com", 443), timeout=5)
                health_status["network_connected"] = True
            except Exception as e:
                health_status["error_message"] = f"网络连接失败: {e}"
                return health_status
            
            # 测试API调用
            printLog("测试API认证...", "DEBUG")
            start_time = time.time()
            test_response = self._call_simple_test()
            health_status["response_time"] = round(time.time() - start_time, 2)
            
            if test_response and "API测试成功" in test_response:
                health_status["authentication_valid"] = True
                health_status["service_available"] = True
                health_status["balance_sufficient"] = True
                printLog("✅ API健康检查通过", "DEBUG")
            else:
                # 检查是否是余额问题
                if test_response is None:
                    health_status["error_message"] = "API调用返回None"
                elif "余额不足" in test_response or "Insufficient Balance" in test_response:
                    health_status["error_message"] = "API余额不足"
                    health_status["balance_sufficient"] = False
                    health_status["authentication_valid"] = True  # 认证是有效的，只是余额不足
                else:
                    health_status["error_message"] = f"API返回异常: {test_response}"
                printLog(f"❌ API返回异常: {test_response}", "DEBUG")
            
            return health_status
            
        except Exception as e:
            # 如果发生任何异常，返回一个基本的健康状态
            printLog(f"健康检查发生异常: {e}", "ERROR")
            return {
                "api_configured": bool(self.api_key and self.api_key != 'your_deepseek_api_key_here'),
                "network_connected": False,
                "authentication_valid": False,
                "service_available": False,
                "balance_sufficient": False,
                "response_time": None,
                "last_check": datetime.now().isoformat(),
                "error_message": f"健康检查异常: {e}"
            }
    
    def _call_simple_test(self) -> str:
        """简单的API测试调用"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user", 
                        "content": "请只回复'API测试成功'这四个字，不要添加任何其他内容"
                    }
                ],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content'].strip()
            else:
                printLog(f"测试调用失败: HTTP {response.status_code} - {response.text}", "ERROR")
                return None
                
        except Exception as e:
            printLog(f"测试调用异常: {e}", "ERROR")
            return None
    
    def get_api_status(self) -> dict:
        """获取API状态统计"""
        status = self.api_status.copy()
        if status["total_calls"] > 0:
            status["success_rate"] = round(status["successful_calls"] / status["total_calls"], 3)
        else:
            status["success_rate"] = 0.0
        
        # 添加健康检查结果
        try:
            status["health"] = self.health_check()
        except Exception as e:
            status["health"] = {
                "api_configured": False,
                "network_connected": False,
                "authentication_valid": False,
                "service_available": False,
                "balance_sufficient": False,
                "response_time": None,
                "error_message": f"获取健康状态失败: {e}"
            }
        
        return status
    
    def generate_agriculture_response(self, user_message: str, sensor_data: Dict, context: Dict = None) -> str:
        """生成农业建议响应"""
        self.api_status["total_calls"] += 1
        
        try:
            # 构建提示词
            prompt = self._build_agriculture_prompt(user_message, sensor_data, context)
            
            # 调用DeepSeek API
            response = self._call_deepseek_api(prompt)
            
            # 记录成功
            self.api_status["successful_calls"] += 1
            self.api_status["last_success"] = datetime.now().isoformat()
            self.api_status["consecutive_failures"] = 0
            
            return self._post_process_response(response)
            
        except Exception as e:
            # 记录失败
            self.api_status["last_failure"] = datetime.now().isoformat()
            self.api_status["consecutive_failures"] += 1
            printLog(f"DeepSeek API调用失败: {e}", "ERROR")
            return self._get_fallback_response(user_message, sensor_data)
    
    def _build_agriculture_prompt(self, user_message: str, sensor_data: Dict, context: Dict) -> str:
        """构建农业专用提示词"""
        
        # 传感器数据部分
        sensor_info = self._format_sensor_data(sensor_data)
        
        # 上下文知识部分
        context_info = self._format_context_data(context)
        
        prompt = f"""你是一个专业的农业专家助手，专门帮助柑橘种植户解决实际问题。请用专业但易懂的中文回答农民的问题。

# 当前农场数据：
{sensor_info}

{context_info}

# 农民的问题：
{user_message}

# 回答要求：
1. 首先分析传感器数据反映的问题
2. 给出具体的、可操作的建议
3. 说明建议的科学依据
4. 提醒注意事项
5. 语气要亲切、专业、务实
6. 使用emoji让回答更生动
7. 如果数据异常，要明确指出并提供解决方案

请直接给出实用的农业建议："""
        
        return prompt
    
    def _format_sensor_data(self, sensor_data: Dict) -> str:
        """格式化传感器数据"""
        if not sensor_data:
            return "暂无传感器数据"
        
        lines = ["🌱 **当前农场监测数据**："]
        
        # 土壤湿度
        moisture = sensor_data.get('soil_moisture')
        if moisture is not None:
            if moisture < 25:
                status = "🔴严重不足"
            elif moisture < 35:
                status = "🟡偏低"
            elif moisture > 65:
                status = "🟢过高"
            else:
                status = "✅正常"
            lines.append(f"- 💧土壤湿度：{moisture}% ({status})")
        
        # 温度
        temperature = sensor_data.get('temperature')
        if temperature is not None:
            if temperature < 10:
                status = "🔴过低"
            elif temperature < 15:
                status = "🟡偏低"
            elif temperature > 35:
                status = "🟢过高"
            else:
                status = "✅适宜"
            lines.append(f"- 🌡️温度：{temperature}°C ({status})")
        
        # pH值
        ph = sensor_data.get('soil_ph')
        if ph is not None:
            if ph < 5.5:
                status = "🔴过酸"
            elif ph > 7.5:
                status = "🟢过碱"
            else:
                status = "✅正常"
            lines.append(f"- 🧪土壤pH：{ph} ({status})")
        
        # NPK营养
        npk_lines = []
        nutrients = [
            ('npk_nitrogen', '氮(N)'),
            ('npk_phosphorus', '磷(P)'), 
            ('npk_potassium', '钾(K)')
        ]
        
        for nutrient_key, nutrient_name in nutrients:
            value = sensor_data.get(nutrient_key)
            if value is not None:
                if value < 30:
                    status = "🔴不足"
                elif value < 40:
                    status = "🟡偏低"
                else:
                    status = "✅充足"
                npk_lines.append(f"{nutrient_name}:{value}%({status})")
        
        if npk_lines:
            lines.append(f"- 🌿营养元素：{', '.join(npk_lines)}")
        
        return "\n".join(lines)
    
    def _format_context_data(self, context: Dict) -> str:
        """格式化上下文数据"""
        if not context or not context.get('knowledge_results'):
            return ""
        
        knowledge = context['knowledge_results']
        context_info = "📚 **相关知识参考**：\n"
        for i, item in enumerate(knowledge[:2], 1):
            title = item.get('title', '')
            content = item.get('content', '')
            context_info += f"{i}. **{title}**：{content}\n"
        
        return context_info
    
    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        if not self.api_key or self.api_key == 'your_deepseek_api_key_here':
            printLog("DeepSeek API密钥未设置，使用模拟模式", "WARNING")
            return self._get_mock_response(prompt)
        
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的农业专家，专门帮助农民解决柑橘种植问题。请用亲切、专业、易懂的中文回答。"
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.7,
                "stream": False
            }
            
            printLog(f"🔄 发送DeepSeek API请求，提示词长度: {len(prompt)}", "DEBUG")
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            
            printLog(f"📡 API响应状态: {response.status_code}", "DEBUG")
            
            if response.status_code == 200:
                result = response.json()
                answer = result['choices'][0]['message']['content']
                printLog("✅ DeepSeek API调用成功", "DEBUG")
                return answer
            elif response.status_code == 401:
                printLog("❌ DeepSeek API认证失败，请检查API密钥", "ERROR")
                return self._get_mock_response(prompt)
            elif response.status_code == 402:
                printLog("❌ DeepSeek API余额不足，请充值账户", "ERROR")
                return self._get_balance_error_response(prompt)
            elif response.status_code == 429:
                printLog("❌ DeepSeek API调用频率限制", "ERROR")
                return self._get_mock_response(prompt)
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                printLog(f"DeepSeek API返回错误: {error_msg}", "ERROR")
                return self._get_mock_response(prompt)
                
        except requests.exceptions.Timeout:
            printLog("DeepSeek API请求超时", "ERROR")
            return self._get_mock_response(prompt)
        except requests.exceptions.ConnectionError:
            printLog("DeepSeek API连接错误，请检查网络", "ERROR")
            return self._get_mock_response(prompt)
        except Exception as e:
            printLog(f"DeepSeek API调用异常: {e}", "ERROR")
            return self._get_mock_response(prompt)
    
    def _get_balance_error_response(self, prompt: str) -> str:
        """余额不足时的专用响应"""
        return """💰 **DeepSeek API余额不足**

🔍 **检测到问题**：
您的DeepSeek API账户余额不足，无法使用AI服务。

🌱 **当前解决方案**：
系统已自动切换到**智能模拟模式**，您仍然可以获得专业的农业建议：

💡 **模拟模式功能**：
• 基于预设的农业知识库
• 智能关键词匹配回答
• 专业的柑橘种植建议

🔧 **恢复AI服务**：
1. 访问 https://platform.deepseek.com/
2. 登录您的账户
3. 查看余额并充值
4. 系统将自动切换回AI模式

📞 **技术支持**：
如有疑问，请联系DeepSeek官方支持。

现在，请告诉我您的农业问题，我将尽力为您提供帮助！"""
    
    def _get_mock_response(self, prompt: str) -> str:
        """智能模拟响应 - 用于降级"""
        prompt_lower = prompt.lower()
        
        # 更精确的关键词匹配
        if any(word in prompt_lower for word in ['叶子发黄', '叶黄', '黄叶']):
            return """🍂 **柑橘叶子发黄分析**：

可能原因及解决方案：

🔍 **营养缺乏**：
• 缺氮：叶片均匀发黄，施氮肥
• 缺铁：新叶发黄，叶脉绿色，补硫酸亚铁
• 缺镁：老叶发黄，补硫酸镁

💧 **水分问题**：
• 过湿：根部腐烂，改善排水
• 过干：叶片萎蔫，及时浇水

🐛 **病虫害**：
• 检查红蜘蛛、蚜虫
• 及时使用生物农药

🌱 **建议措施**：
1. 检查具体症状，对症处理
2. 补充平衡型复合肥
3. 改善灌溉管理"""

        elif any(word in prompt_lower for word in ['红蜘蛛', '螨虫', '叶螨']):
            return """🐛 **柑橘红蜘蛛综合防治**：

🔍 **识别特征**：
• 叶片出现黄白色小点
• 叶背有红色小点移动
• 严重时叶片枯黄脱落

🛡️ **化学防治**：
• 阿维菌素 1500倍液喷雾
• 螺螨酯 2000倍液防治
• 哒螨灵 1000倍液杀灭

🌱 **生物防治**：
• 引入捕食螨（如加州新小绥螨）
• 保护瓢虫、草蛉等天敌

💡 **农业防治**：
• 保持果园通风透光
• 避免过度使用氮肥
• 冬季清园，减少虫源

⚠️ **注意事项**：
• 轮换用药，防止抗性
• 重点喷洒叶背
• 高温干旱季节加强预防"""

        elif any(word in prompt_lower for word in ['npk', '肥料', '配比', '施肥']):
            return """🌿 **NPK肥料科学配比指南**：

📊 **不同生育期配比建议**：
• 幼树期（1-2年）：N-P-K = 2-1-1
• 开花期：N-P-K = 1-2-2  
• 果实膨大期：N-P-K = 1-1-2
• 采后期：N-P-K = 2-1-1

🎯 **施肥方法**：
• 基肥：有机肥3-5kg/株 + 复合肥0.5kg/株
• 追肥：花前肥、壮果肥、采果肥
• 叶面肥：补充硼、锌、镁等微量元素

💡 **使用技巧**：
• 环状沟施：树冠投影处开沟
• 穴施：树周围4-6个穴
• 撒施覆土：均匀撒施后浅耕

⚠️ **注意事项**：
• 避免单一肥料过量
• 施肥后及时浇水
• 根据土壤检测精准施肥"""

        elif any(word in prompt_lower for word in ['温度', '高温', '热']):
            return """🌡️ **高温对柑橘的影响及防护**：

🔥 **高温危害表现**：
• 叶片灼伤、卷曲
• 果实日灼病（向阳面灼伤）
• 落花落果加剧
• 水分蒸发过快

🛡️ **防护措施**：
• 适时灌溉：早晨或傍晚浇水
• 果实套袋：保护果实免受日灼
• 种植绿肥：园生草覆盖降温
• 搭建遮阳网：极端高温时使用

💡 **管理建议**：
• 避免中午高温时田间作业
• 保持土壤湿润但不积水
• 加强病虫害监测预防

📈 **适宜温度范围**：
• 生长适温：15-30°C
• 开花适温：17-20°C  
• 果实发育：20-30°C"""

        elif any(word in prompt_lower for word in ['浇水', '灌溉', '湿度']):
            return """💧 **柑橘科学灌溉指南**：

📊 **不同时期需水量**：
• 萌芽期：保持土壤湿润
• 开花期：湿度30%-40%
• 果实膨大期：湿度40%-50%
• 成熟期：适当控水提高品质

🎯 **灌溉方法**：
• 滴灌：节水高效，推荐使用
• 微喷灌：均匀温和
• 沟灌：传统方法，注意排水

💡 **判断时机**：
• 土壤手握成团，落地散开 - 适宜
• 土壤手握不成团 - 需要浇水
• 土壤粘手 - 水分过多

⚠️ **注意事项**：
• 避免中午高温时灌溉
• 花期控制水分防落花
• 雨季注意排水防涝"""

        else:
            # 提取用户问题
            user_message = "未知问题"
            lines = prompt.split('\n')
            for line in lines:
                if line.startswith('# 农民的问题：'):
                    user_message = line.replace('# 农民的问题：', '').strip()
                    break
            
            # 通用智能回复
            return f"""🌱 **智能农业助手** 

关于"**{user_message}**"的问题，我可以为您提供专业分析：

🔍 **我能帮您分析**：
• 土壤营养状况评估
• 水分管理优化方案  
• 病虫害综合防治
• 生长环境调控建议

💡 **请提供更多细节**：
• 具体症状描述
• 发生时间和范围
• 已采取的措施

我将基于当前传感器数据给出针对性解决方案！

📞 **专业支持**：如有复杂问题，建议咨询当地农技人员。"""

    def _post_process_response(self, response: str) -> str:
        """后处理响应"""
        response = response.strip()
        
        # 确保响应不为空
        if not response:
            return "🌱 抱歉，我暂时无法提供具体建议。请检查传感器数据或联系当地农业技术人员获取帮助。"
        
        # 移除可能的API特定格式
        if response.startswith('"') and response.endswith('"'):
            response = response[1:-1]
        
        return response
    
    def _get_fallback_response(self, user_message: str, sensor_data: Dict) -> str:
        """完整的降级响应"""
        return f"""🤔 **关于"{user_message}"的专业分析**

📊 基于当前农场数据，建议您：

🔍 **重点关注**：
• 定期监测土壤关键指标
• 观察作物生长状态变化
• 记录管理措施和效果

🌱 **专业建议**：
1. 遵循科学的种植管理规范
2. 结合当地气候条件调整
3. 建立系统的生产记录

💡 **温馨提示**：
具体操作请结合实际情况，如有异常及时咨询当地农技人员。

📞 **技术支持**：随时为您提供专业的农业咨询服务！"""

# 全局DeepSeek服务实例
deepseek_service = DeepSeekService()