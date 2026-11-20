from PySide6.QtCore import QThread, Signal

from llm_client import fetch_me


class ProbeWorker(QThread):
    result = Signal(bool, object)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            self.result.emit(True, fetch_me(self.cfg))
        except Exception as e:
            self.result.emit(False, str(e))
