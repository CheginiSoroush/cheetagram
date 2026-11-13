#!/usr/bin/env python3
"""Audit darkblue.attheme coverage vs Theme.java keys and ThemeColors defaults.

Resolves every theme key through the runtime chain:
  attheme value > ThemeColors default > fallbackKey resolution
and reports keys that resolve to light colors (OLED violations).
"""
import re

BASE = "/home/z/telegram/TMessagesProj/src/main"
THEME_JAVA = f"{BASE}/java/org/telegram/ui/ActionBar/Theme.java"
THEMECOLORS = f"{BASE}/java/org/telegram/ui/ActionBar/ThemeColors.java"
ATTHEME = f"{BASE}/assets/darkblue.attheme"

# 1. All keys in declaration order
keys = []  # (name)
for m in re.finditer(r'public static final int (key_\w+) = colorsCount\+\+\;', open(THEME_JAVA).read()):
    keys.append(m.group(1))
print(f"total keys: {len(keys)}")

# 2. ThemeColors defaults
defaults = {}
CONSTS = {'TELEGRAM_COLOR': 0xffE8A33D, 'TELEGRAM_COLOR_TEXT': 0xffC6842A, 'DEFAULT_BLACK_TEXT': 0xFF1A1D21}
for m in re.finditer(r'defaultColors\[(key_\w+)\]\s*=\s*([^;]+);', open(THEMECOLORS).read()):
    key, val = m.group(1), m.group(2).strip()
    if val.startswith('0x'):
        defaults[key] = int(val, 16)
    elif val in CONSTS:
        defaults[key] = CONSTS[val]
    else:
        defaults[key] = ('REF', val)
# resolve REF entries (e.g. defaultColors[key_x] = defaultColors[key_y])
for k, v in list(defaults.items()):
    if isinstance(v, tuple):
        src = re.search(r'(key_\w+)', v[1])
        defaults[k] = defaults.get(src.group(1), 0) if src else 0
print(f"defaults assigned: {len(defaults)}")

# 3. fallbackKeys
fb = {}
for m in re.finditer(r'fallbackKeys\.put\((key_\w+),\s*(key_\w+)\);', open(THEME_JAVA).read()):
    fb[m.group(1)] = m.group(2)
print(f"fallbacks: {len(fb)}")

# 4. attheme values (attheme names = Java key name without "key_" prefix)
attheme = {}
for line in open(ATTHEME):
    line = line.strip()
    if '=' in line and not line.startswith('//'):
        k, v = line.split('=', 1)
        try:
            attheme[k] = int(v) if not v.startswith('#') else int(v[1:], 16) | (0xff000000 if len(v) <= 7 else 0)
        except ValueError:
            pass
# index by java-style key name too
attheme_j = {('key_' + k): v for k, v in attheme.items()}
print(f"attheme keys: {len(attheme)}")

# 5. resolve
def resolve(key, depth=0):
    if key in attheme_j:
        return attheme_j[key]
    if depth < 6:
        f = fb.get(key)
        if f:
            r = resolve(f, depth + 1)
            if r is not None:
                return r
    if key in defaults:
        return defaults[key]
    return None

def lum(c):
    if c is None: return -1
    r, g, b = (c >> 16) & 255, (c >> 8) & 255, c & 255
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255

def is_surface(name):
    n = name.lower()
    # strip key_ prefix
    n = n[4:] if n.startswith('key_') else n
    TEXTY = ('text', 'icon', 'check', 'title', 'name', 'hint', 'selector', 'linkselection',
             'progressline', 'stroke', 'dot', 'shine', 'gradient1', 'gradient2', 'gradient3',
             'rotation', 'offset', 'shadowline', 'clock', 'animatedtext')
    for t in TEXTY:
        if n.endswith(t) or t in n.split('_')[-1]:
            return False
    SURFACE = ('background', 'windowbackground', 'wallpaper', 'panel', 'menu', 'sheet',
               'bubble', 'gray', 'divider', 'track', 'inputfield', 'searchbackground',
               'actionbackground', 'keyboard', 'checkboxsquarebackground', 'radiobackground',
               'view', 'placeholder', 'queryfield', 'tabs', 'header', 'bar', 'emptylistplaceholder')
    for s in SURFACE:
        if s in n:
            return True
    return False

violations = []
unset = []
missing = []
for name in keys:
    v = resolve(name)
    if v is None:
        unset.append(name)
    elif name not in attheme_j:
        missing.append(name)
    if v is None:
        continue
    if is_surface(name) and lum(v) > 0.30:
        violations.append((name, v, lum(v)))

print(f"\nmissing from attheme (resolved via fallback/default): {len(missing)}")
print(f"\n=== SURFACE LIGHT VIOLATIONS ({len(violations)}) ===")
for name, v, l in sorted(violations, key=lambda x: -x[2]):
    in_at = 'ATTHEME' if name in attheme_j else 'fallback/default'
    print(f"{name} = {v & 0xffffffff:08x} lum={l:.2f} src={in_at}")
print(f"\n=== UNSET ({len(unset)}) ===")
for n in unset:
    print(n)
