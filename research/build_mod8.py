"""Build the override archive: the opening cutscene pauses at a line's end until the German line is done.

Rules: only active lines count; everything runs at original speed outside a pause; a nested chore runs in
real time; sounds move but are never stretched. Ordinary dialogs keep their simple stretched timeline.

Usage: build_mod8.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv> <archives dir>
                     <output dir> <set name> <landb> [...]
"""
import array
import csv
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anm_patch import patch
from build_mod import crc64, make_archive
from chore_fit import line_resources
from chore_warp import chore_info, find_times, line_hashes
from curves import refine
from ectt import Ectt
from ima import FRAME_SAMPLES, make_fsb5_ima
from nctt import read_nctt
from port_schedule import apply_map, pairs_to_map, port
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox

INNER = "cs_opening.chore"
OUTER = "env_office_cs_opening_e1_56.chore"
ACTIVE_FLAG = 2
STEP = 0.002  # a pause is a jump in the table between two original times this close together


def is_active(d, block):
    return d[block + 13 + ACTIVE_FLAG] == 0x31


def active_seconds(d, hashes, seconds):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    return {r: seconds[r] for r, _, b, _ in line_resources(d, hashes, blocks) if r in seconds and is_active(d, b)}


def line_table(d, hashes, seconds, base=None, start_shift=0.0, hold=False):
    """Make room for each active line; `base` pairs come first for a nested scene.

    With `hold` the scene runs at original speed and stops at the line's end; without it the line's
    own stretch of timeline is slowed down.
    """
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    spans = sorted((*struct.unpack_from("<ff", d, b), r) for r, _, b, _ in line_resources(d, hashes, blocks) if is_active(d, b))
    pairs = list(base) if base else [(0.0, 0.0)]
    floor = pairs[-1][0]
    shift = start_shift
    for s, e, rid in spans:
        if s < floor:
            continue
        pairs.append((s, s + shift))
        extra = max(0.0, seconds[rid] - (e - s)) if rid in seconds else 0.0
        if hold and extra > 0:
            pairs.append((e, e + shift))
            shift += extra
            pairs.append((e + STEP, e + STEP + shift))
        else:
            shift += extra
            pairs.append((e, e + shift))
    return pairs_to_map(pairs)


def named_records(d, body, crc):
    """Records whose name checksum is known, in file order, without the repeated second mention."""
    hits = []
    for i in range(body, len(d) - 8):
        n = crc.get(d[i:i + 8])
        if n and (not hits or hits[-1][1] != n or i - hits[-1][0] > 64):
            hits.append((i, n))
    return hits


def fix_sounds(original, patched, table, crc):
    """Sounds keep their duration and curve shape: every block just moves to its new start."""
    body, _, length = chore_info(original)
    blocks, keys, _ = find_times(original, body, length)
    blocks = sorted(blocks)
    out = bytearray(patched)
    protected = []
    moved = 0
    hits = named_records(original, body, crc)
    for j, (pos, name) in enumerate(hits):
        limit = hits[j + 1][0] if j + 1 < len(hits) else len(original)
        own = [b for b in blocks if pos < b < limit]
        if not own:
            continue
        if name.endswith(".chore"):
            protected.append((pos, own[0]))
        if not name.endswith(".wav"):
            continue
        protected.append((pos, own[0]))
        rows = [struct.unpack_from("<ff", original, b) for b in own]
        for b, (s, e) in zip(own, rows):
            shift = apply_map(table, s) - s
            struct.pack_into("<ff", out, b, s + shift, e + shift)
        starts = [s for s, _ in rows]
        for k in keys:
            if pos < k < own[0]:
                t = struct.unpack_from("<f", original, k)[0]
                ref = [s for s in starts if s <= t + 0.02] or starts[:1]
                struct.pack_into("<f", out, k, t + apply_map(table, ref[-1]) - ref[-1])
        moved += 1
    return bytes(out), protected, moved


def main():
    dll, source, voices, mapping, arch_dir, out, set_name, *landbs = sys.argv[1:]
    rows = {int(r["remaster_id"]): r for r in csv.DictReader(open(mapping, encoding="utf-8-sig"), delimiter=";")}
    old_key = load_key(source, "SM201")
    key = load_key(source, "SMBTaS")
    remaster = Ectt(os.path.join(arch_dir, "SM2_pc_SamMax201_compressed.ttarch2"), key)
    preview = os.path.join(out, "preview_wav")
    install = os.path.join(out, "install")
    os.makedirs(preview, exist_ok=True)
    os.makedirs(install, exist_ok=True)

    crc = {}
    names = set(remaster.files)
    for f in ("SM2_pc_SamMax201_uncompressed.ttarch2", "SM2_pc_Common_uncompressed.ttarch2"):
        names.update(read_nctt(os.path.join(arch_dir, f))[1])
    names.update(Ectt(os.path.join(arch_dir, "SM2_pc_Common_compressed.ttarch2"), key).files)
    for n in names:
        if n.lower().endswith((".wav", ".chore", ".anm")):
            crc[struct.pack("<Q", crc64(n.lower().encode()))] = n.lower()
    print("resource names known:", len(crc))

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

    by_lower = {n.lower(): n for n in remaster.files}
    inner = remaster.read(by_lower[INNER])
    schedule = line_table(inner, hashes, active_seconds(inner, hashes, seconds), hold=True)
    pauses = [(round(x, 2), round(y2 - y - STEP, 2)) for x, x2, y, y2 in zip(schedule[0], schedule[0][1:], schedule[1], schedule[1][1:]) if x2 - x < 2 * STEP and y2 - y > 0.01]
    print("opening pauses (scene time, seconds):", pauses)
    print("longest pause:", max(p for _, p in pauses), " total:", round(sum(p for _, p in pauses), 2))

    # The outer chore follows the inner one exactly while the inner one plays.
    outer = remaster.read(by_lower[OUTER])
    body, _, length = chore_info(outer)
    blocks, _, _ = find_times(outer, body, length)
    nested = next(p for p, n in named_records(outer, body, crc) if n == INNER)
    start, end = struct.unpack_from("<ff", outer, min(b for b in blocks if b > nested))
    pairs = [(0.0, 0.0), (start, start)]
    pairs += [(start + x, start + y) for x, y in zip(*schedule) if start + x > start and start + x <= end]
    new_end = start + apply_map(schedule, end - start)
    if pairs[-1][0] < end:
        pairs.append((end, new_end))
    outer_table = line_table(outer, hashes, active_seconds(outer, hashes, seconds), pairs, new_end - end, hold=True)
    print(f"nested scene {start:.3f}-{end:.3f} -> {start:.3f}-{new_end:.3f}")

    wanted = {h for h, r in hashes.items() if r in selected}
    misfits = curves = points = count = sounds = 0
    for n in sorted(remaster.files):
        if not n.endswith(".chore"):
            continue
        d = remaster.read(n)
        if not any(h in d for h in wanted):
            continue
        active = active_seconds(d, hashes, seconds)
        low = n.lower()
        table = schedule if low == INNER else outer_table if low == OUTER else line_table(d, hashes, active)
        data, report, new_length, lines = port(d, hashes, active, table)
        data, protected, moved = fix_sounds(d, data, table, crc)
        data, changed, added = refine(d, data, table, lines, protected)
        files[n] = data
        count += 1
        curves += changed
        points += added
        sounds += moved
        bad = [r for r in report if not r[5]]
        misfits += len(bad)
        if low in (INNER, OUTER) or bad:
            print(f"{n}: length {chore_info(d)[2]:.2f} -> {new_length:.2f}, active lines {len(active)}, curves refined {changed}, sounds moved {moved}, too long {len(bad)}")
        for r in bad:
            print(f"   {r[0]} too long by {r[1] + r[3] - r[4]:.2f}s")
    print(f"chores {count}, curves refined {curves}, points {points}, sounds moved {sounds}, lines too long {misfits}")

    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
