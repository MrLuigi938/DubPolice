"""Read-only: which non-voice tracks in the opening changed their duration, and by how much?"""
import os
import struct
import sys

sys.path.insert(0, sys.argv[1])
from build_mod import crc64
from build_mod7 import named_records
from chore_warp import chore_info, find_times
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch_dir, mod = sys.argv[2:5]
key = load_key(source, "SMBTaS")
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
names = set(a.files) | set(Ectt(os.path.join(arch_dir, "SM2_pc_Common_compressed.ttarch2"), key).files)
crc = {struct.pack("<Q", crc64(n.lower().encode())): n.lower() for n in names if n.lower().endswith((".anm", ".chore"))}
_, files = read_nctt(mod)
f = open(mod, "rb")
for name in ("cs_Opening.chore", "env_office_cs_opening_e1_56.chore"):
    o, s = files[name.lower()]
    f.seek(o)
    after = f.read(s)
    before = a.read(name)
    body, _, l0 = chore_info(before)
    _, _, l1 = chore_info(after)
    b0, _, _ = find_times(before, body, l0)
    b1, _, _ = find_times(after, body, l1)
    b0, b1 = sorted(b0), sorted(b1)
    h0 = named_records(before, body, crc)
    print(f"\n== {name}: {l0:.2f}s -> {l1:.2f}s, {len(h0)} named tracks")
    rows = []
    for j, (pos, n) in enumerate(h0):
        limit = h0[j + 1][0] if j + 1 < len(h0) else len(before)
        idx = [i for i, b in enumerate(b0) if pos < b < limit]
        for i in idx[:3]:
            s0, e0 = struct.unpack_from("<ff", before, b0[i])
            s1, e1 = struct.unpack_from("<ff", after, b1[i])
            factor = (e1 - s1) / (e0 - s0) if e0 > s0 else 1.0
            rows.append((factor, n, s0, e0, s1, e1))
    moved = [r for r in rows if abs(r[0] - 1) > 0.02]
    print(f"   tracks stretched by more than 2%: {len(moved)} of {len(rows)}")
    for factor, n, s0, e0, s1, e1 in sorted(moved, key=lambda r: -r[0])[:22]:
        print(f"   x{factor:4.2f}  {n[:44]:44} {s0:7.2f}-{e0:7.2f} ({e0 - s0:5.2f}s) -> {s1:7.2f}-{e1:7.2f}")
    nested = [r for r in rows if r[1].endswith(".chore")]
    print("   nested chores:", [(r[1], round(r[0], 2)) for r in nested])
