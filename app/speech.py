import os
import tempfile
import time
import wave

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self):
        self.frames = []
        self.stream = None

    def start(self):
        self.frames = []

        def callback(indata, frames, time_info, status):
            self.frames.append(indata.copy())

        self.stream = sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback)
        self.stream.start()

    def stop(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        audio = np.concatenate(self.frames) if self.frames else np.zeros((0, 1), dtype="int16")
        path = os.path.join(tempfile.gettempdir(), f"revit_agent_rec_{int(time.time())}.wav")
        with wave.open(path, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            w.writeframes(audio.tobytes())
        return path
