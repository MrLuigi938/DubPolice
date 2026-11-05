"""Build the override archive: German voices plus lipsync files stretched to the German length.

Usage: build_mod2.py <libspeex.dll> <MainMenu.cs> <old German voice ttarch> <mapping.csv>
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
    for rid in ids:
        r = rows[rid]
        v = parse_vox(read_vox(voices, r["old_id"] + ".vox", old_key))
        if speex is None or speex.frame != v["frame"]:
            speex = Speex(dll, v["mode"])
        pcm = array.array("h")
        for p in v["packets"]:
            pcm.extend(speex.decode(p)[0])
        seconds = len(pcm) / v["rate"]
        files[rid + ".wav"] = make_fsb5(rid, pcm, v["rate"])
        with wave.open(os.path.join(preview, f"{rid}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(v["rate"])
            w.writeframes(pcm.tobytes())
        name = rid + ".anm"
        if name in remaster.files:
            data, old, scale, keys = patch(remaster.read(name), seconds)
            files[name] = data
            note = f"anm {old:6.2f}s -> {seconds:6.2f}s (x{scale:.2f}), {keys} keys"
        else:
            note = "no anm in remaster"
        print(f"{rid} {r['speaker']:6} {note}")
    archive_name = f"SM2_pc_{set_name}_uncompressed.ttarch2"
    with open(os.path.join(install, archive_name), "wb") as f:
        f.write(make_archive(files))
    print("built", archive_name, os.path.getsize(os.path.join(install, archive_name)), "files", len(files))


if __name__ == "__main__":
    main()
