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


# French spelling to shapes, longest spellings first. Silent endings are dropped by french_word().
FRENCH = [
    ("eaux", ["o"]), ("eau", ["o"]), ("ain", ["ee"]), ("ein", ["ee"]), ("oin", ["u", "ee"]), ("ill", ["i"]),
    ("au", ["o"]), ("ou", ["u"]), ("où", ["u"]), ("oi", ["u", "aa"]), ("ai", ["ee"]), ("ei", ["ee"]),
    ("eu", ["o"]), ("œu", ["o"]), ("œ", ["o"]), ("an", ["aa"]), ("am", ["aa"]), ("en", ["aa"]), ("em", ["aa"]),
    ("on", ["o"]), ("om", ["o"]), ("in", ["ee"]), ("im", ["ee"]), ("un", ["ee"]), ("er", ["ee"]), ("ez", ["ee"]),
    ("gn", ["nn"]), ("ch", ["sh"]), ("ph", ["fv"]), ("qu", ["nn"]), ("gu", ["nn"]), ("ge", ["sh", "ee"]), ("gi", ["sh", "i"]),
    ("ce", ["th", "ee"]), ("ci", ["th", "i"]), ("th", ["th"]),
    ("a", ["aa"]), ("à", ["aa"]), ("â", ["aa"]), ("e", ["ee"]), ("é", ["ee"]), ("è", ["ee"]), ("ê", ["ee"]), ("ë", ["ee"]),
    ("i", ["i"]), ("î", ["i"]), ("ï", ["i"]), ("y", ["i"]), ("o", ["o"]), ("ô", ["o"]), ("u", ["u"]), ("û", ["u"]), ("ù", ["u"]), ("ü", ["u"]),
    ("b", ["mm"]), ("p", ["mm"]), ("m", ["mm"]), ("f", ["fv"]), ("v", ["fv"]), ("w", ["u"]), ("l", ["ll"]),
    ("j", ["sh"]), ("g", ["nn"]), ("ç", ["th"]), ("c", ["nn"]), ("k", ["nn"]), ("q", ["nn"]), ("r", ["nn"]), ("n", ["nn"]),
    ("d", ["th"]), ("t", ["th"]), ("s", ["th"]), ("z", ["th"]), ("x", ["nn", "th"]), ("h", []),
]


def german_word(word):
    """Doubled letters are one sound."""
    return re.sub(r"(.)\1", r"\1", word.replace("ß", "\0")).replace("\0", "ß")


def french_word(word):
    """What French does not say: the elided part before an apostrophe is kept, silent end letters go."""
    if len(word) > 3 and word.endswith("es"):
        word = word[:-2]
    if len(word) > 2:
        word = re.sub(r"[stxdp]$", "", word)
    if len(word) > 2 and word.endswith("e"):
        word = word[:-1]
    return re.sub(r"(.)\1", r"\1", word)


LANGUAGES = {
    "german": (GERMAN, r"[a-zäöüß]+", german_word),
    "french": (FRENCH, r"[a-zàâäçéèêëîïôöùûüÿœæ]+", french_word),
}


def text_shapes(text, language="german"):
    """The shapes of a line in spoken order, one entry per sound; None between words."""
    rules, letters, fold = LANGUAGES[language]
    text = re.sub(r"\{[^}]*\}|\[[^\]]*\]|\*[^*]*\*", " ", text).lower()
    out = []
    for word in re.findall(letters, text):
        word = fold(word)
        i = 0
        while i < len(word):
            for spelling, shapes in rules:
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


def dub_lips(template, text, level, length, language="german"):
    """`level` comes from loudness(); the MP3 starts about one frame (25 ms) late, so the shapes do too."""
    keys = [(frame + 1, shape, value) for frame, shape, value in thin(schedule(text_shapes(text, language), level))]
    return rebuild(template, keys, length)


# Gadgets such as the Moviefone, the synth or Sinistar have no mouth shapes, only a switch that is on while they talk:
# a block of <size><count> and 10-byte records  time:f32  '1'  01 00 00 00  value:'1'|'0'.
TOGGLE = 10


def toggle_block(d):
    """(offset of first record, record count) of the talk switch, or None."""
    from anm_patch import length_offset
    for i in range(length_offset(d) + 4, len(d) - 8):
        size, count = struct.unpack_from("<II", d, i)
        if count and size == 8 + count * TOGGLE and i + size <= len(d):
            if all(d[i + 8 + k * TOGGLE + 4:i + 8 + k * TOGGLE + 9] == b"1\1\0\0\0" for k in range(count)):
                return i + 8, count
    return None


def talking(level):
    """On while the voice is loud, as frames; runs shorter than two frames are folded into their neighbours."""
    on = list(level > 0.12)
    for want in (False, True):
        i = 0
        while i < len(on):
            j = i
            while j < len(on) and on[j] == on[i]:
                j += 1
            if on[i] == want and j - i < 2 and 0 < i and j < len(on):
                on[i:j] = [not want] * (j - i)
            i = j
    return on


def toggle_lips(template, level, length):
    """The talk switch of a gadget, set from the loudness of the dubbed line. None if the file has no switch."""
    from anm_patch import length_offset
    found = toggle_block(template)
    if not found:
        return None
    start, count = found
    # The MP3 starts about one frame late, so the switch does too.
    on = [False] + talking(level)
    keys, last = [], None
    for frame, state in enumerate(on):
        if frame / FPS >= length:
            break
        if state != last:
            keys.append((frame / FPS, state))
            last = state
    keys.append((length, False))
    body = b"".join(struct.pack("<f", t) + b"1\1\0\0\0" + (b"1" if s else b"0") for t, s in keys)
    grow = len(body) - count * TOGGLE
    out = bytearray(template[:start - 8]) + struct.pack("<II", 8 + len(body), len(keys)) + body + template[start + count * TOGGLE:]
    offset = length_offset(template)
    struct.pack_into("<f", out, offset, length)
    struct.pack_into("<I", out, 4, struct.unpack_from("<I", template, 4)[0] + grow)
    old = int.from_bytes(template[offset + 9:offset + 12], "little")
    out[offset + 9:offset + 12] = (old + grow).to_bytes(3, "little")
    return bytes(out)


def borrow_lips(template, pool, length):
    """Bone lip files (the Maimtron, the bugs, Sal) cannot be rebuilt: take the one of the same character whose length
    fits the dubbed line best, so the mouth moves as long as the voice. `pool` is [(length, data)] of that character."""
    from anm_patch import length_offset
    offset = length_offset(template)
    types = struct.unpack_from("<I", template, 16)[0]
    head = template[16:20 + 12 * types]
    if 0 <= struct.unpack_from("<f", template, offset)[0] - length <= 0.4:
        return template
    own = struct.unpack_from("<f", template, offset)[0]
    if own <= 0:
        return None  # an empty file: this line moves no mouth
    same = [(l, d) for l, d in pool if d[16:20 + 12 * types] == head]
    fits = [(l - length, d) for l, d in same if 0 <= l - length <= 0.4]
    if fits:
        donor = min(fits, key=lambda f: f[0])[1]
    else:
        # Nothing long enough: the longest shorter one, if it comes closer than the line's own.
        shorter = [(l, d) for l, d in same if own < l < length]
        if not shorter:
            return None
        donor = max(shorter, key=lambda f: f[0])[1]
    if donor == template:
        return template
    out = bytearray(donor)
    # Keep this line's own animation name.
    out[length_offset(donor) - 8:length_offset(donor)] = template[offset - 8:offset]
    return bytes(out)
