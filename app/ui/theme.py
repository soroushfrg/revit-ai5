DARK_QSS = """
QWidget { background:#1e1f22; color:#dfe1e5; font-family:'Segoe UI'; font-size:10pt; }
QMainWindow, QDialog { background:#1e1f22; }

QFrame#sidebar { background:#2b2d30; border-right:1px solid #393b40; }
QFrame#card { background:#2b2d30; border:1px solid #393b40; border-radius:14px; }
QFrame#header { background:transparent; }

QLabel#title { font-size:14pt; font-weight:600; color:#ffffff; background:transparent; }
QLabel#brand { font-size:13pt; font-weight:700; color:#9fd8f5; background:transparent; padding:6px 4px; }
QLabel#muted { color:#8a8f98; background:transparent; }
QLabel#chip { background:#2b2d30; border:1px solid #3c3f41; border-radius:12px; padding:5px 12px; color:#9fd8f5; }
QLabel#attach { color:#9fd8f5; background:transparent; }

QTextEdit#log { background:transparent; border:none; padding:14px; }
QTextEdit#input { background:transparent; border:none; font-size:11pt; padding:6px; }

QTextEdit, QLineEdit, QTableWidget, QComboBox, QSpinBox {
    background:#1e1f22; border:1px solid #3c3f41; border-radius:8px; padding:5px; selection-background-color:#0696d7;
}

QPushButton { background:#3c3f41; border:none; border-radius:10px; padding:8px 14px; }
QPushButton:hover { background:#4b4e52; }
QPushButton:pressed { background:#2f3134; }
QPushButton:disabled { color:#6b6f75; background:#2f3134; }

QPushButton#icon { background:transparent; border-radius:18px; min-width:36px; max-width:36px;
                   min-height:36px; max-height:36px; padding:0; font-size:13pt; }
QPushButton#icon:hover { background:#3c3f41; }

QPushButton#round { border-radius:22px; min-width:44px; max-width:44px; min-height:44px; max-height:44px;
                    padding:0; font-size:14pt; background:#3c3f41; }
QPushButton#round:hover { background:#4b4e52; }
QPushButton#round[recording="true"] { background:#e5484d; color:white; }

QPushButton#primary { background:#0696d7; color:white; font-weight:600; border-radius:22px;
                      min-width:44px; max-width:44px; min-height:44px; max-height:44px; padding:0; font-size:14pt; }
QPushButton#primary:hover { background:#2aa7e3; }
QPushButton#primary:disabled { background:#3c3f41; color:#6b6f75; }

QPushButton#nav { background:transparent; text-align:left; padding:9px 14px; border-radius:10px; color:#dfe1e5; }
QPushButton#nav:hover { background:#3c3f41; }
QPushButton#nav:checked { background:#0696d7; color:white; font-weight:600; }

QPushButton#accent { background:#0696d7; color:white; font-weight:600; }
QPushButton#accent:hover { background:#2aa7e3; }

QCheckBox { spacing:8px; background:transparent; padding:4px 6px; }
QCheckBox::indicator { width:16px; height:16px; border-radius:4px; border:1px solid #5a5d63; background:#1e1f22; }
QCheckBox::indicator:checked { background:#0696d7; border-color:#0696d7; }

QStatusBar { background:transparent; color:#8a8f98; }
QStatusBar::item { border:none; }

QScrollBar:vertical { background:transparent; width:10px; margin:2px; }
QScrollBar::handle:vertical { background:#4b4e52; border-radius:4px; min-height:30px; }
QScrollBar::handle:vertical:hover { background:#5c6066; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }

QGroupBox { border:1px solid #393b40; border-radius:10px; margin-top:16px; padding-top:12px; background:#2b2d30; }
QGroupBox::title { subcontrol-origin: margin; left:12px; padding:0 6px; color:#9fd8f5; background:#2b2d30; }
QHeaderView::section { background:#2b2d30; padding:6px; border:none; }
QToolTip { background:#2b2d30; color:#dfe1e5; border:1px solid #3c3f41; padding:6px; border-radius:6px; }
"""
