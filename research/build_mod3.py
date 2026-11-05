"""Build the override archive: German voices, stretched lipsync, and stretched chores.

Usage: build_mod3.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
                     <SM2_pc_SamMax201_compressed.ttarch2> <output dir> <set name> <id> [<id> ...]
"""
import array
import csv
import os
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anm_patch import patch
from build_mod import make_archive, make_fsb5
from chore_warp import line_hashes, warp
from ectt import Ectt
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox


def main():
    dll, source, voices, mapping, episode, out, set_name, *ids = sys.argv[1:]
    rows = {r["remaster_id"]: r for r in csv.DictReader(open(mapping, encoding="utf-8-sig"), delimiter=";")}
    old_key = load_key(source, "SM201")
    remaster = Ectt(episode, load_key(source, "SMBTaS"))
    preview = os.path.join(out, "preview_wav")
    install = os.path.join(out, "install")
    os.makedirs(preview, exist_ok=True)
    os.makedirs(install, exist_ok=True)
    speex = None
    files = {}
    seconds = {}
    for rid in ids:
        r = rows[rid]
        v = parse_vox(read_vox(voices, r["old_id"] + ".vox", old_key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        for p in v["packets"]:
            pcm.extend(speex.decode(p)[0])
        seconds[int(rid)] = len(pcm) / v["rate"]
        files[rid + ".wav"] = make_fsb5(rid, pcm, v["rate"])
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v["rate"])
            w.writeframes(pcm.tobytes())
        name = rid + ".anm"
        if name in remaster.files:
            files[name] = patch(remaster.read(name), seconds[int(rid)])[0]

    hashes = {}
    for n in remaster.files:
        if n.endswith("_english.landb"):
            hashes.update(line_hashes(remaster.read(n)))
    wanted = {h: rid for h, rid in hashes.items() if rid in seconds}
    print("line hashes:", len(hashes), "selected:", len(wanted))

    covered = set()
    for n in sorted(remaster.files):
        if not n.endswith(".chore"):
            continue
        d = remaster.read(n)
        if not any(h in d for h in wanted):
            continue
        print(n)
        data, report, leftovers, added, new_length = warp(d, hashes, seconds)
        files[n] = data
        for rid, s, e, g, need in report:
            covered.add(rid)
            print(f"   {rid} block {s:7.2f}-{e:7.2f} ({e - s:5.2f}s)  German {g:5.2f}s  pause +{need:4.2f}s")
        print(f"   added {added:.2f}s, new length {new_length:.2f}s, untouched copies of line-end times: {leftovers}")
    print("lines covered by a chore:", len(covered), "missing:", sorted(set(seconds) - covered))

    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
