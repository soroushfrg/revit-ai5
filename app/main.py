import os
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog

from config import load_config
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.theme import DARK_QSS


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Revit AI")
    app.setWindowIcon(QIcon(resource_path(os.path.join("assets", "icon.ico"))))
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_QSS)
    cfg = load_config()
    if cfg.get("language") == "fa":
        app.setLayoutDirection(Qt.RightToLeft)
    if not cfg.get("session_token") or not cfg.get("models"):
        login = LoginDialog(cfg)
        if login.exec() != QDialog.Accepted:
            sys.exit(0)
    window = MainWindow(cfg)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
