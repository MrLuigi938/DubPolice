"""Read-only: find how the 2009 German chore keeps long animations in step with its longer timeline."""
import difflib
import re
import struct
import sys

en = open(sys.argv[1], "rb").read()
de = open(sys.argv[2], "rb").read()


def clean(b):
    return re.sub(rb"[^ -~]", b".", b).decode()


def dump(d, a, n):
    for o in range(a, a + n, 16):
        print(f"   {o:6} {d[o:o+16].hex(' '):48} {clean(d[o:o+16])}")


print("strings only in German:", sorted({m.group() for m in re.finditer(rb"[\x20-\x7e]{4,}", de)} - {m.group() for m in re.finditer(rb"[\x20-\x7e]{4,}", en)})[:40])
print("strings only in English:", sorted({m.group() for m in re.finditer(rb"[\x20-\x7e]{4,}", en)} - {m.group() for m in re.finditer(rb"[\x20-\x7e]{4,}", de)})[:40])

for label, d in (("English", en), ("German", de)):
    at = d.find(b"cs_opening_sk22_max.anm")
    print(f"\n{label}: first resource at {at}")
    dump(d, at - 16, 300)

i = de.find(b"AG_BodyLower")
print("\nGerman AG_BodyLower at", i)
dump(de, i - 60, 200)

# Resource names and their block lists, in order, for both languages.
for label, d in (("English", en), ("German", de)):
    names = [(m.start(), m.group().decode()) for m in re.finditer(rb"[A-Za-z0-9_]{5,}\.(?:anm|wav|aud|vox|chore|lang|dlg)", d)]
    print(f"\n{label} resources ({len(names)}):", [n for _, n in names][:60])

# All float pairs that differ between languages, ignoring block times.
sm = difflib.SequenceMatcher(None, en, de, autojunk=False) if len(en) < 3000 else None
print("\nGerman floats around 80.44 / 85.516:")
for target in (80.44, 85.516, 70.0, 75.076):
    for label, d in (("en", en), ("de", de)):
        hits = [i for i in range(len(d) - 3) if abs(struct.unpack_from("<f", d, i)[0] - target) < 0.002]
        print(f"  {target} in {label}:", hits[:14])
