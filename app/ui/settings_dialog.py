import copy

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLineEdit, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from config import save_config


class SettingsDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تنظیمات")
        self.resize(600, 380)
        self.cfg = copy.deepcopy(cfg)
        root = QVBoxLayout(self)

        general = QGroupBox("عمومی")
        form = QFormLayout(general)
        self.name = QLineEdit(self.cfg["user_name"])
        self.lang = QComboBox()
        self.lang.addItems(["fa", "en"])
        self.lang.setCurrentText(self.cfg["language"])
        self.stt_lang = QLineEdit(self.cfg.get("stt_language", "fa"))
        bridge_w, self.bridge = self._path_widget(self.cfg["bridge_dir"])
        backup_w, self.backup = self._path_widget(self.cfg["backup_dir"])
        self.retries = QSpinBox()
        self.retries.setRange(1, 10)
        self.retries.setValue(int(self.cfg["max_retries"]))
        self.timeout = QSpinBox()
        self.timeout.setRange(30, 3600)
        self.timeout.setValue(int(self.cfg["job_timeout_sec"]))
        self.approval = QCheckBox("قبل از هر اجرا تأیید بگیر")
        self.approval.setChecked(bool(self.cfg["require_approval"]))
        form.addRow("نام شما:", self.name)
        form.addRow("زبان:", self.lang)
        form.addRow("زبان صوت (fa یا en):", self.stt_lang)
        form.addRow("پوشه پل Revit:", bridge_w)
        form.addRow("پوشه بکاپ:", backup_w)
        form.addRow("حداکثر تلاش اصلاح خطا:", self.retries)
        form.addRow("زمان انتظار هر اجرا (ثانیه):", self.timeout)
        form.addRow("", self.approval)
        root.addWidget(general)

        account = QGroupBox("حساب")
        alay = QHBoxLayout(account)
        self.logout_btn = QPushButton("خروج از حساب")
        self.logout_btn.clicked.connect(self._logout)
        alay.addWidget(self.logout_btn)
        alay.addStretch()
        root.addWidget(account)

        root.addStretch()
        bb = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        bb.accepted.connect(self._save)
        bb.rejected.connect(self.reject)
        root.addWidget(bb)

    def _path_widget(self, text):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        edit = QLineEdit(text)
        btn = QPushButton("...")
        btn.setFixedWidth(40)
        btn.clicked.connect(lambda: self._browse(edit))
        h.addWidget(edit)
        h.addWidget(btn)
        return w, edit

    def _browse(self, edit):
        d = QFileDialog.getExistingDirectory(self, "انتخاب پوشه", edit.text())
        if d:
            edit.setText(d)

    def _logout(self):
        self.cfg["session_token"] = ""
        self.cfg["models"] = []
        self.cfg["model_name"] = ""
        self.accept()

    def _save(self):
        self.cfg.update({
            "user_name": self.name.text().strip(),
            "language": self.lang.currentText(),
            "stt_language": self.stt_lang.text().strip() or "fa",
            "bridge_dir": self.bridge.text().strip(),
            "backup_dir": self.backup.text().strip(),
            "max_retries": self.retries.value(),
            "job_timeout_sec": self.timeout.value(),
            "require_approval": self.approval.isChecked(),
        })
        save_config(self.cfg)
        self.accept()
