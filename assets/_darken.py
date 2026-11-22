# -*- coding: utf-8 -*-
"""矿物标本照做「油灯显影」色调映射，输出 _dk.jpg，原图保留。
关键：用 亮度×低饱和 判定「白底/浅色围岩」并压到近黑，
而「亮且高饱和」的矿石晶体高光完整保留 —— 只有矿石被光找出来。
金箔图为暗金黑底，无需处理。
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BG = np.array([28, 20, 13], dtype=np.float32)       # 洞窟暗面
BG_HI = np.array([66, 49, 31], dtype=np.float32)     # 被照亮的砂岩
NAMES = ['min-cinnabar', 'min-azurite', 'min-malachite', 'min-hematite']

def smoothstep(t):
    return t * t * (3 - 2 * t)

for name in NAMES:
    src = os.path.join(HERE, name + '.jpg')
    if not os.path.exists(src):
        print('skip missing', src)
        continue
    im = Image.open(src).convert('RGB')
    w, h = im.size
    if max(w, h) > 1100:
        im.thumbnail((1100, 1100))
        w, h = im.size
    a = np.asarray(im).astype(np.float32)

    L = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    mx = a.max(axis=2)
    mn = a.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)   # 0=灰白 1=纯色

    # 亮 × 灰 = 白底围岩，压得最狠；亮 × 艳 = 晶体高光，保留
    bright = smoothstep(np.clip((L - 95) / 160, 0, 1))
    chalk = bright * (1 - smoothstep(np.clip(sat / 0.55, 0, 1)))
    keep = np.clip(1 - 1.12 * chalk, 0.055, 1.0)

    # 暗角：四周沉入黑暗，中心矿石被照住
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
    vig = np.clip((d - 0.30) / 0.70, 0, 1) ** 1.35
    keep = np.clip(keep * (1 - 0.68 * vig), 0.04, 1.0)

    base = BG_HI + (BG - BG_HI) * bright[..., None]
    out = a * keep[..., None] + base * (1 - keep[..., None])
    np.clip(out, 0, 255, out=out)

    dst = os.path.join(HERE, name + '-dk.jpg')
    Image.fromarray(out.astype(np.uint8)).save(dst, 'JPEG', quality=84, optimize=True)
    print(f'{name}: {w}x{h} -> {os.path.getsize(dst)//1024}KB')

# 清理上一版误生成的金箔暗底（金箔用原图即可）
stale = os.path.join(HERE, 'min-gold-dk.jpg')
if os.path.exists(stale):
    os.remove(stale)
    print('removed stale min-gold-dk.jpg')
