# Signal processing helpers: raw passthrough, bandpass filter, RMS envelope.
#
# Filter:  4th-order zero-phase Butterworth bandpass, 20–450 Hz
#   20 Hz  — removes DC drift and movement artefacts
#   450 Hz — well below Nyquist (1000 Hz) at 2000 Hz sampling rate
#
# RMS: rolling window RMS using uniform_filter1d (preserves full time-series shape)

import numpy as np
from scipy import signal as sp_signal
from scipy.ndimage import uniform_filter1d


def bandpass_filter(
    data: np.ndarray,
    sampling_rate: float,
    low_cut: float = 20.0,
    high_cut: float = 450.0,
    order: int = 4,
) -> np.ndarray:
    """Zero-phase Butterworth bandpass filter. data shape: (channels, samples)."""
    nyquist = sampling_rate / 2.0
    low = low_cut / nyquist
    high = min(high_cut / nyquist, 0.999)

    b, a = sp_signal.butter(order, [low, high], btype="band")

    # filtfilt requires len(x) > padlen = 3 * max(len(a), len(b))
    padlen = 3 * max(len(a), len(b))
    if data.shape[1] <= padlen:
        return data.copy()
    filtered = np.zeros_like(data)
    for ch in range(data.shape[0]):
        filtered[ch, :] = sp_signal.filtfilt(b, a, data[ch, :])
    return filtered


def compute_rms(data: np.ndarray, window_size: int = 200) -> np.ndarray:
    """
    Rolling RMS envelope. data shape: (channels, samples) -> same shape out.

    window_size=200 samples = 100 ms at 2000 Hz.
    uniform_filter1d slides along axis=1 (time), so the output is a full
    time-series — same shape as input — and the plot line stays visible.
    """
    mean_squares = uniform_filter1d(data ** 2, size=window_size, axis=1)
    # Clamp to 0 to prevent NaN from floating-point inaccuracies
    return np.sqrt(np.maximum(mean_squares, 0))


def process_signal(
    data: np.ndarray,
    sampling_rate: float,
    mode: str,
) -> np.ndarray:
    """
    Dispatch to the right processing mode.

    mode: "original" | "filtered" | "rms"
    data shape: (channels, samples)
    """
    if mode == "original":
        return data

    filtered = bandpass_filter(data, sampling_rate)

    if mode == "filtered":
        return filtered

    if mode == "rms":
        return compute_rms(filtered)

    raise ValueError(f"Unknown signal mode: {mode!r}")
