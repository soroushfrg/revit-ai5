import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app")
OUT_DIR = os.path.join(ROOT, "release")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "app.zip")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for base, dirs, files in os.walk(APP):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if fn.endswith(".pyc") or fn in ("requirements.txt", "config.json"):
                continue
            full = os.path.join(base, fn)
            z.write(full, os.path.relpath(full, APP).replace(os.sep, "/"))
print(out)
