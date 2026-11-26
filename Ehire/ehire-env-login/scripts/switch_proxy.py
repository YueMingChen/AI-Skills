#!/usr/bin/env python3
"""切换系统 Wi-Fi 代理（主机名/端口），让 Ehire 调试包自动切换到 QA/DEV 环境。

用法：
    python3 switch_proxy.py qa
    python3 switch_proxy.py dev

原理：App 的 SystemProxyHelper 读取当前 Wi-Fi 的 LinkProperties.httpProxy，
命中 10.100.2.150:3128 / 10.100.6.106:3128 后自动切换到对应域账号环境。
设备未 root，因此通过系统设置 UI 修改（与手工操作一致）。
"""

import re
import sys
import time

import adbui as ui

ENVS = {
    "qa": ("10.100.2.150", 3128, "QA环境"),
    "dev": ("10.100.6.106", 3128, "DEV环境"),
}


def normalize_env(value):
    value = (value or "").strip().lower()
    if value in ("qa", "test", "测试", "qa环境"):
        return "qa"
    if value in ("dev", "开发", "dev环境"):
        return "dev"
    raise SystemExit("未知环境：%s（可选 qa / dev）" % value)


def current_proxy():
    """返回当前 Wi-Fi 生效代理 (host, port)，未配置返回 (None, 0)。"""
    out = ui.adb("shell", "dumpsys", "connectivity")
    blocks = out.split("NetworkAgentInfo{")
    for block in blocks:
        if "WIFI" not in block:
            continue
        match = re.search(r"HttpProxy: \[([^\]]*)\] (\d+)", block)
        if match:
            return match.group(1), int(match.group(2))
    match = re.search(r"HttpProxy: \[([^\]]*)\] (\d+)", out)
    if match:
        return match.group(1), int(match.group(2))
    return None, 0


def current_ssid():
    out = ui.adb("shell", "cmd", "wifi", "status")
    match = re.search(r'Wifi is connected to "([^"]+)"', out)
    return match.group(1) if match else None


def row_value(nodes, label):
    """读取详情页某个 label 右侧的值文本。"""
    label_node = ui.find(nodes, text=label, exact=True)
    if label_node is None:
        return None
    candidates = []
    for node in nodes:
        if not node.text or node.text == label:
            continue
        if abs(node.cy - label_node.cy) <= 16 and node.x1 > label_node.x2 - 20:
            candidates.append(node)
    candidates.sort(key=lambda n: n.x1)
    return candidates[0].text.strip() if candidates else None


def open_wifi_detail(ssid):
    ui.adb("shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS")
    time.sleep(2.0)
    deadline = time.time() + 12
    while time.time() < deadline:
        nodes = ui.nodes()
        target = ui.find(nodes, text=ssid, exact=True) if ssid else None
        if target is None:
            target = ui.find(nodes, text="已连接")
            if target is not None and target.parent is not None:
                target = target.parent
        if target is not None:
            ui.tap_node(target)
            time.sleep(1.8)
            return True
        time.sleep(1.0)
    return False


def tap_proxy_row():
    nodes = ui.nodes()
    label = ui.find(nodes, text="代理", exact=True)
    if label is None:
        return False
    ui.tap_node(label)
    time.sleep(1.2)
    return True


def choose_manual():
    if ui.tap_text("手动", timeout=6):
        time.sleep(1.2)
        return True
    return False


def find_edit_dialog():
    for _ in range(4):
        nodes = ui.nodes()
        edit = ui.find(nodes, cls="android.widget.EditText")
        if edit is not None:
            return edit
        time.sleep(0.6)
    return None


def set_field(host_or_port, value, attempts=2):
    """点击某行（主机名/端口）并在弹窗里改成 value。"""
    for _ in range(attempts):
        node = ui.scroll_until(host_or_port, max_scrolls=4,
                               direction="up" if host_or_port == "端口" else "down")
        if node is None:
            continue
        ui.tap_node(node)
        time.sleep(1.0)
        edit = find_edit_dialog()
        if edit is None:
            # 某些系统直接内联编辑
            nodes = ui.nodes()
            edit = ui.find(nodes, cls="android.widget.EditText")
        if edit is None:
            continue
        ui.tap_node(edit)
        time.sleep(0.6)
        ui.clear_focused(24)
        ui.input_text(str(value))
        time.sleep(0.6)
        if ui.tap_text("确定", timeout=3, exact=True) or ui.tap_text("保存", timeout=2, exact=True):
            time.sleep(1.2)
            return True
    return False


def switch_env(env, verbose=True):
    env = normalize_env(env)
    host, port, label = ENVS[env]
    cur_host, cur_port = current_proxy()
    if cur_host == host and cur_port == port:
        if verbose:
            print("代理已是 %s：%s:%d，跳过设置" % (label, host, port))
        return True

    ssid = current_ssid()
    if not verbose:
        pass
    else:
        print("当前代理：%s:%s，目标：%s %s:%d，SSID=%s" %
              (cur_host, cur_port, label, host, port, ssid))

    if not open_wifi_detail(ssid):
        raise RuntimeError("未能进入 Wi-Fi 详情页（请确认已连接 Wi-Fi，SSID=%s）" % ssid)

    if ui.wait_text("代理", timeout=8) is None:
        raise RuntimeError("Wi-Fi 详情页未找到「代理」设置项")

    if not tap_proxy_row():
        raise RuntimeError("点击「代理」失败")
    if ui.find(ui.nodes(), text="手动") is not None:
        choose_manual()
    else:
        nodes = ui.nodes()
        manual = ui.find(nodes, text="手动")
        if manual is not None:
            ui.tap_node(manual)
            time.sleep(1.2)

    if ui.wait_text("主机名", timeout=8) is None:
        raise RuntimeError("选择手动代理后未出现「主机名」输入项")

    nodes = ui.nodes()
    ui_host = row_value(nodes, "主机名")
    ui_port = row_value(nodes, "端口")
    if verbose:
        print("界面当前：主机名=%s 端口=%s" % (ui_host, ui_port))

    if ui_host != host:
        if not set_field("主机名", host):
            raise RuntimeError("设置主机名失败")
        if verbose:
            print("主机名已改为 %s" % host)

    nodes = ui.nodes()
    ui_port = row_value(nodes, "端口")
    if str(ui_port).strip() != str(port):
        if not set_field("端口", port):
            raise RuntimeError("设置端口失败")
        if verbose:
            print("端口已改为 %d" % port)

    # 退出 Wi-Fi 详情页后系统才会把新代理下发到当前网络（实测 vivo 必需）。
    ui.keyevent(4)
    time.sleep(1.5)

    deadline = time.time() + 20
    while time.time() < deadline:
        cur_host, cur_port = current_proxy()
        if cur_host == host and cur_port == port:
            if verbose:
                print("切换成功：%s %s:%d" % (label, host, port))
            return True
        time.sleep(1.0)
    raise RuntimeError("代理未生效，当前仍为 %s:%s" % (cur_host, cur_port))


def main():
    if len(sys.argv) < 2:
        print("用法：python3 switch_proxy.py qa|dev")
        return 2
    ui.require_device()
    try:
        switch_env(sys.argv[1])
        return 0
    except Exception as exc:
        print("切换失败：%s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
