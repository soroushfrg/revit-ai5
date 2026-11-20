import subprocess
import sys

import bootstrap
from version import APP_VERSION

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000000


def check_update(url=None):
    manifest = bootstrap.fetch_manifest()
    if bootstrap.is_newer(manifest["version"], APP_VERSION):
        return manifest
    return None


def download(manifest, progress=None):
    return bootstrap.stage_update(manifest, progress)


def apply_and_restart(_staged=None):
    """Start the launcher again; it applies the staged code and opens the new version."""
    if not getattr(sys, "frozen", False):
        raise RuntimeError("نسخه‌ی جدید آماده شد. برای اعمال، برنامه را از Launcher دوباره اجرا کنید.")
    subprocess.Popen([sys.executable], creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW)
