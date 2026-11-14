from test_engine import MockBackend

from audio_loopback.engine import AudioEngine
from audio_loopback.session import Session


class FakeSource:
    instances = []

    def __init__(self, path, rate, channels, video=False):
        self.rate = rate
        self.video = video
        self.error = ""
        self.stopped = False
        self.started = False
        self.instances.append(self)

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True


def test_players_are_exclusive_and_mic_capture_continues():
    session = Session(AudioEngine(MockBackend()), FakeSource)
    session.select_devices(1, 7)
    assert session.play("MP3", "audio.mp3")
    first = session.source
    assert session.engine.capture
    assert not session.engine.monitor
    assert session.engine.stream.options["device"] == (1, 7)
    assert session.start_microphone()
    assert not session.engine.monitor
    session.monitor_media = True
    session.poll()
    assert session.engine.monitor
    assert session.play("MP4", "video.mp4")
    assert first.stopped and session.source.video
    assert not session.engine.monitor
    session.stop_microphone()
    assert session.source and session.engine.capture
    session.stop_media()
    assert session.engine.state == "Stopped"
    session.select_devices(1, 8)
    assert session.play("MP3", "audio.mp3")
    assert session.engine.stream.options["device"] == (1, 8)
    session.stop_all()
    assert session.engine.stream is None and session.source is None


def test_missing_microphone_falls_back_to_selected_output_and_errors_stop():
    session = Session(AudioEngine(MockBackend()), FakeSource)
    session.select_devices(None, 9)
    assert session.play("MP3", "audio.mp3")
    assert session.engine.stream.options["device"] == 9
    assert "microphone unavailable" in session.diagnostic
    session.source.error = "bad codec"
    session.poll()
    assert session.engine.state == "Error"
    assert session.engine.error == "bad codec"
    assert not session.source and not session.engine.stream


def test_tone_is_independent_and_stop_all_cleans_up():
    session = Session(AudioEngine(MockBackend()), FakeSource)
    session.select_devices(1, 8)
    assert session.set_tone(True)
    assert not session.microphone
    assert session.engine.tone
    assert session.set_tone(False)
    assert session.engine.stream is None
    assert session.start_microphone()
    assert session.play("MP4", "video.mp4")
    source = session.source
    session.select_devices(1, 9)
    assert source.stopped and not session.microphone
