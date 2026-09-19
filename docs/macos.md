# macOS 使用与发布

## 安装

- Apple 芯片（M 系列）选择 `CampusConnect-macOS-arm64.dmg`。
- Intel Mac 选择 `CampusConnect-macOS-x86_64.dmg`。
- 打开 DMG，将 CampusConnect 拖到 Applications，再从“应用程序”启动。
- ZIP 为同一 App 的压缩版本，不需要另装 Python。

自动构建默认使用 ad-hoc 签名，**未经 Apple 公证**。这类测试包从互联网下载后可能被 Gatekeeper 拦截；仅在确认来源可靠时，按 macOS“系统设置 → 隐私与安全性”中的提示允许打开。不要关闭系统安全检查。需要免额外确认的正式分发时，应使用下文的 Developer ID 签名和公证流程。

## Mac 行为

认证协议与 Windows 一致，仍仅针对安徽理工大学有线校园网。Mac 通常需通过网线及以太网转接器接入校园网络；无线网络未验证。认证在线不保证外网可用。

“记住密码”使用当前用户的登录钥匙串，服务名为 `io.github.xtbreak.CampusConnect`。配置文件只记录是否使用钥匙串，不写入密码。第一次访问钥匙串或应用签名变化时，系统可能询问访问权限。取消记住密码并保存将删除该密码项。

配置和日志：`~/Library/Application Support/CampusConnect/`。

“开机启动”指登录当前 Mac 用户后启动。启用后写入 `~/Library/LaunchAgents/io.github.xtbreak.CampusConnect.plist`，**下次登录生效**，保存时不会额外启动一个实例。启用前先把 App 放到固定位置；移动 App 后需重新保存启动设置。关闭此选项并保存会删除启动项。卸载前应关闭开机启动，并根据需要清除已保存密码。

窗口关闭后默认保留菜单栏图标，可通过图标菜单恢复窗口、停止连接或退出。Dock 图标也可以恢复窗口；Command-Q 会退出并停止网络任务。菜单栏图标不可用时会最小化窗口。

## 源码运行与构建

使用带 Tk 8.6 或更新版本的 Python 3.10+（推荐 python.org 的 Python 3.12 安装包）。系统自带的旧 Python/Tk 不适用。Homebrew 用户需安装与 Python 版本匹配的 `python-tk`。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements/runtime.txt
.venv/bin/python -m campusconnect
```

构建会创建 `.venv-build`、安装依赖、运行测试，并生成 App、ZIP、DMG 和 SHA-256 校验文件：

```bash
bash scripts/build_macos.sh
# 选择指定 Python 时：
PYTHON=/path/to/python3 bash scripts/build_macos.sh
```

产物在 `dist/`。在 Apple 芯片 Mac 上使用原生 arm64 Python 构建 arm64 包，在 Intel Mac 上构建 x86_64 包；不能将 arm64 包改名作为 Intel 包。最低 macOS 版本还受构建使用的 Python、Tk 和依赖库限制，应在目标系统验证后声明支持范围。

## 签名和公证

需要 Apple Developer Program 的 **Developer ID Application** 证书及公证凭据。证书须已导入构建机器钥匙串；用 `xcrun notarytool store-credentials` 按 Apple 提示创建钥匙串配置，不要将证书私钥、密码或 API 私钥提交到仓库。

```bash
MACOS_SIGNING_IDENTITY='Developer ID Application: Your Name (TEAMID)' \
MACOS_NOTARY_PROFILE='CampusConnect-notary' \
bash scripts/build_macos.sh
```

脚本会签名 App、提交公证、装订公证票据并检查 Gatekeeper，然后生成 ZIP 和 DMG；DMG 也会单独签名、公证和装订票据。任何步骤失败会终止构建。未提供公证配置时只生成未经公证的测试包，并明确提示。

## GitHub 构建与发布

`.github/workflows/build.yml` 在 main 推送、PR 和手动触发时构建 Windows、Apple 芯片 Mac、Intel Mac 三种产物。可在 Actions 的 Artifacts 下载；下载可能需要 GitHub 登录。

推送 `v*` 标签后，三平台构建全部通过才创建带附件的 **Release 草稿**。默认附件未经 Apple 公证；正式发布前，应使用上述凭据在可信 Mac 上构建签名、公证包，替换对应附件和校验文件，确认安装和校园网验收，再发布草稿。工作流不会将未经公证的包自动公开为正式发行版。

## 验收边界

自动测试使用模拟认证响应，不会尝试真实校园网登录。Mac GUI、文件锁、取消任务、设置逻辑可本地验证；Windows DPAPI 和注册表测试仅在 Windows 运行。真实账号认证、注销后再次登录、睡眠唤醒、网络切换，以及另一种芯片和旧版 macOS 的兼容性，需要对应环境验证。
