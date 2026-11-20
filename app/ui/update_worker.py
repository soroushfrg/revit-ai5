from PySide6.QtCore import QThread, Signal

from updater import check_update, download


class UpdateCheckWorker(QThread):
    found = Signal(object)
    up_to_date = Signal()
    failed = Signal(str)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        try:
            manifest = check_update(self.url)
            if manifest:
                self.found.emit(manifest)
            else:
                self.up_to_date.emit()
        except Exception as e:
            self.failed.emit(f"✖ بررسی بروزرسانی انجام نشد: {e}")


class DownloadWorker(QThread):
    progress = Signal(int)
    done = Signal(str)
    error = Signal(str)

    def __init__(self, manifest):
        super().__init__()
        self.manifest = manifest

    def run(self):
        try:
            path = download(self.manifest, self.progress.emit)
            self.done.emit(path)
        except Exception as e:
            self.error.emit(f"✖ بروزرسانی انجام نشد: {e}")
