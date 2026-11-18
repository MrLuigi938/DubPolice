"""Dub the retro episodes: the original Season 2 that the remaster installs in ep<number> folders, in English only.

The retro release keeps each recording as a single file next to one big archive, and its texts in english.langdb inside
that archive. The old dubbed version (2008) has the same recordings and texts in other wrappers:

- a retro voice is a fixed head followed by the old voice file without its 20-byte head and its last byte(s);
- a retro language database is its own head followed by the same body as the old one.

Both are measured on the English files first, so nothing is written unless the old English files turn into the retro
ones byte for byte. The English files are kept in DubPolice_Retro next to the episodes and come back on removal.
"""
import json
import os
import shutil
import struct
import unicodedata

from old_archive import FlatArchive, OldArchive
from ttarch4 import Blowfish, load_key

BACKUP = "DubPolice_Retro"
OLD_HEAD = 20  # ERTM voice files of 2008


def retro_folder(game, e):
    return os.path.join(game, f"ep{e}", "Pack", f"SamMax{e}_english")


def retro_archive(game, e):
    return os.path.join(retro_folder(game, e), f"SamMax{e}_english.ttarch")


def available(game, episodes):
    return [e for e in episodes if os.path.isfile(retro_archive(game, e))]


def body_start(d):
    """A language database's body starts with its own size: the 32-bit number there equals what follows."""
    for at in range(0, min(len(d) - 4, 512)):
        if struct.unpack_from("<I", d, at)[0] == len(d) - at:
            return at
    raise ValueError("Sprachdatenbank ohne erkennbaren Anfang")


def rows(body):
    """[(the 8 id bytes, [four strings as bytes], the 7 bytes after)] of a database body: <size><count>, then per line
    two equal ids, four <block><length> strings and 7 more bytes."""
    count = struct.unpack_from("<I", body, 4)[0]
    out = []
    p = 8
    for _ in range(count):
        ids = body[p:p + 8]
        p += 8
        fields = []
        for _ in range(4):
            block, ln = struct.unpack_from("<II", body, p)
            if block != ln + 8:
                raise ValueError("Unerwarteter Aufbau der Sprachdatenbank")
            fields.append(body[p + 8:p + 8 + ln])
            p += block
        out.append((ids, fields, body[p:p + 7]))
        p += 7
    if p != len(body):
        raise ValueError("Sprachdatenbank nicht vollständig gelesen")
    return out


# The retro engine leaves out every letter beyond plain ASCII, whatever the encoding (its fonts hold them, but even
# letters moved to free ASCII places stayed blank). So umlauts are written out and other accents dropped.
SPELLED = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss",
           "…": "...", "„": '"', "“": '"', "”": '"', "–": "-", "—": "-", "’": "'", "‘": "'", " ": " ",
           "œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE", "°": "o"}
# Menu buttons have fixed places; these German words ran into each other.
MENU = {"german": {27547520: "ENDE", 27547776: "SPIELSTAND"}}


def ascii_text(text):
    out = []
    for i, c in enumerate(text):
        spelled = SPELLED.get(c, c)
        # In capitals, the second letter is a capital too: SPIELSTAENDE, not SPIELSTAeNDE.
        if len(spelled) == 2 and c.isupper() and any(x.isupper() for x in text[max(0, i - 1):i + 2] if x != c):
            spelled = spelled.upper()
        out.append(spelled)
    rest = unicodedata.normalize("NFKD", "".join(out))
    return "".join(c for c in rest if ord(c) < 128 and not unicodedata.combining(c))


def retro_body(body, language):
    """The dubbed database body for the retro engine, in plain ASCII."""
    menu = MENU.get(language, {})
    out = bytearray(body[4:8])
    for ids, fields, tail in rows(body):
        out += ids
        for k, raw in enumerate(fields):
            text = raw.decode("cp1252", "replace")
            if k == 1 and struct.unpack_from("<I", ids)[0] in menu:
                text = menu[struct.unpack_from("<I", ids)[0]]
            data = ascii_text(text).encode("ascii")
            out += struct.pack("<II", len(data) + 8, len(data)) + data
        out += tail
    return struct.pack("<I", len(out) + 4) + bytes(out)


def voice_layout(folder, english):
    """(retro head, bytes the retro files drop at the end), measured on recordings both releases have."""
    names = {n.lower(): n for n in english.files if n.lower().endswith(".vox")}
    found = set()
    checked = 0
    for n in sorted(os.listdir(folder)):
        if n.lower() not in names:
            continue
        with open(os.path.join(folder, n), "rb") as f:
            retro = f.read()
        old = english.read(names[n.lower()])
        body = old[OLD_HEAD:]
        for head in range(8, 96):
            kept = len(retro) - head
            if 0 < kept <= len(body) and retro[head:] == body[:kept]:
                found.add((retro[:head], len(body) - kept))
                break
        else:
            raise ValueError(f"Retro-Stimme {n} passt nicht zur alten englischen")
        checked += 1
        if checked == 24:
            break
    if len(found) != 1 or not checked:
        raise ValueError("Die Retro-Stimmen sind nicht einheitlich aufgebaut")
    return found.pop()


# Data files start with 4 bytes, then blocks: (block size, every n-th block encrypted, every n-th of the others left
# as it is); all other blocks are inverted. Episode 205 marks its files with WIDE and uses larger blocks.
NORMAL = (0x80, 0x20, 0x50)
WIDE = bytes.fromhex("aadeaf64")
MARK = bytes.fromhex("fbdeaf64")


def _blocks(body, bf, mark, encrypt):
    size, crypt, clean = (0x100, 8, 24) if mark == WIDE else NORMAL
    out = bytearray(body)
    for i in range(len(body) // size):
        at = i * size
        chunk = bytes(body[at:at + size])
        if i % crypt == 0:
            out[at:at + size] = (bf.encrypt if encrypt else bf.decrypt)(chunk, "<II")
        elif i % clean != 0:
            out[at:at + size] = bytes(b ^ 0xFF for b in chunk)
    return bytes(out)


def obscure(body, bf, mark=MARK):
    """The inverse of reveal."""
    return _blocks(body, bf, mark, True)


def reveal(stored, bf):
    """A stored data file without its first 4 bytes, in plain form."""
    return _blocks(stored[4:], bf, stored[:4], False)


def read_plain(archive, name):
    """A data file of the retro archive (chore, language database) in plain form."""
    off, size = archive.files[name.lower()]
    archive._f.seek(archive.base + off)
    stored = archive._f.read(size)
    return reveal(stored, archive.bf)


def read_table(path, bf):
    with open(path, "rb") as f:
        head = f.read(16)
        size = struct.unpack_from("<i", head, 12)[0]
        raw = f.read(size)
    return head, raw, bf.decrypt(raw, "<II")


def file_entries(table):
    """{name: offset in the table of its (offset, size)} of a decrypted version 2 table."""
    p = 4
    for _ in range(struct.unpack_from("<i", table, 0)[0]):
        p += 4 + struct.unpack_from("<i", table, p)[0]
    count = struct.unpack_from("<i", table, p)[0]
    p += 4
    out = {}
    for _ in range(count):
        ln = struct.unpack_from("<i", table, p)[0]
        name = table[p + 4:p + 4 + ln].decode("latin-1").lower()
        p += 4 + ln
        out[name] = p + 4
        p += 12
    return out


def backup_dir(game, e):
    return os.path.join(game, BACKUP, f"ep{e}")


def is_dubbed(game, e):
    return os.path.isfile(os.path.join(backup_dir(game, e), "state.json"))


FULLSCREEN = b"\x0f\x00\x00\x00Fullscreen Size"


def prefs_path(game, e):
    return os.path.join(game, f"ep{e}", "prefs.prop")


def set_fullscreen(game, e, bf, size, only_from=None):
    """Change the stored full screen size in the episode's settings. Returns the old size, or None if unchanged."""
    path = prefs_path(game, e)
    if not size or not os.path.isfile(path):
        return None
    with open(path, "rb") as f:
        stored = f.read()
    plain = reveal(stored, bf)
    at = plain.find(FULLSCREEN)
    if at < 0 or stored[:4] + obscure(plain, bf, stored[:4]) != stored:
        return None
    at += len(FULLSCREEN)
    old = [round(v) for v in struct.unpack_from("<ff", plain, at)]
    if only_from is not None and old != list(only_from) or old == list(size):
        return None
    plain = bytearray(plain)
    struct.pack_into("<ff", plain, at, *size)
    with open(path, "wb") as f:
        f.write(stored[:4] + obscure(bytes(plain), bf, stored[:4]))
    return old


def restore(game, e):
    """Put the English retro episode back. Returns True if there was something to restore."""
    folder, archive, keep = retro_folder(game, e), retro_archive(game, e), backup_dir(game, e)
    state_path = os.path.join(keep, "state.json")
    if not os.path.isfile(state_path):
        return False
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    with open(os.path.join(keep, "table.bin"), "rb") as f:
        table = f.read()
    with open(archive, "r+b") as f:
        f.seek(16)
        f.write(table)
        f.truncate(state["size"])
    voices = os.path.join(keep, "voices")
    for n in os.listdir(voices):
        shutil.copyfile(os.path.join(voices, n), os.path.join(folder, n))
    # A test build set a 16:9 screen size, which only stretched the 4:3 picture: put the old one back unless the player
    # chose another one in the game meanwhile.
    if state.get("fullscreen"):
        set_fullscreen(game, e, Blowfish(load_key(None, f"SM{e}")), state["fullscreen"], state.get("fullscreen_set"))
    shutil.rmtree(keep)
    parent = os.path.join(game, BACKUP)
    if os.path.isdir(parent) and not os.listdir(parent):
        os.rmdir(parent)
    return True


def dub(game, e, paths, language, files=None):
    """Give one retro episode the old dubbed voices and texts, and `files` ({name: plain data}, retimed chores) in
    place of its own. Returns (voices replaced, text lines)."""
    folder, archive = retro_folder(game, e), retro_archive(game, e)
    key = load_key(None, f"SM{e}")
    bf = Blowfish(key)
    restore(game, e)

    data = OldArchive(paths["data"], key)
    english = OldArchive(paths["voice_en"], key)
    dubbed = OldArchive(paths["voice_dub"], key)
    retro = FlatArchive(archive, key)

    # Texts: the retro head, then the dubbed body. The English one must come out unchanged the same way.
    retro_text = read_plain(retro, "english.langdb")
    off, size = retro.files["english.langdb"]
    with open(archive, "rb") as f:
        f.seek(retro.base + off)
        stored = f.read(size)
    if stored[:4] + obscure(retro_text, bf, stored[:4]) != stored:
        raise ValueError("Die Retro-Texte lassen sich nicht unverändert zurückschreiben")
    old_dub = data.read(f"{language}.langdb")
    text = retro_text[:body_start(retro_text)] + retro_body(old_dub[body_start(old_dub):], language)
    new_text = stored[:4] + obscure(text, bf, stored[:4])

    head, cut = voice_layout(folder, english)
    names = {n.lower(): n for n in dubbed.files if n.lower().endswith(".vox")}
    targets = [n for n in os.listdir(folder) if n.lower() in names]

    # Keep the English state first, so a stop half way can always be undone.
    keep = backup_dir(game, e)
    voices = os.path.join(keep, "voices")
    os.makedirs(voices, exist_ok=True)
    table_head, table_raw, table = read_table(archive, bf)
    if bf.encrypt(table, "<II") != table_raw:
        raise ValueError("Das Retro-Archiv lässt sich nicht unverändert zurückschreiben")
    with open(os.path.join(keep, "table.bin"), "wb") as f:
        f.write(table_raw)
    for n in targets:
        shutil.copyfile(os.path.join(folder, n), os.path.join(voices, n))
    size_now = os.path.getsize(archive)
    with open(os.path.join(keep, "state.json"), "w", encoding="utf-8") as f:
        json.dump({"size": size_now, "language": language, "voices": len(targets)}, f)

    # Changed files are stored the same way; check that first on each original.
    added = [("english.langdb", new_text)]
    for name, plain in sorted((files or {}).items()):
        off, size = retro.files[name]
        retro._f.seek(retro.base + off)
        stored = retro._f.read(size)
        if stored[:4] + obscure(reveal(stored, bf), bf, stored[:4]) != stored:
            raise ValueError(f"{name} lässt sich nicht unverändert zurückschreiben")
        added.append((name, stored[:4] + obscure(plain, bf, stored[:4])))

    # The new files go to the end of the archive, and the table points there.
    entries = file_entries(table)
    table = bytearray(table)
    retro._f.close()
    at = size_now
    with open(archive, "r+b") as f:
        f.seek(size_now)
        for name, data in added:
            struct.pack_into("<Ii", table, entries[name], at - retro.base, len(data))
            f.write(data)
            at += len(data)
        f.seek(16)
        f.write(bf.encrypt(bytes(table), "<II"))
    for n in targets:
        body = dubbed.read(names[n.lower()])[OLD_HEAD:]
        with open(os.path.join(folder, n), "wb") as f:
            f.write(head + body[:len(body) - cut])

    return len(targets), len(text)
