# 校园网自动连接器

CampusConnect 是面向安徽理工大学有线校园网的 Windows 自动认证工具，提供图形界面、运营商选择、后台监测和系统托盘。

## 获取源码与构建

```powershell
git clone https://github.com/Xtbreak/CampusConnect.git
cd CampusConnect
powershell -ExecutionPolicy Bypass -File build.ps1
```

构建需要 Windows 和 Python 3.10+，完成后运行 `dist/CampusConnect.exe`。源码仓库不包含 EXE；构建得到的 EXE 可单独分发，使用者不需要安装 Python。

直接从源码启动图形界面：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe desktop.py
```

运行测试：`.\.venv\Scripts\python.exe -m unittest discover -v`。开机启动功能需要使用打包后的 EXE。

## Windows 图形版（不需要安装 Python）

新版采用“连接 / 设置”双页布局：连接页保留状态、账号、运营商、主操作和关键动态；设置页集中管理四个滑动开关及窗口关闭行为。点击左侧“设置”、顶部“设置 → 偏好设置”或托盘“设置”均可进入。

在设置页选择“隐藏到托盘”或“彻底退出”，点击“保存设置”后生效，并在下次启动时恢复。默认隐藏到托盘；选择彻底退出后，窗口右上角关闭按钮会停止任务并退出。侧栏或托盘的“退出程序”始终彻底退出。运行连接任务时，先停止再修改设置。

新图标由 imagegen 内置工具生成，源图为 `assets/campus-icon.png`，提示词见 `assets/icon-prompt.md`，Windows 多尺寸图标为 `assets/campus.ico`。图标用于 EXE、窗口、侧栏和托盘。打包脚本会携带 CustomTkinter 资源和图标。

双击 `dist/CampusConnect.exe`，填写学号、校园网密码，选择电信、移动或联通，点击“连接”。图形版只查询 `/drcom/chkstatus`：在线即结束本轮；离线立即登录，再查询认证状态确认。默认不访问百度、QQ、必应，避免外网超时阻塞认证。登录后的首次验证立即执行，仍未在线时再分别等待 1 秒、2 秒查询；接口异常仍受请求超时限制。认证服务器状态未知时不盲目登录。`page_type_data` 返回成功不代表认证在线。

勾选“保持运行，断线自动登录”后，窗口会持续检查认证状态并在离线时重新认证。点击关闭按钮会隐藏到 Windows 系统托盘，继续监测；双击托盘图标或右键选“显示窗口”可恢复。托盘菜单可停止自动连接或退出程序，窗口中的“退出”按钮也会彻底退出。托盘不可用时回退为最小化到任务栏，防止窗口隐藏后无法找回。图形版不执行每日注销或主动解绑。“认证在线”不保证外网可用；命令行脚本仍保留原有外网诊断逻辑。

图形版支持“记住密码（Windows 加密）”“开机启动”“启动后自动连接”。首次填写账号密码、选择运营商后，勾选这三个选项和“保持运行”，点击“保存设置”或“连接”。启动后自动连接要求记住密码。开机启动在当前用户登录 Windows 后运行，并最小化窗口；电脑需先接入校园 Wi-Fi 或网线，网络未就绪时程序按退避间隔重试。

密码用 Windows DPAPI 以当前用户身份加密后保存，不写入明文密码。取消“记住密码”和“启动后自动连接”并保存即可删除保存的密码。设置和滚动日志放在 `%LOCALAPPDATA%/MyWatch`，无需写入 EXE 所在文件夹。启动项位于当前用户 `HKCU/Software/Microsoft/Windows/CurrentVersion/Run` 下的 `MyWatchCampusConnect`，取消“开机启动”并保存即可移除，无需管理员权限。请将 EXE 放在固定位置，移动后需重新保存启动设置。程序每轮检查重新生成 `v` 参数。

停止按钮直接终止独立的网络进程，不等待整轮网络检查或退避计时。进程退出后恢复“连接”按钮并释放操作锁；下一次连接创建新的进程和消息队列。停止不会注销已有连接，也不能撤回已经到达服务器的认证请求。登录接口拒绝或未确认成功时显示有限的数字错误码及固定分类提示，不输出原始响应、密码或认证 URL，并跳过该轮后续外网检测。尚未确定此前真实登录失败的具体原因，需要下一次失败的错误码进一步定位。

当前适配安徽理工大学有线 Dr.COM 门户。2026-09-18 读取学校实际页面 `http://10.255.0.19:801/eportal/extern/lgdx/ip/3/pc.js` 核实：电信 `@aust`、移动 `@cmcc`、联通 `@unicom`；公共脚本 `http://10.255.0.19/a41.js` 中 `enableR3=0`。无线或其他学校不保证兼容。

原脚本的 `upass` 是校园网密码，没有独立 Token 获取步骤。先前命令行配置里的 `token` 只是密码字段的旧名称，不表示支持任意 Token 认证。认证已在线时，图形版保留当前会话，不重新提交新填写的凭据。

开发者在 Windows 上运行 `powershell -ExecutionPolicy Bypass -File build.ps1` 即可打包。构建使用独立 `.venv-build` 环境，只打包代码和依赖，不包含本地凭据。发布给同学只需发送 `dist/CampusConnect.exe`。

基于原有 `AutoConnect.py` 整理的 Windows 校园网自动认证项目，支持：

- 定时检查认证状态和外网连通性；
- 断网后自动恢复登录；
- 每日定时注销、解绑并重新认证；
- 凭据保存在本机，不写进源码，也不会提交到 Git。

## 快速开始

需要 Python 3.10+ 和 Windows。

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup.py
.\.venv\Scripts\python.exe AutoConnect.py --login-once
.\.venv\Scripts\python.exe AutoConnect.py
```

`setup.py` 第一次运行时会创建 `config.json` 和 `credentials.json`。其中 `credentials.json` 已加入 `.gitignore`，不要把它上传到公开仓库。

## 学校地址或参数不同

复制出的 `config.json` 中，修改 `login_url_template`。模板只允许使用 `{account}` 和 `{token}` 两个占位符；程序会对它们进行 URL 编码。

当前示例使用的是 Dr.COM 风格接口。如果学校认证页面使用不同协议，需要根据该门户的登录接口调整模板和请求逻辑，不能仅靠通用脚本自动猜出 Token。

## 关于“自动获取 Token”

校园网 Token 通常是密码、临时票据或统一身份认证会话，是否能自动获取完全取决于学校门户：

1. 如果它就是校园网密码，首次运行输入一次即可，之后由本地凭据文件自动使用。
2. 如果学校提供合法的 Token API，应在本项目中增加一个明确的 `token_provider`，由该 API 获取短期 Token；不要抓取浏览器密码或复制他人的 Cookie。
3. 如果必须经过验证码、短信或统一身份认证，程序不能绕过这些安全步骤，应保留首次人工登录。

因此本项目默认采用“首次配置、后续自动使用”的安全方案，没有把任何账号、密码或 Token 放入 Git。

如果原始脚本中的账号或密码曾经提交到过远程仓库，请立即修改校园网密码；仅删除本地文件不足以清除 Git 历史中的凭据。

## 图形版诊断日志

点击窗口中的“详细日志”打开 `%LOCALAPPDATA%/MyWatch`，当前日志为 `client.log`，按天轮转保留 14 份。“关键动态”面板只显示连接、认证结果、失败提示、失败后等待重试、设置保存和停止等关键事件，并抑制重复在线信息。面板不显示逐条 HTTP 请求、进程编号及正常轮询等待；完整诊断仍保存在文件中。文件日志包含版本、启动方式、设置开关、网络子进程 PID、检查轮次、每个请求的开始/结束、HTTP 状态、耗时、TLS/DNS/连接/读取超时分类、认证数字错误码、重试等待以及停止和退出记录。子进程消息保留其产生时间；外层时间为主进程接收时间。

日志不输出账号、密码、完整认证 URL、Cookie、原始响应或异常正文；无法识别的服务端错误只记录安全字段是否存在以及有限数字码。强制停止会丢弃子进程未送达的消息，但主进程会记录停止动作和退出码。新增日志不代表已解决此前的登录失败，需要失败时的日志继续定位。

## 命令行用法

```powershell
python AutoConnect.py --check-only       # 只检查，不改变连接
python AutoConnect.py --login-once       # 登录并验证一次
python AutoConnect.py --reconnect-once   # 注销后重连并验证
python AutoConnect.py --no-daily-reconnect
```

日志写入 `logs/AutoConnect.log`，默认保留 14 天。
