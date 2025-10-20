from src.file_api import FileAPI

class APIRegistry:
    def __init__(self):
        self.apis = {}
        # 初始化时注册系统级API
        self._register_system_apis()

    def _register_system_apis(self):
        """
        注册系统级API，如文件操作API
        """
        # 文件操作API
        self.register_api("System", "read_file", FileAPI.read_file, show_output=False)
        self.register_api("System", "write_file", FileAPI.write_file, show_output=False)
        self.register_api("System", "edit_file", FileAPI.edit_file, show_output=False)
        self.register_api("System", "append_file", FileAPI.append_file, show_output=False)

    def register_api(self, plugin_name, api_name, api_function, show_output=True):
        """
        注册API接口
        :param plugin_name: 插件名称
        :param api_name: API名称
        :param api_function: API函数
        :param show_output: 是否显示注册信息，默认为True
        """
        if plugin_name not in self.apis:
            self.apis[plugin_name] = {}
        
        self.apis[plugin_name][api_name] = api_function
        if show_output:
            print(f"API registered: {plugin_name}.{api_name}")

    def get_api(self, plugin_name, api_name):
        if plugin_name in self.apis and api_name in self.apis[plugin_name]:
            return self.apis[plugin_name][api_name]
        return None

    def list_apis(self, plugin_name=None):
        if plugin_name:
            if plugin_name in self.apis:
                return list(self.apis[plugin_name].keys())
            else:
                return []
        else:
            return self.apis

# 全局API注册表实例
api_registry = APIRegistry()