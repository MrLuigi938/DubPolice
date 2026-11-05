"""Read-only: find time-keyed records my scanner does not move, with the property and track they belong to."""
import os
import re
import struct
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from build_mod import crc64
from build_mod8 import named_records
from chore_warp import chore_info, find_times
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch_dir = sys.argv[2:4]
key = load_key(source, "SMBTaS")
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
names = set(a.files) | set(Ectt(os.path.join(arch_dir, "SM2_pc_Common_compressed.ttarch2"), key).files)
for f in ("SM2_pc_SamMax201_uncompressed.ttarch2", "SM2_pc_Common_uncompressed.ttarch2"):
    names |= set(read_nctt(os.path.join(arch_dir, f))[1])
crc = {struct.pack("<Q", crc64(n.lower().encode())): n.lower() for n in names if n.lower().endswith((".anm", ".chore", ".wav"))}

for chore in ("cs_Opening.chore", "env_office_cs_opening_e1_56.chore"):
    d = a.read(chore)
    body, _, length = chore_info(d)
    blocks, keys, stats = find_times(d, body, length)
    known = set(keys)
    for b in blocks:
        known.update((b, b + 4))
    print(f"\n== {chore}: length {length:.2f}, known key times {len(keys)}, {dict(stats)}")
    missed = []
    for i in range(body, len(d) - 9):
        if i in known:
            continue
        t = struct.unpack_from("<f", d, i)[0]
        if 0.0 < t <= length + 1 and d[i + 4] in (0x30, 0x31) and struct.unpack_from("<I", d, i + 5)[0] <= 8:
            missed.append((i, t))
    print(" records that look like unmoved keys:", len(missed))
    records = named_records(d, body, crc)
    by_track = Counter()
    for i, t in missed:
        owner = [n for p, n in records if p < i]
        by_track[owner[-1] if owner else "(start)"] += 1
    print(" by track:", by_track.most_common(20))
    for i, t in missed[:45]:
        owner = [n for p, n in records if p < i]
        print(f"   @{i:6} t={t:7.3f}  next {d[i + 4:i + 22].hex(' ')}  prev {d[i - 12:i].hex(' ')}  [{(owner[-1] if owner else '')[:30]}]")
