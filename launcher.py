import ctypes
import importlib
import os
import sys
import traceback

if not getattr(sys, "frozen", False):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "app"))

import bootstrap  # noqa: E402


def _bundle_runtime_deps():
    # Never called. Makes PyInstaller bundle every library the downloaded app code imports,
    # so the frozen launcher can run that code even when it is not in the exe itself.
    import base64  # noqa: F401
    import certifi  # noqa: F401
    import copy  # noqa: F401
    import datetime  # noqa: F401
    import hashlib  # noqa: F401
    import io  # noqa: F401
    import html  # noqa: F401
    import json  # noqa: F401
    import mimetypes  # noqa: F401
    import re  # noqa: F401
    import shutil  # noqa: F401
    import ssl  # noqa: F401
    import subprocess  # noqa: F401
    import tempfile  # noqa: F401
    import threading  # noqa: F401
    import time  # noqa: F401
    import traceback  # noqa: F401
    import urllib.request  # noqa: F401
    import uuid  # noqa: F401
    import wave  # noqa: F401
    import zipfile  # noqa: F401
    import numpy  # noqa: F401
    import pypdf  # noqa: F401
    import requests  # noqa: F401
    import sounddevice  # noqa: F401
    import PySide6.QtCore  # noqa: F401
    import PySide6.QtGui  # noqa: F401
    import PySide6.QtWidgets  # noqa: F401


def message(text):
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(0, text, "Revit AI", 0x10)
    else:
        print(text)


def main():
    try:
        if bootstrap.self_update():
            return  # a newer RevitAI.exe was published and has been started
    except Exception:
        pass  # launcher self-update is best effort; the app still starts

    try:
        status = bootstrap.sync()
    except Exception as e:
        status = str(e)

    if not os.path.isfile(os.path.join(bootstrap.APP_DIR, "main.py")):
        message("برای اولین اجرا به اینترنت نیاز است. اتصال را بررسی کنید و دوباره اجرا کنید.\n\n" + status)
        return

    sys.path.insert(0, bootstrap.APP_DIR)
    try:
        app_main = importlib.import_module("main")
    except Exception:
        err = traceback.format_exc()
        try:
            with open(os.path.join(bootstrap.LOCAL_ROOT, "launch_error.log"), "w", encoding="utf-8") as f:
                f.write(err)
        except Exception:
            pass
        bootstrap.rollback()
        message("خطا در شروع نسخه‌ی جدید. به نسخه‌ی قبلی برگشتیم. دوباره اجرا کنید.\n\n" + err[-800:])
        return
    app_main.main()


if __name__ == "__main__":
    main()
