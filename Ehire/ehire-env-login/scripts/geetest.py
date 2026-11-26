#!/usr/bin/env python3
"""自动完成极验滑块验证（登录页/验证码页点击获取验证码后可能出现）。

用法：
    python3 geetest.py            # 有极验就滑，没有直接返回
    python3 geetest.py --check    # 只检查当前是否出现极验

思路：截屏 -> 在验证弹窗图片区域内找最暗的拼图缺口 -> 按「缺口左边 - 拼图块初始左边」
换算拖动距离 -> adb swipe 拖动滑块；失败自动微调重试。
"""

import argparse
import sys
import time

import adbui as ui

PIECE_LEFT_RATIO = 0.038   # 拼图块初始左边相对图片左边缘
KNOB_X_RATIO = 0.108       # 滑块圆点中心相对图片左边缘
GAP_W_RATIO = 0.153        # 缺口宽度 / 图片宽度
GAP_H_RATIO = 0.225        # 缺口高度 / 图片高度


def captcha_nodes(nodes):
    dialog = ui.find(nodes, text="请通过以下验证")
    slider = ui.find(nodes, text="拖动滑块完成拼图")
    if dialog is None and slider is not None:
        dialog = slider
    return dialog, slider


def present(nodes=None):
    nodes = nodes or ui.nodes()
    return captcha_nodes(nodes)[0] is not None


def detect_gap(image_path, image_box):
    """返回缺口左边缘 x；失败返回 None。"""
    from PIL import Image
    import numpy as np

    x1, y1, x2, y2 = image_box
    gray = np.asarray(Image.open(image_path).convert("RGB")).astype("float32").mean(axis=2)
    width, height = x2 - x1, y2 - y1
    gap_w = max(50, int(width * GAP_W_RATIO))
    gap_h = max(50, int(height * GAP_H_RATIO))

    best = None
    start_x = x1 + int(width * 0.25)
    end_x = x2 - gap_w - 4
    start_y = y1 + int(height * 0.08)
    end_y = y2 - gap_h - int(height * 0.04)
    step = max(4, int(width / 106))
    for y in range(start_y, max(start_y + 1, end_y), step):
        for x in range(start_x, max(start_x + 1, end_x), step):
            win = gray[y:y + gap_h, x:x + gap_w]
            inside = float(win.mean())
            ring = np.concatenate([
                gray[max(y1, y - 12):y, x:x + gap_w].ravel(),
                gray[y + gap_h:min(y2, y + gap_h + 12), x:x + gap_w].ravel(),
                gray[y:y + gap_h, max(x1, x - 12):x].ravel(),
                gray[y:y + gap_h, x + gap_w:min(x2, x + gap_w + 12)].ravel(),
            ])
            if ring.size == 0:
                continue
            score = float(ring.mean()) - inside
            if best is None or score > best[0]:
                best = (score, x)
    if best is None or best[0] < 8:
        return None
    return best[1]


def solve(max_attempts=4, verbose=True):
    nodes = ui.nodes()
    dialog, slider = captcha_nodes(nodes)
    if dialog is None:
        if verbose:
            print("当前没有极验弹窗")
        return True

    for attempt in range(max_attempts):
        nodes = ui.nodes()
        dialog, slider = captcha_nodes(nodes)
        if dialog is None:
            return True
        if slider is None:
            time.sleep(1.0)
            continue

        x1, y1, x2, y2 = dialog.x1 + 8, dialog.y1 + 8, dialog.x2 - 8, dialog.y2 - 8
        iy2 = slider.y1 - 4
        if iy2 <= y1 + 80:
            iy2 = dialog.cy
        image_box = (x1, y1, x2, iy2)
        width = x2 - x1
        piece_left = x1 + int(width * PIECE_LEFT_RATIO)
        knob_x = x1 + int(width * KNOB_X_RATIO)
        knob_y = slider.cy

        shot = "/tmp/ehire_geetest.png"
        ui.screenshot(shot)
        gap_left = detect_gap(shot, image_box)
        if gap_left is None:
            if verbose:
                print("未识别到缺口，重试")
            time.sleep(1.5)
            continue

        adjust = [0, -10, 10, -18, 18][attempt] if attempt < 5 else 0
        distance = gap_left - piece_left + adjust
        if verbose:
            print("第 %d 次：缺口 x=%d，拖动 %d px" % (attempt + 1, gap_left, distance))
        if distance <= 0:
            time.sleep(1.0)
            continue
        ui.swipe(knob_x, knob_y, knob_x + distance, knob_y, 900)
        time.sleep(2.0)

        if ui.find(ui.nodes(), text="拖动滑块完成拼图") is None:
            if verbose:
                print("极验通过")
            time.sleep(1.0)
            return True
        time.sleep(1.0)

    if verbose:
        print("极验自动滑动失败，请手工拖动滑块完成验证后重试")
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="只检查是否有极验")
    parser.add_argument("--max-attempts", type=int, default=4)
    args = parser.parse_args()
    ui.require_device()
    if args.check:
        print("有极验" if present() else "无极验")
        return 0
    return 0 if solve(max_attempts=args.max_attempts) else 2


if __name__ == "__main__":
    sys.exit(main())
