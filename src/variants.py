"""Write temporary test descriptors that point at existing, unused language archives.

Usage: variants.py <MainMenu.cs> <output dir>
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ectt import Blowfish7
from ttarch4 import load_key


def encrypt(bf, data):
    out = bytearray(data)
    P = bf.P
    Q = bf.P7
    s0, s1, s2, s3 = bf.S
    for o in range(0, len(data) - len(data) % 8, 8):
        l, r = struct.unpack_from("<II", data, o)
        l ^= P[0]
        for i in range(0, 16, 2):
            r ^= (((((s0[l >> 24] + s1[(l >> 16) & 255]) & 0xFFFFFFFF) ^ s2[(l >> 8) & 255]) + s3[l & 255]) & 0xFFFFFFFF) ^ Q[i + 1]
            l ^= (((((s0[r >> 24] + s1[(r >> 16) & 255]) & 0xFFFFFFFF) ^ s2[(r >> 8) & 255]) + s3[r & 255]) & 0xFFFFFFFF) ^ Q[i + 2]
        r ^= P[17]
        struct.pack_into("<II", out, o, r, l)
    return b"\x1bLEo" + bytes(out)


def desc(name, mode, archive, priority=1000):
    text = f"""local set = {{}}
set.name = "{name}"
set.setName = "{name}"
set.descriptionFilenameOverride = ""
set.logicalName = "<{name}>"
set.logicalDestination = "<>"
set.priority = {priority}
set.localDir = _currentDirectory
set.enableMode = "{mode}"
set.version = "trunk"
set.descriptionPriority = 0
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
    _currentDirectory .. "{archive}"
}}
RegisterSetDescription(set)
"""
    return text.replace("\n", "\r\n").encode("ascii")


if __name__ == "__main__":
    source, out = sys.argv[1:3]
    bf = Blowfish7(load_key(source, "SMBTaS"))
    # Round-trip check against a real game file before trusting encrypt().
    real = open(os.path.join(out, "_resdesc_50_German.lua"), "rb").read()
    plain = bf.decrypt(real[4:], "<II")
    assert encrypt(bf, plain) == real, "encrypt does not reproduce the game's file"
    print("encrypt() reproduces _resdesc_50_German.lua byte for byte")
    open(os.path.join(out, "_resdesc_50_ZTestPlain.lua"), "wb").write(desc("ZTestPlain", "constant", "SM2_pc_French_compressed.ttarch2"))
    open(os.path.join(out, "_resdesc_50_ZTestEnc.lua"), "wb").write(encrypt(bf, desc("ZTestEnc", "constant", "SM2_pc_Spanish_compressed.ttarch2")))
    open(os.path.join(out, "_resdesc_50_ZTestBoot.lua"), "wb").write(desc("ZTestBoot", "bootable", "SM2_pc_Italian_compressed.ttarch2"))
    print("wrote 3 test descriptors")
