"""Fit longer German lines into a chore.

Cutscenes have long animations whose keys live in separate files, so their timeline must stay as it is:
a line may only grow into the gap before the next line. Simple dialog chores may be stretched instead.
"""
import array
import math
import re
import struct

from chore_warp import EDGE, chore_info, find_times, warp

GAP = 0.05
_patterns = {}


def line_resources(d, hashes, blocks):
    """Return [(line id, hash offset, first block offset, end of its own data)] in file order."""
    key = id(hashes)
    if key not in _patterns:
        _patterns.clear()
        _patterns[key] = re.compile(b"|".join(re.escape(h) for h in hashes))
    hits = [(m.start(), hashes[m.group()]) for m in _patterns[key].finditer(d)]
    first = []
    for pos, rid in hits:
        if not first or first[-1][1] != rid:
            first.append((pos, rid))
    out = []
    ordered = sorted(blocks)
    for i, (pos, rid) in enumerate(first):
        limit = first[i + 1][0] if i + 1 < len(first) else len(d)
        own = [b for b in ordered if pos < b < limit]
        if own:
            # A line's own data ends at its first block; other tracks may follow before the next line.
            out.append((rid, pos, own[0], own[0]))
    return out


def analyse(d, hashes, name=""):
    """Describe a chore: is it a cutscene, and how much room does each line have?"""
    body, length_at, length = chore_info(d)
    blocks, keys, _ = find_times(d, body, length)
    lines = line_resources(d, hashes, blocks)
    line_blocks = {x[2] for x in lines}
    spans = sorted((struct.unpack_from("<ff", d, x[2]) + (x[0],)) for x in lines)
    ends = [e for _, e, _ in spans]
    longest = 0
    for b in blocks:
        if b in line_blocks:
            continue
        s, e = struct.unpack_from("<ff", d, b)
        longest = max(longest, sum(1 for x in ends if s < x - EDGE and x + EDGE < e))
    room = {}
    for i, (s, e, rid) in enumerate(spans):
        following = spans[i + 1][0] if i + 1 < len(spans) else None
        room[rid] = (following - s - GAP) if following is not None else math.inf
    named = "cs_" in name.lower()
    return dict(cutscene=named or longest >= 5, length_at=length_at, length=length, lines=lines, keys=keys, blocks=blocks, room=room, spans=len(spans), longest=longest)


def apply_fit(d, info, seconds):
    """Extend line blocks in place; nothing else moves. `seconds` maps line id -> final audio length."""
    out = bytearray(d)
    report = []
    last_end = info["length"]
    for rid, pos, block, limit in info["lines"]:
        if rid not in seconds:
            continue
        s, e = struct.unpack_from("<ff", d, block)
        new_end = s + min(seconds[rid] + GAP, info["room"][rid])
        last_end = max(last_end, new_end)
        delta = new_end - e
        report.append((rid, s, e, new_end, seconds[rid]))
        if delta <= 0:
            continue
        struct.pack_into("<f", out, block + 4, new_end)
        struct.pack_into("<f", out, pos + 8, seconds[rid])
        for k in info["keys"]:
            if pos < k < limit:
                t = struct.unpack_from("<f", d, k)[0]
                if t >= e - EDGE:
                    struct.pack_into("<f", out, k, t + delta)
    # Only a final line can pass the old end, and nothing else plays there.
    struct.pack_into("<f", out, info["length_at"], last_end)
    return bytes(out), report


def stretch_chore(d, hashes, seconds):
    """Dialog chores: insert pauses so the whole line fits."""
    return warp(d, hashes, seconds, verbose=lambda *_: None)


def trim(pcm, rate, threshold=250, margin=0.04):
    """Cut silence at both ends, keeping a short margin."""
    win = max(1, rate // 100)
    n = len(pcm)
    a = 0
    while a + win < n and max(abs(x) for x in pcm[a:a + win]) < threshold:
        a += win
    z = n
    while z - win > a and max(abs(x) for x in pcm[z - win:z]) < threshold:
        z -= win
    m = int(margin * rate)
    return pcm[max(0, a - m):min(n, z + m)]


def change_tempo(pcm, rate, factor):
    """Pitch-preserving speed change (waveform-similarity overlap-add). factor > 1 is faster."""
    if factor <= 1.001:
        return pcm
    size = int(0.030 * rate)
    syn = size // 2
    ana = syn * factor
    tol = int(0.008 * rate)
    step = 4
    window = [0.5 - 0.5 * math.cos(2 * math.pi * i / size) for i in range(size)]
    total = int(len(pcm) / factor) + size
    out = [0.0] * total
    weight = [0.0] * total
    src = list(pcm)
    pos_out = 0
    prev_end = 0
    k = 0
    while True:
        target = int(k * ana)
        if target + size + tol >= len(src) or pos_out + size >= total:
            break
        best = target
        if k:
            ref = src[prev_end:prev_end + syn]
            best_score = -1e30
            for lag in range(-tol, tol + 1, 2):
                c = target + lag
                if c < 0:
                    continue
                seg = src[c:c + syn]
                score = sum(ref[i] * seg[i] for i in range(0, min(len(ref), len(seg)), step))
                if score > best_score:
                    best_score, best = score, c
        for i in range(size):
            out[pos_out + i] += src[best + i] * window[i]
            weight[pos_out + i] += window[i]
        prev_end = best + syn
        pos_out += syn
        k += 1
    used = pos_out + syn
    res = array.array("h", (0 for _ in range(used)))
    for i in range(used):
        w = weight[i]
        v = out[i] / w if w > 1e-3 else 0.0
        res[i] = max(-32768, min(32767, int(v)))
    return res
