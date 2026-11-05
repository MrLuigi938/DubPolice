"""Build the override archive for chosen conversations: German voices, lipsync and timing adapted.

Usage: build_mod4.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
                     <episode compressed ttarch2> <output dir> <set name> <landb name> [<landb name> ...]
"""
import array
import csv
import math
import os
import sys
import wave
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anm_patch import patch
from build_mod import make_archive, make_fsb5
from chore_fit import analyse, apply_fit, change_tempo, stretch_chore, trim
from chore_warp import line_hashes
from ectt import Ectt
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox


def main():
    dll, source, voices, mapping, episode, out, set_name, *landbs = sys.argv[1:]
    rows = {int(r["remaster_id"]): r for r in csv.DictReader(open(mapping, encoding="utf-8-sig"), delimiter=";")}
    old_key = load_key(source, "SM201")
    remaster = Ectt(episode, load_key(source, "SMBTaS"))
    preview = os.path.join(out, "preview_wav")
    install = os.path.join(out, "install")
    os.makedirs(preview, exist_ok=True)
    os.makedirs(install, exist_ok=True)

    hashes = {}
    selected = set()
    for n in remaster.files:
        if n.endswith("_english.landb"):
            h = line_hashes(remaster.read(n))
            hashes.update(h)
            if n[:-len("_english.landb")].lower() in landbs:
                selected.update(h.values())
    selected = {r for r in selected if r in rows and rows[r]["old_id"]}
    print("selected voiced, mapped lines:", len(selected))
    wanted = {h for h, r in hashes.items() if r in selected}

    chores = {}
    for n in sorted(remaster.files):
        if n.endswith(".chore"):
            d = remaster.read(n)
            if any(h in d for h in wanted):
                chores[n] = (d, analyse(d, hashes, n))
    print("chores:", len(chores), "cutscenes:", [n for n, (_, i) in chores.items() if i["cutscene"]])

    room = {}
    for n, (d, info) in chores.items():
        if info["cutscene"]:
            for rid, _, _, _ in info["lines"]:
                if rid in selected:
                    room[rid] = min(room.get(rid, math.inf), info["room"][rid])

    speex = None
    files = {}
    seconds = {}
    tempos = {}
    for rid in sorted(selected):
        r = rows[rid]
        v = parse_vox(read_vox(voices, r["old_id"] + ".vox", old_key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        for p in v["packets"]:
            pcm.extend(speex.decode(p)[0])
        rate = v["rate"]
        factor = 1.0
        limit = room.get(rid, math.inf)
        if len(pcm) / rate > limit:
            pcm = trim(pcm, rate)
            if len(pcm) / rate > limit:
                factor = (len(pcm) / rate) / limit
                pcm = change_tempo(pcm, rate, factor)
        tempos[rid] = factor
        seconds[rid] = len(pcm) / rate
        files[f"{rid}.wav"] = make_fsb5(str(rid), pcm, rate)
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(pcm.tobytes())
        anm = f"{rid}.anm"
        if anm in remaster.files:
            files[anm] = patch(remaster.read(anm), seconds[rid])[0]

    fast = sorted(((f, rid) for rid, f in tempos.items() if f > 1.001), reverse=True)
    print("lines sped up:", len(fast), [(rid, round(f, 2)) for f, rid in fast[:25]])

    kinds = Counter()
    for n, (d, info) in chores.items():
        if info["cutscene"]:
            data, report = apply_fit(d, info, seconds)
            files[n] = data
            kinds["cutscene"] += 1
            print(n, f"length {info['length']:.2f} unchanged, spanning track covers {info['longest']} lines")
            for rid, s, e, new_end, g in report:
                print(f"   {rid} {s:7.2f}-{e:7.2f} -> {new_end:7.2f}  audio {g:5.2f}s  tempo x{tempos[rid]:.2f}")
        else:
            present = {k: v for k, v in seconds.items() if k in {x[0] for x in info["lines"]}}
            data, report, leftovers, added, new_length = stretch_chore(d, hashes, present)
            files[n] = data
            kinds["dialog"] += 1
            kinds["dialog with pause"] += added > 0
    print("chore kinds:", dict(kinds))

    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
