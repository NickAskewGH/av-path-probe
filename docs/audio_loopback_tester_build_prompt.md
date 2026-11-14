# Build brief: Cross-platform audio loopback and processing tester

## Your role

Act as a senior Python desktop/audio engineer. Build a small, reliable, cross-platform desktop application from this specification. Deliver working source code, tests, local development instructions, and automated builds for distributable Linux, macOS, and Windows applications. Do not stop at a design proposal or pseudocode.

## Purpose

I am developing a separate tool that injects, captures, or plays audio on computers and connected devices. I need a simple **local audio-path test utility** that lets me confirm that audio presented to a machine's microphone input can be captured, altered in a predictable way, and forwarded to its selected speaker/headphone output. I also need independent, repeatable **MP3 playback** and **MP4 video-with-audio playback**, each looping until explicitly stopped, so that my external tool can test received audio and video playback.

The core path is:

**Selected microphone/input device → observable input level → audio transformation → observable output level → selected speaker/output device.**

The application must run on desktop Linux, macOS, and Windows. It is a test instrument, not a digital audio workstation. Keep it small, dependable, and easy to deploy. The three modes are **microphone processing**, **looped MP3 audio**, and **looped MP4 video + audio**.

## User interface

Create one compact window with:

1. An **Input device** selector, defaulting to the system's default microphone. Include any usable virtual input devices exposed by the OS.
2. An **Output device** selector, defaulting to the system's default playback device.
3. A clearly labelled **Microphone input** live level meter that responds only to received input audio.
4. A clearly labelled **Speaker output (submitted)** live level meter representing the processed samples sent to the playback stream.
5. A prominent **Start / Stop** control. Start must not be automatic on application launch.
6. An **Effect: Modulated / Bypass** selector, defaulting to Modulated.
7. A modest **Output level** control, with a conservative default and clipping protection.
8. An optional **Test tone** toggle (off by default) that emits a low-level 1 kHz signal to validate the output path independently of microphone input. Make it visually obvious when the test tone is active.
9. A single-line status area showing **Stopped / Running / Error**, selected sample rate, and helpful diagnostics for device or permission errors.
10. A **Play MP3 / Stop MP3** toggle button showing playback state and a loop counter. The user can browse for their own MP3 or immediately play the bundled 30-second sample; make the sample the default.
11. A **Play MP4 / Stop MP4** toggle button showing playback state and a loop counter. The user can browse for their own MP4 or play the bundled 30-second sample by default. Video appears in a separate, normal movable/resizable window.
12. **Video width** and **Video height** numeric inputs, defaulting to **960 × 540** logical pixels, applied when opening the video window and changeable at runtime. Validate sensible bounds (for example minimum 320 × 180) and preserve the last setting between runs. Define width/height as the *video content area*, not the OS title bar; account for high-DPI scaling. Preserve the video's aspect ratio by fitting/letterboxing rather than stretching it, even if the chosen dimensions are not 16:9. Allow normal manual resizing as well.

Keep the window practical and uncluttered. Simple horizontal meters updated around 20–30 times per second are sufficient; a waveform graph and elaborate visual styling are unnecessary. Make the meters visibly useful for both quiet and loud signals (e.g. RMS level with a peak indicator). Show clipping or overrun/underrun warnings where available.

**Important measurement distinction:** The output meter proves that the application is producing/submitting audio buffers; it cannot prove that sound physically emerges from a speaker or that a different application/device receives it. Do not describe it as a hardware acoustic measurement. The test tone makes the playback path independently checkable by a human or an external capture tool. Ideally, the speaker output meter must also respond to *actual decoded MP3/MP4 audio samples*; do not fake audio levels based on a playing flag or video position. If distinct backends prevent accurate common PCM metering, label each monitor's coverage explicitly and document the limitation.

## Looped sample-media playback

The media buttons must be useful on an isolated test machine with no network connection. Provide **bundled** sample assets and allow the user to select replacement local files:

| Test asset | Source and required default | Evidence of reuse permission | local source |
| --- | --- | --- | --- |
| `sample-30s.mp3` | 30-second music MP3: https://samplelib.com/mp3/sample-30s.mp3 | Publisher says downloaded files may be used/changed freely: https://samplelib.com/license.html | assets/sample-30s.mp3 |
| `sample-30s-720p.mp4` | 30-second 1280 × 720 H.264/AAC video: https://lorem.space/sample-video/sample-30s-720p.mp4 | Publisher describes generated media usable for tests/demos without attribution: https://lorem.space/sample-video/ | assets/sample-30s-720p.mp4 |

The MP4 is a diagnostic moving-graphics video, not narrative film footage. It has a visible timer/frame counter and a 440 Hz tone that changes to a higher beep each second, so testers can assess picture motion and A/V synchronisation. Its audio track **must** be played, not ignored. Both assets are covered by permissive publisher terms, but do not mislabel them as CC0 or copyright-free. Preserve source URLs, permissions, original file names, and download/checksum information in an asset-provenance document.

- Download the two samples **at development/build preparation time**, verify their formats, duration, actual audio streams, and checksums with appropriate tools (for example FFprobe), then include their bytes with the application installer. Do not hotlink, stream or download them at runtime. If a source becomes unavailable, stop and report the issue instead of substituting unlicensed media.
- **Loop each selected asset indefinitely** until stopped, avoiding duplicate simultaneous player instances, progressive volume accumulation or resource leaks. A short loop-boundary pause may be reported if unavoidable; aim for stable continuous playback. Show current playback time and completed loop count. The MP3 and MP4 buttons are independent from the microphone Start/Stop control, but **only one of the two file players may be active at once**: starting one stops the other cleanly.
- Normal file playback should use the original MP3/MP4 soundtrack **without the microphone tremolo effect**. The microphone effect and file playback are separate test signals.
- Let microphone capture and its *input meter* continue while media is playing. Provide an unambiguous **Monitor microphone into output** setting; default it to **off during media playback** to avoid feedback or accidental mixing, but allow concurrent mic forwarding and media playback when deliberately enabled. Use safe mixing/gain limiting if concurrent playback is supported. Do not block the audio callback.
- Both MP3 and MP4 audio must go to the **currently selected output device**, not silently to a different OS default. If media decoding/playback uses Qt Multimedia while microphone processing uses PortAudio, explicitly map/verify device selection, report unsupported pairings, and avoid opening conflicting streams. A shared output/mixer path is preferable when practical.
- If Qt Multimedia is used for MP4, verify that its codec plugins (especially H.264/AAC and MP3) and media backends work *inside packaged releases* on all three OSes. Do not assume development-machine playback guarantees packaged playback. If a different decoder is needed, justify its size, portability, licensing, and A/V-sync behaviour.
- The video window must display picture and synchronised soundtrack, begin at the chosen size, respond to later size changes, and close cleanly. Closing it should stop MP4 playback and release the video/audio resources. A missing or invalid video, unsupported codec, or missing audio stream should produce a clear diagnostic.
- Keep controls simple: provide distinct media Play/Stop buttons, a global Stop All (or an equally obvious stop behaviour), and current playback labels. No playlists, media library, seeking timeline, or editing functionality is needed.

## Audio processing behaviour

- Use full-duplex, continuous, low-latency streaming for simultaneous capture and playback; avoid a record-then-play design.
- Support ordinary mono microphone input and stereo playback, duplicating mono input to both stereo channels as appropriate. Handle other supported channel layouts explicitly rather than crashing.
- Use `float32` audio buffers and NumPy-based processing.
- **Default transformation:** apply safe attenuation plus an obvious, deterministic **8 Hz tremolo** to the incoming signal. The result should remain recognisably related to the source, but audibly and measurably different. For example, a continuously phased amplitude envelope `0.65 + 0.35 * sin(2π * 8 * t)` with additional conservative output gain. Preserve phase continuity between audio callback blocks.
- The **Bypass** mode must allow A/B comparison of unmodulated and modulated routing, while retaining safety gain limiting.
- Do not generate any microphone-derived output from silent input (apart from an explicitly enabled test tone). A static test tone must not be mistaken for proof of microphone capture.
- Bound samples to a safe output range, avoid NaNs and clipping, and handle gain changes without audible clicks if reasonably achievable.
- Prefer 48 kHz when supported, but negotiate a compatible stream format and report unsupported device combinations clearly. Do not silently assume every input/output device pair supports the same host API, channel count, or sample rate.
- Aim for responsive monitoring (approximately 50–150 ms end-to-end where hardware permits), but do not claim a fixed latency guarantee across devices and operating systems. Report the stream's configured/estimated latency if available.
- Do not block the real-time audio callback with GUI operations, disk access, logs, network calls, allocations of large buffers, or expensive DSP. Use a safe low-contention path for passing level/status measurements to the GUI.
- Support clean start, stop, close, repeated restarts, and unplugged/invalid devices without freezing or leaving an audio stream running. Changing devices while running may trigger a controlled stop/restart.
- Safely deal with stream underflow/overflow and recover gracefully where feasible. If a full-duplex stream cannot be opened for a selected device pair, present a useful error and suggest choosing compatible devices; do not implement a complicated asynchronous resampling engine unless truly needed.

## Preferred implementation

- Python 3.11+ with a single maintainable project and a standard `pyproject.toml`.
- `sounddevice`/PortAudio for portable audio I/O, NumPy for DSP, and PySide6 for a basic native-feeling Qt window. You may substitute a library only with a concrete cross-platform or packaging justification.
- Keep the code separated into a small audio engine, deterministic DSP functions, device discovery/validation, the GUI, and application startup. Avoid needless abstractions or a large framework.
- Keep audio entirely local: **no servers, cloud services, network telemetry, recording, or persistent captured audio**.
- The bundled sample media may be stored locally as application resources; this is not permission to record user audio. Use standard local file dialogs for user-provided MP3/MP4 files.
- Use understandable defaults and clearly surfaced errors for microphone permission denial, missing devices, unsupported sample rates, PortAudio initialization, and hot-unplug scenarios.
- On macOS include an `NSMicrophoneUsageDescription` in the packaged application's `Info.plist` and test the permission flow. Provide equivalent OS-specific troubleshooting notes for Windows microphone privacy settings and Linux PipeWire/PulseAudio/ALSA.
- Include a concise explanation of how to use a virtual microphone or virtual audio routing device when the external testing tool exposes one, but do not require third-party virtual cable software for basic operation.
- Keep third-party dependencies minimal and pin/lock versions used in releases.

## Packaging and deployment

Deliver the source project and an automated build workflow (preferably GitHub Actions) that builds **natively on each target OS**, using PyInstaller and any necessary platform packagers:

| OS | Expected release artifact |
| --- | --- |
| Windows | Installer `.exe`, preferably via Inno Setup, containing a runnable bundled application |
| macOS | `.app` inside a convenient `.dmg`; document Apple Silicon/Intel architecture coverage |
| Linux | AppImage or an installable `.deb`, plus clear compatibility notes if needed |

The release artifact should include the Python runtime and application dependencies as far as technically practical. Ordinary end users must not have to install Python, create a virtual environment, or run `pip`. Where Linux distribution system libraries remain prerequisites, document them precisely. Prefer reliable bundled/on-disk builds over a fragile single-file executable.

Provide:

- A reproducible local development setup and run command, ideally using `uv` (or equally simple tooling).
- A PyInstaller spec/configuration and platform-specific build commands/scripts.
- Build scripts and packaging configuration that include the actual bundled MP3 and MP4 resources and required multimedia decoder/backend plugins, with file lookup working both from source and in packaged applications.
- CI workflows that run unit tests and produce downloadable artifacts for Linux, macOS, and Windows; publish tagged releases if practical.
- Instructions for running the package on a clean machine.
- A brief, honest statement about unsigned installers, Windows SmartScreen, macOS Gatekeeper, and the separate credentials/process needed for code signing or notarization. Do not present unsigned software as fully frictionless to install.
- A short license/dependency acknowledgement appropriate to bundled third-party components.

## Tests and verification

Automate tests that do **not** require real audio devices:

1. Silence in → silence out when the test tone is off.
2. A known synthetic sine-wave input produces the expected attenuated/tremolo-modulated output, with block-to-block phase continuity.
3. Bypass produces an unmodulated result within the defined safe gain envelope.
4. No NaN/Inf, unexpected channel shape, or out-of-range sample values for ordinary and boundary inputs.
5. RMS/peak meter calculations are correct for silence, a known test signal, and clipping conditions.
6. Audio stream state transitions (start/stop/restart/error) remain predictable, using a mock backend where useful.
7. MP3 and MP4 players start, stop, reach end-of-media, restart without duplicate instances, and maintain correct loop counts using mocked or temporary synthetic files where feasible.
8. The selected output device is honoured in all three modes, including when a media file is played after changing device selection. Validate the expected output metering behaviour.
9. Video width/height settings are validated/persisted, and aspect-fit calculation works for both matching and nonmatching window aspect ratios.

Also provide a **manual smoke-test checklist**, to be performed on each OS:

- Launch packaged app, select microphone and speakers, and confirm permissions.
- Start with headphones (to avoid acoustic feedback) and speak or inject test audio. Confirm the input meter moves.
- Confirm the output meter moves and externally observe the transformed signal on the selected output.
- Switch between Modulated and Bypass and verify an audible or measurable difference.
- Check Test tone with no microphone activity; ensure only the output meter moves, and turning the tone off restores silence if the input is silent.
- Stop and restart several times; disconnect a device while active and confirm helpful recovery/error handling.
- Run for at least 10 minutes without the GUI freezing or the audio path leaking resources.
- Play the **bundled MP3** through at least three complete 30-second loops; check the output meter and stop button. Confirm the microphone input meter remains independent.
- Play the **bundled MP4** through at least three complete 30-second loops; verify both picture and audible once-per-second beeps, no obvious A/V drift, and clean stop/restart.
- Open video at **640 × 360** and **1024 × 768** content sizes, verify that resizing works and that 16:9 video is letterboxed rather than distorted at 4:3. Closing the video window must stop its audio.
- Test switching from MP3 to MP4 and back, selecting another output device, and deliberately enabling concurrent mic forwarding to check mixing and volume safety.

Do not imply that a green CI build proves actual physical audio playback. Clearly distinguish automated DSP/unit tests, packaging smoke tests, and hardware-in-the-loop manual verification.

## Definition of done / response expected

1. Create the **complete runnable repository**, not just explanations or illustrative fragments.
2. Show a brief project tree and the exact commands to install dependencies, run tests, launch the app, and build each platform package.
3. Provide all source code, packaging definitions, CI configuration, and a practical README.
4. Run the relevant lightweight tests and report results honestly. If you cannot run audio hardware tests or native builds for a given OS, mark them **not verified**, not passed.
5. Explain any intentional deviations from this specification and any unavoidable cross-platform limitations.
6. Prioritise a reliable, working MVP over optional features. Do not add recording, waveform editors, networking, accounts, analytics, a plugin architecture, or other unrelated capabilities.

**Final user experience:** install the application, choose microphone and speaker devices, and either (a) click Start to watch microphone input activity and hear/capture an unmistakably modified version of incoming audio, (b) click Play MP3 to loop a known 30-second music sample through the chosen speakers, or (c) click Play MP4 to loop a known 30-second audiovisual test clip in a window of user-chosen dimensions. All must work offline from a packaged application.
