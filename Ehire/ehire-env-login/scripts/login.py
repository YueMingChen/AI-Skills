#!/usr/bin/env python3
"""一键切换 QA/DEV 环境并登录网才/商业化测试账号到 Ehire 主页。

用法：
    python3 login.py --product wangcai --env qa
    python3 login.py --product commercial --env dev
    python3 login.py --product 网才 --env qa --phone 13501010102

流程：
    切换系统 Wi-Fi 代理 -> 启动 App -> 已登录先退出 -> 手机号 + 获取短信验证码
    -> 内部短信自动填充（极验出现时自动滑）-> 校验进入 EhireHomeActivity
"""

import argparse
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import adbui as ui
import geetest
import switch_proxy

PACKAGE = "com.job.android.ehire"
HOME_ACTIVITY = "EhireHomeActivity"
LOGIN_ACTIVITY = "LoginRegisterActivity"

ACCOUNTS = {
    "wangcai": {
        "label": "网才",
        "phones": {"qa": "13501010102", "dev": "18516139412"},
    },
    "commercial": {
        "label": "商业化",
        "phones": {"qa": "17717845700", "dev": "13348296722"},
    },
}

ALIASES = {
    "wangcai": "wangcai", "网才": "wangcai", "ehire": "wangcai",
    "commercial": "commercial", "商业化": "commercial", "onl": "commercial",
    "shangye": "commercial", "商业": "commercial",
}


def normalize_product(value):
    key = ALIASES.get((value or "").strip().lower())
    if key is None:
        raise SystemExit("未知账号类型：%s（可选 wangcai/网才 或 commercial/商业化）" % value)
    return key


def ensure_installed():
    if PACKAGE not in ui.adb("shell", "pm", "list", "packages", PACKAGE):
        raise SystemExit("设备未安装 %s（请先安装 debug 包）" % PACKAGE)


def is_home():
    return HOME_ACTIVITY in ui.activity()


def is_login():
    return LOGIN_ACTIVITY in ui.activity()


HOME_TAB_TEXTS = ("人才管理", "人才望远镜", "人才搜索", "人才推荐", "搜索人才", "会员中心", "消息", "我的")


def visible_home_tabs(nodes=None):
    try:
        nodes = nodes if nodes is not None else ui.nodes()
    except Exception:
        return []
    return [text for text in HOME_TAB_TEXTS
            if ui.find(nodes, text=text, exact=True, min_y=1900) is not None]


def ensure_home_visible(max_back=4):
    """首页可能被 AI 淘金/筛选/引导页盖住，返回直到看到底部导航。
    返回 True=确认在主页，False=确认不在，None=界面不可读（动画阻塞 dump）。"""
    for _ in range(max_back):
        try:
            nodes = ui.nodes()
        except Exception:
            return None
        if len(set(visible_home_tabs(nodes))) >= 2:
            return True
        ui.keyevent(4)
        time.sleep(1.2)
    return False


def screen_size():
    match = re.search(r"(\d+)x(\d+)", ui.adb("shell", "wm", "size"))
    return (int(match.group(1)), int(match.group(2))) if match else (1080, 2376)


def tap_my_tab_coord():
    width, height = screen_size()
    ui.tap(int(width * 0.90), int(height * 0.96))
    time.sleep(2.0)


def tap_settings_coord(product):
    """界面无法 dump 时，按右上角图标坐标依次尝试（网才/商业化图标数量不同）。"""
    width, height = screen_size()
    ratios = (0.80, 0.92, 0.68) if product == "commercial" else (0.92, 0.80, 0.68)
    for ratio in ratios:
        ui.tap(int(width * ratio), int(height * 0.078))
        time.sleep(1.6)
        if "SettingActivity" in ui.activity():
            return True
        ui.keyevent(4)
        time.sleep(1.2)
    return False


def open_settings_from_mine(product):
    for _ in range(2):
        visible = ensure_home_visible()
        if visible is True:
            me = ui.find(ui.nodes(), text="我的", exact=True, min_y=1800)
            if me is not None:
                ui.tap_node(me)
                time.sleep(2.0)
                try:
                    nodes = ui.nodes()
                except Exception:
                    nodes = None
                if nodes is not None:
                    candidates = [
                        node for node in nodes
                        if node.cls.endswith("ImageView") and node.clickable
                        and node.cy < 340 and node.cx > 500
                    ]
                    candidates.sort(key=lambda node: node.cx, reverse=True)
                    for node in candidates[:3]:
                        ui.tap_node(node)
                        time.sleep(1.6)
                        if "SettingActivity" in ui.activity():
                            return True
                        ui.keyevent(4)
                        time.sleep(1.2)
                if tap_settings_coord(product):
                    return True
                continue
        # 无法确认主页时刚重启过 App，直接按坐标进入我的页
        tap_my_tab_coord()
        if tap_settings_coord(product):
            return True
    return False


def logout(product):
    """从主页退出到登录页。"""
    print("检测到已登录主页，先退出登录")
    if ensure_home_visible() is not True:
        print("界面不可读（动画浮层/筛选页），重启 App 后重试退出")
        ui.adb("shell", "am", "force-stop", PACKAGE)
        time.sleep(0.8)
        ui.launch(PACKAGE)
        time.sleep(3.0)
        if is_login():
            print("已在登录页，无需退出")
            return True
    if not open_settings_from_mine(product):
        raise RuntimeError("未能打开设置页（未找到右上角设置入口）")
    node = ui.scroll_until("退出登录", max_scrolls=9)
    if node is None:
        raise RuntimeError("设置页未找到「退出登录」")
    ui.tap_node(node)
    time.sleep(1.2)
    # 注意用 exact：确认框标题「你确定要退出登录吗？」也包含「确定」
    if not ui.tap_text("确定", timeout=6, exact=True):
        raise RuntimeError("退出登录确认框未出现")
    deadline = time.time() + 20
    while time.time() < deadline:
        if is_login():
            print("已退出到登录页")
            return True
        time.sleep(1.0)
    raise RuntimeError("退出登录后未回到登录页，当前：%s" % ui.activity())


def ensure_login_form(product):
    for _ in range(3):
        if ui.wait_text("获取短信验证码", timeout=10) is not None:
            return True
        ui.adb("shell", "am", "force-stop", PACKAGE)
        time.sleep(1.0)
        ui.launch(PACKAGE)
        time.sleep(3.0)
        if is_home():
            logout(product)
    return ui.wait_text("获取短信验证码", timeout=10) is not None


def ensure_entry():
    """把 App 带到「登录页」或「主页」，其它页面先返回、再兜底重启。"""
    ui.launch(PACKAGE)
    time.sleep(2.5)
    for _ in range(6):
        if is_login() or is_home():
            return True
        ui.keyevent(4)
        time.sleep(1.0)
    ui.adb("shell", "am", "force-stop", PACKAGE)
    time.sleep(1.0)
    ui.launch(PACKAGE)
    time.sleep(3.0)
    deadline = time.time() + 15
    while time.time() < deadline:
        if is_login() or is_home():
            return True
        time.sleep(1.0)
    return False


def read_env_status():
    node = ui.find(ui.nodes(), text="域账号环境：")
    return node.text if node is not None else ""


def wait_env_ready(env_label, timeout=25):
    deadline = time.time() + timeout
    status = ""
    while time.time() < deadline:
        status = read_env_status()
        if env_label in status and "已登录" in status:
            return status
        if env_label in status and "未登录" in status:
            raise RuntimeError(
                "内部短信域账号在%s未登录，无法自动取验证码。"
                "请在登录页点击「登录」完成 SSO 后重跑本命令。当前状态：%s" % (env_label, status))
        time.sleep(1.5)
    raise RuntimeError("等待域账号环境切换超时，当前状态：%s" % status)


def fill_phone(phone):
    nodes = ui.nodes()
    edit = None
    for node in nodes:
        if node.cls.endswith("EditText") and node.x1 > 320 and node.y1 < 1000:
            edit = node
            break
    if edit is None:
        edit = ui.find(nodes, text="手机", cls="EditText")
    if edit is None:
        raise RuntimeError("未找到手机号输入框")
    ui.tap_node(edit)
    time.sleep(0.8)
    ui.clear_focused(20)
    ui.input_text(phone)
    time.sleep(0.6)
    ui.keyevent(4)
    time.sleep(0.8)

    nodes = ui.nodes()
    checkbox = ui.find(nodes, cls="CheckBox")
    if checkbox is not None and not checkbox.checked:
        ui.tap_node(checkbox)
        time.sleep(0.5)
    print("已输入手机号 %s" % phone)


def handle_popups():
    """关闭登录后常见的升级/权限弹窗；不处理登录页协议勾选。"""
    for _ in range(2):
        try:
            nodes = ui.nodes()
        except Exception:
            return
        for text in ("我知道了", "知道了", "允许", "仅在使用中允许", "始终允许", "以后再说", "跳过"):
            node = ui.find(nodes, text=text, exact=True)
            if node is not None:
                print("关闭弹窗：%s" % text)
                ui.tap_node(node)
                time.sleep(1.0)
                break


def wait_home(timeout=150):
    deadline = time.time() + timeout
    last_check = 0.0
    while time.time() < deadline:
        if is_home():
            time.sleep(1.5)
            ensure_home_visible()
            handle_popups()
            return True
        if "SwitchCompanyActivity" in ui.activity():
            print("账号绑定多个企业，App 停在「切换企业」页；自动点击企业登录未生效，请手工选择企业后重跑")
            return False
        if time.time() - last_check > 4:
            last_check = time.time()
            if geetest.present():
                print("出现极验滑块，自动验证")
                geetest.solve()
            else:
                try:
                    nodes = ui.nodes()
                except Exception:
                    nodes = []
                if ui.find(nodes, text="未获取到登录信息") is not None:
                    print("启动页提示「未获取到登录信息」，停止等待")
                    return False
                handle_popups()
        time.sleep(1.5)
    return False


def report_home():
    tabs = list(dict.fromkeys(visible_home_tabs()))
    print("当前主页底部入口：%s" % (" / ".join(tabs) if tabs else "未识别（可能被浮层遮挡）"))


def run(product, env, phone=None, skip_proxy=False):
    ui.require_device()
    ensure_installed()
    product_key = normalize_product(product)
    env_key = switch_proxy.normalize_env(env)
    account = ACCOUNTS[product_key]
    phone = phone or account["phones"][env_key]
    env_label = switch_proxy.ENVS[env_key][2]

    print("目标：%s + %s，账号 %s" % (account["label"], env_label, phone))

    if not skip_proxy:
        switch_proxy.switch_env(env_key, verbose=True)
    else:
        print("跳过代理切换")

    if not ensure_entry():
        raise RuntimeError("未能进入登录页或主页，当前：%s" % ui.activity())

    if is_home():
        logout(product_key)

    if not ensure_login_form(product_key):
        raise RuntimeError("未能进入手机号登录页，当前：%s" % ui.activity())

    # 清掉可能残留的 EhireLaunchActivity 错误页：单实例 Activity 不会接收新 token，
    # 会导致「未获取到登录信息」。登录前重启一次，保证任务栈干净。
    ui.adb("shell", "am", "force-stop", PACKAGE)
    time.sleep(0.8)
    ui.launch(PACKAGE)
    time.sleep(2.5)
    if is_home():
        logout(product_key)
    if not ensure_login_form(product_key):
        raise RuntimeError("重启后未能进入手机号登录页，当前：%s" % ui.activity())

    status = wait_env_ready(env_label)
    print("域账号状态：%s" % status)

    fill_phone(phone)
    if ui.wait_text("获取短信验证码", timeout=5) is None:
        raise RuntimeError("登录页未找到「获取短信验证码」")

    ui.tap_text("获取短信验证码", timeout=5)
    time.sleep(2.5)

    if geetest.present():
        print("出现极验滑块，开始自动验证")
        if not geetest.solve():
            raise RuntimeError("极验滑块自动验证失败，请手工完成后重跑")
        time.sleep(1.5)

    print("等待短信自动填充并登录（最长 %d 秒）" % 150)
    if not wait_home():
        raise RuntimeError("等待进入主页超时，当前：%s" % ui.activity())

    print("登录成功，已进入 %s" % ui.activity())
    report_home()
    return True


def main():
    parser = argparse.ArgumentParser(description="Ehire QA/DEV 环境切换并登录测试账号")
    parser.add_argument("--product", required=True, help="wangcai/网才 或 commercial/商业化")
    parser.add_argument("--env", required=True, help="qa 或 dev")
    parser.add_argument("--phone", default=None, help="可选，覆盖默认手机号")
    parser.add_argument("--skip-proxy", action="store_true", help="不切换系统代理")
    args = parser.parse_args()
    try:
        run(args.product, args.env, args.phone, args.skip_proxy)
        return 0
    except Exception as exc:
        print("失败：%s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
