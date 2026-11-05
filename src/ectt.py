"""Read-only access to encrypted, compressed .ttarch2 (ECTT) archives."""
import os
import struct
import sys
import zlib
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttarch4 import Blowfish, load_key


class Blowfish7(Blowfish):
    """Telltale's variant for version 7 and later archives."""

    def __init__(self, key):
        w = list(self._init)
        self.P = w[:18]
        self.S = [w[18 + 256 * i: 18 + 256 * (i + 1)] for i in range(4)]
        j = 0
        for i in range(18):
            d = 0
            for _ in range(4):
                d = (d << 8) | key[j % len(key)]
                j += 1
            self.P[i] ^= d
        x = self.S[0][118]
        self.S[0][118] = int.from_bytes(x.to_bytes(4, "big"), "little")
        l = r = 0
        for i in range(0, 18, 2):
            l, r = self._enc(l, r)
            self.P[i], self.P[i + 1] = l, r
        for s in self.S:
            for i in range(0, 256, 2):
                l, r = self._enc(l, r)
                s[i], s[i + 1] = l, r
        self.P7 = list(self.P)
        self.P7[1], self.P7[2], self.P7[3], self.P7[4] = self.P[3], self.P[4], self.P[1], self.P[2]

    def _dec(self, l, r):
        P = self.P7
        s0, s1, s2, s3 = self.S
        l ^= self.P[17]
        for i in range(16, 0, -2):
            r ^= (((((s0[l >> 24] + s1[(l >> 16) & 255]) & 0xFFFFFFFF)
                    ^ s2[(l >> 8) & 255]) + s3[l & 255]) & 0xFFFFFFFF) ^ P[i]
            l ^= (((((s0[r >> 24] + s1[(r >> 16) & 255]) & 0xFFFFFFFF)
                    ^ s2[(r >> 8) & 255]) + s3[r & 255]) & 0xFFFFFFFF) ^ P[i - 1]
        r ^= self.P[0]
        return r, l


class Ectt:
    def __init__(self, path, key):
        self.f = open(path, "rb")
        self.bf = Blowfish7(key)
        magic = self.f.read(4)
        if magic != b"ECTT":
            raise SystemExit(f"{path}: unsupported {magic!r}")
        self.chunk, count = struct.unpack("<II", self.f.read(8))
        offs = struct.unpack(f"<{count + 1}Q", self.f.read(8 * (count + 1)))
        self.spans = [(offs[i], offs[i + 1] - offs[i]) for i in range(count)]
        self.cache = {}
        head = self._read(0, 12)
        self.sub = head[:4]
        name_size, n = struct.unpack_from("<II", head, 4)
        table = self._read(12, 28 * n + name_size)
        names = table[28 * n:]
        self.data = 12 + 28 * n + name_size
        self.files = {}
        for i in range(n):
            _crc, off, size, _u, blk, nm = struct.unpack_from("<QQIIHH", table, 28 * i)
            p = blk * 0x10000 + nm
            name = names[p:names.index(b"\0", p)].decode("latin-1")
            self.files[name] = (off, size)

    def _chunk(self, i):
        if i not in self.cache:
            if len(self.cache) > 8:
                self.cache.clear()
            pos, size = self.spans[i]
            self.f.seek(pos)
            raw = self.bf.decrypt(self.f.read(size), "<II")
            for wbits in (-15, 15):
                try:
                    self.cache[i] = zlib.decompress(raw, wbits)
                    break
                except zlib.error:
                    continue
            else:
                raise ValueError(f"chunk {i}: not zlib/deflate, starts {raw[:16].hex(' ')}")
        return self.cache[i]

    def _read(self, off, size):
        out = bytearray()
        while size > 0:
            i, inner = divmod(off, self.chunk)
            part = self._chunk(i)[inner:inner + size]
            if not part:
                raise EOFError
            out += part
            off += len(part)
            size -= len(part)
        return bytes(out)

    def read(self, name):
        off, size = self.files[name]
        return self._read(self.data + off, size)


def main():
    source, key_name, out, *paths = sys.argv[1:]
    key = load_key(source, key_name)
    os.makedirs(out, exist_ok=True)
    for path in paths:
        a = Ectt(path, key)
        print("\n===", os.path.basename(path), a.sub, "files:", len(a.files))
        c, s = Counter(), Counter()
        for n, (_, size) in a.files.items():
            e = n.rsplit(".", 1)[-1].lower()
            c[e] += 1
            s[e] += size
        for e, k in c.most_common(25):
            print(f"  .{e:12} {k:6} files {s[e] / 1048576:8.1f} MB")
        for n in sorted(a.files):
            if n.lower().endswith((".landb", ".langdb", ".dlog", ".lua")) and len(n) < 70 and n.lower().endswith((".landb", ".langdb")):
                print(" ", n, a.files[n][1])
                with open(os.path.join(out, os.path.basename(path) + "__" + n), "wb") as f:
                    f.write(a.read(n))


if __name__ == "__main__":
    main()
