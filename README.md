<img width="357" height="134" alt="Kaos_White" src="https://github.com/user-attachments/assets/4712c04e-bdb6-4b88-97fd-f566f3458145" />

# Kaos-Module-System

![Python Version](https://img.shields.io/badge/Python-3.10+-blue)
![Status](https://img.shields.io/badge/状态-开发中-yellow)

Kaos，一个旨在高度模块化的自由定制系统

## · 介绍

Kaos基于Python开发，通过高度模块化结构来实现高自由度的效果。理论上，只要代码可以实现，Kaos可以支持几乎所有的功能。

> 因个人开发者经历有限，Kaos的更新不会很勤快。欢迎来和我一起~~乱搞~~开发Kaos系统~
>
> 交流群：966012245  群里还有一只可爱的小九Bot可以随便rua ~~（尽管经常会胡言乱语不知所云外加发神经）~~

## 📌 注意事项

使用本项目前必须阅读和同意[用户协议](EULA.md)。至于为什么没有隐私协议，因为Kaos不采集用户任何信息。 ~~（其实就是没写）~~

> [!WARNING]
> 
> 欢迎使用 Kaos 系统。本最终用户许可协议是您与 Kaos 开发者之间的法律协议。
> 
> 通过安装、复制或以其他方式使用本软件，您同意受本协议条款的约束。如果您不同意条款，请勿安装或使用本软件。
> 
> 1.软件本体许可授予
> 
> 开发者在此授予您一项有限的、非独占的、不可转让的许可，允许您在设备上安装和使用Kaos，仅用于非商业用途。如需用于商业用途，请联系作者。
> 
> 2.限制
> 
> 您不得：
> 
> a) 将Kaos运行在非经许可授权的设备上
> 
> b) 对Kaos进行逆向工程、反编译或尝试获取其源代码
> 
> c) 将本软件用于任何非法目的
> 
> 如发现违反以上限制，Kaos有权删除该设备上运行的Kaos副本及其承载的所有数据。因违反限制造成Kaos删除数据所带来的损失，开发者不负任何责任。
> 
> 3.所有权
> 
> 开发者保留Kaos的所有权利、所有权，包括所有知识产权。在允许情况下，Kaos欢迎进行二次开发。二次开发不得以盈利为目的，否则视为将本软件用于商业目的。
> 
> 4.责任限制
> 
> Kaos系高自由度模块化系统，用户在Kaos上安装的插件应仔细确保其功能，防止其为恶意插件。因安装Kaos恶意插件而导致Kaos对设备及数据造成损害的，开发者不负任何责任。
> 
> 5.适用法律
> 
> 本协议受您所在国家/地区的法律管辖。

> # ~~以下内容是AI自己生成的Readme.md内容，当开发档案看看就得了。0.1.0-Snapshot要改很多~~

Kaos 是一个基于Python的模块加载程序，支持插件化架构和内部API通讯机制。

## 目录结构

```
kaos/
├── main.py              # 程序入口文件
├── src/                 # 核心源代码目录
│   ├── api_registry.py  # API统一平台
│   └── plugin_loader.py # 插件加载器
└── plugins/             # 插件存储目录
```

## 功能特性

1. **插件化架构**：支持动态加载和管理插件
2. **API统一平台**：插件间通过统一API平台进行通讯
3. **依赖检查**：自动检查插件依赖关系
4. **权限管理**：支持多级权限控制
5. **可视化界面**：通过插件提供Web界面（默认运行在6099端口）
6. **Manifest校验**：主程序会校验插件的manifest文件，校验不通过的插件不会被加载

## 运行模式

Kaos本体启动后会在控制台窗口显示已加载插件的信息，包括：
- 插件目录名
- 插件名称（来自manifest文件）
- 开发者信息

HTTP服务器功能已移除，现在通过专门的可视化插件提供Web界面。

## 插件系统

### 插件目录结构

插件需要按照以下结构组织：

```
plugins/
└── 示例插件/
    ├── _manifest.json
    └── plugin.py
```

### Manifest文件规范

每个插件目录必须包含`_manifest.json`文件，格式如下：

```json
{
    "version": "0.0.1",
    "pluginName": "插件名称",
    "dependencies": [],
    "Developer": "开发者名称",
    "Permission": "System/User/Visitor",
    "InstallationLevel": "Admin/Normal"
}
```

字段说明：
- `version`：插件版本号
- `pluginName`：插件名称
- `dependencies`：依赖的插件列表（数组格式，可选）
- `Developer`：开发者名称
- `Permission`：权限等级（System/User/Visitor）
- `InstallationLevel`：安装等级（Admin/Normal）

### Plugin.py文件

插件的主文件，必须包含插件的逻辑实现。
- 所有插件的入口文件必须命名为`plugin.py`
- 插件可以通过API系统向Web界面动态注入内容（CSS、HTML、JavaScript）

## API系统

### API注册

插件可以通过以下方式注册自己的API：

```python
# 在plugin.py中
def my_api_function():
    return "Hello from my API"

# 注册API
api_registry.register_api("插件名称", "api名称", my_api_function)
```

### API调用

插件可以通过以下方式调用其他插件的API：

```python
# 获取其他插件的API
api_func = api_registry.get_api("目标插件名称", "api名称")

# 调用API
if api_func:
    result = api_func()
```

## 插件API系统

Web平台提供API供其他插件使用，允许插件动态地向页面注入内容：

```python
# 注册CSS样式
WebInterfaceHandler.register_plugin_content("插件名称", "css", css_content, "head")

# 注册HTML内容
WebInterfaceHandler.register_plugin_content("插件名称", "html", html_content, "body")

# 注册JavaScript内容
WebInterfaceHandler.register_plugin_content("插件名称", "js", js_content, "body")
```

这种设计避免了直接修改WebUI代码来兼容特定插件，而是通过API系统实现动态内容注入。

## 快速开始

1. 安装Python环境
2. 创建插件目录结构
3. 编写插件代码和manifest文件
4. 运行程序：`python main.py`

## 可视化界面

程序提供了一个可视化插件，启动后会在本地6099端口运行Web服务器，可以通过访问`http://localhost:6099`查看可视化界面。

### WebPlatform配置

WebPlatform插件支持通过配置文件修改运行参数：

在 `plugins/WebPlatform/config.json` 文件中可以配置：
```json
{
    "host": "0.0.0.0",
    "port": 6099
}
```

参数说明：
- `host`：服务器绑定的IP地址，默认为"0.0.0.0"（允许外部访问）
- `port`：服务器运行的端口，默认为6099
