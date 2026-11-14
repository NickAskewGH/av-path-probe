# Bundled Asset Provenance

Only the two files below are shipped. The additional local
`assets/picture-this-hear-that.mp3` is user-owned workspace content and is not
included in builds or assigned a license by this project.

## sample-30s.mp3

- Original file name: `sample-30s.mp3`.
- Source: https://samplelib.com/mp3/sample-30s.mp3
- Permission: https://samplelib.com/license.html
- Publisher statement checked 2026-11-14: after downloading, users may change,
  supplement, and use the files as they like; provided AS IS without guarantees.
- Local file supplied before implementation; bytes checked against the publisher
  by `scripts/prepare_assets.py --verify-remote` during development preparation.
- SHA-256: `e8728a58a5c169ff2b0330d7c8963be831fa2ad9185b1d0adf9d48b547987d53`.
- Size: 480697 bytes. FFprobe duration: 30.014694 seconds (MP3 encoder padding).
- Stream: MP3, 44100 Hz, stereo, approximately 128 kbit/s.

## sample-30s-720p.mp4

- Original file name: `sample-30s-720p.mp4`.
- Source: https://lorem.space/sample-video/sample-30s-720p.mp4
- Permission/context: https://lorem.space/sample-video/
- Publisher describes generated moving graphics, timer/frame counter, and a
  440 Hz tone with a higher beep each second, usable for tests/demos without
  attribution. These are permissive publisher terms, not a CC0 declaration.
- Local file supplied before implementation; bytes checked against the publisher
  by `scripts/prepare_assets.py --verify-remote` during development preparation.
- SHA-256: `c9b332456e1358eb2d29bdc62180e123cf2d8497eb8ff8dd3f190d4d8bf4f63b`.
- Size: 2776504 bytes. FFprobe duration: 30.000000 seconds.
- Video: H.264 High profile, 1280 x 720, 30 fps, 900 frames.
- Audio: AAC LC, mono, 48000 Hz, 30 seconds, approximately 98 kbit/s.

## Preparation And Verification

`uv run python scripts/prepare_assets.py --download` downloads only missing
files, verifies SHA-256, duration, codecs, and actual decodable audio, and stops
on errors. `--verify-remote` checks a fresh temporary download against the pinned
hashes. No substitution or runtime networking is implemented. Re-review sources
and permissions before deliberately changing a hash. Build preparation checks
existing local bytes and fails if they are missing or changed.

Neither file is labelled copyright-free. Retain this document with installers.