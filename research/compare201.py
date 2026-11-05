import hashlib
import sys

sys.path.insert(0, sys.argv[1])
from ttarch4 import load_key, read_table

source, german, ms, english = sys.argv[2:6]
key = load_key(source, "SM201")
gm, _, g = read_table(german, key)
_, _, l = read_table(ms, key)
em, _, e = read_table(english, key)

gv = {n.lower(): (o, s) for n, o, s in g}
ev = {n.lower(): (o, s) for n, o, s in e}
anm = {n.lower()[:-4] for n, _, _ in l if n.lower().endswith(".anm")}
stem = lambda s: {n[:-4] for n in s}

print("German voice:", len(gv), "English voice:", len(ev), "both:", len(gv.keys() & ev.keys()))
print("only German:", sorted(gv.keys() - ev.keys())[:15])
print("only English:", sorted(ev.keys() - gv.keys())[:15])
print("German lipsync anm:", len(anm), "matching a German vox:", len(anm & stem(gv)))

same = different = 0
with open(german, "rb") as fg, open(english, "rb") as fe:
    for n in gv.keys() & ev.keys():
        fg.seek(gm["data_start"] + gv[n][0])
        fe.seek(em["data_start"] + ev[n][0])
        if hashlib.md5(fg.read(gv[n][1])).digest() == hashlib.md5(fe.read(ev[n][1])).digest():
            same += 1
        else:
            different += 1
print("identical audio:", same, "different audio:", different)
print("German total MB:", round(sum(s for _, s in gv.values()) / 1048576, 1),
      "English total MB:", round(sum(s for _, s in ev.values()) / 1048576, 1))
