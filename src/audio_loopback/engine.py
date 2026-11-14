import numpy as np
import sounddevice as sd

from .devices import negotiate
from .dsp import DEFAULT_GAIN, SAFE_PEAK, Levels, Processor, levels


class AudioEngine:
    def __init__(self, backend=sd):
        self.backend = backend
        self.stream = None
        self.state = "Stopped"
        self.error = ""
        self.warning = ""
        self.capture = False
        self.rate = 48000
        self.channels = 2
        self.blocksize = 512
        self.input_device = None
        self.output_device = None
        self.input_levels = Levels()
        self.output_levels = Levels()
        self.media = None
        self.gain = DEFAULT_GAIN
        self.modulated = True
        self.tone = False
        self.monitor = False
        self.latency = 0.0
        self._failed = ""
        self._finished = False

    def start(self, input_device, output_device, capture=True):
        self.stop()
        self.error = ""
        self.warning = ""
        self._failed = ""
        self._finished = False
        try:
            self.rate, self.channels = negotiate(
                input_device,
                output_device,
                capture,
                self.backend,
                fixed_rate=self.media.rate if self.media else None,
            )
            self.input_device, self.output_device = input_device, output_device
            self.capture = capture
            self.processor = Processor(self.rate, self.blocksize, self.gain)
            self.silence = np.zeros((self.blocksize, 1), np.float32)
            self.decoded = np.zeros((self.blocksize, self.channels), np.float32)
            options = dict(
                samplerate=self.rate,
                blocksize=self.blocksize,
                dtype="float32",
                latency="low",
                finished_callback=self._on_finished,
            )
            if capture:
                self.stream = self.backend.Stream(
                    device=(input_device, output_device),
                    channels=(1, self.channels),
                    callback=self._duplex,
                    **options,
                )
            else:
                self.stream = self.backend.OutputStream(
                    device=output_device,
                    channels=self.channels,
                    callback=self._output,
                    **options,
                )
            self.state = "Running"
            self.stream.start()
            stream_latency = self.stream.latency
            self.latency = float(
                stream_latency[-1]
                if isinstance(stream_latency, tuple)
                else stream_latency
            )
            return True
        except Exception as error:
            self.stop()
            self.state = "Error"
            self.error = (
                f"Audio device/permission error: {error}. "
                "Check microphone privacy settings and compatible devices."
            )
            return False

    def stop(self):
        self.state = "Stopped"
        stream, self.stream = self.stream, None
        if stream:
            try:
                stream.abort()
            except Exception as error:
                self.error = f"Stopping disconnected stream: {error}"
            try:
                stream.close()
            except Exception as error:
                self.error = f"Closing disconnected stream: {error}"
        self.capture = False
        self.input_levels = Levels()
        self.output_levels = Levels()

    def _on_finished(self):
        if self.state == "Running":
            self._finished = True

    def poll(self):
        if self._failed or self._finished:
            message = (
                self._failed
                or "Audio stream stopped unexpectedly; device may be unplugged"
            )
            self.stop()
            self.state = "Error"
            self.error = message
            self._failed = ""
            self._finished = False
        return self.state

    def _duplex(self, incoming, outgoing, frames, timing, status):
        self._process(incoming, outgoing, frames, status)

    def _output(self, outgoing, frames, timing, status):
        self._process(self.silence, outgoing, frames, status)

    def _process(self, incoming, outgoing, frames, status):
        try:
            if frames != self.blocksize:
                raise ValueError("Backend changed the fixed callback block size")
            if status:
                self.warning = str(status)
            self.input_levels = levels(incoming) if self.capture else Levels()
            self.processor.process(
                incoming,
                outgoing,
                modulated=self.modulated,
                gain=self.gain,
                tone=self.tone,
                monitor=self.monitor and self.capture,
            )
            media = self.media
            if media:
                media.read_into(self.decoded)
                self.decoded *= self.processor.gains[:, None]
                outgoing += self.decoded
            np.nan_to_num(outgoing, copy=False, nan=0, posinf=0, neginf=0)
            limited = bool(np.max(np.abs(outgoing)) >= SAFE_PEAK)
            np.clip(outgoing, -SAFE_PEAK, SAFE_PEAK, out=outgoing)
            self.output_levels = levels(outgoing)
            if limited:
                self.warning = "Output safety limiter active"
        except Exception as error:
            outgoing.fill(0)
            self._failed = f"Audio callback failed: {error}"
