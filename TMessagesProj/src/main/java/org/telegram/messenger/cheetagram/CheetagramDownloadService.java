/*
 * Cheetagram — foreground service for the sequential download queue.
 *
 * Guarantees that queued downloads keep running while the screen is OFF /
 * the device is LOCKED:
 *  - Runs as a foreground service (dataSync type) with a visible notification.
 *  - Holds a PARTIAL_WAKE_LOCK so the CPU never sleeps mid-download.
 *  - Holds a low-latency WifiLock so Wi-Fi does not enter power-save mode.
 *  - START_STICKY: if the system kills the process, the service is restarted
 *    and the persistent queue (SQLite) continues from where it stopped.
 */
package org.telegram.messenger.cheetagram;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.net.wifi.WifiManager;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import android.text.TextUtils;

import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.UserConfig;
import org.telegram.ui.LaunchActivity;

import androidx.core.app.NotificationCompat;

public class CheetagramDownloadService extends Service implements NotificationCenter.NotificationCenterDelegate {

    public static final String ACTION_STOP_QUEUE = "org.telegram.cheetagram.ACTION_STOP_QUEUE";
    public static final String CHANNEL_ID = "cheetagram_download_queue";

    private static final int NOTIFICATION_ID = 47302;

    private static volatile boolean running = false;

    private PowerManager.WakeLock wakeLock;
    private WifiManager.WifiLock wifiLock;
    private NotificationCompat.Builder builder;
    private StopReceiver stopReceiver;
    private int account;

    public static boolean isRunning() {
        return running;
    }

    /** Starts (or re-syncs) the foreground service. Safe to call from any thread. */
    public static void start(int currentAccount) {
        try {
            Context context = ApplicationLoader.applicationContext;
            Intent intent = new Intent(context, CheetagramDownloadService.class);
            intent.putExtra("account", currentAccount);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent);
            } else {
                context.startService(intent);
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    /** Stops the service if it is running. Safe to call from any thread. */
    public static void stop() {
        if (!running) {
            return;
        }
        try {
            Context context = ApplicationLoader.applicationContext;
            context.stopService(new Intent(context, CheetagramDownloadService.class));
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    @Override
    public void onCreate() {
        super.onCreate();
        running = true;
        account = UserConfig.selectedAccount;
        acquireLocks();

        stopReceiver = new StopReceiver();
        IntentFilter filter = new IntentFilter(ACTION_STOP_QUEUE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(stopReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(stopReceiver, filter);
        }

        ensureChannel();
        builder = new NotificationCompat.Builder(ApplicationLoader.applicationContext, CHANNEL_ID);
        builder.setSmallIcon(R.drawable.msg_download)
            .setOnlyAlertOnce(true)
            .setOngoing(true)
            .setChannelId(CHANNEL_ID);

        NotificationCenter.getInstance(account).addObserver(this, NotificationCenter.fileLoadProgressChanged);

        // Force the queue to (re)start processing so the notification fills in.
        AndroidUtilities.runOnUIThread(CheetagramDownloadQueue.getInstance(account)::processNext);
    }

    private void ensureChannel() {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
                if (nm != null && nm.getNotificationChannel(CHANNEL_ID) == null) {
                    NotificationChannel channel = new NotificationChannel(
                        CHANNEL_ID,
                        LocaleController.getString(R.string.CheetagramQueueChannel),
                        NotificationManager.IMPORTANCE_LOW
                    );
                    channel.setShowBadge(false);
                    nm.createNotificationChannel(channel);
                }
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    private void acquireLocks() {
        try {
            PowerManager pm = (PowerManager) getSystemService(Context.POWER_SERVICE);
            if (pm != null && wakeLock == null) {
                wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "cheetagram:download-queue");
                wakeLock.setReferenceCounted(false);
                wakeLock.acquire(6 * 60 * 60 * 1000L); // 6h cap, matches dataSync FGS limit
            }
            WifiManager wm = (WifiManager) getApplicationContext().getSystemService(Context.WIFI_SERVICE);
            if (wm != null && wifiLock == null) {
                int mode;
                try {
                    mode = Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q
                        ? WifiManager.WIFI_MODE_FULL_LOW_LATENCY
                        : WifiManager.WIFI_MODE_FULL_HIGH_PERF;
                    wifiLock = wm.createWifiLock(mode, "cheetagram:download-queue");
                } catch (Throwable e) {
                    wifiLock = wm.createWifiLock(WifiManager.WIFI_MODE_FULL_HIGH_PERF, "cheetagram:download-queue");
                }
                wifiLock.setReferenceCounted(false);
                wifiLock.acquire();
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    private void releaseLocks() {
        try {
            if (wakeLock != null && wakeLock.isHeld()) {
                wakeLock.release();
            }
        } catch (Throwable ignore) {}
        wakeLock = null;
        try {
            if (wifiLock != null && wifiLock.isHeld()) {
                wifiLock.release();
            }
        } catch (Throwable ignore) {}
        wifiLock = null;
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && intent.hasExtra("account")) {
            account = intent.getIntExtra("account", UserConfig.selectedAccount);
        }

        buildBaseNotification();

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                startForeground(NOTIFICATION_ID, builder.build(), android.content.pm.ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC);
            } else {
                startForeground(NOTIFICATION_ID, builder.build());
            }
        } catch (Throwable e) {
            // ForegroundServiceStartNotAllowedException — e.g. app is in
            // background, or Android 15 blocks dataSync from BOOT_COMPLETED.
            // Stop cleanly (never leave a startForegroundService unfinished),
            // the queue stays persistent and resumes when the app opens.
            FileLog.e(e);
            stopSelf();
            return Service.START_NOT_STICKY;
        }

        if (!CheetagramDownloadQueue.getInstance(account).isProcessing()) {
            // Nothing to do (queue may have been cleared) — stop quietly.
            AndroidUtilities.runOnUIThread(() -> {
                if (!CheetagramDownloadQueue.getInstance(account).isProcessing()) {
                    stopSelf();
                }
            });
        }
        return Service.START_STICKY;
    }

    private void buildBaseNotification() {
        if (builder == null) {
            return;
        }
        Intent contentIntent = new Intent(this, LaunchActivity.class);
        PendingIntent contentPending = PendingIntent.getActivity(this, 4730, contentIntent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        // setPackage: on Android 14+ implicit broadcasts are NOT delivered to
        // RECEIVER_NOT_EXPORTED receivers unless the intent is package-scoped.
        Intent stopIntent = new Intent(ACTION_STOP_QUEUE).setPackage(getPackageName());
        PendingIntent stopPending = PendingIntent.getBroadcast(this, 4731, stopIntent, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);

        builder.setContentTitle(LocaleController.getString(R.string.CheetagramQueueTitle))
            .setContentText(LocaleController.getString(R.string.CheetagramQueuePreparing))
            .setContentIntent(contentPending)
            .setProgress(0, 0, true)
            .addAction(0, LocaleController.getString(R.string.CheetagramQueueStop), stopPending);
    }

    private void showProgressNotification(String fileName, int done, int total, int percent) {
        if (builder == null) {
            return;
        }
        builder.setContentTitle(LocaleController.formatString("CheetagramQueueDownloading", R.string.CheetagramQueueDownloading, done, total))
            .setContentText(fileName);
        if (percent >= 0) {
            builder.setProgress(100, Math.max(0, Math.min(100, percent)), false);
        } else {
            builder.setProgress(0, 0, true);
        }
        updateNotification();
    }

    @Override
    public void didReceivedNotification(int id, int account, Object... args) {
        if (id != NotificationCenter.fileLoadProgressChanged || builder == null) {
            return;
        }
        CheetagramDownloadQueue queue = CheetagramDownloadQueue.getInstance(account);
        if (!queue.isProcessing()) {
            return;
        }
        String location = args.length > 0 ? (String) args[0] : null;
        long loaded = args.length > 1 && args[1] instanceof Long ? (Long) args[1] : 0L;
        long total = args.length > 2 && args[2] instanceof Long ? (Long) args[2] : 0L;

        if (!TextUtils.equals(location, queue.getCurrentFileName())) {
            return;
        }

        int percent = total > 0 ? (int) (loaded * 100 / total) : -1;
        showProgressNotification(queue.getCurrentDisplayName(), queue.getSessionDone(), queue.getSessionTotal(), percent);
    }

    private void updateNotification() {
        try {
            NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && builder != null) {
                nm.notify(NOTIFICATION_ID, builder.build());
            }
        } catch (Throwable e) {
            FileLog.e(e);
        }
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        running = false;
        try {
            NotificationCenter.getInstance(account).removeObserver(this, NotificationCenter.fileLoadProgressChanged);
        } catch (Throwable ignore) {}
        try {
            if (stopReceiver != null) {
                unregisterReceiver(stopReceiver);
            }
        } catch (Throwable ignore) {}
        releaseLocks();
        builder = null;
    }

    @Override
    public void onTimeout(int startId, int fgsType) {
        // dataSync 6h/day background limit (Android 15+): drop foreground state.
        // Locks are released too; downloads continue in normal mode.
        FileLog.d("CheetagramDownloadService onTimeout, type = " + fgsType);
        try {
            stopForeground(true);
        } catch (Throwable ignore) {}
        releaseLocks();
        stopSelf();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private class StopReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (ACTION_STOP_QUEUE.equals(intent.getAction())) {
                CheetagramDownloadQueue.getInstance(account).clearAll();
                stopSelf();
            }
        }
    }
}
