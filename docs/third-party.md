# Third-Party Components

Release versions are pinned by `uv.lock`; do not ship an unlocked resolution.
PyInstaller copies available distribution license files into the bundle's
`notices` directory, alongside this document and media provenance.

| Component | Upstream and license family |
| --- | --- |
| Python | https://www.python.org/ - PSF license |
| NumPy | https://numpy.org/ - BSD-3-Clause; wheel dependencies have additional notices |
| sounddevice | https://python-sounddevice.readthedocs.io/ - MIT |
| PortAudio | https://www.portaudio.com/ - permissive PortAudio license |
| PySide6 / Shiboken / Qt | https://www.qt.io/qt-for-python - LGPLv3/GPLv3/commercial, module-dependent |
| PyAV | https://pyav.org/ - BSD-3-Clause |
| FFmpeg and codec dependencies | https://ffmpeg.org/legal.html - build-dependent LGPL/GPL and third-party terms |
| CFFI | https://cffi.readthedocs.io/ - MIT |
| PyInstaller | https://pyinstaller.org/ - GPL with bootloader distribution exception |

PyAV is deliberately used instead of Qt Multimedia: it provides actual decoded
PCM for metering and one selected PortAudio output, with resampling off the
callback. Its binary wheels bundle FFmpeg and are larger than a codec-free GUI;
this avoids depending on an end user's separately installed codec plugins.
Qt Multimedia is excluded. Video is painted through Qt Widgets, timestamped
against consumed audio samples, compensated by configured output latency. A
short decode/queue boundary gap and dropped late video frames are possible.

FFmpeg wheel license/configuration varies by OS/version. The Linux development
wheel is PyAV 16.1.0 with FFmpeg 8 libraries; its configuration includes shared
libraries, version3, x264/x265 and other codec dependencies. Inspect the shipped
libraries' `avcodec_license()` and `avcodec_configuration()` and review wheel
notices on EVERY release platform; do not infer LGPL-only from PyAV's BSD
license. Source/build references: https://github.com/PyAV/PyAV and
https://github.com/PyAV/av-wheels. Release distributors must meet the actual
binary licenses, provide corresponding source/build information or offers as
required, preserve notices, and allow LGPL library replacement/relinking.
The on-disk build keeps dynamic libraries replaceable. Codec patent obligations
may vary by jurisdiction; no patent clearance is asserted.

This acknowledgement is not legal advice and does not replace a release
license audit. No license for the application's original code is imposed here;
the repository owner should choose one before external redistribution.