"""Read-only: active flags of outer lines; compare old English and German scene audio; list remaster scene audio."""
import os
import struct
import sys

sys.path.insert(0, sys.argv[1])
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key, read_table

source, arch_dir, ms_en, ms_de = sys.argv[2:6]
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), load_key(source, "SMBTaS"))
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))
for name in ("env_office_cs_opening_e1_56.chore", "cs_Opening.chore", "env_office_use_bearHead_e1_5.chore", "env_office_use_robotKey_e1_4.chore"):
    d = a.read(name)
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    flags = [(r % 1000, d[b + 13:b + 21].decode("latin-1")) for r, _, b, _ in line_resources(d, hashes, blocks)]
    print(name, flags)

key = load_key(source, "SM201")
def listing(path):
    meta, _, files = read_table(path, key)
    return meta, {n.lower(): (o, s) for n, o, s in files}, path
me, en, pe = listing(ms_en)
md, de, pd = listing(ms_de)
print("\nold audio files EN/DE:", sum(n.endswith(".aud") for n in en), sum(n.endswith(".aud") for n in de))
print(" names in German only:", sorted(n for n in de if n.endswith(".aud") and n not in en)[:10])
print(" names in English only:", sorted(n for n in en if n.endswith(".aud") and n not in de)[:10])
same = diff = 0
different = []
for n in sorted(de):
    if n.endswith(".aud") and n in en:
        with open(pe, "rb") as f:
            f.seek(me["data_start"] + en[n][0]); x = f.read(en[n][1])
        with open(pd, "rb") as f:
            f.seek(md["data_start"] + de[n][0]); y = f.read(de[n][1])
        if x == y:
            same += 1
        else:
            diff += 1
            different.append((n, len(x), len(y)))
print(" identical:", same, " different:", diff)
print(" different files:", different[:30])
for n in ("cs_opening_enter_office.aud", "mus_opening.aud"):
    print(" ", n, "EN", en.get(n), "DE", de.get(n))
if "cs_opening_enter_office.aud" in en:
    with open(pe, "rb") as f:
        f.seek(me["data_start"] + en["cs_opening_enter_office.aud"][0]); x = f.read(64)
    print("  head:", x.hex(" "))
    b = x[20:]
    print("  EN duration float:", struct.unpack_from("<f", b, 1)[0])
if "cs_opening_enter_office.aud" in de:
    with open(pd, "rb") as f:
        f.seek(md["data_start"] + de["cs_opening_enter_office.aud"][0]); x = f.read(64)
    print("  DE duration float:", struct.unpack_from("<f", x[20:], 1)[0])

for arch in ("SM2_pc_SamMax201_uncompressed.ttarch2", "SM2_pc_Common_uncompressed.ttarch2"):
    _, files = read_nctt(os.path.join(arch_dir, arch))
    for n in ("cs_opening_enter_office.wav", "mus_opening.wav"):
        if n in files:
            with open(os.path.join(arch_dir, arch), "rb") as f:
                f.seek(files[n][0]); h = f.read(0x60)
            word = struct.unpack_from("<Q", h, 0x3C)[0]
            rate = {5: 22050, 7: 32000, 8: 44100, 9: 48000}.get((word >> 1) & 15, 44100)
            print(f"  remaster {arch}: {n}: {(word >> 34) / rate:.3f}s, mode {struct.unpack_from('<I', h, 24)[0]}")
