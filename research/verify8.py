"""Read-only: outside pauses, does every animation in the opening still run at original speed?"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curves import TIME_PROPERTY
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, arch_dir, mod = sys.argv[1:4]
a = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), load_key(source, "SMBTaS"))
originals = {n.lower(): n for n in a.files}
_, files = read_nctt(mod)
f = open(mod, "rb")


def curves(buf):
    out = []
    for m in re.finditer(re.escape(TIME_PROPERTY), buf):
        c = m.start() + 20
        size, count = struct.unpack_from("<II", buf, c)
        if count >= 2 and size == 8 + 13 * count:
            out.append([struct.unpack_from("<ff", buf[c + 8 + 13 * i:c + 8 + 13 * i + 4] + buf[c + 8 + 13 * i + 9:c + 8 + 13 * i + 13]) for i in range(count)])
    return out


for name in ("cs_opening.chore", "env_office_cs_opening_e1_56.chore"):
    o, s = files[name]
    f.seek(o)
    after = f.read(s)
    before = a.read(originals[name])
    c0, c1 = curves(before), curves(after)
    print(name, "curves", len(c0), len(c1))
    normal = paused = other = 0
    worst = 1.0
    refined = 0
    for k0, k1 in zip(c0, c1):
        if len(k1) <= 2 or len(k0) != 2:
            continue
        refined += 1
        duration = k0[1][0] - k0[0][0]
        for (t0, v0), (t1, v1) in zip(k1, k1[1:]):
            dt = t1 - t0
            if dt < 0.03:
                continue
            speed = (v1 - v0) * duration / dt
            if speed < 0.03:
                paused += 1
            elif 0.97 <= speed <= 1.03:
                normal += 1
            else:
                other += 1
                worst = min(worst, speed)
    print(f"   refined curves {refined}: segments at original speed {normal}, paused {paused}, other {other}, slowest other {worst:.2f}")
