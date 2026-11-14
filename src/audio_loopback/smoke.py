import json
import time
from pathlib import Path

import av
import numpy as np
from PySide6.QtCore import QSettings

from .gui import MainWindow
from .media import MediaSource, asset_path


def run_smoke(application, report_path):
    report_path = Path(report_path).resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "hardware_playback": "NOT VERIFIED",
        "pyav": av.__version__,
        "ffmpeg": {key: list(value) for key, value in av.library_versions.items()},
    }
    window = None
    try:
        window = MainWindow(
            settings=QSettings(
                str(report_path.with_suffix(".ini")), QSettings.IniFormat
            ),
            device_discovery=lambda: ([], (-1, -1)),
        )
        window.timer.stop()
        window.show()
        application.processEvents()
        window.grab().save(str(report_path.with_suffix(".png")))
        for filename, video in (
            ("sample-30s.mp3", False),
            ("sample-30s-720p.mp4", True),
        ):
            source = MediaSource(asset_path(filename), 48000, 2, video)
            source.start()
            try:
                if not source.ready.wait(10) or source.error:
                    raise RuntimeError(source.error or "Decoder startup timed out")
                output = np.empty((512, 2), np.float32)
                peak = 0.0
                picture = None
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    source.read_into(output)
                    peak = max(peak, float(np.max(np.abs(output))))
                    if video:
                        picture = source.video_frame() or picture
                    if peak > 0 and (not video or picture is not None):
                        break
                    source.cancel.wait(0.002)
                if peak == 0 or (video and picture is None):
                    raise RuntimeError(f"No decoded audio/video from {filename}")
                if video:
                    window.video.resize(1024, 768)
                    window.video.show_frame(picture)
                    window.video.show()
                    application.processEvents()
                    image = window.video.grab().toImage()
                    if image.pixelColor(10, 10).value() != 0:
                        raise RuntimeError("Video aspect-fit smoke check failed")
                    content = [
                        image.pixelColor(horizontal, vertical).value()
                        for horizontal in range(64, 1024, 64)
                        for vertical in range(128, 640, 64)
                    ]
                    if max(content) < 20:
                        raise RuntimeError("Packaged video rendered blank")
                    image.save(
                        str(report_path.with_name(report_path.stem + "-video.png"))
                    )
                report[filename] = {
                    "decoded_peak": peak,
                    "duration": source.duration,
                    "video_frame": picture is not None,
                }
            finally:
                source.stop()
        report["result"] = "PASS (decoder and Qt only)"
        result = 0
    except Exception as error:
        report["result"] = "FAIL"
        report["error"] = str(error)
        result = 1
    finally:
        if window:
            window.close()
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return result
