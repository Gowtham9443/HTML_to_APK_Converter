#!/usr/bin/env python3
"""
HTML → APK Builder
Developed by BEST_TEAM
Converts a single-file HTML project into an installable Android APK.
"""

import os
import sys
import re
import shutil
import subprocess
import logging
import datetime
import textwrap
from pathlib import Path

# ─────────────────────────── CONFIGURATION ───────────────────────────
APP_NAME     = "MyWebApp"
PACKAGE_NAME = "com.bestteam.generatedapp"
VERSION_CODE = 1
VERSION_NAME = "1.0"
MIN_SDK      = 21     # Android 5.0+
TARGET_SDK   = 34     # Android 14
COMPILE_SDK  = 34

# ─────────────────────────── PATHS ───────────────────────────────────
BASE_DIR      = Path(__file__).parent.resolve()
INPUT_HTML    = BASE_DIR / "input_project" / "index.html"
BUILD_DIR     = BASE_DIR / "build" / "android_project"
OUTPUT_DIR    = BASE_DIR / "output"
LOG_DIR       = BASE_DIR / "logs"

PACKAGE_PATH  = PACKAGE_NAME.replace(".", "/")
JAVA_DIR      = BUILD_DIR / "app" / "src" / "main" / "java" / PACKAGE_PATH
ASSETS_DIR    = BUILD_DIR / "app" / "src" / "main" / "assets"
RES_DIR       = BUILD_DIR / "app" / "src" / "main" / "res"
MANIFEST_PATH = BUILD_DIR / "app" / "src" / "main" / "AndroidManifest.xml"

# ─────────────────────────── LOGGING ─────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
timestamp   = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
log_file    = LOG_DIR / f"build_{timestamp}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("html2apk")


# ═════════════════════════════════════════════════════════════════════
# STEP 1 — HTML ANALYSER
# ═════════════════════════════════════════════════════════════════════

class HtmlFeatures:
    """Detected feature flags from the source HTML."""
    def __init__(self):
        self.needs_internet       = False
        self.needs_storage        = False
        self.needs_camera         = False
        self.needs_microphone     = False
        self.needs_location       = False
        self.uses_local_storage   = False
        self.uses_iframe          = False
        self.uses_file_input      = False
        self.uses_drag_drop       = False
        self.uses_media           = False
        self.uses_dark_mode       = False
        self.uses_geolocation     = False
        self.uses_webrtc          = False

    def summary(self) -> list[str]:
        lines = []
        for k, v in vars(self).items():
            if v:
                lines.append(k.replace("_", " ").title())
        return lines


def analyse_html(html: str) -> HtmlFeatures:
    f = HtmlFeatures()
    lower = html.lower()

    # Internet
    if any(x in lower for x in ["http://", "https://", "fetch(", "xmlhttprequest",
                                   "cdn.", "ajax", "import ", "require("]):
        f.needs_internet = True

    # Storage
    if "localstorage" in lower or "sessionstorage" in lower or "indexeddb" in lower:
        f.uses_local_storage = True

    # File input
    if 'type="file"' in lower or "type='file'" in lower:
        f.uses_file_input    = True
        f.needs_storage      = True

    # Drag & drop
    if "draggable" in lower or "ondrop" in lower or "dragover" in lower or "dragevent" in lower:
        f.uses_drag_drop = True

    # IFrame
    if "<iframe" in lower:
        f.uses_iframe = True

    # Media
    if "<video" in lower or "<audio" in lower or "getusermedia" in lower:
        f.uses_media = True

    # Camera / Microphone (getUserMedia)
    if "getusermedia" in lower or "mediastreamconstraints" in lower:
        f.needs_camera    = True
        f.needs_microphone = True

    # Geolocation
    if "geolocation" in lower or "getcurrentposition" in lower:
        f.needs_location  = True
        f.uses_geolocation = True

    # WebRTC
    if "rtcpeerconnection" in lower or "webrtc" in lower:
        f.uses_webrtc    = True
        f.needs_internet = True

    # Dark mode
    if "prefers-color-scheme" in lower or 'data-theme' in lower:
        f.uses_dark_mode = True

    return f


# ═════════════════════════════════════════════════════════════════════
# STEP 2 — ANDROID PROJECT GENERATOR
# ═════════════════════════════════════════════════════════════════════

def permissions_xml(f: HtmlFeatures) -> str:
    perms = []
    if f.needs_internet:
        perms.append('<uses-permission android:name="android.permission.INTERNET" />')
    if f.needs_storage:
        perms.append('<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" android:maxSdkVersion="32" />')
        perms.append('<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" android:maxSdkVersion="29" />')
        perms.append('<uses-permission android:name="android.permission.READ_MEDIA_IMAGES" />')
    if f.needs_camera:
        perms.append('<uses-permission android:name="android.permission.CAMERA" />')
        perms.append('<uses-feature android:name="android.hardware.camera" android:required="false" />')
    if f.needs_microphone:
        perms.append('<uses-permission android:name="android.permission.RECORD_AUDIO" />')
    if f.needs_location:
        perms.append('<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION" />')
        perms.append('<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />')
    return "\n    ".join(perms)


def generate_manifest(f: HtmlFeatures) -> str:
    return textwrap.dedent(f"""\
    <?xml version="1.0" encoding="utf-8"?>
    <manifest xmlns:android="http://schemas.android.com/apk/res/android"
        package="{PACKAGE_NAME}">

        {permissions_xml(f)}

        <application
            android:allowBackup="true"
            android:icon="@mipmap/ic_launcher"
            android:label="{APP_NAME}"
            android:roundIcon="@mipmap/ic_launcher_round"
            android:supportsRtl="true"
            android:theme="@style/AppTheme"
            android:hardwareAccelerated="true"
            android:usesCleartextTraffic="true">

            <activity
                android:name=".MainActivity"
                android:exported="true"
                android:configChanges="orientation|screenSize|keyboardHidden"
                android:windowSoftInputMode="adjustResize">
                <intent-filter>
                    <action android:name="android.intent.action.MAIN" />
                    <category android:name="android.intent.category.LAUNCHER" />
                </intent-filter>
            </activity>
        </application>
    </manifest>
    """)


def generate_main_activity(f: HtmlFeatures) -> str:
    extra_imports = []
    extra_webview = []
    extra_client  = []
    extra_fields  = []

    if f.uses_file_input or f.uses_drag_drop:
        extra_imports += [
            "import android.content.Intent;",
            "import android.net.Uri;",
            "import android.webkit.ValueCallback;",
            "import android.webkit.WebChromeClient;",
            "import androidx.activity.result.ActivityResultLauncher;",
            "import androidx.activity.result.contract.ActivityResultContracts;",
        ]
        extra_fields += [
            "private ValueCallback<Uri[]> mFilePathCallback;",
            "private ActivityResultLauncher<Intent> filePickerLauncher;",
        ]
        extra_webview += [
            "webView.setWebChromeClient(new CustomChromeClient());",
        ]
        extra_client += [
            """
    class CustomChromeClient extends WebChromeClient {
        @Override
        public boolean onShowFileChooser(android.webkit.WebView webView,
                ValueCallback<Uri[]> filePathCallback,
                WebChromeClient.FileChooserParams fileChooserParams) {
            if (mFilePathCallback != null) mFilePathCallback.onReceiveValue(null);
            mFilePathCallback = filePathCallback;
            Intent intent = fileChooserParams.createIntent();
            try {
                filePickerLauncher.launch(intent);
            } catch (Exception e) {
                mFilePathCallback = null;
                return false;
            }
            return true;
        }

        @Override
        public void onPermissionRequest(android.webkit.PermissionRequest request) {
            request.grant(request.getResources());
        }
    }"""
        ]

    geolocation_setup = ""
    if f.uses_geolocation:
        extra_imports += [
            "import android.webkit.GeolocationPermissions;",
        ]
        if not f.uses_file_input:
            extra_webview += ["webView.setWebChromeClient(new CustomChromeClient());"]
        extra_client += [
            """
    @Override
    public void onGeolocationPermissionsShowPrompt(String origin,
            GeolocationPermissions.Callback callback) {
        callback.invoke(origin, true, false);
    }"""
        ]

    imports_str = "\n".join(extra_imports)
    fields_str  = "\n    ".join(extra_fields)
    webview_str = "\n        ".join(extra_webview)
    client_str  = "\n".join(extra_client)

    file_picker_init = ""
    if f.uses_file_input or f.uses_drag_drop:
        file_picker_init = """
        filePickerLauncher = registerForActivityResult(
            new ActivityResultContracts.StartActivityForResult(), result -> {
                if (mFilePathCallback == null) return;
                Uri[] results = WebChromeClient.FileChooserParams.parseResult(
                    result.getResultCode(), result.getData());
                mFilePathCallback.onReceiveValue(results);
                mFilePathCallback = null;
            });"""

    return textwrap.dedent(f"""\
    package {PACKAGE_NAME};

    import android.annotation.SuppressLint;
    import android.os.Bundle;
    import android.webkit.WebSettings;
    import android.webkit.WebView;
    import android.webkit.WebViewClient;
    import androidx.appcompat.app.AppCompatActivity;
    {imports_str}

    public class MainActivity extends AppCompatActivity {{

        private WebView webView;
        {fields_str}

        @SuppressLint("SetJavaScriptEnabled")
        @Override
        protected void onCreate(Bundle savedInstanceState) {{
            super.onCreate(savedInstanceState);
            setContentView(R.layout.activity_main);
            {file_picker_init}

            webView = findViewById(R.id.webView);
            WebSettings s = webView.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setAllowFileAccess(true);
            s.setAllowContentAccess(true);
            s.setMediaPlaybackRequiresUserGesture(false);
            s.setDatabaseEnabled(true);
            s.setCacheMode(WebSettings.LOAD_DEFAULT);
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
            s.setSupportZoom(false);
            s.setBuiltInZoomControls(false);
            s.setDisplayZoomControls(false);
            {webview_str}
            webView.setWebViewClient(new WebViewClient());
            webView.loadUrl("file:///android_asset/index.html");
        }}

        @Override
        public void onBackPressed() {{
            if (webView.canGoBack()) {{
                webView.goBack();
            }} else {{
                super.onBackPressed();
            }}
        }}
        {client_str}
    }}
    """)


def generate_app_build_gradle() -> str:
    return textwrap.dedent(f"""\
    plugins {{
        id 'com.android.application'
    }}

    android {{
        compileSdkVersion {COMPILE_SDK}
        namespace "{PACKAGE_NAME}"

        defaultConfig {{
            applicationId "{PACKAGE_NAME}"
            minSdkVersion {MIN_SDK}
            targetSdkVersion {TARGET_SDK}
            versionCode {VERSION_CODE}
            versionName "{VERSION_NAME}"
        }}

        buildTypes {{
            debug {{
                debuggable true
            }}
            release {{
                minifyEnabled false
                proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
            }}
        }}

        compileOptions {{
            sourceCompatibility JavaVersion.VERSION_17
            targetCompatibility JavaVersion.VERSION_17
        }}
    }}

    dependencies {{
        implementation 'androidx.appcompat:appcompat:1.6.1'
        implementation 'com.google.android.material:material:1.11.0'
        implementation 'androidx.constraintlayout:constraintlayout:2.1.4'
    }}
    """)


def generate_settings_gradle() -> str:
    return textwrap.dedent(f"""\
    pluginManagement {{
        repositories {{
            google()
            mavenCentral()
            gradlePluginPortal()
        }}
    }}
    dependencyResolutionManagement {{
        repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
        repositories {{
            google()
            mavenCentral()
        }}
    }}

    rootProject.name = "{APP_NAME}"
    include ':app'
    """)


def generate_root_build_gradle() -> str:
    return textwrap.dedent("""\
    plugins {
        id 'com.android.application' version '8.3.0' apply false
    }
    """)


def generate_gradle_properties() -> str:
    return textwrap.dedent("""\
    org.gradle.jvmargs=-Xmx2048m -Dfile.encoding=UTF-8
    android.useAndroidX=true
    android.enableJetifier=true
    """)


def generate_layout() -> str:
    return textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
        android:layout_width="match_parent"
        android:layout_height="match_parent">

        <WebView
            android:id="@+id/webView"
            android:layout_width="match_parent"
            android:layout_height="match_parent" />
    </FrameLayout>
    """)


def generate_styles() -> str:
    return textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <resources>
        <style name="AppTheme" parent="Theme.AppCompat.NoActionBar">
            <item name="colorPrimary">#1976D2</item>
            <item name="colorPrimaryDark">#0D47A1</item>
            <item name="colorAccent">#42A5F5</item>
            <item name="android:windowBackground">@android:color/white</item>
        </style>
    </resources>
    """)


def generate_network_security() -> str:
    return textwrap.dedent("""\
    <?xml version="1.0" encoding="utf-8"?>
    <network-security-config>
        <base-config cleartextTrafficPermitted="true">
            <trust-anchors>
                <certificates src="system" />
            </trust-anchors>
        </base-config>
    </network-security-config>
    """)


def generate_launcher_icon_svg() -> str:
    """Returns a minimal SVG launcher icon (used as placeholder)."""
    return textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <vector xmlns:android="http://schemas.android.com/apk/res/android"
        android:width="108dp"
        android:height="108dp"
        android:viewportWidth="108"
        android:viewportHeight="108">
      <path android:fillColor="#1976D2" android:pathData="M0,0h108v108h-108z"/>
      <path android:fillColor="#FFFFFF"
        android:pathData="M32,30 L76,30 Q80,30 80,34 L80,58 Q80,62 76,62 L60,62 L54,74 L48,62 L32,62 Q28,62 28,58 L28,34 Q28,30 32,30z"/>
    </vector>
    """)


def write_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    log.debug(f"  Wrote: {path.relative_to(BASE_DIR)}")


def generate_android_project(html: str, f: HtmlFeatures):
    log.info("Generating Android project structure …")

    # Clean previous build
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    # Assets
    write_file(ASSETS_DIR / "index.html", html)

    # Java
    write_file(JAVA_DIR / "MainActivity.java", generate_main_activity(f))

    # Manifest
    write_file(MANIFEST_PATH, generate_manifest(f))

    # Res
    write_file(RES_DIR / "layout" / "activity_main.xml", generate_layout())
    write_file(RES_DIR / "values" / "styles.xml", generate_styles())
    write_file(RES_DIR / "xml" / "network_security_config.xml", generate_network_security())

    # Launcher icons (vector drawable as placeholder)
    for density in ["mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi", "mipmap-xxhdpi", "mipmap-xxxhdpi"]:
        write_file(RES_DIR / density / "ic_launcher.xml", generate_launcher_icon_svg())
        write_file(RES_DIR / density / "ic_launcher_round.xml", generate_launcher_icon_svg())

    # Gradle files
    write_file(BUILD_DIR / "app" / "build.gradle", generate_app_build_gradle())
    write_file(BUILD_DIR / "app" / "proguard-rules.pro", "# Add project specific ProGuard rules here.\n")
    write_file(BUILD_DIR / "settings.gradle", generate_settings_gradle())
    write_file(BUILD_DIR / "build.gradle", generate_root_build_gradle())
    write_file(BUILD_DIR / "gradle.properties", generate_gradle_properties())

    # gradle wrapper
    _write_gradle_wrapper()

    log.info("Android project generation complete.")


def _write_gradle_wrapper():
    wrapper_dir = BUILD_DIR / "gradle" / "wrapper"
    wrapper_dir.mkdir(parents=True, exist_ok=True)
    props = textwrap.dedent("""\
    distributionBase=GRADLE_USER_HOME
    distributionPath=wrapper/dists
    distributionUrl=https\\://services.gradle.org/distributions/gradle-8.4-bin.zip
    zipStoreBase=GRADLE_USER_HOME
    zipStorePath=wrapper/dists
    """)
    write_file(wrapper_dir / "gradle-wrapper.properties", props)

    # gradlew (Unix)
    gradlew = textwrap.dedent("""\
    #!/bin/sh
    exec "$(dirname "$0")/gradle/wrapper/gradlew" "$@"
    """)
    gradlew_path = BUILD_DIR / "gradlew"
    gradlew_path.write_text(gradlew)
    gradlew_path.chmod(0o755)

    # gradlew.bat (Windows)
    gradlew_bat = textwrap.dedent("""\
    @echo off
    "%~dp0gradle\\wrapper\\gradlew.bat" %*
    """)
    write_file(BUILD_DIR / "gradlew.bat", gradlew_bat)


# ═════════════════════════════════════════════════════════════════════
# STEP 3 — APK COMPILER
# ═════════════════════════════════════════════════════════════════════

def find_sdk() -> Path | None:
    candidates = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        Path.home() / "Android" / "Sdk",
        Path.home() / "AppData" / "Local" / "Android" / "Sdk",
        Path("/opt/android-sdk"),
        Path("/usr/local/lib/android/sdk"),
    ]
    for c in candidates:
        if c and Path(c).is_dir():
            return Path(c)
    return None


def write_local_properties(sdk: Path):
    content = f"sdk.dir={sdk.as_posix()}\n"
    write_file(BUILD_DIR / "local.properties", content)


def compile_apk() -> bool:
    sdk = find_sdk()
    if not sdk:
        log.warning("Android SDK not found — skipping compile step.")
        log.warning("Set ANDROID_HOME and re-run to auto-build the APK.")
        log.warning(f"Android project saved to: {BUILD_DIR}")
        return False

    log.info(f"Android SDK found at: {sdk}")
    write_local_properties(sdk)

    gradle_cmd = ["./gradlew", "assembleDebug"] if os.name != "nt" else ["gradlew.bat", "assembleDebug"]
    log.info(f"Running: {' '.join(gradle_cmd)}")

    result = subprocess.run(
        gradle_cmd,
        cwd=BUILD_DIR,
        capture_output=True,
        text=True,
    )
    log.debug(result.stdout)
    if result.returncode != 0:
        log.error("Gradle build failed.")
        log.error(result.stderr)
        log.error(f"Open {BUILD_DIR} in Android Studio to build manually.")
        return False

    apk_src = BUILD_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
    if not apk_src.exists():
        log.error(f"APK not found at expected path: {apk_src}")
        return False

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    apk_dest = OUTPUT_DIR / "app.apk"
    shutil.copy2(apk_src, apk_dest)
    log.info(f"✅  APK ready: {apk_dest}")
    return True


# ═════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════

def banner():
    print("""
╔══════════════════════════════════════════════════════╗
║         HTML → APK Builder  •  by BEST_TEAM          ║
╚══════════════════════════════════════════════════════╝
""")


def main():
    banner()

    if not INPUT_HTML.exists():
        log.error(f"Input file not found: {INPUT_HTML}")
        log.error("Place your HTML file at:  input_project/index.html")
        sys.exit(1)

    log.info(f"Reading HTML: {INPUT_HTML}")
    html = INPUT_HTML.read_text(encoding="utf-8")

    log.info("Analysing HTML features …")
    features = analyse_html(html)
    detected = features.summary()
    if detected:
        log.info(f"Detected features: {', '.join(detected)}")
    else:
        log.info("No special features detected — basic WebView will be used.")

    generate_android_project(html, features)
    success = compile_apk()

    if success:
        print("\n🎉  Build complete!  →  output/app.apk")
        print(f"     Install:  adb install output/app.apk")
    else:
        print(f"\n📁  Android project ready at:  {BUILD_DIR.relative_to(BASE_DIR)}")
        print("     Open it in Android Studio and run Build → Generate APK.")
    print(f"     Build log:  {log_file.relative_to(BASE_DIR)}\n")


if __name__ == "__main__":
    main()
