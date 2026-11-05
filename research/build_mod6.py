"""Build the override archive: compressed German voices at original speed, exact line lengths,
Telltale's German cutscene schedule, and time curves that follow the lines.

Usage: build_mod6.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
                     <episode compressed ttarch2> <old EN chore> <old DE chore> <output dir> <set name> <landb> [...]
"""
import array
import csv
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anm_patch import patch
from build_mod import make_archive
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from curves import refine
from ectt import Ectt
from ima import FRAME_SAMPLES, make_fsb5_ima
from port_schedule import pairs_to_map, port, time_map
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox

SCHEDULED = "cs_opening.chore"


def line_table(d, hashes, seconds):
    """A timeline stretched just enough for each line, for chores without a schedule from 2009."""
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    spans = []
    for rid, _, block, _ in line_resources(d, hashes, blocks):
        s, e = struct.unpack_from("<ff", d, block)
        spans.append((s, e, rid))
    pairs = [(0.0, 0.0)]
    shift = 0.0
    for s, e, rid in sorted(spans):
        pairs.append((s, s + shift))
        if rid in seconds:
            shift += max(0.0, seconds[rid] - (e - s))
        pairs.append((e, e + shift))
    return pairs_to_map(pairs)


def main():
    dll, source, voices, mapping, episode, old_en, old_de, out, set_name, *landbs = sys.argv[1:]
    rows = {int(r["remaster_id"]): r for r in csv.DictReader(open(mapping, encoding="utf-8-sig"), delimiter=";")}
    old_key = load_key(source, "SM201")
    remaster = Ectt(episode, load_key(source, "SMBTaS"))
    preview = os.path.join(out, "preview_wav")
    install = os.path.join(out, "install")
    os.makedirs(preview, exist_ok=True)
    os.makedirs(install, exist_ok=True)

    hashes, selected = {}, set()
    for n in remaster.files:
        if n.endswith("_english.landb"):
            h = line_hashes(remaster.read(n))
            hashes.update(h)
            if n[:-len("_english.landb")].lower() in landbs:
                selected.update(h.values())
    selected = {r for r in selected if r in rows and rows[r]["old_id"]}
    print("selected voiced, mapped lines:", len(selected))

    speex, files, seconds = None, {}, {}
    for rid in sorted(selected):
        v = parse_vox(read_vox(voices, rows[rid]["old_id"] + ".vox", old_key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        for p in v["packets"]:
            pcm.extend(speex.decode(p)[0])
        pcm.extend(array.array("h", bytes(2 * (-len(pcm) % FRAME_SAMPLES))))
        seconds[rid] = len(pcm) / v["rate"]
        files[f"{rid}.wav"] = make_fsb5_ima(str(rid), pcm, v["rate"])
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v["rate"])
            w.writeframes(pcm.tobytes())
        anm = f"{rid}.anm"
        if anm in remaster.files:
            files[anm] = patch(remaster.read(anm), seconds[rid])[0]

    schedule = time_map(open(old_en, "rb").read(), open(old_de, "rb").read())
    wanted = {h for h, r in hashes.items() if r in selected}
    misfits = curves = points = count = 0
    for n in sorted(remaster.files):
        if not n.endswith(".chore"):
            continue
        d = remaster.read(n)
        if not any(h in d for h in wanted):
            continue
        table = schedule if n.lower() == SCHEDULED else line_table(d, hashes, seconds)
        data, report, new_length, lines = port(d, hashes, seconds, table)
        data, changed, added = refine(d, data, table, lines)
        files[n] = data
        count += 1
        curves += changed
        points += added
        bad = [r for r in report if not r[5]]
        misfits += len(bad)
        if n.lower() == SCHEDULED or changed > 5 or bad:
            print(f"{n}: length {chore_info(d)[2]:.2f} -> {new_length:.2f}, curves refined {changed}, points {added}, lines too long {len(bad)}")
        for r in bad:
            print(f"   {r[0]} too long by {r[1] + r[3] - r[4]:.2f}s")
    print(f"chores {count}, curves refined {curves}, points {points}, lines too long {misfits}")

    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
