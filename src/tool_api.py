import subprocess
import os

def run_tool_command(command: str, timeout: int = 30) -> dict:
    """
    执行命令行工具（如模型推理、脚本等），返回结果。
    :param command: 要执行的命令字符串
    :param timeout: 超时时间（秒）
    :return: {'success': bool, 'output': str, 'error': str}
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout)
        return {
            'success': result.returncode == 0,
            'output': result.stdout.strip(),
            'error': result.stderr.strip()
        }
    except Exception as e:
        return {
            'success': False,
            'output': '',
            'error': str(e)
        }

# 注册到系统API（在api_registry初始化时调用）
from src.api_registry import api_registry
api_registry.register_api('System', 'run_tool_command', run_tool_command)
