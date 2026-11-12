# Telegram Client — Android

کلاینت تلگرام برای اندروید، بر پایه سورس رسمی تلگرام (DrKLO/Telegram) — مشابه پروژه‌هایی مثل Nekogram و Owlgram — با برنامه افزودن امکانات و تغییرات بیشتر.

A custom Telegram client for Android based on the official Telegram for Android source code, with more features and customization planned.

> **Status / وضعیت:** Base import — پایه پروژه از سورس رسمی تلگرام اندروید وارد شده و خط تولید بیلد/ریلیز خودکار روی GitHub Actions راه‌اندازی شده است. امکانات سفارشی به‌زودی اضافه می‌شوند.

---

## Build & Release (GitHub Actions) / بیلد و ریلیز خودکار

همه بیلدها و ریلیزها روی سرورهای گیت‌هاب انجام می‌شود؛ نیازی به بیلد لوکال نیست.

| Trigger | Result |
|---|---|
| push یا PR به `main` | بیلد خودکار debug APK → دانلود از artifacts صفحه Actions |
| تگ `v*` (مثلاً `v13.2.2`) | ریلیز خودکار: APK امضاشده + AAB در صفحه Releases |
| اجرای دستی | تب Actions → Run workflow |

## Local build (اختیاری)

پیش‌نیازها: JDK 17+ (پیشنهادی 21)، Android SDK 36، NDK 27.2.12479018، CMake 3.22.1

```bash
git clone --recurse-submodules https://github.com/CheginiSoroush/telegram.git
cd telegram
./gradlew :TMessagesProj_App:assembleAfatDebug    # debug APK
./gradlew :TMessagesProj_App:assembleAfatRelease  # release APK
```

خروجی APK: `TMessagesProj_App/build/outputs/apk/afat/<variant>/app.apk`

## Structure / ساختار پروژه

| مسیر | توضیح |
|---|---|
| `TMessagesProj/` | هسته پروژه (library): UI، شبکه، کد نیتیو (jni)، ریسورس‌ها |
| `TMessagesProj_App/` | اپلیکیشن اصلی (`applicationId`: `org.telegram.messenger`) |
| `TMessagesProj_AppStandalone/` | واریانت standalone |
| `TMessagesProj_AppHuawei/` | واریانت Huawei |
| `TMessagesProj_Modules/` | ماژول‌های media3 (پخش رسانه) |
| `buildSrc/` | پلاگین‌های گریدل سفارشی تلگرام |

**Flavors:** `afat` (APK همه معماری‌ها) و `bundleAfat` (AAB) — **Build types:** `debug`، `release`، `standalone`

## Submodules / ساب‌ماژول‌ها

سورس نیتیو (ffmpeg، libvpx، dav1d، tdlib، tgcalls، boringssl و...) به‌صورت ساب‌ماژول اضافه شده. همیشه با `--recurse-submodules` کلون کنید:

```bash
git submodule update --init --recursive
```

## Signing / امضا

فعلاً بیلدها با keystore عمومی آپ‌استریم امضا می‌شوند (`TMessagesProj/config/release.keystore` — alias: `androidkey` — password: `android`).

> هشدار: قبل از هر ریلیز عمومی باید یک keystore خصوصیِ جدید ساخته و جایگزین شود؛ keystore عمومی فقط برای تست و پایه است.

## Versioning / نسخه‌گذاری

نسخه از `gradle.properties` خوانده می‌شود:

```properties
APP_VERSION_CODE=7303
APP_VERSION_NAME=13.2.2
APP_PACKAGE=org.telegram.messenger
```

## Roadmap / نقشه راه

- [ ] پایه: ایمپورت سورس + CI بیلد و ریلیز (انجام شد)
- [ ] شخصی‌سازی نام و برند اپلیکیشن
- [ ] تغییر applicationId برای نصب کنار تلگرام رسمی
- [ ] افزودن امکانات اختصاصی (به‌زودی)
