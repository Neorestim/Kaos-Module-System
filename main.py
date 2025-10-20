import os
import time
import signal
import sys
import json
import threading
import subprocess
import importlib.util
from src.plugin_loader import PluginLoader
from src.logger import get_logger
from src.config_manager import get_config_manager

# 获取全局日志实例和配置管理器
logger = get_logger()
config_manager = get_config_manager()

# 全局变量用于控制程序运行状态
running = True
restart_requested = False

def signal_handler(sig, frame):
    global running
    logger.info("\n正在退出Kaos...")
    running = False
    sys.exit(0)

def restart_program():
    """重启程序"""
    global running, restart_requested
    logger.info("\n正在重启Kaos...")
    running = False
    restart_requested = True
    # 清理实例文件
    instance_file = os.path.join(os.path.dirname(__file__), '.kaos_instance')
    cleanup_instance_file(instance_file)
    # 重新启动程序
    python = sys.executable
    os.execl(python, python, *sys.argv)

def check_and_install_dependencies():
    """检查并安装必要的依赖"""
    required_packages = [
        'toml',  # 用于解析TOML配置文件
        'requests'  # 用于HTTP请求
    ]
    
    missing_packages = []
    
    # 检查每个包是否已安装
    for package in required_packages:
        if not is_package_installed(package):
            missing_packages.append(package)
    
    # 如果有缺失的包，则安装它们
    if missing_packages:
        logger.info(f"检测到缺失的依赖包: {', '.join(missing_packages)}")
        logger.info("正在自动安装缺失的依赖...")
        
        try:
            # 使用pip安装缺失的包
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', '--user'
            ] + missing_packages)
            
            logger.info("依赖安装完成!")
            
            # 重新检查安装结果
            still_missing = []
            for package in missing_packages:
                if not is_package_installed(package):
                    still_missing.append(package)
            
            if still_missing:
                logger.warning(f"以下包可能安装失败: {', '.join(still_missing)}")
                logger.warning("某些功能可能无法正常工作")
            else:
                logger.info("所有依赖均已成功安装")
                
        except subprocess.CalledProcessError as e:
            logger.error(f"安装依赖时出错: {e}")
            logger.warning("某些功能可能无法正常工作")
        except Exception as e:
            logger.error(f"安装依赖时发生未知错误: {e}")
            logger.warning("某些功能可能无法正常工作")

def is_package_installed(package_name):
    """检查包是否已安装"""
    try:
        importlib.util.find_spec(package_name)
        return True
    except ImportError:
        return False

def check_restart_key():
    """检查Ctrl+R组合键"""
    global restart_requested
    try:
        import msvcrt
        logger.info("键盘监听已启动，按Ctrl+R可重启程序")
        while running and not restart_requested:
            try:
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # 检查Ctrl+R组合键 (Ctrl+R对应的ASCII码是18)
                    if ord(key) == 18:  # Ctrl+R
                        logger.info("检测到Ctrl+R组合键，正在重启程序...")
                        restart_requested = True
                        restart_program()
                        break
                time.sleep(0.05)  # 减少延迟以提高响应性
            except Exception as e:
                logger.warning(f"键盘监听循环中出现异常: {e}")
                time.sleep(0.1)  # 出现异常时稍作延迟
    except ImportError:
        # 非Windows系统使用keyboard库
        try:
            import keyboard
            keyboard.add_hotkey('ctrl+r', restart_program)
            logger.info("键盘监听已启动（使用keyboard库），按Ctrl+R可重启程序")
            keyboard.wait()
        except ImportError:
            logger.warning("未安装keyboard库，无法使用Ctrl+R重启功能")
    except Exception as e:
        logger.warning(f"键盘监听出现异常: {e}")

def manage_multiple_instances():
    """管理多个kaos实例，确保只保留最后一个实例"""
    # 创建一个临时文件来标识当前实例
    instance_file = os.path.join(os.path.dirname(__file__), '.kaos_instance')
    
    # 检查是否已存在实例文件
    if os.path.exists(instance_file):
        try:
            # 读取现有实例文件中的PID
            with open(instance_file, 'r') as f:
                existing_pids = f.read().strip().split('\n')
            
            # 通知所有现有实例退出
            current_pid = str(os.getpid())
            new_pids = []
            
            for pid in existing_pids:
                if pid and pid != current_pid:
                    try:
                        # 在Windows上使用taskkill命令终止进程
                        os.system(f"taskkill /F /PID {pid} >nul 2>&1")
                        print(f"10-19 22:48:37 [主程序] 已通知PID {pid} 的kaos实例退出")
                    except Exception:
                        pass  # 进程可能已经退出
                else:
                    new_pids.append(pid)
            
            # 添加当前PID到列表中
            new_pids.append(current_pid)
            
            # 更新实例文件
            with open(instance_file, 'w') as f:
                f.write('\n'.join(new_pids))
                
        except Exception as e:
            # 如果读取失败，创建新的实例文件
            with open(instance_file, 'w') as f:
                f.write(str(os.getpid()))
    else:
        # 创建新的实例文件
        with open(instance_file, 'w') as f:
            f.write(str(os.getpid()))
    
    return instance_file

def cleanup_instance_file(instance_file):
    """清理实例文件"""
    if instance_file and os.path.exists(instance_file):
        try:
            # 从文件中移除当前PID
            current_pid = str(os.getpid())
            if os.path.exists(instance_file):
                with open(instance_file, 'r') as f:
                    pids = f.read().strip().split('\n')
                
                # 过滤掉当前PID
                new_pids = [pid for pid in pids if pid and pid != current_pid]
                
                if new_pids:
                    # 如果还有其他PID，写回文件
                    with open(instance_file, 'w') as f:
                        f.write('\n'.join(new_pids))
                else:
                    # 如果没有其他PID，删除文件
                    os.remove(instance_file)
        except Exception:
            pass

def format_loading_message(plugin_loader):
    logger.info("欢迎使用Kaos系统！")
    logger.info("已成功加载环境变量配置")
    logger.info("已启动日志清理任务，将自动清理30天前的日志文件（轮转份数限制: 30个文件）")
    logger.info("日志系统已初始化:")
    logger.info("  - 控制台级别: INFO")
    logger.info("  - 文件级别: INFO")
    logger.info("  - 轮转份数: 30个文件|自动清理: 30天前的日志")
    
    # 从配置管理器获取版本信息
    version = config_manager.get_version()
    logger.info(f"KaosCore当前版本: {version}")
    
    logger.info("数据库初始化完成")
    logger.info("插件管理器初始化完成")
    logger.info("API统一平台初始化完成")
    logger.info("检查EULA和隐私条款完成")
    logger.info("正在唤醒Kaos......")
    
    plugins = plugin_loader.get_plugins()
    
    # 校验插件manifest
    valid_plugins = []
    for plugin in plugins:
        manifest = plugin['manifest']
        # 使用PluginLoader的validate_manifest方法校验
        if plugin_loader.validate_manifest(manifest):
            valid_plugins.append(plugin)
        else:
            logger.warning(f"插件 {manifest['pluginName']} 的manifest校验失败，跳过加载")
    
    enabled_plugins = [p for p in valid_plugins if p]  # 这里简化处理，实际可能需要检查插件是否启用
    disabled_plugins_count = len(valid_plugins) - len(enabled_plugins)
    
    logger.info("🎉 插件系统加载完成!")
    logger.info(f"📊 总览: {len(enabled_plugins)}个插件")
    logger.info("📋 已加载插件详情:")
    
    for i, plugin in enumerate(enabled_plugins):
        manifest = plugin['manifest']
        logger.info(f"✅ 插件加载成功: {manifest['pluginName']} v{manifest['version']} () - {manifest['Developer']}")
        # 调用插件的启动函数
        if hasattr(plugin['module'], 'start_plugin'):
            try:
                logger.info(f"🚀 正在启动插件: {manifest['pluginName']}")
                # 从插件模块中获取api_registry对象
                api_registry = getattr(plugin['module'], 'api_registry', None)
                
                # 使用插件上下文管理器，使插件的print函数带前缀
                from src.plugin_printer import plugin_context
                with plugin_context(manifest['pluginName']):
                    plugin['module'].start_plugin(api_registry, plugin_loader)
                
                logger.info(f"✅ 插件 {manifest['pluginName']} 启动完成")
            except Exception as e:
                logger.error(f"插件 {manifest['pluginName']} 启动失败: {e}")
        else:
            logger.warning(f"插件 {manifest['pluginName']} 没有start_plugin函数")
    
    logger.info("-" * 32)
    logger.info("全部系统初始化完成，监听已启动，Kaos正常运作中~")
    logger.info("-" * 32)

def check_eula_agreement():
    """检查用户是否已同意EULA和隐私条款"""
    agreement_file = os.path.join(os.path.dirname(__file__), '.eula_agreed')
    return os.path.exists(agreement_file)

def show_eula_and_privacy_policy():
    """显示EULA和隐私条款并请求用户同意"""
    eula_file = os.path.join(os.path.dirname(__file__), 'EULA.md')
    privacy_file = os.path.join(os.path.dirname(__file__), 'PrivacyPolicy.txt')
    
    print("=" * 50)
    print("Kaos 最终用户许可协议和隐私条款")
    print("=" * 50)
    
    # 显示EULA
    if os.path.exists(eula_file):
        print("\n最终用户许可协议 (EULA):\n")
        with open(eula_file, 'r', encoding='utf-8') as f:
            print(f.read())
    
    # 显示隐私条款
    if os.path.exists(privacy_file):
        print("\n隐私条款:\n")
        with open(privacy_file, 'r', encoding='utf-8') as f:
            print(f.read())
    
    print("=" * 50)
    print("请仔细阅读以上条款。使用本软件表示您同意这些条款。")
    
    # 请求用户同意
    while True:
        response = input("\n您同意以上条款吗？(输入 'yes' 表示同意，'no' 表示不同意): ").strip().lower()
        if response == 'yes':
            # 创建同意文件
            agreement_file = os.path.join(os.path.dirname(__file__), '.eula_agreed')
            with open(agreement_file, 'w') as f:
                f.write("User agreed to EULA and Privacy Policy on " + time.strftime("%Y-%m-%d %H:%M:%S"))
            print("感谢您的同意！现在将启动Kaos系统。")
            return True
        elif response == 'no':
            print("您必须同意最终用户许可协议和隐私条款才能使用本软件。")
            print("程序将退出。")
            return False
        else:
            print("请输入 'yes' 或 'no'。")

if __name__ == "__main__":
    # 注册信号处理器以实现优雅退出
    signal.signal(signal.SIGINT, signal_handler)
    
    # 管理多个kaos实例
    instance_file = manage_multiple_instances()
    
    # 确保在程序退出时清理实例文件
    import atexit
    atexit.register(cleanup_instance_file, instance_file)
    
    # 检查EULA和隐私条款同意情况
    if not check_eula_agreement():
        if not show_eula_and_privacy_policy():
            cleanup_instance_file(instance_file)
            sys.exit(0)
    
    # 检查并安装必要的依赖
    check_and_install_dependencies()
    
    # Load plugins
    plugins_dir = os.path.join(os.path.dirname(__file__), 'plugins')
    plugin_loader = PluginLoader(plugins_dir)
    plugin_loader.load_plugins()
    
    # Display formatted loading message
    format_loading_message(plugin_loader)
    
    # 启动键盘监听线程
    keyboard_thread = threading.Thread(target=check_restart_key, daemon=True)
    keyboard_thread.start()
    
    logger.info("\nKaos 正在运行中... 按 Ctrl+C 退出, 按 Ctrl+R 重启")
    
    # 持续运行循环
    try:
        while running and not restart_requested:
            try:
                # 每隔1秒检查一次运行状态
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n正在退出Kaos...")
                break
    except Exception as e:
        logger.error(f"\nKaos发生未处理的异常: {e}")
        logger.info("按回车键退出或按Ctrl+R重启...")
        try:
            import msvcrt
            start_time = time.time()
            while True:
                # 检查是否超时（30秒后自动退出）
                if time.time() - start_time > 30:
                    logger.info("超时自动退出")
                    break
                    
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    # 检查Ctrl+R组合键 (Ctrl+R对应的ASCII码是18)
                    if ord(key) == 18:  # Ctrl+R
                        restart_requested = True
                        restart_program()
                        break
                    # 检查回车键
                    elif ord(key) == 13:  # Enter
                        break
                time.sleep(0.05)  # 减少延迟以提高响应性
        except ImportError:
            # 非Windows系统
            input("按回车键退出...")
        except Exception as e:
            logger.warning(f"异常处理中的键盘监听出现错误: {e}")
    finally:
        # 清理实例文件
        cleanup_instance_file(instance_file)
    
    if restart_requested:
        logger.info("Kaos 正在重启...")
        # 重新启动程序
        python = sys.executable
        os.execl(python, python, *sys.argv)
    else:
        logger.info("Kaos 已退出")