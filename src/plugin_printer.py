import sys
import threading
import builtins
from contextlib import contextmanager
from src.logger import get_logger

# 保存原始print函数
_original_print = builtins.print
logger = get_logger()

class PluginPrinter:
    """插件打印处理器，用于在插件print输出前添加插件名称前缀"""
    
    _local = threading.local()
    
    @classmethod
    def set_current_plugin(cls, plugin_name):
        """设置当前插件名称"""
        cls._local.current_plugin = plugin_name
    
    @classmethod
    def get_current_plugin(cls):
        """获取当前插件名称"""
        return getattr(cls._local, 'current_plugin', None)
    
    @classmethod
    def print(cls, *args, **kwargs):
        """带插件前缀的print函数"""
        plugin_name = cls.get_current_plugin()
        if plugin_name:
            # 构造带插件前缀的消息
            message = ' '.join(str(arg) for arg in args)
            # 使用logger记录INFO级别日志，这样会自动添加时间戳和插件名称
            logger.info(message, plugin_name=plugin_name)
        else:
            # 没有插件上下文时使用原始print
            _original_print(*args, **kwargs)

# 上下文管理器，用于设置插件上下文
@contextmanager
def plugin_context(plugin_name):
    """插件执行上下文管理器"""
    # 设置当前插件名称
    PluginPrinter.set_current_plugin(plugin_name)
    # 临时替换print函数
    builtins.print = PluginPrinter.print
    try:
        yield
    finally:
        # 恢复原始print函数
        builtins.print = _original_print
        # 清除当前插件名称
        PluginPrinter.set_current_plugin(None)