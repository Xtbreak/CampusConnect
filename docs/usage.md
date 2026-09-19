# 使用说明

## 图形界面

打开构建后的 `CampusConnect.exe`，填写学号、密码并选择电信、移动或联通。点击“连接校园网”后查询认证状态，离线时立即登录，再查询状态确认。图形版不检测外网、不主动注销或解绑；“认证在线”不保证外网可用，已有会话也不代表新输入的凭据已通过验证。

左侧“设置”、顶部设置菜单或托盘设置菜单可打开偏好设置：

- 断线自动登录：保持后台监测，失败后退避重试。
- 记住密码：使用 Windows DPAPI 保存，当前用户可解密。
- 开机启动：在登录 Windows 后启动 EXE，需固定程序位置。
- 启动后自动连接：需同时开启记住密码。
- 关闭行为：隐藏到托盘或彻底退出，点击“保存设置”后生效。

默认关闭窗口会隐藏到托盘；双击托盘图标恢复窗口。托盘或侧栏的“退出程序”始终彻底退出。停止按钮终止网络任务，不注销已有连接，也不能撤回已经到达服务器的请求。

## 配置与日志

图形版数据存储于 `%LOCALAPPDATA%/MyWatch`。取消记住密码和启动后自动连接并保存，会移除已保存的加密密码。取消开机启动并保存，会移除当前用户 Run 注册表中的 `MyWatchCampusConnect` 启动项。

“关键动态”只显示重要事件；“查看详细日志”打开包含 `client.log` 的目录。详细日志按天轮转、保留 14 份，记录请求耗时、状态码、错误分类、重试和停止情况，不记录账号密码或完整认证链接。

## 兼容命令行模式

以下命令在项目根目录、已安装依赖的 Python 环境中执行：

```powershell
python -m scripts.configure_cli
python -m campusconnect.core --check-only
python -m campusconnect.core --login-once
python -m campusconnect.core --no-daily-reconnect
```

配置向导读取 `config/config.example.json`，在根目录生成被 Git 忽略的 `config.json` 和明文 `credentials.json`，仅供旧命令行流程使用。图形界面不需要此步骤。旧配置中的 `token` 是密码字段的历史名称，不是独立票据。

命令行保留原有外网诊断、每日重连与解绑逻辑；不加 `--no-daily-reconnect` 时默认每日 04:00 重连。`--reconnect-once` 会主动注销解绑后再登录，请仅在需要时使用。日志位于配置文件同目录的 `logs/`。

## 适配范围与已知限制

当前适配安徽理工大学有线 Dr.COM 门户，电信 `@aust`、移动 `@cmcc`、联通 `@unicom`。来源为学校门户 `http://10.255.0.19:801/eportal/extern/lgdx/ip/3/pc.js`（2026-09-18 核对）。认证状态来自 `/drcom/chkstatus`；`page_type_data` 返回成功不等于在线。

认证接口沿用学校 HTTP 协议，URL 编码不是传输加密。无线网络及其他学校未验证兼容。此前登录失败的具体原因仍需结合错误码定位，未完成三家运营商账号的实际登录验收。
