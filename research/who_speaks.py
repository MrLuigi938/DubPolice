"""Read-only: compare one line's record in the outer and nested chore, list curves with their property names,
and look at how the 2009 game organised the same scene."""
import os
import re
import struct
import sys
import zlib

sys.path.insert(0, sys.argv[1])
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from ttarch4 import Blowfish, load_key

source, arch_dir, old_data, old_ms = sys.argv[2:6]
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), load_key(source, "SMBTaS"))
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))


def record(d, rid):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    for r, pos, block, _ in line_resources(d, hashes, blocks):
        if r == rid:
            return pos, block


outer = a.read("env_office_cs_opening_e1_56.chore")
inner = a.read("cs_Opening.chore")
rid = 400637953
po, bo = record(outer, rid)
pi, bi = record(inner, rid)
ro = outer[po - 40:bo + 40]
ri = inner[pi - 40:bi + 40]
print("record sizes", len(ro), len(ri))
diffs = [i for i in range(min(len(ro), len(ri))) if ro[i] != ri[i]]
print("differing byte positions (relative to record):", len(diffs))
i = 0
groups = []
while i < len(diffs):
    j = i
    while j + 1 < len(diffs) and diffs[j + 1] - diffs[j] <= 4:
        j += 1
    groups.append((diffs[i], diffs[j]))
    i = j + 1
for x, y in groups[:60]:
    a0 = max(0, x - (x % 4))
    print(f"   +{x:4}-{y:4}  outer {ro[x:y + 1].hex(' ')[:48]:48}  inner {ri[x:y + 1].hex(' ')[:48]}")
print("\nFlags after the block (outer):", outer[bo + 13:bo + 30], " (inner):", inner[bi + 13:bi + 30])

# How do both describe their lines overall?
for label, d in (("outer", outer), ("inner", inner)):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    rows = sorted((struct.unpack_from("<f", d, b)[0], r) for r, _, b, _ in line_resources(d, hashes, blocks))
    print(label, [(round(s, 2), r % 1000) for s, r in rows])

# The 2009 game: which chores name these lines?
key = load_key(source, "SM201")
bf = Blowfish(key)
for path in (old_data, old_ms):
    f = open(path, "rb")
    i32 = lambda: struct.unpack("<i", f.read(4))[0]
    _v, _e, _u, _mode = i32(), i32(), i32(), i32()
    blk = [i32() for _ in range(i32())]
    _s, _p, _q, hsize = i32(), i32(), i32(), i32()
    t = bf.decrypt(f.read(hsize), "<II")
    base = f.tell()
    p = 0
    n = struct.unpack_from("<i", t, p)[0]; p += 4
    for _ in range(n):
        p += 4 + struct.unpack_from("<i", t, p)[0]
    n = struct.unpack_from("<i", t, p)[0]; p += 4
    names = {}
    for _ in range(n):
        ln = struct.unpack_from("<i", t, p)[0]; p += 4
        nm = t[p:p + ln].decode("latin-1"); p += ln
        _z, off, size = struct.unpack_from("<iIi", t, p); p += 12
        names[nm.lower()] = (off, size)
    print("\n", os.path.basename(path), "names with 'opening':", sorted(n for n in names if "opening" in n)[:30])
    print("   env_office chores:", sorted(n for n in names if n.startswith("env_office") and n.endswith(".chore"))[:12])
    print("   dialog files:", sorted(n for n in names if n.endswith((".dlg", ".dlog")))[:12])
