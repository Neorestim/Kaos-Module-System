import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class WebInterfaceHandler(BaseHTTPRequestHandler):
    # 存储注册的菜单项
    registered_menu_items = []
    # 存储注册的插件内容
    registered_plugin_contents = []
    
    @classmethod
    def register_menu_item(cls, name, icon, view, callback=None):
        """注册菜单项到sidebar
        :param name: 菜单项名称
        :param icon: 图标类名 (Font Awesome)
        :param view: 视图标识符
        :param callback: 可选的回调函数
        """
        menu_item = {
            'name': name,
            'icon': icon,
            'view': view,
            'callback': callback
        }
        cls.registered_menu_items.append(menu_item)
    
    @classmethod
    def register_plugin_content(cls, plugin_name, content_type, content, position="body"):
        """注册插件内容到页面
        :param plugin_name: 插件名称
        :param content_type: 内容类型 ('html', 'css', 'js')
        :param content: 内容字符串
        :param position: 内容位置 ('head', 'body', 'footer')
        """
        plugin_content = {
            'plugin_name': plugin_name,
            'content_type': content_type,
            'content': content,
            'position': position
        }
        cls.registered_plugin_contents.append(plugin_content)
    
    def generate_menu_items(self):
        """生成菜单项HTML"""
        if not self.registered_menu_items:
            return '<!-- 功能区已清空 -->'
        
        menu_html = ''
        for i, item in enumerate(self.registered_menu_items):
            menu_html += f'''
            <div class="menu-item" data-view="{item['view']}" onclick="handleMenuItemClick('{item['view']}', event)">
                <i class="fas fa-{item['icon']}"></i>
                <span>{item['name']}</span>
            </div>
            '''
        return menu_html

    def serve_image(self):
        try:
            # 处理logo文件夹中的图片
            if self.path.startswith('/logo/'):
                image_name = self.path[6:]  # 去掉'/logo/'前缀
                image_path = os.path.join(os.path.dirname(__file__), '..', '..', 'logo', image_name)
            else:
                image_path = os.path.join(os.path.dirname(__file__), '..', '..', self.path[1:])
            
            with open(image_path, 'rb') as f:
                image_data = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'image/png')
            self.send_header('Content-Length', str(len(image_data)))
            self.end_headers()
            self.wfile.write(image_data)
        except Exception as e:
            self.send_error(404, "Image not found")

    def serve_plugins_api(self):
        plugins_info = self.get_plugins_info()
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(plugins_info, ensure_ascii=False).encode('utf-8'))

    def get_plugins_info(self):
        # 获取插件信息
        plugins_info = []
        if hasattr(self.server, 'plugin_loader'):
            for plugin in self.server.plugin_loader.get_plugins():
                manifest = plugin['manifest']
                plugins_info.append({
                    "name": manifest['pluginName'],
                    "developer": manifest['Developer'],
                    "version": manifest['version']
                })
        return plugins_info

    def get_plugin_contents_by_position(self, position, content_type):
        """根据位置和类型获取插件内容"""
        contents = []
        for plugin_content in self.registered_plugin_contents:
            if plugin_content['position'] == position and plugin_content['content_type'] == content_type:
                contents.append(plugin_content['content'])
        return '\n'.join(contents)
    
    def generate_plugin_cards(self, plugins_info):
        """生成插件卡片的HTML"""
        if not plugins_info:
            return '<p>暂无插件</p>'
        
        cards_html = ''
        for plugin in plugins_info:
            cards_html += f'''
                <div class="plugin-card">
                    <div class="plugin-name">{plugin['name']}</div>
                    <div class="plugin-developer"><i class="fas fa-user"></i> 开发者: {plugin['developer']}</div>
                    <div class="plugin-version"><i class="fas fa-code-branch"></i> 版本: {plugin['version']}</div>
                    <div class="plugin-description">这是一个强大的Kaos插件，提供丰富的功能和特性。</div>
                </div>
            '''
        return cards_html

    def do_GET(self):
        if self.path == '/':
            self.serve_html()
        elif self.path == '/api/plugins':
            self.serve_plugins_api()
        elif self.path.startswith('/logo/') or self.path.endswith('.png'):
            self.serve_image()
        else:
            self.send_error(404, "Page not found")

    def do_POST(self):
        # 处理API请求
        if self.path == '/api/plugins':
            self.serve_plugins_api()
        elif self.path.startswith('/api/copilot/'):
            self.serve_copilot_api()
        else:
            # 简单的POST处理示例
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status": "success"}')
    
    def serve_copilot_api(self):
        """处理Copilot API请求"""
        try:
            # 获取请求路径和方法
            api_method = self.path.split('/')[-1]
            
            # 读取请求数据
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            # 根据API方法处理请求
            if api_method == 'chat':
                # 处理聊天请求
                message = request_data.get('message', '')
                
                # 通过API注册表获取Copilot的聊天处理函数
                if hasattr(self, 'server') and hasattr(self.server, 'plugin_loader'):
                    # 获取API注册表
                    from src.api_registry import api_registry
                    
                    # 调用Copilot的聊天处理函数
                    handle_chat_func = api_registry.get_api("Copilot", "handle_chat")
                    if handle_chat_func:
                        response = handle_chat_func(message)
                        
                        # 发送响应
                        self.send_response(200)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps(response, ensure_ascii=False).encode('utf-8'))
                    else:
                        # Copilot聊天处理器未找到
                        self.send_response(404)
                        self.send_header('Content-type', 'application/json')
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Copilot聊天处理器未找到"}, ensure_ascii=False).encode('utf-8'))
                else:
                    # API注册表不可用
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "API注册表不可用"}, ensure_ascii=False).encode('utf-8'))
            else:
                # 未知API方法
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": "未知API方法"}, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            # 错误处理
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"error": f"处理请求时出错: {str(e)}"}
            self.wfile.write(json.dumps(error_response, ensure_ascii=False).encode('utf-8'))

    def serve_html(self):
        # 每次请求时动态获取最新的插件信息
        plugins_info = self.get_plugins_info()
        
        # 动态生成菜单项HTML
        menu_items_html = self.generate_menu_items()
        plugin_cards_html = self.generate_plugin_cards(plugins_info)
        plugin_count = len(plugins_info)
        
        # 动态获取插件CSS内容
        plugin_css = self.get_plugin_contents_by_position('head', 'css')
        # 动态获取插件HTML内容
        plugin_html = self.get_plugin_contents_by_position('body', 'html')
        # 动态获取插件JS内容
        plugin_js = self.get_plugin_contents_by_position('body', 'js')
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <title>Kaos Web Platform</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" href="/logo/Kaos_Logo.png" type="image/png">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', 'Microsoft YaHei', Tahoma, Geneva, Verdana, sans-serif;
            height: 100vh;
            overflow: hidden;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            /* 添加背景图片以增强毛玻璃效果 */
            background-image: url('https://images.unsplash.com/photo-1518791841217-8f162f1e1131?ixlib=rb-1.2.1&auto=format&fit=crop&w=1950&q=80');
            background-size: cover;
            background-position: center;
        }}
        
        .container {{
            display: flex;
            height: 100vh;
            overflow: hidden;
        }}
        
        /* 左侧导航栏样式 */
        .sidebar {{
            width: 260px;
            background: linear-gradient(180deg, #2c3e50 0%, #1a2530 100%);
            color: white;
            height: 100%;
            overflow-y: auto;
            transition: all 0.3s ease;
            box-shadow: 3px 0 15px rgba(0,0,0,0.2);
            position: relative;
            z-index: 100;
        }}
        
        .sidebar-header {{
            padding: 10px 20px;
            background: rgba(0, 0, 0, 0.2);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
            position: sticky;
            top: 0;
            background: linear-gradient(180deg, #2c3e50 0%, #1a2530 100%);
            z-index: 101;
        }}
        
        .sidebar-header h1 {{
            font-size: 1.8rem;
            font-weight: 700;
            margin: 10px 0 5px;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;
        }}
        
        .sidebar-header p {{
            font-size: 0.9rem;
            color: #bdc3c7;
            margin-top: 5px;
            opacity: 0.8;
        }}
        
        .sidebar-menu {{
            padding: 15px 0;
        }}
        
        .menu-item {{
            padding: 14px 24px;
            display: flex;
            align-items: center;
            cursor: pointer;
            transition: all 0.3s ease;
            border-left: 4px solid transparent;
            margin: 6px 12px;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
            background: rgba(255, 255, 255, 0.05);
        }}
        
        .menu-item:hover {{
            background: rgba(52, 152, 219, 0.25);
            transform: translateX(6px);
            border-left-color: #3498db;
        }}
        
        .menu-item.active {{
            background: rgba(46, 204, 113, 0.25);
            border-left: 4px solid #2ecc71;
            transform: translateX(6px);
        }}
        
        .menu-item.active::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            transform: translateX(-100%);
            animation: shimmer 1.5s infinite;
        }}
        
        @keyframes shimmer {{
            100% {{
                transform: translateX(100%);
            }}
        }}
        
        .menu-item i {{
            margin-right: 15px;
            font-size: 1.2rem;
            width: 24px;
            text-align: center;
            color: #3498db;
        }}
        
        .menu-item span {{
            font-size: 1.05rem;
            font-weight: 500;
        }}
        
        /* 右侧内容区域样式 */
        .main-content {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: rgba(245, 247, 250, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-left: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .content-header {{
            padding: 25px 30px;
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 2px 15px rgba(0,0,0,0.1);
            z-index: 10;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }}
        
        .content-header h2 {{
            color: #2c3e50;
            font-size: 1.8rem;
            font-weight: 700;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
        }}
        
        .content-header h2 i {{
            margin-right: 12px;
            color: #3498db;
        }}
        
        .content-header p {{
            color: #7f8c8d;
            font-size: 1rem;
            margin: 0;
        }}
        
        .content-body {{
            flex: 1;
            padding: 25px;
            overflow-y: auto;
            background: rgba(245, 247, 250, 0.7);
            backdrop-filter: blur(5px);
            -webkit-backdrop-filter: blur(5px);
        }}
        
        /* 统计信息样式 */
        .stats-container {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.08);
            display: flex;
            flex-direction: column;
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.12);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3498db, #2ecc71, #e74c3c, #f39c12);
            background-size: 400% 400%;
            animation: gradientBG 3s ease infinite;
        }}
        
        @keyframes gradientBG {{
            0% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        
        .stat-icon {{
            font-size: 2.2rem;
            margin-bottom: 15px;
            width: 70px;
            height: 70px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-top: 10px;
        }}
        
        .stat-value {{
            font-size: 2.5rem;
            font-weight: 800;
            color: #2c3e50;
            margin: 12px 0;
            text-align: center;
            background: linear-gradient(135deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}
        
        .stat-label {{
            color: #7f8c8d;
            font-size: 0.95rem;
            text-align: center;
            font-weight: 500;
            margin-top: 5px;
        }}
        
        /* 插件卡片样式 */
        .plugins-title {{
            display: flex;
            align-items: center;
            margin: 25px 0 20px;
            color: #2c3e50;
            font-size: 1.3rem;
            font-weight: 600;
        }}
        
        .plugins-title i {{
            margin-right: 10px;
            color: #3498db;
        }}
        
        .plugins-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 10px;
        }}
        
        .plugin-card {{
            background: rgba(255, 255, 255, 0.85);
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 6px 25px rgba(0,0,0,0.08);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            position: relative;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.2);
            animation: fadeInUp 0.6s ease-out;
        }}
        
        .plugin-card:hover {{
            transform: translateY(-8px) scale(1.02);
            box-shadow: 0 15px 40px rgba(0,0,0,0.15);
        }}
        
        .plugin-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #3498db, #2ecc71, #e74c3c, #f39c12);
            background-size: 400% 400%;
            animation: gradientBG 3s ease infinite;
        }}
        
        @keyframes fadeInUp {{
            from {{
                opacity: 0;
                transform: translateY(30px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .plugin-name {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #2c3e50;
            margin-bottom: 12px;
            position: relative;
            padding-bottom: 10px;
        }}
        
        .plugin-name::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 40px;
            height: 3px;
            background: linear-gradient(90deg, #3498db, #2ecc71);
            border-radius: 2px;
        }}
        
        .plugin-developer {{
            color: #7f8c8d;
            margin: 10px 0;
            font-size: 1rem;
            display: flex;
            align-items: center;
        }}
        
        .plugin-developer i {{
            margin-right: 8px;
            color: #3498db;
        }}
        
        .plugin-version {{
            color: #2ecc71;
            font-weight: 600;
            font-size: 0.95rem;
            display: inline-block;
            background: rgba(46, 204, 113, 0.1);
            padding: 6px 14px;
            border-radius: 20px;
            margin-top: 8px;
            border: 1px solid rgba(46, 204, 113, 0.2);
        }}
        
        .plugin-description {{
            color: #7f8c8d;
            font-size: 0.9rem;
            margin-top: 12px;
            line-height: 1.5;
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .sidebar {{
                width: 80px;
            }}
            
            .sidebar-header h1, .sidebar-header p, .menu-item span {{
                display: none;
            }}
            
            .menu-item {{
                justify-content: center;
                padding: 18px;
            }}
            
            .menu-item i {{
                margin-right: 0;
                font-size: 1.4rem;
            }}
            
            .content-header h2 {{
                font-size: 1.5rem;
            }}
            
            .stats-container {{
                grid-template-columns: 1fr;
            }}
            
            .plugins-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        
        /* 滚动条样式 */
        ::-webkit-scrollbar {{
            width: 10px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
            border-radius: 10px;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: linear-gradient(180deg, #3498db, #2c3e50);
            border-radius: 10px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(180deg, #2ecc71, #27ae60);
        }}
        
        /* 插件CSS内容 */
        {plugin_css}
    </style>
</head>
<body>
    
    
    <div class="container">
        <!-- 左侧导航栏 -->
        <div class="sidebar">
            <div class="sidebar-header">
                <img src="/logo/Kaos_White.png" alt="Kaos Logo" style="max-width: 80%; height: auto; margin: 10px auto; display: block;">
            </div>
            <div class="sidebar-menu" id="sidebar-menu">
                {menu_items_html}
            </div>
        </div>
        
        <!-- 右侧内容区域 -->
        <div class="main-content">
            <div class="content-header">
                <h2><i class="fas fa-tachometer-alt"></i> 系统仪表板</h2>
                <p>欢迎使用Kaos系统管理平台</p>
            </div>
            <div class="content-body">
                <!-- 统计信息 -->
                <div class="stats-container">
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-plug"></i>
                        </div>
                        <div class="stat-label">已加载插件</div>
                        <div class="stat-value">{plugin_count}</div>
                        <div class="stat-label">个插件正在运行</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-heartbeat"></i>
                        </div>
                        <div class="stat-label">系统状态</div>
                        <div class="stat-value">正常</div>
                        <div class="stat-label">所有服务运行中</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="stat-label">运行时间</div>
                        <div class="stat-value">0</div>
                        <div class="stat-label">天</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-icon">
                            <i class="fas fa-microchip"></i>
                        </div>
                        <div class="stat-label">CPU使用率</div>
                        <div class="stat-value">32%</div>
                        <div class="stat-label">当前负载</div>
                    </div>
                </div>
                
                <!-- 插件列表 -->
                <div class="plugins-title">
                    <i class="fas fa-list"></i>
                    <span>已加载插件</span>
                </div>
                <div class="plugins-grid" id="plugins-container">
                    {plugin_cards_html}
                </div>
            </div>
        </div>
    </div>
    
    <!-- 插件HTML内容 -->
    {plugin_html}
    
    <script>
        
        
        // 菜单切换功能
        function handleMenuItemClick(view, evt) {{
            // 移除所有激活状态
            document.querySelectorAll('.menu-item').forEach(i => i.classList.remove('active'));
            // 添加当前激活状态
            if (evt && evt.currentTarget) {{
                evt.currentTarget.classList.add('active');
            }}
            
            // 更新内容标题
            const titles = {{
                'dashboard': '系统仪表板',
                'plugins': '插件管理',
                'settings': '系统设置',
                'logs': '日志查看',
                'analytics': '数据分析'
            }};
            
            const icons = {{
                'dashboard': 'tachometer-alt',
                'plugins': 'plug',
                'settings': 'cog',
                'logs': 'file-alt',
                'analytics': 'chart-line'
            }};
            
            const descriptions = {{
                'dashboard': '欢迎使用Kaos系统管理平台',
                'plugins': '管理系统中安装的所有插件',
                'settings': '配置系统参数和选项',
                'logs': '查看系统运行日志',
                'analytics': '分析系统性能和使用情况'
            }};
            
            // 检查是否是动态注册的菜单项
            const dynamicTitles = {{}};
            const dynamicIcons = {{}};
            const dynamicDescriptions = {{}};
            
            document.querySelector('.content-header h2').innerHTML = `<i class="fas fa-${{icons[view] || dynamicIcons[view] || 'bars'}}"></i> ${{titles[view] || dynamicTitles[view] || '系统管理'}}`;
            document.querySelector('.content-header p').textContent = descriptions[view] || dynamicDescriptions[view] || 'Kaos系统管理平台';
            
            // 这里可以根据视图加载不同的内容
            if (view === 'plugins') {{
                // 插件管理视图可以显示更详细的插件信息
                console.log('切换到插件管理视图');
            }} else if (view === 'settings') {{
                // 系统设置视图
                console.log('切换到系统设置视图');
            }} else if (view === 'logs') {{
                // 日志查看视图
                console.log('切换到日志查看视图');
            }} else if (view === 'analytics') {{
                // 数据分析视图
                console.log('切换到数据分析视图');
            }} else {{
                // 处理动态注册的菜单项
                console.log(`切换到动态视图: ${{view}}`);
            }}
        }}
        
        // 为静态菜单项添加事件监听器
        document.querySelectorAll('.menu-item').forEach(item => {{
            item.addEventListener('click', function(e) {{
                const view = this.getAttribute('data-view');
                handleMenuItemClick(view, e);
            }});
        }});
        
        // 每5秒刷新一次插件信息
        setInterval(() => {{
            fetch('/api/plugins')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('plugins-container').innerHTML = generatePluginCards(data);
                    // 更新插件统计信息
                    document.querySelector('.stat-value').textContent = data.length;
                }});
        }}, 5000);
        
        function generatePluginCards(plugins) {{
            let html = '';
            plugins.forEach(plugin => {{
                html += `
                    <div class="plugin-card">
                        <div class="plugin-name">${{plugin.name}}</div>
                        <div class="plugin-developer"><i class="fas fa-user"></i> 开发者: ${{plugin.developer}}</div>
                        <div class="plugin-version"><i class="fas fa-code-branch"></i> 版本: ${{plugin.version}}</div>
                        <div class="plugin-description">这是一个强大的Kaos插件，提供丰富的功能和特性。</div>
                    </div>
                `;
            }});
            return html;
        }}
        
        // 更新运行时间
        function updateUptime() {{
            const uptimeElement = document.querySelector('.stat-value:nth-child(3)');
            if (uptimeElement) {{
                // 这里可以实现实际的运行时间计算
                // 暂时使用模拟数据
                uptimeElement.textContent = Math.floor(Math.random() * 30) + 1;
            }}
        }}
        
        // 定期更新运行时间
        setInterval(updateUptime, 60000);
        updateUptime();
        
        // 插件JS内容
        {plugin_js}
    </script>
</body>
</html>
"""
        self.send_response(200)
        self.send_header('content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_content.encode('utf-8'))

def run_web_server(plugin_loader):
    # 读取配置文件
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        host = config.get('host', '0.0.0.0')
        port = config.get('port', 6099)
    except Exception as e:
        print(f"警告: 无法读取配置文件，使用默认设置: {e}")
        host = '0.0.0.0'
        port = 6099
    
    server_address = (host, port)
    httpd = HTTPServer(server_address, WebInterfaceHandler)
    # 将plugin_loader传递给服务器实例
    httpd.plugin_loader = plugin_loader
    print(f"启动Web管理界面...")
    print(f"Web管理界面地址: http://{host}:{port}")
    httpd.serve_forever()

def start_plugin(api_registry, plugin_loader):
    """插件入口函数"""
    # 注册菜单项API（如果api_registry可用）
    if api_registry is not None:
        api_registry.register_api("WebPlatform", "register_menu_item", WebInterfaceHandler.register_menu_item, show_output=False)
        api_registry.register_api("WebPlatform", "register_plugin_content", WebInterfaceHandler.register_plugin_content, show_output=False)
    else:
        print("警告: API注册表不可用，部分功能可能无法正常工作")
    
    # 启动Web服务器
    web_thread = threading.Thread(target=run_web_server, args=(plugin_loader,), daemon=True)
    web_thread.start()