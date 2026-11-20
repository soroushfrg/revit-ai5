from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout

SUPPORT_URL = "https://t.me/soroushfrg"


class SupportDialog(QDialog):
    def __init__(self, username, parent=None):
        super().__init__(parent)
        self.username = username or "کاربر"
        self.setWindowTitle("پیام به پشتیبانی")
        self.resize(480, 320)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 16)
        lay.setSpacing(10)

        title = QLabel("پیام خودتون رو بنویسید")
        title.setObjectName("title")
        lay.addWidget(title)

        hint = QLabel("پیام شما کپی میشه و تلگرام پشتیبانی باز میشه. کافیه در تلگرام Ctrl+V بزنید و ارسال کنید.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self.text = QTextEdit()
        self.text.setPlaceholderText("مشکل یا سؤالتون رو بنویسید...")
        lay.addWidget(self.text, 1)

        row = QHBoxLayout()
        cancel = QPushButton("انصراف")
        send = QPushButton("کپی و باز کردن تلگرام")
        send.setObjectName("accent")
        cancel.clicked.connect(self.reject)
        send.clicked.connect(self.send)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(send)
        lay.addLayout(row)

    def send(self):
        body = self.text.toPlainText().strip()
        if not body:
            return
        message = f"[Revit AI] کاربر: {self.username}\n\n{body}"
        QApplication.clipboard().setText(message)
        QDesktopServices.openUrl(QUrl(SUPPORT_URL))
        self.accept()
