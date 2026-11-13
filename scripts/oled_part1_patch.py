#!/usr/bin/env python3
"""Part 1: OLED core — surgical darkblue.attheme fixes.

1. Fix 6 malformed keys (key_ prefix -> parser ignores them silently)
2. Update off-brand surface values (light-brown input fields, cyan tints)
3. Add missing keys that resolved to light defaults (media pill, code blocks,
   dividers, voice panel, tabs, reactions)
"""
import re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"

def dec(hexstr):
    h = hexstr.lstrip('#')
    v = int(h, 16)
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return str(v)

# key -> value (hex ARGB)
FIX_MALFORMED = {
    'key_chat_messagePanelVoiceLock': 'FFFFFFFF',
    'key_sheet_other': '43FFFFFF',
    'key_graySectionText': '757575FF',
    'key_chat_messagePanelVoiceLockBackground': 'FF141414',
    'key_player_progressCachedBackground': 'FF3D3D3D',
    'key_sheet_scrollUp': '0DFFFFFF',
}
UPDATE = {
    'dialogInputField': 'FF1F1F1F',
    'emptyListPlaceholder': 'FF666666',
    'radioBackground': '9E666666',
    'actionBarDefaultSearchPlaceholder': '66FFFFFF',
    'chat_topPanelClose': '8CFFFFFF',
    'chat_topPanelMessage': '8CFFFFFF',
    'chat_replyPanelClose': '8CFFFFFF',
    'chat_messagePanelCancelInlineBot': '8CFFFFFF',
}
ADD = {
    'chat_mediaViews': 'B3141414',
    'chat_inDivider': '1FFFFFFF',
    'chat_outDivider': '33B57E1F',
    'chat_inArticleCodeBackground': 'FF1A1A1A',
    'chat_inArticleCodeScrollbarBackground': 'FF2A2A2A',
    'chat_outArticleCodeScrollbarBackground': 'FF3D3223',
    'chat_inArticleCodeScrollbar': 'FF404040',
    'chat_outArticleCodeScrollbar': 'FF5C4A2E',
    'chats_tabUnreadUnactiveBackground': 'FF2A2A2A',
    'voipgroup_windowBackgroundWhiteInputField': 'FF2A2A2A',
    'voipgroup_windowBackgroundWhiteInputFieldActivated': 'FFE8A33D',
    'chat_messagePanelVoicePressed': 'FF141414',
    'chat_emojiSearchBackground': '0DFFFFFF',
    'chat_inReactionButtonBackground': 'FF2A2A2A',
    'chat_undoBackground': 'E6141414',
}

lines = open(ATTHEME).read().split('\n')

def strip_alpha_hex(v):
    # normalize AARRGGBB -> RRGGBBAA is NOT used; attheme wants signed decimal of ARGB int
    return v

# pass 1: fix malformed + update existing
out = []
seen = set()
fixed, updated = 0, 0
for line in lines:
    m = re.match(r'^(key_[A-Za-z0-9_]+)=(.*)$', line)
    if m and m.group(1) in FIX_MALFORMED:
        name = m.group(1)[4:]
        val = dec(FIX_MALFORMED[m.group(1)])
        out.append(f"{name}={val}")
        seen.add(name)
        fixed += 1
        continue
    m2 = re.match(r'^([A-Za-z0-9_]+)=(.*)$', line)
    if m2 and m2.group(1) in UPDATE:
        name = m2.group(1)
        out.append(f"{name}={dec(UPDATE[name])}")
        seen.add(name)
        updated += 1
        continue
    out.append(line)

# pass 2: append missing keys before the WPS/WLS/wallpaper section if any, else at end
added = []
for name, hexv in ADD.items():
    if name not in seen:
        out.append(f"{name}={dec(hexv)}")
        added.append(name)

open(ATTHEME, 'w').write('\n'.join(out))
print(f"malformed fixed: {fixed}, updated: {updated}, added: {len(added)}")
for n in added:
    print("  +", n)
