"""Read-only lister for uncompressed .ttarch2 (NCTT) archives, plus comparison with 2009 voices."""
import os
import struct
import sys
from collections import Counter


def read_nctt(path):
    with open(path, "rb") as f:
        magic = f.read(4)
        if magic != b"NCTT":
            raise SystemExit(f"{path}: {magic!r}")
        _size = struct.unpack("<Q", f.read(8))[0]
        sub = f.read(4)
        if sub == b"3ATT":
            f.read(4)
        name_size, count = struct.unpack("<II", f.read(8))
        table = f.read(28 * count)
        names = f.read(name_size)
        base = f.tell()
    files = {}
    for i in range(count):
        _crc, off, size, _unk, block, name_off = struct.unpack_from("<QQIIHH", table, 28 * i)
        p = block * 0x10000 + name_off
        name = names[p:names.index(b"\0", p)].decode("latin-1")
        files[name.lower()] = (base + off, size)
    return sub, files


def main():
    for path in sys.argv[1:]:
        sub, files = read_nctt(path)
        print("\n===", os.path.basename(path), sub, "files:", len(files))
        c, s = Counter(), Counter()
        for n, (_, size) in files.items():
            e = n.rsplit(".", 1)[-1]
            c[e] += 1
            s[e] += size
        for e, k in c.most_common():
            print(f"  .{e:10} {k:6} files {s[e] / 1048576:8.1f} MB")
        with open(path, "rb") as f:
            seen = Counter()
            for n, (o, size) in sorted(files.items()):
                e = n.rsplit(".", 1)[-1]
                seen[e] += 1
                if seen[e] <= 3:
                    f.seek(o)
                    print(f"  {n} ({size} B) {f.read(48).hex(' ')}")


if __name__ == "__main__":
    main()
