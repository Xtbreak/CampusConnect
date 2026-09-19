# 项目维护

## 模块边界

| 目录 / 模块 | 职责 |
| --- | --- |
| `campusconnect/desktop.py` | 窗口生命周期、用户交互、日志分发 |
| `campusconnect/ui_layout.py` | 首页与设置页布局 |
| `campusconnect/core.py` | 认证状态、登录、兼容命令行逻辑 |
| `campusconnect/connection_worker.py` | 独立网络进程、取消与重试 |
| `campusconnect/portal.py` | 运营商及登录参数构造 |
| `campusconnect/windows_settings.py` | 密码加密、本地设置、开机启动 |
| `campusconnect/platform_settings.py` | 平台选择、数据目录、打开文件夹 |
| `campusconnect/mac_settings.py` | macOS 钥匙串、本地设置、登录启动 |
| `campusconnect/tray.py` | 托盘及菜单 |
| `campusconnect/paths.py` | 源码与 EXE 资源路径 |
| `campusconnect/diagnostics.py` | 脱敏请求诊断 |

## 验证与构建

```powershell
python -m unittest discover -s tests -v
python -m campusconnect.core --help
powershell -ExecutionPolicy Bypass -File scripts/build.ps1
```

测试覆盖参数编码、认证流程、进程停止、密码保存、窗口行为及日志脱敏。平台专用测试在另一平台自动跳过；Mac 设置测试模拟钥匙串，避免操作开发者真实凭据和启动项。测试不使用真实校园网账号登录。GUI 测试需要可用的桌面环境。

macOS 构建执行 `bash scripts/build_macos.sh`，详见 [macOS 使用与发布](macos.md)。GitHub Actions 分别构建 Windows、macOS arm64 和 macOS x86_64；标签发布只创建草稿，正式发布前需完成对应平台实际验收。

构建使用 `.venv-build/`，图标转换由 `python -m scripts.prepare_icon` 完成。`scripts/launch.py` 为 EXE 入口；源码通过 `python -m campusconnect` 运行。构建产物写入 `build/` 和 `dist/`，不进入 Git。发布 EXE 应作为 Releases 附件，避免把每个版本的二进制提交到源码历史。

## 提交约定

- 源码放 `campusconnect/`，测试放 `tests/`，开发命令放 `scripts/`。
- `config/` 只包含占位示例，真实凭据、日志和本地设置不提交。
- `assets/` 仅保留运行和打包需要的图标；临时设计说明与预览放 `local/`，该目录不上传。
- 保持根目录只有 README 和 Git 配置，不新增零散脚本。
- 提交前运行测试、检查 `git diff --check` 和暂存清单；不记录认证 URL、密码或完整原始响应。
- 使用描述具体变化的提交信息，如 `fix: ...`、`feat: ...`、`refactor: ...`、`docs: ...`。
- 当前未指定开源许可证；不要自行假定代码采用 MIT 或其他授权。
