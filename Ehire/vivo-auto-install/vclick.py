#!/usr/bin/env python3
"""vivo 手机 APK 自动确认安装工具。

用法:
  python3 vclick.py <apk>     安装指定 APK，并自动点击系统安装器的「继续安装」
  python3 vclick.py --watch   常驻监听，自动点击安装确认页（配合 Android Studio Run）

环境变量:
  ANDROID_SERIAL   指定设备序列号，连接多台设备时必填
  ADB              adb 可执行文件路径，默认 adb
  INSTALL_TIMEOUT  安装超时秒数，默认 600
"""
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ADB = os.environ.get("ADB", "adb")
SERIAL = os.environ.get("ANDROID_SERIAL", "").strip()
TIMEOUT = int(os.environ.get("INSTALL_TIMEOUT", "600"))
CONFIRM_TEXTS = ("继续安装",)
UI_XML = "/sdcard/vclick_ui.xml"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def run(args, timeout=None):
    return subprocess.run([ADB] + args, capture_output=True, text=True, timeout=timeout)


def adb(*args):
    result = run(["-s", SERIAL] + list(args))
    return (result.stdout or "") + (result.stderr or "")


def check_adb():
    try:
        subprocess.run([ADB, "version"], capture_output=True)
    except FileNotFoundError:
        sys.exit(f"找不到 adb（{ADB}），请确认已安装并加入 PATH")


def pick_device():
    global SERIAL
    result = run(["devices"])
    devices = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device":
            devices.append(parts[0])
    if SERIAL:
        if SERIAL not in devices:
            sys.exit(f"设备 {SERIAL} 未连接或未授权，当前在线设备: {devices or '无'}")
        return
    if len(devices) == 1:
        SERIAL = devices[0]
        return
    if not devices:
        sys.exit("没有已连接并授权的设备，请检查 USB 调试和手机上的授权弹窗")
    sys.exit("检测到多台设备，请通过 ANDROID_SERIAL 指定: " + ", ".join(devices))


def wake_screen():
    adb("shell", "input", "keyevent", "KEYCODE_WAKEUP")
    adb("shell", "wm", "dismiss-keyguard")


def is_locked():
    out = adb("shell", "dumpsys", "window")
    if "mDreamingLockscreen=true" in out or "mShowingLockscreen=true" in out:
        return True
    focus = re.search(r"mCurrentFocus=(\S+)", out)
    return bool(focus and "Keyguard" in focus.group(1))


def tap_confirm():
    """抓取当前界面，找到「继续安装」按钮并点击。"""
    adb("shell", "rm", "-f", UI_XML)
    adb("shell", "uiautomator", "dump", UI_XML)
    xml = adb("shell", "cat", UI_XML)
    if "<hierarchy" not in xml:
        return False
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return False
    for node in root.iter("node"):
        text = (node.get("text") or "").strip()
        if not text or not any(t in text for t in CONFIRM_TEXTS):
            continue
        bounds = list(map(int, re.findall(r"\d+", node.get("bounds", ""))))
        if len(bounds) != 4:
            continue
        x = (bounds[0] + bounds[2]) // 2
        y = (bounds[1] + bounds[3]) // 2
        log(f"点击「{text}」({x}, {y})")
        adb("shell", "input", "tap", str(x), str(y))
        return True
    return False


def watch():
    log(f"设备 {SERIAL}：监听安装确认页，Ctrl+C 退出")
    warned = False
    while True:
        if not warned and is_locked():
            log("提示：屏幕处于锁屏状态，请手动解锁，否则点击无效")
            warned = True
        if tap_confirm():
            time.sleep(2)
        else:
            time.sleep(1)


def install(apk):
    if not os.path.isfile(apk):
        sys.exit(f"APK 文件不存在: {apk}")
    wake_screen()
    if is_locked():
        sys.exit("屏幕处于锁屏状态，请先手动解锁后再安装")
    log(f"设备 {SERIAL}：安装 {apk}")
    proc = subprocess.Popen(
        [ADB, "-s", SERIAL, "install", "-r", "-t", apk],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    started = time.time()
    taps = 0
    while proc.poll() is None:
        if time.time() - started > TIMEOUT:
            proc.kill()
            sys.exit(f"安装超时（{TIMEOUT}s），已终止")
        if tap_confirm():
            taps += 1
            time.sleep(2)
        else:
            time.sleep(1)
    output = proc.stdout.read() if proc.stdout else ""
    ok = proc.returncode == 0
    log(f"{'成功' if ok else '失败'}：退出码 {proc.returncode}，自动点击 {taps} 次，"
        f"耗时 {time.time() - started:.1f}s")
    for line in output.strip().splitlines():
        print("  " + line)
    return 0 if ok else 1


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0 if len(sys.argv) >= 2 else 2
    check_adb()
    pick_device()
    if sys.argv[1] == "--watch":
        try:
            watch()
        except KeyboardInterrupt:
            return 0
        return 0
    return install(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
