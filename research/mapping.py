"""Read-only: map remaster voice IDs to 2009 voice IDs through English text; check with audio duration."""
import csv
import glob
import os
import re
import struct
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, sys.argv[1])
from nctt import read_nctt
from ttarch4 import load_key, read_table

source, old_de_voice, old_en_voice, nctt_path, landb_dir, old_lang_dir, out_csv = sys.argv[2:9]
key = load_key(source, "SM201")


def parse_old(path):
    d = open(path, "rb").read()
    p = 44
    count = struct.unpack_from("<I", d, 40)[0] if False else None
    rows = {}
    n = struct.unpack_from("<I", d, 48)[0] if False else None
    # Entries start right after the 8-byte size/count pair at offset 44.
    p = 52
    while p + 8 < len(d):
        a, b = struct.unpack_from("<II", d, p)
        if a != b:
            break
        p += 8
        fields = []
        for _ in range(4):
            block, ln = struct.unpack_from("<II", d, p)
            fields.append(d[p + 8:p + 8 + ln].decode("cp1252", "replace"))
            p += block
        p += 7
        rows[a] = (fields[0], fields[1])
    return rows


def parse_new(path):
    d = open(path, "rb").read()
    rows = {}
    for i in range(0, len(d) - 60):
        if d[i + 16:i + 20] != b"\0\0\0\0" or d[i + 20:i + 24] != b"\x0c\0\0\0":
            continue
        a = struct.unpack_from("<I", d, i)[0]
        if a != struct.unpack_from("<I", d, i + 12)[0]:
            continue
        p = i + 16 + 4 + 12 + 12 + 8 + 4 + 4
        try:
            block, ln = struct.unpack_from("<II", d, p)
            speaker = d[p + 8:p + 8 + ln].decode("utf-8", "replace")
            p += block
            block, ln = struct.unpack_from("<II", d, p)
            text = d[p + 8:p + 8 + ln].decode("utf-8", "replace")
        except struct.error:
            continue
        rows[a] = (speaker, text)
    return rows


def norm(s):
    s = re.sub(r"\{[^}]*\}|\[[^\]]*\]", " ", s)
    s = s.replace("’", "'").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


old_en = parse_old(os.path.join(old_lang_dir, "english.langdb"))
old_de = parse_old(os.path.join(old_lang_dir, "german.langdb"))
print("old entries EN/DE:", len(old_en), len(old_de))

new_en, new_de, where = {}, {}, {}
for p in glob.glob(os.path.join(landb_dir, "*_english.landb")):
    r = parse_new(p)
    new_en.update(r)
    for k in r:
        where[k] = os.path.basename(p).split("__")[1]
for p in glob.glob(os.path.join(landb_dir, "*_german.landb")):
    new_de.update(parse_new(p))
print("remaster entries EN/DE:", len(new_en), len(new_de))

_, wavs = read_nctt(nctt_path)
new_dur = {}
with open(nctt_path, "rb") as f:
    for n, (o, _size) in wavs.items():
        if not n[:-4].isdigit():
            continue
        f.seek(o)
        h = f.read(0x60)
        _v, _s, _sh, _nm, _ds, _m = struct.unpack_from("<6I", h, 4)
        word = struct.unpack_from("<Q", h, 0x3C)[0]
        rate = {5: 22050, 7: 32000, 8: 44100, 9: 48000}.get((word >> 1) & 0xF, 44100)
        samples = (word >> 34) & 0x3FFFFFFF
        new_dur[int(n[:-4])] = samples / rate
print("remaster voice files:", len(new_dur), " with EN text:", len(new_dur.keys() & new_en.keys()))


def voice(path):
    meta, _, files = read_table(path, key)
    out = {}
    with open(path, "rb") as f:
        for n, o, s in files:
            if n.endswith(".vox") and n[:-4].isdigit():
                f.seek(meta["data_start"] + o + 20 + 1)
                out[int(n[:-4])] = struct.unpack("<f", f.read(4))[0]
    return out


old_en_dur = voice(old_en_voice)
old_de_dur = voice(old_de_voice)
print("old voice files EN/DE:", len(old_en_dur), len(old_de_dur))

by_text = defaultdict(list)
for i in old_en_dur:
    if i in old_en:
        by_text[norm(old_en[i][1])].append(i)

rows, status = [], Counter()
errs = []
for nid in sorted(new_dur):
    if nid not in new_en:
        status["no remaster text"] += 1
        rows.append((nid, "", "no remaster text", new_dur[nid], "", "", "", ""))
        continue
    sp, text = new_en[nid]
    cands = by_text.get(norm(text), [])
    kind = "exact"
    if not cands:
        kind = "none"
    elif len(cands) > 1:
        same_sp = [c for c in cands if old_en[c][0] == sp] or cands
        cands = sorted(same_sp, key=lambda c: abs(old_en_dur[c] - new_dur[nid]))
        kind = "exact-dup"
    if kind == "none":
        status["no old match"] += 1
        rows.append((nid, "", kind, new_dur[nid], "", sp, text, ""))
        continue
    best = cands[0]
    delta = new_dur[nid] - old_en_dur[best]
    errs.append(delta)
    status[kind] += 1
    rows.append((nid, best, kind, round(new_dur[nid], 3), round(old_en_dur[best], 3), sp, text, old_de.get(best, ("", ""))[1]))

print("status:", status.most_common())
print("mapped lines:", len(errs))
for lim in (0.05, 0.1, 0.25, 0.5, 1, 2):
    print(f"  |duration difference| <= {lim:>4}s: {sum(abs(e) <= lim for e in errs)}")
print("  largest:", sorted((round(abs(e), 2) for e in errs), reverse=True)[:12])

used = [r[1] for r in rows if r[1] != ""]
print("distinct old lines used:", len(set(used)), " mapped lines with German vox:", sum(u in old_de_dur for u in used))
print("old EN voice unused:", len(set(old_en_dur) - set(used)))

de_same = de_diff = 0
samples = []
for r in rows:
    if r[1] == "" or r[0] not in new_de:
        continue
    a, b = norm(new_de[r[0]][1]), norm(old_de.get(r[1], ("", ""))[1])
    if a == b:
        de_same += 1
    else:
        de_diff += 1
        if len(samples) < 6:
            samples.append((new_de[r[0]][1], old_de.get(r[1], ("", ""))[1]))
print("German subtitle identical to 2009:", de_same, " different:", de_diff)
for s in samples:
    print("   new:", s[0][:90], "\n   old:", s[1][:90])

none = [r for r in rows if r[2] == "none"]
close = 0
print("\nUnmatched examples:")
all_old = list(by_text)
for r in none[:12]:
    m = max(all_old, key=lambda t: SequenceMatcher(None, t, norm(r[6])).quick_ratio())
    q = SequenceMatcher(None, m, norm(r[6])).ratio()
    print(f"  {r[0]} [{r[5]}] {r[6][:75]!r}\n      nearest ({q:.2f}): {m[:75]!r}")
for r in none:
    m = max(all_old, key=lambda t: SequenceMatcher(None, t, norm(r[6])).quick_ratio())
    if SequenceMatcher(None, m, norm(r[6])).ratio() >= 0.8:
        close += 1
print("unmatched with a close text (>=0.80):", close, "of", len(none))

with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["remaster_id", "old_id", "match", "remaster_seconds", "old_english_seconds", "speaker", "english", "old_german"])
    w.writerows(rows)
print("\nwritten:", out_csv)
