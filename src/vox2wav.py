"""Decode one line from a 2009 Telltale voice archive (.vox, Speex) to a 16-bit WAV file."""
import array
import ctypes
import math
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttarch4 import load_key, read_table

SPEEX_SET_ENH = 0
SPEEX_GET_FRAME_SIZE = 3


class Speex:
    def __init__(self, dll_path, mode):
        os.add_dll_directory(os.path.dirname(dll_path))
        lib = ctypes.CDLL(dll_path)
        self.lib = lib
        lib.speex_lib_get_mode.restype = ctypes.c_void_p
        lib.speex_lib_get_mode.argtypes = [ctypes.c_int]
        lib.speex_decoder_init.restype = ctypes.c_void_p
        lib.speex_decoder_init.argtypes = [ctypes.c_void_p]
        lib.speex_decoder_ctl.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        lib.speex_decode_int.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
        lib.speex_bits_init.argtypes = [ctypes.c_void_p]
        lib.speex_bits_read_from.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        lib.speex_bits_remaining.argtypes = [ctypes.c_void_p]
        self.state = lib.speex_decoder_init(lib.speex_lib_get_mode(mode))
        self.bits = ctypes.create_string_buffer(512)
        lib.speex_bits_init(self.bits)
        enh = ctypes.c_int(1)
        lib.speex_decoder_ctl(self.state, SPEEX_SET_ENH, ctypes.byref(enh))
        size = ctypes.c_int()
        lib.speex_decoder_ctl(self.state, SPEEX_GET_FRAME_SIZE, ctypes.byref(size))
        self.frame = size.value

    def close(self):
        self.lib.speex_decoder_destroy.argtypes = [ctypes.c_void_p]
        self.lib.speex_decoder_destroy(self.state)
        self.lib.speex_bits_destroy.argtypes = [ctypes.c_void_p]
        self.lib.speex_bits_destroy(self.bits)

    def decode(self, packet):
        """Return (samples, frame count, error count) for one packet."""
        self.lib.speex_bits_read_from(self.bits, packet, len(packet))
        out = array.array("h")
        frames = errors = 0
        buf = (ctypes.c_short * self.frame)()
        while True:
            r = self.lib.speex_decode_int(self.state, self.bits, buf)
            if r == -1:
                break
            if r == -2:
                errors += 1
                break
            out.extend(buf)
            frames += 1
            if self.lib.speex_bits_remaining(self.bits) < 5:
                break
        return out, frames, errors


def read_vox(archive, name, key):
    meta, _, files = read_table(archive, key)
    entries = {n.lower(): (o, s) for n, o, s in files}
    off, size = entries[name.lower()]
    with open(archive, "rb") as f:
        f.seek(meta["data_start"] + off)
        return f.read(size)


def parse_vox(blob):
    """Split a .vox file into stream properties and its packets."""
    if blob[:4] != b"ERTM":
        raise ValueError("expected an ERTM voice file")
    b = blob[20:]
    duration = struct.unpack_from("<f", b, 1)[0]
    size, frame, rate, mode, _block, count = struct.unpack_from("<6I", b, 5)
    offsets = list(struct.unpack_from(f"<{count}I", b, 29))
    data = b[29 + 4 * count:]
    if len(data) < size:
        raise ValueError(f"voice data too short: {len(data)} < {size}")
    data = data[:size]  # some files carry a stray byte at the end
    packets = [data[a:z] for a, z in zip(offsets, offsets[1:] + [size])]
    # The first packet is a text comment ("Encoded with Speex ..."), not audio.
    if packets and b"Encoded with" in packets[0][:16]:
        packets = packets[1:]
    return dict(duration=duration, frame=frame, rate=rate, mode=mode, packets=packets)


def main():
    dll, source, archive, name, out = sys.argv[1:6]
    v = parse_vox(read_vox(archive, name, load_key(source, "SM201")))
    print({k: v[k] for k in ("duration", "frame", "rate", "mode")}, "packets", len(v["packets"]))
    print("first packets:", [p[:12].hex(" ") for p in v["packets"][:2]])
    sp = Speex(dll, v["mode"])
    print("decoder frame size", sp.frame)
    pcm = array.array("h")
    frames = Counter = errors = 0
    per = {}
    for i, p in enumerate(v["packets"]):
        s, fr, err = sp.decode(p)
        pcm.extend(s)
        frames += fr
        errors += err
        per[fr] = per.get(fr, 0) + 1
        if err:
            print(" error in packet", i, "len", len(p), p[:8])
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(v["rate"])
        w.writeframes(pcm.tobytes())
    peak = max(abs(x) for x in pcm)
    rms = math.sqrt(sum(x * x for x in pcm) / len(pcm))
    print("frames", frames, "frames per packet", per, "errors", errors)
    print(f"seconds {len(pcm) / v['rate']:.3f} peak {peak} rms {rms:.0f}")
    seg = max(1, len(pcm) // 20)
    print("loudness over time:", [round(math.sqrt(sum(x * x for x in pcm[i:i + seg]) / seg)) for i in range(0, len(pcm) - seg + 1, seg)])
    print("written", out)


if __name__ == "__main__":
    main()
