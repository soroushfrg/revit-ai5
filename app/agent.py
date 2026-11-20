import datetime
import json
import os
import re
import shutil
import time
import uuid

from llm_client import chat

SYSTEM_PROMPT = """You are an expert Revit automation agent. You write Python for the Autodesk Revit API (Autodesk.Revit.DB), executed by a pyRevit CPython bridge inside Revit.

Each turn, reply in ONE of two ways:
1. CLARIFY: if the request is ambiguous or required information is missing (which room, which walls, which level, which reference plane, which wall type, base or top constraint, scope), reply with ONE short question in the user's language and NO code block. Never guess large or destructive changes. Do not ask unnecessary questions.
2. CODE: reply with exactly one ```python code block, then a short summary in the user's language.

Code contract:
- Globals provided: doc, uidoc, DB, changed (int). Increment changed for every element you modify or create.
- The code runs in Python 3 (CPython) inside Revit through the pyRevit engine. Use Python 3 syntax and the standard library. Use the provided DB global for Revit API types.
- The code runs inside a Revit transaction. Do not open, save, close or switch documents, and do not create transactions.
- Revit internal units are feet. Convert explicitly.
- Check None for every element lookup and parameter read.
- Use only Revit API members that exist in the Revit version given in the snapshot.
- Make only the changes the user asked for. Never delete elements unless explicitly asked.
- Define a function verify(doc) that returns a list of strings describing problems (empty list if everything is correct). Check the real result: for example, each target wall is actually joined or attached to the intended level or ceiling, heights are in a sensible range, and no unrelated elements changed. The bridge runs verify before committing; if it returns problems, nothing is committed and you receive them.
- If a previous attempt failed, read the error carefully and change the approach, do not repeat the same code.
"""

CODE_RE = re.compile(r"```(?:python)?[ \t]*\n(.*?)```", re.S)


def parse_reply(text):
    m = CODE_RE.search(text)
    if not m:
        return None, text.strip()
    code = m.group(1).strip()
    summary = CODE_RE.sub("", text).strip()
    return code, summary


class Bridge:
    """File-based queue shared with the pyRevit bridge button inside Revit."""

    def __init__(self, root):
        self.root = root
        self.inbox = os.path.join(root, "inbox")
        self.outbox = os.path.join(root, "outbox")
        os.makedirs(self.inbox, exist_ok=True)
        os.makedirs(self.outbox, exist_ok=True)

    def read_snapshot(self):
        p = os.path.join(self.root, "snapshot.json")
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    def submit(self, code, job, mode, timeout):
        """mode is 'dry' (run, collect warnings, always roll back) or 'commit' (run and keep)."""
        name = f"{job}__{mode}"
        path = os.path.join(self.inbox, name + ".py")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(code)
        os.replace(path + ".tmp", path)

        result_path = os.path.join(self.outbox, name + ".json")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if os.path.exists(result_path):
                time.sleep(0.2)
                with open(result_path, encoding="utf-8") as f:
                    data = json.load(f)
                os.remove(result_path)
                return data
            time.sleep(1)

        if os.path.exists(path):
            os.remove(path)
        return {"status": "timeout", "error": "Revit did not process the job. Click 'Run Bridge' in Revit and try again."}


def backup_project(snapshot, cfg, job, code):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = os.path.join(cfg["backup_dir"], f"{stamp}_{job}")
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "job.py"), "w", encoding="utf-8") as f:
        f.write(code)
    path = (snapshot or {}).get("path") or ""
    if path and os.path.exists(path):
        shutil.copy2(path, folder)
        return folder, "model file copied"
    return folder, "model path unknown, only code saved"


def format_report(dry):
    lines = [f"پیش‌نمایش موفق. عناصر تغییریافته: {dry.get('changed', 0)}"]
    if dry.get("warnings"):
        lines.append("هشدارهای Revit:")
        lines += [f"- {w}" for w in dry["warnings"]]
    return "\n".join(lines)


def error_text(res):
    return res.get("traceback") or res.get("error") or "unknown error"


class RevitAgent:
    MAX_QUESTIONS = 8

    def __init__(self, cfg, log, ask_approval, ask_user):
        self.cfg = cfg
        self.log = log
        self.ask_approval = ask_approval
        self.ask_user = ask_user
        self.bridge = Bridge(cfg["bridge_dir"])

    def run(self, request):
        if not self.cfg.get("session_token") or not self.cfg["model_name"].strip():
            self.log("⚠ ابتدا وارد حساب شوید و مدل را انتخاب کنید.")
            return False

        snapshot = self.bridge.read_snapshot()
        if snapshot:
            snap_text = json.dumps(snapshot, ensure_ascii=False, indent=1)[:15000]
        else:
            snap_text = "NO SNAPSHOT. Ask the user to click 'Run Bridge' in Revit first."

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nCurrent Revit snapshot:\n" + snap_text},
            {"role": "user", "content": request},
        ]

        attempts = 0
        questions = 0
        max_attempts = int(self.cfg["max_retries"])

        while attempts < max_attempts:
            reply = chat(self.cfg, messages)
            messages.append({"role": "assistant", "content": reply})
            code, summary = parse_reply(reply)

            if not code:
                questions += 1
                if questions > self.MAX_QUESTIONS:
                    self.log("⚠ تعداد سؤال‌ها زیاد شد. لطفاً درخواست را دقیق‌تر بنویسید.")
                    return False
                answer = self.ask_user(summary)
                if not answer:
                    self.log("✖ پاسخی داده نشد.")
                    return False
                messages.append({"role": "user", "content": answer})
                continue

            attempts += 1
            self.log(f"— تلاش {attempts} با مدل {self.cfg['model_name']}")
            if summary:
                self.log(summary)

            job = uuid.uuid4().hex[:12]

            dry = self.bridge.submit(code, job, "dry", int(self.cfg["job_timeout_sec"]))
            if dry.get("status") != "ok":
                err = error_text(dry)
                self.log("✖ خطا در پیش‌نمایش (تغییری اعمال نشد):\n" + err)
                snapshot = self.bridge.read_snapshot() or snapshot
                messages.append(self._fail_msg(err))
                continue

            report = format_report(dry)
            self.log(report)

            if self.cfg["require_approval"] and not self.ask_approval(code, (summary + "\n\n" + report).strip()):
                self.log("✖ اجرا توسط شما لغو شد.")
                return False

            folder, note = backup_project(snapshot, self.cfg, job, code)
            self.log(f"بکاپ ساخته شد: {folder} ({note})")

            res = self.bridge.submit(code, job, "commit", int(self.cfg["job_timeout_sec"]))
            if res.get("status") == "ok":
                self.log(f"✔ اجرا موفق. عناصر تغییریافته: {res.get('changed', 0)}")
                return True

            err = error_text(res)
            self.log("✖ خطا در اجرای نهایی (تغییری ذخیره نشد):\n" + err)
            snapshot = self.bridge.read_snapshot() or snapshot
            messages.append(self._fail_msg(err))

        self.log("⚠ به حداکثر تعداد تلاش رسیدیم. لطفاً بررسی کنید.")
        return False

    @staticmethod
    def _fail_msg(err):
        return {
            "role": "user",
            "content": "Revit execution failed and nothing was changed.\nError:\n" + err
                       + "\nFix the approach and reply with a corrected ```python block, "
                         "or ask one question if the cause is missing information.",
        }
