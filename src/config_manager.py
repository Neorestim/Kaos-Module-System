import os
import json
from typing import Dict, Any

class ConfigManager:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), config_dir)
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.config = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                # 如果配置文件不存在，创建默认配置
                self._create_default_config()
        except Exception as e:
            print(f"警告: 无法加载配置文件: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """创建默认配置"""
        self.config = {
            "version": "0.11.0-snapshot.3",
            "log": {
                "console_level": "INFO",
                "file_level": "INFO"
            }
        }
        self._save_config()
    
    def _save_config(self):
        """保存配置文件"""
        try:
            # 确保配置目录存在
            if not os.path.exists(self.config_dir):
                os.makedirs(self.config_dir)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"警告: 无法保存配置文件: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        keys = key.split('.')
        value = self.config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """设置配置项"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self._save_config()
    
    def get_version(self) -> str:
        """获取当前版本"""
        return self.get("version", "0.0.0")
    
    def get_log_levels(self) -> tuple:
        """获取日志级别设置"""
        console_level = self.get("log.console_level", "INFO")
        file_level = self.get("log.file_level", "INFO")
        return console_level, file_level
    
    def set_log_levels(self, console_level: str = None, file_level: str = None):
        """设置日志级别"""
        if console_level is not None:
            self.set("log.console_level", console_level)
        if file_level is not None:
            self.set("log.file_level", file_level)

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config_manager():
    """获取全局配置管理器实例"""
    return config_manager