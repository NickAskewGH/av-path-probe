import importlib.metadata
from pathlib import Path

from PyInstaller.compat import is_darwin
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

root = Path(SPECPATH).parent
datas = [
    (str(root / "assets" / "sample-30s.mp3"), "audio_loopback/assets"),
    (str(root / "assets" / "sample-30s-720p.mp4"), "audio_loopback/assets"),
    (str(root / "docs" / "asset-provenance.md"), "notices"),
    (str(root / "docs" / "third-party.md"), "notices"),
]
av_datas, av_binaries, av_imports = collect_all("av")
datas += av_datas + collect_data_files("numpy")
for name in ("av", "numpy", "PySide6", "shiboken6", "sounddevice", "cffi", "pyinstaller"):
    distribution = importlib.metadata.distribution(name)
    for entry in distribution.files or []:
        if "license" in str(entry).lower() and distribution.locate_file(entry).is_file():
            datas.append((str(distribution.locate_file(entry)), f"notices/{name}/{entry.parent}"))
binaries = av_binaries + collect_dynamic_libs("sounddevice")
for directory in ("av.libs", "av/.dylibs", "av.libs/.dylibs", "_sounddevice_data"):
    dependency_dir = Path(importlib.metadata.distribution("av").locate_file(directory))
    if dependency_dir.is_dir():
        datas.append((str(dependency_dir), directory))

analysis = Analysis(
    [str(root / "packaging" / "launcher.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=av_imports + ["_sounddevice", "_cffi_backend"],
    excludes=["PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "tkinter"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True,
    name="AudioLoopbackTester", debug=False, strip=False, upx=False, console=False,
)
bundle = COLLECT(executable, analysis.binaries, analysis.datas,
                 strip=False, upx=False, name="AudioLoopbackTester")
if is_darwin:
    app = BUNDLE(
        bundle, name="AudioLoopbackTester.app", bundle_identifier="local.audio.loopbacktester",
        info_plist={
            "CFBundleShortVersionString": "0.1.0",
            "NSMicrophoneUsageDescription": "Capture local microphone audio for audio-path testing.",
            "NSHighResolutionCapable": True,
        },
    )