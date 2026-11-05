"""Read-only: find where the remaster stores each line's length (searching for the duration as a float)."""
import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from ectt import Ectt
from ttarch4 import load_key

source, arch_dir, out = sys.argv[2:5]
key = load_key(source, "SMBTaS")
os.makedirs(out, exist_ok=True)
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
names = sorted(a.files)
print("numeric anm:", sum(1 for n in names if n.lower().endswith(".anm") and n[:-4].isdigit()))
print("chore name samples:", [n for n in names if n.endswith(".chore")][:10])
print("chores mentioning 400637953:", [n for n in names if "400637953" in n])
print("all files with 40063795x:", [n for n in names if "40063795" in n][:12])
office = [n for n in names if n.lower().startswith("env_office") and n.endswith(".chore")]
print("env_office chores:", len(office), office[:14])

# (id, English seconds from the remaster FSB)
targets = {400637953: 2.94, 400637956: 5.34, 400637959: 10.60}
for rid, sec in targets.items():
    n = f"{rid}.anm"
    if n not in a.files:
        print(rid, "no anm")
        continue
    d = a.read(n)
    open(os.path.join(out, n), "wb").write(d)
    print(f"\n== {n} {len(d)} bytes  magic {d[:4]}")
    print(d[:220].hex(" "))
    print(" strings:", [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{5,}", d)][:12])
    hits = []
    for i in range(0, len(d) - 3):
        v = struct.unpack_from("<f", d, i)[0]
        if abs(v - sec) < 0.15:
            hits.append((i, round(v, 3)))
    print(" floats near duration:", hits[:10])

# Which other file types mention the line ID or its duration?
needle = struct.pack("<I", 400637953)
found = Counter()
examples = {}
for n in names:
    e = n.rsplit(".", 1)[-1].lower()
    if e not in ("dlog", "chore", "landb", "prop", "lua", "scene"):
        continue
    d = a.read(n)
    if needle in d or b"400637953" in d:
        found[e] += 1
        examples.setdefault(e, []).append(n)
print("\nfiles mentioning the ID:", found.most_common(), {k: v[:5] for k, v in examples.items()})
for n in examples.get("chore", [])[:2]:
    d = a.read(n)
    open(os.path.join(out, n), "wb").write(d)
    print(" chore", n, len(d), d[:64].hex(" "))
