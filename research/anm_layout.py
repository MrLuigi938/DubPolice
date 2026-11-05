"""Read-only: show the structure of a remaster lipsync .anm, focusing on the keyframe records."""
import struct
import sys

path = sys.argv[1]
d = open(path, "rb").read()
print("file", len(d))
print("from 116:")
for o in range(116, 300, 16):
    print(f" {o:5} {d[o:o+16].hex(' ')}")

# Look for the repeating record pattern near time floats.
print("\nfloats in 0..length with their following bytes:")
length = struct.unpack_from("<f", d, 132)[0]
count = 0
for i in range(196, len(d) - 8):
    v = struct.unpack_from("<f", d, i)[0]
    if 0 <= v <= length + 0.01 and (abs(v * 30 - round(v * 30)) < 2e-3) and d[i + 4:i + 5] in (b"\x30", b"\x31"):
        print(f"  @{i:5} t={v:7.3f} next={d[i+4:i+16].hex(' ')}  prev={d[i-8:i].hex(' ')}")
        count += 1
        if count > 45:
            break
print("\nlast 80 bytes:", d[-80:].hex(" "))
