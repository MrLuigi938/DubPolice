"""Read-only: re-read patched chores and confirm their structure and timing still make sense."""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chore_warp import chore_info, find_times
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, episode, mod = sys.argv[1:4]
original = Ectt(episode, load_key(source, "SMBTaS"))
_, files = read_nctt(mod)
bad = 0
with open(mod, "rb") as f:
    for name, (off, size) in files.items():
        if not name.endswith(".chore"):
            continue
        real = next(n for n in original.files if n.lower() == name)
        before = original.read(real)
        f.seek(off)
        after = f.read(size)
        body, at, old_len = chore_info(before)
        _, _, new_len = chore_info(after)
        b0, k0, _ = find_times(before, body, old_len)
        b1, k1, _ = find_times(after, body, new_len)
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        allowed = set()
        for x in b0:
            allowed.update(range(x, x + 8))
        for x in k0:
            allowed.update(range(x, x + 4))
        allowed.update(range(at, at + 4))
        outside = [i for i in changed if i not in allowed]
        negative = sum(struct.unpack_from("<f", after, x)[0] < struct.unpack_from("<f", before, x)[0] - 1e-4 for x in k0)
        over = sum(struct.unpack_from("<f", after, x + 4)[0] > new_len + 60 for x in b0)
        print(f"{name}: size same {len(before) == len(after)}, length {old_len:.2f}->{new_len:.2f}, blocks {len(b0)}->{len(b1)}, keys {len(k0)}->{len(k1)}")
        print(f"   bytes changed {len(changed)}, outside known time fields {len(outside)}, times moved earlier {negative}, block ends past limit {over}")
        print(f"   outside samples: {[(i, before[i], after[i]) for i in outside[:12]]}")
        if len(b0) != len(b1) or negative:
            bad += 1
print("problems:", bad)
