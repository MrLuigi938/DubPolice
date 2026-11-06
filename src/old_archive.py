"""Read files from an original Telltale .ttarch archive (versions 4 to 9, plain or compressed)."""
import os
import struct
import zlib

from ectt import Blowfish7
from ttarch4 import Blowfish
from vox2wav import reveal_nibm


class OldArchive:
    def __init__(self, path, key):
        self.path = path
        with open(path, "rb") as f:
            i32 = lambda: struct.unpack("<i", f.read(4))[0]
            self.version, self.encrypted, _unk, mode = i32(), i32(), i32(), i32()
            self.blocks = [i32() for _ in range(i32())]
            _size, _p1, _p2 = i32(), i32(), i32()
            self.chunk = 0x10000
            if self.version >= 7:
                i32(), i32()
                self.chunk = i32() * 1024
                if self.version == 8:
                    f.read(1)
                elif self.version == 9:
                    f.read(1)
                    i32()
            hsize = i32()
            stored = i32() if self.version >= 7 and mode == 2 else hsize
            raw = f.read(stored)
            self.base = f.tell()
        if self.version >= 7 and mode == 2:
            raw = _inflate(raw)
        self.bf = Blowfish7(key) if self.version >= 7 else Blowfish(key)
        table = self.bf.decrypt(raw, "<II") if self.encrypted else raw
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
        self._chunk_data = b""

    def _read_chunk(self, i):
        if i != self._chunk_index:
            self._f.seek(self.positions[i])
            raw = self._f.read(self.blocks[i])
            if self.encrypted:
                raw = self.bf.decrypt(raw, "<II")
            self._chunk_data = _inflate(raw)
            self._chunk_index = i
        return self._chunk_data

    def read(self, name):
        off, size = self.files[name.lower()]
        if not self.blocks:
            self._f.seek(self.base + off)
            return self._f.read(size)
        out = bytearray()
        while size > 0:
            i, inner = divmod(off, self.chunk)
            part = self._read_chunk(i)[inner:inner + size]
            out += part
            off += len(part)
            size -= len(part)
        return bytes(out)


class FlatArchive:
    """Season 1 from 2007: archive version 2, nothing compressed, metadata files obscured block by block."""

    def __init__(self, path, key):
        self.bf = Blowfish(key)
        self._f = open(path, "rb")
        version, encrypted, _unknown, size = struct.unpack("<4i", self._f.read(16))
        if version != 2 or not encrypted:
            raise ValueError(f"unexpected archive version {version}")
        table = self.bf.decrypt(self._f.read(size), "<II")
        self.base = self._f.tell()
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

    def read(self, name):
        off, size = self.files[name.lower()]
        self._f.seek(self.base + off)
        data = self._f.read(size)
        return self._reveal(data) if name.lower().endswith(".langdb") else data

    def _reveal(self, data):
        body = bytearray(data[4:])
        block = 0x80
        for i in range(len(body) // block):
            at = i * block
            chunk = bytes(body[at:at + block])
            if i % 0x20 == 0:
                body[at:at + block] = self.bf.decrypt(chunk, "<II")
            elif i % 0x50 != 0:
                body[at:at + block] = bytes(b ^ 0xFF for b in chunk)
        return bytes(body)


class LooseVoices:
    """Season 1 keeps its recordings as single files in a folder."""

    def __init__(self, folder, key):
        self.cipher = Blowfish(key)
        self.files = {n.lower(): os.path.join(folder, n) for n in os.listdir(folder) if n.lower().endswith(".vox")}

    def read(self, name):
        with open(self.files[name.lower()], "rb") as f:
            return reveal_nibm(f.read(), self.cipher)


def _inflate(raw):
    try:
        return zlib.decompress(raw)
    except zlib.error:
        return zlib.decompress(raw, -15)
