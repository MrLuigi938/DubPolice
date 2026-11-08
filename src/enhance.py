"""Gentle clean-up of the old voice recordings, and MP3 inside FSB5 as a better output format.

Nothing here replaces or re-synthesises a voice. It corrects part of the measured difference to the
remaster's recordings, restores a trace of air above the old 16 kHz limit, and keeps the level.
"""
import hashlib
import struct

import lameenc
import numpy as np

OUTPUT_RATE = 44100
MP3_KBPS = 128
FSB_MODE_MPEG = 11
RATE_CODE_44100 = 8
MP3_FRAME = 1152
TAIL_SECONDS = 0.15

# Frequency (Hz) and gain (dB): about half to three quarters of the measured difference to the remaster.
EQ_POINTS = (
    (0, -30.0), (40, -18.0), (70, 0.0), (800, 0.0), (1400, -1.0), (2000, 0.5), (3000, 2.5), (4000, 1.5),
    (5000, 0.0), (7000, -1.5), (9000, 1.0), (11000, 1.0), (14000, 2.5), (16000, 2.5),
)
DEESS_LOW = 4500
DEESS_HIGH = 12000
# dB below the speech level where it starts, compression ratio, largest cut in dB.
DEESS = (14.0, 4.0, 10.0)
AIR_LEVEL = 0.05
LEVEL_DB = 0.5
PEAK = 0.97


def resample(x, source_rate):
    """Band-limited resampling by the Fourier method, with a mirrored edge so line starts stay clean."""
    if source_rate == OUTPUT_RATE:
        return x
    pad = min(2048, len(x))
    padded = np.concatenate((x[:pad][::-1], x, x[-pad:][::-1]))
    target = int(round(len(padded) * OUTPUT_RATE / source_rate))
    spectrum = np.fft.rfft(padded)
    out = np.zeros(target // 2 + 1, dtype=complex)
    n = min(len(out), len(spectrum))
    out[:n] = spectrum[:n]
    result = np.fft.irfft(out, target) * target / len(padded)
    start = int(round(pad * OUTPUT_RATE / source_rate))
    return result[start:start + int(round(len(x) * OUTPUT_RATE / source_rate))]


def equalize(x):
    spectrum = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), 1 / OUTPUT_RATE)
    points = np.array(EQ_POINTS)
    gain_db = np.interp(freq, points[:, 0], points[:, 1])
    return np.fft.irfft(spectrum * 10 ** (gain_db / 20), len(x))


def band(x, low, high):
    spectrum = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), 1 / OUTPUT_RATE)
    ramp = 500.0
    mask = np.clip((freq - low) / ramp + 0.5, 0, 1) * np.clip((high - freq) / ramp + 0.5, 0, 1)
    return np.fft.irfft(spectrum * mask, len(x))


def add_air(x):
    """A little of the voice's own sibilance, folded up above the old limit."""
    upper = band(x, 7000, 15500)
    return x + AIR_LEVEL * band(np.abs(upper) * np.sign(upper) * np.abs(upper) ** 0.5, 16000, 20000)


def soft_limit(x):
    """Only the rare peaks above the limit are rounded off; everything else stays untouched."""
    over = np.abs(x) > PEAK * 0.9
    if over.any():
        knee = PEAK * 0.9
        room = PEAK - knee
        x = x.copy()
        x[over] = np.sign(x[over]) * (knee + room * np.tanh((np.abs(x[over]) - knee) / room))
    return x


def smooth(x, ms):
    """Moving average over the given time, centred so nothing shifts."""
    size = max(1, int(OUTPUT_RATE * ms / 1000))
    total = np.concatenate(([0.0], np.cumsum(x)))
    left = np.clip(np.arange(len(x)) - size // 2, 0, len(x))
    right = np.clip(left + size, 0, len(x))
    return (total[right] - total[left]) / np.maximum(right - left, 1)


def deess(x, setting):
    """Turn the sibilant band down only while an S is sounding; vowels pass unchanged."""
    below_db, ratio, most_db = setting
    high = band(x, DEESS_LOW, DEESS_HIGH)
    level = 10 * np.log10(smooth(x * x, 20) + 1e-12)
    speech = np.percentile(level, 90)
    sibilant = 10 * np.log10(smooth(high * high, 4) + 1e-12)
    over = np.maximum(sibilant - (speech - below_db), 0.0)
    cut = np.minimum(over * (1 - 1 / ratio), most_db)
    # Smoothed twice so the gain never moves fast enough to click.
    cut = smooth(smooth(cut, 6), 6)
    return x - high + high * 10 ** (-cut / 20)


def enhance(pcm, source_rate, deess_setting=None):
    """Take int16 samples, return float samples at OUTPUT_RATE with the same duration."""
    x = np.asarray(pcm, dtype=np.float64) / 32768.0
    if len(x) < 64:
        return resample(x, source_rate)
    x = resample(x, source_rate)
    x = equalize(x)
    if deess_setting is None:
        deess_setting = DEESS
    if deess_setting:
        x = deess(x, deess_setting)
    x = add_air(x)
    x *= 10 ** (LEVEL_DB / 20)
    return soft_limit(x)


def pad_end(samples):
    """The old recordings stop right at the last sound; the remaster's have a little silence there.
    Without it, the game can swallow the last letters when it starts a line a moment late."""
    return np.concatenate((samples, np.zeros(int(OUTPUT_RATE * TAIL_SECONDS))))


def split_frames(raw):
    """Cut an MPEG-1 Layer III stream into its frames."""
    frames = []
    p = 0
    while p + 4 <= len(raw):
        if raw[p] != 0xFF or raw[p + 1] & 0xE0 != 0xE0:
            raise ValueError(f"MP3-Daten bei Byte {p} nicht lesbar")
        bitrate = (0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320)[raw[p + 2] >> 4]
        rate = (44100, 48000, 32000)[(raw[p + 2] >> 2) & 3]
        size = 144 * bitrate * 1000 // rate + ((raw[p + 2] >> 1) & 1)
        frames.append(raw[p:p + size])
        p += size
    return frames


def make_fsb5_mp3(name, samples):
    """Encode float samples as MP3 in an FSB5 container; return (file bytes, seconds it plays)."""
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(MP3_KBPS)
    encoder.set_in_sample_rate(OUTPUT_RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    encoder.silence()
    data = np.clip(samples * 32767.0, -32768, 32767).astype("<i2").tobytes()
    frames = split_frames(bytes(encoder.encode(data)) + bytes(encoder.flush()))
    # FMOD stops after the first frames unless each one starts on a 4-byte boundary.
    raw = b"".join(f + b"\0" * (-len(f) % 4) for f in frames)
    count = len(frames) * MP3_FRAME
    sample_header = struct.pack("<Q", (RATE_CODE_44100 << 1) | (count << 34))
    padded = raw + b"\0" * (-len(raw) % 32)
    names = struct.pack("<I", 4) + name.encode() + b"\0"
    names += b"\0" * (-(60 + len(sample_header) + len(names)) % 32)
    head = b"FSB5" + struct.pack("<6I", 1, 1, len(sample_header), len(names), len(padded), FSB_MODE_MPEG)
    head += struct.pack("<IIII", 1, 0, 0, 0) + hashlib.md5(padded).digest()
    return head + sample_header + names + padded, count / OUTPUT_RATE
