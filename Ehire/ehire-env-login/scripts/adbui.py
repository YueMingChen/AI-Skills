#!/usr/bin/env python3
"""adb + uiautomator 基础操作，供 ehire-env-login skill 使用。"""

import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET

ADB = os.environ.get("ADB", "adb")
DUMP_PATH = "/sdcard/ehire_ui.xml"


def adb(*args, timeout=60):
    result = subprocess.run([ADB, *args], capture_output=True, text=True, timeout=timeout)
    return result.stdout.strip()


def require_device():
    state = adb("get-state")
    if state != "device":
        raise SystemExit("设备未就绪（adb state=%s），先执行 adb devices 检查连接" % (state or "无设备"))


def activity():
    """返回当前前台组件，如 com.job.android.ehire/com.ehire.android.pages.EhireHomeActivity。"""
    out = adb("shell", "dumpsys", "activity", "activities")
    match = re.search(r"topResumedActivity=ActivityRecord\{[^}]*\s+u\d+\s+(\S+)\s", out)
    return match.group(1) if match else ""


def launch(package="com.job.android.ehire"):
    adb("shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1")


def dump_xml(retries=6, interval=1.0):
    last = ""
    for _ in range(retries):
        # 先删旧文件：dump 失败时会保留上一次的 XML，读旧树会误判界面状态。
        adb("shell", "rm", "-f", DUMP_PATH)
        adb("shell", "uiautomator", "dump", DUMP_PATH)
        xml = adb("shell", "cat", DUMP_PATH)
        if xml.startswith("<?xml"):
            return xml
        last = xml
        time.sleep(interval)
    raise RuntimeError("uiautomator dump 失败（界面持续动画或卡死）：%s" % last[:200])


class Node:
    __slots__ = ("text", "desc", "cls", "x1", "y1", "x2", "y2", "clickable", "checked", "enabled", "parent")

    def __init__(self, elem, parent=None):
        self.text = elem.get("text", "") or ""
        self.desc = elem.get("content-desc", "") or ""
        self.cls = elem.get("class", "") or ""
        self.clickable = elem.get("clickable") == "true"
        self.checked = elem.get("checked") == "true"
        self.enabled = elem.get("enabled") == "true"
        self.parent = parent
        match = re.findall(r"\[(\d+),(\d+)\]", elem.get("bounds", ""))
        if match:
            (self.x1, self.y1), (self.x2, self.y2) = [(int(a), int(b)) for a, b in match]
        else:
            self.x1 = self.y1 = self.x2 = self.y2 = 0

    @property
    def cx(self):
        return (self.x1 + self.x2) // 2

    @property
    def cy(self):
        return (self.y1 + self.y2) // 2

    def __repr__(self):
        return "<%s text=%r desc=%r bounds=[%d,%d][%d,%d]>" % (
            self.cls.split(".")[-1], self.text, self.desc, self.x1, self.y1, self.x2, self.y2)


def nodes(xml=None):
    xml = xml or dump_xml()
    root = ET.fromstring(xml)
    result = []

    def walk(elem, parent=None):
        node = Node(elem, parent)
        node.parent = parent
        result.append(node)
        for child in elem:
            walk(child, node)

    walk(root)
    return result


def find(items, text=None, desc=None, exact=False, cls=None,
         min_x=None, max_x=None, min_y=None, max_y=None):
    for node in items:
        if text is not None:
            target = node.text
            if exact:
                if target != text:
                    continue
            elif text not in target:
                continue
        if desc is not None and desc not in node.desc:
            continue
        if cls is not None and cls not in node.cls:
            continue
        if min_x is not None and node.cx < min_x:
            continue
        if max_x is not None and node.cx > max_x:
            continue
        if min_y is not None and node.cy < min_y:
            continue
        if max_y is not None and node.cy > max_y:
            continue
        return node
    return None


def find_all(items, text=None, desc=None, exact=False, cls=None):
    result = []
    for node in items:
        if text is not None:
            if exact and node.text != text:
                continue
            if not exact and text not in node.text:
                continue
        if desc is not None and desc not in node.desc:
            continue
        if cls is not None and cls not in node.cls:
            continue
        result.append(node)
    return result


def tap(x, y):
    adb("shell", "input", "tap", str(int(x)), str(int(y)))


def tap_node(node):
    if node is None:
        raise RuntimeError("要点击的节点不存在")
    tap(node.cx, node.cy)


def keyevent(*codes):
    adb("shell", "input", "keyevent", *[str(c) for c in codes])


def swipe(x1, y1, x2, y2, duration=600):
    adb("shell", "input", "swipe", str(int(x1)), str(int(y1)),
        str(int(x2)), str(int(y2)), str(int(duration)))


def input_text(value):
    adb("shell", "input", "text", value)


def clear_focused(max_len=30):
    """光标移到末尾后连按删除键，清空当前输入框。"""
    keyevent(123, *([67] * max_len))


def screenshot(path):
    result = subprocess.run([ADB, "exec-out", "screencap", "-p"], capture_output=True, timeout=60)
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError("截图失败：%s" % result.stderr.decode("utf-8", "ignore")[:200])
    with open(path, "wb") as file:
        file.write(result.stdout)
    return path


def wait_text(text, timeout=15.0, interval=0.8, exact=False):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            node = find(nodes(), text=text, exact=exact)
        except Exception:
            node = None
        if node is not None:
            return node
        time.sleep(interval)
    return None


def wait_gone(text, timeout=10.0, interval=0.8):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if find(nodes(), text=text) is None:
                return True
        except Exception:
            return True
        time.sleep(interval)
    return False


def tap_text(text, timeout=10.0, exact=False):
    node = wait_text(text, timeout=timeout, exact=exact)
    if node is None:
        return False
    tap_node(node)
    return True


def scroll_until(text, max_scrolls=6, direction="up"):
    """在滚动列表中查找文案，找到返回节点。direction=up 表示内容上滑（看后面的内容）。"""
    for _ in range(max_scrolls):
        node = find(nodes(), text=text)
        if node is not None:
            return node
        if direction == "up":
            swipe(540, 2000, 540, 600, 350)
        else:
            swipe(540, 700, 540, 2000, 350)
        time.sleep(0.8)
    return find(nodes(), text=text)
