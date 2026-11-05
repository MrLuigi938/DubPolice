"""Read-only: verify the mod's chores: structure intact, curves rising, line blocks exactly as long as their audio."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from curves import TIME_PROPERTY
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key
import re

source, episode, mod = sys.argv[1:4]
a = Ectt(episode, load_key(source, "SMBTaS"))
originals = {n.lower(): n for n in a.files}
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))
_, files = read_nctt(mod)
problems = chores = lines_checked = worst = 0
with open(mod, "rb") as f:
    def get(name):
        o, s = files[name]
        f.seek(o)
        return f.read(s)

    audio = {}
    for n in files:
        if n.endswith(".wav"):
            h = get(n)[:0x60]
            word = struct.unpack_from("<Q", h, 0x3C)[0]
            audio[int(n[:-4])] = (word >> 34) / 32000
    for n in files:
        if not n.endswith(".chore"):
            continue
        chores += 1
        before, after = a.read(originals[n]), get(n)
        if struct.unpack_from("<I", after, 4)[0] - struct.unpack_from("<I", before, 4)[0] != len(after) - len(before):
            print("  total size wrong:", n)
            problems += 1
        body, _, length = chore_info(after)
        b1, k1, _ = find_times(after, body, length)
        b0, k0, _ = find_times(before, body, chore_info(before)[2])
        if len(b1) != len(b0):
            print(f"  block count differs: {n}: {len(b0)} -> {len(b1)}")
            problems += 1
        def curves(buf):
            res = []
            for m in re.finditer(re.escape(TIME_PROPERTY), buf):
                c = m.start() + 20
                size, count = struct.unpack_from("<II", buf, c)
                if count >= 2 and size == 8 + 13 * count:
                    res.append(([struct.unpack_from("<f", buf, c + 8 + 13 * i)[0] for i in range(count)],
                                [struct.unpack_from("<f", buf, c + 8 + 13 * i + 9)[0] for i in range(count)]))
            return res

        c0, c1 = curves(before), curves(after)
        if len(c0) != len(c1):
            print(f"  curve count differs: {n}: {len(c0)} -> {len(c1)}")
            problems += 1
        for (t0, v0), (t1, v1) in zip(c0, c1):
            fell_before = any(y < x - 1e-6 for x, y in zip(t0, t0[1:]))
            fell_after = any(y < x - 1e-6 for x, y in zip(t1, t1[1:]))
            if fell_after and not fell_before:
                print(f"  curve times now fall: {n}: {[round(x, 2) for x in t0[:6]]} -> {[round(x, 2) for x in t1[:6]]}")
                problems += 1
            if (v0[0], v0[-1]) != (v1[0], v1[-1]):
                print(f"  curve ends changed: {n}")
                problems += 1
        for rid, pos, block, _ in line_resources(after, hashes, b1):
            if rid in audio:
                s, e = struct.unpack_from("<ff", after, block)
                diff = (e - s) - audio[rid]
                lines_checked += 1
                worst = max(worst, abs(diff))
                if diff > 0.002:
                    print(f"  block longer than audio: {n} {rid} {diff:+.3f}")
                    problems += 1
print(f"chores {chores}, line blocks checked {lines_checked}, largest block/audio difference {worst:.3f}s, problems {problems}")
