#!/usr/bin/env python3
"""Part 3 scan: find remaining blue/slate/cyan hues in the main-pages namespaces.

Namespaces: dialogs_*, chats_*, profile_*, drawer*, picker_*, photos_*,
windowBackground*, settings_*, passcode*, contacts_*, and misc main-page keys.
Blue hue range on OLED = anything with hue 175..260 and saturation > 0.12
(i.e. not neutral gray, not the amber accent ~30..45deg).
"""
import colorsys, re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"

PREFIXES = ('dialogs_', 'chats_', 'profile_', 'drawer', 'picker_', 'photos_',
            'windowBackground', 'settings_', 'passcode', 'contacts_',
            'calls_', 'sponsor', 'emptyList', 'listSelector', 'radialGradient',
            'switch2', 'checkboxCheck', 'radioGroup', 'progressCircle',
            'player_', 'comment', 'statistic_', 'boost', 'channel', 'discussion',
            'gift', 'premium', 'stars', 'business', 'monetization', 'verified')

rows = []
for line in open(ATTHEME):
    line = line.strip()
    if not line or line.startswith('WPS') or line.startswith('WLS') or '=' not in line:
        continue
    name, val = line.split('=', 1)
    try:
        v = int(val)
    except ValueError:
        continue
    v &= 0xFFFFFFFF
    a = (v >> 24) & 0xFF
    r, g, b = (v >> 16) & 255, (v >> 8) & 255, v & 255
    h, s, lum = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    hue = h * 360
    blue = 165 <= hue <= 265 and s > 0.10
    amber = 20 <= hue <= 55 and s > 0.10
    prefix_hit = name.startswith(PREFIXES)
    if blue:
        tag = 'MAINPAGE' if prefix_hit else 'other'
        rows.append((name, v, hue, s, lum, tag))

main = [r for r in rows if r[5] == 'MAINPAGE']
other = [r for r in rows if r[5] == 'other']
print(f"=== MAIN-PAGE blue hues: {len(main)} ===")
for name, v, hue, s, lum, _ in sorted(main, key=lambda x: -x[4]):
    print(f"{name:52s} #{v:08X} hue={hue:5.1f} sat={s:.2f} lum={lum:.2f}")
print(f"\n=== OTHER namespaces blue hues: {len(other)} ===")
for name, v, hue, s, lum, _ in sorted(other, key=lambda x: -x[4]):
    print(f"{name:52s} #{v:08X} hue={hue:5.1f} sat={s:.2f} lum={lum:.2f}")

# also: pure-light surfaces on main pages (lum > 0.30, low sat = gray/white surfaces)
print("\n=== MAIN-PAGE light/neutral surfaces (lum>0.30, sat<0.10) ===")
for line in open(ATTHEME):
    line = line.strip()
    if not line or line.startswith('WPS') or line.startswith('WLS') or '=' not in line:
        continue
    name, val = line.split('=', 1)
    if not name.startswith(PREFIXES):
        continue
    try:
        v = int(val) & 0xFFFFFFFF
    except ValueError:
        continue
    a = (v >> 24) & 0xFF
    if a < 0x60:  # mostly transparent overlays are fine
        continue
    r, g, b = (v >> 16) & 255, (v >> 8) & 255, v & 255
    h, s, lum = colorsys.rgb_to_hsv(r/255, g/255, b/255)
    if s < 0.10 and lum > 0.30 and not name.endswith(('Text', 'Icon', 'text', 'icon', 'Check', 'checkboxCheck')):
        print(f"{name:52s} #{v:08X} lum={lum:.2f}")
