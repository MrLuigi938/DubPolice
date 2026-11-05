"""Read-only: is a line's ending repeated inside the audio file, and how do block and audio lengths relate?"""
import array
import math
import os
import struct
import sys
import wave

sys.path.insert(0, sys.argv[1])
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from nctt import read_nctt
from ttarch4 import load_key

source, episode, uncompressed, mod, preview = sys.argv[2:7]


def repeat_score(path):
    """Best similarity between the last 0.5 s of speech and any earlier stretch (1.0 = exact repeat)."""
    with wave.open(path, "rb") as w:
        rate = w.getframerate()
        pcm = array.array("h", w.readframes(w.getnframes()))
    step = 16
    x = [abs(v) for v in pcm[::step]]
    n = len(x)
    size = int(0.5 * rate / step)
    end = n
    while end > size and max(x[end - 40:end]) < 300:
        end -= 40
    tail = x[end - size:end]
    tn = math.sqrt(sum(v * v for v in tail)) or 1.0
    best = 0.0
    at = 0
    for i in range(0, end - 2 * size, 8):
        seg = x[i:i + size]
        sn = math.sqrt(sum(v * v for v in seg)) or 1.0
        c = sum(a * b for a, b in zip(tail, seg)) / (tn * sn)
        if c > best:
            best, at = c, i
    return best, at * step / rate, (end - size) * step / rate, n * step / rate


print("German audio, line ending vs earlier audio (loudness similarity):")
for rid in (400637953, 400637954, 400637956, 400637959):
    best, at, tail_at, total = repeat_score(os.path.join(preview, f"{rid}.wav"))
    print(f"  {rid}: total {total:5.2f}s, ending at {tail_at:5.2f}s, best match {best:.3f} at {at:5.2f}s")

a = Ectt(episode, load_key(source, "SMBTaS"))
hashes = {}
for n in a.files:
    if n.endswith("_english.landb"):
        hashes.update(line_hashes(a.read(n)))

_, wavs = read_nctt(uncompressed)
real = {}
with open(uncompressed, "rb") as f:
    for n, (o, s) in wavs.items():
        if n[:-4].isdigit():
            f.seek(o)
            h = f.read(0x60)
            word = struct.unpack_from("<Q", h, 0x3C)[0]
            rate = {5: 22050, 7: 32000, 8: 44100, 9: 48000}.get((word >> 1) & 15, 44100)
            real[int(n[:-4])] = (word >> 34) / rate

d = a.read(next(n for n in a.files if n.lower() == "cs_opening.chore"))
body, _, length = chore_info(d)
blocks, _, _ = find_times(d, body, length)
print("\nOriginal remaster: block length minus English audio length")
diffs = []
for rid, pos, block, limit in line_resources(d, hashes, blocks):
    if rid in real:
        s, e = struct.unpack_from("<ff", d, block)
        stored = struct.unpack_from("<f", d, pos + 8)[0]
        diffs.append(e - s - real[rid])
        print(f"  {rid}: block {e - s:6.3f}  stored {stored:6.3f}  audio {real[rid]:6.3f}  block-audio {e - s - real[rid]:+.3f}")
print("  range:", round(min(diffs), 3), "to", round(max(diffs), 3))

_, mf = read_nctt(mod)
with open(mod, "rb") as f:
    o, s = mf["cs_opening.chore"]
    f.seek(o)
    m = f.read(s)
    body, _, length = chore_info(m)
    blocks, _, _ = find_times(m, body, length)
    print("\nMod: block length minus German audio length")
    for rid, pos, block, limit in line_resources(m, hashes, blocks)[:6]:
        s0, e0 = struct.unpack_from("<ff", m, block)
        o2, s2 = mf.get(f"{rid}.wav", (None, None))
        if o2 is None:
            continue
        f.seek(o2)
        h = f.read(0x60)
        word = struct.unpack_from("<Q", h, 0x3C)[0]
        print(f"  {rid}: block {e0 - s0:6.3f}  audio {(word >> 34) / 32000:6.3f}  block-audio {e0 - s0 - (word >> 34) / 32000:+.3f}")
