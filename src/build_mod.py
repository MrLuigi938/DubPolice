"""Build a small override archive with German 2009 voices for remaster voice IDs.

Usage: build_mod.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
                    <output dir> <set name> <remaster id> [<remaster id> ...]
"""
import array
import csv
import hashlib
import os
import struct
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ttarch4 import load_key
from vox2wav import Speex, parse_vox, read_vox

RATE_CODES = {8000: 1, 11025: 2, 16000: 3, 22050: 5, 24000: 6, 32000: 7, 44100: 8, 48000: 9}
FSB_MODE_PCM16 = 2


def crc64(data):
    c = 0
    for b in data:
        c ^= b << 56
        for _ in range(8):
            c = ((c << 1) ^ 0x42F0E1EBA9EA3693) & 0xFFFFFFFFFFFFFFFF if c >> 63 else (c << 1) & 0xFFFFFFFFFFFFFFFF
    return c


def make_fsb5(name, pcm, rate):
    """One-sample mono FSB5 version 1 container holding 16-bit PCM."""
    samples = len(pcm)
    word = (RATE_CODES[rate] << 1) | (samples << 34)
    sample_header = struct.pack("<Q", word)
    raw = pcm.tobytes()
    raw += b"\0" * (-len(raw) % 32)
    names = struct.pack("<I", 4) + name.encode() + b"\0"
    names += b"\0" * (-(60 + len(sample_header) + len(names)) % 32)
    head = b"FSB5" + struct.pack("<6I", 1, 1, len(sample_header), len(names), len(raw), FSB_MODE_PCM16)
    head += struct.pack("<IIII", 1, 0, 0, 0)
    head += hashlib.md5(raw).digest()
    assert len(head) == 60
    return head + sample_header + names + raw


def make_archive(files):
    """Uncompressed, unencrypted .ttarch2 (NCTT) with the same layout as the game's own archives."""
    items = sorted(((crc64(n.lower().encode()), n, d) for n, d in files.items()), key=lambda x: x[0])
    names = bytearray()
    positions = {}
    for _, n, _d in items:
        raw = n.encode() + b"\0"
        room = 0x10000 - (len(names) % 0x10000)
        if len(raw) > room:
            names += b"\0" * room
        positions[n] = len(names)
        names += raw
    names += b"\0" * (-len(names) % 0x10000)
    table = bytearray()
    off = 0
    for crc, n, d in items:
        block, inner = divmod(positions[n], 0x10000)
        table += struct.pack("<QQIIHH", crc, off, len(d), 0, block, inner)
        off += len(d)
    body = b"4ATT" + struct.pack("<II", len(names), len(items)) + bytes(table) + bytes(names)
    body += b"".join(d for _, _, d in items)
    return b"NCTT" + struct.pack("<Q", len(body)) + body


def resdesc(set_name, archive_name):
    return f"""local set = {{}}
set.name = "{set_name}"
set.setName = "{set_name}"
set.descriptionFilenameOverride = ""
set.logicalName = "<{set_name}>"
set.logicalDestination = "<>"
set.priority = 1000
set.localDir = _currentDirectory
set.enableMode = "constant"
set.version = "trunk"
set.descriptionPriority = 0
set.gameDataName = "{set_name} Game Data"
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
    _currentDirectory .. "{archive_name}"
}}
RegisterSetDescription(set)
""".replace("\n", "\r\n").encode("ascii")


def main():
    dll, source, voices, mapping, out, set_name, *ids = sys.argv[1:]
    rows = {r["remaster_id"]: r for r in csv.DictReader(open(mapping, encoding="utf-8-sig"), delimiter=";")}
    key = load_key(source, "SM201")
    preview = os.path.join(out, "preview_wav")
    install = os.path.join(out, "install")
    os.makedirs(preview, exist_ok=True)
    os.makedirs(install, exist_ok=True)
    speex = None
    files = {}
    for rid in ids:
        r = rows[rid]
        if not r["old_id"]:
            raise SystemExit(f"{rid} has no old line")
        v = parse_vox(read_vox(voices, r["old_id"] + ".vox", key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        errors = 0
        for p in v["packets"]:
            s, _fr, err = speex.decode(p)
            pcm.extend(s)
            errors += err
        files[rid + ".wav"] = make_fsb5(rid, pcm, v["rate"])
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v["rate"])
            w.writeframes(pcm.tobytes())
        print(f"{rid} <- {r['old_id']} {r['speaker']:6} DE {len(pcm) / v['rate']:6.2f}s, remaster EN {float(r['remaster_seconds']):6.2f}s, errors {errors}: {ascii(r['old_german'][:60])}")
    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    with open(os.path.join(install, f"_resdesc_50_{set_name}.lua"), "wb") as f:
        f.write(resdesc(set_name, archive_name))
    for n in sorted(os.listdir(install)):
        print("built", n, os.path.getsize(os.path.join(install, n)))


if __name__ == "__main__":
    main()
