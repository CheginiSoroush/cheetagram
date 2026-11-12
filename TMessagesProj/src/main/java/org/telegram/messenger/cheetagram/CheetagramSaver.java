/*
 * Cheetagram — crash-free, always-callback saver for the download queue.
 *
 * Why not MediaController.saveFile():
 *  1. It creates an AlertDialog on the passed context. With the application
 *     context (our case: screen may be LOCKED, no activity) dialog.show()
 *     throws BadTokenException on the UI thread -> app crash.
 *  2. It only invokes its callback on SUCCESS; on failure the callback is
 *     dropped, which would stall the queue forever.
 *
 * This saver does no UI at all (works with the screen off) and ALWAYS
 * invokes the callback exactly once — with the target Uri, or null on any
 * failure — so the queue can always advance.
 */
package org.telegram.messenger.cheetagram;

import android.content.ContentValues;
import android.content.Context;
import android.media.MediaScannerConnection;
import android.net.Uri;
import android.os.Build;
import android.os.Environment;
import android.provider.MediaStore;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.Utilities;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.OutputStream;

public final class CheetagramSaver {

    private CheetagramSaver() {}

    /**
     * Copies {@code sourcePath} into the public Downloads folder
     * (Download/Telegram). Calls {@code onDone} ON THE UI THREAD exactly
     * once — with the saved Uri, or null if the save failed.
     */
    public static void saveToDownloads(String sourcePath, String displayName, String mimeType, final Utilities.Callback<Uri> onDone) {
        if (Build.VERSION.SDK_INT >= 29) {
            saveQ(sourcePath, displayName, mimeType, onDone);
        } else {
            saveLegacy(sourcePath, displayName, mimeType, onDone);
        }
    }

    // API 29+: MediaStore.Downloads (no storage permission needed)
    private static void saveQ(String sourcePath, String displayName, String mimeType, final Utilities.Callback<Uri> onDone) {
        Utilities.globalQueue.postRunnable(() -> {
            Uri saved = null;
            try {
                File src = new File(sourcePath);
                if (!src.exists()) {
                    throw new IllegalStateException("source missing: " + sourcePath);
                }
                Context context = ApplicationLoader.applicationContext;
                ContentValues values = new ContentValues();
                values.put(MediaStore.MediaColumns.DISPLAY_NAME, displayName);
                values.put(MediaStore.MediaColumns.MIME_TYPE,
                    mimeType != null ? mimeType : "application/octet-stream");
                values.put(MediaStore.MediaColumns.RELATIVE_PATH,
                    Environment.DIRECTORY_DOWNLOADS + File.separator + "Telegram");
                Uri uri = context.getContentResolver().insert(
                    MediaStore.Downloads.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY), values);
                if (uri == null) {
                    throw new IllegalStateException("MediaStore insert returned null");
                }
                try (InputStream in = new FileInputStream(src);
                     OutputStream out = context.getContentResolver().openOutputStream(uri)) {
                    if (out == null) {
                        throw new IllegalStateException("output stream is null");
                    }
                    AndroidUtilities.copyFile(in, out);
                }
                saved = uri;
            } catch (Throwable e) {
                FileLog.e(e);
                saved = null;
            }
            final Uri result = saved;
            AndroidUtilities.runOnUIThread(() -> {
                if (onDone != null) {
                    onDone.run(result);
                }
            });
        });
    }

    // API < 29: direct copy into public Downloads/Telegram (needs WRITE_EXTERNAL_STORAGE,
    // which upstream already requests on first launch for legacy devices)
    private static void saveLegacy(String sourcePath, String displayName, String mimeType, final Utilities.Callback<Uri> onDone) {
        Utilities.globalQueue.postRunnable(() -> {
            Uri saved = null;
            try {
                File src = new File(sourcePath);
                if (!src.exists()) {
                    throw new IllegalStateException("source missing: " + sourcePath);
                }
                File dir = new File(Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS), "Telegram");
                dir.mkdirs();
                File dest = new File(dir, displayName);
                String name = displayName;
                String ext = "";
                int idx = displayName.lastIndexOf('.');
                if (idx >= 0) {
                    name = displayName.substring(0, idx);
                    ext = displayName.substring(idx);
                }
                for (int a = 1; a <= 20 && dest.exists(); a++) {
                    dest = new File(dir, name + " (" + a + ")" + ext);
                }
                try (FileInputStream in = new FileInputStream(src);
                     FileOutputStream out = new FileOutputStream(dest)) {
                    AndroidUtilities.copyFile(in, out);
                }
                MediaScannerConnection.scanFile(ApplicationLoader.applicationContext,
                    new String[]{dest.getAbsolutePath()}, new String[]{mimeType}, null);
                saved = Uri.fromFile(dest);
            } catch (Throwable e) {
                FileLog.e(e);
                saved = null;
            }
            final Uri result = saved;
            AndroidUtilities.runOnUIThread(() -> {
                if (onDone != null) {
                    onDone.run(result);
                }
            });
        });
    }
}
