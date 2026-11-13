#!/usr/bin/env python3
"""Part 4: consistency — one amber family, visible ripples, neutral controls.

Consolidates 99 scattered amber variants into a canonical palette:
  ACCENT        #E8A33D  filled elements, icons, active tabs, badges
  ACCENT_LIGHT  #EFBB6F  links, counters, status text on dark (dominant family)
  ACCENT_ON_AMBER #DFC195  secondary text/icons on the amber out-bubble
  ACCENT_PRESSED #D18A20  pressed fills
  PRESS_WASH    #E0B069  opaque list press backgrounds (was 3 near-identical)
  WARM_GRAY     #998E7F  secondary text/icons (was 15 variants)
Unchecked control surfaces (checkbox, radio, tracks, input field) go neutral
dark. Visible ripples instead of invisible ones on black.
"""
import re

ATTHEME = "/home/z/telegram/TMessagesProj/src/main/assets/darkblue.attheme"

def dec(hexstr):
    v = int(hexstr, 16)
    if v > 0x7FFFFFFF:
        v -= 0x100000000
    return str(v)

A       = 'FFE8A33D'  # accent
AL      = 'FFEFBB6F'  # accent light
AOA     = 'FFDFC195'  # on-amber secondary
AP      = 'FFD18A20'  # pressed
PW      = 'FFE0B069'  # press wash
WG      = 'FF998E7F'  # warm gray secondary

UPDATE = {
    # --- light accent family (links/counters/status) -> #EFBB6F ---
    'chat_inInstantSelected':              AL,  # F2BE6A
    'chat_status':                         AL,  # F7C67D
    'profile_status':                      AL,  # F7C67D
    'chat_recordVoiceCancel':              AL,  # EEC07C
    'chat_topPanelTitle':                  AL,  # E6B874
    'chat_goDownButtonCounterBackground':  AL,  # EEB45D
    'returnToCallBackground':              AL,  # E7B468
    'switchTrackChecked':                  AL,  # D7AB6A checked track = light accent
    # --- accent family -> #E8A33D ---
    'actionBarTabActiveText':              A,   # FFC875
    'actionBarTabLine':                    A,   # FFC570
    'chat_attachActiveTab':                A,   # FFC875
    'chat_attachGalleryBackground':        A,   # F5B75A
    'chat_attachPollBackground':           A,   # DEB045
    'chat_attachContactBackground':        A,   # DEB045
    'chat_emojiPanelBadgeBackground':      A,   # F5B95F
    'picker_badge':                        A,   # F7BB62
    'files_folderIconBackground':          A,   # E0A95A
    'windowBackgroundWhiteInputFieldActivated': A,  # EFBF78
    'checkboxSquareBackground':            A,   # E5B56E
    'passport_authorizeBackground':        A,   # BA8E4C
    'contextProgressOuter1':               A,   # F8C373
    # --- pressed -> #D18A20 ---
    'chat_msgIvButtonPrimaryInPressed':    AP,  # DBA24E
    'chat_msgIvButtonPrimaryOutPressed':   AP,  # DBA24E
    'profile_actionPressedBackground':     AP,  # D4A156
    'passport_authorizeBackgroundSelected': AP, # D7A458
    # --- on-amber out-bubble secondary -> #DFC195 ---
    'chat_outSentClock':                   AOA, # CBB087
    'chat_outMenu':                        AOA, # CEAA74
    'chat_outAudioSeekbarSelected':        AOA, # D6B077
    'chat_outVoiceSeekbarSelected':        AOA, # DCB47A
    # --- warm gray secondary -> #998E7F ---
    'chats_menuPhoneCats':                 WG,  # A4957F
    'chats_menuItemIcon':                  WG,  # 9A8F80
    'dialogIcon':                          WG,  # AA9E8D
    'chats_attachMessage':                 WG,  # 988E7F
    'chat_inAudioDurationText':            WG,  # 978C7C
    'chat_secretChatStatusText':           WG,  # 978B7B
    'chat_inAudioPerfomerText':            WG,  # 978B7B
    'chat_inContactPhoneText':             WG,  # 978B7B
    'chat_inFileInfoText':                 WG,  # 978B7B
    'chat_inReplyMediaMessageText':        WG,  # 978B7B
    'chat_inVenueInfoText':                WG,  # 978B7B
    'chat_inViews':                        WG,  # 978B7B
    'chats_pinnedIcon':                    WG,  # 80715B
    'chat_unreadMessagesStartArrowIcon':   WG,  # 7A6E5C
    'chat_attachUnactiveTab':              WG,  # A69171
    # --- unchecked controls / warm surfaces -> neutral dark ---
    'dialogCheckboxSquareUnchecked':       'FF3A3A3A',  # 796B56
    'checkboxSquareUnchecked':             'FF3A3A3A',  # 796B56
    'dialogRadioBackground':               'FF3A3A3A',  # 796B56
    'windowBackgroundWhiteInputField':     'FF3A3A3A',  # 6F604B
    'switchTrack':                         'FF3C3C3C',  # 847560
    'picker_disabledButton':               'FF3A3A3A',  # 80705A
    'stickers_menu':                       'FF2A2A2A',  # 7F725E
    'chats_archiveBackground':             'FF1A1A1A',  # CCA060 saturated amber surface
    'dialogTopBackground':                 'FF1A1A1A',  # 98723A
    'chat_inAudioSeekbar':                 'FF3A3A3A',  # 706453
    'chat_inAudioCacheSeekbar':            'FF565656',  # C3A06C
    'chat_inVoiceSeekbar':                 'FF3A3A3A',  # 80735F
    'chat_inAudioSeekbarSelected':         'FF6E6E6E',  # AB9677
    'chat_inVoiceSeekbarSelected':         'FF6E6E6E',  # AB9677
    'chat_emojiPanelBackspace':            '73FFFFFF',  # 877B69 -> panel icon white
    'chat_emojiPanelIcon':                 '73FFFFFF',  # 877B69
    'contextProgressInner1':               '649B9B9B',  # 649B9183 neutral
    # --- switch checked thumb: dark amber on amber -> white ---
    'switchTrackBlueThumbChecked':         'FFFFFFFF',  # AB8855
    # --- press wash unify -> #E0B069 ---
    'chats_actionBackground':              PW,  # DEAF69
    'profile_actionBackground':            PW,  # E1B16B
    'chats_actionMessage':                 PW,  # E9B86E
}

lines = open(ATTHEME).read().split('\n')
missing = set(UPDATE)
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
    print("  MISSING:", n)
