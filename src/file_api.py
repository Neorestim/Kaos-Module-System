import os

class FileAPI:
    @staticmethod
    def read_file(file_path):
        """
        读取文件内容
        :param file_path: 文件路径
        :return: 文件内容字符串，如果出错则返回None
        """
        try:
            # 确保文件路径在kaos目录范围内
            abs_path = os.path.abspath(file_path)
            base_path = os.path.abspath(os.path.dirname(__file__) + "/../")
            if not abs_path.startswith(base_path):
                raise PermissionError("不允许访问kaos目录外的文件")
                
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"读取文件失败 {file_path}: {e}")
            return None

    @staticmethod
    def write_file(file_path, content):
        """
        写入文件内容
        :param file_path: 文件路径
        :param content: 要写入的内容
        :return: 成功返回True，失败返回False
        """
        try:
            # 确保文件路径在kaos目录范围内
            abs_path = os.path.abspath(file_path)
            base_path = os.path.abspath(os.path.dirname(__file__) + "/../")
            if not abs_path.startswith(base_path):
                raise PermissionError("不允许访问kaos目录外的文件")
                
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            print(f"写入文件失败 {file_path}: {e}")
            return False

    @staticmethod
    def edit_file(file_path, old_content, new_content):
        """
        编辑文件内容，替换指定内容
        :param file_path: 文件路径
        :param old_content: 要替换的旧内容
        :param new_content: 新内容
        :return: 成功返回True，失败返回False
        """
        try:
            # 读取文件
            content = FileAPI.read_file(file_path)
            if content is None:
                return False
            
            # 替换内容
            updated_content = content.replace(old_content, new_content)
            
            # 写入文件
            return FileAPI.write_file(file_path, updated_content)
        except Exception as e:
            print(f"编辑文件失败 {file_path}: {e}")
            return False

    @staticmethod
    def append_file(file_path, content):
        """
        向文件追加内容
        :param file_path: 文件路径
        :param content: 要追加的内容
        :return: 成功返回True，失败返回False
        """
        try:
            # 确保文件路径在kaos目录范围内
            abs_path = os.path.abspath(file_path)
            base_path = os.path.abspath(os.path.dirname(__file__) + "/../")
            if not abs_path.startswith(base_path):
                raise PermissionError("不允许访问kaos目录外的文件")
                
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'a', encoding='utf-8') as file:
                file.write(content)
            return True
        except Exception as e:
            print(f"追加文件失败 {file_path}: {e}")
            return False