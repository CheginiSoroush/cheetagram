#!/usr/bin/env python3
"""Part 3: main pages OLED — settings, profile, chat list, drawer, viewer.

Slate-blue remnants of upstream's Dark Blue palette (#58626E / #1D2733 /
#2A394B / #212D3B families), cyan text tints (#DCF4 family) and off-accent
mint greens (#E0FCCB family) on the main pages -> neutral OLED surfaces and
the amber accent. Semantic colors (secret-chat green, online green, name
colors, chart data lines, code syntax, closeFriends ring) are left alone.
"""
import re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"

def dec(hexstr):
    v = int(hexstr, 16)
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return str(v)

UPDATE = {
    # --- chat list ---
    'chats_menuPhone':                     'FFFFFFFF',  # slate #93C0D0DD -> white
    'chats_date':                          'FF8A8A8A',  # slate #737F8B -> neutral secondary
    'chats_sentClock':                     'FF6E6E6E',  # slate #4C5F6A -> neutral
    'chats_muteIcon':                      'FF6E6E6E',  # slate #4E5F6A -> neutral
    'chats_unreadCounterMuted':            'FF2A2A2A',  # slate #3E5263 -> dark surface
    'chats_archivePinBackground':          'FF2A2A2A',  # slate #2E3E4B -> dark surface
    'chats_menuTopBackgroundCats':         'FF1A1A1A',  # slate #23303F -> dark surface
    'chats_menuTopShadow':                 'A4000000',  # slate shadow -> black shadow
    'graySectionText':                     'FF8A8A8A',  # was 46%-alpha BLUE (#7575FF)!
    'profile_tabText':                     '50FFFFFF',  # cyan #78DCF4 -> white 31%
    # --- settings accents (mint green / cyan -> amber or neutral) ---
    'windowBackgroundWhiteValueText':      'FFE8A33D',  # mint #E0FCCB83 -> amber
    'windowBackgroundWhiteBlueIcon':       'FFE8A33D',  # mint -> amber
    'windowBackgroundWhiteBlueHeader':     'FFE8A33D',  # peach #FCCB83 -> amber
    'windowBackgroundWhiteGrayText2':      'FF8A8A8A',  # was 44%-alpha CYAN (#F1FD)!
    'windowBackgroundUnchecked':           'FF2A2A2A',  # slate #1D2733 -> dark surface
    'switchTrackBlue':                     'FF3C3C3C',  # slate #58626E -> neutral track
    'switchTrackBlueThumb':                'FF232323',  # slate #1D2733 -> neutral thumb
    'switchTrackBlueSelector':             '19FFFFFF',  # cyan ripple -> white ripple
    'actionBarTabUnactiveText':            'FF8A8A8A',  # slate #8B97A2 -> neutral
    'dialogCheckboxSquareDisabled':        'FF3A3A3A',  # slate #445362
    'checkboxSquareDisabled':              '643A3A3A',  # slate alpha
    'dialogButtonSelector':                '1FFFFFFF',  # slate #324156 -> white ripple
    'fastScrollInactive':                  'FF3A3A3A',  # slate #3D4A59
    'undo_background':                     'F21E1E1E',  # slate #2C3B4D -> dark toast
    'dialogBackgroundGray':                'FF141414',  # slate #1C2631 -> black
    'dialogLineProgressBackground':        'FF2E2E2E',  # slate #314352
    'dialog_inlineProgressBackground':     'FF1E1E1E',  # slate #151E27
    'dialogSearchBackground':              'FF1E1E1E',  # slate #2A394B
    'dialogSearchHint':                    'FF8A8A8A',  # slate #7F8892
    'dialogSearchIcon':                    'FF8A8A8A',  # slate #77808F
    'sharedMedia_linkPlaceholder':         'FF232323',  # slate #273745
    'groupcreate_spanBackground':          'FF2A2A2A',  # slate #2C3C4E
    # --- player / media viewer ---
    'player_background':                   'FF141414',  # slate #1F2A36 -> black
    'player_actionBarSubtitle':            'B3FFFFFF',  # cyan -> white 70%
    'player_actionBarSelector':            '1FFFFFFF',  # slate #324153 -> white ripple
    'player_progressBackground':           'FF2E2E2E',  # slate #394758
    'inappPlayerBackground':               'FF141414',  # slate #212D3B -> black
    'inappPlayerTitle':                    'FFFFFFFF',  # cyan -> white
    'inappPlayerClose':                    'B3FFFFFF',  # cyan -> white 70%
    # --- default story rings: green/blue -> amber gradient ---
    'stories_circle1':                     'FFD18A20',
    'stories_circle2':                     'FFE8A33D',
    'stories_circle_dialog1':              'FFD18A20',
    'stories_circle_dialog2':              'FFE8A33D',
    # --- chart controls (data lines stay categorical) ---
    'statisticChartBackZoomColor':         'FFE8A33D',  # blue #46AAEE -> amber
    'statisticChartRipple':                '2CFFFFFF',  # cyan ripple -> white
    'statisticChartActivePickerChart':     'D86E6E6E',  # slate -> neutral
    'statisticChartInactivePickerChart':   'C83A3A3A',  # slate -> neutral
    'statisticChartChevronColor':          'FF8A8A8A',  # slate #767C85
    'statisticChartSignature':             '99FFFFFF',  # slate -> white 60%
    # --- premium / glass / misc surfaces ---
    'premiumGradientBackground1':          'FF202020',  # blue-violet -> neutral
    'premiumGradientBackground2':          'FF171717',
    'premiumGradientBackground3':          'FF141414',
    'premiumGradientBackground4':          'FF101010',
    'glass_targetMainTopPanel':            'FF1C1C1C',  # slate #233141
    'glass_targetMainTabs':                'FF181818',  # slate #202E3E
    'voipgroup_topPanelGray':              'FF9E9E9E',  # slate #5F7381
    'chat_compact_outAccentIcon':          'FF141414',  # blue-black #1A1D21
    'chat_compact_reactionTextSelected':   'FF141414',  # blue-black #1A1D21
    # part-2 leftover: selected out-bubble performer text still light blue
    'chat_outAudioPerfomerSelectedText':   'FFFFFFFF',
}

lines = open(ATTHEME).read().split('\n')
seen, missing = set(), set(UPDATE)
out, updated = [], 0
for l in lines:
    ls = l.strip()
    m = re.match(r'^([A-Za-z0-9_]+)=(-?\d+)$', ls)
    if m and m.group(1) in UPDATE:
        out.append(f"{m.group(1)}={dec(UPDATE[m.group(1)])}")
        updated += 1
        missing.discard(m.group(1))
        continue
    out.append(l)

open(ATTHEME, 'w').write('\n'.join(out))
print(f"updated: {updated}/{len(UPDATE)}")
for n in sorted(missing):
    print("  MISSING (not in attheme):", n)
