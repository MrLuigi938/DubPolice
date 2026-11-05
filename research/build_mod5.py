"""Build the override archive: German voices at original speed, Telltale's 2009 German cutscene timing.

Usage: build_mod5.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
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
from build_mod import make_archive, make_fsb5
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from ectt import Ectt
from port_schedule import apply_map, pairs_to_map, port, time_map
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox

TAIL_SILENCE = 0.25  # stored audio always outlasts its block, as in the original game
CUTSCENE = "cs_opening.chore"
VARIANT = "env_office_cs_opening_e1_56.chore"


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

    # Longest block each line has in any chore: the audio must never end before it.
    longest = {}
    wanted = {h for h, r in hashes.items() if r in selected}
    for n in remaster.files:
        if n.endswith(".chore"):
            c = remaster.read(n)
            if any(h in c for h in wanted):
                body, _, length = chore_info(c)
                blocks, _, _ = find_times(c, body, length)
                for rid, _, block, _ in line_resources(c, hashes, blocks):
                    s, e = struct.unpack_from("<ff", c, block)
                    longest[rid] = max(longest.get(rid, 0.0), e - s)

    speex, files, seconds = None, {}, {}
    padded = 0
    for rid in sorted(selected):
        v = parse_vox(read_vox(voices, rows[rid]["old_id"] + ".vox", old_key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        for p in v["packets"]:
            pcm.extend(speex.decode(p)[0])
        seconds[rid] = len(pcm) / v["rate"]
        need = max(seconds[rid], longest.get(rid, 0.0)) + TAIL_SILENCE
        extra = int(round(need * v["rate"])) - len(pcm)
        padded += longest.get(rid, 0.0) > seconds[rid]
        pcm.extend(array.array("h", bytes(2 * extra)))
        files[f"{rid}.wav"] = make_fsb5(str(rid), pcm, v["rate"])
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v["rate"])
            w.writeframes(pcm.tobytes())
        anm = f"{rid}.anm"
        if anm in remaster.files:
            files[anm] = patch(remaster.read(anm), seconds[rid])[0]

    print("lines shorter than their English block:", padded)
    table = time_map(open(old_en, "rb").read(), open(old_de, "rb").read())
    print("time pairs:", len(table[0]), "75.076 ->", apply_map(table, 75.076))

    names = {n.lower(): n for n in remaster.files}
    main_name = names[CUTSCENE]
    d = remaster.read(main_name)
    data, report, new_length, lines = port(d, hashes, seconds, table)
    files[main_name] = data
    print(main_name, f"length {chore_info(d)[2]:.2f} -> {new_length:.2f}")
    misfits = 0
    for rid, s, e, g, next_start, fits in sorted(report, key=lambda r: r[1]):
        misfits += not fits
        print(f"   {rid} {s:7.2f}-{e:7.2f}  audio {g:5.2f}s  next {next_start if next_start is None else round(next_start, 2)}  {'ok' if fits else 'TOO LONG by %.2fs' % (s + g - next_start)}")
    print("lines that do not fit:", misfits)

    # The dialog-tool copy of the scene has its own start times: anchor it to the same lines.
    original_start = {rid: struct.unpack_from("<f", d, block)[0] for rid, _, block, _ in lines}
    new_start = {rid: s for rid, s, *_ in report}
    variant_name = names[VARIANT]
    v = remaster.read(variant_name)
    body, _, length = chore_info(v)
    v_blocks, _, _ = find_times(v, body, length)
    v_lines = line_resources(v, hashes, v_blocks)
    pairs = []
    for rid, _, block, _ in v_lines:
        if rid in new_start:
            s = struct.unpack_from("<f", v, block)[0]
            pairs.append((s, s + new_start[rid] - original_start[rid]))
    v_table = pairs_to_map(pairs)
    v_data, v_report, v_length, _ = port(v, hashes, seconds, v_table)
    files[variant_name] = v_data
    print(variant_name, f"length {length:.2f} -> {v_length:.2f}, lines that do not fit: {sum(not r[5] for r in v_report)}")
    for rid, s, e, g, next_start, fits in v_report:
        if not fits:
            print(f"   {rid} TOO LONG by {s + g - next_start:.2f}s")

    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
