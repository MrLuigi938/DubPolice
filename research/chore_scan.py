"""Read-only: how the opening chore times its lines, how a line is laid out in the dialog files,
and what the old German lipsync file looks like."""
import os
import re
import struct
import sys

sys.path.insert(0, sys.argv[1])
from ectt import Ectt
from ttarch4 import Blowfish, load_key

source, arch_dir, old_data, out = sys.argv[2:6]
key = load_key(source, "SMBTaS")
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
os.makedirs(out, exist_ok=True)


def floats(d, lo=0.05, hi=120.0):
    res = []
    for i in range(0, len(d) - 3):
        v = struct.unpack_from("<f", d, i)[0]
        if lo < v < hi and abs(v * 30 - round(v * 30)) < 1e-3:
            res.append((i, round(v, 3)))
    return res


name = "env_office_cs_opening_e1_56.chore"
d = a.read(name)
open(os.path.join(out, name), "wb").write(d)
print(name, len(d))
print(" strings:", [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{6,}", d)][:40])
print(" id 400637953 in chore:", struct.pack("<I", 400637953) in d, " anm crc?", b"400637953" in d)
print(" head:", d[:160].hex(" "))
from build_mod import crc64  # noqa: E402

for rid in (400637953, 400637954, 400637956):
    c = struct.pack("<Q", crc64(f"{rid}.anm".encode()))
    w = struct.pack("<Q", crc64(f"{rid}.wav".encode()))
    print(f" {rid}: anm-crc at", [m.start() for m in re.finditer(re.escape(c), d)][:4], "wav-crc at", [m.start() for m in re.finditer(re.escape(w), d)][:4])
ranges = sorted({v for _, v in floats(d, 0.2, 200)})
print(" 1/30s floats:", ranges[:60], "count", len(ranges))

ld = a.read("env_office.dlog")
t = struct.pack("<I", 400637953)
print("\ndlog env_office size", len(ld), "id at", [m.start() for m in re.finditer(re.escape(t), ld)][:5])
for m in list(re.finditer(re.escape(t), ld))[:1]:
    s = m.start()
    print(" around:", ld[s - 120:s + 140].hex(" "))
    print(" names:", [x.group().decode() for x in re.finditer(rb"[\x20-\x7e]{6,}", ld[s - 400:s + 400])][:12])

lb = a.read("env_office_german.landb")
for rid in (400637953,):
    i = lb.find(struct.pack("<I", rid))
    print("\nlandb entry:", lb[i:i + 170].hex(" "))
    print(" crc anm", struct.pack("<Q", crc64(f"{rid}.anm".encode())).hex(" "), " crc wav", struct.pack("<Q", crc64(f"{rid}.wav".encode())).hex(" "))

# The 2009 German lipsync for the same line.
with open(old_data, "rb") as f:
    k2 = load_key(source, "SM201")
    bf = Blowfish(k2)
    i32 = lambda: struct.unpack("<i", f.read(4))[0]
    version, enc, _u, mode = i32(), i32(), i32(), i32()
    blocks = [i32() for _ in range(i32())]
    _s, _p, _q, hsize = i32(), i32(), i32(), i32()
    table = bf.decrypt(f.read(hsize), "<II")
    base = f.tell()
    p = 0
    n = struct.unpack_from("<i", table, p)[0]; p += 4
    for _ in range(n):
        p += 4 + struct.unpack_from("<i", table, p)[0]
    n = struct.unpack_from("<i", table, p)[0]; p += 4
    files = {}
    for _ in range(n):
        ln = struct.unpack_from("<i", table, p)[0]; p += 4
        nm = table[p:p + ln].decode("latin-1"); p += ln
        _z, off, size = struct.unpack_from("<iIi", table, p); p += 12
        files[nm] = (off, size)
    pos = [base]
    for b in blocks:
        pos.append(pos[-1] + b)
    import zlib

    def rd(off, size):
        o = bytearray()
        while size > 0:
            i, inner = divmod(off, 0x10000)
            f.seek(pos[i])
            c = zlib.decompress(bf.decrypt(f.read(blocks[i]), "<II"))
            part = c[inner:inner + size]
            o += part
            off += len(part)
            size -= len(part)
        return bytes(o)

    old = rd(*files["55964544.anm"])
    open(os.path.join(out, "old_de_55964544.anm"), "wb").write(old)
    print("\nold German anm", len(old), old[:200].hex(" "))
    print(" strings:", [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{6,}", old)][:10])
    print(" near 4.26s:", [(i, round(struct.unpack_from('<f', old, i)[0], 3)) for i in range(0, min(len(old), 400)) if abs(struct.unpack_from('<f', old, i)[0] - 4.26) < 0.2])

new = a.read("400637953.anm")
print("\nremaster anm around length", new[120:200].hex(" "), "file", len(new))
print(" meta size field", struct.unpack_from('<I', new, 4)[0], "total-?", len(new) - struct.unpack_from('<I', new, 4)[0])
