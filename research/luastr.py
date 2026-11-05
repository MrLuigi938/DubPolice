"""Read-only: print the constant strings of compiled Lua scripts, in file order."""
import os
import re
import sys

folder, *names = sys.argv[1:]
for n in names:
    d = open(os.path.join(folder, n), "rb").read()
    print("\n==", n, len(d))
    parts = [m.group().decode("latin-1") for m in re.finditer(rb"[\x20-\x7e]{3,}", d[12:])]
    print(" | ".join(p for p in parts if not p.startswith("@file")))
