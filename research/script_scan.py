"""Read-only: which scripts and dialogs start the opening cutscene, and do they use fixed timers or music cues?"""
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
from ectt import Blowfish7, Ectt
from ttarch4 import load_key

source, arch_dir = sys.argv[2:4]
key = load_key(source, "SMBTaS")
bf = Blowfish7(key)
terms = re.compile(rb"opening|Opening", re.I)
for archive in ("SM2_pc_SamMax201_compressed.ttarch2", "SM2_pc_Project_compressed.ttarch2", "SM2_pc_Boot_compressed.ttarch2"):
    a = Ectt(os.path.join(arch_dir, archive), key)
    print("==", archive)
    print("  opening named files:", [n for n in a.files if b"opening" in n.lower().encode()])
    for n in sorted(a.files):
        low = n.lower()
        if not low.endswith((".lua", ".scene", ".dlog", ".prop")):
            continue
        d = a.read(n)
        if d[:4] == b"\x1bLEo":
            d = bf.decrypt(d[4:], "<II")
        elif d[:4] == b"\x1bLEn":
            d = b"\x1bLua" + bf.decrypt(d[4:], "<II")
        if terms.search(d):
            parts = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{3,}", d) if not m.group().startswith(b"@file")]
            hits = [i for i, p in enumerate(parts) if re.search("opening", p, re.I)]
            shown = sorted({j for i in hits for j in range(max(0, i - 6), min(len(parts), i + 8))})
            print(f"\n  {n} ({len(d)} bytes):", " | ".join(parts[j] for j in shown)[:1400])
        if low in ("opening.lua", "env_office.lua", "sound.lua"):
            parts = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{3,}", d) if not m.group().startswith(b"@file")]
            print(f"\n  ALL {n}:", " | ".join(parts)[:2600])
