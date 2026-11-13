#!/usr/bin/env python3
"""Part 5: page-by-page gap audit.

Simulates the full runtime resolution chain for all 866 theme keys:
    attheme value -> fallbackKeys chain -> ThemeColors default
and reports ONLY genuine OLED violations, grouped by page namespace:

  LIGHT-SURFACE  opaque (alpha>=C0) surface key resolving to a light color
  BLUE-ANY       any opaque key resolving into the blue hue band (165..265)
  UNSET          key with no value anywhere in the chain
  FALLBACK-LIGHT key missing from attheme, rescued by fallback into a
                 light default (works now, but fragile if fallback changes)
"""
import colorsys, re
from collections import defaultdict

BASE = "/home/z/telegram/TMessagesProj/src/main"
THEME_JAVA = f"{BASE}/java/org/telegram/ui/ActionBar/Theme.java"
THEMECOLORS = f"{BASE}/java/org/telegram/ui/ActionBar/ThemeColors.java"
ATTHEME = f"{BASE}/assets/darkblue.attheme"

keys = [m.group(1) for m in re.finditer(
    r'public static final int (key_\w+) = colorsCount\+\+\;', open(THEME_JAVA).read())]

CONSTS = {'TELEGRAM_COLOR': 0xffE8A33D, 'TELEGRAM_COLOR_TEXT': 0xffC6842A,
          'DEFAULT_BLACK_TEXT': 0xFF1A1D21}
defaults = {}
for m in re.finditer(r'defaultColors\[(key_\w+)\]\s*=\s*([^;]+);', open(THEMECOLORS).read()):
    key, val = m.group(1), m.group(2).strip()
    if val.startswith('0x'):
        defaults[key] = int(val, 16)
    elif val in CONSTS:
        defaults[key] = CONSTS[val]
    else:
        defaults[key] = ('REF', val)
for k, v in list(defaults.items()):
    if isinstance(v, tuple):
        src = re.search(r'(key_\w+)', v[1])
        defaults[k] = defaults.get(src.group(1), 0xFF000000) if src else 0xFF000000

fb = {}
for m in re.finditer(r'fallbackKeys\.put\((key_\w+),\s*(key_\w+)\);', open(THEME_JAVA).read()):
    fb[m.group(1)] = m.group(2)

attheme = {}
for line in open(ATTHEME):
    line = line.strip()
    if '=' in line and not line.startswith('//'):
        k, v = line.split('=', 1)
        try:
            attheme['key_' + k] = int(v) & 0xFFFFFFFF
        except ValueError:
            pass

def resolve(key, depth=0):
    if key in attheme:
        return attheme[key]
    if depth < 6 and key in fb:
        r = resolve(fb[key], depth + 1)
        if r is not None:
            return r
    return defaults.get(key)

def hsv(v):
    r, g, b = (v >> 16) & 255, (v >> 8) & 255, v & 255
    h, s, l = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, l

def is_surface(key):
    n = key[4:]
    TEXTY = ('text', 'icon', 'check', 'title', 'name', 'hint', 'selector', 'linkselection',
             'progressline', 'stroke', 'dot', 'shine', 'gradient1', 'gradient2', 'gradient3',
             'rotation', 'offset', 'shadowline', 'clock', 'animatedtext', 'circle', 'badge',
             'line', 'progress', 'divider', 'tag', 'waveform', 'sentcheck', 'views')
    last = n.split('_')[-1]
    if any(n.endswith(t) or last == t for t in TEXTY):
        return False
    SURF = ('background', 'windowbackground', 'wallpaper', 'panel', 'menu', 'sheet',
            'bubble', 'gray', 'track', 'inputfield', 'searchbackground', 'actionbackground',
            'keyboard', 'checkboxsquarebackground', 'radiobackground', 'view',
            'placeholder', 'queryfield', 'tabs', 'header', 'bar', 'emptylistplaceholder',
            'avatar_background', 'archivebackground', 'slider')
    if any(s in n for s in SURF):
        return True
    return False

# page grouping by prefix
def page_of(key):
    n = key[4:]
    for pre, page in [
        ('chat_', 'chat'), ('actionBar', 'bars'), ('windowBackground', 'settings'),
        ('dialog', 'dialogs'), ('chats_', 'chat-list'), ('dialogs_', 'chat-list'),
        ('profile_', 'profile'), ('avatar_', 'avatars'), ('picker_', 'gallery'),
        ('photos_', 'gallery'), ('player_', 'player'), ('inappPlayer', 'player'),
        ('stories_', 'stories'), ('voip', 'calls'), ('calls_', 'calls'),
        ('groupcreate', 'create'), ('statistic', 'stats'), ('premium', 'premium'),
        ('passcode', 'lock'), ('drawer', 'drawer'), ('contacts_', 'contacts'),
        ('graySection', 'settings'), ('listSelector', 'global'), ('switch', 'settings'),
        ('checkbox', 'global'), ('radio', 'global'), ('undo_', 'global'),
        ('fastScroll', 'global'), ('contextProgress', 'global'), ('progressCircle', 'global'),
        ('sharedMedia_', 'media'), ('location_', 'location'), ('stickers_', 'stickers'),
        ('emoji_', 'emoji'), ('passport', 'passport'), ('wallet', 'wallet'),
    ]:
        if n.startswith(pre):
            return page
    return 'other'

light, blue, unset, fblight = [], [], [], []
for key in keys:
    v = resolve(key)
    if v is None:
        unset.append(key)
        continue
    a = (v >> 24) & 0xFF
    hue, sat, lum = hsv(v)
    opaque = a >= 0xC0
    if opaque and lum > 0.35 and sat < 0.15 and is_surface(key):
        light.append((key, v, lum))
    if opaque and 165 <= hue <= 265 and sat > 0.10:
        blue.append((key, v, hue, sat))
    if key not in attheme and opaque and lum > 0.35 and sat < 0.15 and is_surface(key):
        fblight.append(key)

print(f"keys={len(keys)} attheme={len(attheme)} defaults={len(defaults)} fallbacks={len(fb)}")
print(f"\n=== OPAQUE LIGHT SURFACES ({len(light)}) ===")
by_page = defaultdict(list)
for k, v, l in light:
    by_page[page_of(k)].append((k, v, l))
for page in sorted(by_page):
    print(f"-- {page} --")
    for k, v, l in sorted(by_page[page], key=lambda x: -x[2]):
        src = 'ATTHEME' if k in attheme else 'default'
        print(f"  {k[4:]:48s} #{v:08X} lum={l:.2f} src={src}")

print(f"\n=== OPAQUE BLUE ANY ({len(blue)}) ===")
by_page = defaultdict(list)
for k, v, h, s in blue:
    by_page[page_of(k)].append((k, v, h, s))
for page in sorted(by_page):
    print(f"-- {page} --")
    for k, v, h, s in sorted(by_page[page], key=lambda x: -x[2]):
        src = 'ATTHEME' if k in attheme else 'default'
        print(f"  {k[4:]:48s} #{v:08X} hue={h:.0f} src={src}")

print(f"\n=== UNSET ({len(unset)}) ===")
for k in unset:
    print(f"  {k[4:]}")
print(f"\n=== FALLBACK-RESCUED LIGHT SURFACES ({len(fblight)}) ===")
for k in fblight:
    print(f"  {k[4:]}  <- falls back to {fb.get(k, '?')[4:]}")
