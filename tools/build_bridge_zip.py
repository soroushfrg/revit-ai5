import os
import re
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT = os.path.join(ROOT, "revit_bridge", "AgentBridge.extension")
SCRIPT = os.path.join(EXT, "AgentBridge.tab", "Agent.panel", "RunBridge.pushbutton", "script.py")

with open(SCRIPT, encoding="utf-8") as f:
    version = re.search(r'BRIDGE_VERSION = "([\d.]+)"', f.read()).group(1)

OUT_DIR = os.path.join(ROOT, "release")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "bridge.zip")

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("BRIDGE_VERSION", version)
    for base, dirs, files in os.walk(EXT):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if fn.endswith(".pyc"):
                continue
            full = os.path.join(base, fn)
            z.write(full, os.path.relpath(full, os.path.dirname(EXT)).replace(os.sep, "/"))
print(out, version)
