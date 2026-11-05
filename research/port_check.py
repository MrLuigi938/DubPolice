"""Read-only: compare the remaster's cs_Opening with the 2009 chores; report every old time pair and how well the
remaster's times match the old English ones."""
import re
import struct
import sys

sys.path.insert(0, sys.argv[1])
from chore_warp import chore_info, find_times
from ectt import Ectt
from ttarch4 import load_key

source, episode, old_en, old_de = sys.argv[2:6]
a = Ectt(episode, load_key(source, "SMBTaS"))
d = a.read(next(n for n in a.files if n.lower() == "cs_opening.chore"))
en = open(old_en, "rb").read()
de = open(old_de, "rb").read()


def clean(b):
    return re.sub(rb"[^ -~]", b".", b).decode()


body, length_at, length = chore_info(d)
blocks, keys, stats = find_times(d, body, length)
print("remaster cs_Opening size", len(d), "length", round(length, 3), "blocks", len(blocks), "keys", len(keys), dict(stats))

sym = bytes.fromhex("55 d3 dc a6 0f a3 d6 4b")
for label, buf in (("remaster", d), ("old EN", en), ("old DE", de)):
    hits = [m.start() for m in re.finditer(re.escape(sym), buf)]
    print(f"\n{label}: time-property symbol hits {len(hits)}")
    for h in hits[:3]:
        print(f"  @{h} {buf[h:h + 60].hex(' ')}")
    values = []
    for h in hits:
        tail = buf[h + 8:h + 40]
        m = re.search(rb"\x22\0\0\0\x02\0\0\0", tail)
        if m:
            values.append(round(struct.unpack_from("<f", tail, m.start() - 4)[0], 3))
    print("  value before the two-key curve:", sorted(set(values))[:20], "count", len(values))

# Old time pairs: same fields at the same order in both old files.
def old_pairs(buf):
    res = []
    for i in range(0, len(buf) - 13):
        s = struct.unpack_from("<f", buf, i)[0]
        if buf[i + 4] in (0x30, 0x31) and buf[i + 5:i + 9] in (b"\x02\0\0\0", b"\x01\0\0\0") and -1 <= s < 200:
            res.append(s)
    return res


ke = old_pairs(en)
kd = old_pairs(de)
print("\nold key times EN/DE:", len(ke), len(kd))
pairs = sorted(set((round(a_, 3), round(b_, 3)) for a_, b_ in zip(ke, kd)))
back = sum(1 for (x, y), (x2, y2) in zip(pairs, pairs[1:]) if y2 < y - 0.01)
print("distinct pairs:", len(pairs), "non-monotonic steps:", back)
print("sample:", pairs[:10], "...", pairs[-6:])

# Do remaster times match old English times?
old_set = sorted({round(v, 2) for v in ke})
remaster_times = sorted({round(struct.unpack_from("<f", d, k)[0], 2) for k in keys} | {round(struct.unpack_from("<f", d, b)[0], 2) for b in blocks})
missing = [t for t in remaster_times if min(abs(t - o) for o in old_set) > 0.02]
print("\nremaster times:", len(remaster_times), "with no old counterpart:", len(missing), missing[:30])
