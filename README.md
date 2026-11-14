# Audio Loopback Tester

A local desktop instrument for microphone processing and independently looping
MP3 or MP4 playback. Python, NumPy, sounddevice/PortAudio, PyAV/FFmpeg, and
PySide6. No recording, server, telemetry, or runtime downloads.

## Develop

Install [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/).
Python 3.12+ is supported; release builds use 3.12. The existing project minimum
is retained rather than lowered to the brief's preferred 3.11.

```sh
uv sync --locked
just assets
just test
just check
just run
```

Without just: `uv run --locked pytest -q` and
`uv run --locked audio-loopback-tester`.
Use `just format` for formatting; `uv add` / `uv add --dev` to change dependencies.
Commit both `pyproject.toml` and `uv.lock`.

On Debian/Ubuntu install desktop prerequisites before source development:

```sh
sudo apt-get install libportaudio2 libasound2 libxcb-cursor0 libxkbcommon-x11-0 \
	libegl1 libgl1 libdbus-1-3 libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
	libxcb-render-util0 libxcb-xinerama0 libxcb-xkb1 libglib2.0-0
```

For headless checks: `QT_QPA_PLATFORM=offscreen just smoke` on Linux/macOS;
in PowerShell set `$env:QT_QPA_PLATFORM="offscreen"` first.

## Use

1. Connect headphones first to prevent acoustic feedback. Select input and
	 output devices, including OS-exposed virtual inputs if appropriate.
2. Click **Start** to capture/forward microphone audio. The default is 8 Hz
	 tremolo with 20% output gain. Bypass retains the safety gain. Stop disables
	 microphone forwarding independently of file playback.
3. Test tone explicitly enables a low-level 1 kHz output signal, even without
	 a microphone session; it never drives the microphone input meter itself.
4. Play MP3 or MP4 to loop the bundled 30-second samples offline, or browse
	 for a replacement local file. Starting a file stops the other file player.
	 MP4 opens a normal movable, resizable video window; closing it stops MP4.
5. Input capture/metering continues during media playback where the microphone
	 can be opened, even when the microphone Start control is off. Forwarding
	 during media is **off by default**. To mix deliberately, click Start and
	 enable **Monitor microphone into output during media**. Starting a new file
	 resets this opt-in. Stop All releases streams and decoders.
6. Video width/height are logical-pixel **content area** dimensions, not window
	 decorations. Defaults are 960 x 540, bounds 320–3840 x 180–2160. Changes
	 apply live; manual resizing is persisted too. Qt performs high-DPI mapping;
	 picture is aspect-fitted with black letterboxing, never stretched.

The microphone meter measures received input; the speaker meter measures the
actual limited PCM submitted for **microphone, tone, and decoded media combined**.
It is not a hardware/acoustic measurement and cannot prove a device played sound.
Meters show logarithmic RMS (-60 to 0 dBFS) and a peak marker. Red/limit indicators
flag the safety ceiling; callback over/underruns appear in status. Long status
diagnostics are elided on screen with the full message in the hover tooltip.

## Audio And Playback Limits

- One full-duplex float32 stream with mono capture and mono/stereo output;
	devices with more channels explicitly use the first input and first two outputs.
- Prefer 48 kHz, then 44.1 kHz, then the output default. Input/output must have a
	common rate and host API. Unsupported pairs produce an error instead of an
	asynchronous capture resampler. If media can run but input cannot, file
	playback falls back to output-only and clearly reports unavailable input.
- DSP phase is continuous across 512-frame blocks, gain ramps over each block,
	and a final +/-0.9 safety limiter protects mixed output. Silent input produces
	no microphone-derived output. File soundtracks bypass tremolo.
- File decoding/resampling is on one cancellable worker. Eight queued audio
	chunks and 24 timestamped video frames bound buffering. The callback does no
	GUI work, disk I/O, logging, or decoding. It performs small NumPy operations
	and nonblocking queue reads; Python/PortAudio is not hard real-time.
- Video follows consumed audio samples, offset by configured output latency.
	Late pictures may be dropped. EOF reopens the same file with fresh codec state;
	brief loop-boundary silence or device-dependent A/V jitter may occur. No
	fixed end-to-end latency or perfect gaplessness is claimed.
- Status latency is PortAudio's estimated **output** latency, not a measured
	round-trip delay. Target responsive monitoring, typically around 50–150 ms
	where hardware allows. Device changes stop all modes safely; restart explicitly.
- Preferences persist only video dimensions. Captured audio is never persisted.

## Build Installers

Run **on the target OS**, not by cross-compiling:

```sh
uv sync --locked --group build
just build
```

Equivalent on every OS:
`uv run --locked --group build python scripts/build_release.py`.
`just bundle` builds only the on-disk PyInstaller application. Both commands run
the bundled codec/Qt smoke test before producing an installer.

| Native host | Prerequisites | Output in `dist/installers/` |
| --- | --- | --- |
| Linux x86_64 | runtime libraries above, `dpkg-deb` | `AudioLoopbackTester-linux-amd64.deb` |
| macOS | Xcode command-line tools, `hdiutil` | `AudioLoopbackTester-macos-arm64.dmg` or `-x86_64.dmg` |
| Windows x64 | Inno Setup 6 (`ISCC` in PATH or standard install directory) | `AudioLoopbackTester-windows-x64.exe` |

The CI workflow builds Ubuntu 22.04 x86_64, Windows x64, and separate macOS
Apple Silicon and Intel artifacts, runs tests and packaged smoke checks, and
uploads installers/screenshots/reports. `v*` tags publish a release after all
native jobs succeed. ARM Linux/Windows and universal macOS bundles are not provided.
The local Linux build inherits this host's glibc floor; use the Ubuntu 22.04 CI
artifact for the documented Ubuntu 22.04+/Debian 12+ baseline, pending clean
machine verification. Older Linux distributions may not load the bundled Qt,
NumPy, or FFmpeg binaries. Users still need a working OS audio service/session.

PyInstaller's on-disk layout includes Python, NumPy, Qt Widgets/platform plugins,
PyAV/FFmpeg shared libraries, Windows/macOS PortAudio, sample bytes, and notices.
Linux uses distribution PortAudio/ALSA and the declared system libraries.
No separate Python, pip, codec pack, or media download is needed by end users.

## Clean-Machine Installation

- Linux: `sudo apt install ./AudioLoopbackTester-linux-amd64.deb`; launch from
	the desktop menu or `/opt/audio-loopback-tester/AudioLoopbackTester`.
- Windows: run the installer and launch from its Start menu entry. Unsigned
	downloads may show SmartScreen warnings; confirm source/hash with the publisher.
- macOS: mount the architecture-matching DMG and drag the app to Applications.
	Unsigned apps may be blocked by Gatekeeper; use the OS's approved Open/Privacy
	& Security override only after confirming provenance. Enterprise policy may
	forbid an override. Developer ID signing and Apple notarization require
	separately managed credentials and CI steps, not included here. Windows
	Authenticode signing similarly requires a certificate/service.

Packaging alone is not redistribution license clearance. See
[dependency notices](docs/third-party.md) and [media provenance](docs/asset-provenance.md).

## Permissions And Routing

- macOS: allow microphone access for the application (or Terminal/Python during
	development) under System Settings > Privacy & Security > Microphone. The
	app bundle contains `NSMicrophoneUsageDescription`. Quit/relaunch after changing
	permission. Permission prompting must still be checked on a clean Mac.
- Windows: enable Settings > Privacy & security > Microphone, including desktop
	app access. Pick input/output entries from the same host API (e.g. both WASAPI).
	Check disabled devices and exclusive-mode conflicts if opening fails.
- Linux: confirm PipeWire/PulseAudio/ALSA is running in the logged-in desktop
	session, input is unmuted, and the default ALSA/PortAudio mapping routes to it.
	Prefer paired devices from the same API. Hardware ALSA devices may be busy
	while PipeWire is using them; select its default/virtual route instead.
- A virtual microphone exposed by an external tool appears in Input device like
	a physical microphone. Route the external signal into it, select it here, and
	choose the desired output/capture endpoint. No virtual cable is required for
	ordinary microphone/headphone testing. This app does not create virtual devices.
- Refresh devices after plugging/unplugging. On a stream error the app stops
	cleanly and keeps the diagnostic; reconnect, refresh, and start again.

## Repository

```text
src/audio_loopback/   app, GUI, DSP, devices, stream engine, media decoder, session
tests/               hardware-free DSP, mocked routing, decoder and offscreen Qt
assets/              two pinned bundled samples (plus unbundled user media)
packaging/           PyInstaller spec, entry point, Inno Setup configuration
scripts/             asset verification and native release build
.github/workflows/   tests, native installers, tagged releases
docs/                brief, provenance, dependencies, manual smoke checklist
```

Automated tests do not prove physical playback. Package smoke checks verify
bundled sample lookup, actual MP3/AAC/H.264 decoding, and nonblank letterboxed Qt
rendering, without audio hardware. Follow the
[per-OS manual checklist](docs/manual-smoke-test.md) before releasing.