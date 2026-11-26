#!/usr/bin/env python3
"""解析 Android uiautomator dump 的 XML，输出节点的 text、bounds 与中心坐标。

用法:
    uiparse.py <ui.xml>                 # 所有带 text 的节点
    uiparse.py <ui.xml> --text 附件      # 只输出 text 含关键词的节点
    uiparse.py <ui.xml> --clickable     # 只输出可点击节点（含 text 为空的）
    uiparse.py <ui.xml> --min-h 400 --min-w 900   # 过滤出大块卡片区域

可用 `adb shell cat /sdcard/ui.xml > /tmp/ui.xml` 先把 dump 拉下来再解析。
"""
import re
import sys
import html


def parse_args(argv):
    path = None
    text_filter = None
    clickable_only = False
    min_h = 0
    min_w = 0
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--text":
            text_filter = argv[i + 1]
            i += 2
        elif a == "--clickable":
            clickable_only = True
            i += 1
        elif a == "--min-h":
            min_h = int(argv[i + 1])
            i += 2
        elif a == "--min-w":
            min_w = int(argv[i + 1])
            i += 2
        else:
            path = a
            i += 1
    return path, text_filter, clickable_only, min_h, min_w


def main():
    path, text_filter, clickable_only, min_h, min_w = parse_args(sys.argv[1:])
    if not path:
        print(__doc__)
        sys.exit(1)
    with open(path, encoding="utf-8", errors="ignore") as f:
        xml = f.read()

    nodes = re.findall(r"<node\b[^>]*>", xml)
    for node in nodes:
        text = re.search(r'text="([^"]*)"', node)
        text = html.unescape(text.group(1)) if text else ""
        bounds = re.search(r'bounds="(\[\d+,\d+\]\[\d+,\d+\])"', node)
        if not bounds:
            continue
        nums = list(map(int, re.findall(r"\d+", bounds.group(1))))
        x1, y1, x2, y2 = nums
        w, h = x2 - x1, y2 - y1
        clickable = 'clickable="true"' in node

        if clickable_only and not clickable:
            continue
        if min_h and h < min_h:
            continue
        if min_w and w < min_w:
            continue
        if text_filter and text_filter not in text:
            continue
        if not text and not clickable_only:
            continue

        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        tag = "CLICK" if clickable else "     "
        print(f"{tag} {text} [{x1},{y1}][{x2},{y2}] center=({cx},{cy})")


if __name__ == "__main__":
    main()
