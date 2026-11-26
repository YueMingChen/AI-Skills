# vivo 手机 APK 自动确认安装方案

v1.0.0 · 2026-11-26

vivo 手机（OriginOS / Funtouch OS）通过 adb 或 Android Studio Run 安装 APK 时，系统会强制弹出「安全守护提示 - 外部来源应用」页面，必须人工点击「继续安装」。本方案用脚本自动完成这一步，实现无人值守安装。

已验证机型：vivo V2408A（Android 16 / OriginOS 16，1080×2376），macOS + adb。

## 方案组成

| 文件 | 说明 |
| --- | --- |
| `vclick.py` | 核心脚本，通过 uiautomator 找到「继续安装」并模拟点击 |
| `install.sh` | 一键安装脚本，部署 vclick.py 并注册 Trae 全局 skill |
| `skill/vivo-auto-install/SKILL.md` | Trae skill 模板，安装时自动替换脚本绝对路径 |
| `README.md` | 使用文档 |

原理：安装时后台执行 `adb install`，同时轮询 `uiautomator dump`，发现文本包含「继续安装」的节点就计算其坐标并执行 `input tap`；安装结束后按 adb 退出码判断成败。不 root、不修改系统、不绕过系统校验，只是代替人手点击。

## 环境要求

- macOS / Linux（Windows 可手动使用脚本，但需自行调整路径）
- 已安装 adb，`adb devices` 能看到设备
- Python 3
- 手机侧设置：
  1. 开启开发者选项中的 USB 调试，并允许本机调试
  2. 开发者选项打开「USB 安装」
  3. 关闭「USB 安装验证」（不同系统版本菜单名可能不同）
  4. 登录 vivo 账号并保持联网，否则可能弹账号验证页，脚本无法处理
  5. 安装时保持亮屏并解锁；有 PIN、图案或密码锁时需先手动解锁
  6. 建议在开发者选项打开「保持唤醒（充电时）」，避免安装中息屏

## 快速开始

### 1. 安装

```bash
bash install.sh
```

默认行为：

- 脚本安装到 `~/projects/vivo-auto-install/vclick.py`
- skill 安装到 `~/.trae-cn/skills/vivo-auto-install/`；检测到国际版 Trae 时使用 `~/.trae/skills/`，未检测到 Trae 则跳过

自定义脚本安装位置：

```bash
VIVO_INSTALL_DIR=/your/path bash install.sh
```

### 2. 安装 APK

```bash
python3 ~/projects/vivo-auto-install/vclick.py /path/to/app.apk
```

成功输出示例：

```
[11:15:01] 设备 10AEBE4EGC001YZ：安装 /tmp/app.apk
[11:15:06] 点击「继续安装」(540, 2223)
[11:15:09] 成功：退出码 0，自动点击 1 次，耗时 7.4s
```

退出码 0 表示安装成功。

### 3. Android Studio Run 场景

Android Studio 自己调用 adb 安装，无法替换安装命令，使用常驻监听模式：

```bash
python3 ~/projects/vivo-auto-install/vclick.py --watch
```

保持该终端运行，之后正常点 Studio 的 Run 即可；任务结束后 Ctrl+C 停止。常驻模式不要与一次性安装同时使用。

## 参数与环境变量

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `ANDROID_SERIAL` | 自动 | 指定设备序列号，连接多台设备时必填 |
| `ADB` | `adb` | adb 可执行文件路径 |
| `INSTALL_TIMEOUT` | `600` | 单次安装超时秒数 |

## 常见问题

| 现象 | 处理 |
| --- | --- |
| `没有已连接并授权的设备` | 检查数据线、USB 调试开关和手机上的调试授权弹窗 |
| `屏幕处于锁屏状态` | 手动解锁后重试；有密码锁时脚本无法自动解锁 |
| `安装超时` | 确认安装页是否出现；若出现的是 vivo 账号验证页，需手动登录 vivo 账号 |
| `INSTALL_FAILED_*` | APK、签名或系统限制问题，按 adb 输出定位，与脚本无关 |
| AI 对话没有调用 skill | 新开一个对话让 skill 生效，或直接说「用 vivo-auto-install 技能装一下」 |
| 连接了多台设备 | `ANDROID_SERIAL=设备序列号 python3 vclick.py app.apk` |

## 卸载

```bash
rm -rf ~/projects/vivo-auto-install ~/.trae-cn/skills/vivo-auto-install
```

## 配合 AI 使用

安装完成后新开对话，说「帮我把 app 安装到真机」即可命中 skill。skill 的工作规则：

- 自动选择唯一在线设备，多设备时要求用户指定序列号
- 优先安装 `**/build/outputs/apk/**/*.apk` 中最新的构建产物
- 失败时把脚本完整输出反馈给用户
