import av
import numpy as np
import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from test_engine import MockBackend
from test_session import FakeSource

from audio_loopback.devices import Device
from audio_loopback.engine import AudioEngine
from audio_loopback.gui import (
    MainWindow,
    VideoWindow,
    load_size,
    save_size,
    validate_size,
)
from audio_loopback.session import Session


@pytest.fixture(scope="module")
def application():
    return QApplication.instance() or QApplication([])


def test_size_validation_and_persistence(tmp_path):
    settings = QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat)
    assert load_size(settings) == (960, 540)
    save_size(settings, 1024, 768)
    assert load_size(QSettings(str(tmp_path / "test.ini"), QSettings.IniFormat)) == (
        1024,
        768,
    )
    with pytest.raises(ValueError):
        validate_size(200, 100)
    settings.setValue("video/width", "invalid")
    assert load_size(settings) == (960, 540)


def test_video_content_size_letterbox_and_close(application):
    video = VideoWindow()
    video.resize(1024, 768)
    frame = av.VideoFrame.from_ndarray(
        np.full((720, 1280, 3), 180, np.uint8), format="rgb24"
    )
    video.show_frame(frame)
    video.show()
    application.processEvents()
    image = video.grab().toImage()
    assert image.pixelColor(10, 10).value() == 0
    assert image.pixelColor(512, 384).value() > 100
    closed = []
    video.closed.connect(lambda: closed.append(True))
    video.close()
    assert closed and video.image.isNull()


def test_window_starts_stopped_and_device_change_stops(application, tmp_path):
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.IniFormat)
    session = Session(AudioEngine(MockBackend()), FakeSource)
    devices = [
        Device(1, "Input", 0, 1, 0, 48000),
        Device(2, "Speakers", 0, 0, 2, 48000),
        Device(3, "Headphones", 0, 0, 2, 48000),
    ]
    window = MainWindow(session, settings, lambda: (devices, (1, 2)))
    window.show()
    application.processEvents()
    assert session.engine.stream is None
    assert window.start.text() == "Start"
    window.start.click()
    assert session.microphone
    window.outputs.setCurrentIndex(1)
    assert not session.microphone and session.output_device == 3
    assert session.engine.stream is None
    window.width_input.setValue(640)
    window.height_input.setValue(360)
    assert load_size(settings) == (640, 360)
    window.close()


def test_source_smoke_renders_real_nonblank_video(application, tmp_path):
    from PySide6.QtGui import QImage

    from audio_loopback.smoke import run_smoke

    assert run_smoke(application, tmp_path / "smoke.json") == 0
    image = QImage(str(tmp_path / "smoke-video.png"))
    assert image.pixelColor(256, 384).value() > 20
