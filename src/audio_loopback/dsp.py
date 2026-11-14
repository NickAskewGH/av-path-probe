from dataclasses import dataclass

import numpy as np

SAFE_PEAK = 0.9
DEFAULT_GAIN = 0.2


@dataclass(frozen=True)
class Levels:
    rms: float = 0.0
    peak: float = 0.0
    clipped: bool = False


def levels(samples: np.ndarray) -> Levels:
    if not samples.size:
        return Levels()
    peak = float(np.max(np.abs(samples)))
    rms = float(np.sqrt(np.mean(np.square(samples), dtype=np.float64)))
    return Levels(rms, peak, peak >= float(np.float32(SAFE_PEAK)))


def aspect_fit(width: int, height: int, source_width: int, source_height: int):
    if min(width, height, source_width, source_height) <= 0:
        raise ValueError("Video dimensions must be positive")
    scale = min(width / source_width, height / source_height)
    fitted_width = round(source_width * scale)
    fitted_height = round(source_height * scale)
    return (
        (width - fitted_width) // 2,
        (height - fitted_height) // 2,
        fitted_width,
        fitted_height,
    )


class Processor:
    """Fixed-size, continuously phased microphone DSP; no I/O in processing."""

    def __init__(self, rate=48000, blocksize=512, gain=DEFAULT_GAIN):
        self.rate = rate
        self.blocksize = blocksize
        self.position = 0
        self.gain = gain
        self.indices = np.arange(blocksize, dtype=np.float64)
        self.ramp = (self.indices + 1) / blocksize
        self.envelope = np.empty(blocksize, dtype=np.float64)
        self.gains = np.empty(blocksize, dtype=np.float64)
        self.mono = np.empty(blocksize, dtype=np.float32)
        self.tone = np.empty(blocksize, dtype=np.float64)

    def process(
        self,
        incoming,
        outgoing,
        *,
        modulated=True,
        gain=DEFAULT_GAIN,
        tone=False,
        monitor=True,
    ):
        if incoming.shape[0] != self.blocksize or outgoing.shape[0] != self.blocksize:
            raise ValueError("Unexpected callback block size")
        if incoming.ndim != 2 or outgoing.ndim != 2:
            raise ValueError("Audio buffers must be frames by channels")
        if not incoming.shape[1] or not outgoing.shape[1]:
            raise ValueError("Audio buffers need at least one channel")
        with np.errstate(invalid="ignore", over="ignore"):
            np.mean(incoming, axis=1, out=self.mono)
        np.nan_to_num(self.mono, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
        np.clip(self.mono, -1.0, 1.0, out=self.mono)
        np.add(self.indices, self.position, out=self.envelope)
        self.envelope *= 2 * np.pi * 8 / self.rate
        np.sin(self.envelope, out=self.envelope)
        self.envelope *= 0.35
        self.envelope += 0.65
        if not modulated:
            self.envelope.fill(1.0)
        target = float(np.clip(np.nan_to_num(gain), 0.0, 0.5))
        np.multiply(self.ramp, target - self.gain, out=self.gains)
        self.gains += self.gain
        self.gain = target
        self.mono *= self.envelope
        if not monitor:
            self.mono.fill(0.0)
        if tone:
            np.add(self.indices, self.position, out=self.tone)
            self.tone *= 2 * np.pi * 1000 / self.rate
            np.sin(self.tone, out=self.tone)
            self.mono += self.tone * 0.1
        self.mono *= self.gains
        np.clip(self.mono, -SAFE_PEAK, SAFE_PEAK, out=self.mono)
        outgoing[:] = self.mono[:, None]
        self.position += self.blocksize
