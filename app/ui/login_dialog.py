from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

from config import save_config
from llm_client import LLMError, apply_me, fetch_me, login_user


class LoginDialog(QDialog):
    def __init__(self, cfg, parent=None):
        super().__init__(parent)
        self.cfg = cfg
        self.setWindowTitle("ورود")
        self.setFixedWidth(360)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 24, 24, 20)
        lay.setSpacing(8)

        title = QLabel("ورود به Revit AI")
        title.setObjectName("title")
        lay.addWidget(title)

        lay.addWidget(QLabel("نام کاربری"))
        self.username = QLineEdit(cfg.get("username", ""))
        lay.addWidget(self.username)

        lay.addWidget(QLabel("رمز عبور"))
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        lay.addWidget(self.password)

        self.error = QLabel("")
        self.error.setStyleSheet("color:#ff8a80;")
        self.error.setWordWrap(True)
        lay.addWidget(self.error)

        row = QHBoxLayout()
        cancel = QPushButton("انصراف")
        ok = QPushButton("ورود")
        ok.setObjectName("accent")
        cancel.clicked.connect(self.reject)
        ok.clicked.connect(self.try_login)
        self.password.returnPressed.connect(self.try_login)
        row.addStretch()
        row.addWidget(cancel)
        row.addWidget(ok)
        lay.addLayout(row)

        (self.password if self.username.text() else self.username).setFocus()

    def try_login(self):
        try:
            data = login_user(self.cfg, self.username.text().strip(), self.password.text())
            self.cfg["session_token"] = data["token"]
            self.cfg["username"] = data["username"]
            apply_me(self.cfg, fetch_me(self.cfg))
            save_config(self.cfg)
            self.accept()
        except LLMError as e:
            self.cfg["session_token"] = ""
            self.error.setText(str(e))
            self.password.clear()
            self.password.setFocus()
        except Exception:
            self.error.setText("اتصال به سرور برقرار نشد. اینترنت رو بررسی کنید.")
