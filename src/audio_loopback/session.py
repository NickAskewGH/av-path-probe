from .engine import AudioEngine
from .media import MediaSource


class Session:
    def __init__(self, engine=None, source_factory=MediaSource):
        self.engine = engine if engine is not None else AudioEngine()
        self.source_factory = source_factory
        self.input_device = None
        self.output_device = None
        self.microphone = False
        self.monitor_media = False
        self.source = None
        self.kind = None
        self.diagnostic = ""

    def _monitor(self):
        self.engine.monitor = self.microphone and (
            not self.source or self.monitor_media
        )

    def _stream(self, capture):
        if self.engine.stream and self.engine.capture == capture:
            return True
        return self.engine.start(self.input_device, self.output_device, capture)

    def start_microphone(self):
        if self._stream(True):
            self.microphone = True
            self._monitor()
            return True
        return False

    def stop_microphone(self):
        self.microphone = False
        self._monitor()
        if not self.source and not self.engine.tone:
            self.engine.stop()

    def set_tone(self, enabled):
        self.engine.tone = enabled
        if enabled and not self.engine.stream:
            if not self._stream(False):
                self.engine.tone = False
                return False
        elif not enabled and not self.microphone and not self.source:
            self.engine.stop()
        return True

    def play(self, kind, path):
        if kind not in ("MP3", "MP4"):
            raise ValueError("Unsupported player mode")
        self.stop_media()
        self.monitor_media = False
        self.diagnostic = ""
        if not self._stream(True):
            if self.microphone:
                return False
            capture_error = self.engine.error
            if not self._stream(False):
                return False
            self.diagnostic = (
                f"Media output only; microphone unavailable: {capture_error}"
            )
        source = self.source_factory(
            path, self.engine.rate, self.engine.channels, video=kind == "MP4"
        )
        try:
            source.start()
        except Exception as error:
            self.engine.error = f"Cannot start media: {error}"
            self.engine.state = "Error"
            source.stop()
            return False
        self.source = source
        self.kind = kind
        self.engine.media = source
        self._monitor()
        return True

    def stop_media(self):
        source, self.source = self.source, None
        self.kind = None
        self.engine.media = None
        if source:
            source.stop()
        self._monitor()
        if not self.microphone and not self.engine.tone:
            self.engine.stop()

    def stop_all(self):
        self.microphone = False
        self.engine.tone = False
        self.stop_media()
        self.engine.stop()

    def select_devices(self, input_device, output_device):
        self.stop_all()
        self.input_device, self.output_device = input_device, output_device
        self.diagnostic = (
            "Devices changed; stopped safely. Start the desired mode again."
        )

    def poll(self):
        state = self.engine.poll()
        error = self.source.error if self.source else ""
        if state == "Error" or error:
            message = error or self.engine.error
            self.stop_all()
            self.engine.state = "Error"
            self.engine.error = message
        self._monitor()
