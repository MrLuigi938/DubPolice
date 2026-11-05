"""Read-only: decrypt resource descriptors and show how a remaster FSB5 and an old vox are laid out."""
import os
import struct
import sys

sys.path.insert(0, sys.argv[1])
from ectt import Blowfish7
from nctt import read_nctt
from ttarch4 import load_key, read_table

source, arch_dir, old_de, new_id, old_id = sys.argv[2:7]
bf = Blowfish7(load_key(source, "SMBTaS"))

for name in ("_resdesc_50_German.lua", "_resdesc_50_SamMax201.lua", "_resdesc_50_English.lua"):
    d = open(os.path.join(arch_dir, name), "rb").read()
    print("\n===", name, d[:4])
    print(bf.decrypt(d[4:], "<II").decode("latin-1").replace("\r", ""))

_, files = read_nctt(os.path.join(arch_dir, "SM2_pc_SamMax201_uncompressed.ttarch2"))
o, s = files[new_id + ".wav"]
with open(os.path.join(arch_dir, "SM2_pc_SamMax201_uncompressed.ttarch2"), "rb") as f:
    f.seek(o)
    fsb = f.read(s)
ver, n, shdr, nm, data, mode = struct.unpack_from("<6I", fsb, 4)
print("\nFSB5 size", s, "ver", ver, "n", n, "sampleHdr", shdr, "names", nm, "data", data, "mode", mode)
print(" main header:", fsb[:0x3C].hex(" "))
print(" sample+name:", fsb[0x3C:0x3C + shdr + nm][:96].hex(" "))
word = struct.unpack_from("<Q", fsb, 0x3C)[0]
print(" extra", word & 1, "rate", (word >> 1) & 15, "chan", (word >> 5) & 1, "dataoff", (word >> 7) & 0x7FFFFFF, "samples", word >> 34)

meta, _, lst = read_table(old_de, load_key(source, "SM201"))
e = {n.lower(): (o, s) for n, o, s in lst}
o, s = e[old_id + ".vox"]
with open(old_de, "rb") as f:
    f.seek(meta["data_start"] + o)
    v = f.read(s)
print("\nvox size", s)
print(" head:", v[:20].hex(" "))
b = v[20:]
dur = struct.unpack_from("<f", b, 1)[0]
dsize, frame, rate, smode, block, count = struct.unpack_from("<6I", b, 5)
print(" flag", b[0], "duration", dur, "dataSize", dsize, "frame", frame, "rate", rate, "mode", smode, "tableBlock", block, "count", count)
tab = struct.unpack_from(f"<{count}I", b, 29)
print(" offsets:", tab[:12], "... last", tab[-1])
print(" packet lengths:", [tab[i + 1] - tab[i] for i in range(min(12, count - 1))])
start = 29 + 4 * count
print(" after table offset", start, "remaining", len(b) - start, "next bytes", b[start:start + 24].hex(" "))
print(" samples implied", count * frame, "seconds", count * frame / rate)
