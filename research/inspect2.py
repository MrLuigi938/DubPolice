"""Read-only: archive table details, all set descriptors, and where the candidate lines live."""
import glob
import os
import struct
import sys

sys.path.insert(0, sys.argv[1])
from ectt import Blowfish7, Ectt
from ttarch4 import load_key

source, arch_dir, landb_dir = sys.argv[2:5]
key = load_key(source, "SMBTaS")
bf = Blowfish7(key)

for p in sorted(glob.glob(os.path.join(arch_dir, "_resdesc_*.lua"))):
    t = bf.decrypt(open(p, "rb").read()[4:], "<II").decode("latin-1").replace("\r", "")
    keep = [l.strip() for l in t.split("\n") if l.strip().startswith(("set.name", "set.priority", "set.enableMode", "set.gameDataEnableMode", "set.gameDataPriority"))]
    print(os.path.basename(p), keep if keep else ascii(t[:300]))


def crc64(data):
    c = 0
    for b in data:
        c ^= b << 56
        for _ in range(8):
            c = ((c << 1) ^ 0x42F0E1EBA9EA3693) & 0xFFFFFFFFFFFFFFFF if c >> 63 else (c << 1) & 0xFFFFFFFFFFFFFFFF
    return c


path = os.path.join(arch_dir, "SM2_pc_SamMax201_uncompressed.ttarch2")
with open(path, "rb") as f:
    f.read(12)
    sub = f.read(4)
    name_size, count = struct.unpack("<II", f.read(8))
    table = f.read(28 * count)
    names = f.read(name_size)
    base = f.tell()
    size = os.path.getsize(path)
    print("\n", sub, "name_size", hex(name_size), "count", count, "data base", hex(base), "file", size)
    rows = []
    for i in range(count):
        crc, off, sz, unk, blk, nm = struct.unpack_from("<QQIIHH", table, 28 * i)
        p = blk * 0x10000 + nm
        rows.append((crc, off, sz, unk, blk, nm, names[p:names.index(b"\0", p)].decode()))
    for r in rows[:4]:
        print("  crc", hex(r[0]), "calc", hex(crc64(r[6].lower().encode())), r[1:])
    print("  sorted by crc:", all(rows[i][0] < rows[i + 1][0] for i in range(count - 1)))
    print("  unk values:", {r[3] for r in rows})
    print("  name table used", max(r[4] * 0x10000 + r[5] + len(r[6]) + 1 for r in rows))
    print("  sorted by offset gap:", sorted(rows, key=lambda r: r[1])[0][1], "gaps", {b[1] - a[1] - a[2] for a, b in zip(sorted(rows, key=lambda r: r[1]), sorted(rows, key=lambda r: r[1])[1:])})
    print("  data end vs size", max(r[1] + r[2] for r in rows) + base, size)
    print("  12-byte header size field", struct.unpack("<Q", open(path, "rb").read(12)[4:])[0], "file-12", size - 12)

# Which conversation holds the first voice lines, and how the episode opens.
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
target = struct.pack("<I", 400592897)
for p in glob.glob(os.path.join(landb_dir, "*_english.landb")):
    if target in open(p, "rb").read():
        print("\nline 400592897 is in", os.path.basename(p))
print("first file names with ep opening:", [n for n in a.files if n.lower().startswith(("cs_", "module_")) and n.lower().endswith(".dlog")][:20])
print("dlogs:", sorted(n for n in a.files if n.lower().endswith(".dlog"))[:40])
