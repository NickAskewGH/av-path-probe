from dataclasses import dataclass

import sounddevice as sd


@dataclass(frozen=True)
class Device:
    index: int
    name: str
    hostapi: int
    inputs: int
    outputs: int
    rate: float


def discover(backend=sd):
    apis = backend.query_hostapis()
    devices = [
        Device(
            index,
            f"{info['name']} ({apis[info['hostapi']]['name']})",
            info["hostapi"],
            info["max_input_channels"],
            info["max_output_channels"],
            info["default_samplerate"],
        )
        for index, info in enumerate(backend.query_devices())
    ]
    defaults = tuple(backend.default.device)
    return devices, defaults


def negotiate(input_device, output_device, capture, backend=sd, fixed_rate=None):
    if output_device is None or output_device < 0:
        raise ValueError("No output device. Connect or select speakers/headphones.")
    output = backend.query_devices(output_device)
    channels = min(2, output["max_output_channels"])
    if channels < 1:
        raise ValueError("Selected device has no playback channels")
    incoming = None
    if capture:
        if input_device is None or input_device < 0:
            raise ValueError("No microphone. Select an input or check OS permissions.")
        incoming = backend.query_devices(input_device)
        if incoming["max_input_channels"] < 1:
            raise ValueError("Selected device has no microphone channels")
        if incoming["hostapi"] != output["hostapi"]:
            raise ValueError("Choose input/output devices on the same host API")
    candidates = (
        [fixed_rate]
        if fixed_rate
        else [48000, 44100, int(output["default_samplerate"])]
    )
    diagnostics = []
    for rate in dict.fromkeys(candidates):
        try:
            backend.check_output_settings(
                device=output_device,
                channels=channels,
                dtype="float32",
                samplerate=rate,
            )
            if capture:
                backend.check_input_settings(
                    device=input_device, channels=1, dtype="float32", samplerate=rate
                )
            return rate, channels
        except Exception as error:
            diagnostics.append(f"{rate} Hz: {error}")
    raise ValueError(
        "No compatible format. Choose compatible devices. " + "; ".join(diagnostics)
    )
