"""Read-only: find every timed block in a chore, tie line blocks to dialog lines, list what else holds times."""
import re
import struct
import sys
from collections import Counter

d = open(sys.argv[1], "rb").read()
landb = open(sys.argv[2], "rb").read()
types = struct.unpack_from("<I", d, 16)[0]
body = 20 + 12 * types
name_len = struct.unpack_from("<I", d, body + 4)[0]
p = body + 8 + name_len
print("after name:", d[p:p + 32].hex(" "))
flags, length, nres, nagents = struct.unpack_from("<IfII", d, p)
print(f"flags {flags} length {length:.3f} resources {nres} agents {nagents}")

# Timed blocks: size, count, then count * (start, end, loop char, scale).
blocks = []
for i in range(body, len(d) - 21):
    size, count = struct.unpack_from("<II", d, i)
    if 1 <= count <= 64 and size == 8 + 13 * count and i + size <= len(d):
        rows = []
        ok = True
        for k in range(count):
            s, e, loop, scale = struct.unpack_from("<ffcf", d, i + 8 + 13 * k)
            if not (-1 <= s <= length + 1 and s <= e <= length + 60 and loop in (b"0", b"1") and 0.01 < scale < 100):
                ok = False
                break
            rows.append((round(s, 3), round(e, 3), loop.decode(), round(scale, 3)))
        if ok:
            blocks.append((i, rows))
print("block lists:", len(blocks), "blocks:", sum(len(r) for _, r in blocks), "scales:", Counter(x[3] for _, r in blocks for x in r).most_common(5))

# Dialog line hashes from the landb: id, 8-byte hash, id again.
lines = {}
for i in range(0, len(landb) - 24):
    if landb[i + 16:i + 20] == b"\0\0\0\0" and landb[i + 20:i + 24] == b"\x0c\0\0\0" and landb[i:i + 4] == landb[i + 12:i + 16]:
        lines[landb[i + 4:i + 12]] = struct.unpack_from("<I", landb, i)[0]
print("landb lines:", len(lines))

positions = []
for h, rid in lines.items():
    for m in re.finditer(re.escape(h), d):
        positions.append((m.start(), rid))
positions.sort()
print("line hash hits:", len(positions), positions[:12])

for off, rows in blocks[:70]:
    near = [rid for pos, rid in positions if off - 1400 < pos < off]
    print(f"  @{off:6} {rows[:3]}  {'line ' + str(near[-1]) if near else ''}")

print("\nheader region 700-1400:")
for o in range(700, 1400, 16):
    print(f" {o:6} {d[o:o+16].hex(' ')}  {re.sub(rb'[^ -~]', b'.', d[o:o+16]).decode()}")
