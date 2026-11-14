# Hardware And Installer Smoke Checklist

Run on a clean Linux, Windows, and macOS desktop using the native packaged
artifact. Record OS/version, CPU architecture, artifact SHA-256, audio devices,
host APIs, sample rate, estimated output latency, observations, and PASS/FAIL.
No hardware checks have been performed by automated CI or offscreen tests.

1. Install without Python or codec packs. Launch via desktop/Start menu/Finder.
   Confirm macOS microphone prompt and Windows privacy permissions. App starts
   stopped with tone off; both bundled media files work with network disconnected.
2. Wear headphones. Choose input/output from the same host API. Start and speak
   or inject a known signal. Input meter responds only to incoming samples.
3. Observe output meter and independently capture/listen to the transformed
   signal at the selected output. A submitted-buffer meter is not acoustic proof.
4. Switch Modulated/Bypass. Confirm obvious 8 Hz tremolo versus unmodulated,
   conservatively attenuated output; gain changes should not click badly.
5. With silent input, toggle tone. Output alone moves, unless acoustic feedback
   reaches the mic. Disable tone and confirm output returns to silence.
6. Stop/restart repeatedly. Disconnect an active device. Expect a helpful
   diagnostic and released stream; reconnect, refresh, and restart. Close the
   app while active and confirm no residual playback or decoder processes.
7. Run microphone processing for at least ten minutes; watch CPU/memory and
   meters, with no frozen GUI or progressive resource growth. Note overruns.
8. Play bundled MP3 for at least three complete loops (about 90 seconds). Confirm
   selected output, real output meter activity, time/loop count, and clean stop.
   Input meter should still respond independently; default mic forwarding is off.
9. Play bundled MP4 for at least three loops. Confirm moving graphics, timer,
   once-per-second audible higher beep, no obvious progressive A/V drift, and
   stable CPU/memory. Note any loop-boundary gap; stop/restart several times.
10. Open video at 640 x 360 and 1024 x 768 **content** sizes. At 4:3 verify
    top/bottom black letterboxing, not stretching. Change spinboxes while playing,
    manually resize/move, and check preferences survive application restart.
    Repeat on a high-DPI display; logical size need not equal physical pixels.
11. Close the video window and confirm its audio stops immediately. Start MP4
    again with no duplicate window, then alternate MP3/MP4: never two file players.
12. Change output while a mode is active: all modes stop deliberately. Restart
    MP3, MP4, and mic in turn; confirm all audio uses the newly selected device.
13. During media, click Start and explicitly enable microphone monitoring.
    Verify safe mixed audio and independent input metering; Stop only mic,
    keeping file playback. Starting another file resets media mic monitoring off.
14. Try invalid files, a video without soundtrack, missing/unplugged devices,
    unsupported device pairs, and permission denial. Confirm clear error state,
    clean resource release, and recovery without relaunch where OS allows it.
15. Check unsigned installer warnings and uninstall. Perform the same tests on
    BOTH macOS architectures before claiming architecture coverage.

Keep packaged decoder/Qt smoke reports separate from this hardware record.
Record unperformed steps as **NOT VERIFIED**, not passed.