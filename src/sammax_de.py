"""Bring the German voices of the 2009 Sam & Max Season 2 into Beyond Time and Space Remastered.

The tool reads your own copy of the old German release and builds one extra archive per episode.
No original game file is changed. Usage:

    python sammax_de.py --game "<remaster folder>" --source "<old German game or disc>" [--episodes 201 202]
    python sammax_de.py --game "<remaster folder>" --uninstall
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
from curves import refine  # noqa: E402
from ectt import Blowfish7, Ectt  # noqa: E402
from ima import FRAME_SAMPLES, make_fsb5_ima  # noqa: E402
from nctt import read_nctt  # noqa: E402
from old_archive import OldArchive  # noqa: E402
from port_schedule import apply_map, pairs_to_map, port  # noqa: E402
from ttarch4 import load_key  # noqa: E402
from variants import encrypt  # noqa: E402
from vox2wav import Speex, parse_vox  # noqa: E402

EPISODES = ("201", "202", "203", "204", "205")
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


def check_game(game):
    if not os.path.isfile(os.path.join(game, "SamMax200.exe")) or not os.path.isdir(os.path.join(game, "Archives")):
        raise SystemExit(f"Das ist kein Remaster-Ordner (SamMax200.exe oder Archives fehlt): {game}")


def find_7zip():
    found = shutil.which("7z") or shutil.which("7za")
    bundled = os.path.join(BIN, "7z.exe")
    for path in (bundled, found, r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe"):
        if path and os.path.isfile(path):
            return path
    return None


def collect_source(source, work, episodes):
    """Return {episode: {role: path}} from an installed game, a folder, or a disc with installers."""
    wanted = {}
    for e in episodes:
        wanted[e] = {
            "data": f"1_sammax{e}_pc_data.ttarch",
            "voice_en": f"2_sammax{e}_pc_voice.ttarch",
            "voice_de": f"2_sammax{e}_pc_voice_german.ttarch",
        }
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
                        if role == "voice_en" and parent != "english":
                            continue
                        found[e][role] = os.path.join(root, f)

    scan(source)
    missing = [e for e in episodes if len(found[e]) < 3]
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
    still = {e: sorted(set(wanted[e]) - set(found[e])) for e in episodes if len(found[e]) < 3}
    if still:
        raise SystemExit(f"Die deutsche Version wurde nicht vollständig gefunden: {still}")
    return found


# ---------------------------------------------------------------- matching lines


def parse_old_lang(d):
    """2009 language database: {id: (speaker, text)}."""
    rows = {}
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
        out[int(n[:-4])] = struct.unpack_from("<f", archive.read(n)[:40], 21)[0]
    return out


def match_lines(e, paths, remaster, arch_dir, work):
    """Pair each remaster voice with its 2009 voice through the English text; return {remaster id: old id}."""
    key = load_key(None, f"SM{e}")
    data = OldArchive(paths["data"], key)
    voice_en = OldArchive(paths["voice_en"], key)
    voice_de = OldArchive(paths["voice_de"], key)
    old_en = parse_old_lang(data.read("english.langdb"))
    old_de = parse_old_lang(data.read("german.langdb"))
    numeric = lambda a: [n for n in a.files if n.endswith(".vox") and n[:-4].isdigit()]
    en_len = voice_lengths(voice_en, numeric(voice_en))
    de_ids = {int(n[:-4]) for n in numeric(voice_de)}

    new_text = {}
    for n in remaster.files:
        if n.endswith("_english.landb"):
            new_text.update(parse_new_lang(remaster.read(n)))
    path = os.path.join(arch_dir, f"SM2_pc_SamMax{e}_uncompressed.ttarch2")
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

    pairs, counts, rows = {}, {"exact": 0, "same text": 0, "close": 0, "none": 0}, []
    keys = list(by_text)
    for rid in sorted(new_len):
        speaker, text = new_text.get(rid, ("", ""))
        wanted = norm(text)
        cands = by_text.get(wanted, [])
        kind = "exact" if len(cands) == 1 else "same text"
        if not cands and wanted:
            best = max(keys, key=lambda k: SequenceMatcher(None, k, wanted).quick_ratio(), default=None)
            if best and SequenceMatcher(None, best, wanted).ratio() >= 0.92:
                cands, kind = by_text[best], "close"
        cands = [c for c in cands if c in de_ids]
        if not cands:
            counts["none"] += 1
            rows.append((rid, "", "none", speaker, text, ""))
            continue
        same = [c for c in cands if old_en[c][0] == speaker] or cands
        old = min(same, key=lambda c: abs(en_len[c] - new_len[rid]))
        pairs[rid] = old
        counts[kind] += 1
        rows.append((rid, old, kind, speaker, text, old_de.get(old, ("", ""))[1]))
    with open(os.path.join(work, f"ep{e}_lines.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["remaster_id", "old_id", "match", "speaker", "english", "old_german"])
        w.writerows(rows)
    say(f"Episode {e}: {len(new_len)} Sprachzeilen, {len(pairs)} zugeordnet.")
    return pairs, voice_de


# ---------------------------------------------------------------- voices (run in worker processes)


def convert_voice(job):
    rid, blob = job
    try:
        v = parse_vox(blob)
    except (ValueError, struct.error) as err:
        return rid, None, str(err)
    speex = Speex(SPEEX_DLL, v["mode"])
    pcm = array.array("h")
    for p in v["packets"]:
        pcm.extend(speex.decode(p)[0])
    speex.close()
    pcm.extend(array.array("h", bytes(2 * (-len(pcm) % FRAME_SAMPLES))))
    return rid, make_fsb5_ima(str(rid), pcm, v["rate"]), len(pcm) / v["rate"]


# ---------------------------------------------------------------- timing


def is_active(d, block):
    return d[block + 13 + ACTIVE_FLAG] == 0x31


def active_seconds(d, hashes, seconds):
    body, _, length = chore_info(d)
    blocks, _, _ = find_times(d, body, length)
    return {r: seconds[r] for r, _, b, _ in line_resources(d, hashes, blocks) if r in seconds and is_active(d, b)}


def line_table(d, hashes, seconds, base=None, start_shift=0.0, hold=False):
    """Make room for each active line: cutscenes pause at a line's end, dialogs slow down during the line."""
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


def named_records(d, body, pattern, crc):
    """Records with a known name in file order, without the repeated second mention."""
    hits = []
    for m in pattern.finditer(d, body):
        n = crc[m.group()]
        if not hits or hits[-1][1] != n or m.start() - hits[-1][0] > 64:
            hits.append((m.start(), n))
    return hits


def fix_sounds(original, patched, table, pattern, crc):
    """Sounds keep their length and curve shape: every block just moves to its new start."""
    body, _, length = chore_info(original)
    blocks, keys, _ = find_times(original, body, length)
    blocks = sorted(blocks)
    out = bytearray(patched)
    protected = []
    hits = named_records(original, body, pattern, crc)
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
    return bytes(out), protected


_shared = {}


def init_worker(hashes, seconds, crc):
    _shared["hashes"] = hashes
    _shared["seconds"] = seconds
    _shared["crc"] = crc
    _shared["pattern"] = re.compile(b"|".join(re.escape(k) for k in crc))


def convert_chore(job):
    """Adapt one chore. `table` is given for cutscenes; otherwise a dialog table is computed here."""
    name, d, table = job
    hashes, seconds = _shared["hashes"], _shared["seconds"]
    active = active_seconds(d, hashes, seconds)
    if table is None:
        table = line_table(d, hashes, active)
    data, report, _length, lines = port(d, hashes, active, table)
    data, protected = fix_sounds(d, data, table, _shared["pattern"], _shared["crc"])
    note = None
    try:
        data = refine(d, data, table, lines, protected)[0]
    except ValueError as err:
        note = str(err)
    return name, data, sum(not r[5] for r in report), note


# ---------------------------------------------------------------- one episode


def build_episode(e, paths, game, work, pool_size):
    arch_dir = os.path.join(game, "Archives")
    key = load_key(None, "SMBTaS")
    remaster = Ectt(os.path.join(arch_dir, f"SM2_pc_SamMax{e}_compressed.ttarch2"), key)
    pairs, voice_de = match_lines(e, paths, remaster, arch_dir, work)

    jobs = [(rid, voice_de.read(f"{old}.vox")) for rid, old in pairs.items()]
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
            hashes.update(line_hashes(remaster.read(n)))
    names = set(remaster.files) | set(read_nctt(os.path.join(arch_dir, f"SM2_pc_SamMax{e}_uncompressed.ttarch2"))[1])
    common = Ectt(os.path.join(arch_dir, "SM2_pc_Common_compressed.ttarch2"), key)
    names |= set(common.files) | set(read_nctt(os.path.join(arch_dir, "SM2_pc_Common_uncompressed.ttarch2"))[1])
    crc = {struct.pack("<Q", crc64(n.lower().encode())): n.lower() for n in names if n.lower().endswith((".wav", ".chore", ".anm"))}

    wanted = re.compile(b"|".join(re.escape(h) for h, r in hashes.items() if r in seconds))
    chore_pattern = re.compile(b"|".join(re.escape(k) for k, v in crc.items() if v.endswith(".chore")))
    by_lower = {n.lower(): n for n in remaster.files}
    chores = {}
    for n in remaster.files:
        if n.endswith(".chore"):
            d = remaster.read(n)
            if wanted.search(d):
                chores[n.lower()] = (n, d)
    say(f"Episode {e}: {len(chores)} Choreografien mit deutschen Zeilen.")

    # Cutscenes run in real time with pauses; a chore that contains one shares its timeline.
    tables = {}
    nested_in = {}
    for low, (n, d) in chores.items():
        body = chore_info(d)[0]
        inner = [(m.start(), crc[m.group()]) for m in chore_pattern.finditer(d, body)]
        inner = [(p, x) for p, x in inner if x in chores and x != low]
        if inner:
            nested_in[low] = inner
    inner_names = {x for v in nested_in.values() for _, x in v}
    for low in inner_names | {x for x in chores if x.startswith("cs_") or "_cs_" in x}:
        if low not in nested_in:
            n, d = chores[low]
            tables[low] = line_table(d, hashes, active_seconds(d, hashes, seconds), hold=True)
    for low, inner in nested_in.items():
        n, d = chores[low]
        body, _, length = chore_info(d)
        blocks, _, _ = find_times(d, body, length)
        pairs_base, shift, used = [(0.0, 0.0)], 0.0, set()
        for pos, name in sorted(inner):
            if name in used or name not in tables:
                continue
            used.add(name)
            later = [b for b in blocks if b > pos]
            if not later:
                continue
            start, end = struct.unpack_from("<ff", d, min(later))
            schedule = tables[name]
            pairs_base.append((start, start + shift))
            pairs_base += [(start + x, start + y + shift) for x, y in zip(*schedule) if start < start + x <= end]
            new_end = start + apply_map(schedule, end - start) + shift
            if pairs_base[-1][0] < end:
                pairs_base.append((end, new_end))
            shift = new_end - end
        if used:
            tables[low] = line_table(d, hashes, active_seconds(d, hashes, seconds), pairs_base, shift, hold=True)
    say(f"Episode {e}: {len(tables)} Zwischensequenzen mit Pausen.")

    jobs = [(n, d, tables.get(low)) for low, (n, d) in chores.items()]
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
    return make_archive(files), dict(lines=len(seconds), chores=len(chores), cutscenes=len(tables), too_long=too_long, no_curves=len(notes))


def descriptor(e, archive_name):
    """A second description of the episode's own set, listing the German archive first."""
    name = f"SamMax{e}"
    text = f"""local set = {{}}
set.name = "{name}"
set.setName = "{name}"
set.descriptionFilenameOverride = ""
set.logicalName = "<{name}>"
set.logicalDestination = "<>"
set.priority = {int(e) - 100}
set.localDir = _currentDirectory
set.enableMode = "bootable"
set.version = "trunk"
set.descriptionPriority = 100
set.gameDataName = "{name} Game Data"
set.gameDataPriority = 0
set.gameDataEnableMode = "constant"
set.localDirIncludeBase = true
set.localDirRecurse = false
set.localDirIncludeOnly = nil
set.localDirExclude =
{{
    "Packaging/",
    "_dev/"
}}
set.gameDataArchives =
{{
    _currentDirectory .. "{archive_name}",
    _currentDirectory .. "SM2_pc_{name}_compressed.ttarch2",
    _currentDirectory .. "SM2_pc_{name}_uncompressed.ttarch2"
}}
RegisterSetDescription(set)
"""
    return encrypt(Blowfish7(load_key(None, "SMBTaS")), text.replace("\n", "\r\n").encode("ascii"))


# ---------------------------------------------------------------- install


def game_running():
    try:
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq SamMax200.exe"], capture_output=True, creationflags=NO_WINDOW).stdout
        return b"SamMax200.exe" in out
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


def episode_files(e):
    return [f"SM2_pc_SamMax{e}_GermanDub_uncompressed.ttarch2", f"_resdesc_51_SamMax{e}GermanDub.lua"]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--game", required=True)
    ap.add_argument("--source")
    ap.add_argument("--episodes", nargs="*", default=list(EPISODES))
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--work", help="Arbeitsordner (Standard: temporär, wird danach gelöscht)")
    ap.add_argument("--log", help="Meldungen in diese Datei schreiben (für das Fenster)")
    args = ap.parse_args()
    if args.log:
        sys.stdout = sys.stderr = open(args.log, "w", encoding="utf-8", buffering=1)

    check_game(args.game)
    if game_running():
        raise SystemExit("Bitte zuerst das Spiel schließen.")
    if args.uninstall:
        say(f"Entfernt: {remove_files(args.game)} Dateien. Das Spiel ist wieder im Originalzustand.")
        return
    if not args.source:
        raise SystemExit("Bitte die alte deutsche Version angeben (--source).")

    unknown = sorted(set(args.episodes) - set(EPISODES))
    if unknown:
        raise SystemExit(f"Unbekannte Episoden: {unknown}")
    temporary = None
    work = args.work
    if not work:
        temporary = tempfile.mkdtemp(prefix="SamMaxDE_")
        work = temporary
    os.makedirs(work, exist_ok=True)
    try:
        sources = collect_source(args.source, work, args.episodes)
        pool = max(1, (os.cpu_count() or 2) - 1)
        arch = os.path.join(args.game, "Archives")
        built, stats = {}, {}
        for e in args.episodes:
            say(f"=== Episode {e} ===")
            archive, stats[e] = build_episode(e, sources[e], args.game, work, pool)
            built[e] = archive
        say("Schreibe die Archive ins Spiel ...")
        # Only touch the game once every episode has been built; other episodes stay installed.
        manifest = read_manifest(args.game)
        delete_from_archives(args.game, LEGACY_FILES)
        for e, archive in built.items():
            archive_name, desc_name = episode_files(e)
            # Finished files appear in one step, so stopping here never leaves a half-written archive.
            write_atomic(os.path.join(arch, archive_name), archive)
            write_atomic(os.path.join(arch, desc_name), descriptor(e, archive_name))
            manifest["files"] = sorted(set(manifest.get("files", [])) | {archive_name, desc_name})
            manifest.setdefault("episodes", {})[e] = stats[e]
            write_atomic(os.path.join(args.game, MANIFEST), json.dumps(manifest, indent=1).encode("utf-8"))
        say("FERTIG. Installiert: " + ", ".join(f"Episode {e} ({s['lines']} Zeilen)" for e, s in stats.items()))
    finally:
        if temporary:
            shutil.rmtree(temporary, ignore_errors=True)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
