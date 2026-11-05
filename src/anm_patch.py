"""Change the length of a remaster lipsync .anm and stretch its keyframe times to match.

Layout found in the remaster's files: a length float at an offset derived from the meta header, then one or more blocks of
<size:u32><count:u32> followed by 37-byte records:
    time:f32  flag:u8  01 00 00 00  1c 00 00 00  symbol:8 bytes  rampIn:f32  zero:f32  rampOut:f32  value:f32
"""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RECORD = 37
TAG = b"\x01\0\0\0\x1c\0\0\0"


def length_offset(d):
    """Meta header: 20 bytes, then 12 bytes per type entry; then version (8) and name symbol (8)."""
    types = struct.unpack_from("<I", d, 16)[0]
    return 20 + 12 * types + 8 + 8


def key_blocks(d):
    """Return (offset of first record, record count) for each keyframe block."""
    blocks = []
    i = length_offset(d) + 4
    end = len(d) - 8
    while i < end:
        size, count = struct.unpack_from("<II", d, i)
        if count and size == 8 + count * RECORD and i + size <= len(d) and d[i + 8 + 5:i + 8 + 5 + 8] == TAG:
            if all(d[i + 8 + k * RECORD + 5:i + 8 + k * RECORD + 13] == TAG for k in range(count)):
                blocks.append((i + 8, count))
                i += size
                continue
        i += 1
    return blocks


def patch(d, new_length):
    """Return a copy of the .anm with its length set and every keyframe time scaled."""
    if d[:4] != b"6VSM":
        raise ValueError("not a remaster .anm")
    offset = length_offset(d)
    old = struct.unpack_from("<f", d, offset)[0]
    blocks = key_blocks(d)
    # Some files use another keyframe format: their length still changes, their keys stay as they are.
    if not 0 < old < 600:
        raise ValueError(f"unexpected length {old}")
    scale = new_length / old
    out = bytearray(d)
    struct.pack_into("<f", out, offset, new_length)
    for start, count in blocks:
        for k in range(count):
            at = start + k * RECORD
            t = struct.unpack_from("<f", d, at)[0]
            struct.pack_into("<f", out, at, t * scale)
    return bytes(out), old, scale, sum(c for _, c in blocks)


def main():
    from ectt import Ectt
    from ttarch4 import load_key

    source, archive = sys.argv[1:3]
    a = Ectt(archive, load_key(source, "SMBTaS"))
    stats = Counter()
    failures = []
    max_key_over = 0.0
    for n in a.files:
        if not (n.endswith(".anm") and n[:-4].isdigit()):
            continue
        d = a.read(n)
        stats["files"] += 1
        try:
            length = struct.unpack_from("<f", d, length_offset(d))[0]
            blocks = key_blocks(d)
            if not blocks or not 0 < length < 600:
                raise ValueError(f"length {length} blocks {len(blocks)}")
            stats[f"blocks={len(blocks)}"] += 1
            stats["keys"] += sum(c for _, c in blocks)
            for s, c in blocks:
                for k in range(c):
                    t = struct.unpack_from("<f", d, s + k * RECORD)[0]
                    max_key_over = max(max_key_over, t - length)
        except (ValueError, struct.error) as e:
            failures.append((n, len(d), str(e)))
    print(stats.most_common())
    print("largest key time beyond length:", round(max_key_over, 3))
    print("failed:", len(failures), failures[:8])


if __name__ == "__main__":
    main()
