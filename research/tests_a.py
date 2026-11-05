"""Read-only tests: (1) does the game's FMOD decode my IMA-ADPCM correctly? (2) which size fields enclose a time curve?"""
import array
import ctypes
import math
import os
import re
import struct
import sys
import wave

sys.path.insert(0, sys.argv[1])
from chore_warp import chore_info
from ectt import Ectt
from ima import make_fsb5_ima
from ttarch4 import load_key

fmod_path, preview, source, episode = sys.argv[2:6]
os.add_dll_directory(os.path.dirname(fmod_path))
fmod = ctypes.WinDLL(fmod_path)
vp = ctypes.c_void_p
system = vp()
assert fmod.FMOD_System_Create(ctypes.byref(system)) == 0
fmod.FMOD_System_SetOutput(system, 2)
assert fmod.FMOD_System_Init(system, 32, 0, None) == 0


def decode(data):
    for cb in range(8, 512, 4):
        ex = ctypes.create_string_buffer(512)
        ctypes.memmove(ex, cb.to_bytes(4, "little"), 4)
        ctypes.memmove(ctypes.addressof(ex) + 4, len(data).to_bytes(4, "little"), 4)
        snd = vp()
        buf = ctypes.create_string_buffer(data, len(data))
        r = fmod.FMOD_System_CreateSound(system, buf, 0x800 | 0x100, ex, ctypes.byref(snd))
        if r == 0:
            break
    else:
        raise SystemExit(f"FMOD refused the file: {r}")
    sub = vp()
    fmod.FMOD_Sound_GetSubSound(snd, 0, ctypes.byref(sub))
    t, f, ch, bits = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
    fmod.FMOD_Sound_GetFormat(sub, ctypes.byref(t), ctypes.byref(f), ctypes.byref(ch), ctypes.byref(bits))
    length = ctypes.c_uint()
    fmod.FMOD_Sound_GetLength(sub, ctypes.byref(length), 2)
    size = length.value * ch.value * max(bits.value, 16) // 8
    p1, p2, l1, l2 = vp(), vp(), ctypes.c_uint(), ctypes.c_uint()
    r = fmod.FMOD_Sound_Lock(sub, 0, size, ctypes.byref(p1), ctypes.byref(p2), ctypes.byref(l1), ctypes.byref(l2))
    raw = ctypes.string_at(p1, l1.value) if r == 0 else b""
    fmod.FMOD_Sound_Unlock(sub, p1, p2, l1, l2)
    fmod.FMOD_Sound_Release(snd)
    return dict(type=t.value, format=f.value, bits=bits.value, samples=length.value), raw


for rid in ("400637953", "400637959"):
    with wave.open(os.path.join(preview, rid + ".wav"), "rb") as w:
        rate = w.getframerate()
        pcm = array.array("h", w.readframes(w.getnframes()))
    fsb = make_fsb5_ima(rid, pcm, rate)
    info, raw = decode(fsb)
    print(rid, "original samples", len(pcm), "file", len(fsb), f"{len(fsb) / (len(pcm) / rate) / 1024:.1f} kB/s", info)
    if info["bits"] == 16 and raw:
        out = array.array("h", raw)
        best = (-1e9, 0)
        limit = min(len(out), len(pcm)) - 200
        sub = range(1000, min(limit, 41000))
        for lag in range(-4, 5):
            noise = sum((pcm[i] - out[i + lag]) ** 2 for i in sub)
            signal = sum(pcm[i] ** 2 for i in sub)
            snr = 10 * math.log10(signal / max(noise, 1))
            if snr > best[0]:
                best = (snr, lag)
        print(f"   decoded quality {best[0]:.1f} dB at lag {best[1]}")

a = Ectt(episode, load_key(source, "SMBTaS"))
for name in ("cs_opening.chore", "env_office_cs_opening_e1_56.chore"):
    d = a.read(next(n for n in a.files if n.lower() == name))
    print("\n", name, "file", len(d), "meta total", struct.unpack_from("<I", d, 4)[0])
    sym = bytes.fromhex("55 d3 dc a6 0f a3 d6 4b")
    curves = [m.start() + 8 + 12 for m in re.finditer(re.escape(sym), d) if d[m.start() + 20:m.start() + 28] == bytes.fromhex("22 00 00 00 02 00 00 00")]
    for c in curves[:3] + curves[-2:]:
        ends = {}
        for p in range(0, c):
            s = struct.unpack_from("<I", d, p)[0]
            e = p + s
            if c + 34 <= e <= len(d):
                ends.setdefault(e, []).append(p)
        shared = {e: ps for e, ps in ends.items() if len(ps) >= 2 and (c - ps[-1]) < 800}
        print(f"  curve @{c}: enclosing candidates {[(e, ps) for e, ps in sorted(shared.items())[:4]]}")
        wide = sorted(((e, ps) for e, ps in ends.items() if e - c > 5000), key=lambda x: -len(x[1]))[:3]
        print(f"     wide candidates: {[(e, ps[:4]) for e, ps in wide]}")
