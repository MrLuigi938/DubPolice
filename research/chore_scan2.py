"""Read-only: lay out the opening chore: header, repeating blocks, and every float that could be a time."""
import re
import struct
import sys

d = open(sys.argv[1], "rb").read()
types = struct.unpack_from("<I", d, 16)[0]
body = 20 + 12 * types
print("size", len(d), "types", types, "body starts", body)
for o in range(body, body + 200, 16):
    print(f" {o:6} {d[o:o+16].hex(' ')}  {re.sub(rb'[^ -~]', b'.', d[o:o+16]).decode()}")

print("\nascii strings with offsets:")
for m in list(re.finditer(rb"[\x20-\x7e]{5,}", d))[:40]:
    print(f"  {m.start():7} {m.group().decode()[:70]}")

marker = bytes.fromhex(re.search(rb"kxRS\]\^", d).group().hex())
hits = [m.start() for m in re.finditer(re.escape(marker), d)]
print("\nrepeating marker", marker, "count", len(hits), "first gaps", [b - a for a, b in zip(hits, hits[1:])][:30])
for h in hits[:3]:
    print(f"\n @ {h}")
    for o in range(h - 96, h + 112, 16):
        print(f"   {o:7} {d[o:o+16].hex(' ')}  {re.sub(rb'[^ -~]', b'.', d[o:o+16]).decode()}")

print("\ncumulative English targets vs chore floats")
lens = [2.933, 3.70, 3.43, 5.233, 0.133, 4.60, 10.433, 5.17, 2.70, 0.60, 1.00, 4.43]
vals = []
for i in range(body, len(d) - 3):
    v = struct.unpack_from("<f", d, i)[0]
    if 0.01 < v < 300:
        vals.append((i, v))
for single in lens:
    print(f"  length {single:7.3f}:", [(i, round(v, 3)) for i, v in vals if abs(v - single) < 0.012][:6])
c = 0
for single in lens:
    c += single
    print(f"  cumul  {c:7.3f}:", [(i, round(v, 3)) for i, v in vals if abs(v - c) < 0.05][:6])
