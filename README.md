# CampusConnect

面向安徽理工大学有线校园网的 Windows / macOS 自动认证工具。支持电信、移动、联通，提供图形界面、托盘或菜单栏、系统安全存储密码、登录启动和断线自动登录。

## 运行

Windows 源码运行需要 Python 3.10+：

```powershell
git clone https://github.com/Xtbreak/CampusConnect.git
cd CampusConnect
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements/runtime.txt
.\.venv\Scripts\python.exe -m campusconnect
```

## 构建 EXE

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

输出为 `dist/CampusConnect.exe`。使用 EXE 不需要安装 Python；源码仓库不包含构建产物。开机启动功能需要运行打包后的 EXE。

## macOS

需要 Python 3.10+ 和 Tk 8.6+，推荐 python.org Python 3.12：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/runtime.txt
.venv/bin/python -m campusconnect
```

在 Mac 上执行 `bash scripts/build_macos.sh`，生成 `dist/CampusConnect.app`、对应芯片的 ZIP 和 DMG。使用 App 不需要安装 Python。默认构建未经 Apple 公证，正式分发的签名、公证和 GitHub 发布流程见 [macOS 使用与发布](docs/macos.md)。

## 目录

```text
campusconnect/   应用源码
tests/          回归测试
scripts/        构建、图标转换与命令行配置
requirements/   运行和构建依赖
config/         无敏感信息的配置示例
assets/         应用图标
docs/           使用说明与维护约定
```

`local/`、`dist/`、`build/`、虚拟环境、本地配置及日志均不上传。

## 文档

- [使用与设置](docs/usage.md)
- [开发、测试与项目维护](docs/development.md)
- [macOS 使用与发布](docs/macos.md)

图形版先处理校园网认证，再检查外网：检测成功显示“网络已连接”，失败时提示并区分认证是否成功。外网检查失败不会触发对已认证会话的重复登录或注销。当前未保证其他学校或无线网络兼容。
