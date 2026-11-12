/*
 * Cheetagram — persistent sequential download queue.
 *
 * Lets the user queue multiple video/document messages from any chat and
 * downloads them ONE BY ONE (in enqueue order). The queue is stored in the
 * per-account MessagesStorage SQLite database, so it survives process death,
 * app restarts and full device reboots (resumed from AppStartReceiver).
 *
 * Flow: enqueue(messageObjects) -> rows (state=0 pending) -> processNext()
 * pulls the oldest pending row, starts a FileLoader download, and on
 * NotificationCenter.fileLoaded saves the file into the public Downloads
 * folder via MediaController.saveFile(type=2), then continues with the next
 * row until the queue is empty.
 */
package org.telegram.messenger.cheetagram;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.os.Build;
import android.text.TextUtils;

import org.telegram.SQLite.SQLiteCursor;
import org.telegram.SQLite.SQLitePreparedStatement;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.BaseController;
import org.telegram.messenger.FileLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MediaController;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.UserConfig;
import org.telegram.tgnet.NativeByteBuffer;
import org.telegram.tgnet.TLRPC;

import java.io.File;
import java.util.ArrayList;
import java.util.HashSet;

public class CheetagramDownloadQueue extends BaseController implements NotificationCenter.NotificationCenterDelegate {

    private static final String CHANNEL_ID = "cheetagram_download_queue";
    private static final int NOTIFICATION_ID = 47301;
    private static final int DONE_NOTIFICATION_ID = 47303;
    private static final long ITEM_TIMEOUT_MS = 45 * 60 * 1000L;
    private static final int MAX_ATTEMPTS = 3;

    // region Public state (read by CheetagramDownloadService)

    public boolean isProcessing() {
        return currentItem != null || pulling;
    }

    public String getCurrentFileName() {
        QueueItem item = currentItem;
        return item != null ? item.attachFileName : null;
    }

    public String getCurrentDisplayName() {
        QueueItem item = currentItem;
        return item != null ? item.displayName : null;
    }

    public int getSessionDone() {
        return sessionDone;
    }

    public int getSessionTotal() {
        return sessionTotal;
    }

    /**
     * Cancels everything: stops the current download, wipes the persisted
     * queue and stops the foreground service. Called from the service's
     * "Stop" notification action.
     */
    public void clearAll() {
        QueueItem item = currentItem;
        currentItem = null;
        AndroidUtilities.cancelRunOnUIThread(watchdogRunnable);
        if (item != null && item.document != null) {
            try {
                getFileLoader().cancelLoadFile(item.document);
            } catch (Throwable e) {
                FileLog.e(e);
            }
        }
        queuedDocIds.clear();
        sessionTotal = 0;
        sessionDone = 0;
        hadActiveSession = false;
        getMessagesStorage().getStorageQueue().postRunnable(() -> {
            try {
                getMessagesStorage().getDatabase().executeFast("DELETE FROM cheetagram_queue").stepThis().dispose();
            } catch (Exception e) {
                FileLog.e(e);
            }
        });
        cancelNotification();
        CheetagramDownloadService.stop();
    }

    // endregion

    private static volatile CheetagramDownloadQueue[] Instance = new CheetagramDownloadQueue[UserConfig.MAX_ACCOUNT_COUNT];

    public static CheetagramDownloadQueue getInstance(int num) {
        CheetagramDownloadQueue localInstance = Instance[num];
        if (localInstance == null) {
            synchronized (CheetagramDownloadQueue.class) {
                localInstance = Instance[num];
                if (localInstance == null) {
                    localInstance = Instance[num] = new CheetagramDownloadQueue(num);
                }
            }
        }
        return localInstance;
    }

    /**
     * Resumes the queue for every active account. Called from
     * AppStartReceiver (BOOT_COMPLETED) and LaunchActivity.onCreate.
     */
    public static void resumeAll() {
        for (int a = 0; a < UserConfig.MAX_ACCOUNT_COUNT; a++) {
            if (UserConfig.getInstance(a).isClientActivated()) {
                CheetagramDownloadQueue.getInstance(a).resumeIfNeeded();
            }
        }
    }

    private static class QueueItem {
        long docId;
        long size;
        String attachFileName;
        String displayName;
        TLRPC.Message message;
        TLRPC.Document document;
        int attempts;
    }

    private QueueItem currentItem;
    private boolean pulling;
    private boolean hadActiveSession;
    private int sessionTotal;
    private int sessionDone;
    private final HashSet<Long> queuedDocIds = new HashSet<>();

    private final Runnable watchdogRunnable = () -> {
        if (currentItem != null) {
            FileLog.e("CheetagramDownloadQueue item timeout docId=" + currentItem.docId);
            finishItem(false);
        }
    };

    private CheetagramDownloadQueue(int instance) {
        super(instance);
        ensureTable();
        AndroidUtilities.runOnUIThread(() -> {
            getNotificationCenter().addObserver(this, NotificationCenter.fileLoaded);
            getNotificationCenter().addObserver(this, NotificationCenter.fileLoadFailed);
        });
    }

    // region Database

    private void ensureTable() {
        getMessagesStorage().getStorageQueue().postRunnable(() -> {
            try {
                getMessagesStorage().getDatabase().executeFast("CREATE TABLE IF NOT EXISTS cheetagram_queue(data BLOB, dialog_id INTEGER, msg_id INTEGER, doc_id INTEGER, state INTEGER, date INTEGER, PRIMARY KEY(doc_id))").stepThis().dispose();
            } catch (Exception e) {
                FileLog.e(e);
            }
        });
    }

    /**
     * Adds documents (videos/files/music) extracted from the given selected
     * messages to the persistent queue. Returns the number of items actually
     * added (duplicates are skipped). Must be called from the main thread.
     */
    public int enqueue(ArrayList<MessageObject> messageObjects) {
        if (messageObjects == null || messageObjects.isEmpty()) {
            return 0;
        }
        int added = 0;
        final long now = System.currentTimeMillis();
        for (int i = 0; i < messageObjects.size(); i++) {
            MessageObject messageObject = messageObjects.get(i);
            final TLRPC.Document document = messageObject == null ? null : messageObject.getDocument();
            final TLRPC.Message message = messageObject == null ? null : messageObject.messageOwner;
            if (document == null || message == null || document.dc_id == 0) {
                continue;
            }
            final long docId = document.id;
            if (!queuedDocIds.add(docId)) {
                continue;
            }
            added++;
            final long date = now + added;
            getMessagesStorage().getStorageQueue().postRunnable(() -> {
                NativeByteBuffer data = null;
                try {
                    SQLiteCursor cursor = getMessagesStorage().getDatabase().queryFinalized("SELECT doc_id FROM cheetagram_queue WHERE doc_id = " + docId);
                    boolean exists = cursor.next();
                    cursor.dispose();
                    if (exists) {
                        return;
                    }
                    data = new NativeByteBuffer(message.getObjectSize());
                    message.serializeToStream(data);
                    SQLitePreparedStatement state = getMessagesStorage().getDatabase().executeFast("REPLACE INTO cheetagram_queue(data, dialog_id, msg_id, doc_id, state, date) VALUES(?, ?, ?, ?, ?, ?)");
                    state.bindByteBuffer(1, data);
                    state.bindLong(2, message.dialog_id);
                    state.bindInteger(3, message.id);
                    state.bindLong(4, docId);
                    state.bindInteger(5, 0);
                    state.bindLong(6, date);
                    state.step();
                    state.dispose();
                    AndroidUtilities.runOnUIThread(CheetagramDownloadQueue.this::processNext);
                } catch (Exception e) {
                    FileLog.e(e);
                    AndroidUtilities.runOnUIThread(() -> queuedDocIds.remove(docId));
                } finally {
                    if (data != null) {
                        data.reuse();
                    }
                }
            });
        }
        if (added > 0) {
            sessionTotal += added;
            AndroidUtilities.runOnUIThread(this::processNext);
        }
        return added;
    }

    /** Resets stale "processing" rows back to pending and starts the queue. */
    public void resumeIfNeeded() {
        CheetagramDownloadQueue self = this;
        getMessagesStorage().getStorageQueue().postRunnable(() -> {
            int pending = 0;
            try {
                getMessagesStorage().getDatabase().executeFast("UPDATE cheetagram_queue SET state = 0 WHERE state = 1").stepThis().dispose();
                SQLiteCursor cursor = getMessagesStorage().getDatabase().queryFinalized("SELECT COUNT(*) FROM cheetagram_queue WHERE state = 0");
                if (cursor.next()) {
                    pending = (int) cursor.longValue(0);
                }
                cursor.dispose();
            } catch (Exception e) {
                FileLog.e(e);
            }
            final int count = pending;
            AndroidUtilities.runOnUIThread(() -> {
                sessionTotal = count;
                sessionDone = 0;
                if (count > 0) {
                    hadActiveSession = true;
                }
                self.processNext();
            });
        });
    }

    private void deleteRow(long docId) {
        getMessagesStorage().getStorageQueue().postRunnable(() -> {
            try {
                getMessagesStorage().getDatabase().executeFast("DELETE FROM cheetagram_queue WHERE doc_id = " + docId).stepThis().dispose();
            } catch (Exception e) {
                FileLog.e(e);
            }
        });
        queuedDocIds.remove(docId);
    }

    // endregion

    // region Processing

    void processNext() {
        if (currentItem != null || pulling) {
            return;
        }
        pulling = true;
        getMessagesStorage().getStorageQueue().postRunnable(() -> {
            QueueItem next = null;
            try {
                SQLiteCursor cursor = getMessagesStorage().getDatabase().queryFinalized("SELECT data, dialog_id, msg_id, doc_id FROM cheetagram_queue WHERE state = 0 ORDER BY date ASC LIMIT 1");
                if (cursor.next()) {
                    NativeByteBuffer data = cursor.byteBufferValue(0);
                    if (data != null) {
                        TLRPC.Message message = TLRPC.Message.TLdeserialize(data, data.readInt32(false), false);
                        if (message != null) {
                            message.readAttachPath(data, UserConfig.getInstance(currentAccount).clientUserId);
                            next = new QueueItem();
                            next.message = message;
                            next.docId = cursor.longValue(3);
                            next.document = MessageObject.getDocument(message);
                        }
                        data.reuse();
                    }
                }
                cursor.dispose();
                if (next != null) {
                    getMessagesStorage().getDatabase().executeFast("UPDATE cheetagram_queue SET state = 1 WHERE doc_id = " + next.docId).stepThis().dispose();
                }
            } catch (Exception e) {
                FileLog.e(e);
            }
            final QueueItem item = next;
            AndroidUtilities.runOnUIThread(() -> {
                pulling = false;
                if (item == null) {
                    CheetagramDownloadService.stop();
                    if (hadActiveSession) {
                        notifyQueueDone();
                        hadActiveSession = false;
                    } else {
                        cancelNotification();
                    }
                    return;
                }
                if (currentItem != null) {
                    // Safety: another item is already active, push this one back to pending.
                    getMessagesStorage().getStorageQueue().postRunnable(() -> {
                        try {
                            getMessagesStorage().getDatabase().executeFast("UPDATE cheetagram_queue SET state = 0 WHERE doc_id = " + item.docId).stepThis().dispose();
                        } catch (Exception e) {
                            FileLog.e(e);
                        }
                    });
                    return;
                }
                startItem(item);
            });
        });
    }

    private void startItem(QueueItem item) {
        currentItem = item;
        hadActiveSession = true;
        if (item.document == null) {
            finishItem(true);
            return;
        }
        item.attachFileName = FileLoader.getAttachFileName(item.document);
        item.displayName = FileLoader.getDocumentFileName(item.document);
        if (TextUtils.isEmpty(item.displayName)) {
            item.displayName = item.attachFileName != null ? item.attachFileName : ("file_" + item.docId);
        }
        item.size = item.document.size;

        // Foreground service keeps the CPU awake and Wi-Fi at full power so
        // downloads continue while the screen is locked / device in Doze.
        CheetagramDownloadService.start(currentAccount);

        File existing = getFileLoader().getPathToMessage(item.message, true);
        if (existing != null && existing.exists()) {
            saveToDownloads(existing.getAbsolutePath());
            return;
        }

        MessageObject wrapper = new MessageObject(currentAccount, item.message, false, false);
        wrapper.putInDownloadsStore = true;
        scheduleWatchdog();
        getFileLoader().loadFile(item.document, wrapper, FileLoader.PRIORITY_NORMAL, 0);
    }

    private void saveToDownloads(String readyPath) {
        QueueItem item = currentItem;
        if (item == null) {
            return;
        }
        if (TextUtils.isEmpty(readyPath)) {
            File file = getFileLoader().getPathToMessage(item.message, true);
            readyPath = file != null ? file.getAbsolutePath() : null;
        }
        if (TextUtils.isEmpty(readyPath)) {
            finishItem(false);
            return;
        }
        final String path = readyPath;
        final String mime = item.document.mime_type != null ? item.document.mime_type : "application/octet-stream";
        MediaController.saveFile(path, ApplicationLoader.applicationContext, 2, item.displayName, mime, uri ->
            AndroidUtilities.runOnUIThread(() -> finishItem(true))
        );
    }

    private void finishItem(boolean success) {
        QueueItem item = currentItem;
        if (item == null) {
            return;
        }
        currentItem = null;
        AndroidUtilities.cancelRunOnUIThread(watchdogRunnable);
        sessionDone++;
        if (!success && item.attempts + 1 < MAX_ATTEMPTS) {
            item.attempts++;
            final long docId = item.docId;
            getMessagesStorage().getStorageQueue().postRunnable(() -> {
                try {
                    getMessagesStorage().getDatabase().executeFast("UPDATE cheetagram_queue SET state = 0 WHERE doc_id = " + docId).stepThis().dispose();
                } catch (Exception e) {
                    FileLog.e(e);
                }
            });
        } else {
            deleteRow(item.docId);
        }
        processNext();
    }

    private void scheduleWatchdog() {
        AndroidUtilities.cancelRunOnUIThread(watchdogRunnable);
        AndroidUtilities.runOnUIThread(watchdogRunnable, ITEM_TIMEOUT_MS);
    }

    // endregion

    // region NotificationCenter

    @Override
    public void didReceivedNotification(int id, int account, Object... args) {
        if (account != currentAccount || currentItem == null) {
            return;
        }
        if (id == NotificationCenter.fileLoaded) {
            String location = (String) args[0];
            if (currentItem.attachFileName != null && currentItem.attachFileName.equals(location)) {
                AndroidUtilities.cancelRunOnUIThread(watchdogRunnable);
                saveToDownloads(null);
            }
        } else if (id == NotificationCenter.fileLoadFailed) {
            String location = (String) args[0];
            if (currentItem.attachFileName != null && currentItem.attachFileName.equals(location)) {
                AndroidUtilities.cancelRunOnUIThread(watchdogRunnable);
                finishItem(false);
            }
        }
        // Progress events are handled by CheetagramDownloadService (foreground
        // notification); the queue itself only reacts to completion/failure.
    }

    // endregion

    // region Notifications

    private void ensureChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager nm = (NotificationManager) ApplicationLoader.applicationContext.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null && nm.getNotificationChannel(CHANNEL_ID) == null) {
                NotificationChannel channel = new NotificationChannel(CHANNEL_ID, LocaleController.getString(R.string.CheetagramQueueChannel), NotificationManager.IMPORTANCE_LOW);
                nm.createNotificationChannel(channel);
            }
        }
    }

    private void notifyQueueDone() {
        ensureChannel();
        Context context = ApplicationLoader.applicationContext;
        Notification.Builder builder = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
            ? new Notification.Builder(context, CHANNEL_ID)
            : new Notification.Builder(context);
        builder.setSmallIcon(R.drawable.msg_download)
            .setContentTitle(LocaleController.getString(R.string.CheetagramQueueTitle))
            .setContentText(LocaleController.getString(R.string.CheetagramQueueDone))
            .setAutoCancel(true);
        notifySafely(DONE_NOTIFICATION_ID, builder.build());
    }

    private void cancelNotification() {
        try {
            NotificationManager nm = (NotificationManager) ApplicationLoader.applicationContext.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.cancel(NOTIFICATION_ID);
            }
        } catch (Exception e) {
            FileLog.e(e);
        }
    }

    private void notifySafely(int id, Notification notification) {
        try {
            NotificationManager nm = (NotificationManager) ApplicationLoader.applicationContext.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm != null) {
                nm.notify(id, notification);
            }
        } catch (Exception e) {
            FileLog.e(e);
        }
    }

    // endregion
}
