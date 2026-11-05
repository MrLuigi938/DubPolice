"""Read-only: which tracks of the opening run where, how far uniform slowdown drifts from the lines,
how much voice data the original uses per second, and what surrounds a time curve in the file."""
import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from chore_warp import chore_info, find_times
from ectt import Ectt
from nctt import read_nctt
from port_schedule import apply_map, time_map
from ttarch4 import load_key

source, episode, uncompressed, old_en, old_de = sys.argv[2:7]
en = open(old_en, "rb").read()
de = open(old_de, "rb").read()
table = time_map(en, de)

print("== Old English resources and their blocks")
names = [(m.start(), m.group().decode()) for m in re.finditer(rb"[A-Za-z0-9_]{4,}\.(?:anm|wav|aud|vox|chore|dlg|lang|langres|prop|style|bank)", en)]
seen = []
for i, (pos, n) in enumerate(names):
    if seen and seen[-1][1] == n:
        continue
    seen.append((pos, n))
kinds = Counter(n.rsplit(".", 1)[-1] for _, n in seen)
print(" kinds:", kinds.most_common())
for j, (pos, n) in enumerate(seen):
    if n.endswith(".langres"):
        continue
    limit = seen[j + 1][0] if j + 1 < len(seen) else len(en)
    res = []
    for i in range(pos, limit - 13):
        s, e = struct.unpack_from("<ff", en, i)
        if 0 <= s < e < 200 and en[i + 8] in (0x30, 0x31) and en[i + 9:i + 13] == b"\0\0\x80\x3f":
            res.append((round(s, 2), round(e, 2)))
    print(f"  {n[:44]:44} {res[:4]}")

print("\n== Drift: uniform slowdown vs the lines' German position")
factor = (85.516 - 5.076) / 70.0
print(f" uniform factor {factor:.4f}")
worst = 0.0
for t in (8.209, 12.276, 16.443, 22.043, 23.043, 28.009, 39.143, 47.743, 50.743, 53.243, 54.709, 59.376, 61.443, 65.243, 67.276, 69.576, 73.076):
    line = apply_map(table, t)
    uni = 5.076 + (t - 5.076) * factor
    worst = max(worst, abs(line - uni))
    print(f"   English {t:6.2f}: line at {line:6.2f}, long animations at {uni:6.2f}, offset {line - uni:+5.2f}s")
print(f" largest offset {worst:.2f}s")

print("\n== Voice data rate of the original")
_, wavs = read_nctt(uncompressed)
total_bytes = total_seconds = 0
modes = Counter()
with open(uncompressed, "rb") as f:
    for n, (o, s) in wavs.items():
        if n[:-4].isdigit():
            f.seek(o)
            h = f.read(0x60)
            modes[struct.unpack_from("<I", h, 24)[0]] += 1
            word = struct.unpack_from("<Q", h, 0x3C)[0]
            rate = {5: 22050, 7: 32000, 8: 44100, 9: 48000}.get((word >> 1) & 15, 44100)
            total_bytes += s
            total_seconds += (word >> 34) / rate
print(f" modes {modes.most_common()}, {total_bytes / total_seconds / 1024:.1f} kB/s; mine (32 kHz PCM) {64000 / 1024:.1f} kB/s")

print("\n== Remaster: music/sound resources and file structure around a time curve")
a = Ectt(episode, load_key(source, "SMBTaS"))
d = a.read(next(n for n in a.files if n.lower() == "cs_opening.chore"))
body, length_at, length = chore_info(d)
print(" meta header:", d[:16].hex(" "), " file", len(d), " body", body)
print(" body head:", d[body:body + 12].hex(" "), " after name:", d[length_at - 4:length_at + 32].hex(" "))
i = d.find(bytes.fromhex("55 d3 dc a6 0f a3 d6 4b"))
for o in range(i - 150, i + 90, 16):
    print(f"   {o:6} {d[o:o+16].hex(' ')}")
blocks, keys, _ = find_times(d, body, length)
two = 0
curve_at = []
for m in re.finditer(re.escape(bytes.fromhex("55 d3 dc a6 0f a3 d6 4b")), d):
    p = m.start() + 8
    if d[p + 12:p + 20] == bytes.fromhex("22 00 00 00 02 00 00 00"):
        two += 1
        curve_at.append(p + 12)
print(" time curves with two keys:", two)
for c in curve_at:
    k0 = struct.unpack_from("<f", d, c + 8)[0]
    k1 = struct.unpack_from("<f", d, c + 21)[0]
    v0 = struct.unpack_from("<f", d, c + 8 + 9)[0]
    v1 = struct.unpack_from("<f", d, c + 21 + 9)[0]
    print(f"   curve @{c}: {k0:7.3f} -> {v0:5.2f}   {k1:7.3f} -> {v1:5.2f}  (duration {k1 - k0:6.2f}s)")
