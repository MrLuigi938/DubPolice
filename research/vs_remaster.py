"""Read-only comparison of the 2009 English/German voices with the remaster's loose .vox files."""
import os
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from ttarch4 import load_key, read_table

source, german, english, loose_dir = sys.argv[2:6]
key = load_key(source, "SM201")


def load(path):
    meta, _, files = read_table(path, key)
    out = {}
    with open(path, "rb") as f:
        for n, o, s in files:
            f.seek(meta["data_start"] + o)
            out[n.lower()] = f.read(s)
    return out


de = load(german)
en = load(english)
new = {}
for n in os.listdir(loose_dir):
    if n.lower().endswith(".vox"):
        with open(os.path.join(loose_dir, n), "rb") as f:
            new[n.lower()] = f.read()

print("remaster vox:", len(new), "old EN:", len(en), "old DE:", len(de))
print("remaster & old EN:", len(new.keys() & en.keys()), " remaster & old DE:", len(new.keys() & de.keys()))
print("only remaster:", len(new.keys() - de.keys()), sorted(new.keys() - de.keys())[:25])
print("only old DE:", sorted(de.keys() - new.keys())[:25])

delta = Counter(len(new[n]) - len(en[n]) for n in new.keys() & en.keys())
print("size delta remaster-oldEN (top):", delta.most_common(10))

rel = Counter()
first_diff = Counter()
tail_same = 0
for n in new.keys() & en.keys():
    a, b = en[n], new[n]
    d = len(b) - len(a)
    if d == 10 and a[-1000:] == b[-1000:]:
        tail_same += 1
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    first_diff[i] += 1
print("delta 10 and last 1000 bytes identical:", tail_same)
print("first differing offset (top):", first_diff.most_common(8))

for n in sorted(new.keys() & en.keys())[:2]:
    print("\n", n)
    print(" oldEN", len(en[n]), en[n][:128].hex(" "))
    print(" new  ", len(new[n]), new[n][:128].hex(" "))
    print(" oldDE", len(de[n]), de[n][:128].hex(" "))
