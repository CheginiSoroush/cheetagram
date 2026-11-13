/*
 * Cheetagram — one-shot theme upgrade for existing installs.
 *
 * The OLED theme ships in darkblue.attheme (loaded from the APK asset on
 * every start), but two pieces of per-install state survive upgrades and
 * keep the chat background non-black:
 *
 *   1. Persisted wallpaper overrides ("{theme}_{accentId}_owp" JSON in the
 *      themeconfig preferences + wallpaper image files).
 *   2. Downloaded accent pattern wallpaper files (*_v5.jpg / *_v8_debug.jpg).
 *
 * This class clears that state exactly once per upgrade (version marker in
 * globalMainSettings), then rebuilds the wallpaper drawable so every surface
 * — including the chat background — matches the built-in OLED palette.
 */
package org.telegram.messenger.cheetagram;

import android.content.Context;
import android.content.SharedPreferences;

import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.MessagesController;
import org.telegram.ui.ActionBar.Theme;

import java.io.File;

public final class CheetagramThemeUpgrade {

    /** Bump when the built-in theme changes in a way existing installs must pick up. */
    public static final int CURRENT_VERSION = 2;

    private static final String PREF_KEY = "cheetagram_theme_version";

    private CheetagramThemeUpgrade() { }

    public static void checkAndApply() {
        try {
            SharedPreferences globalPrefs = MessagesController.getGlobalMainSettings();
            if (globalPrefs.getInt(PREF_KEY, 0) >= CURRENT_VERSION) {
                return;
            }

            Theme.ThemeInfo night = Theme.getCurrentNightTheme();
            if (night != null && night.assetName != null) {
                // 1. drop the persisted wallpaper override of the theme and of
                //    every accent (setOverrideWallpaper(null) removes the JSON
                //    pref and the wallpaper image files of the current accent).
                night.setOverrideWallpaper(null);
                clearAccentWallpaperState(night);

                // 2. rebuild the chat wallpaper from the (fresh) theme colors —
                //    with gradients absent this becomes a solid ColorDrawable.
                Theme.reloadWallpaper(true);
            }

            globalPrefs.edit().putInt(PREF_KEY, CURRENT_VERSION).apply();
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    /**
     * Removes every accent's persisted wallpaper override and downloaded
     * pattern file for the given theme. The theme is reloaded from the APK
     * asset on the next start, so wiping accent state here cannot corrupt it.
     */
    private static void clearAccentWallpaperState(Theme.ThemeInfo themeInfo) {
        try {
            SharedPreferences themeConfig = ApplicationLoader.applicationContext
                    .getSharedPreferences("themeconfig", Context.MODE_PRIVATE);
            SharedPreferences.Editor editor = themeConfig.edit();
            editor.remove(themeInfo.name + "_owp");
            if (themeInfo.themeAccents != null) {
                for (int a = 0; a < themeInfo.themeAccents.size(); a++) {
                    Theme.ThemeAccent accent = themeInfo.themeAccents.get(a);
                    accent.overrideWallpaper = null;
                    editor.remove(themeInfo.name + "_" + accent.id + "_owp");
                    try {
                        File patternFile = accent.getPathToWallpaper();
                        if (patternFile != null && patternFile.exists()) {
                            patternFile.delete();
                        }
                    } catch (Throwable ignore) { }
                }
            }
            editor.apply();
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }
}
