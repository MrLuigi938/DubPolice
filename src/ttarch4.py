"""Read-only lister for classic Telltale .ttarch archives (version < 7)."""
import re
import struct
import sys
from collections import Counter


def pi_words(count):
    """Fractional hex digits of pi as 32-bit words (Blowfish P and S boxes)."""
    bits = count * 32 + 64
    one = 1 << bits

    def arctan_inv(x):
        total = term = one // x
        n, sign, xx = 3, -1, x * x
        while term:
            term //= xx
            total += sign * (term // n)
            n += 2
            sign = -sign
        return total

    pi = 4 * (4 * arctan_inv(5) - arctan_inv(239))
    frac = pi - (3 << bits)
    frac >>= 64
    return [(frac >> (32 * (count - 1 - i))) & 0xFFFFFFFF for i in range(count)]


class Blowfish:
    _init = pi_words(18 + 4 * 256)

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
        l = r = 0
        for i in range(0, 18, 2):
            l, r = self._enc(l, r)
            self.P[i], self.P[i + 1] = l, r
        for s in self.S:
            for i in range(0, 256, 2):
                l, r = self._enc(l, r)
                s[i], s[i + 1] = l, r

    def _f(self, x):
        s = self.S
        return ((((s[0][x >> 24] + s[1][(x >> 16) & 255]) & 0xFFFFFFFF)
                 ^ s[2][(x >> 8) & 255]) + s[3][x & 255]) & 0xFFFFFFFF

    def _enc(self, l, r):
        for i in range(16):
            l ^= self.P[i]
            r ^= self._f(l)
            l, r = r, l
        l, r = r, l
        r ^= self.P[16]
        l ^= self.P[17]
        return l, r

    def _dec(self, l, r):
        for i in range(17, 1, -1):
            l ^= self.P[i]
            r ^= self._f(l)
            l, r = r, l
        l, r = r, l
        r ^= self.P[1]
        l ^= self.P[0]
        return l, r

    def decrypt(self, data, fmt):
        out = bytearray(data)
        for o in range(0, len(data) - len(data) % 8, 8):
            l, r = struct.unpack_from(fmt, data, o)
            l, r = self._dec(l, r)
            struct.pack_into(fmt, out, o, l, r)
        return bytes(out)


def load_key(_source, name):
    from keys import KEYS
    return KEYS[name]


def read_table(path, key):
    with open(path, "rb") as f:
        def i32():
            return struct.unpack("<i", f.read(4))[0]
        version, encryption, _unk = i32(), i32(), i32()
        mode = i32()
        blocks = [i32() for _ in range(i32())]
        block_size = i32()
        prio, prio2 = i32(), i32()
        header_size = i32()
        raw = f.read(header_size)
        data_start = f.tell()
    meta = dict(version=version, encryption=encryption, mode=mode, blocks=len(blocks),
                block_size=block_size, header_size=header_size, data_start=data_start)
    bf = Blowfish(key)
    for fmt in (">II", "<II"):
        d = bf.decrypt(raw, fmt) if encryption else raw
        try:
            p = 0
            dirs = []
            n = struct.unpack_from("<i", d, p)[0]; p += 4
            if not 0 <= n < 1000:
                raise ValueError
            for _ in range(n):
                ln = struct.unpack_from("<i", d, p)[0]; p += 4
                dirs.append(d[p:p + ln].decode("latin-1")); p += ln
            n = struct.unpack_from("<i", d, p)[0]; p += 4
            if not 0 <= n < 1000000:
                raise ValueError
            files = []
            for _ in range(n):
                ln = struct.unpack_from("<i", d, p)[0]; p += 4
                name = d[p:p + ln].decode("latin-1"); p += ln
                _zero, off, size = struct.unpack_from("<iIi", d, p); p += 12
                files.append((name, off, size))
            meta["byte_order"] = fmt
            return meta, dirs, files
        except (ValueError, struct.error):
            continue
    raise SystemExit("Could not decode table with this key: " + repr(meta))


def main():
    source, key_name, *paths = sys.argv[1:]
    key = load_key(source, key_name)
    print("key bytes:", len(key))
    for path in paths:
        meta, dirs, files = read_table(path, key)
        print("\n===", path.replace("\\", "/").rsplit("/", 1)[-1])
        print(meta)
        print("dirs:", dirs[:10])
        exts = Counter(n.rsplit(".", 1)[-1].lower() for n, _, _ in files)
        sizes = Counter()
        for n, _, s in files:
            sizes[n.rsplit(".", 1)[-1].lower()] += s
        print("files:", len(files))
        for e, c in exts.most_common():
            print(f"  .{e:10} {c:6} files {sizes[e] / 1048576:8.1f} MB")
        seen = Counter()
        with open(path, "rb") as f:
            for n, off, size in files:
                e = n.rsplit(".", 1)[-1].lower()
                seen[e] += 1
                if seen[e] <= 4:
                    head = b""
                    if meta["mode"] != 2:
                        f.seek(meta["data_start"] + off)
                        head = f.read(16)
                    print(f"  {n}  ({size} B) head={head.hex(' ')}")


if __name__ == "__main__":
    main()
