import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments, **options):
    subprocess.run(
        [str(argument) for argument in arguments], cwd=ROOT, check=True, **options
    )


def main():
    parser = argparse.ArgumentParser(
        description="Build a native installer on the current OS"
    )
    parser.add_argument("--bundle-only", action="store_true")
    options = parser.parse_args()
    run(sys.executable, ROOT / "scripts" / "prepare_assets.py")
    run(
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        ROOT / "packaging" / "audio-loopback.spec",
    )
    system = platform.system()
    if system == "Darwin":
        executable = (
            ROOT
            / "dist"
            / "AudioLoopbackTester.app"
            / "Contents"
            / "MacOS"
            / "AudioLoopbackTester"
        )
    else:
        executable = (
            ROOT
            / "dist"
            / "AudioLoopbackTester"
            / (
                "AudioLoopbackTester.exe"
                if system == "Windows"
                else "AudioLoopbackTester"
            )
        )
    report = ROOT / "dist" / "package-smoke.json"
    import os

    environment = os.environ.copy()
    environment["QT_QPA_PLATFORM"] = "offscreen"
    run(executable, "--smoke-test", report, env=environment)
    if (
        json.loads(report.read_text(encoding="utf-8"))["result"]
        != "PASS (decoder and Qt only)"
    ):
        raise RuntimeError("Packaged decoder/Qt smoke test failed")
    if options.bundle_only:
        return
    installers = ROOT / "dist" / "installers"
    installers.mkdir(exist_ok=True)
    if system == "Windows":
        compiler = shutil.which("ISCC") or str(
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))
            / "Inno Setup 6"
            / "ISCC.exe"
        )
        run(compiler, ROOT / "packaging" / "windows.iss")
    elif system == "Darwin":
        staging = ROOT / "build" / "dmg"
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True)
        shutil.copytree(
            ROOT / "dist" / "AudioLoopbackTester.app",
            staging / "AudioLoopbackTester.app",
            symlinks=True,
        )
        (staging / "Applications").symlink_to("/Applications")
        run(
            "hdiutil",
            "create",
            "-volname",
            "Audio Loopback Tester",
            "-srcfolder",
            staging,
            "-ov",
            "-format",
            "UDZO",
            installers / f"AudioLoopbackTester-macos-{platform.machine()}.dmg",
        )
    elif system == "Linux":
        package = ROOT / "build" / "deb"
        if package.exists():
            shutil.rmtree(package)
        app_dir = package / "opt" / "audio-loopback-tester"
        shutil.copytree(ROOT / "dist" / "AudioLoopbackTester", app_dir)
        control = package / "DEBIAN"
        control.mkdir()
        (control / "control").write_text(
            "Package: audio-loopback-tester\nVersion: 0.1.0\nSection: sound\nPriority: optional\n"
            "Architecture: amd64\nMaintainer: Audio Loopback Tester contributors\n"
            "Depends: libportaudio2, libasound2, libxcb-cursor0, libxkbcommon-x11-0, libegl1, "
            "libgl1, libdbus-1-3, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, "
            "libxcb-render-util0, libxcb-xinerama0, libxcb-xkb1, libglib2.0-0\n"
            "Description: Local microphone processing and looping audio/video test instrument\n",
            encoding="utf-8",
        )
        desktop_dir = package / "usr" / "share" / "applications"
        desktop_dir.mkdir(parents=True)
        (desktop_dir / "audio-loopback-tester.desktop").write_text(
            "[Desktop Entry]\nType=Application\nName=Audio Loopback Tester\n"
            "Exec=/opt/audio-loopback-tester/AudioLoopbackTester\nTerminal=false\n"
            "Categories=AudioVideo;Audio;\n",
            encoding="utf-8",
        )
        run(
            "dpkg-deb",
            "--root-owner-group",
            "--build",
            package,
            installers / "AudioLoopbackTester-linux-amd64.deb",
        )
    else:
        raise RuntimeError(f"Unsupported release OS: {system}")


if __name__ == "__main__":
    main()
