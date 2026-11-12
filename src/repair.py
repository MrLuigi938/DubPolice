"""Repair old takes that stop in the middle of a sound.

About one Season 1 take in ten (German and French alike) ends while the voice is still loud: the last letters were cut
off when the recordings were prepared in 2007, and the game's own lip files from back then are just as short. Two
repairs, both with real recordings of the same actor:

1. whole take: the same speaker says the same text in another take that ends properly; it is used instead.
2. graft: the missing ending is taken from another take of the same speaker whose last word ends the same way
   ("hat" from "... anvisiert hat."). The donor is searched for the spot that sounds most like the end of the cut take,
   level-matched and cross-faded. A graft that does not fit well enough is not made.
"""
import numpy as np

RATE_FRAME = 640          # 20 ms at 32 kHz
CUT_RATIO = 0.3           # last 20 ms louder than this share of the take's level: cut off
MAX_TAIL = 0.35           # seconds a graft may add
MAX_DISTANCE = 1.0        # spectral distance a graft may have
MAX_DONORS = 25


def level(x):
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0


def is_cut(pcm):
    x = np.asarray(pcm, dtype=np.float64)
    whole = level(x)
    return bool(whole) and level(x[-RATE_FRAME:]) / whole > CUT_RATIO


def _features(x):
    win, hop = 640, 160
    n = max(1, (len(x) - win) // hop + 1)
    window = np.hanning(win)
    spec = np.array([np.abs(np.fft.rfft(x[i * hop:i * hop + win] * window)) for i in range(n)])
    edges = np.geomspace(2, spec.shape[1] - 1, 33).astype(int)
    bands = np.array([spec[:, a:b + 1].mean(axis=1) for a, b in zip(edges, edges[1:])]).T
    return np.log(bands + 1.0)


def graft(cut, donor, rate):
    """Return (repaired samples, distance) or (None, inf). Both inputs are int16 sample sequences at `rate`."""
    cut = np.asarray(cut, dtype=np.float64)
    donor = np.asarray(donor, dtype=np.float64)
    hop, template_frames = 160, 12
    fc, fd = _features(cut), _features(donor)
    if len(fc) < template_frames or len(fd) < template_frames + 3:
        return None, float("inf")
    template = fc[-template_frames:]
    best, position = float("inf"), None
    # Only the donor's last word can hold the ending.
    for j in range(max(template_frames, len(fd) - 60), len(fd) - 2):
        d = float(np.mean((fd[j - template_frames:j] - template) ** 2))
        if d < best:
            best, position = d, j
    if position is None:
        return None, float("inf")
    end = (position - 1) * hop + 640
    tail = donor[end:]
    if not 160 <= len(tail) <= MAX_TAIL * rate:
        return None, float("inf")
    gain = level(cut[-1920:]) / (level(donor[max(0, end - 1920):end]) or 1.0)
    fade = 256
    ramp = np.linspace(0.0, 1.0, fade)
    joined = cut.copy()
    joined[-fade:] = cut[-fade:] * (1 - ramp) + donor[end - fade:end] * gain * ramp
    out = np.concatenate([joined, tail * gain])
    return np.clip(out, -32768, 32767).astype(np.int16), best


def repair(pcm, rate, whole_takes, donors, decode):
    """Return (samples, kind): kind is "", "whole take" or "graft". `decode(ref)` gives a candidate's samples."""
    if not is_cut(pcm):
        return pcm, ""
    complete = []
    for ref in whole_takes:
        other = decode(ref)
        if other is not None and len(other) and not is_cut(other):
            complete.append(other)
    if complete:
        return max(complete, key=len), "whole take"
    best, best_distance = None, MAX_DISTANCE
    for ref in donors[:MAX_DONORS]:
        other = decode(ref)
        if other is None or not len(other) or is_cut(other):
            continue
        joined, distance = graft(pcm, other, rate)
        if joined is not None and distance < best_distance:
            best, best_distance = joined, distance
    if best is not None:
        return best, "graft"
    return pcm, ""


def last_word(text):
    words = text.split()
    return words[-1] if words else ""


def candidates(speaker, text, pool, exclude):
    """Whole takes and graft donors for one take, from `pool`: [(ref, speaker, normalized text)]."""
    whole = [ref for ref, s, t in pool if s == speaker and t == text and ref != exclude]
    word = last_word(text)
    donors = []
    if word:
        for k in (len(word), 3, 2):
            ending = word[-k:]
            for ref, s, t in pool:
                if s == speaker and ref != exclude and ref not in donors and last_word(t).endswith(ending):
                    donors.append(ref)
            if len(donors) >= MAX_DONORS:
                break
    return whole, donors[:MAX_DONORS]
