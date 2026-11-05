"""Read-only: count mapped lines per conversation and show the first lines of early conversations."""
import csv
import glob
import os
import re
import struct
import sys

landb_dir, mapping_csv = sys.argv[1:3]
wanted = sys.argv[3:]
rows = {int(r["remaster_id"]): r for r in csv.DictReader(open(mapping_csv, encoding="utf-8-sig"), delimiter=";")}


def ids_in(path):
    d = open(path, "rb").read()
    out = []
    for i in range(0, len(d) - 24):
        if d[i + 16:i + 20] == b"\0\0\0\0" and d[i + 20:i + 24] == b"\x0c\0\0\0" and d[i:i + 4] == d[i + 12:i + 16]:
            out.append(struct.unpack_from("<I", d, i)[0])
    return out


for p in sorted(glob.glob(os.path.join(landb_dir, "*_english.landb"))):
    name = os.path.basename(p).split("__")[1].replace("_english.landb", "")
    ids = ids_in(p)
    voiced = [i for i in ids if i in rows]
    ok = [i for i in voiced if rows[i]["old_id"]]
    print(f"{name:40} entries {len(ids):4} voiced {len(voiced):4} mapped {len(ok):4}")
    if name in wanted:
        for i in voiced[:12]:
            r = rows[i]
            print("   ", i, r["speaker"], ascii(r["english"][:60]), "->", ascii(r["old_german"][:60]))
