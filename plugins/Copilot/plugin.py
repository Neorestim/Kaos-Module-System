import os
import json
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

class CopilotPlugin:
    def _register_ui_content(self):
        """直接注入Copilot浮窗UI内容到WebPlatform插件（不依赖API注册表）"""
        copilot_css = '''
        /* Copilot AI助手悬浮窗样式 */
        ...existing code...
        '''
        copilot_html = '''
        <!-- Copilot AI助手悬浮窗 -->
        ...existing code...
        '''
        copilot_js = '''
        ...existing code...
        '''
        try:
            import sys
            web_module = sys.modules.get('plugins.WebPlatform.plugin')
            if web_module and hasattr(web_module, 'WebInterfaceHandler'):
                handler = getattr(web_module, 'WebInterfaceHandler')
                handler.register_plugin_content("Copilot", "css", copilot_css, "head")
                handler.register_plugin_content("Copilot", "html", copilot_html, "body")
                handler.register_plugin_content("Copilot", "js", copilot_js, "body")
                self.ui_registered = True
                print("Copilot浮窗UI已直接注入WebPlatform")
                return True
            else:
                print("未找到WebPlatform插件模块或Handler，无法注入UI内容")
        except Exception as e:
            print(f"注册UI内容时发生未预期错误: {e}")
            import traceback
            traceback.print_exc()
        return False
    def call_tool_command(self, command: str, timeout: int = 30) -> dict:
        """
        通过系统API调用工具命令（如模型推理/脚本），返回执行结果。
        :param command: 命令字符串
        :param timeout: 超时时间（秒）
        :return: {'success': bool, 'output': str, 'error': str}
        """
        if not self.api_registry:
            return {'success': False, 'output': '', 'error': 'API注册表不可用'}
        tool_api = self.api_registry.get_api('System', 'run_tool_command')
        if not tool_api:
            return {'success': False, 'output': '', 'error': '未找到工具API'}
        return tool_api(command, timeout)
    def __init__(self, api_registry=None, config_path=None):
        self.name = "Copilot"
        self.version = "1.0.0"
        self.developer = "Kaos Team"
        self.description = "AI助手插件，提供智能对话功能"
        self.api_registry = api_registry
        # 自动查找 config/model_config.toml
        if config_path is not None:
            self.config_path = config_path
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            default_path = os.path.join(base_dir, "config", "model_config.toml")
            self.config_path = default_path if os.path.exists(default_path) else None
        self.is_registered = False
        self.is_started = False
        self.ai_manager = None
        self.conversation_history = []
        self.pending_requests = {}
        self.ui_registered = False
        
    def get_manifest(self):
        """获取插件清单信息"""
        return {
            "pluginName": self.name,
            "version": self.version,
            "Developer": self.developer,
            "description": self.description
        }
        
    def register_apis(self):
        """注册插件API（仅聊天处理API）"""
        try:
            if self.api_registry and not self.is_registered:
                self.api_registry.register_api(
                    "Copilot", 
                    "handle_chat", 
                    self._handle_chat_request, 
                    show_output=False
                )
                self.is_registered = True
                print("[Copilot] API注册成功")
                return True
        except Exception as e:
            error_msg = f"注册API时出错: {e}"
            print(f"[Copilot] {error_msg}")
            import traceback
            traceback.print_exc()
        return False
            
    # 菜单注册相关方法已移除
        
    def _ai_message_handler(self, message_type, data):
        """处理AI消息"""
        try:
            if message_type == "ai_response":
                request_id = data.get("request_id")
                if request_id in self.pending_requests:
                    # 存储响应数据
                    self.pending_requests[request_id]["response"] = data
                    # 通知等待的线程
                    if "event" in self.pending_requests[request_id]:
                        self.pending_requests[request_id]["event"].set()
        except Exception as e:
            print(f"处理AI消息时出错: {e}")

    def _handle_chat_request(self, message, model_name="G3"):
        """处理聊天请求"""
        try:
            # 添加用户消息到对话历史
            self.conversation_history.append({
                "role": "user",
                "content": message
            })
            
            # 发送请求到AI管理器
            if self.ai_manager:
                request_id = self.ai_manager.send_request(
                    model_name=model_name,
                    messages=self.conversation_history
                )
                
                # 创建等待事件
                import threading
                event = threading.Event()
                self.pending_requests[request_id] = {
                    "event": event,
                    "response": None
                }
                
                # 等待响应（最多30秒）
                if event.wait(timeout=30):
                    response_data = self.pending_requests[request_id]["response"]
                    # 清理等待记录
                    del self.pending_requests[request_id]
                    
                    if "error" in response_data:
                        return {"error": response_data["error"]}
                    
                    # 添加AI回复到对话历史
                    ai_response = response_data["response"]
                    if "content" in ai_response:
                        self.conversation_history.append({
                            "role": "assistant",
                            "content": ai_response["content"]
                        })
                        return {"response": ai_response["content"]}
                    else:
                        return {"error": "AI响应格式错误"}
                else:
                    # 超时处理
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
                    return {"error": "请求超时"}
            else:
                return {"error": "AI管理器未初始化"}
        except Exception as e:
            error_msg = f"处理聊天请求时出错: {e}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def truncate_thought_chain(self, text, start_marker="<think>", end_marker="</think>"):
        """
        截断思维链文本，提取 <think> ... </think> 区间内容。
        参数:
            text (str): 原始文本。
            start_marker (str): 起始标记，默认 <think>
            end_marker (str): 结束标记，默认 </think>
        返回:
            str: 截取后的内容，若无则返回空字符串。
        """
        try:
            start = text.find(start_marker)
            if start == -1:
                return ""
            start += len(start_marker)
            end = text.find(end_marker, start)
            if end == -1:
                return ""
            return text[start:end].strip()
        except Exception as e:
            print(f"截断思维链时出错: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def start(self):
        """启动插件"""
        if self.is_started:
            print("插件已启动，无需重复启动")
            return True
            
        try:
            print("正在启动Copilot插件...")
            # 注册API
            if not self.register_apis():
                print("警告: API注册失败，插件功能可能受限")
            # 初始化AI管理器
            try:
                from src.ai_api import get_ai_manager, register_ai_message_listener
                # 如果配置文件存在，传递配置文件路径给AI管理器
                if self.config_path and os.path.exists(self.config_path):
                    self.ai_manager = get_ai_manager(self.config_path)
                    print(f"使用配置文件: {self.config_path}")
                else:
                    self.ai_manager = get_ai_manager()
                # 注册消息监听器
                register_ai_message_listener(self._ai_message_handler)
                print("AI管理器初始化成功")
            except ImportError as e:
                print(f"警告: 无法导入AI管理器模块: {e}")
            except Exception as e:
                print(f"警告: 无法初始化AI管理器: {e}")
                import traceback
                traceback.print_exc()
            # 注册UI内容到Web平台
            self._register_ui_content()
        except Exception as e:
            print(f"Copilot启动异常: {e}")
            import traceback
            traceback.print_exc()
        return True

    def _register_ui_content(self):
        """直接注入Copilot浮窗UI内容到WebPlatform插件（不依赖API注册表）"""
        copilot_css = '''
        /* Copilot AI助手悬浮窗样式 */
        ...existing code...
        '''
        copilot_html = '''
        <!-- Copilot AI助手悬浮窗 -->
        ...existing code...
        '''
        copilot_js = '''
        ...existing code...
        '''
        try:
            import sys
            web_module = sys.modules.get('plugins.WebPlatform.plugin')
            if web_module and hasattr(web_module, 'WebInterfaceHandler'):
                handler = getattr(web_module, 'WebInterfaceHandler')
                handler.register_plugin_content("Copilot", "css", copilot_css, "head")
                handler.register_plugin_content("Copilot", "html", copilot_html, "body")
                handler.register_plugin_content("Copilot", "js", copilot_js, "body")
                self.ui_registered = True
                print("Copilot浮窗UI已直接注入WebPlatform")
                return True
            else:
                print("未找到WebPlatform插件模块或Handler，无法注入UI内容")
        except Exception as e:
            print(f"Copilot UI注入WebPlatform失败: {e}")
            import traceback
            traceback.print_exc()
        return False
        
    def _register_ui_content(self):
        """注册UI内容到Web平台（仅浮窗UI，无菜单）"""
        try:
            if not self.api_registry:
                print("警告: API注册表不可用，无法注册UI内容")
                return False

            # 注册Copilot CSS样式
            copilot_css = '''
            /* Copilot AI助手悬浮窗样式 */
            .copilot-float-btn {
                position: fixed;
                bottom: 30px;
                right: 30px;
                width: 60px;
                height: 60px;
                border-radius: 50%;
                background: linear-gradient(135deg, #3498db, #8e44ad);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
                z-index: 1000;
                transition: all 0.3s ease;
                font-size: 24px;
            }
            
            .copilot-float-btn:hover {
                transform: scale(1.1);
                box-shadow: 0 6px 25px rgba(0,0,0,0.4);
            }
            
            .copilot-container {
                position: fixed;
                bottom: 100px;
                right: 30px;
                width: 400px;
                height: 500px;
                background: rgba(255, 255, 255, 0.95);
                backdrop-filter: blur(10px);
                -webkit-backdrop-filter: blur(10px);
                border-radius: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                z-index: 1000;
                display: none;
                flex-direction: column;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, 0.3);
            }
            
            .copilot-header {
                padding: 20px;
                background: linear-gradient(135deg, #3498db, #8e44ad);
                color: white;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .copilot-title {
                font-size: 1.2rem;
                font-weight: 600;
            }
            
            .copilot-close {
                background: none;
                border: none;
                color: white;
                font-size: 1.5rem;
                cursor: pointer;
                width: 30px;
                height: 30px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 50%;
                transition: background 0.3s ease;
            }
            
            .copilot-close:hover {
                background: rgba(255, 255, 255, 0.2);
            }
            
            .copilot-messages {
                flex: 1;
                padding: 20px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }
            
            .copilot-message {
                max-width: 80%;
                padding: 12px 16px;
                margin-bottom: 15px;
                border-radius: 18px;
                word-wrap: break-word;
                animation: fadeIn 0.3s ease;
            }
            
            .copilot-user-message {
                align-self: flex-end;
                background: linear-gradient(135deg, #3498db, #2980b9);
                color: white;
            }
            
            .copilot-ai-message {
                align-self: flex-start;
                background: rgba(241, 241, 241, 0.9);
                color: #333;
            }
            
            .copilot-input-container {
                padding: 20px;
                border-top: 1px solid rgba(0, 0, 0, 0.1);
                display: flex;
            }
            
            .copilot-input {
                flex: 1;
                padding: 12px 15px;
                border: 1px solid #ddd;
                border-radius: 25px;
                outline: none;
                font-size: 1rem;
                background: rgba(255, 255, 255, 0.8);
            }
            
            .copilot-send-btn {
                margin-left: 10px;
                padding: 12px 20px;
                background: linear-gradient(135deg, #3498db, #8e44ad);
                color: white;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                font-weight: 600;
                transition: transform 0.2s ease;
            }
            
            .copilot-send-btn:hover {
                transform: translateY(-2px);
            }
            
            .copilot-send-btn:active {
                transform: translateY(0);
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            /* 添加打字效果 */
            .copilot-typing-indicator {
                align-self: flex-start;
                background: rgba(241, 241, 241, 0.9);
                color: #333;
                padding: 12px 16px;
                border-radius: 18px;
                margin-bottom: 15px;
                display: flex;
                align-items: center;
            }
            
            .typing-dot {
                width: 8px;
                height: 8px;
                background-color: #999;
                border-radius: 50%;
                margin: 0 2px;
                animation: typing 1.4s infinite ease-in-out;
            }
            
            .typing-dot:nth-child(1) { animation-delay: 0s; }
            .typing-dot:nth-child(2) { animation-delay: 0.2s; }
            .typing-dot:nth-child(3) { animation-delay: 0.4s; }
            
            @keyframes typing {
                0%, 60%, 100% { transform: translateY(0); }
                30% { transform: translateY(-5px); }
            }
            '''
            
            # 注册Copilot HTML内容（增加工具调用确认弹窗）
            copilot_html = '''
            <!-- Copilot AI助手悬浮窗 -->
            <div class="copilot-float-btn" id="copilotFloatBtn">
                <i class="fas fa-robot"></i>
            </div>
            <div class="copilot-container" id="copilotContainer">
                <div class="copilot-header">
                    <div class="copilot-title">Copilot AI助手</div>
                    <button class="copilot-close" id="copilotClose">&times;</button>
                </div>
                <div class="copilot-messages" id="copilotMessages">
                    <div class="copilot-message copilot-ai-message">
                        您好！我是Copilot AI助手，有什么我可以帮您的吗？
                    </div>
                </div>
                <div class="copilot-input-container">
                    <input type="text" class="copilot-input" id="copilotInput" placeholder="输入您的问题...">
                    <button class="copilot-send-btn" id="copilotSend">发送</button>
                </div>
            </div>
            <!-- 工具调用确认弹窗 -->
            <div class="copilot-tool-confirm" id="copilotToolConfirm" style="display:none;position:fixed;bottom:160px;right:50px;width:320px;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.18);z-index:2000;padding:24px;">
                <div style="font-weight:bold;font-size:16px;margin-bottom:12px;">工具调用请求</div>
                <div id="copilotToolConfirmMsg" style="margin-bottom:18px;">是否允许Copilot执行工具命令？</div>
                <button id="copilotToolAllow" style="margin-right:16px;padding:8px 18px;border-radius:6px;background:#3498db;color:#fff;border:none;">允许</button>
                <button id="copilotToolDeny" style="padding:8px 18px;border-radius:6px;background:#eee;color:#333;border:none;">拒绝</button>
            </div>
            '''
            
            copilot_js = '''
            // Copilot AI助手功能
            (function() {
                const floatBtn = document.getElementById('copilotFloatBtn');
                const container = document.getElementById('copilotContainer');
                const closeBtn = document.getElementById('copilotClose');
                const input = document.getElementById('copilotInput');
                const sendBtn = document.getElementById('copilotSend');
                const messages = document.getElementById('copilotMessages');
                const toolConfirm = document.getElementById('copilotToolConfirm');
                const toolAllow = document.getElementById('copilotToolAllow');
                const toolDeny = document.getElementById('copilotToolDeny');
                const toolConfirmMsg = document.getElementById('copilotToolConfirmMsg');

                let pendingTool = null;

                // 切换悬浮窗显示/隐藏
                floatBtn.addEventListener('click', function() {
                    container.style.display = container.style.display === 'flex' ? 'none' : 'flex';
                });

                // 关闭悬浮窗
                closeBtn.addEventListener('click', function() {
                    container.style.display = 'none';
                });

                // 发送消息
                function sendMessage() {
                    const message = input.value.trim();
                    if (message) {
                        addMessage(message, 'user');
                        input.value = '';
                        const typingIndicator = addTypingIndicator();
                        fetch('/api/copilot/chat', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({message: message})
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (typingIndicator && typingIndicator.parentNode) {
                                typingIndicator.parentNode.removeChild(typingIndicator);
                            }
                            // 工具调用请求
                            if (data.tool_request) {
                                pendingTool = data.tool_request;
                                toolConfirmMsg.textContent = data.tool_request.confirm_msg || '是否允许Copilot执行工具命令？';
                                toolConfirm.style.display = 'block';
                            } else {
                                // 普通AI回复
                                if (data.response) {
                                    addMessage(data.response, 'ai');
                                } else if (data.error) {
                                    addMessage('抱歉，处理您的请求时出现了错误: ' + data.error, 'ai');
                                }
                            }
                        })
                        .catch(error => {
                            if (typingIndicator && typingIndicator.parentNode) {
                                typingIndicator.parentNode.removeChild(typingIndicator);
                            }
                            addMessage('抱歉，无法连接到AI服务: ' + error.message, 'ai');
                        });
                    }
                }

                // 工具调用确认弹窗交互
                toolAllow.addEventListener('click', function() {
                    if (pendingTool) {
                        toolConfirm.style.display = 'none';
                        // 发送工具命令到后端
                        fetch('/api/copilot/tool', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(pendingTool)
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                addMessage('[工具执行结果]\n' + data.output, 'ai');
                            } else {
                                addMessage('[工具执行失败]\n' + data.error, 'ai');
                            }
                        });
                        pendingTool = null;
                    }
                });
                toolDeny.addEventListener('click', function() {
                    toolConfirm.style.display = 'none';
                    addMessage('已拒绝工具命令执行。', 'ai');
                    pendingTool = null;
                });

                // 添加消息到聊天窗口
                function addMessage(text, sender) {
                    const messageDiv = document.createElement('div');
                    messageDiv.classList.add('copilot-message');
                    messageDiv.classList.add(sender === 'user' ? 'copilot-user-message' : 'copilot-ai-message');
                    messageDiv.textContent = text;
                    messages.appendChild(messageDiv);
                    messages.scrollTop = messages.scrollHeight;
                }
                // 添加打字指示器
                function addTypingIndicator() {
                    const typingDiv = document.createElement('div');
                    typingDiv.className = 'copilot-typing-indicator';
                    typingDiv.innerHTML = `
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    `;
                    messages.appendChild(typingDiv);
                    messages.scrollTop = messages.scrollHeight;
                    return typingDiv;
                }
                
                // 发送按钮点击事件
                sendBtn.addEventListener('click', sendMessage);
                
                // 回车发送消息
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter') {
                        sendMessage();
                    }
                });
            })();
            '''
            
            # 通过API系统注册内容到Web平台
            register_content_api = self.api_registry.get_api("WebPlatform", "register_plugin_content")
            if register_content_api is not None:
                try:
                    register_content_api("Copilot", "css", copilot_css, "head")
                    register_content_api("Copilot", "html", copilot_html, "body")
                    register_content_api("Copilot", "js", copilot_js, "body")
                    self.ui_registered = True
                    print("UI内容已注册")
                    return True
                except Exception as e:
                    print(f"警告: 注册UI内容时出错: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                print("警告: 无法获取注册内容API，无法注册UI内容")
        except Exception as e:
            print(f"注册UI内容时发生未预期错误: {e}")
            import traceback
            traceback.print_exc()
        return False
        
    # 延迟注册UI相关方法已移除

    def stop(self):
        """停止插件"""
        print("插件已停止")
        
    def send_ai_request(self, message, model_name="G3"):
        """发送AI请求"""
        if not self.ai_manager:
            return {"error": "AI管理器未初始化"}
        
        # 添加用户消息到对话历史
        self.conversation_history.append({
            "role": "user",
            "content": message
        })
        
        # 发送请求
        request_id = self.ai_manager.send_request(
            model_name=model_name,
            messages=self.conversation_history
        )
        
        # 创建等待事件
        import threading
        event = threading.Event()
        self.pending_requests[request_id] = {
            "event": event,
            "response": None
        }
        
        # 等待响应（最多30秒）
        if event.wait(timeout=30):
            response_data = self.pending_requests[request_id]["response"]
            # 清理等待记录
            del self.pending_requests[request_id]
            
            if "error" in response_data:
                return {"error": response_data["error"]}
            
            # 添加AI回复到对话历史
            ai_response = response_data["response"]
            if "content" in ai_response:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": ai_response["content"]
                })
                return {"response": ai_response["content"]}
            else:
                return {"error": "AI响应格式错误"}
        else:
            # 超时处理
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            return {"error": "请求超时"}

def create_plugin(api_registry=None):
    """创建插件实例的工厂函数"""
    try:
        plugin_instance = CopilotPlugin(api_registry)
        return plugin_instance
    except Exception as e:
        error_msg = f"创建Copilot插件实例失败: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        # 创建一个空实例以防止崩溃
        class EmptyPlugin:
            def __init__(self, api_registry=None):
                self.name = "Copilot"
                self.version = "1.0.0"
                
            def start(self):
                print("插件启动失败")
                return False
                
            def stop(self):
                print("插件停止")
                
        return EmptyPlugin()

def start_plugin(api_registry, plugin_loader):
    """插件入口函数"""
    try:
        print("正在创建Copilot插件实例...")
        # 创建插件实例并启动
        plugin = create_plugin(api_registry)
        if not hasattr(plugin, 'start'):
            print("错误: 创建的插件实例没有start方法")
            return False
            
        print("Copilot插件实例创建成功，正在启动...")
        success = plugin.start()
        if success:
            print("Copilot插件启动成功")
        else:
            print("Copilot插件启动失败")
        return success
    except Exception as e:
        error_msg = f"Copilot插件启动失败: {e}"
        print(error_msg)
        import traceback
        traceback.print_exc()
        return False

# 导出插件信息
PLUGIN_NAME = "Copilot"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DEVELOPER = "Kaos Team"
PLUGIN_DESCRIPTION = "AI助手插件，提供智能对话功能"