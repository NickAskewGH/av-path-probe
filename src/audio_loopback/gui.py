import math
from pathlib import Path

from PySide6.QtCore import QRect, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .devices import discover
from .dsp import Levels, aspect_fit
from .media import asset_path
from .session import Session


def validate_size(width, height):
    width, height = int(width), int(height)
    if not 320 <= width <= 3840 or not 180 <= height <= 2160:
        raise ValueError(
            "Video content size must be 320-3840 by 180-2160 logical pixels"
        )
    return width, height


def load_size(settings):
    try:
        return validate_size(
            settings.value("video/width", 960), settings.value("video/height", 540)
        )
    except (ValueError, TypeError):
        return 960, 540


def save_size(settings, width, height):
    width, height = validate_size(width, height)
    settings.setValue("video/width", width)
    settings.setValue("video/height", height)
    settings.sync()


class Meter(QWidget):
    def __init__(self):
        super().__init__()
        self.level = Levels()
        self.setMinimumHeight(24)
        self.setMinimumWidth(220)

    def set_level(self, level):
        self.level = level
        self.update()

    @staticmethod
    def fraction(value):
        return max(0, min(1, (20 * math.log10(max(value, 1e-6)) + 60) / 60))

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#202b28"))
        color = QColor("#c94143" if self.level.clipped else "#329c72")
        painter.fillRect(
            0,
            0,
            round(self.width() * self.fraction(self.level.rms)),
            self.height(),
            color,
        )
        peak = min(
            self.width() - 2, round(self.width() * self.fraction(self.level.peak))
        )
        painter.fillRect(peak, 0, 2, self.height(), QColor("#efc85b"))
        painter.setPen(QColor("#ffffff"))
        decibels = 20 * math.log10(max(self.level.rms, 1e-6))
        text = "Silent" if decibels <= -100 else f"{decibels:.1f} dBFS RMS"
        painter.drawText(
            self.rect().adjusted(8, 0, -8, 0),
            Qt.AlignRight | Qt.AlignVCenter,
            text + (" · LIMIT" if self.level.clipped else ""),
        )


class VideoWindow(QWidget):
    closed = Signal()
    resized = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Loopback Tester · Video")
        self.setMinimumSize(320, 180)
        self.setMaximumSize(3840, 2160)
        self.image = QImage()

    def show_frame(self, frame):
        pixels = frame.to_ndarray(format="rgb24")
        self.image = QImage(
            pixels.data,
            pixels.shape[1],
            pixels.shape[0],
            pixels.strides[0],
            QImage.Format_RGB888,
        ).copy()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.black)
        if not self.image.isNull():
            fitted = aspect_fit(
                self.width(), self.height(), self.image.width(), self.image.height()
            )
            painter.drawImage(QRect(*fitted), self.image)

    def resizeEvent(self, event):
        self.resized.emit(self.width(), self.height())

    def closeEvent(self, event):
        self.image = QImage()
        self.closed.emit()
        event.accept()


class MainWindow(QWidget):
    def __init__(self, session=None, settings=None, device_discovery=discover):
        super().__init__()
        self.session = session if session is not None else Session()
        self.settings = (
            settings if settings is not None else QSettings("AudioLoopback", "Tester")
        )
        self.device_discovery = device_discovery
        self.setWindowTitle("Audio Loopback Tester")
        self.resize(640, 600)
        self.video = VideoWindow()
        self.video.closed.connect(self._video_closed)
        self.paths = {
            "MP3": asset_path("sample-30s.mp3"),
            "MP4": asset_path("sample-30s-720p.mp4"),
        }
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        devices = QFormLayout()
        self.inputs, self.outputs = QComboBox(), QComboBox()
        self.inputs.setMinimumContentsLength(24)
        self.outputs.setMinimumContentsLength(24)
        self.inputs.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.outputs.setSizeAdjustPolicy(
            QComboBox.AdjustToMinimumContentsLengthWithIcon
        )
        devices.addRow("Input device", self.inputs)
        devices.addRow("Output device", self.outputs)
        layout.addLayout(devices)
        refresh = QPushButton("Refresh devices")
        refresh.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        refresh.clicked.connect(self._refresh_devices)
        layout.addWidget(refresh, alignment=Qt.AlignRight)
        layout.addWidget(QLabel("Microphone input"))
        self.input_meter = Meter()
        layout.addWidget(self.input_meter)
        layout.addWidget(
            QLabel("Speaker output (submitted) · microphone + tone + decoded media")
        )
        self.output_meter = Meter()
        layout.addWidget(self.output_meter)
        controls = QHBoxLayout()
        self.start = QPushButton("Start")
        self.start.setMinimumHeight(40)
        self.start.clicked.connect(self._microphone)
        controls.addWidget(self.start)
        self.effect = QComboBox()
        self.effect.addItems(["Modulated", "Bypass"])
        self.effect.currentIndexChanged.connect(
            lambda index: setattr(self.session.engine, "modulated", index == 0)
        )
        controls.addWidget(QLabel("Effect"))
        controls.addWidget(self.effect)
        stop_all = QPushButton("Stop All")
        stop_all.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        stop_all.clicked.connect(self._stop_all)
        controls.addWidget(stop_all)
        layout.addLayout(controls)
        gain_row = QHBoxLayout()
        gain_row.addWidget(QLabel("Output level"))
        self.gain = QSlider(Qt.Horizontal)
        self.gain.setRange(0, 50)
        self.gain.setValue(20)
        self.gain_label = QLabel("20%")
        self.gain.valueChanged.connect(self._gain_changed)
        gain_row.addWidget(self.gain)
        gain_row.addWidget(self.gain_label)
        layout.addLayout(gain_row)
        self.tone = QCheckBox("Test tone · 1 kHz")
        self.tone.toggled.connect(self._tone_changed)
        layout.addWidget(self.tone)
        self.monitor = QCheckBox("Monitor microphone into output during media")
        self.monitor.toggled.connect(
            lambda enabled: setattr(self.session, "monitor_media", enabled)
        )
        layout.addWidget(self.monitor)
        self.buttons, self.labels, self.file_labels = {}, {}, {}
        for kind in ("MP3", "MP4"):
            row = QHBoxLayout()
            button = QPushButton(f"Play {kind}")
            button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
            button.clicked.connect(lambda checked=False, mode=kind: self._play(mode))
            row.addWidget(button)
            browse = QPushButton()
            browse.setIcon(self.style().standardIcon(QStyle.SP_DialogOpenButton))
            browse.setToolTip(f"Choose local {kind} file")
            browse.clicked.connect(lambda checked=False, mode=kind: self._browse(mode))
            row.addWidget(browse)
            reset = QPushButton()
            reset.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
            reset.setToolTip(f"Use bundled {kind} sample")
            reset.clicked.connect(
                lambda checked=False, mode=kind: self._reset_sample(mode)
            )
            row.addWidget(reset)
            file_label = QLabel(self.paths[kind].name)
            file_label.setMinimumWidth(0)
            row.addWidget(file_label, 1)
            layout.addLayout(row)
            label = QLabel("Stopped · 0:00 · loops 0")
            layout.addWidget(label)
            self.buttons[kind], self.labels[kind] = button, label
            self.file_labels[kind] = file_label
        size_row = QHBoxLayout()
        self.width_input, self.height_input = QSpinBox(), QSpinBox()
        self.width_input.setRange(320, 3840)
        self.height_input.setRange(180, 2160)
        width, height = load_size(self.settings)
        self.width_input.setValue(width)
        self.height_input.setValue(height)
        size_row.addWidget(QLabel("Video width"))
        size_row.addWidget(self.width_input)
        size_row.addWidget(QLabel("Video height"))
        size_row.addWidget(self.height_input)
        layout.addLayout(size_row)
        self.width_input.valueChanged.connect(self._size_changed)
        self.height_input.valueChanged.connect(self._size_changed)
        self.video.resized.connect(self._manual_resize)
        self.status = QLabel("Stopped")
        self.status.setMinimumWidth(0)
        layout.addWidget(self.status)
        self._refresh_devices()
        self.inputs.currentIndexChanged.connect(self._devices_changed)
        self.outputs.currentIndexChanged.connect(self._devices_changed)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(40)
        self._tick()

    def _refresh_devices(self):
        self._stop_all()
        old_input = self.inputs.currentData()
        old_output = self.outputs.currentData()
        self.inputs.blockSignals(True)
        self.outputs.blockSignals(True)
        self.inputs.clear()
        self.outputs.clear()
        try:
            devices, defaults = self.device_discovery()
            for device in devices:
                if device.inputs:
                    self.inputs.addItem(device.name, device.index)
                if device.outputs:
                    self.outputs.addItem(device.name, device.index)
            for combo, previous, default in (
                (self.inputs, old_input, defaults[0]),
                (self.outputs, old_output, defaults[1]),
            ):
                index = combo.findData(previous if previous is not None else default)
                combo.setCurrentIndex(
                    index if index >= 0 else (0 if combo.count() else -1)
                )
            self.session.diagnostic = (
                ""
                if self.outputs.count()
                else "No audio devices; check OS audio service"
            )
        except Exception as error:
            self.session.diagnostic = f"Device discovery failed: {error}"
        finally:
            self.inputs.blockSignals(False)
            self.outputs.blockSignals(False)
        self.session.input_device = self.inputs.currentData()
        self.session.output_device = self.outputs.currentData()

    def _devices_changed(self):
        self._stop_all()
        self.session.select_devices(
            self.inputs.currentData(), self.outputs.currentData()
        )

    def _microphone(self):
        if self.session.microphone:
            self.session.stop_microphone()
        else:
            self.session.start_microphone()
        self._tick()

    def _gain_changed(self, value):
        self.session.engine.gain = value / 100
        self.gain_label.setText(f"{value}%")

    def _tone_changed(self, enabled):
        if not self.session.set_tone(enabled):
            self.tone.blockSignals(True)
            self.tone.setChecked(False)
            self.tone.blockSignals(False)
        self._tick()

    def _play(self, kind):
        if self.session.kind == kind:
            self.session.stop_media()
            if kind == "MP4":
                self.video.close()
        else:
            self.video.close()
            self.monitor.setChecked(False)
            if self.session.play(kind, self.paths[kind]) and kind == "MP4":
                self.video.resize(self.width_input.value(), self.height_input.value())
                self.video.show()
        self._tick()

    def _browse(self, kind):
        path, _ = QFileDialog.getOpenFileName(
            self, f"Choose {kind}", str(Path.home()), f"{kind} files (*.{kind.lower()})"
        )
        if path:
            if self.session.kind == kind:
                self.session.stop_media()
                self.video.close()
            self.paths[kind] = Path(path)
            self.file_labels[kind].setText(Path(path).name)
            self.file_labels[kind].setToolTip(path)

    def _reset_sample(self, kind):
        if self.session.kind == kind:
            self.session.stop_media()
            self.video.close()
        filename = "sample-30s.mp3" if kind == "MP3" else "sample-30s-720p.mp4"
        self.paths[kind] = asset_path(filename)
        self.file_labels[kind].setText(filename)

    def _size_changed(self):
        width, height = self.width_input.value(), self.height_input.value()
        save_size(self.settings, width, height)
        if self.video.isVisible():
            self.video.resize(width, height)

    def _manual_resize(self, width, height):
        width, height = max(320, min(3840, width)), max(180, min(2160, height))
        for control, value in ((self.width_input, width), (self.height_input, height)):
            control.blockSignals(True)
            control.setValue(value)
            control.blockSignals(False)
        save_size(self.settings, width, height)

    def _video_closed(self):
        if self.session.kind == "MP4":
            self.session.stop_media()

    def _stop_all(self):
        self.session.stop_all()
        self.video.close()
        if hasattr(self, "tone"):
            self.tone.setChecked(False)

    def _tick(self):
        self.session.poll()
        engine = self.session.engine
        self.input_meter.set_level(engine.input_levels)
        self.output_meter.set_level(engine.output_levels)
        self.start.setText("Stop" if self.session.microphone else "Start")
        self.start.setIcon(
            self.style().standardIcon(
                QStyle.SP_MediaStop if self.session.microphone else QStyle.SP_MediaPlay
            )
        )
        tone_active = engine.tone
        if self.tone.isChecked() != tone_active:
            self.tone.blockSignals(True)
            self.tone.setChecked(tone_active)
            self.tone.blockSignals(False)
        self.tone.setText(
            "TEST TONE ACTIVE · 1 kHz" if tone_active else "Test tone · 1 kHz"
        )
        self.tone.setStyleSheet(
            "color: #b13a20; font-weight: bold;" if tone_active else ""
        )
        source = self.session.source
        for kind in ("MP3", "MP4"):
            active = kind == self.session.kind
            self.buttons[kind].setText(f"Stop {kind}" if active else f"Play {kind}")
            self.buttons[kind].setIcon(
                self.style().standardIcon(
                    QStyle.SP_MediaStop if active else QStyle.SP_MediaPlay
                )
            )
            if active:
                position = source.position
                text = f"Playing · {int(position) // 60}:{position % 60:04.1f} · loops {source.loops}"
                if source.underruns:
                    text += f" · buffer underruns {source.underruns}"
                self.labels[kind].setText(text)
            else:
                self.labels[kind].setText("Stopped · 0:00 · loops 0")
        if self.session.kind == "MP4":
            frame = source.video_frame(engine.latency)
            if frame is not None:
                self.video.show_frame(frame)
        elif self.video.isVisible():
            self.video.close()
        detail = (
            engine.error
            if engine.state == "Error"
            else (engine.warning or self.session.diagnostic)
        )
        mode = ""
        if source and engine.capture:
            mode = " · mic capture on; forwarding " + (
                "on" if engine.monitor else "off"
            )
        message = f"{engine.state} · {engine.rate} Hz · output latency {engine.latency * 1000:.0f} ms{mode}"
        if detail:
            message += " · " + detail
        self.status.setToolTip(message)
        self.status.setText(
            self.status.fontMetrics().elidedText(
                message, Qt.ElideRight, max(200, self.width() - 24)
            )
        )

    def closeEvent(self, event):
        self.timer.stop()
        self._stop_all()
        event.accept()
