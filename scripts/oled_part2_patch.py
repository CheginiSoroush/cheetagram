#!/usr/bin/env python3
"""Part 2: chat section OLED — kill the remaining blue-gray/slate surfaces.

The compose panel, emoji panel, bot keyboard, service pills, file/location
cards and all selected-state text still carried upstream's dark-blue hues
(#212D3B family) which clash with the pure black + amber OLED palette.
"""
import re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"

def dec(hexstr):
    v = int(hexstr, 16)
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return str(v)

UPDATE = {
    # --- big surfaces: slate blue -> neutral OLED dark ---
    'chat_messagePanelBackground':           'FF141414',  # compose panel
    'chat_emojiPanelBackground':             'FF141414',  # sticker/emoji/GIF panel
    'chat_stickersHintPanel':                'FF1A1A1A',
    'chat_serviceBackground':                '821E1E1E',  # date pills / service bubbles
    'chat_unreadMessagesStartBackground':    'FF1F1F1F',
    'chat_botKeyboardButtonBackground':      'FF1F1F1F',
    'chat_botKeyboardButtonBackgroundPressed': 'FF2A2A2A',
    # --- in-bubble cards ---
    'chat_inFileBackground':                 'FF232323',
    'chat_inLocationBackground':             'FF262626',
    'chat_inLoaderPhoto':                    'FF1E1E1E',
    'chat_inBubbleLocationPlaceholder':      '1E3A3A3A',
    # --- compact mode fades ---
    'chat_compact_fadeEdge':                 'FF141414',
    'chat_compact_fadeMiddle':               'A3141414',
    # --- code blocks on amber out-bubble: blue tint -> neutral dark tint ---
    'chat_outCodeBackground':                '33000000',
    # --- cyan hints/icons -> white semi ---
    'chat_messagePanelHint':                 '66FFFFFF',
    'chat_messagePanelIcons':                '73FFFFFF',
    'chat_muteIcon':                         '3CFFFFFF',
    'chat_emojiPanelStickerPackSelector':    '0AFFFFFF',
    # --- selected out-bubble text family: light blue -> white ---
    'chat_outTimeSelectedText':              'FFFFFFFF',
    'chat_outInstantSelected':               'FFFFFFFF',
    'chat_outContactPhoneSelectedText':      'FFFFFFFF',
    'chat_outFileInfoSelectedText':          'FFFFFFFF',
    'chat_outVenueInfoSelectedText':         'FFFFFFFF',
    'chat_outViewsSelected':                 'FFFFFFFF',
    'chat_outSentCheckSelected':             'FFFFFFFF',
    'chat_outSentClockSelected':             'FFFFFFFF',
    'chat_outAudioDurationSelectedText':     'FFFFFFFF',
    'chat_outMenuSelected':                  'DFFFFFFF',
    'chat_inSentClockSelected':              'FFFFFFFF',
    'chat_inReplyMediaMessageSelectedText':  'FFFFFFFF',
    # --- misc ---
    'chat_inInstantSelected':                'FFF2BE6A',  # light-blue -> light amber
    'chat_secretTimeText':                   'FFEBEBEB',
    'chat_emojiPanelEmptyText':              'FF8A8A8A',
    'chat_emojiPanelTrendingDescription':    'FF8A8A8A',
}

ADD = {
    'chat_gifSaveHintBackground':            'E2141414',  # fallback was blue DEF
    'chat_recordedVoiceProgress':            'FFFFFFFF',  # waveform while recording
    'chat_inAudioPerformerText':             'FF979797',  # was dark DEF on dark bubble
    'chat_inAudioPerformerSelectedText':     'FFB8B8B8',
}

lines = open(ATTHEME).read().split('\n')
seen = {}
for i, l in enumerate(lines):
    ls = l.strip()
    if ls and '=' in ls and not ls.startswith('WPS') and not ls.startswith('WLS='):
        seen[ls.split('=', 1)[0]] = i

out, updated, added = [], 0, []
for i, l in enumerate(lines):
    ls = l.strip()
    m = re.match(r'^([A-Za-z0-9_]+)=(-?\d+)$', ls)
    if m and m.group(1) in UPDATE:
        out.append(f"{m.group(1)}={dec(UPDATE[m.group(1)])}")
        updated += 1
        continue
    out.append(l)
for name, hexv in ADD.items():
    if name not in seen:
        out.append(f"{name}={dec(hexv)}")
        added.append(name)

open(ATTHEME, 'w').write('\n'.join(out))
print(f"updated: {updated}, added: {len(added)}")
for n in added:
    print("  +", n)
