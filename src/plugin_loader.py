import os
import json
import importlib.util
from src.api_registry import api_registry
from src.logger import get_logger

# 获取全局日志实例
logger = get_logger()

class PluginLoader:
    def __init__(self, plugins_dir):
        self.plugins_dir = plugins_dir
        self.plugins = []

    def load_plugins(self):
        if not os.path.exists(self.plugins_dir):
            logger.warning(f"Plugins directory {self.plugins_dir} does not exist.")
            return

        # 收集所有插件信息
        plugin_infos = []
        for item in os.listdir(self.plugins_dir):
            plugin_dir = os.path.join(self.plugins_dir, item)
            if os.path.isdir(plugin_dir):
                manifest_path = os.path.join(plugin_dir, '_manifest.json')
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                        if self.validate_manifest(manifest):
                            plugin_infos.append({
                                'dir': plugin_dir,
                                'manifest': manifest,
                                'dependencies': manifest.get('dependencies', [])
                            })
                    except Exception as e:
                        logger.error(f"Failed to read manifest in {plugin_dir}: {e}")

        # 按依赖关系排序插件
        sorted_plugins = self._sort_plugins_by_dependencies(plugin_infos)
        
        # 按排序后的顺序加载插件
        for plugin_info in sorted_plugins:
            self.load_plugin_from_dir(plugin_info['dir'])

    def _sort_plugins_by_dependencies(self, plugin_infos):
        """
        根据依赖关系对插件进行排序，确保依赖的插件先加载
        :param plugin_infos: 插件信息列表
        :return: 排序后的插件信息列表
        """
        # 创建插件名称到插件信息的映射
        plugin_map = {info['manifest']['pluginName']: info for info in plugin_infos}
        
        # 使用拓扑排序对插件进行排序
        sorted_plugins = []
        visited = set()
        temp_visited = set()
        
        def visit(plugin_info):
            plugin_name = plugin_info['manifest']['pluginName']
            
            # 如果已经访问过，直接返回
            if plugin_name in visited:
                return
            
            # 如果在临时访问集合中，说明存在循环依赖
            if plugin_name in temp_visited:
                logger.warning(f"检测到插件 {plugin_name} 存在循环依赖")
                return
            
            # 标记为临时访问
            temp_visited.add(plugin_name)
            
            # 递归访问所有依赖的插件
            for dep in plugin_info['dependencies']:
                if dep in plugin_map:
                    visit(plugin_map[dep])
                else:
                    logger.warning(f"插件 {plugin_name} 依赖的插件 {dep} 不存在")
            
            # 标记为已访问并添加到结果中
            temp_visited.remove(plugin_name)
            visited.add(plugin_name)
            sorted_plugins.append(plugin_info)
        
        # 对所有插件进行拓扑排序
        for plugin_info in plugin_infos:
            if plugin_info['manifest']['pluginName'] not in visited:
                visit(plugin_info)
        
        return sorted_plugins

    def load_plugin_from_dir(self, plugin_dir):
        # Check for manifest file
        manifest_path = os.path.join(plugin_dir, '_manifest.json')
        if not os.path.exists(manifest_path):
            logger.warning(f"Manifest file not found in {plugin_dir}")
            return

        # Load and validate manifest
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
            if not self.validate_manifest(manifest):
                logger.warning(f"Invalid manifest in {plugin_dir}")
                return
        except Exception as e:
            logger.error(f"Failed to read manifest in {plugin_dir}: {e}")
            return

        # Check dependencies (已通过排序确保依赖项已加载)
        if 'dependencies' in manifest:
            for dep in manifest['dependencies']:
                if not self.check_dependency(dep):
                    logger.warning(f"未检测到注明的依赖模块 {dep}，该模块可能无法运行")
                    return

        # Load plugin module
        plugin_py_path = os.path.join(plugin_dir, 'plugin.py')
        if not os.path.exists(plugin_py_path):
            logger.warning(f"plugin.py not found in {plugin_dir}")
            return

        try:
            spec = importlib.util.spec_from_file_location(manifest['pluginName'], plugin_py_path)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            
            # Add api_registry to plugin module so it can register its APIs
            plugin_module.api_registry = api_registry
            
            self.plugins.append({
                'manifest': manifest,
                'module': plugin_module
            })
        except Exception as e:
            logger.error(f"Failed to load plugin {plugin_dir}: {e}")

    def check_dependency(self, dependency_name):
        # Check if dependency plugin is already loaded
        for plugin in self.plugins:
            if plugin['manifest']['pluginName'] == dependency_name:
                return True
        # Also check if dependency exists in plugin directory
        for item in os.listdir(self.plugins_dir):
            plugin_dir = os.path.join(self.plugins_dir, item)
            if os.path.isdir(plugin_dir):
                manifest_path = os.path.join(plugin_dir, '_manifest.json')
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                        if manifest.get('pluginName') == dependency_name:
                            return True
                    except:
                        continue
        return False

    def validate_manifest(self, manifest):
        # Required fields based on the example
        required_fields = ['version', 'pluginName', 'Developer', 'Permission', 'InstallationLevel']
        for field in required_fields:
            if field not in manifest:
                logger.warning(f"Missing required field in manifest: {field}")
                return False

        # Validate permission level
        valid_permissions = ['System', 'User', 'Visitor']
        if manifest['Permission'] not in valid_permissions:
            logger.warning(f"Invalid permission level in manifest: {manifest['Permission']}")
            return False

        # Validate installation level
        valid_installation_levels = ['Admin', 'Normal']
        if manifest['InstallationLevel'] not in valid_installation_levels:
            logger.warning(f"Invalid installation level in manifest: {manifest['InstallationLevel']}")
            return False

        return True

    def get_plugins(self):
        return self.plugins