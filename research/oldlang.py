"""Read-only: extract the 2009 .langdb files from the compressed data archive."""
import os
import re
import struct
import sys
import zlib

sys.path.insert(0, sys.argv[1])
from ttarch4 import Blowfish, load_key

source, old_data, out = sys.argv[2:5]
key = load_key(source, "SM201")
bf = Blowfish(key)
os.makedirs(out, exist_ok=True)

with open(old_data, "rb") as f:
    i32 = lambda: struct.unpack("<i", f.read(4))[0]
    version, enc, _u, mode = i32(), i32(), i32(), i32()
    blocks = [i32() for _ in range(i32())]
    data_size, _p1, _p2, hsize = i32(), i32(), i32(), i32()
    raw = f.read(hsize)
    base = f.tell()
    table = bf.decrypt(raw, "<II")
    p = 0
    def rd():
        return struct.unpack_from("<i", table, p)[0]
    n = rd(); p += 4
    for _ in range(n):
        p += 4 + rd()
    n = rd(); p += 4
    files = {}
    for _ in range(n):
        ln = rd(); p += 4
        name = table[p:p + ln].decode("latin-1"); p += ln
        _z, off, size = struct.unpack_from("<iIi", table, p); p += 12
        files[name] = (off, size)
    positions = [base]
    for b in blocks:
        positions.append(positions[-1] + b)
    CHUNK = 0x10000

    def chunk(i):
        f.seek(positions[i])
        return zlib.decompress(bf.decrypt(f.read(blocks[i]), "<II"))

    def read(off, size):
        o = bytearray()
        while size > 0:
            i, inner = divmod(off, CHUNK)
            part = chunk(i)[inner:inner + size]
            o += part
            off += len(part)
            size -= len(part)
        return bytes(o)

    for name in ("english.langdb", "german.langdb"):
        d = read(*files[name])
        open(os.path.join(out, name), "wb").write(d)
        print("\n==", name, len(d))
        print(d[:300].hex(" "))
        needle = struct.pack("<I", 27630080)
        hits = [m.start() for m in re.finditer(re.escape(needle), d)]
        print("hits for id 27630080:", hits[:5])
        for h in hits[:2]:
            s = max(0, h - 40)
            print(" hex", d[s:h + 200].hex(" "))
            print(" txt", re.sub(rb"[^\x20-\x7e\xc0-\xff]+", b" | ", d[s:h + 300]).decode("latin-1"))
        print(" ascii vox names?", re.findall(rb"[0-9]{6,10}\.[a-z]{3}", d)[:5])
