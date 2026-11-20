import threading

from PySide6.QtCore import QThread, Signal

from agent import RevitAgent
from llm_client import chat, transcribe

CHAT_SYSTEM = "You are a helpful assistant. Reply in the same language the user writes in. Be clear and accurate."


class AgentWorker(QThread):
    log_signal = Signal(str)
    approval_request = Signal(str, str)
    question_request = Signal(str)
    finished_ok = Signal(bool)

    def __init__(self, cfg, request):
        super().__init__()
        self.cfg = cfg
        self.request = request
        self._event = threading.Event()
        self._answer = None

    def run(self):
        ok = False
        try:
            agent = RevitAgent(self.cfg, self.log_signal.emit, self._ask_approval, self._ask_user)
            ok = agent.run(self.request)
        except Exception as e:
            self.log_signal.emit(f"✖ خطای داخلی: {e}")
        self.finished_ok.emit(ok)

    def _ui_call(self, signal, *args):
        self._event.clear()
        self._answer = None
        signal.emit(*args)
        self._event.wait()
        return self._answer

    def _ask_approval(self, code, summary):
        return bool(self._ui_call(self.approval_request, code, summary))

    def _ask_user(self, question):
        return self._ui_call(self.question_request, question) or ""

    def answer(self, value):
        self._answer = value
        self._event.set()


class ChatWorker(QThread):
    reply_ready = Signal(str)
    finished_ok = Signal(bool)
    error = Signal(str)

    def __init__(self, cfg, history, content):
        super().__init__()
        self.cfg = cfg
        self.history = list(history)
        self.content = content

    def run(self):
        try:
            messages = [{"role": "system", "content": CHAT_SYSTEM}] + self.history
            messages.append({"role": "user", "content": self.content})
            reply = chat(self.cfg, messages)
            self.reply_ready.emit(reply)
            self.finished_ok.emit(True)
        except Exception as e:
            self.error.emit(f"✖ {e}")
            self.finished_ok.emit(False)


class TranscribeWorker(QThread):
    text_ready = Signal(str)
    error = Signal(str)

    def __init__(self, cfg, wav_path):
        super().__init__()
        self.cfg = cfg
        self.wav_path = wav_path

    def run(self):
        try:
            self.text_ready.emit(transcribe(self.cfg, self.wav_path))
        except Exception as e:
            self.error.emit(f"✖ خطا در تبدیل صوت به متن: {e}")
