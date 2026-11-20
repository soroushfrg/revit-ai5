import copy
import html
import os

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QComboBox, QCheckBox, QDialog, QFileDialog, QFrame, QGraphicsDropShadowEffect,
    QHBoxLayout, QInputDialog, QLabel, QMainWindow, QPushButton, QSizePolicy, QStatusBar,
    QTextEdit, QVBoxLayout, QWidget,
)

from config import save_config
from media import build_user_content, load_attachment
from speech import Recorder
from ui.approval_dialog import ApprovalDialog
from ui.settings_dialog import SettingsDialog
from PySide6.QtWidgets import QMessageBox, QProgressDialog
from PySide6.QtWidgets import QApplication as _QApp
from updater import apply_and_restart
from version import APP_VERSION
from ui.update_worker import DownloadWorker, UpdateCheckWorker
from llm_client import apply_me
from ui.probe_worker import ProbeWorker
from ui.support_dialog import SUPPORT_URL, SupportDialog
from ui.worker import AgentWorker, ChatWorker, TranscribeWorker

MAX_HISTORY = 20
SIDEBAR_W = 230
FILE_FILTER = "فایل‌ها (*.png *.jpg *.jpeg *.webp *.gif *.pdf *.txt *.md *.csv *.json *.py *.log *.xml *.html);;همه فایل‌ها (*)"

COLORS = {"user": "#9fd8f5", "assistant": "#dfe1e5", "error": "#ff8a80", "ok": "#8be28b", "sys": "#8a8f98"}


def add_shadow(widget, blur=30, y=8, alpha=120):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(blur)
    effect.setOffset(0, y)
    effect.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(effect)


def classify(text):
    t = text.lstrip()
    if t.startswith("🧑"):
        return "user"
    if t.startswith("🤖"):
        return "assistant"
    if t.startswith(("✖", "⚠")):
        return "error"
    if t.startswith("✔"):
        return "ok"
    return "sys"


class MainWindow(QMainWindow):
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.worker = None
        self.recorder = Recorder()
        self.recording = False
        self.attachments = []
        self.chat_history = []
        self.pending_user_content = None
        self._dots = 0

        self.setWindowTitle(f"Revit AI v{APP_VERSION}")
        self._fit_to_screen()

        self._busy_timer = QTimer(self)
        self._busy_timer.timeout.connect(self._tick_dots)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QHBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.sidebar = self._build_sidebar()
        outer.addWidget(self.sidebar)

        main = QWidget()
        mlay = QVBoxLayout(main)
        mlay.setContentsMargins(20, 12, 20, 14)
        mlay.setSpacing(12)
        mlay.addWidget(self._build_header())
        mlay.addWidget(self._build_log_card(), 1)
        mlay.addWidget(self._build_input_card())
        outer.addWidget(main, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("آماده")
        footer = QLabel(f'<a href="{SUPPORT_URL}" style="color:#9fd8f5;text-decoration:none;">© Revit AI · @soroushfrg</a>')
        footer.setOpenExternalLinks(True)
        self.status.addPermanentWidget(footer)

        self.refresh_top()

    # ---------- layout ----------
    def _fit_to_screen(self):
        avail = QApplication.primaryScreen().availableGeometry()
        w = min(1200, int(avail.width() * 0.85))
        h = min(800, int(avail.height() * 0.85))
        self.setMinimumSize(min(900, avail.width()), min(600, avail.height()))
        self.resize(w, h)
        self.move(avail.center().x() - w // 2, avail.center().y() - h // 2)

    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setMinimumWidth(0)
        side.setMaximumWidth(SIDEBAR_W)
        side.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        lay = QVBoxLayout(side)
        lay.setContentsMargins(14, 16, 14, 16)
        lay.setSpacing(6)

        brand = QLabel(f"Revit AI  v{APP_VERSION}")
        brand.setObjectName("brand")
        lay.addWidget(brand)

        self.new_chat_btn = QPushButton("＋  چت جدید")
        self.new_chat_btn.setObjectName("nav")
        self.new_chat_btn.clicked.connect(self.new_chat)
        lay.addWidget(self.new_chat_btn)

        section = QLabel("حالت کار")
        section.setObjectName("muted")
        lay.addSpacing(12)
        lay.addWidget(section)

        self.mode_revit = QPushButton("🛠  Revit")
        self.mode_chat = QPushButton("💬  چت عمومی")
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        for b in (self.mode_revit, self.mode_chat):
            b.setObjectName("nav")
            b.setCheckable(True)
            self.mode_group.addButton(b)
            lay.addWidget(b)
        self.mode_revit.setChecked(True)

        lay.addSpacing(12)
        self.approval_chk = QCheckBox("تأیید قبل از اجرا")
        self.approval_chk.toggled.connect(self.on_approval_toggled)
        lay.addWidget(self.approval_chk)

        lay.addStretch()
        self.user_label = QLabel()
        self.user_label.setObjectName("muted")
        lay.addWidget(self.user_label)

        self.update_btn = QPushButton("⟳  بررسی بروزرسانی")
        self.update_btn.setObjectName("nav")
        self.update_btn.clicked.connect(lambda: self.check_updates(manual=True))
        lay.addWidget(self.update_btn)
        self.support_btn = QPushButton("✉  پیام به پشتیبانی")
        self.support_btn.setObjectName("nav")
        self.support_btn.clicked.connect(self.open_support)
        lay.addWidget(self.support_btn)
        self.settings_btn = QPushButton("⚙  تنظیمات")
        self.settings_btn.setObjectName("nav")
        self.settings_btn.clicked.connect(self.open_settings)
        lay.addWidget(self.settings_btn)
        return side

    def _build_header(self):
        bar = QFrame()
        bar.setObjectName("header")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 0, 0)

        self.menu_btn = QPushButton("☰")
        self.menu_btn.setObjectName("icon")
        self.menu_btn.setToolTip("نمایش / مخفی کردن منو")
        self.menu_btn.clicked.connect(self.toggle_sidebar)

        self.greet = QLabel()
        self.greet.setObjectName("title")
        self.conn_label = QLabel("● در حال اتصال")
        self.conn_label.setStyleSheet("color:#8a8f98;font-weight:600;")
        self.usage_label = QLabel("")
        self.usage_label.setObjectName("muted")
        self.revit_label = QLabel("")
        self.revit_label.setObjectName("muted")
        self.model_label = QComboBox()
        self.model_label.setMinimumWidth(200)
        self.model_label.setToolTip("مدل هوش مصنوعی")
        self.model_label.setObjectName("chip")

        lay.addWidget(self.menu_btn)
        lay.addSpacing(8)
        lay.addWidget(self.greet)
        lay.addStretch()
        lay.addWidget(self.conn_label)
        lay.addWidget(self.revit_label)
        lay.addWidget(self.usage_label)
        lay.addWidget(self.model_label)
        return bar

    def _build_log_card(self):
        card = QFrame()
        card.setObjectName("card")
        add_shadow(card)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(4, 4, 4, 4)
        self.log = QTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        lay.addWidget(self.log)
        return card

    def _build_input_card(self):
        card = QFrame()
        card.setObjectName("card")
        add_shadow(card, blur=24, y=6, alpha=90)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(4)

        att = QHBoxLayout()
        self.attach_label = QLabel("")
        self.attach_label.setObjectName("attach")
        self.clear_att_btn = QPushButton("✖")
        self.clear_att_btn.setObjectName("icon")
        self.clear_att_btn.setToolTip("حذف پیوست‌ها")
        self.clear_att_btn.clicked.connect(self.clear_attachments)
        att.addWidget(self.attach_label, 1)
        att.addWidget(self.clear_att_btn)
        lay.addLayout(att)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setObjectName("round")
        self.attach_btn.setToolTip("افزودن فایل یا عکس")
        self.attach_btn.clicked.connect(self.pick_files)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("round")
        self.mic_btn.setToolTip("ضبط صدا")
        self.mic_btn.clicked.connect(self.toggle_recording)

        self.input = QTextEdit()
        self.input.setObjectName("input")
        self.input.setPlaceholderText("درخواستتون رو بنویسید یا با صدا بگید (فارسی یا English)...")
        self.input.setMinimumHeight(56)
        self.input.setMaximumHeight(120)

        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("primary")
        self.send_btn.setToolTip("ارسال")
        self.send_btn.clicked.connect(self.send)

        row.addWidget(self.attach_btn)
        row.addWidget(self.input, 1)
        row.addWidget(self.mic_btn)
        row.addWidget(self.send_btn)
        lay.addLayout(row)
        return card

    # ---------- sidebar animation ----------
    def toggle_sidebar(self):
        opening = self.sidebar.maximumWidth() == 0
        self._anim = QPropertyAnimation(self.sidebar, b"maximumWidth", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setStartValue(self.sidebar.maximumWidth())
        self._anim.setEndValue(SIDEBAR_W if opening else 0)
        self._anim.start()

    # ---------- state ----------
    def refresh_top(self):
        name = self.cfg.get("user_name") or ""
        self.greet.setText(f"سلام {name} 👋" if name else "Revit Agent")
        self.model_label.blockSignals(True)
        self.model_label.clear()
        models = self.cfg.get("models") or []
        self.model_label.addItems(models)
        if self.cfg.get("model_name") in models:
            self.model_label.setCurrentText(self.cfg["model_name"])
        self.model_label.blockSignals(False)
        if not getattr(self, "_model_connected", False):
            self.model_label.currentTextChanged.connect(self.on_model_changed)
            self._model_connected = True
        self.user_label.setText(self.cfg.get("username", ""))
        forced = self.cfg.get("forced_model") or ""
        self.model_label.setEnabled(not forced)
        self.model_label.setToolTip("مدل توسط مدیر تعیین شده" if forced else "مدل هوش مصنوعی")
        self.usage_label.setText(self._usage_text())
        self.revit_label.setText(self._revit_text())
        if not getattr(self, "_timer_started", False):
            self._timer_started = True
            self.probe_timer = QTimer(self)
            self.probe_timer.timeout.connect(self.start_probe)
            self.probe_timer.start(60000)
            QTimer.singleShot(300, self.start_probe)
        self.user_label.setText(name or "")
        self.approval_chk.blockSignals(True)
        self.approval_chk.setChecked(bool(self.cfg["require_approval"]))
        self.approval_chk.blockSignals(False)

    def append(self, text):
        kind = classify(text)
        safe = html.escape(text).replace("\n", "<br>")
        self.log.append(f'<div style="color:{COLORS[kind]}; margin:6px 0;">{safe}</div>')

    def busy(self):
        return self.worker is not None

    def open_settings(self):
        dlg = SettingsDialog(self.cfg, self)
        if dlg.exec() == QDialog.Accepted:
            self.cfg = dlg.cfg
            self.refresh_top()
            self.append("✔ تنظیمات ذخیره شد.")

    def on_approval_toggled(self, checked):
        self.cfg["require_approval"] = checked
        save_config(self.cfg)

    def new_chat(self):
        self.chat_history = []
        self.log.clear()
        self.append("— چت جدید شروع شد —")

    def _set_busy_status(self, on):
        if on:
            self._busy_timer.start(450)
        else:
            self._busy_timer.stop()
            self.status.showMessage("آماده")

    def _tick_dots(self):
        self._dots = (self._dots + 1) % 4
        self.status.showMessage("در حال کار" + "." * self._dots)

    # ---------- attachments ----------
    def pick_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "انتخاب فایل یا عکس", "", FILE_FILTER)
        for p in paths:
            try:
                self.attachments.append(load_attachment(p))
            except Exception as e:
                self.append(f"✖ {os.path.basename(p)}: {e}")
        self.refresh_attachments()

    def clear_attachments(self):
        self.attachments = []
        self.refresh_attachments()

    def refresh_attachments(self):
        names = [a["name"] for a in self.attachments]
        self.attach_label.setText("📎 " + "،  ".join(names) if names else "")

    # ---------- voice ----------
    def _set_recording_style(self, on):
        self.mic_btn.setProperty("recording", "true" if on else "false")
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)

    def toggle_recording(self):
        if not self.recording:
            if self.busy():
                return
            try:
                self.recorder.start()
            except Exception as e:
                self.append(f"✖ میکروفون در دسترس نیست: {e}")
                return
            self.recording = True
            self._set_recording_style(True)
            self.mic_btn.setText("⏹")
            self.status.showMessage("در حال ضبط...")
        else:
            path = self.recorder.stop()
            self.recording = False
            self._set_recording_style(False)
            self.mic_btn.setText("🎤")
            self.status.showMessage("در حال تبدیل صوت به متن...")
            self.mic_btn.setEnabled(False)
            self.tw = TranscribeWorker(copy.deepcopy(self.cfg), path)
            self.tw.text_ready.connect(self.on_transcribed)
            self.tw.error.connect(self.on_transcribe_error)
            self.tw.start()

    def on_transcribed(self, text):
        self.mic_btn.setEnabled(True)
        self.status.showMessage("آماده")
        if text:
            current = self.input.toPlainText().strip()
            self.input.setPlainText((current + " " + text).strip())

    def on_transcribe_error(self, msg):
        self.mic_btn.setEnabled(True)
        self.status.showMessage("آماده")
        self.append(msg)

    # ---------- sending ----------
    def send(self):
        text = self.input.toPlainText().strip()
        if (not text and not self.attachments) or self.busy() or self.recording:
            return
        if not self.cfg.get("session_token") or not self.cfg["model_name"]:
            self.append("⚠ ابتدا وارد حساب شوید و مدل را انتخاب کنید.")
            return

        names = [a["name"] for a in self.attachments]
        shown = text + (f"\n📎 {', '.join(names)}" if names else "")
        self.append(f"🧑 {shown}")
        content = build_user_content(text, self.attachments)
        self.input.clear()
        self.attachments = []
        self.refresh_attachments()

        self.send_btn.setEnabled(False)
        self._set_busy_status(True)

        if self.mode_chat.isChecked():
            self.pending_user_content = content
            self.worker = ChatWorker(copy.deepcopy(self.cfg), self.chat_history, content)
            self.worker.reply_ready.connect(self.on_chat_reply)
            self.worker.error.connect(self.append)
            self.worker.finished_ok.connect(self.on_finished)
        else:
            self.worker = AgentWorker(copy.deepcopy(self.cfg), content)
            self.worker.log_signal.connect(self.append)
            self.worker.approval_request.connect(self.on_approval_request)
            self.worker.question_request.connect(self.on_question_request)
            self.worker.finished_ok.connect(self.on_finished)
        self.worker.start()

    def on_chat_reply(self, reply):
        self.append(f"🤖 {reply}")
        self.chat_history.append({"role": "user", "content": self.pending_user_content})
        self.chat_history.append({"role": "assistant", "content": reply})
        self.chat_history = self.chat_history[-MAX_HISTORY:]

    def on_approval_request(self, code, summary):
        dlg = ApprovalDialog(code, summary, self)
        ok = dlg.exec() == QDialog.Accepted
        if self.worker:
            self.worker.answer(ok)

    def on_question_request(self, question):
        self.append(f"🤖 {question}")
        text, ok = QInputDialog.getMultiLineText(self, "سوال از هوش مصنوعی", question)
        if self.worker:
            self.worker.answer(text.strip() if ok else "")

    def on_finished(self, ok):
        if self.worker:
            self.worker.wait()
            self.worker.deleteLater()
            self.worker = None
        self.send_btn.setEnabled(True)
        self._set_busy_status(False)
        self.status.showMessage("کار تمام شد" if ok else "کار با خطا یا توقف تمام شد", 5000)
        self.start_probe()

    # ---------- updates ----------
    def check_updates(self, manual=False):
        url = (self.cfg.get("update_url") or "").strip()
        if not url:
            if manual:
                self.append("⚠ آدرس بروزرسانی در تنظیمات وارد نشده است.")
            return
        self.update_check = UpdateCheckWorker(url)
        self.update_check.found.connect(self.on_update_found)
        self.update_check.failed.connect(self.append)
        if manual:
            self.update_check.up_to_date.connect(lambda: self.append(f"✔ نسخه‌ی شما ({APP_VERSION}) به‌روزه."))
        self.update_check.start()

    def on_update_found(self, manifest):
        notes = manifest.get("notes") or ""
        text = f"نسخه‌ی جدید {manifest['version']} موجوده (نسخه‌ی فعلی: {APP_VERSION})."
        if notes:
            text += f"\n\n{notes}"
        text += "\n\nدانلود و نصب الان؟"
        if QMessageBox.question(self, "بروزرسانی", text) != QMessageBox.Yes:
            return
        self.update_manifest = manifest
        self.progress = QProgressDialog("در حال دانلود بروزرسانی...", None, 0, 100, self)
        self.progress.setWindowTitle("بروزرسانی")
        self.progress.setMinimumDuration(0)
        self.progress.setValue(0)
        self.download_worker = DownloadWorker(manifest)
        self.download_worker.progress.connect(self.progress.setValue)
        self.download_worker.done.connect(self.on_download_done)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()

    def on_download_error(self, msg):
        if hasattr(self, "progress"):
            self.progress.close()
        self.append(msg)

    def on_download_done(self, path):
        self.progress.close()
        try:
            apply_and_restart(path)
        except RuntimeError:
            self.append(f"✔ فایل بروزرسانی در {path} ذخیره شد (فقط در نسخه‌ی exe خودکار نصب می‌شه).")
            return
        _QApp.quit()

    def on_model_changed(self, name):
        if name:
            self.cfg["model_name"] = name
            save_config(self.cfg)

    # ---------- status ----------
    def _usage_text(self):
        used = self.cfg.get("used") or 0
        limit = self.cfg.get("limit") or 0
        remaining = self.cfg.get("remaining") or 0
        cost = self.cfg.get("window_cost") or 0
        return f"مصرف بازه: {used:,} / {limit:,} توکن   |   هزینه بازه: ${cost:.4f}   |   باقی‌مانده: {remaining:,}"

    def _revit_text(self):
        import os
        import time
        snap = os.path.join(self.cfg["bridge_dir"], "snapshot.json")
        if not os.path.exists(snap):
            return "Revit: هنوز همگام نشده"
        minutes = int((time.time() - os.path.getmtime(snap)) // 60)
        if minutes < 10:
            return f"Revit: همگام ({minutes} دقیقه پیش)"
        return f"Revit: آخرین همگام {minutes} دقیقه پیش"

    def start_probe(self):
        if not self.cfg.get("session_token"):
            return
        if getattr(self, "probe", None) is not None and self.probe.isRunning():
            return
        self.probe = ProbeWorker(copy.deepcopy(self.cfg))
        self.probe.result.connect(self.on_probe)
        self.probe.start()

    def on_probe(self, ok, data):
        if ok:
            apply_me(self.cfg, data)
            save_config(self.cfg)
            self.conn_label.setText("● متصل به سرور")
            self.conn_label.setStyleSheet("color:#8be28b;font-weight:600;")
            self.conn_label.setToolTip("")
        else:
            self.conn_label.setText("● قطع")
            self.conn_label.setStyleSheet("color:#ff8a80;font-weight:600;")
            self.conn_label.setToolTip(str(data))
        self.refresh_top()

    def open_support(self):
        SupportDialog(self.cfg.get("username", ""), self).exec()
