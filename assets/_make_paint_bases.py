# -*- coding: utf-8 -*-
"""
一眼千年 · S7「把颜色还给它」待上色底图生成器

把 12 幅经典敦煌壁画处理成「颜色褪去、只留明暗与线条」的暖绢素稿，
再以 base64 data URI 写入 assets/paint-images.js。

为什么用 data URI：本地 file:// 直接打开时，相对路径的 <img> 会把 canvas
标记为 tainted，导致 toDataURL 导出失败。内嵌后画布保持干净，
双击 html 与在线部署都能正常「收下这幅画」。

新增图源（均为古代壁画，图像取自公开专题页 / 官方机构）：
  mural-257-nine-deer       搜狐《敦煌石窟》北魏 257 窟专题（伯希和图录系统）
  mural-112-pipa            敦煌研究院官网 dha.ac.cn 第 112 窟
  mural-407-three-hares     搜狐《敦煌石窟》隋 407 窟三兔藻井专题
  mural-bodhisattva         酒泉市文旅局「莫高窟最著名的十幅壁画」
  mural-156-zhangyichao     同上，第 156 窟《张议潮统军出行图》局部

重新生成：python assets/_make_paint_bases.py
换图只需改下面的 SOURCES 列表；crop 可裁掉原图底部的图注文字。
"""
import base64
import io
import json
import os
import random
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
BOX = 900               # 底图最长边（等比缩放，横竖图都完整保留）
random.seed(2026)

SOURCES = [
    dict(file="mural-257-nine-deer.jpg",     id="deer",    name="九色鹿",   meta="第 257 窟 · 北魏",   note="土红打底，鹿身留白，山石试石绿", crop=.035),
    dict(file="mural-112-pipa.jpg",          id="pipa",    name="伎乐图",   meta="第 112 窟 · 中唐",   note="石绿铺地，衣裙朱砂；反弹琵琶就在这铺乐舞里"),
    dict(file="mural-407-three-hares.jpg",   id="hares",   name="三兔藻井", meta="第 407 窟 · 隋",     note="井心三兔留白，莲瓣试朱砂，外圈石青"),
    dict(file="mural-220-emperor.jpg",       id="emperor", name="帝王图",   meta="第 220 窟 · 初唐",   note="冕服朱砂，随从石青，仪仗用金"),
    dict(file="mural-156-zhangyichao.jpg",   id="march",   name="出行图",   meta="第 156 窟 · 晚唐",   note="红袍主角最亮，鞍马赭石，旗仗石绿"),
    dict(file="mural-bodhisattva.jpg",       id="bodhi",   name="菩萨",     meta="盛唐 · 菩萨",        note="头光用金，璎珞朱砂，天衣月白"),
    dict(file="apsara-detail.jpg",           id="apsara",  name="双飞天",   meta="莫高窟 · 伎乐天",    note="飘带用石青，衣裙试石绿，肌肤留米白"),
    dict(file="dancer.jpg",                  id="dancer",  name="舞乐天",   meta="莫高窟 · 经变乐舞",  note="长裙试朱砂，披帛用月白，底色赭石"),
    dict(file="mural-428-apsaras.jpg",       id="preach",  name="说法图",   meta="第 428 窟 · 北朝",   note="背光用金，袈裟试土红，供养人石青"),
    dict(file="mural-buddha.jpg",            id="story",   name="本生故事", meta="第 254 窟 · 北朝",   note="大块土红打底，山石石绿，兽身留赭"),
    dict(file="apsara-flute.jpg",            id="flute",   name="吹笛飞天", meta="莫高窟 · 唐代",      note="飘带石青，裙裾朱砂，云气月白"),
    dict(file="mural-217.jpg",               id="sutra",   name="经变画",   meta="第 217 窟 · 盛唐",   note="殿宇赭石，水池石绿，菩萨衣朱砂"),
]


def make_base(spec):
    im = Image.open(os.path.join(HERE, spec["file"])).convert("RGB")
    w, h = im.size
    if spec.get("crop"):
        im = im.crop((0, 0, w, round(h * (1 - spec["crop"]))))
        w, h = im.size
    s = BOX / max(w, h)
    nw, nh = round(w * s), round(h * s)
    im = im.resize((nw, nh), Image.LANCZOS)

    # 1. 去色：灰度 → 自动色阶 → 降对比 → 提亮，让线条留得住、底色不闷
    g = ImageOps.grayscale(im)
    g = ImageOps.autocontrast(g, cutoff=1)
    g = ImageEnhance.Contrast(g).enhance(0.92)
    g = ImageEnhance.Brightness(g).enhance(1.10)

    # 2. 暖绢 duotone：暗部沉褐、亮部绢白，像泥壁上褪尽颜色的素稿
    lo, hi = (86, 70, 52), (242, 230, 204)
    lut = []
    for c in range(3):
        lut += [max(0, min(255, round(lo[c] + (hi[c] - lo[c]) * v / 255)))
                for v in range(256)]
    out = Image.merge("RGB", (g, g, g)).point(lut)

    # 3. 壁面颗粒
    noise = Image.effect_noise((nw, nh), 14).convert("L")
    out = Image.blend(out, Image.merge("RGB", (noise, noise, noise)), 0.05)

    # 4. 斑驳剥落：随机暗斑模糊后轻叠
    spots = Image.new("L", (nw, nh), 0)
    d = ImageDraw.Draw(spots)
    for _ in range(48):
        x, y = random.randrange(nw), random.randrange(nh)
        r = random.randrange(18, 80)
        d.ellipse([x - r, y - r, x + r, y + r], fill=random.randrange(12, 38))
    spots = spots.filter(ImageFilter.GaussianBlur(18)).point(lambda v: int(v * 0.55))
    out = Image.composite(Image.new("RGB", (nw, nh), (74, 56, 38)), out, spots)

    # 5. 四角沉色，收进洞窟的暗里
    rg = Image.radial_gradient("L").resize((nw, nh)).point(lambda v: int(v * 0.22))
    out = Image.composite(Image.new("RGB", (nw, nh), (58, 44, 30)), out, rg)

    buf = io.BytesIO()
    out.save(buf, "JPEG", quality=76, subsampling=2, optimize=True)
    raw = buf.getvalue()
    return nw, nh, base64.b64encode(raw).decode("ascii"), len(raw)


items = []
for s in SOURCES:
    w, h, b64, n = make_base(s)
    items.append({
        "id": s["id"], "name": s["name"], "meta": s["meta"], "note": s["note"],
        "w": w, "h": h, "src": "data:image/jpeg;base64," + b64,
    })
    print(f'{s["name"]:<8} {w}x{h}  {n/1024:.0f} KB')

head = (
    "/* 一眼千年 · S7 待上色底图（由 _make_paint_bases.py 生成，请勿手改）\n"
    "   12 幅经典壁画暖绢素稿 + data URI：保证 file:// 下 canvas 可导出 */\n"
)
js = head + "window.PAINT_IMAGES = " + json.dumps(items, ensure_ascii=False, indent=1) + ";\n"
out_path = os.path.join(HERE, "paint-images.js")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(js)
print(f"\n共 {len(items)} 幅 → {out_path}  ({os.path.getsize(out_path)/1024:.0f} KB)")
