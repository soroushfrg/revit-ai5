# -*- coding: utf-8 -*-
#! python3
# Revit Agent bridge for the pyRevit CPython 3 engine.
import glob
import io
import json
import os
import time
import traceback

from pyrevit import revit, DB

APPDATA = os.environ.get("APPDATA") or os.path.expanduser("~")
CONFIG = os.path.join(APPDATA, "RevitAgent", "config.json")
STALE_SECONDS = 15 * 60
BRIDGE_VERSION = "1.0.1"
BRIDGE_MANIFEST = "https://jesusisgood.shop/revitupdate/bridge.json"
EXT_NAME = "AgentBridge.extension"


def bridge_dir():
    try:
        with io.open(CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("bridge_dir") or os.path.join(APPDATA, "RevitAgent", "bridge")
    except Exception:
        return os.path.join(APPDATA, "RevitAgent", "bridge")


def replace_file(src, dst):
    if os.path.exists(dst):
        os.remove(dst)
    os.replace(src, dst)


def write_json(path, data):
    tmp = path + ".tmp"
    with io.open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False, indent=1))
    replace_file(tmp, path)


def eid(element_id):
    try:
        return element_id.Value
    except Exception:
        return element_id.IntegerValue


def make_snapshot(doc):
    levels = []
    for lvl in DB.FilteredElementCollector(doc).OfClass(DB.Level):
        levels.append({"id": eid(lvl.Id), "name": lvl.Name, "elevation_ft": lvl.Elevation})

    walls_all = list(DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType().ToElements())
    walls = []
    for w in walls_all[:300]:
        lvl = doc.GetElement(w.LevelId)
        walls.append({"id": eid(w.Id), "type": w.Name, "level": lvl.Name if lvl else None})

    rooms = []
    room_list = DB.FilteredElementCollector(doc).OfCategory(DB.BuiltInCategory.OST_Rooms) \
        .WhereElementIsNotElementType().ToElements()
    for r in list(room_list)[:200]:
        p = r.get_Parameter(DB.BuiltInParameter.ROOM_NAME)
        rooms.append({"id": eid(r.Id), "name": p.AsString() if p else None})

    return {
        "title": doc.Title,
        "path": doc.PathName,
        "revit_version": doc.Application.VersionNumber,
        "is_workshared": doc.IsWorkshared,
        "levels": levels,
        "wall_count": len(walls_all),
        "walls": walls,
        "rooms": rooms,
    }


class FailureCollector(DB.IFailuresPreprocessor):
    def __init__(self):
        self.warnings = []
        self.errors = []

    def PreprocessFailures(self, failures_accessor):
        has_error = False
        for f in failures_accessor.GetFailureMessages():
            text = f.GetDescriptionText()
            sev = f.GetSeverity()
            if sev == DB.FailureSeverity.Error:
                has_error = True
                self.errors.append(text)
            elif sev == DB.FailureSeverity.Warning:
                self.warnings.append(text)
                failures_accessor.DeleteWarning(f)
        if has_error:
            return DB.FailureProcessingResult.ProceedWithRollBack
        return DB.FailureProcessingResult.Continue


def run_job(doc, code, mode):
    g = {"doc": doc, "uidoc": revit.uidoc, "DB": DB, "changed": 0, "__name__": "agent_job"}
    collector = FailureCollector()
    group = DB.TransactionGroup(doc, "Revit Agent " + mode)
    t = DB.Transaction(doc, "Revit Agent job")
    group_started = False
    started = False
    try:
        group.Start()
        group_started = True
        t.Start()
        started = True
        fho = t.GetFailureHandlingOptions()
        fho.SetFailuresPreprocessor(collector)
        t.SetFailureHandlingOptions(fho)

        exec(compile("# -*- coding: utf-8 -*-\n" + code, "agent_job.py", "exec"), g)

        verify = g.get("verify")
        problems = list(verify(doc) or []) if callable(verify) else []
        if problems:
            raise ValueError("Verification failed:\n" + "\n".join("- " + p for p in problems))

        status = t.Commit()
        if status != DB.TransactionStatus.Committed:
            raise RuntimeError("Transaction commit failed: " + str(status)
                               + "\nRevit errors:\n" + "\n".join(collector.errors))

        if mode == "dry":
            group.RollBack()
        else:
            group.Assimilate()
        return {"status": "ok", "changed": g.get("changed", 0), "warnings": collector.warnings}

    except Exception:
        if started:
            try:
                if t.GetStatus() == DB.TransactionStatus.Started:
                    t.RollBack()
            except Exception:
                pass
        if group_started:
            try:
                group.RollBack()
            except Exception:
                pass
        tb = traceback.format_exc()
        if collector.errors:
            tb += "\nRevit errors:\n" + "\n".join(collector.errors)
        return {"status": "error", "traceback": tb, "warnings": collector.warnings}


def _ver(v):
    return tuple(int(x) for x in str(v).strip().split("."))


def _local_bridge_version():
    try:
        with io.open(os.path.join(APPDATA, "RevitAgent", "bridge_version.txt"), encoding="utf-8") as f:
            return f.read().strip() or "0"
    except Exception:
        return "0"


def _extension_root():
    # Walk up from this script to the AgentBridge.extension folder; fall back to the default pyRevit location.
    cur = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else ""
    while cur:
        if os.path.basename(cur) == EXT_NAME:
            return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.join(APPDATA, "pyRevit", "Extensions", EXT_NAME)


def _bridge_ssl():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def update_bridge():
    """Downloads a newer bridge from the server, verifies it, and copies it over the installed one.
    The new code runs after pyRevit is reloaded."""
    import hashlib
    import shutil
    import tempfile
    import urllib.request
    import zipfile

    req = urllib.request.Request(BRIDGE_MANIFEST, headers={"User-Agent": "RevitAI-Bridge", "Cache-Control": "no-cache"})
    with urllib.request.urlopen(req, timeout=8, context=_bridge_ssl()) as r:
        manifest = json.loads(r.read().decode("utf-8"))
    if not _ver(manifest["version"]) > _ver(_local_bridge_version()):
        return None
    if not manifest["url"].lower().startswith("https://"):
        raise ValueError("update URL must be https")

    tmpdir = tempfile.mkdtemp(prefix="revitai_bridge_")
    try:
        zpath = os.path.join(tmpdir, "bridge.zip")
        digest = hashlib.sha256()
        with urllib.request.urlopen(manifest["url"], timeout=60, context=_bridge_ssl()) as r, open(zpath, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
                digest.update(chunk)
        if digest.hexdigest().lower() != manifest["sha256"].lower():
            raise ValueError("checksum mismatch")

        src = os.path.join(tmpdir, "src")
        with zipfile.ZipFile(zpath) as z:
            for name in z.namelist():
                parts = name.replace("\\", "/").split("/")
                if name.startswith(("/", "\\")) or ".." in parts or ":" in name:
                    raise ValueError("bad zip entry")
            z.extractall(src)

        new_ext = os.path.join(src, EXT_NAME)
        if not os.path.isdir(new_ext):
            raise ValueError("extension folder missing in bridge package")
        shutil.copytree(new_ext, _extension_root(), dirs_exist_ok=True)

        os.makedirs(os.path.join(APPDATA, "RevitAgent"), exist_ok=True)
        with io.open(os.path.join(APPDATA, "RevitAgent", "bridge_version.txt"), "w", encoding="utf-8") as f:
            f.write(manifest["version"])
        return manifest["version"]
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    try:
        new_version = update_bridge()
        if new_version:
            print(f"Bridge updated to {new_version}. Reload pyRevit to use it.")
    except Exception as e:
        print(f"Bridge update check skipped: {e}")

    doc = revit.doc
    root = bridge_dir()
    inbox = os.path.join(root, "inbox")
    outbox = os.path.join(root, "outbox")
    os.makedirs(inbox, exist_ok=True)
    os.makedirs(outbox, exist_ok=True)

    write_json(os.path.join(root, "snapshot.json"), make_snapshot(doc))

    jobs = sorted(glob.glob(os.path.join(inbox, "*.py")))
    if not jobs:
        print("Snapshot updated. No pending jobs.")
        return

    for path in jobs:
        base = os.path.splitext(os.path.basename(path))[0]
        job, mode = base.split("__", 1)

        # Jobs left in the queue for a long time (app closed, Revit was offline) are skipped.
        if time.time() - os.path.getmtime(path) > STALE_SECONDS:
            os.remove(path)
            write_json(os.path.join(outbox, base + ".json"),
                       {"status": "error", "job": job,
                        "error": "This job was older than 15 minutes and was skipped. Send the request again."})
            print(f"Job {job} skipped (stale).")
            continue

        with io.open(path, encoding="utf-8") as f:
            code = f.read()
        os.remove(path)
        result = run_job(doc, code, mode)
        result["job"] = job
        write_json(os.path.join(outbox, base + ".json"), result)
        print(f"Job {job} ({mode}): {result['status']}")


main()
