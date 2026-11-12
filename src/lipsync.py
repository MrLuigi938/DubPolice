"""Mouth shapes for a dubbed line, from its text and the loudness of its recording.

The remaster's lip files are short lists of mouth shapes: at a time (on a 1/30 s grid) a shape such as AA or MM fades in,
holds and fades out with a weight. Each line gets its own list here instead of the stretched English one: the German
text gives the order of the shapes, the recording gives where the voice is loud, so open vowels land on loud syllables.
"""
import re
import struct

import numpy as np

from build_mod import crc64

FPS = 30.0
RECORD = 37
TAG = b"\x01\0\0\0\x1c\0\0\0"
# Shapes the remaster's characters know (sam_phoneme_AA.anm and so on), keyed by their name in lower case.
SHAPES = ("aa", "ee", "fv", "i", "ll", "mm", "nn", "o", "sh", "th", "u")
SYMBOL = {s: struct.pack("<Q", crc64(s.encode())) for s in SHAPES}
VOWELS = {"aa", "ee", "i", "o", "u"}

# German spelling to shapes; longest spellings first. Silent "h" after a vowel and doubled letters are folded away.
GERMAN = [
    ("tsch", ["sh"]), ("sch", ["sh"]), ("chs", ["nn", "th"]), ("ch", ["sh"]),
    ("au", ["aa", "u"]), ("ei", ["aa", "i"]), ("ai", ["aa", "i"]), ("eu", ["o", "i"]), ("äu", ["o", "i"]),
    ("ie", ["i"]), ("ah", ["aa"]), ("eh", ["ee"]), ("ih", ["i"]), ("oh", ["o"]), ("uh", ["u"]), ("äh", ["ee"]), ("öh", ["o"]), ("üh", ["u"]),
    ("aa", ["aa"]), ("ee", ["ee"]), ("oo", ["o"]), ("ng", ["nn"]), ("pf", ["fv"]), ("ph", ["fv"]), ("qu", ["nn", "fv"]), ("ck", ["nn"]),
    ("ß", ["th"]), ("tz", ["th"]), ("sp", ["sh", "mm"]), ("st", ["th"]),
    ("a", ["aa"]), ("e", ["ee"]), ("i", ["i"]), ("o", ["o"]), ("u", ["u"]), ("ä", ["ee"]), ("ö", ["o"]), ("ü", ["u"]), ("y", ["i"]),
    ("b", ["mm"]), ("p", ["mm"]), ("m", ["mm"]), ("f", ["fv"]), ("v", ["fv"]), ("w", ["fv"]), ("l", ["ll"]),
    ("j", ["i"]), ("d", ["th"]), ("t", ["th"]), ("s", ["th"]), ("z", ["th"]), ("x", ["nn", "th"]),
    ("n", ["nn"]), ("g", ["nn"]), ("k", ["nn"]), ("c", ["nn"]), ("r", ["nn"]), ("h", []),
]


def text_shapes(text):
    """The shapes of a German line in spoken order, one entry per sound; None between words."""
    text = re.sub(r"\{[^}]*\}|\[[^\]]*\]|\*[^*]*\*", " ", text).lower()
    out = []
    for word in re.findall(r"[a-zäöüß]+", text):
        word = re.sub(r"(.)\1", r"\1", word.replace("ß", "\0")).replace("\0", "ß")
        i = 0
        while i < len(word):
            for spelling, shapes in GERMAN:
                if word.startswith(spelling, i):
                    out += shapes
                    i += len(spelling)
                    break
            else:
                i += 1
        out.append(None)
    # One shape twice in a row is one longer sound.
    merged = []
    for s in out:
        if s is None or not merged or merged[-1] != s:
            merged.append(s)
    return merged


def loudness(pcm, rate):
    """Loudness per 1/30 s frame, 0..1."""
    samples = np.asarray(pcm, dtype=np.float64)
    hop = int(rate / FPS)
    frames = max(1, len(samples) // hop)
    rms = np.sqrt(np.array([np.mean(samples[i * hop:(i + 1) * hop] ** 2) for i in range(frames)]) + 1e-9)
    top = np.percentile(rms, 95) or 1.0
    return np.clip(rms / top, 0.0, 1.0)


def schedule(shapes, level):
    """Place the shapes on the speech: each takes a share of the loudness, vowels twice as much as consonants."""
    sounds = [s for s in shapes if s]
    if not sounds:
        return []
    voiced = np.where(level > 0.12)[0]
    if not len(voiced):
        return []
    first, last = int(voiced[0]), int(voiced[-1]) + 1
    weight = np.maximum(level[first:last], 0.05)
    cum = np.concatenate([[0.0], np.cumsum(weight)])
    need = np.array([2.0 if s in VOWELS else 1.0 for s in sounds])
    edges = np.concatenate([[0.0], np.cumsum(need)]) / need.sum() * cum[-1]
    keys = []
    for s, a, b in zip(sounds, edges, edges[1:]):
        mid = (a + b) / 2
        frame = first + int(np.searchsorted(cum, mid)) - 1
        frame = min(max(frame, first), last - 1)
        if keys and frame <= keys[-1][0]:
            frame = keys[-1][0] + 1
        if frame >= last + 2:
            break
        local = float(level[min(frame, len(level) - 1)])
        value = (0.45 + 0.4 * local) if s in VOWELS else (0.4 + 0.3 * local)
        keys.append((frame, s, value))
    return keys


# Fewer, softer changes: one shape at most every 1/10 s, the clearest one wins where several crowd together.
MIN_GAP = 3
RANK = {"aa": 5, "o": 5, "ee": 4, "u": 4, "i": 4, "mm": 3, "fv": 3, "ll": 1, "sh": 2, "th": 1, "nn": 0}


def thin(keys):
    kept = []
    for key in keys:
        if kept and key[0] - kept[-1][0] < MIN_GAP:
            if RANK[key[1]] > RANK[kept[-1][1]]:
                kept[-1] = (kept[-1][0], key[1], key[2])
            continue
        kept.append(key)
    return kept


def records(keys):
    out = bytearray()
    for i, (frame, shape, value) in enumerate(keys):
        gap = (keys[i + 1][0] - frame) if i + 1 < len(keys) else 4
        # Ramps overlap the neighbours, so the mouth glides from shape to shape instead of snapping.
        ramp_in = 3 / FPS
        hold = 1 / FPS if gap >= 4 else 0.0
        ramp_out = min(5, max(3, gap)) / FPS
        out += struct.pack("<f", frame / FPS) + b"1" + TAG + SYMBOL[shape] + struct.pack("<4f", ramp_in, hold, ramp_out, value * 0.85)
    return bytes(out)


def rebuild(template, keys, length):
    """A remaster lip file with these keys and this length, everything else taken over from the template."""
    from anm_patch import key_blocks, length_offset
    blocks = key_blocks(template)
    if len(blocks) != 1 or not keys:
        raise ValueError("lip file without exactly one block of mouth shapes")
    start, count = blocks[0]
    body = records(keys)
    grow = len(body) - count * RECORD
    out = bytearray(template[:start - 8]) + struct.pack("<II", 8 + len(body), len(keys)) + body + template[start + count * RECORD:]
    struct.pack_into("<f", out, length_offset(template), length)
    # Two sizes cover the block: the body after the 116-byte meta header, and a 24-bit size beside the length.
    struct.pack_into("<I", out, 4, struct.unpack_from("<I", template, 4)[0] + grow)
    at = length_offset(template) + 9
    old = int.from_bytes(template[at:at + 3], "little")
    out[at:at + 3] = (old + grow).to_bytes(3, "little")
    return bytes(out)


def german_lips(template, text, level, length):
    """`level` comes from loudness(); the MP3 starts about one frame (25 ms) late, so the shapes do too."""
    keys = [(frame + 1, shape, value) for frame, shape, value in thin(schedule(text_shapes(text), level))]
    return rebuild(template, keys, length)
