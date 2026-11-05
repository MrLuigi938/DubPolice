"""Read-only: name every resource in the opening chores by matching file-name checksums, with blocks and curves."""
import os
import re
import struct
import sys

sys.path.insert(0, sys.argv[1])
from build_mod import crc64
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch_dir = sys.argv[2:4]
key = load_key(source, "SMBTaS")
names = set()
for f in os.listdir(arch_dir):
    p = os.path.join(arch_dir, f)
    if f.endswith(".ttarch2"):
        with open(p, "rb") as h:
            magic = h.read(4)
        if magic == b"ECTT":
            names.update(Ectt(p, key).files)
        elif magic == b"NCTT":
            names.update(read_nctt(p)[1])
print("known file names:", len(names))
crc = {struct.pack("<Q", crc64(n.lower().encode())): n for n in names}

a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))

for chore in ("env_office_cs_opening_e1_56.chore", "cs_Opening.chore"):
    d = a.read(chore)
    body, _, length = chore_info(d)
    blocks, keys, _ = find_times(d, body, length)
    print(f"\n== {chore}: length {length:.3f}")
    found = []
    for i in range(body, len(d) - 8):
        n = crc.get(d[i:i + 8])
        if n:
            found.append((i, n))
        elif d[i:i + 8] in hashes:
            found.append((i, f"LINE {hashes[d[i:i + 8]]}"))
    seen = []
    for i, n in found:
        if not seen or seen[-1][1] != n:
            seen.append((i, n))
    ordered = sorted(blocks)
    lines = 0
    for j, (i, n) in enumerate(seen):
        limit = seen[j + 1][0] if j + 1 < len(seen) else len(d)
        own = [struct.unpack_from("<ff", d, b) for b in ordered if i < b < limit]
        if n.startswith("LINE"):
            lines += 1
            if lines > 3:
                continue
        print(f"  @{i:6} {n[:48]:48} blocks {[(round(s, 3), round(e, 3)) for s, e in own[:3]]}")
    print("  line resources:", lines)

    if chore.startswith("env_office"):
        at = next((i for i, n in seen if n.lower() == "cs_opening.chore"), None)
        print("  nested cs_Opening record at", at)
        if at is not None:
            for o in range(at - 40, at + 330, 16):
                print(f"    {o:6} {d[o:o+16].hex(' ')}")
            sym = bytes.fromhex("55 d3 dc a6 0f a3 d6 4b")
            for m in re.finditer(re.escape(sym), d[at:at + 1200]):
                c = at + m.start() + 20
                size, count = struct.unpack_from("<II", d, c)
                if size == 8 + 13 * count and 1 <= count < 50:
                    print("    time curve:", [(round(struct.unpack_from('<f', d, c + 8 + 13 * i)[0], 3), round(struct.unpack_from('<f', d, c + 8 + 13 * i + 9)[0], 3)) for i in range(count)])
