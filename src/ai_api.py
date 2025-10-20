import os
import json
import requests
import threading
import time
import toml
from typing import Dict, Any, Callable, Optional, List
from src.logger import get_logger

logger = get_logger()

class AIProvider:
    """AI提供商基类"""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = config.get('name', '')
        self.api_key = config.get('api_key', '')
        self.base_url = config.get('base_url', '')
        self.client_type = config.get('client_type', 'openai')
        self.max_retry = config.get('max_retry', 2)
        self.timeout = config.get('timeout', 120)
        self.retry_interval = config.get('retry_interval', 10)
    
    def send_request(self, messages: list, tools: Optional[list] = None, model_identifier: str = "") -> Dict[str, Any]:
        """发送请求到AI模型"""
        raise NotImplementedError("子类必须实现send_request方法")
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析AI模型的响应"""
        raise NotImplementedError("子类必须实现parse_response方法")

class OpenAIProvider(AIProvider):
    """OpenAI提供商实现"""
    def send_request(self, messages: list, tools: Optional[list] = None, model_identifier: str = "") -> Dict[str, Any]:
        """发送请求到OpenAI模型"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model_identifier,
            "messages": messages,
        }
        
        # 添加额外参数
        extra_params = self.config.get('extra_params', {})
        if 'temperature' in extra_params:
            payload["temperature"] = extra_params['temperature']
        if 'max_tokens' in extra_params:
            payload["max_tokens"] = extra_params['max_tokens']
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        
        # 重试机制
        for attempt in range(self.max_retry + 1):
            try:
                url = f"{self.base_url}/chat/completions"
                logger.debug(f"发送OpenAI请求到: {url}")
                logger.debug(f"请求载荷: {payload}")
                
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # 检查响应内容是否为空
                response_text = response.text
                logger.debug(f"收到响应，长度: {len(response_text)} 字符")
                
                if not response_text or response_text.strip() == '':
                    raise ValueError("API返回空响应")
                
                # 检查是否是HTML响应
                if response_text.strip().startswith('<!doctype') or response_text.strip().startswith('<html'):
                    logger.error(f"OpenAI API返回HTML页面而不是JSON响应，这通常是URL错误或服务不可用")
                    logger.error(f"响应内容预览: {response_text[:200]}...")
                    raise ValueError("API返回HTML页面而不是JSON响应")
                
                # 尝试解析JSON
                try:
                    response_json = response.json()
                    logger.debug(f"成功解析JSON响应")
                    return response_json
                except ValueError as e:
                    logger.error(f"OpenAI API返回非JSON格式响应: {response_text[:500]}")  # 只记录前500个字符
                    raise e
                
            except Exception as e:
                if attempt < self.max_retry:
                    logger.warning(f"OpenAI请求失败，{self.retry_interval}秒后重试 (尝试 {attempt + 1}/{self.max_retry + 1}): {e}")
                    time.sleep(self.retry_interval)
                else:
                    logger.error(f"OpenAI请求失败: {e}")
                    return {"error": str(e)}
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析OpenAI模型的响应"""
        if "error" in response:
            return response
        
        try:
            # 检查响应是否包含选择项
            if "choices" not in response or not response["choices"]:
                return {"error": "OpenAI API返回无选择项的响应"}
            
            choice = response["choices"][0]
            
            # 检查消息是否存在
            if "message" not in choice:
                return {"error": "OpenAI API返回格式错误的响应"}
            
            message = choice["message"]
            
            result = {
                "content": message.get("content", ""),
                "role": message.get("role", "assistant")
            }
            
            # 处理工具调用
            if "tool_calls" in message:
                result["tool_calls"] = message["tool_calls"]
            
            return result
        except KeyError as e:
            logger.error(f"解析OpenAI响应时缺少必要字段: {e}")
            return {"error": f"解析响应失败，缺少字段: {e}"}
        except Exception as e:
            logger.error(f"解析OpenAI响应失败: {e}")
            return {"error": f"解析响应失败: {e}"}

class GeminiProvider(AIProvider):
    """Gemini提供商实现"""
    def send_request(self, messages: list, tools: Optional[list] = None, model_identifier: str = "") -> Dict[str, Any]:
        """发送请求到Gemini模型"""
        # 转换消息格式为Gemini格式
        gemini_messages = []
        for msg in messages:
            if msg["role"] == "system":
                # Gemini没有system角色，将其添加到第一个user消息前
                gemini_messages.append({
                    "role": "user",
                    "parts": [{"text": f"[System Message] {msg['content']}"}]
                })
            else:
                gemini_messages.append({
                    "role": msg["role"],
                    "parts": [{"text": msg["content"]}]
                })
        
        payload = {
            "contents": gemini_messages,
        }
        
        # 添加额外参数
        extra_params = self.config.get('extra_params', {})
        if 'temperature' in extra_params:
            if 'generationConfig' not in payload:
                payload['generationConfig'] = {}
            payload['generationConfig']['temperature'] = extra_params['temperature']
        if 'max_tokens' in extra_params:
            if 'generationConfig' not in payload:
                payload['generationConfig'] = {}
            payload['generationConfig']['maxOutputTokens'] = extra_params['max_tokens']
        
        if tools:
            payload["tools"] = [{"functionDeclarations": tools}]
        
        # 重试机制
        for attempt in range(self.max_retry + 1):
            try:
                # 根据base_url格式确定正确的API端点
                if "/v1beta/" in self.base_url or self.base_url.endswith("/v1beta"):
                    # 标准Google API格式
                    url = f"{self.base_url}/models/{model_identifier}:generateContent?key={self.api_key}"
                elif "/v1/" in self.base_url or self.base_url.endswith("/v1"):
                    # OpenAI兼容格式（如果适用）
                    url = f"{self.base_url}/models/{model_identifier}:generateContent?key={self.api_key}"
                else:
                    # 中间商API格式，可能需要添加版本路径
                    if self.base_url.endswith("/"):
                        url = f"{self.base_url}v1beta/models/{model_identifier}:generateContent?key={self.api_key}"
                    else:
                        url = f"{self.base_url}/v1beta/models/{model_identifier}:generateContent?key={self.api_key}"
                
                logger.debug(f"发送Gemini请求到: {url}")
                logger.debug(f"请求载荷: {payload}")
                
                response = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                # 检查响应内容是否为空
                response_text = response.text
                logger.debug(f"收到响应，长度: {len(response_text)} 字符")
                
                if not response_text or response_text.strip() == '':
                    raise ValueError("API返回空响应")
                
                # 检查是否是HTML响应
                if response_text.strip().startswith('<!doctype') or response_text.strip().startswith('<html'):
                    logger.error(f"Gemini API返回HTML页面而不是JSON响应，这通常是URL错误或服务不可用")
                    logger.error(f"响应内容预览: {response_text[:200]}...")
                    raise ValueError("API返回HTML页面而不是JSON响应")
                
                # 尝试解析JSON
                try:
                    response_json = response.json()
                    logger.debug(f"成功解析JSON响应")
                    return response_json
                except ValueError as e:
                    logger.error(f"Gemini API返回非JSON格式响应: {response_text[:500]}")  # 只记录前500个字符
                    raise e
                
            except Exception as e:
                if attempt < self.max_retry:
                    logger.warning(f"Gemini请求失败，{self.retry_interval}秒后重试 (尝试 {attempt + 1}/{self.max_retry + 1}): {e}")
                    time.sleep(self.retry_interval)
                else:
                    logger.error(f"Gemini请求失败: {e}")
                    return {"error": str(e)}
    
    def parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析Gemini模型的响应"""
        if "error" in response:
            return response
        
        try:
            # 检查响应是否包含候选答案
            if "candidates" not in response or not response["candidates"]:
                return {"error": "Gemini API返回无候选答案的响应"}
            
            candidate = response["candidates"][0]
            
            # 检查内容是否存在
            if "content" not in candidate or "parts" not in candidate["content"]:
                return {"error": "Gemini API返回格式错误的响应"}
            
            content_parts = candidate["content"]["parts"]
            
            # 合并所有文本部分
            content_text = ""
            tool_calls = []
            
            for part in content_parts:
                if "text" in part:
                    content_text += part["text"]
                elif "functionCall" in part:
                    tool_calls.append({
                        "id": f"call_{int(time.time() * 1000000)}",
                        "type": "function",
                        "function": {
                            "name": part["functionCall"]["name"],
                            "arguments": json.dumps(part["functionCall"].get("args", {}))
                        }
                    })
            
            result = {
                "content": content_text,
                "role": "assistant"
            }
            
            if tool_calls:
                result["tool_calls"] = tool_calls
            
            return result
        except KeyError as e:
            logger.error(f"解析Gemini响应时缺少必要字段: {e}")
            return {"error": f"解析响应失败，缺少字段: {e}"}
        except Exception as e:
            logger.error(f"解析Gemini响应失败: {e}")
            return {"error": f"解析响应失败: {e}"}

class AIManager:
    """AI管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, config_path=None):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AIManager, cls).__new__(cls)
                    cls._instance._initialized = False
                    cls._instance._init_config_path = config_path
        return cls._instance
    
    def __init__(self, config_path=None):
        if self._initialized:
            return
        
        self._initialized = True
        # 使用初始化时传递的配置路径，或者使用__new__时保存的路径
        actual_config_path = config_path or getattr(self, '_init_config_path', None)
        self.config = self._load_config(actual_config_path)
        self.providers = {}
        self.models = {}
        self.model_task_config = {}
        
        # 初始化提供商
        self._init_providers()
        # 初始化模型
        self._init_models()
        # 初始化任务配置
        self._init_task_config()
        
        self.request_queue = []
        self.response_callbacks = {}
        self.message_listeners = []
    
    def _load_config(self, config_path=None) -> Dict[str, Any]:
        """加载配置文件"""
        # 如果提供了配置文件路径，优先使用
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    logger.info(f"加载配置文件: {config_path}")
                    return toml.load(f)
            except Exception as e:
                logger.error(f"加载配置文件 {config_path} 失败: {e}")
        
        # 默认配置文件路径
        config_paths = [
            "plugins/Copilot/config/model_config.toml",
            "model_config.toml"
        ]
        
        for path in config_paths:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    logger.info(f"加载配置文件: {path}")
                    return toml.load(f)
            except FileNotFoundError:
                continue
            except Exception as e:
                logger.error(f"加载配置文件 {path} 失败: {e}")
                continue
        
        logger.warning("未找到配置文件，使用默认配置")
        return {}
    
    def _init_providers(self):
        """初始化AI提供商"""
        api_providers = self.config.get("api_providers", [])
        for provider_config in api_providers:
            provider_name = provider_config.get("name")
            client_type = provider_config.get("client_type", "openai")
            
            if client_type == "openai":
                self.providers[provider_name] = OpenAIProvider(provider_config)
            elif client_type == "gemini":
                self.providers[provider_name] = GeminiProvider(provider_config)
            else:
                logger.warning(f"不支持的客户端类型: {client_type}")
    
    def _init_models(self):
        """初始化模型"""
        models = self.config.get("models", [])
        for model_config in models:
            model_name = model_config.get("name")
            self.models[model_name] = model_config
    
    def _init_task_config(self):
        """初始化任务配置"""
        self.model_task_config = self.config.get("model_task_config", {})
    
    def register_message_listener(self, listener: Callable[[str, Dict[str, Any]], None]):
        """注册消息监听器"""
        self.message_listeners.append(listener)
    
    def send_message(self, message_type: str, data: Dict[str, Any]):
        """发送消息给所有监听器"""
        for listener in self.message_listeners:
            try:
                listener(message_type, data)
            except Exception as e:
                logger.error(f"消息监听器处理失败: {e}")
    
    def send_request(self, model_name: str, messages: list, tools: Optional[list] = None, 
                     request_id: Optional[str] = None) -> str:
        """发送AI请求"""
        if request_id is None:
            request_id = f"req_{int(time.time() * 1000000)}"
        
        # 异步发送请求
        thread = threading.Thread(
            target=self._async_send_request,
            args=(model_name, messages, tools, request_id),
            daemon=True
        )
        thread.start()
        
        return request_id
    
    def _async_send_request(self, model_name: str, messages: list, tools: Optional[list], 
                            request_id: str):
        """异步发送AI请求"""
        try:
            # 查找模型配置
            if model_name not in self.models:
                error_msg = f"未找到模型: {model_name}"
                logger.error(error_msg)
                self.send_message("ai_response", {
                    "request_id": request_id,
                    "error": error_msg
                })
                return
            
            model_config = self.models[model_name]
            api_provider_name = model_config.get("api_provider")
            model_identifier = model_config.get("model_identifier")
            
            # 查找提供商
            if api_provider_name not in self.providers:
                error_msg = f"未找到API提供商: {api_provider_name}"
                logger.error(error_msg)
                self.send_message("ai_response", {
                    "request_id": request_id,
                    "error": error_msg
                })
                return
            
            provider = self.providers[api_provider_name]
            
            # 发送请求
            response = provider.send_request(messages, tools, model_identifier)
            
            # 解析响应
            parsed_response = provider.parse_response(response)
            
            # 发送响应消息
            self.send_message("ai_response", {
                "request_id": request_id,
                "model": model_name,
                "provider": api_provider_name,
                "response": parsed_response
            })
        except Exception as e:
            logger.error(f"AI请求处理失败: {e}")
            self.send_message("ai_response", {
                "request_id": request_id,
                "error": str(e)
            })
    
    def get_available_models(self) -> List[str]:
        """获取可用模型列表"""
        return list(self.models.keys())
    
    def get_model_for_task(self, task_type: str) -> Optional[str]:
        """根据任务类型获取推荐模型"""
        task_config = self.model_task_config.get(task_type, {})
        model_list = task_config.get("model_list", [])
        
        # 返回第一个可用模型
        for model_name in model_list:
            if model_name in self.models:
                return model_name
        
        # 如果没有找到任务特定模型，返回第一个可用模型
        if self.models:
            return list(self.models.keys())[0]
        
        return None

# 全局AI管理器实例
ai_manager = None

def get_ai_manager(config_path=None):
    """获取全局AI管理器实例"""
    global ai_manager
    if ai_manager is None:
        ai_manager = AIManager(config_path)
    elif config_path:
        # 如果AI管理器已经存在并且提供了新的配置路径，则重新加载配置
        ai_manager.config = ai_manager._load_config(config_path)
        ai_manager._init_providers()
        ai_manager._init_models()
        ai_manager._init_task_config()
    return ai_manager

def send_ai_request(model_name: str, messages: list, tools: Optional[list] = None, 
                    request_id: Optional[str] = None) -> str:
    """发送AI请求的便捷函数"""
    return ai_manager.send_request(model_name, messages, tools, request_id)

def register_ai_message_listener(listener: Callable[[str, Dict[str, Any]], None]):
    """注册AI消息监听器的便捷函数"""
    ai_manager.register_message_listener(listener)