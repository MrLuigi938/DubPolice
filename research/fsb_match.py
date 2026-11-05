"""Read-only: read FSB5 names and details from the remaster's voice archive, match with 2009 voices."""
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, sys.argv[1])
from nctt import read_nctt
from ttarch4 import load_key, read_table

source, german, english, nctt_path, loose_dir = sys.argv[2:7]
key = load_key(source, "SM201")

_, files = read_nctt(nctt_path)
rows = []
modes = Counter()
rates = Counter()
with open(nctt_path, "rb") as f:
    for n, (o, size) in files.items():
        f.seek(o)
        h = f.read(min(size, 65536))
        if h[:4] != b"FSB5":
            continue
        ver, samples, shdr, name_size, data_size, mode = struct.unpack_from("<6I", h, 4)
        modes[(ver, samples, mode)] += 1
        hdr = 0x3C if ver == 1 else 0x40
        word = struct.unpack_from("<Q", h, hdr)[0]
        rates[(word >> 1) & 0xF] += 1
        nm = b""
        if name_size:
            off = hdr + shdr
            first = struct.unpack_from("<I", h, off)[0]
            nm = h[off + first:off + name_size].split(b"\0")[0]
        rows.append((n, nm.decode("latin-1").lower(), size, word))

print("fsb files:", len(rows), "(version, samples, mode):", modes.most_common(5))
print("rate code (FSB5 flags bits 1-4):", rates.most_common(5))
print("samples:", [(a, b) for a, b, _, _ in rows[:12]])


def names_of(path):
    _, _, lst = read_table(path, key)
    return {n.lower()[:-4] for n, _, _ in lst if n.lower().endswith(".vox")}


de = names_of(german)
en = names_of(english)
wav = {r[0][:-4] for r in rows}
inner = {r[1].rsplit(".", 1)[0] for r in rows}
print("\nold DE:", len(de), "old EN:", len(en), "remaster wav:", len(wav))
print("wav filename == old DE:", len(wav & de), " inner FSB name == old DE:", len(inner & de))
print("remaster with no old match (by filename):", len(wav - de), sorted(wav - de)[:15])
print("remaster with no old match (by inner name):", len(inner - de), sorted(inner - de)[:15])
print("old DE with no remaster match (inner):", len(de - inner), sorted(de - inner)[:15])
for a in sorted(wav)[:6]:
    v = int(a) if a.isdigit() else 0
    print(a, hex(v))
for a in sorted(de)[:6]:
    v = int(a) if a.isdigit() else 0
    print(a, hex(v))
