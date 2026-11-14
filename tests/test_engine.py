from types import SimpleNamespace

import numpy as np

from audio_loopback.engine import AudioEngine


class MockStream:
    def __init__(self, **options):
        self.options = options
        self.latency = (0.03, 0.04)
        self.active = False
        self.closed = False

    def start(self):
        self.active = True

    def abort(self):
        self.active = False
        self.options["finished_callback"]()

    def close(self):
        self.closed = True


class MockBackend:
    Stream = MockStream
    OutputStream = MockStream

    def query_devices(self, index):
        return dict(
            max_input_channels=1,
            max_output_channels=2,
            default_samplerate=48000,
            hostapi=0 if index != 99 else 1,
        )

    def check_input_settings(self, **options):
        pass

    def check_output_settings(self, **options):
        pass


def test_start_stop_restart_and_errors():
    engine = AudioEngine(MockBackend())
    assert engine.start(1, 2)
    first = engine.stream
    assert first.options["device"] == (1, 2)
    assert engine.latency == 0.04
    engine.stop()
    assert first.closed and engine.state == "Stopped"
    assert engine.start(1, 3)
    assert engine.stream is not first
    assert not engine.start(99, 3)
    assert engine.state == "Error" and "host API" in engine.error
    assert engine.start(1, 3)
    engine._on_finished()
    assert engine.poll() == "Error"
    assert "unplugged" in engine.error


def test_media_and_microphone_meter_actual_samples_selected_output():
    engine = AudioEngine(MockBackend())
    assert engine.start(1, 7)
    engine.monitor = False
    incoming = np.full((512, 1), 0.25, np.float32)
    outgoing = np.empty((512, 2), np.float32)
    source = SimpleNamespace(read_into=lambda buffer: buffer.fill(0.5))
    engine.media = source
    engine._duplex(incoming, outgoing, 512, None, None)
    assert engine.input_levels.rms == 0.25
    np.testing.assert_allclose(outgoing, 0.1)
    assert engine.output_levels.rms > 0
    engine.media = None
    engine._duplex(incoming, outgoing, 512, None, None)
    assert not outgoing.any()
    assert engine.input_levels.rms > 0
    assert engine.stream.options["device"] == (1, 7)
    engine.stop()


def test_output_only_tone_and_callback_failure():
    engine = AudioEngine(MockBackend())
    assert engine.start(None, 8, capture=False)
    assert engine.stream.options["device"] == 8
    engine.tone = True
    outgoing = np.empty((512, 2), np.float32)
    engine._output(outgoing, 512, None, None)
    assert engine.input_levels.peak == 0 and engine.output_levels.peak > 0
    engine._output(outgoing, 100, None, None)
    assert not outgoing.any()
    assert engine.poll() == "Error"


def test_rate_negotiation_falls_back():
    class Backend(MockBackend):
        def check_input_settings(self, **options):
            if options["samplerate"] == 48000:
                raise ValueError("unsupported sample rate")

    engine = AudioEngine(Backend())
    assert engine.start(1, 2)
    assert engine.rate == 44100
    engine.stop()


def test_media_gain_changes_are_smoothed_and_mixing_is_limited():
    engine = AudioEngine(MockBackend())
    assert engine.start(1, 7)
    engine.media = SimpleNamespace(read_into=lambda buffer: buffer.fill(1.0))
    engine.gain = 0.5
    outgoing = np.empty((512, 2), np.float32)
    incoming = np.ones((512, 1), np.float32)
    engine._duplex(incoming, outgoing, 512, None, None)
    assert 0.2 < outgoing[0, 0] < 0.201
    engine.monitor = True
    engine.modulated = False
    engine._duplex(incoming, outgoing, 512, None, None)
    assert np.max(outgoing) <= 0.9
    assert engine.output_levels.clipped
    assert "limiter" in engine.warning
    engine.stop()
