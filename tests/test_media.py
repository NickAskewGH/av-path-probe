import time
import wave
from fractions import Fraction

import av
import numpy as np

from audio_loopback.media import MediaSource, asset_path


def create_wav(path):
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48000)
        times = np.arange(1440) / 48000
        output.writeframes(
            (np.sin(2 * np.pi * 440 * times) * 8000).astype("<i2").tobytes()
        )


def test_decoder_loops_clock_and_stop(tmp_path):
    path = tmp_path / "tone.wav"
    create_wav(path)
    source = MediaSource(path, 48000, 2)
    source.start()
    assert source.ready.wait(5)
    output = np.zeros((512, 2), np.float32)
    deadline = time.monotonic() + 5
    peaks = []
    while source.loops < 3 and time.monotonic() < deadline:
        source.read_into(output)
        peaks.append(float(np.abs(output).max()))
        source.cancel.wait(0.001)
    source.stop()
    assert not source.thread.is_alive()
    assert source.loops >= 3
    assert max(peaks) > 0.1
    assert not source.error
    assert source.audio.empty()


def test_missing_file_and_missing_soundtrack(tmp_path):
    source = MediaSource(tmp_path / "missing.mp4", 48000, 2, video=True)
    source.start()
    assert source.ready.wait(5)
    source.stop()
    assert "not found" in source.error
    path = tmp_path / "silent.mp4"
    with av.open(str(path), "w") as container:
        stream = container.add_stream("mpeg4", rate=30)
        stream.width, stream.height, stream.pix_fmt = 64, 64, "yuv420p"
        frame = av.VideoFrame.from_ndarray(
            np.zeros((64, 64, 3), np.uint8), format="rgb24"
        )
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    source = MediaSource(path, 48000, 2, video=True)
    source.start()
    assert source.ready.wait(5)
    source.stop()
    assert "no audio" in source.error


def test_short_mp4_loops_audio_video_and_restarts(tmp_path):
    path = tmp_path / "short.mp4"
    with av.open(str(path), "w") as container:
        video = container.add_stream("mpeg4", rate=30)
        video.width, video.height, video.pix_fmt = 64, 64, "yuv420p"
        audio = container.add_stream("aac", rate=48000)
        audio.layout = "mono"
        for index in range(10):
            frame = av.VideoFrame.from_ndarray(
                np.full((64, 64, 3), 30 + index * 20, np.uint8), format="rgb24"
            )
            frame.pts, frame.time_base = index, Fraction(1, 30)
            for packet in video.encode(frame):
                container.mux(packet)
        times = np.arange(16000) / 48000
        frame = av.AudioFrame.from_ndarray(
            (0.2 * np.sin(2 * np.pi * 440 * times)).astype(np.float32)[None, :],
            format="fltp",
            layout="mono",
        )
        frame.sample_rate, frame.pts, frame.time_base = 48000, 0, Fraction(1, 48000)
        for packet in audio.encode(frame):
            container.mux(packet)
        for stream in (audio, video):
            for packet in stream.encode():
                container.mux(packet)
    for _ in range(2):
        source = MediaSource(path, 48000, 2, video=True)
        source.start()
        try:
            assert source.ready.wait(5)
            output = np.empty((512, 2), np.float32)
            deadline = time.monotonic() + 5
            pictures, nonzero = 0, False
            while source.loops < 3 and time.monotonic() < deadline:
                source.read_into(output)
                nonzero |= bool(output.any())
                pictures += source.video_frame() is not None
                source.cancel.wait(0.001)
            assert not source.error
            assert source.loops >= 3
            assert pictures > 2 and nonzero
        finally:
            source.stop()
        assert not source.thread.is_alive()


def test_bundled_codecs_decode_actual_audio_and_video():
    for filename, video in (("sample-30s.mp3", False), ("sample-30s-720p.mp4", True)):
        source = MediaSource(asset_path(filename), 48000, 2, video=video)
        source.start()
        try:
            assert source.ready.wait(10)
            assert not source.error
            assert 29.9 < source.duration < 30.1
            output = np.zeros((512, 2), np.float32)
            nonzero = False
            saw_picture = False
            deadline = time.monotonic() + 10
            for _ in range(60):
                source.read_into(output)
                nonzero |= bool(output.any())
                if video:
                    frame = source.video_frame()
                    saw_picture |= frame is not None
                if time.monotonic() > deadline:
                    break
                source.cancel.wait(0.002)
            assert nonzero
            if video:
                assert saw_picture
        finally:
            source.stop()
