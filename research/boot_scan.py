"""Read-only: list the game's boot-time scripts and search them and the exe for resource-set logic."""
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
from ectt import Blowfish7, Ectt
from ttarch4 import load_key

source, root, out = sys.argv[2:5]
key = load_key(source, "SMBTaS")
bf = Blowfish7(key)
os.makedirs(out, exist_ok=True)
arch = os.path.join(root, "Archives")

exe = open(os.path.join(root, "SamMax200.exe"), "rb").read()
terms = [rb"_resdesc", rb"resdesc", rb"RegisterSetDescription", rb"ResourceSet", rb"enableMode", rb"bootable", rb"localization", rb"\.ttarch2", rb"\*\.lua", rb"Archives", rb"_lang", rb"FindFirstFile", rb"\.wav"]
print("== exe strings")
seen = set()
for m in re.finditer(rb"[\x20-\x7e]{5,120}", exe):
    s = m.group()
    if any(re.search(t, s, re.I) for t in terms) and s not in seen:
        seen.add(s)
        if len(seen) < 90:
            print("  ", s.decode())

for name in sorted(os.listdir(arch)):
    p = os.path.join(arch, name)
    if name.endswith(".ttarch2"):
        with open(p, "rb") as f:
            print(name, f.read(4))

for name in ("SM2_pc_Boot_compressed.ttarch2", "SM2_pc_Project_compressed.ttarch2"):
    a = Ectt(os.path.join(arch, name), key)
    print("\n==", name, len(a.files))
    for n in sorted(a.files):
        d = a.read(n)
        if d[:4] == b"\x1bLEo":
            d = bf.decrypt(d[4:], "<II")
        elif d[:4] == b"\x1bLEn":
            d = b"\x1bLua" + bf.decrypt(d[4:], "<II")
        low = n.lower()
        if low.endswith(".lua"):
            open(os.path.join(out, n), "wb").write(d)
        print(f"  {n} {len(d)} {ascii(d[:16])}")
