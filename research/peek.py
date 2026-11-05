"""Read-only: show the remaster landb layout and list the old compressed data archive."""
import os
import re
import struct
import sys
import zlib
from collections import Counter

sys.path.insert(0, sys.argv[1])
from ttarch4 import Blowfish, load_key

source, landb, old_german_data, old_data, out = sys.argv[2:7]

d = open(landb, "rb").read()
print("landb bytes", len(d))
print(d[:520].hex(" "))
print(re.sub(rb"[^\x20-\x7e\xc0-\xff]+", b" | ", d[:1800]).decode("latin-1"))


def old_files(path, key):
    with open(path, "rb") as f:
        i32 = lambda: struct.unpack("<i", f.read(4))[0]
        version, enc, _u, mode = i32(), i32(), i32(), i32()
        blocks = [i32() for _ in range(i32())]
        data_size, _p1, _p2, hsize = i32(), i32(), i32(), i32()
        print("\n", os.path.basename(path), "version", version, "mode", mode, "blocks", len(blocks), "hdr", hsize)
        raw = f.read(hsize)
        base = f.tell()
        print(" first blocks", blocks[:6], "total", sum(blocks), "data", data_size)
        bf = Blowfish(key)
        table = bf.decrypt(raw, "<II")
        p = 0
        rd = lambda: struct.unpack_from("<i", table, p)[0]
        n = rd(); p += 4
        dirs = []
        for _ in range(n):
            ln = rd(); p += 4
            dirs.append(table[p:p + ln].decode("latin-1")); p += ln
        n = rd(); p += 4
        files = []
        for _ in range(n):
            ln = rd(); p += 4
            name = table[p:p + ln].decode("latin-1"); p += ln
            _z, off, size = struct.unpack_from("<iIi", table, p); p += 12
            files.append((name, off, size))
        print(" dirs", dirs[:8], " files", len(files), Counter(x[0].rsplit('.', 1)[-1].lower() for x in files).most_common(14))
        print(" samples", [x for x in files if x[0].lower().endswith(("landb", "langdb", "dlog"))][:8])
        pos = base
        spans = []
        for b in blocks:
            spans.append((pos, b))
            pos += b
        if spans:
            f.seek(spans[0][0])
            c = f.read(spans[0][1])
            print(" chunk0 raw head", c[:16].hex(" "))
            plain = bf.decrypt(c, "<II")
            print(" chunk0 dec head", plain[:16].hex(" "))
            for tag, buf in (("raw", c), ("dec", plain)):
                for w in (-15, 15):
                    try:
                        z = zlib.decompress(buf, w)
                        print(" ok", tag, w, len(z), z[:48].hex(" "))
                    except zlib.error:
                        pass


key = load_key(source, "SM201")
old_files(old_german_data, key)
old_files(old_data, key)
