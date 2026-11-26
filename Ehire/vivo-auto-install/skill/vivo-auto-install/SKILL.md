---
name: vivo-auto-install
description: Install APKs on a connected vivo phone and auto-tap the 继续安装 prompt over USB debugging. Use when deploying an app, 安装 APK 到真机 or Android Studio Run, or when adb install needs phone-side confirmation. Do not use for non-Android targets.
---

# vivo 自动确认安装

在已连接的 vivo 手机上安装 APK，自动点击系统安装器的「继续安装」，不需要人工操作手机。

## 前置检查

1. 本机脚本固定为 `@SCRIPT_PATH@`。文件不存在时停止并告知用户，不要自行重写脚本。
2. 运行 `adb devices` 确认恰好一台状态为 `device` 的手机。多台时向用户确认序列号，并用 `ANDROID_SERIAL=<序列号>` 指定。
3. 手机需亮屏且已解锁。有 PIN、图案或密码时脚本无法自动解锁，先请用户手动解锁。

## 安装 APK

```bash
python3 @SCRIPT_PATH@ /绝对路径/app.apk
```

- 需要安装时先找 APK：优先使用 `**/build/outputs/apk/**/*.apk` 中最新的构建产物（常见为 `app/build/outputs/apk/debug/app-debug.apk`）。
- 退出码为 0 且输出出现「成功」即安装完成；失败时把脚本的完整输出反馈给用户。
- 多设备示例：`ANDROID_SERIAL=设备序列号 python3 @SCRIPT_PATH@ app.apk`

## Android Studio Run 场景

Studio 自己调用 adb 安装，无法替换安装命令，改为后台常驻监听：

```bash
python3 @SCRIPT_PATH@ --watch
```

以后台方式启动并保持运行，之后正常点 Studio 的 Run，安装确认页会被自动点击。用户要求结束或任务完成后停止该进程。常驻模式不要与一次性安装同时运行。

## 常见失败

- `没有已连接并授权的设备`：检查数据线、USB 调试开关和手机上的调试授权弹窗。
- `屏幕处于锁屏状态`：请用户解锁后重试。
- `安装超时`：确认安装页是否出现；如果出现的是 vivo 账号验证页，需要用户手动登录 vivo 账号，脚本不处理该页面。
- `INSTALL_FAILED_*`：属于 APK、签名或系统限制问题，按 adb 输出定位，不要归因于脚本。
