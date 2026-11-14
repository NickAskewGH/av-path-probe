import numpy as np
import pytest

from audio_loopback.dsp import Processor, aspect_fit, levels


def test_silence_and_test_tone_are_independent():
    processor = Processor()
    incoming = np.zeros((512, 1), np.float32)
    outgoing = np.empty((512, 2), np.float32)
    processor.process(incoming, outgoing)
    assert not outgoing.any()
    processor.process(incoming, outgoing, tone=True)
    assert levels(outgoing).peak > 0
    assert levels(incoming).peak == 0


def test_tremolo_matches_reference_across_blocks():
    processor = Processor()
    for block in range(4):
        times = (np.arange(512) + block * 512) / 48000
        incoming = (0.6 * np.sin(2 * np.pi * 440 * times)).astype(np.float32)
        outgoing = np.empty((512, 2), np.float32)
        processor.process(incoming[:, None], outgoing)
        expected = incoming * 0.2 * (0.65 + 0.35 * np.sin(2 * np.pi * 8 * times))
        np.testing.assert_allclose(outgoing[:, 0], expected, atol=3e-8)
        np.testing.assert_array_equal(outgoing[:, 0], outgoing[:, 1])


def test_bypass_and_gain_smoothing():
    processor = Processor()
    incoming = np.full((512, 1), 0.5, np.float32)
    outgoing = np.empty((512, 2), np.float32)
    processor.process(incoming, outgoing, modulated=False)
    np.testing.assert_allclose(outgoing, 0.1)
    processor.process(incoming, outgoing, modulated=False, gain=0.4)
    assert outgoing[0, 0] < 0.101
    assert outgoing[-1, 0] == pytest.approx(0.2)


@pytest.mark.parametrize("channels", [1, 2, 6])
def test_boundary_inputs_are_finite_and_safe(channels):
    incoming = np.resize(
        np.array([np.nan, np.inf, -np.inf, 2, -2], np.float32), (512, channels)
    )
    outgoing = np.empty((512, channels), np.float32)
    Processor().process(incoming, outgoing, gain=99, tone=True)
    assert np.isfinite(outgoing).all()
    assert np.abs(outgoing).max() <= 0.9
    assert outgoing.shape == incoming.shape


def test_levels():
    assert levels(np.zeros((512, 1))).rms == 0
    times = np.arange(48000) / 48000
    signal = 0.5 * np.sin(2 * np.pi * 1000 * times)
    assert levels(signal).rms == pytest.approx(0.5 / np.sqrt(2))
    assert levels(signal).peak == pytest.approx(0.5)
    assert levels(np.ones((2, 2))).clipped


def test_shape_validation_and_aspect_fit():
    with pytest.raises(ValueError):
        Processor().process(np.zeros((32, 1)), np.zeros((32, 2)))
    assert aspect_fit(640, 360, 1280, 720) == (0, 0, 640, 360)
    assert aspect_fit(1024, 768, 1280, 720) == (0, 96, 1024, 576)
    with pytest.raises(ValueError):
        aspect_fit(0, 10, 10, 10)
