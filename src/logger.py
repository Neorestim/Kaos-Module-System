import os
import sys
import datetime
import threading
import builtins
from typing import Optional
from src.config_manager import get_config_manager

# 保存原始print函数
_original_print = builtins.print

class Logger:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Logger, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.log_directory = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        self.log_file = None
        self.console_level = 'INFO'
        self.file_level = 'INFO'
        self.max_files = 30
        
        # 从配置管理器获取日志级别设置
        config_manager = get_config_manager()
        console_level, file_level = config_manager.get_log_levels()
        self.console_level = console_level
        self.file_level = file_level
        
        # 确保日志目录存在
        if not os.path.exists(self.log_directory):
            os.makedirs(self.log_directory)
        
        # 初始化日志文件
        self._init_log_file()
        
        # 启动日志清理任务
        self._start_cleanup_task()
    
    def _init_log_file(self):
        """初始化日志文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d")
        log_filename = f"kaos_{timestamp}.log"
        self.log_file = os.path.join(self.log_directory, log_filename)
    
    def _start_cleanup_task(self):
        """启动日志清理任务"""
        self._cleanup_old_logs()
        # 每天清理一次旧日志（这里简化处理，实际项目中可能需要使用调度器）
    
    def _cleanup_old_logs(self):
        """清理旧日志文件"""
        try:
            if not os.path.exists(self.log_directory):
                return
                
            log_files = [f for f in os.listdir(self.log_directory) if f.endswith('.log')]
            log_files.sort(key=lambda x: os.path.getmtime(os.path.join(self.log_directory, x)))
            
            # 保留最新的max_files个文件
            if len(log_files) > self.max_files:
                files_to_delete = log_files[:-self.max_files]
                for file in files_to_delete:
                    try:
                        os.remove(os.path.join(self.log_directory, file))
                    except Exception:
                        pass
        except Exception:
            pass  # 忽略清理过程中的错误
    
    def _get_level_value(self, level: str) -> int:
        """获取日志级别的数值"""
        levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        return levels.get(level.upper(), 1)
    
    def _should_log(self, level: str, target_level: str) -> bool:
        """判断是否应该记录日志"""
        return self._get_level_value(level) >= self._get_level_value(target_level)
    
    def _format_message(self, level: str, message: str, plugin_name: Optional[str] = None) -> str:
        """格式化日志消息"""
        timestamp = datetime.datetime.now().strftime("%m-%d %H:%M:%S")
        if plugin_name:
            return f"{timestamp} [{plugin_name}] {level}: {message}"
        else:
            return f"{timestamp} [core] {level}: {message}"
    
    def _write_to_file(self, formatted_message: str):
        """写入日志文件"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(formatted_message + '\n')
        except Exception:
            pass  # 忽略文件写入错误
    
    def _write_to_console(self, formatted_message: str):
        """写入控制台"""
        _original_print(formatted_message)
    
    def log(self, level: str, message: str, plugin_name: Optional[str] = None):
        """记录日志"""
        # 格式化消息
        formatted_message = self._format_message(level, message, plugin_name)
        
        # 写入文件（如果级别足够）
        if self._should_log(level, self.file_level):
            self._write_to_file(formatted_message)
        
        # 写入控制台（如果级别足够）
        if self._should_log(level, self.console_level):
            self._write_to_console(formatted_message)
    
    def debug(self, message: str, plugin_name: Optional[str] = None):
        """记录DEBUG级别日志"""
        self.log('DEBUG', message, plugin_name)
    
    def info(self, message: str, plugin_name: Optional[str] = None):
        """记录INFO级别日志"""
        self.log('INFO', message, plugin_name)
    
    def warning(self, message: str, plugin_name: Optional[str] = None):
        """记录WARNING级别日志"""
        self.log('WARNING', message, plugin_name)
    
    def error(self, message: str, plugin_name: Optional[str] = None):
        """记录ERROR级别日志"""
        self.log('ERROR', message, plugin_name)
    
    def critical(self, message: str, plugin_name: Optional[str] = None):
        """记录CRITICAL级别日志"""
        self.log('CRITICAL', message, plugin_name)
    
    def set_levels(self, console_level: str = 'INFO', file_level: str = 'INFO'):
        """设置日志级别"""
        self.console_level = console_level.upper()
        self.file_level = file_level.upper()

# 全局日志实例
logger = Logger()

def get_logger():
    """获取全局日志实例"""
    return logger