#!/usr/bin/env python3
"""Part 5: page-by-page gap fill.

Fills the gaps the deep audit found:
1. UNSET keys with real usage (menu top, bubble selection overlays,
   out-bubble gradients, wallpaper gradient stops) -> explicit OLED values.
   NOTE: chat_wallpaper_gradient_rotation deliberately left unset — it may
   be read as a float, a color value there would corrupt the angle.
2. Group-call screen (voipgroup_*, 29 keys from upstream defaults — the
   page that was never themed): surfaces -> neutral dark, accents -> amber,
   state colors (green speaking, red muted-by-admin, teal live) kept.
3. Wrong defaults: contextProgress pair-2 (white/light-blue), gray avatar
   (light slate), sticker set name (slate).
"""
import re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"
THEMECOLORS = "/home/z/telegram/TMessagesProj/src/main/java/org/telegram/ui/ActionBar/ThemeColors.java"

def dec(hexstr):
    v = int(hexstr, 16)
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return str(v)

ADD = {
    # unset keys with real usages
    'chats_menuTopShadowCats':            'A4000000',  # match chats_menuTopShadow
    'chats_menuTopBackground':            'FF141414',  # drawer header bg (was transparent)
    'chat_inBubbleSelectedOverlay':       '14FFFFFF',  # selection tint on dark bubble
    'chat_outBubbleSelectedOverlay':      '14000000',  # selection tint on amber bubble
    'chat_outBubbleGradient1':            'FF8A6E44',  # amber gradient bubble stops
    'chat_outBubbleGradient2':            'FF917046',
    'chat_outBubbleGradient3':            'FF866A40',
    'chat_outBubbleGradientAnimated':     'FF8A6E44',
    'chat_wallpaper_gradient_to1':        'FF050505',  # OLED black shimmer stops
    'chat_wallpaper_gradient_to2':        'FF0A0A0A',
    'chat_wallpaper_gradient_to3':        'FF000000',
}

# ThemeColors default replacements: (old exact, new exact)
DEF_EDITS = [
    ('defaultColors[key_contextProgressOuter2] = 0xffffffff;',
     'defaultColors[key_contextProgressOuter2] = 0xffE8A33D;'),
    ('defaultColors[key_contextProgressInner2] = 0xffbfdff6;',
     'defaultColors[key_contextProgressInner2] = 0xff6e6e6e;'),
    ('defaultColors[key_avatar_backgroundGray] = 0xffA1ABB5;',
     'defaultColors[key_avatar_backgroundGray] = 0xff8A8A8A;'),
    ('defaultColors[key_chat_emojiPanelStickerSetName] = 0xff828b94;',
     'defaultColors[key_chat_emojiPanelStickerSetName] = 0xff8A8A8A;'),
    # --- voipgroup: the group-call page, never themed (was upstream slate blue) ---
    ('defaultColors[key_voipgroup_listViewBackground] = 0xff1C2229;',
     'defaultColors[key_voipgroup_listViewBackground] = 0xff141414;'),
    ('defaultColors[key_voipgroup_listViewBackgroundUnscrolled] = 0xff222A33;',
     'defaultColors[key_voipgroup_listViewBackgroundUnscrolled] = 0xff1A1A1A;'),
    ('defaultColors[key_voipgroup_dialogBackground] = 0xff1C2229;',
     'defaultColors[key_voipgroup_dialogBackground] = 0xff141414;'),
    ('defaultColors[key_voipgroup_actionBar] = 0xff0F1317;',
     'defaultColors[key_voipgroup_actionBar] = 0xff0A0A0A;'),
    ('defaultColors[key_voipgroup_actionBarUnscrolled] = 0xff191F26;',
     'defaultColors[key_voipgroup_actionBarUnscrolled] = 0xff0F0F0F;'),
    ('defaultColors[key_voipgroup_searchBackground] = 0xff303B47;',
     'defaultColors[key_voipgroup_searchBackground] = 0xff2A2A2A;'),
    ('defaultColors[key_voipgroup_scrollUp] = 0xff394654;',
     'defaultColors[key_voipgroup_scrollUp] = 0xff2E2E2E;'),
    ('defaultColors[key_voipgroup_inviteMembersBackground] = 0xff222A33;',
     'defaultColors[key_voipgroup_inviteMembersBackground] = 0xff1E1E1E;'),
    ('defaultColors[key_voipgroup_disabledButton] = 0xff1C2229;',
     'defaultColors[key_voipgroup_disabledButton] = 0xff2A2A2A;'),
    ('defaultColors[key_voipgroup_disabledButtonActive] = 0xff2C3A45;',
     'defaultColors[key_voipgroup_disabledButtonActive] = 0xff3A3A3A;'),
    ('defaultColors[key_voipgroup_rtmpButton] = 0xff2A3853;',
     'defaultColors[key_voipgroup_rtmpButton] = 0xff2A2A2A;'),
    ('defaultColors[key_voipgroup_lastSeenText] = 0xff79838A;',
     'defaultColors[key_voipgroup_lastSeenText] = 0xff9E9E9E;'),
    ('defaultColors[key_voipgroup_lastSeenTextUnscrolled] = 0xff858D94;',
     'defaultColors[key_voipgroup_lastSeenTextUnscrolled] = 0xff9E9E9E;'),
    ('defaultColors[key_voipgroup_searchPlaceholder] = 0xff858D94;',
     'defaultColors[key_voipgroup_searchPlaceholder] = 0xff8A8A8A;'),
    ('defaultColors[key_voipgroup_mutedIcon] = 0xff6F7980;',
     'defaultColors[key_voipgroup_mutedIcon] = 0xff9E9E9E;'),
    ('defaultColors[key_voipgroup_mutedIconUnscrolled] = 0xff7E868C;',
     'defaultColors[key_voipgroup_mutedIconUnscrolled] = 0xff9E9E9E;'),
    ('defaultColors[key_voipgroup_listeningText] = 0xff4DB8FF;',
     'defaultColors[key_voipgroup_listeningText] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_checkMenu] = 0xff6BB6F9;',
     'defaultColors[key_voipgroup_checkMenu] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_unmuteButton] = 0xff539EF8;',
     'defaultColors[key_voipgroup_unmuteButton] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_unmuteButton2] = 0xff66D4FB;',
     'defaultColors[key_voipgroup_unmuteButton2] = 0xffD18A20;'),
    ('defaultColors[key_voipgroup_connectingProgress] = 0xff28BAFF;',
     'defaultColors[key_voipgroup_connectingProgress] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_topPanelBlue1] = 0xff60C7FB;',
     'defaultColors[key_voipgroup_topPanelBlue1] = 0xffD18A20;'),
    ('defaultColors[key_voipgroup_topPanelBlue2] = 0xff519FF9;',
     'defaultColors[key_voipgroup_topPanelBlue2] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_overlayBlue1] = 0xff2BCEFF;',
     'defaultColors[key_voipgroup_overlayBlue1] = 0xffD18A20;'),
    ('defaultColors[key_voipgroup_overlayBlue2] = 0xff0976E3;',
     'defaultColors[key_voipgroup_overlayBlue2] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_mutedByAdminGradient] = 0xff57A4FE;',
     'defaultColors[key_voipgroup_mutedByAdminGradient] = 0xffD18A20;'),
    ('defaultColors[key_voipgroup_mutedByAdminGradient3] = 0xff766EE9;',
     'defaultColors[key_voipgroup_mutedByAdminGradient3] = 0xffC77F1F;'),
    ('defaultColors[key_voipgroup_overlayAlertMutedByAdmin] = 0xff67709E;',
     'defaultColors[key_voipgroup_overlayAlertMutedByAdmin] = 0xffE8A33D;'),
    ('defaultColors[key_voipgroup_overlayAlertMutedByAdmin2] = 0xff2F5078;',
     'defaultColors[key_voipgroup_overlayAlertMutedByAdmin2] = 0xff382A16;'),
]

src = open(THEMECOLORS).read()
applied, failed = 0, []
for old, new in DEF_EDITS:
    if old in src:
        src = src.replace(old, new, 1)
        applied += 1
    else:
        failed.append(old)
open(THEMECOLORS, 'w').write(src)
print(f"ThemeColors defaults: {applied}/{len(DEF_EDITS)} applied")
for f in failed:
    print("  NOT FOUND:", f)

# attheme additions
lines = open(ATTHEME).read().split('\n')
existing = set()
for l in lines:
    ls = l.strip()
    if ls and '=' in ls:
        existing.add(ls.split('=', 1)[0])
out = list(lines)
added = []
for name, hexv in ADD.items():
    if name not in existing:
        out.append(f"{name}={dec(hexv)}")
        added.append(name)
open(ATTHEME, 'w').write('\n'.join(out))
print(f"attheme added: {len(added)}")
for n in added:
    print("  +", n)
