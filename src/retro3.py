"""The original Season 3 episodes the remaster ships for its retro mode (Telltale 2010, archives of version 8).

Each episode loads every archive in its ep<number>/Pack folder, and of two files with the same name the one in the
archive that sorts first wins (the game's own patches are named 0_..., the data 1_...). So the dub is one more
archive, 0_0DubPolice.ttarch, holding the old dubbed voices, the dialogs with dubbed text and the chores fitted to the
longer lines. The game's own files stay untouched; taking the dub away means deleting that one archive.
"""
import glob
import os
import struct

import retro
from ectt import Blowfish7
from old_archive import OldArchive

PACK = "0_0DubPolice.ttarch"


def pack_dir(game, e):
    return os.path.join(game, f"ep{e}", "Pack")


def available(game, episodes):
    """The episodes whose retro version is installed."""
    return [e for e in episodes if os.path.isfile(os.path.join(pack_dir(game, e), f"1_SamMax{e}_pc_data.ttarch"))]


def is_dubbed(game, e):
    return os.path.isfile(os.path.join(pack_dir(game, e), PACK))


def restore(game, e):
    """Take the dub away again. Returns True if there was one."""
    path = os.path.join(pack_dir(game, e), PACK)
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def plain(archive, name, key):
    """A file in plain form: some (all of episode 302) are stored like the Season 2 retro files, in place of their
    first four bytes ERTM."""
    data = archive.read(name)
    if data[:4] == retro.WIDE:
        return b"ERTM" + retro.reveal(data, Blowfish7(key))
    return data


def game_files(game, e, key):
    """{lower-case name: archive} of the episode as the game sees it, without the dub."""
    owner = {}
    paths = sorted(glob.glob(os.path.join(pack_dir(game, e), "*.ttarch")), key=lambda p: os.path.basename(p).lower())
    for path in paths:
        low = os.path.basename(path).lower()
        if low == PACK.lower() or "_tx." in low or "_ms." in low:
            continue
        archive = OldArchive(path, key)
        for name in archive.files:
            owner.setdefault(name, archive)
    return owner


# ---------------------------------------------------------------- dialogs

def _string(d, p):
    size, length = struct.unpack_from("<II", d, p)
    if size != length + 8:
        raise ValueError
    return d[p + 8:p + 8 + length], p + size


def _lines_at(d, p):
    """The line table of a dialog with its size at p: [size][count], then per line its id twice, a reference, the lip
    and voice names, a block [size][n] with n times [speaker][text][8 bytes] (n is 0, 1 or a few variants, as in
    the menus) and 8 more bytes. Returns [(id, block offset, text offset, text)], one per text, or None."""
    size, count = struct.unpack_from("<II", d, p)
    if not (0 < count < 100000 and 8 < size <= len(d) - p):
        return None
    q = p + 8
    out = []
    try:
        for _ in range(count):
            key, rid = struct.unpack_from("<II", d, q)
            if key != rid:
                return None
            _lips, r = _string(d, q + 12)
            _voice, b = _string(d, r)
            block, texts = struct.unpack_from("<II", d, b)
            if not 0 <= texts <= 16:
                return None
            at = b + 8
            for _ in range(texts):
                _speaker, t = _string(d, at)
                text, end = _string(d, t)
                out.append((rid, b, t, text))
                at = end + 8
            if at != b + block:
                return None
            q = b + block + 8
    except (ValueError, struct.error):
        return None
    return out if q == p + size else None


def dialog_lines(d):
    """[(table offset, lines)] of a dialog."""
    found = []
    for p in range(0, len(d) - 16):
        if d[p + 8:p + 12] == d[p + 12:p + 16] and struct.unpack_from("<I", d, p + 4)[0]:
            lines = _lines_at(d, p)
            if lines is not None:
                found.append((p, lines))
    return found


# The old German release built its menus differently: many menu texts the retro menus use stayed English there,
# while the German words sit under other ids. Those are found by their English text (see english_key); what is
# left are these few.
MENU_GERMAN = {
    "settings": "Einstellungen", "resume game": "Spiel fortsetzen", "gameplay settings": "Spiel-Einstellungen",
    "hint frequency": "Hinweis-Level", "popup text": "Pop-Up-Text", "subtitles": "Untertitel",
    "ready to start a new game?": "Willst du ein neues Spiel starten?", "auto save": "Automatisch gespeichert",
    "new save": "Neuer Spielstand", "<< save": "<< Speichern", "okay": "OK", "yeah!": "Ja!",
    "realtime shadows": "Echtzeit-Schatten", "flip max mode y-axis:": "Max-Modus: Y-Achse umkehren:",
    "game paused press space to continue": "Spiel pausiert\nLeertaste drücken, um fortzufahren",
    "(standard)": "(Standard)", "(widescreen)": "(Breitbild)",
}


def english_key(text):
    return " ".join(text.replace("&", "and").lower().split())


def dubbed_dialog(d, texts, by_english=None):
    """The dialog with the dubbed texts ({id: text}). Returns (data, lines changed); (None, 0) if it has no lines.

    A line whose dubbed text is missing or still English takes the dubbed text of the same English text elsewhere
    (`by_english`, keyed by english_key). The line table and the block 20 bytes before it hold their sizes; both grow
    with the text."""
    by_english = by_english or {}
    tables = dialog_lines(d)
    if len(tables) != 1:
        return None, 0
    p, lines = tables[0]
    outer = p - 20
    if not (struct.unpack_from("<II", d, outer + 4)[0] == 8 and struct.unpack_from("<I", d, outer + 12)[0] == 8
            and outer + struct.unpack_from("<I", d, outer)[0] >= p + struct.unpack_from("<I", d, p)[0]):
        raise ValueError("Dialog unerwartet aufgebaut")
    out = bytearray(d)
    changed = 0
    for rid, b, t, text in reversed(lines):
        english = text.decode("cp1252", "replace")
        dubbed = texts.get(rid)
        if dubbed is None or dubbed == english:
            dubbed = by_english.get(english_key(english), dubbed)
        if dubbed is None or dubbed == english:
            continue
        if dubbed.isupper() and not english.isupper():
            # The old menus wrote some words in capitals where the retro menu does not: "NEUES SPIEL" -> "Neues Spiel".
            dubbed = " ".join(w[:1] + w[1:].lower() for w in dubbed.split(" "))
            dubbed = "/".join(w[:1].upper() + w[1:] for w in dubbed.split("/"))
        new = dubbed.encode("cp1252", "replace")
        grow = len(new) - len(text)
        out[t:t + 8 + len(text)] = struct.pack("<II", len(new) + 8, len(new)) + new
        for field in (b, p, outer):
            struct.pack_into("<I", out, field, struct.unpack_from("<I", out, field)[0] + grow)
        changed += 1
    again = dialog_lines(bytes(out))
    if len(again) != 1 or len(again[0][1]) != len(lines):
        raise ValueError("Dialog lässt sich nach dem Ersetzen nicht mehr lesen")
    return bytes(out), changed


# ---------------------------------------------------------------- the archive

def build_numbers(path):
    """The two build numbers in an archive's head (after the block list), to give the dub the same."""
    with open(path, "rb") as f:
        blocks = struct.unpack_from("<i", f.read(20), 16)[0]
        f.seek(20 + 4 * blocks + 4)
        return struct.unpack("<ii", f.read(8))


def write_archive(path, files, numbers=(0, 0)):
    """An uncompressed, unencrypted archive of version 8, like the game's own 0_8patch.ttarch in episode 305.

    `files` is [(name, data)]."""
    folder = b"dubpolice\\"
    table = struct.pack("<II", 1, len(folder)) + folder + struct.pack("<I", len(files))
    offset = 0
    for name, data in files:
        raw = name.encode("latin-1")
        table += struct.pack("<I", len(raw)) + raw + struct.pack("<IIi", 0, offset, len(data))
        offset += len(data)
    head = struct.pack("<iiiii", 8, 0, 2, 1, 0) + struct.pack("<iii", offset, *numbers) + struct.pack("<iii", 0, 0, 64)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(head + b"\0" + struct.pack("<i", len(table)) + table)
        for _name, data in files:
            f.write(data)
    os.replace(tmp, path)


def dub(game, e, key, texts, voices, chores, by_english=None):
    """Write the dub archive of one episode.

    `texts` {line id: dubbed text}, `voices` {file name: data} (the .vox recordings), `chores` {name: new data}.
    Returns (dialogs changed, text lines, voices)."""
    owner = game_files(game, e, key)
    files = []
    lines = 0
    for name in sorted(n for n in owner if n.endswith(".dlog")):
        new, changed = dubbed_dialog(plain(owner[name], name, key), texts, by_english)
        if new is not None and changed:
            files.append((name, new))
            lines += changed
    dialogs = len(files)
    files += sorted(chores.items())
    files += sorted(voices.items())
    for archive in set(owner.values()):
        archive._f.close()
    path = os.path.join(pack_dir(game, e), PACK)
    write_archive(path, files, build_numbers(os.path.join(pack_dir(game, e), f"1_SamMax{e}_pc_data.ttarch")))
    check = OldArchive(path, key)
    if len(check.files) != len(files) or any(check.read(n) != d for n, d in (files[0], files[-1])):
        os.remove(path)
        raise ValueError("Das neue Archiv lässt sich nicht richtig lesen")
    check._f.close()
    return dialogs, lines, len(voices)
