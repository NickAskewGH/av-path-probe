import argparse
import hashlib
import json
import tempfile
import urllib.request
from pathlib import Path

import av

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = {
    "sample-30s.mp3": (
        "https://samplelib.com/mp3/sample-30s.mp3",
        "e8728a58a5c169ff2b0330d7c8963be831fa2ad9185b1d0adf9d48b547987d53",
    ),
    "sample-30s-720p.mp4": (
        "https://lorem.space/sample-video/sample-30s-720p.mp4",
        "c9b332456e1358eb2d29bdc62180e123cf2d8497eb8ff8dd3f190d4d8bf4f63b",
    ),
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify(path, expected):
    if digest(path) != expected:
        raise RuntimeError(
            f"Checksum changed: {path.name}; review publisher/source before updating"
        )
    with av.open(str(path)) as container:
        duration = float(container.duration or 0) / av.time_base
        if not 29.9 < duration < 30.1 or not container.streams.audio:
            raise RuntimeError(f"Invalid duration or missing soundtrack: {path.name}")
        audio = container.streams.audio[0]
        if path.suffix == ".mp3" and audio.codec_context.name != "mp3float":
            if audio.codec_context.name != "mp3":
                raise RuntimeError("Expected MP3 audio")
        if path.suffix == ".mp4":
            if not container.streams.video:
                raise RuntimeError("MP4 is missing video")
            video = container.streams.video[0]
            if (
                video.codec_context.name,
                video.width,
                video.height,
                audio.codec_context.name,
            ) != ("h264", 1280, 720, "aac"):
                raise RuntimeError("Expected 1280×720 H.264/AAC MP4")
        for frame in container.decode(audio=0):
            if frame.samples:
                break
        else:
            raise RuntimeError("No actual decodable soundtrack samples")
        return {
            "filename": path.name,
            "bytes": path.stat().st_size,
            "sha256": expected,
            "duration_seconds": duration,
            "audio_codec": audio.codec_context.name,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Prepare verified offline sample media"
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download missing samples only; never overwrite existing assets",
    )
    parser.add_argument(
        "--verify-remote",
        action="store_true",
        help="Download publishers' bytes to temporary files and compare hashes",
    )
    options = parser.parse_args()
    reports = []
    for filename, (url, expected) in SAMPLES.items():
        target = ROOT / "assets" / filename
        if options.verify_remote or (options.download and not target.exists()):
            with tempfile.TemporaryDirectory() as folder:
                downloaded = Path(folder) / filename
                request = urllib.request.Request(
                    url, headers={"User-Agent": "AudioLoopback-build/0.1"}
                )
                with (
                    urllib.request.urlopen(request, timeout=30) as response,
                    downloaded.open("wb") as output,
                ):
                    while chunk := response.read(1024 * 1024):
                        output.write(chunk)
                verify(downloaded, expected)
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(downloaded.read_bytes())
        reports.append(verify(target, expected) | {"source": url})
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()
