"""Bring the dubbed voices of the original Sam & Max seasons into the remasters.

The tool reads your own copy of the old release and builds one extra archive per episode.
No original game file is changed. Usage:

    python sammax_de.py --game "<remaster folder>" --source "<old game or disc>" [--language french] [--episodes 201 202]
    python sammax_de.py --game "<remaster folder>" --uninstall

The season follows from the remaster folder.
"""
import argparse
import array
import concurrent.futures as futures
import csv
import json
import math
import multiprocessing
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from difflib import SequenceMatcher

# Inside the exe, bundled files are unpacked to a temporary folder.
HERE = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
# Bundled inside the exe; next to src/ when run from the source code.
BIN = os.path.join(HERE, "bin") if hasattr(sys, "_MEIPASS") else os.path.join(os.path.dirname(HERE), "bin")

from anm_patch import patch  # noqa: E402
from build_mod import crc64, make_archive  # noqa: E402
from chore_fit import line_resources  # noqa: E402
from chore_warp import chore_info, find_times, line_hashes  # noqa: E402
from curves import TIME_PROPERTY, refine  # noqa: E402
from ectt import Blowfish7, Ectt  # noqa: E402
import enhance  # noqa: E402
from nctt import read_nctt  # noqa: E402
from old_archive import FlatArchive, LooseVoices, OldArchive  # noqa: E402
from port_schedule import apply_map, pairs_to_map, port  # noqa: E402
from ttarch4 import load_key  # noqa: E402
from variants import encrypt  # noqa: E402
from vox2wav import Speex, parse_vox, voice_header_size  # noqa: E402

SEASONS = {
    1: {
        "exe": "SamMax100.exe",
        "prefix": "SM1",
        "key": "SMSTWR",
        "episodes": ("101", "102", "103", "104", "105", "106"),
        "languages": ("german", "french"),
        "files": {"data": "sammax{e}_{lang}.ttarch"},
        "same_ids": False,
        "flat": True,
    },
    2: {
        "exe": "SamMax200.exe",
        "prefix": "SM2",
        "key": "SMBTaS",
        "episodes": ("201", "202", "203", "204", "205"),
        "languages": ("german", "french"),
        "files": {
            "data": "1_sammax{e}_pc_data.ttarch",
            "voice_en": "2_sammax{e}_pc_voice.ttarch",
            "voice_dub": "2_sammax{e}_pc_voice_{lang}.ttarch",
        },
        "same_ids": False,
    },
    3: {
        "exe": "SamMax300.exe",
        "prefix": "SM3",
        "key": "SMTDP",
        "episodes": ("301", "302", "303", "304", "305"),
        "languages": ("german",),
        "files": {
            "data": "1_sammax{e}_english_pc_data.ttarch",
            "voice_en": "2_sammax{e}_english_pc_voice.ttarch",
            "voice_dub": "1_sammax{e}_pc_localized_data_{lang}.ttarch",
        },
        "same_ids": True,
    },
}
SPEEX_DLL = os.path.join(BIN, "libspeex-1.dll")
MANIFEST = "SamMax_GermanDub.json"
LEGACY_FILES = ("SM2_pc_GermanVoiceTest_uncompressed.ttarch2", "_resdesc_50_GermanVoiceTest.lua")
STEP = 0.002
ACTIVE_FLAG = 2


def say(text):
    print(text, flush=True)


def progress(step, done, total):
    print(f"PROGRESS {step} {done} {total}", flush=True)


# ---------------------------------------------------------------- finding files


def season_of_game(game):
    """The season number of a remaster folder."""
    if os.path.isdir(os.path.join(game, "Archives")):
        for number, season in SEASONS.items():
            if os.path.isfile(os.path.join(game, season["exe"])):
                return number
    raise SystemExit(f"Das ist kein unterstützter Remaster-Ordner: {game}")


def find_7zip():
    found = shutil.which("7z") or shutil.which("7za")
    bundled = os.path.join(BIN, "7z.exe")
    for path in (bundled, found, r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if path and os.path.isfile(path):
            return path
    return None


def collect_source(season, source, work, episodes, language):
    """Return {episode: {role: path}} from an installed game, a folder, or a disc with installers."""
    wanted = {e: {role: name.format(e=e, lang=language) for role, name in season["files"].items()} for e in episodes}
    found = {e: {} for e in episodes}

    def scan(folder):
        for root, _dirs, files in os.walk(folder):
            parent = os.path.basename(root).lower()
            for f in files:
                low = f.lower()
                for e, roles in wanted.items():
                    for role, name in roles.items():
                        if low != name or role in found[e]:
                            continue
                        # Season 2 ships copies for other languages under the same name.
                        if role == "voice_en" and not season["same_ids"] and parent != "english":
                            continue
                        found[e][role] = os.path.join(root, f)

    scan(source)
    needed = len(season["files"])
    missing = [e for e in episodes if len(found[e]) < needed]
    if missing:
        seven = find_7zip()
        for e in missing:
            installer = None
            for root, _dirs, files in os.walk(source):
                for f in files:
                    if f.lower() == f"sammax{e}_component.exe":
                        installer = os.path.join(root, f)
                if installer:
                    break
            if not installer:
                continue
            if not seven:
                raise SystemExit("Zum Lesen der Installationsdateien wird 7-Zip benötigt (https://www.7-zip.org).")
            say(f"Entpacke Episode {e} aus {os.path.basename(installer)} ...")
            target = os.path.join(work, f"source_{e}")
            os.makedirs(target, exist_ok=True)
            subprocess.run([seven, "x", installer, f"-o{target}", "-y", "-r", "*.ttarch"], check=True, stdout=subprocess.DEVNULL, creationflags=NO_WINDOW)
        scan(work)
    still = {e: sorted(set(wanted[e]) - set(found[e])) for e in episodes if len(found[e]) < needed}
    if still:
        raise SystemExit(f"Die alte Version wurde in dieser Sprache nicht vollständig gefunden: {still}")
    return found


# ---------------------------------------------------------------- matching lines


def parse_old_lang(d):
    """2009 language database: {id: (speaker, text)}."""
    rows = {}
    p = 52
    if d[8:14] == b"class ":
        # 2007: a list of class names, each followed by a 4-byte hash, then two 4-byte sizes.
        p = 4
        for _ in range(struct.unpack_from("<I", d, 0)[0]):
            p += 8 + struct.unpack_from("<I", d, p)[0]
        p += 8
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


def parse_new_lang(d):
    """Remaster language database: {id: (speaker, text)}."""
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
    s = re.sub(r"\{[^}]*\}|\[[^\]]*\]", " ", s).replace("\u2019", "'").lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def voice_lengths(archive, names):
    out = {}
    for n in names:
        head = archive.read(n)[:64]
        out[int(n[:-4])] = struct.unpack_from("<f", head, voice_header_size(head) + 1)[0]
    return out


def parse_old_landb(d):
    """Per-conversation language database of the 2010 release: {id: (speaker, text)}."""
    rows = {}
    marker = b"\0\0\0\0\x08\0\0\0\0\0\0\0\x08\0\0\0\0\0\0\0\x08\0\0\0\0\0\0\0\0\0\0\0"
    at = d.find(marker)
    while at >= 0:
        i = at - 8
        if i >= 0 and d[i:i + 4] == d[i + 4:i + 8]:
            p = at + len(marker) + 4
            try:
                block, ln = struct.unpack_from("<II", d, p)
                speaker = d[p + 8:p + 8 + ln].decode("cp1252", "replace")
                p += block
                block, ln = struct.unpack_from("<II", d, p)
                rows[struct.unpack_from("<I", d, i)[0]] = (speaker, d[p + 8:p + 8 + ln].decode("cp1252", "replace"))
            except struct.error:
                pass
        at = d.find(marker, at + 1)
    return rows


def old_texts(data, language):
    """Text of the old release: one database per language, or one per conversation in later seasons.

    The dubbed text only goes into the line report, so a release may keep it in another archive.
    """
    if "english.langdb" in data.files:
        name = f"{language}.langdb"
        return parse_old_lang(data.read("english.langdb")), parse_old_lang(data.read(name)) if name in data.files else {}
    english, dubbed = {}, {}
    for n in data.files:
        if n.endswith("_english.landb"):
            english.update(parse_old_landb(data.read(n)))
        elif n.endswith(f"_{language}.landb"):
            dubbed.update(parse_old_landb(data.read(n)))
    return english, dubbed


def match_lines(season, e, paths, remaster, arch_dir, work, language):
    """Pair each remaster voice with its old voice: by number where those stayed, else by English text."""
    key = load_key(None, f"SM{e}")
    if season.get("flat"):
        data = FlatArchive(paths["data"], key)
        # This release holds no English recordings; the dubbed lengths serve to tell equal texts apart.
        voice_en = voice_dub = LooseVoices(os.path.dirname(paths["data"]), key)
    else:
        data = OldArchive(paths["data"], key)
        voice_en = OldArchive(paths["voice_en"], key)
        voice_dub = OldArchive(paths["voice_dub"], key)
    old_en, old_dub = old_texts(data, language)
    numeric = lambda a: [n for n in a.files if n.endswith(".vox") and n[:-4].isdigit()]
    en_len = voice_lengths(voice_en, numeric(voice_en))
    dub_ids = {int(n[:-4]) for n in numeric(voice_dub)}

    new_text = {}
    for n in remaster.files:
        if n.endswith("_english.landb"):
            new_text.update(parse_new_lang(remaster.read(n)))
    path = os.path.join(arch_dir, f"{season['prefix']}_pc_SamMax{e}_uncompressed.ttarch2")
    _, wavs = read_nctt(path)
    new_len = {}
    with open(path, "rb") as f:
        for n, (o, _s) in wavs.items():
            if n[:-4].isdigit():
                f.seek(o)
                h = f.read(0x60)
                word = struct.unpack_from("<Q", h, 0x3C)[0]
                rate = {5: 22050, 7: 32000, 8: 44100, 9: 48000}.get((word >> 1) & 15, 44100)
                new_len[int(n[:-4])] = (word >> 34) / rate

    by_text = {}
    for i in en_len:
        if i in old_en:
            by_text.setdefault(norm(old_en[i][1]), []).append(i)

    pairs, counts, rows = {}, {"same id": 0, "text changed": 0, "exact": 0, "same text": 0, "close": 0, "none": 0}, []
    keys = list(by_text)
    for rid in sorted(new_len):
        speaker, text = new_text.get(rid, ("", ""))
        wanted = norm(text)
        if season["same_ids"] and rid in dub_ids:
            kind = "same id" if not old_en.get(rid) or norm(old_en[rid][1]) == wanted else "text changed"
            pairs[rid] = rid
            counts[kind] += 1
            rows.append((rid, rid, kind, speaker, text, old_dub.get(rid, ("", ""))[1]))
            continue
        cands = by_text.get(wanted, [])
        kind = "exact" if len(cands) == 1 else "same text"
        if not cands and wanted:
            best = max(keys, key=lambda k: SequenceMatcher(None, k, wanted).quick_ratio(), default=None)
            if best and SequenceMatcher(None, best, wanted).ratio() >= 0.92:
                cands, kind = by_text[best], "close"
        cands = [c for c in cands if c in dub_ids]
        if not cands:
            counts["none"] += 1
            rows.append((rid, "", "none", speaker, text, ""))
            continue
        same = [c for c in cands if old_en[c][0] == speaker] or cands
        old = min(same, key=lambda c: abs(en_len[c] - new_len[rid]))
        pairs[rid] = old
        counts[kind] += 1
        rows.append((rid, old, kind, speaker, text, old_dub.get(old, ("", ""))[1]))
    with open(os.path.join(work, f"ep{e}_lines.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["remaster_id", "old_id", "match", "speaker", "english", "old_text"])
        w.writerows(rows)
    say(f"Episode {e}: {len(new_len)} Sprachzeilen, {len(pairs)} zugeordnet.")
    print(f"DETAIL {e} {json.dumps(counts)}", flush=True)
    return pairs, voice_dub


# ---------------------------------------------------------------- voices (run in worker processes)


def convert_voice(job):
    rid, blob, deess = job
    try:
        v = parse_vox(blob)
    except (ValueError, struct.error) as err:
        return rid, None, str(err)
    speex = Speex(SPEEX_DLL, v["mode"])
    pcm = array.array("h")
    for p in v["packets"]:
        pcm.extend(speex.decode(p)[0])
    speex.close()
    if not pcm:
        return rid, None, "keine Audiodaten"
    samples = enhance.enhance(pcm, v["rate"], enhance.DEESS if deess else False)
    fsb, length = enhance.make_fsb5_mp3(str(rid), samples)
    return rid, fsb, length


# ---------------------------------------------------------------- timing


def is_active(d, block):
    return d[block + 13 + ACTIVE_FLAG] == 0x31


def active_seconds(d, hashes, seconds):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    return {r: seconds[r] for r, _, b, _ in line_resources(d, hashes, blocks) if r in seconds and is_active(d, b)}


def add_borrowed_lines(landb, seconds):
    """A language entry can name another line's recording, so its chores need that German length too."""
    known = {struct.pack("<Q", crc64(f"{r}.wav".encode())): r for r in seconds}
    for i in range(len(landb) - 44):
        if (landb[i + 16:i + 20] == b"\0\0\0\0" and landb[i + 20:i + 24] == b"\x0c\0\0\0"
                and landb[i:i + 4] == landb[i + 12:i + 16] and landb[i + 32:i + 36] == b"\x0c\0\0\0"):
            source = known.get(landb[i + 36:i + 44])
            if source is not None:
                seconds.setdefault(struct.unpack_from("<I", landb, i)[0], seconds[source])


def line_spans(d, hashes):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    return sorted((*struct.unpack_from("<ff", d, b), r) for r, _, b, _ in line_resources(d, hashes, blocks) if is_active(d, b))


def line_table(d, hashes, seconds):
    """Dialogs: the timeline slows down during a line that needs more room."""
    pairs = [(0.0, 0.0)]
    shift = 0.0
    for s, e, rid in line_spans(d, hashes):
        pairs.append((s, s + shift))
        shift += max(0.0, seconds[rid] - (e - s)) if rid in seconds else 0.0
        pairs.append((e, e + shift))
    return pairs_to_map(pairs)


def nested_uses(d, name_crc, blocks):
    """Each use of a nested chore: its blocks, and the fraction of it the time curve plays."""
    uses = []
    ordered = sorted(blocks)
    done = set()
    for m in re.finditer(re.escape(name_crc), d):
        later = [b for b in ordered if b > m.start()]
        if not later or later[0] in done:
            continue
        first = later[0]
        done.add(first)
        count = struct.unpack_from("<I", d, first - 4)[0]
        if not 1 <= count <= 64:
            continue
        rows = [struct.unpack_from("<ff", d, first + 13 * i) for i in range(count)]
        curve = None
        t = d.find(TIME_PROPERTY, m.start(), first)
        if t >= 0:
            c = t + 20
            size, keys = struct.unpack_from("<II", d, c)
            if keys >= 1 and size == 8 + 13 * keys:
                curve = (c, keys)
        uses.append((rows, curve))
    return uses


def curve_points(d, curve):
    c, keys = curve
    return [(struct.unpack_from("<f", d, c + 8 + 13 * i)[0], struct.unpack_from("<f", d, c + 17 + 13 * i)[0]) for i in range(keys)]


def nested_time(points, old_length, at):
    """When the outer chore reaches this moment of the nested one; None if it skips it or plays it at another speed."""
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        low, high = v0 * old_length, v1 * old_length
        if t1 > t0 and high > low and low - 0.001 <= at <= high + 0.001:
            if not 0.5 <= (high - low) / (t1 - t0) <= 2.0:
                return None
            return t0 + (at - low) / (high - low) * (t1 - t0)
    return None


def pause_events(d, hashes, seconds, kids):
    """Where a cutscene must stop, and for how long: its own lines plus everything its nested chores need."""
    events = []
    for s, e, rid in line_spans(d, hashes):
        extra = seconds[rid] - (e - s) if rid in seconds else 0.0
        if extra > 0:
            # Finished by the line's end: the next line may start within a millisecond of it.
            events.append((e - STEP, extra))
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    for name_crc, old_length, kid_events in kids:
        for rows, curve in nested_uses(d, name_crc, blocks):
            points = curve_points(d, curve) if curve else None
            for at, extra in kid_events:
                if points:
                    t = nested_time(points, old_length, at)
                    if t is None:
                        continue
                    last = points[-1][0]
                    spans = [(s, min(e, last)) for s, e in rows]
                else:
                    t = None
                    spans = rows
                for s, e in spans:
                    here = s + at if t is None else t
                    if s - 0.05 <= here <= e + 0.05:
                        # A pause on the very end must finish inside the block, or the end only moves part of the way.
                        events.append((min(here, e - 2.5 * STEP), extra))
    merged = []
    for at, extra in sorted(events):
        if merged and at - merged[-1][0] < 0.02:
            merged[-1] = (merged[-1][0], max(merged[-1][1], extra))
        else:
            merged.append((at, extra))
    return merged


def hold_table(events):
    """Cutscenes: everything runs at original speed and stands still at each pause."""
    pairs = [(0.0, 0.0)]
    shift = 0.0
    for at, extra in events:
        pairs.append((at, at + shift))
        shift += extra
        pairs.append((at + STEP, at + STEP + shift))
    return pairs_to_map(pairs)


def retime_nested_curves(d, out, kids):
    """A nested chore's time curve counts in fractions of its length, and that length has changed."""
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    for name_crc, old_length, kid_events in kids:
        table = hold_table(kid_events)
        new_length = old_length + sum(extra for _, extra in kid_events)
        for _rows, curve in nested_uses(d, name_crc, blocks):
            if curve:
                c, keys = curve
                for i in range(keys):
                    at = c + 17 + 13 * i
                    value = struct.unpack_from("<f", d, at)[0]
                    if 0.0 < value < 1.0:
                        struct.pack_into("<f", out, at, apply_map(table, value * old_length) / new_length)


def named_records(d, body, pattern, crc):
    """Records with a known name in file order, without the repeated second mention."""
    hits = []
    for m in pattern.finditer(d, body):
        n = crc[m.group()]
        if not hits or hits[-1][1] != n or m.start() - hits[-1][0] > 64:
            hits.append((m.start(), n))
    return hits


def fix_sounds(original, patched, table, pattern, crc, lines):
    """Sounds keep their length and curve shape: every block just moves to its new start."""
    body, _, length = chore_info(original)
    blocks, keys, _ = find_times(original, body, length)
    blocks = sorted(blocks)
    out = bytearray(patched)
    protected = []
    hits = named_records(original, body, pattern, crc)
    line_positions = sorted(x[1] for x in lines)
    for j, (pos, name) in enumerate(hits):
        limit = hits[j + 1][0] if j + 1 < len(hits) else len(original)
        # Other tracks can follow before the next named one, voice lines above all: they are not this track's.
        following = [p for p in line_positions if p > pos]
        if following:
            limit = min(limit, following[0])
        own = [b for b in blocks if pos < b < limit]
        if not own:
            continue
        count = struct.unpack_from("<I", original, own[0] - 4)[0]
        own = own[:count] if 1 <= count <= 64 else own[:1]
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
    return bytes(out), protected


_shared = {}


def init_worker(hashes, seconds, crc):
    _shared["hashes"] = hashes
    _shared["seconds"] = seconds
    _shared["crc"] = crc
    _shared["pattern"] = re.compile(b"|".join(re.escape(k) for k in crc))


def convert_chore(job):
    """Adapt one chore. `events` are given for cutscenes; otherwise a dialog table is computed here."""
    name, d, events, kids = job
    hashes, seconds = _shared["hashes"], _shared["seconds"]
    active = active_seconds(d, hashes, seconds)
    table = line_table(d, hashes, active) if events is None else hold_table(events)
    data, report, _length, lines = port(d, hashes, active, table)
    data, protected = fix_sounds(d, data, table, _shared["pattern"], _shared["crc"], lines)
    data = bytearray(data)
    retime_nested_curves(d, data, kids)
    data = bytes(data)
    note = None
    try:
        data = refine(d, data, table, lines, protected)[0]
    except ValueError as err:
        note = str(err)
    return name, data, sum(not r[5] for r in report), note


# ---------------------------------------------------------------- one episode


def build_episode(season, e, paths, game, work, pool_size, deess, language):
    arch_dir = os.path.join(game, "Archives")
    key = load_key(None, season["key"])
    prefix = season["prefix"]
    remaster = Ectt(os.path.join(arch_dir, f"{prefix}_pc_SamMax{e}_compressed.ttarch2"), key)
    pairs, voice_dub = match_lines(season, e, paths, remaster, arch_dir, work, language)

    jobs = [(rid, voice_dub.read(f"{old}.vox"), deess) for rid, old in pairs.items()]
    files, seconds = {}, {}
    with futures.ProcessPoolExecutor(pool_size) as pool:
        for i, (rid, fsb, length) in enumerate(pool.map(convert_voice, jobs, chunksize=16)):
            if fsb is None:
                say(f"  Zeile {rid} bleibt englisch: {length}")
                continue
            files[f"{rid}.wav"] = fsb
            seconds[rid] = length
            if i % 50 == 0:
                progress(f"Stimmen {e}", i, len(jobs))
    progress(f"Stimmen {e}", len(jobs), len(jobs))

    for rid, length in seconds.items():
        anm = f"{rid}.anm"
        if anm in remaster.files:
            try:
                files[anm] = patch(remaster.read(anm), length)[0]
            except (ValueError, struct.error) as err:
                say(f"  Lippen-Datei {anm} unverändert: {err}")

    hashes = {}
    for n in remaster.files:
        if n.endswith("_english.landb"):
            landb = remaster.read(n)
            hashes.update(line_hashes(landb))
            add_borrowed_lines(landb, seconds)
    names = set(remaster.files) | set(read_nctt(os.path.join(arch_dir, f"{prefix}_pc_SamMax{e}_uncompressed.ttarch2"))[1])
    common = Ectt(os.path.join(arch_dir, f"{prefix}_pc_Common_compressed.ttarch2"), key)
    names |= set(common.files) | set(read_nctt(os.path.join(arch_dir, f"{prefix}_pc_Common_uncompressed.ttarch2"))[1])
    crc = {struct.pack("<Q", crc64(n.lower().encode())): n.lower() for n in names if n.lower().endswith((".wav", ".chore", ".anm"))}

    wanted = re.compile(b"|".join(re.escape(h) for h, r in hashes.items() if r in seconds))
    chore_pattern = re.compile(b"|".join(re.escape(k) for k, v in crc.items() if v.endswith(".chore")))
    all_chores = {n.lower(): (n, remaster.read(n)) for n in remaster.files if n.endswith(".chore")}
    children = {}
    for low, (_n, d) in all_chores.items():
        body = chore_info(d)[0]
        kids = {crc[m.group()] for m in chore_pattern.finditer(d, body)} & set(all_chores)
        kids.discard(low)
        if kids:
            children[low] = kids
    with_lines = {low for low, (_n, d) in all_chores.items() if wanted.search(d)}

    # A chore needs work if it holds German lines or contains a chore that does, at any depth.
    needs_work = set(with_lines)
    grew = True
    while grew:
        grew = False
        for low, kids in children.items():
            if low not in needs_work and kids & needs_work:
                needs_work.add(low)
                grew = True
    say(f"Episode {e}: {len(needs_work)} Choreografien anzupassen.")

    # Cutscenes run in real time with pauses; a chore that contains another shares its timeline.
    nested = {x for low, kids in children.items() for x in kids}
    events = {}
    kid_data = {}

    def plan(low, path=()):
        if low in events or low in path:
            return
        kids = children.get(low, set()) & needs_work
        for kid in kids:
            plan(kid, path + (low,))
        d = all_chores[low][1]
        info = []
        for kid in sorted(kids):
            if events.get(kid):
                old_length = chore_info(all_chores[kid][1])[2]
                info.append((struct.pack("<Q", crc64(kid.encode())), old_length, events[kid]))
        kid_data[low] = info
        if low.startswith("cs_") or "_cs_" in low or low in nested or kids:
            events[low] = pause_events(d, hashes, active_seconds(d, hashes, seconds), info)

    for low in sorted(needs_work):
        plan(low)
    say(f"Episode {e}: {len(events)} Zwischensequenzen mit Pausen.")

    jobs = [(all_chores[low][0], all_chores[low][1], events.get(low), kid_data.get(low, [])) for low in sorted(needs_work)]
    chores = needs_work
    too_long = 0
    notes = []
    with futures.ProcessPoolExecutor(pool_size, initializer=init_worker, initargs=(hashes, seconds, crc)) as pool:
        for i, (n, data, bad, note) in enumerate(pool.map(convert_chore, jobs, chunksize=4)):
            files[n] = data
            too_long += bad
            if note:
                notes.append((n, note))
            if i % 10 == 0:
                progress(f"Choreografien {e}", i, len(jobs))
    progress(f"Choreografien {e}", len(jobs), len(jobs))
    say(f"Episode {e}: {len(files)} Dateien, {too_long} Zeilen knapp zu lang, {len(notes)} ohne Zwischenpunkte.")
    for n, note in notes[:5]:
        say(f"  {n}: {note}")
    return make_archive(files), dict(language=language, lines=sum(n.endswith(".wav") for n in files), chores=len(chores), cutscenes=len(events), too_long=too_long, no_curves=len(notes))


def descriptor(season, e, game, archive_name):
    """A second description of the episode's own set, listing the dubbed archive first."""
    bf = Blowfish7(load_key(None, season["key"]))
    with open(os.path.join(game, "Archives", f"_resdesc_50_SamMax{e}.lua"), "rb") as f:
        original = f.read()
    text = bf.decrypt(original[4:], "<II").decode("latin-1")
    text, priorities = re.subn(r"set\.descriptionPriority\s*=\s*\d+", "set.descriptionPriority = 100", text)
    text, lists = re.subn(
        r"(set\.gameDataArchives\s*=\s*\{\s*)",
        lambda m: f'{m.group(1)}_currentDirectory .. "{archive_name}",\r\n    ',
        text,
    )
    if priorities != 1 or lists != 1:
        raise SystemExit(f"Die Steuerdatei von Episode {e} hat einen unbekannten Aufbau.")
    return encrypt(bf, text.encode("latin-1"))


# ---------------------------------------------------------------- install


def game_running(season):
    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {season['exe']}"], capture_output=True, creationflags=NO_WINDOW).stdout
        return season["exe"].encode() in out
    except OSError:
        return False


def read_manifest(game):
    path = os.path.join(game, MANIFEST)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"files": [], "episodes": {}}


def delete_from_archives(game, names):
    removed = 0
    for n in names:
        if os.path.basename(n) != n:
            continue
        p = os.path.join(game, "Archives", n)
        if os.path.isfile(p):
            os.remove(p)
            removed += 1
    return removed


def remove_files(game):
    """Remove everything this tool installed."""
    names = list(LEGACY_FILES) + read_manifest(game).get("files", [])
    removed = delete_from_archives(game, names)
    delete_from_archives(game, [n + ".tmp" for n in names])
    path = os.path.join(game, MANIFEST)
    if os.path.isfile(path):
        os.remove(path)
    return removed


def write_atomic(path, data):
    temporary = path + ".tmp"
    with open(temporary, "wb") as f:
        f.write(data)
    os.replace(temporary, path)


def episode_files(season, e, language):
    dub = f"{language.capitalize()}Dub"
    return [f"{season['prefix']}_pc_SamMax{e}_{dub}_uncompressed.ttarch2", f"_resdesc_51_SamMax{e}{dub}.lua"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", required=True)
    ap.add_argument("--source")
    ap.add_argument("--episodes", nargs="*", help="Standard: alle Episoden der Season")
    ap.add_argument("--language", default="german", help="Sprache der alten Version: german oder french")
    ap.add_argument("--no-deess", action="store_true", help="S-Laute nicht abmildern (gilt nur für Deutsch, bei den anderen ist er aus)")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--work", help="Arbeitsordner (Standard: temporär, wird danach gelöscht)")
    ap.add_argument("--log", help="Meldungen in diese Datei schreiben (für das Fenster)")
    args = ap.parse_args()
    if args.log:
        sys.stdout = sys.stderr = open(args.log, "w", encoding="utf-8", buffering=1)

    season = SEASONS[season_of_game(args.game)]
    if game_running(season):
        raise SystemExit("Bitte zuerst das Spiel schließen.")
    if args.uninstall:
        say(f"Entfernt: {remove_files(args.game)} Dateien. Das Spiel ist wieder im Originalzustand.")
        return
    if not args.source:
        raise SystemExit("Bitte die alte Version angeben (--source).")
    if args.language not in season["languages"]:
        raise SystemExit(f"Für dieses Spiel gibt es diese Sprachen: {', '.join(season['languages'])}")
    deess = args.language == "german" and not args.no_deess

    episodes = args.episodes or list(season["episodes"])
    unknown = sorted(set(episodes) - set(season["episodes"]))
    if unknown:
        raise SystemExit(f"Diese Episoden gehören nicht zu diesem Spiel: {unknown}")
    temporary = None
    work = args.work
    if not work:
        temporary = tempfile.mkdtemp(prefix="SamMaxDE_")
        work = temporary
    os.makedirs(work, exist_ok=True)
    try:
        sources = collect_source(season, args.source, work, episodes, args.language)
        pool = max(1, (os.cpu_count() or 2) - 1)
        arch = os.path.join(args.game, "Archives")
        built, stats = {}, {}
        for e in episodes:
            say(f"=== Episode {e} ===")
            archive, stats[e] = build_episode(season, e, sources[e], args.game, work, pool, deess, args.language)
            built[e] = archive
        say("Schreibe die Archive ins Spiel ...")
        # Only touch the game once every episode has been built; other episodes stay installed.
        manifest = read_manifest(args.game)
        delete_from_archives(args.game, LEGACY_FILES)
        for e, archive in built.items():
            archive_name, desc_name = episode_files(season, e, args.language)
            # Finished files appear in one step, so stopping here never leaves a half-written archive.
            write_atomic(os.path.join(arch, archive_name), archive)
            write_atomic(os.path.join(arch, desc_name), descriptor(season, e, args.game, archive_name))
            # Both dubs would claim the same lines, so an episode holds one language at a time.
            replaced = {n for other in season["languages"] if other != args.language for n in episode_files(season, e, other)}
            delete_from_archives(args.game, replaced)
            manifest["files"] = sorted((set(manifest.get("files", [])) - replaced) | {archive_name, desc_name})
            manifest.setdefault("episodes", {})[e] = stats[e]
            write_atomic(os.path.join(args.game, MANIFEST), json.dumps(manifest, indent=1).encode("utf-8"))
        say("FERTIG. Installiert: " + ", ".join(f"Episode {e} ({s['lines']} Zeilen)" for e, s in stats.items()))
    finally:
        if temporary:
            shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
