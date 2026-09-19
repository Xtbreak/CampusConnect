# CampusConnect

面向安徽理工大学有线校园网的 Windows 自动认证工具。支持电信、移动、联通，提供图形界面、系统托盘、加密记住密码、开机启动和断线自动登录。

## 运行

源码运行需要 Windows 和 Python 3.10+：

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

图形版只根据认证状态判断是否登录，不通过外网检测阻塞认证。认证在线不保证外网可用，当前未保证其他学校或无线网络兼容。
