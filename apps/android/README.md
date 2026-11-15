# FINN for Android

An Android app that opens the live FINN web app (https://finn-ruddy.vercel.app) inside a WebView,
so the app and the website are always the same version. There is no separate Android UI to maintain.

The APK is built by GitHub Actions (`.github/workflows/android.yml`) and published at a fixed link:

**https://github.com/sahityaiitd-ml/finn/releases/download/android-latest/finn.apk**

## Install
1. Open the link on the Android phone and download `finn.apk`.
2. Tap the file. Android asks to allow installs from this source: allow it once.
3. Open **FINN**. If Play Protect warns that the app is unrecognised, choose **Install anyway**: this is a
   build signed with a debug key, not a Play Store release.

## Notes
- It needs a connection. If the server has been idle, the first screen can take about a minute to load.
- iOS cannot be sideloaded without an Apple Developer account; on iPhone, open the web link and use
  Share → Add to Home Screen.

## Build locally (optional)
Needs Node 22, JDK 21 and the Android SDK.
```bash
cd apps/android && npm install
npx cap add android
npx @capacitor/assets generate --android --assetPath assets
cd android && ./gradlew assembleDebug     # → app/build/outputs/apk/debug/app-debug.apk
```
