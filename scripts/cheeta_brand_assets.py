#!/usr/bin/env python3
"""Cheetagram part 7: build all branded launcher/splash assets from the generated master.

- Neutralizes the near-black background of the generated art to pure #000000 (OLED)
- Replaces legacy ic_launcher / ic_launcher_round (keeps stock per-density alpha masks)
- Rebuilds adaptive foreground (face inside the 66/108 safe zone) + solid black background
- Builds a proper monochrome (themed icon) glyph from the face luminance
- Builds the splash PNG (drawable-nodpi/cheeta_splash.png)
"""
import os
import numpy as np
from PIL import Image, ImageChops

SRC = '/tmp/cheeta_icon_a.png'
APP = '/home/z/telegram/TMessagesProj_App/src/main/res'
MAIN = '/home/z/telegram/TMessagesProj/src/main/res'

DENSITIES_LEGACY = [('mdpi', 48), ('hdpi', 72), ('xhdpi', 96), ('xxhdpi', 144), ('xxxhdpi', 192)]
DENSITIES_ADAPTIVE = [('mdpi', 108), ('hdpi', 162), ('xhdpi', 216), ('xxhdpi', 324), ('xxxhdpi', 432)]

master = Image.open(SRC).convert('RGB')

# --- 1. neutralize desaturated near-black background -> pure #000000 ---
arr = np.asarray(master).astype(np.int16)
mx = arr.max(axis=2)
mn = arr.min(axis=2)
bg_key = (mx - mn < 14) & (mx < 48)
arr[bg_key] = 0
master = Image.fromarray(arr.astype(np.uint8))

# --- 2. tight square crop around the face, re-centered on black ---
diff = ImageChops.difference(master, Image.new('RGB', master.size, (0, 0, 0))).convert('L')
bbox = diff.point(lambda v: 255 if v > 14 else 0).getbbox()
face = master.crop(bbox)
fw, fh = face.size
side = max(fw, fh)
sq = Image.new('RGB', (side, side), (0, 0, 0))
sq.paste(face, ((side - fw) // 2, (side - fh) // 2))
print('face bbox:', bbox, 'square:', side)

# --- 3. legacy launcher icons: reuse stock alpha masks ---
for d, size in DENSITIES_LEGACY:
    for name in ('ic_launcher', 'ic_launcher_round'):
        stock = Image.open(f'{APP}/mipmap-{d}/{name}.png').convert('RGBA')
        mask = stock.split()[3]
        art = sq.resize((size, size), Image.LANCZOS)
        out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        out.paste(art, (0, 0), mask)
        out.save(f'{APP}/mipmap-{d}/{name}.png')
        print('legacy', d, name, out.size)

# --- 4. adaptive foreground (face at 62% of canvas, inside safe zone) + black background ---
for d, size in DENSITIES_ADAPTIVE:
    fg = Image.new('RGBA', (size, size), (0, 0, 0, 255))
    fsize = round(size * 0.62)
    art = sq.resize((fsize, fsize), Image.LANCZOS)
    fg.paste(art, ((size - fsize) // 2, (size - fsize) // 2))
    fg.save(f'{APP}/mipmap-{d}/cheeta_foreground.png')
    Image.new('RGB', (size, size), (0, 0, 0)).save(f'{APP}/mipmap-{d}/cheeta_background.png')
    print('adaptive', d, 'fg/bg', size)

# --- 5. monochrome themed-icon glyph: solid silhouette, smooth edges ---
for d, size in DENSITIES_ADAPTIVE:
    fsize = round(size * 0.62)
    g = sq.resize((fsize, fsize), Image.LANCZOS).convert('L')
    ga = np.asarray(g).astype(np.int16)
    alpha = np.clip((ga - 22) * 8, 0, 255).astype(np.uint8)
    mono = np.zeros((fsize, fsize, 4), dtype=np.uint8)
    mono[..., 0:3] = 255
    mono[..., 3] = alpha
    canvas = np.zeros((size, size, 4), dtype=np.uint8)
    o = (size - fsize) // 2
    canvas[o:o + fsize, o:o + fsize] = mono
    Image.fromarray(canvas, 'RGBA').save(f'{APP}/mipmap-{d}/cheeta_monochrome.png')
    print('monochrome', d, size)

# --- 6. splash PNG (opaque black canvas, face at ~46%) ---
nodpi = f'{MAIN}/drawable-nodpi'
os.makedirs(nodpi, exist_ok=True)
S = 512
sp = Image.new('RGB', (S, S), (0, 0, 0))
fsize = round(S * 0.46)
art = sq.resize((fsize, fsize), Image.LANCZOS)
sp.paste(art, ((S - fsize) // 2, (S - fsize) // 2))
sp.save(f'{nodpi}/cheeta_splash.png')
print('splash saved', sp.size)
print('DONE')
