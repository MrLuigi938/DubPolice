"""Read files from a 2009 Telltale .ttarch archive (version below 7, plain or compressed)."""
import struct
import zlib

from ttarch4 import Blowfish

CHUNK = 0x10000


class OldArchive:
    def __init__(self, path, key):
        self.path = path
        self.bf = Blowfish(key)
        with open(path, "rb") as f:
            i32 = lambda: struct.unpack("<i", f.read(4))[0]
            _version, _enc, _unk, _mode = i32(), i32(), i32(), i32()
            self.blocks = [i32() for _ in range(i32())]
            _size, _p1, _p2, hsize = i32(), i32(), i32(), i32()
            table = self.bf.decrypt(f.read(hsize), "<II")
            self.base = f.tell()
        self.positions = [self.base]
        for b in self.blocks:
            self.positions.append(self.positions[-1] + b)
        p = 0
        count = struct.unpack_from("<i", table, p)[0]
        p += 4
        for _ in range(count):
            p += 4 + struct.unpack_from("<i", table, p)[0]
        count = struct.unpack_from("<i", table, p)[0]
        p += 4
        self.files = {}
        for _ in range(count):
            ln = struct.unpack_from("<i", table, p)[0]
            p += 4
            name = table[p:p + ln].decode("latin-1")
            p += ln
            _z, off, size = struct.unpack_from("<iIi", table, p)
            p += 12
            self.files[name.lower()] = (off, size)
        self._f = open(path, "rb")
        self._chunk_index = None
        self._chunk = b""

    def _read_chunk(self, i):
        if i != self._chunk_index:
            self._f.seek(self.positions[i])
            self._chunk = zlib.decompress(self.bf.decrypt(self._f.read(self.blocks[i]), "<II"))
            self._chunk_index = i
        return self._chunk

    def read(self, name):
        off, size = self.files[name.lower()]
        if not self.blocks:
            self._f.seek(self.base + off)
            return self._f.read(size)
        out = bytearray()
        while size > 0:
            i, inner = divmod(off, CHUNK)
            part = self._read_chunk(i)[inner:inner + size]
            out += part
            off += len(part)
            size -= len(part)
        return bytes(out)
