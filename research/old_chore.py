"""Read-only: decode the 2009 English and German cs_opening chores and compare their timing."""
import os
import re
import struct
import sys
import zlib

sys.path.insert(0, sys.argv[1])
from ttarch4 import Blowfish, load_key

source, ms_german, data_en, ms_en, out = sys.argv[2:7]
key = load_key(source, "SM201")
bf = Blowfish(key)
os.makedirs(out, exist_ok=True)


def table(path):
    f = open(path, "rb")
    i32 = lambda: struct.unpack("<i", f.read(4))[0]
    _v, _e, _u, mode = i32(), i32(), i32(), i32()
    blocks = [i32() for _ in range(i32())]
    _s, _p, _q, hsize = i32(), i32(), i32(), i32()
    t = bf.decrypt(f.read(hsize), "<II")
    base = f.tell()
    p = 0
    n = struct.unpack_from("<i", t, p)[0]; p += 4
    for _ in range(n):
        p += 4 + struct.unpack_from("<i", t, p)[0]
    n = struct.unpack_from("<i", t, p)[0]; p += 4
    files = {}
    for _ in range(n):
        ln = struct.unpack_from("<i", t, p)[0]; p += 4
        nm = t[p:p + ln].decode("latin-1"); p += ln
        _z, off, size = struct.unpack_from("<iIi", t, p); p += 12
        files[nm.lower()] = (off, size)
    return f, blocks, base, files


def read(path, name):
    f, blocks, base, files = table(path)
    off, size = files[name]
    if not blocks:
        f.seek(base + off)
        return f.read(size)
    pos = [base]
    for b in blocks:
        pos.append(pos[-1] + b)
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


def unmeta(d):
    if d[:4] != b"\xaa\xde\xaf\x64":
        return d
    body = bytearray(d[4:])
    size, crypt, clean = 0x100, 8, 0x18
    for i in range(len(body) // size):
        at = i * size
        chunk = bytes(body[at:at + size])
        if i % crypt == 0:
            body[at:at + size] = bf.decrypt(chunk, "<II")
        elif i % clean == 0 and i > 0:
            pass
        else:
            body[at:at + size] = bytes(b ^ 0xFF for b in chunk)
    return d[:4] + bytes(body)


def summary(d, label):
    print(f"\n== {label}: {len(d)} bytes")
    print(" strings:", [m.group().decode() for m in re.finditer(rb"[\x20-\x7e]{6,}", d)][:16])
    # Time blocks: start, end, loop char, scale 1.0
    blocks = []
    for i in range(0, len(d) - 13):
        s, e = struct.unpack_from("<ff", d, i)
        if 0 <= s < e < 400 and d[i + 8] in (0x30, 0x31) and d[i + 9:i + 13] == b"\0\0\x80\x3f":
            blocks.append((round(s, 3), round(e, 3)))
    print(" blocks found:", len(blocks))
    return blocks


ge = unmeta(read(ms_german, "cs_opening.chore"))
try:
    en = unmeta(read(data_en, "cs_opening.chore"))
except KeyError:
    en = unmeta(read(ms_en, "cs_opening.chore"))
open(os.path.join(out, "old_de_cs_opening.chore"), "wb").write(ge)
open(os.path.join(out, "old_en_cs_opening.chore"), "wb").write(en)
bg = summary(ge, "German")
be = summary(en, "English")
print("\nsame block count:", len(bg) == len(be))
print("\n  #   English start-end (len)     German start-end (len)     shift")
for i, (a, b) in enumerate(zip(be, bg)):
    print(f" {i:3} {a[0]:8.3f}-{a[1]:8.3f} ({a[1] - a[0]:6.3f})   {b[0]:8.3f}-{b[1]:8.3f} ({b[1] - b[0]:6.3f})   {b[0] - a[0]:+7.3f}")
