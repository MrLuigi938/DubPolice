"""Stretch a chore's timeline so longer (German) voice lines fit.

A pause equal to the extra length goes in at the end of each line; everything after it moves back.
Time values live in two kinds of sized lists: <size:u32><count:u32> followed by records of
    block:     start:f32 end:f32 loop:char scale:f32                (13 bytes)
    keyframe:  time:f32 flag:char mode:u32 value...                  (13 bytes or more)
"""
import re
import struct
from collections import Counter

PAD = 0.05
EDGE = 0.02  # fade keys sit just before a line's end and must move with it
KEY_SIZES = range(13, 61)


def chore_info(d):
    types = struct.unpack_from("<I", d, 16)[0]
    body = 20 + 12 * types
    name_len = struct.unpack_from("<I", d, body + 4)[0]
    length_at = body + 8 + name_len + 4
    return body, length_at, struct.unpack_from("<f", d, length_at)[0]


def _blocks_at(d, i, count, length):
    if struct.unpack_from("<I", d, i)[0] != 8 + 13 * count:
        return None
    rows = []
    for k in range(count):
        s, e, loop, scale = struct.unpack_from("<ffcf", d, i + 8 + 13 * k)
        if not (-1 <= s <= e <= length + 60 and loop in (b"0", b"1") and 0.01 < scale < 100):
            return None
        rows.append(i + 8 + 13 * k)
    return rows


def _keys_at(d, i, size, count, length):
    rec = (size - 8) // count
    if rec * count != size - 8 or rec not in KEY_SIZES:
        return None
    last = -2.0
    rows = []
    for k in range(count):
        at = i + 8 + rec * k
        t = struct.unpack_from("<f", d, at)[0]
        if not (-1 <= t <= length + 60) or t < last - 1e-4 or d[at + 4] not in (0x30, 0x31):
            return None
        if rec >= 9 and struct.unpack_from("<I", d, at + 5)[0] > 8:
            return None
        last = t
        rows.append(at)
    return rec, rows


def find_times(d, body, length):
    """Return (block offsets, key offsets, stats). Every offset holds a time float."""
    blocks, keys = [], []
    stats = Counter()
    i = body
    end = len(d) - 16
    while i < end:
        size, count = struct.unpack_from("<II", d, i)
        if 1 <= count <= 20000 and 8 < size <= len(d) - i:
            rows = _blocks_at(d, i, count, length) if size == 8 + 13 * count else None
            if rows is not None and d[i + 8 + 5:i + 8 + 9] not in (b"\x01\0\0\0", b"\x02\0\0\0", b"\0\0\0\0", b"\x03\0\0\0"):
                blocks += rows
                stats["block lists"] += 1
                i += size
                continue
            found = _keys_at(d, i, size, count, length)
            if found:
                keys += found[1]
                stats[f"key lists rec={found[0]}"] += 1
                i += 8
                continue
        i += 1
    # Keys with short or variable values (on/off switches, expression names) are not uniform lists.
    known = set(keys)
    for b in blocks:
        known.update(range(b, b + 13))
    for i in range(body, len(d) - 9):
        if i in known or d[i + 4] not in (0x30, 0x31):
            continue
        t = struct.unpack_from("<f", d, i)[0]
        if 0.001 <= t <= length + 60 and struct.unpack_from("<I", d, i + 5)[0] in (1, 2):
            keys.append(i)
            stats["short or text keys"] += 1
    return blocks, keys, stats


def line_hashes(landb):
    out = {}
    for i in range(0, len(landb) - 24):
        if landb[i + 16:i + 20] == b"\0\0\0\0" and landb[i + 20:i + 24] == b"\x0c\0\0\0" and landb[i:i + 4] == landb[i + 12:i + 16]:
            out[landb[i + 4:i + 12]] = struct.unpack_from("<I", landb, i)[0]
    return out


def warp(d, hashes, seconds, verbose=print):
    """Return (patched chore, per-line report); `seconds` maps line id -> German length."""
    body, length_at, length = chore_info(d)
    blocks, keys, stats = find_times(d, body, length)
    verbose(f"  length {length:.3f}, blocks {len(blocks)}, keys {len(keys)}, {dict(stats)}")

    hits = sorted((m.start(), rid) for h, rid in hashes.items() if rid in seconds for m in re.finditer(re.escape(h), d))
    all_hits = sorted((m.start(), rid) for h, rid in hashes.items() for m in re.finditer(re.escape(h), d))
    res_at = {}
    block_set = sorted(blocks)
    for pos, rid in hits:
        if rid in res_at:
            continue
        later = [p for p, r in all_hits if p > pos and r != rid]
        limit = later[0] if later else len(d)
        own = [b for b in block_set if pos < b < limit]
        if own:
            res_at[rid] = (pos, own[0])

    inserts = []
    report = []
    for rid, (pos, b) in sorted(res_at.items(), key=lambda kv: kv[1][1]):
        s, e = struct.unpack_from("<ff", d, b)
        need = seconds[rid] + PAD - (e - s)
        report.append((rid, s, e, seconds[rid], max(0.0, need)))
        if need > 0:
            inserts.append((e, need))
    inserts.sort()

    def shift(t):
        return t + sum(amount for at, amount in inserts if t >= at - EDGE)

    out = bytearray(d)
    for b in blocks:
        s, e = struct.unpack_from("<ff", d, b)
        struct.pack_into("<ff", out, b, shift(s), shift(e))
    for k in keys:
        struct.pack_into("<f", out, k, shift(struct.unpack_from("<f", d, k)[0]))
    struct.pack_into("<f", out, length_at, shift(length))

    # Each line resource stores its own length right after its hash.
    for rid, (pos, b) in res_at.items():
        stored = struct.unpack_from("<f", d, pos + 8)[0]
        if abs(stored - (struct.unpack_from("<f", d, b + 4)[0] - struct.unpack_from("<f", d, b)[0])) < 0.5:
            struct.pack_into("<f", out, pos + 8, seconds[rid])

    # Safety check: time values that were moved must not still appear elsewhere untouched.
    moved = {k for k in blocks} | {b + 4 for b in blocks} | set(keys) | {length_at}
    leftovers = 0
    for rid, s, e, g, need in report:
        raw = struct.pack("<f", struct.unpack_from("<f", d, res_at[rid][1] + 4)[0])
        for m in re.finditer(re.escape(raw), d):
            if m.start() not in moved:
                leftovers += 1
    return bytes(out), report, leftovers, sum(a for _, a in inserts), shift(length)
