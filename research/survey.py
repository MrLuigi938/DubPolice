"""Read-only: name collisions between episodes, how episodes pick resource sets, and where shared voices live."""
import os
import re
import struct
import sys
from collections import Counter, defaultdict

sys.path.insert(0, sys.argv[1])
from chore_warp import line_hashes
from ectt import Blowfish7, Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch = sys.argv[2:4]
key = load_key(source, "SMBTaS")
bf = Blowfish7(key)
eps = ["201", "202", "203", "204", "205"]
archives = {e: Ectt(os.path.join(arch, f"SM2_pc_SamMax{e}_compressed.ttarch2"), key) for e in eps}
common = Ectt(os.path.join(arch, "SM2_pc_Common_compressed.ttarch2"), key)
project = Ectt(os.path.join(arch, "SM2_pc_Project_compressed.ttarch2"), key)

where = defaultdict(list)
for e, a in archives.items():
    for n in a.files:
        where[n.lower()].append(e)
dups = {n: v for n, v in where.items() if len(v) > 1}
print("files in more than one episode:", len(dups), Counter(n.rsplit(".", 1)[-1] for n in dups).most_common(10))
print(" chores in several episodes:", [n for n in dups if n.endswith(".chore")][:12])
print(" anm numeric in several:", sum(n.endswith(".anm") and n[:-4].isdigit() for n in dups))

ids = {}
for e, a in archives.items():
    _, w = read_nctt(os.path.join(arch, f"SM2_pc_SamMax{e}_uncompressed.ttarch2"))
    nums = {n[:-4] for n in w if n[:-4].isdigit()}
    ids[e] = nums
    landb = sum(n.endswith("_english.landb") for n in a.files)
    print(f" ep{e}: numeric voices {len(nums)}, id range {min(nums)}-{max(nums)}, landb {landb}, chores {sum(n.endswith('.chore') for n in a.files)}")
all_ids = Counter(i for s in ids.values() for i in s)
print(" voice ids in several episodes:", sum(v > 1 for v in all_ids.values()))

_, cw = read_nctt(os.path.join(arch, "SM2_pc_Common_uncompressed.ttarch2"))
cn = {n[:-4] for n in cw if n[:-4].isdigit()}
print(" common voices:", len(cn), sorted(cn)[:8])
print(" common landb:", [n for n in common.files if n.endswith("_english.landb")][:12])
print(" common chores:", sum(n.endswith(".chore") for n in common.files))
hc = {}
for n in common.files:
    if n.endswith("_english.landb"):
        hc.update(line_hashes(common.read(n)))
print(" common line entries:", len(hc), " voiced among them:", len({str(v) for v in hc.values()} & cn))
inside = {e: sum(1 for n in a.files if n.endswith(".chore") and any(h in a.read(n) for h in list(hc)[:0])) for e, a in archives.items()}

print("\n== Sub-project property files")
for label, a in list(archives.items()) + [("common", common), ("project", project)]:
    props = [n for n in a.files if re.fullmatch(r"(sammax20\d|subproject|episode|menu|boot)\.prop", n.lower())]
    for n in props:
        d = a.read(n)
        print(f"  {label}: {n} {len(d)} bytes:", [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{4,}", d)][:14])
for name in ("SamMax201.prop", "subProject.prop"):
    for label, a in list(archives.items())[:1] + [("project", project), ("common", common)]:
        if name in a.files:
            d = a.read(name)
            print(f"\n  HEX {label}/{name}:", d.hex(" "))
