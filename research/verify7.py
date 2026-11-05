"""Read-only: check the rules of the shared timeline in the built mod against the game's originals."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_mod import crc64
from build_mod8 import is_active, named_records
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch_dir, mod = sys.argv[1:4]
key = load_key(source, "SMBTaS")
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))
names = set(read_nctt(os.path.join(arch_dir, "SM2_pc_SamMax201_uncompressed.ttarch2"))[1]) | set(read_nctt(os.path.join(arch_dir, "SM2_pc_Common_uncompressed.ttarch2"))[1])
names |= set(Ectt(os.path.join(arch_dir, "SM2_pc_Common_compressed.ttarch2"), key).files)
crc = {struct.pack("<Q", crc64(n.lower().encode())): n.lower() for n in names if n.lower().endswith(".wav")}
crc[struct.pack("<Q", crc64(b"cs_opening.chore"))] = "cs_opening.chore"

_, files = read_nctt(mod)
f = open(mod, "rb")


def get(n):
    o, s = files[n]
    f.seek(o)
    return f.read(s)


audio = {}
for n in files:
    if n.endswith(".wav"):
        word = struct.unpack_from("<Q", get(n), 0x3C)[0]
        audio[int(n[:-4])] = (word >> 34) / 32000

originals = {n.lower(): n for n in a.files}
problems = checked_lines = checked_sounds = 0
inner_length = chore_info(get("cs_opening.chore"))[2]
for n in sorted(files):
    if not n.endswith(".chore"):
        continue
    before, after = a.read(originals[n]), get(n)
    if struct.unpack_from("<I", after, 4)[0] - struct.unpack_from("<I", before, 4)[0] != len(after) - len(before):
        print("  total size wrong:", n)
        problems += 1
    body, _, len0 = chore_info(before)
    _, _, len1 = chore_info(after)
    b0, _, _ = find_times(before, body, len0)
    b1, _, _ = find_times(after, body, len1)
    if len(b0) != len(b1):
        print("  block count changed:", n, len(b0), len(b1))
        problems += 1
    for rid, _, block, _ in line_resources(after, hashes, b1):
        if rid in audio and is_active(after, block):
            s, e = struct.unpack_from("<ff", after, block)
            checked_lines += 1
            if abs((e - s) - audio[rid]) > 0.002:
                print(f"  active line length off: {n} {rid}: block {e - s:.3f}, audio {audio[rid]:.3f}")
                problems += 1
    # Sounds must keep their duration.
    h0 = named_records(before, body, crc)
    h1 = named_records(after, body, crc)
    if len(h0) != len(h1):
        print("  named record count changed:", n)
        problems += 1
    s0, s1 = sorted(b0), sorted(b1)
    for (p0, name), (p1, _) in zip(h0, h1):
        if name.endswith(".wav"):
            own0 = [b for b in s0 if b > p0][:1]
            own1 = [b for b in s1 if b > p1][:1]
            if own0 and own1:
                x0, y0 = struct.unpack_from("<ff", before, own0[0])
                x1, y1 = struct.unpack_from("<ff", after, own1[0])
                checked_sounds += 1
                if abs((y1 - x1) - (y0 - x0)) > 0.002:
                    print(f"  sound stretched: {n} {name}: {y0 - x0:.3f} -> {y1 - x1:.3f}")
                    problems += 1

outer = get("env_office_cs_opening_e1_56.chore")
body, _, length = chore_info(outer)
blocks, _, _ = find_times(outer, body, length)
pos = next(p for p, n in named_records(outer, body, crc) if n == "cs_opening.chore")
s, e = struct.unpack_from("<ff", outer, min(b for b in blocks if b > pos))
print(f"nested scene in outer: {s:.3f}-{e:.3f} = {e - s:.3f}s, inner chore length {inner_length:.3f}s, difference {e - s - inner_length:+.3f}s")
if abs(e - s - inner_length) > 0.05:
    problems += 1
pos = next(p for p, n in named_records(outer, body, crc) if n == "cs_opening_enter_office.wav")
s, e = struct.unpack_from("<ff", outer, min(b for b in blocks if b > pos))
print(f"scene audio block: {s:.3f}-{e:.3f} (original 4.111-104.049); outer chore length {length:.2f}s")
print(f"active lines checked {checked_lines}, sounds checked {checked_sounds}, problems {problems}")
