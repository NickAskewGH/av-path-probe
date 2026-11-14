import queue
import threading
from collections import deque
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np


def asset_path(filename):
    packaged = Path(__file__).parent / "assets" / filename
    if packaged.is_file():
        return packaged
    source = Path(__file__).resolve().parents[2] / "assets" / filename
    if source.is_file():
        return source
    raise FileNotFoundError(f"Bundled sample is missing: {filename}")


@dataclass
class AudioChunk:
    samples: np.ndarray
    loop: int
    position: int


class MediaSource:
    """One decoder worker and bounded queues, clocked by consumed PCM samples."""

    def __init__(self, path, rate, channels, video=False):
        self.path = Path(path)
        self.rate = rate
        self.channels = channels
        self.video = video
        self.audio = queue.Queue(maxsize=8)
        self.frames = deque(maxlen=24)
        self.cancel = threading.Event()
        self.ready = threading.Event()
        self.thread = None
        self.error = ""
        self.duration = 0.0
        self.loops = 0
        self.position = 0.0
        self.played = 0
        self.current = None
        self.offset = 0
        self.underruns = 0

    def start(self):
        if self.thread is not None:
            raise RuntimeError(
                "Decoder already started; create a new source to restart"
            )
        self.thread = threading.Thread(
            target=self._decode, name="media-decoder", daemon=True
        )
        self.thread.start()

    def stop(self):
        self.cancel.set()
        if self.thread:
            self.thread.join(timeout=3)
            if self.thread.is_alive():
                raise RuntimeError("Media decoder did not stop within 3 seconds")
        self.frames.clear()
        while True:
            try:
                self.audio.get_nowait()
            except queue.Empty:
                break

    def _put(self, chunk):
        while not self.cancel.is_set():
            try:
                self.audio.put(chunk, timeout=0.05)
                self.ready.set()
                return True
            except queue.Full:
                continue
        return False

    def _decode(self):
        total = 0
        loop = 0
        try:
            if not self.path.is_file():
                raise ValueError(f"Media file not found: {self.path}")
            while not self.cancel.is_set():
                with av.open(str(self.path)) as container:
                    if not container.streams.audio:
                        raise ValueError("Media has no audio soundtrack")
                    if self.video and not container.streams.video:
                        raise ValueError("MP4 has no video stream")
                    audio_stream = container.streams.audio[0]
                    video_stream = container.streams.video[0] if self.video else None
                    streams = [audio_stream] + ([video_stream] if video_stream else [])
                    self.duration = float(container.duration or 0) / av.time_base
                    resampler = av.AudioResampler(
                        format="fltp",
                        layout="stereo" if self.channels == 2 else "mono",
                        rate=self.rate,
                    )
                    loop_samples = 0
                    loop_start = total / self.rate
                    video_origin = (
                        (
                            float(video_stream.start_time or 0)
                            * float(video_stream.time_base)
                        )
                        if video_stream
                        else 0
                    )
                    for packet in container.demux(streams):
                        if self.cancel.is_set():
                            return
                        for frame in packet.decode():
                            if isinstance(frame, av.VideoFrame):
                                timestamp = (
                                    loop_start + float(frame.time or 0) - video_origin
                                )
                                self.frames.append((timestamp, frame))
                            else:
                                for decoded in resampler.resample(frame):
                                    samples = np.ascontiguousarray(
                                        decoded.to_ndarray().T, dtype=np.float32
                                    )
                                    np.nan_to_num(samples, copy=False)
                                    if not self._put(
                                        AudioChunk(samples, loop, loop_samples)
                                    ):
                                        return
                                    loop_samples += len(samples)
                                    total += len(samples)
                    for decoded in resampler.resample(None):
                        samples = np.ascontiguousarray(
                            decoded.to_ndarray().T, dtype=np.float32
                        )
                        if not self._put(AudioChunk(samples, loop, loop_samples)):
                            return
                        loop_samples += len(samples)
                        total += len(samples)
                    if loop_samples == 0:
                        raise ValueError("Media contains no decodable audio samples")
                    loop += 1
        except Exception as error:
            self.error = f"Cannot decode {self.path.name}: {error}"
            self.ready.set()

    def read_into(self, output):
        output.fill(0)
        written = 0
        while written < len(output):
            if self.current is None:
                try:
                    self.current = self.audio.get_nowait()
                    self.offset = 0
                except queue.Empty:
                    if self.ready.is_set() and not self.error:
                        self.underruns += 1
                    return
            count = min(len(output) - written, len(self.current.samples) - self.offset)
            output[written : written + count] = self.current.samples[
                self.offset : self.offset + count
            ]
            self.offset += count
            written += count
            self.played += count
            self.loops = self.current.loop
            self.position = (self.current.position + self.offset) / self.rate
            if self.offset == len(self.current.samples):
                self.current = None

    def video_frame(self, output_latency=0.0):
        clock = max(0, self.played / self.rate - output_latency)
        latest = None
        while self.frames:
            timestamp, frame = self.frames[0]
            if timestamp > clock:
                break
            try:
                self.frames.popleft()
            except IndexError:
                break
            latest = frame
        return latest
