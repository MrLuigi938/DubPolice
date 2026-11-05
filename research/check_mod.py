"""Validate a built archive: re-read it with the same parser as the game's files, then open every
sound with the game's own FMOD library, using a real game file as the control."""
import array
import ctypes
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nctt import read_nctt

fmod_path, mod_archive, control_archive, preview = sys.argv[1:5]
OPENMEMORY = 0x00000800
CREATESAMPLE = 0x00000100
OPENONLY = 0x00000008
TIMEUNIT_PCM = 2
NOSOUND = 2

os.add_dll_directory(os.path.dirname(fmod_path))
fmod = ctypes.WinDLL(fmod_path)
vp = ctypes.c_void_p


def ok(result, what):
    if result:
        raise SystemExit(f"FMOD error {result} in {what}")


system = vp()
ok(fmod.FMOD_System_Create(ctypes.byref(system)), "System_Create")
ok(fmod.FMOD_System_SetOutput(system, NOSOUND), "SetOutput")
ok(fmod.FMOD_System_Init(system, 32, 0, None), "Init")
version = ctypes.c_uint()
fmod.FMOD_System_GetVersion(system, ctypes.byref(version))
print("FMOD version", hex(version.value))


def open_sound(data):
    """Find the size of the exinfo structure for this FMOD version, then open the sound."""
    for cb in range(8, 512, 4):
        ex = ctypes.create_string_buffer(512)
        ctypes.memmove(ex, ctypes.c_int(cb).__reduce__()[1][0] if False else cb.to_bytes(4, "little"), 4)
        ctypes.memmove(ctypes.addressof(ex) + 4, len(data).to_bytes(4, "little"), 4)
        snd = vp()
        buf = ctypes.create_string_buffer(data, len(data))
        r = fmod.FMOD_System_CreateSound(system, buf, OPENMEMORY | CREATESAMPLE, ex, ctypes.byref(snd))
        if r == 0:
            return snd
    raise ValueError("could not open: last FMOD result %d" % r)


def describe(data):
    snd = open_sound(data)
    count = ctypes.c_int()
    ok(fmod.FMOD_Sound_GetNumSubSounds(snd, ctypes.byref(count)), "GetNumSubSounds")
    target = snd
    if count.value:
        sub = vp()
        ok(fmod.FMOD_Sound_GetSubSound(snd, 0, ctypes.byref(sub)), "GetSubSound")
        target = sub
    length = ctypes.c_uint()
    ok(fmod.FMOD_Sound_GetLength(target, ctypes.byref(length), TIMEUNIT_PCM), "GetLength")
    typ, fmt, chan, bits = ctypes.c_int(), ctypes.c_int(), ctypes.c_int(), ctypes.c_int()
    ok(fmod.FMOD_Sound_GetFormat(target, ctypes.byref(typ), ctypes.byref(fmt), ctypes.byref(chan), ctypes.byref(bits)), "GetFormat")
    freq, prio = ctypes.c_float(), ctypes.c_int()
    ok(fmod.FMOD_Sound_GetDefaults(target, ctypes.byref(freq), ctypes.byref(prio)), "GetDefaults")
    name = ctypes.create_string_buffer(128)
    fmod.FMOD_Sound_GetName(target, name, 128)
    ptr1, ptr2, len1, len2 = vp(), vp(), ctypes.c_uint(), ctypes.c_uint()
    size = length.value * chan.value * bits.value // 8
    pcm = b""
    if fmod.FMOD_Sound_Lock(target, 0, size, ctypes.byref(ptr1), ctypes.byref(ptr2), ctypes.byref(len1), ctypes.byref(len2)) == 0:
        pcm = ctypes.string_at(ptr1, len1.value)
        fmod.FMOD_Sound_Unlock(target, ptr1, ptr2, len1, len2)
    fmod.FMOD_Sound_Release(snd)
    return dict(subsounds=count.value, type=typ.value, format=fmt.value, channels=chan.value, bits=bits.value,
                rate=freq.value, samples=length.value, name=name.value.decode("latin-1")), pcm


_, control = read_nctt(control_archive)
n = sorted(k for k in control if k[:-4].isdigit())[0]
o, s = control[n]
with open(control_archive, "rb") as f:
    f.seek(o)
    info, _pcm = describe(f.read(s))
print("control (real game file)", n, info)

sub, files = read_nctt(mod_archive)
print("mod archive", sub, "files", len(files))
bad = 0
with open(mod_archive, "rb") as f:
    for n, (o, s) in sorted(files.items()):
        if not n.endswith(".wav"):
            continue
        f.seek(o)
        info, pcm = describe(f.read(s))
        with wave.open(os.path.join(preview, n), "rb") as w:
            original = w.readframes(w.getnframes())
        same = pcm == original
        bad += not same
        print(" ", n, info["name"], f"{info['samples'] / info['rate']:.2f}s", f"{int(info['rate'])}Hz", f"{info['bits']}bit", "chan", info["channels"], "pcm_identical", same)
print("all sounds opened by FMOD; PCM mismatches:", bad)
