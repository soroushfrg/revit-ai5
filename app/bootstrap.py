"""Update logic shared by the launcher and the app's update button.
The launcher bundles this file, so keep it small and stable."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

MANIFEST_URL = "https://jesusisgood.shop/revitupdate/app.json"
LOCAL_ROOT = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "RevitAI")
APP_DIR = os.path.join(LOCAL_ROOT, "app")
PREV_DIR = os.path.join(LOCAL_ROOT, "app_prev")
STAGED_DIR = os.path.join(LOCAL_ROOT, "app_staged")
BAD_FILE = os.path.join(LOCAL_ROOT, "bad_version.txt")
DOWNLOAD_ZIP = os.path.join(LOCAL_ROOT, "app_download.zip")
VERSION_URL = MANIFEST_URL.rsplit("/", 1)[0] + "/version.json"  # launcher (exe) manifest, published from the admin page
LAUNCHER_STATE = os.path.join(LOCAL_ROOT, "launcher_state.json")
LAUNCHER_NEW = os.path.join(LOCAL_ROOT, "RevitAI_new.exe")
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def _ssl_context():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _open(url, timeout):
    if not url.lower().startswith("https://"):
        raise ValueError("فقط آدرس https مجازه")
    req = urllib.request.Request(url, headers={"User-Agent": "RevitAI-Launcher", "Cache-Control": "no-cache"})
    return urllib.request.urlopen(req, timeout=timeout, context=_ssl_context())


def fetch_manifest():
    with _open(MANIFEST_URL, 15) as r:
        return json.loads(r.read().decode("utf-8"))


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def installed_version():
    return _read_json(os.path.join(APP_DIR, "installed.json")).get("version", "0")


def _parse(v):
    return tuple(int(x) for x in str(v).strip().lstrip("v").split("."))


def is_newer(remote, local):
    return _parse(remote) > _parse(local)


def stage_update(manifest, progress=None):
    """Download and verify app.zip into the staging folder. The running app is never touched here."""
    os.makedirs(LOCAL_ROOT, exist_ok=True)
    part = DOWNLOAD_ZIP + ".part"
    digest = hashlib.sha256()
    with _open(manifest["url"], 120) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            digest.update(chunk)
            done += len(chunk)
            if progress and total:
                progress(int(done * 100 / total))
    if digest.hexdigest().lower() != manifest["sha256"].lower():
        os.remove(part)
        raise ValueError("checksum فایل نادرست است")
    os.replace(part, DOWNLOAD_ZIP)

    shutil.rmtree(STAGED_DIR, ignore_errors=True)
    with zipfile.ZipFile(DOWNLOAD_ZIP) as z:
        for name in z.namelist():
            parts = name.replace("\\", "/").split("/")
            if name.startswith(("/", "\\")) or ".." in parts or ":" in name:
                raise ValueError("zip نامعتبر است")
        z.extractall(STAGED_DIR)
    if not os.path.isfile(os.path.join(STAGED_DIR, "main.py")):
        shutil.rmtree(STAGED_DIR, ignore_errors=True)
        raise ValueError("main.py داخل بسته پیدا نشد")
    with open(os.path.join(STAGED_DIR, "installed.json"), "w", encoding="utf-8") as f:
        json.dump({"version": manifest["version"], "sha256": manifest["sha256"]}, f)
    if progress:
        progress(100)
    return STAGED_DIR


def apply_staged():
    """Swap the staged code in. Only called when the app is not running from APP_DIR."""
    if not os.path.isdir(STAGED_DIR):
        return False
    last = None
    for _ in range(20):
        try:
            shutil.rmtree(PREV_DIR, ignore_errors=True)
            if os.path.isdir(APP_DIR):
                os.rename(APP_DIR, PREV_DIR)
            try:
                os.rename(STAGED_DIR, APP_DIR)
            except OSError:
                if os.path.isdir(PREV_DIR) and not os.path.isdir(APP_DIR):
                    os.rename(PREV_DIR, APP_DIR)
                raise
            return True
        except OSError as e:
            last = e
            time.sleep(0.5)
    raise last


def rollback():
    """Go back to the previous code after the new code failed to start."""
    broken = installed_version()
    if os.path.isdir(PREV_DIR):
        if broken != "0":
            with open(BAD_FILE, "w", encoding="utf-8") as f:
                f.write(broken)
        shutil.rmtree(APP_DIR, ignore_errors=True)
        os.rename(PREV_DIR, APP_DIR)


def sync():
    """Called by the launcher before the app starts. Never raises."""
    try:
        apply_staged()
    except Exception:
        pass
    try:
        manifest = fetch_manifest()
    except Exception as e:
        return f"offline: {e}"
    try:
        with open(BAD_FILE, encoding="utf-8") as f:
            bad = f.read().strip()
    except Exception:
        bad = ""
    if manifest["version"] == bad:
        return "skipped bad version"
    if not os.path.isdir(APP_DIR) or is_newer(manifest["version"], installed_version()):
        try:
            stage_update(manifest)
            apply_staged()
        except Exception as e:
            return f"update failed: {e}"
    return "ok"


def _file_sha(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def _write_json(path, data):
    os.makedirs(LOCAL_ROOT, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def _remove(path):
    try:
        os.remove(path)
    except OSError:
        pass


def self_update():
    """Replace the running RevitAI.exe with the one published on the host (version.json).
    Returns True when a new exe was started and this process should exit."""
    if not getattr(sys, "frozen", False):
        return False
    exe = sys.executable
    _remove(exe + ".old")  # left over from the previous replacement; fails silently while running
    remote = _read_json_url(VERSION_URL)
    rsha = str(remote.get("sha256") or "").lower()
    url = remote.get("url") or ""
    if not rsha or not url.lower().startswith("https://"):
        return False
    state = _read_json(LAUNCHER_STATE)
    current = str(state.get("sha256") or "").lower()
    if not current:
        current = _file_sha(exe)
        _write_json(LAUNCHER_STATE, {"sha256": current})
    if current == rsha:
        return False

    part = LAUNCHER_NEW + ".part"
    digest = hashlib.sha256()
    with _open(url, 120) as r, open(part, "wb") as f:
        for chunk in iter(lambda: r.read(65536), b""):
            f.write(chunk)
            digest.update(chunk)
    if digest.hexdigest().lower() != rsha:
        _remove(part)
        raise ValueError("checksum فایل لانچر نادرست است")
    os.replace(part, LAUNCHER_NEW)

    old = exe + ".old"
    os.rename(exe, old)  # a running exe can be renamed on Windows, not overwritten
    try:
        shutil.copy2(LAUNCHER_NEW, exe)
    except Exception:
        os.replace(old, exe)
        raise
    _write_json(LAUNCHER_STATE, {"sha256": rsha, "version": remote.get("version", "")})
    subprocess.Popen([exe], creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW, close_fds=True)
    return True


def _read_json_url(url):
    try:
        with _open(url, 15) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return {}
