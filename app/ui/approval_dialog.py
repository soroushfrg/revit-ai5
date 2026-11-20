from PySide6.QtCore import Qt
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout


class ApprovalDialog(QDialog):
    def __init__(self, code, summary, parent=None):
        super().__init__(parent)
        self.setWindowTitle("تأیید اجرا")
        self.resize(760, 560)
        lay = QVBoxLayout(self)

        lbl = QLabel(summary or "کد پیشنهادی برای اجرا در Revit:")
        lbl.setWordWrap(True)
        lay.addWidget(lbl)

        code_box = QTextEdit()
        code_box.setReadOnly(True)
        code_box.setLayoutDirection(Qt.LeftToRight)
        code_box.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        code_box.setPlainText(code)
        lay.addWidget(code_box, 1)

        row = QHBoxLayout()
        row.addStretch()
        reject = QPushButton("رد")
        approve = QPushButton("تأیید و اجرا")
        approve.setObjectName("primary")
        reject.clicked.connect(self.reject)
        approve.clicked.connect(self.accept)
        row.addWidget(reject)
        row.addWidget(approve)
        lay.addLayout(row)
