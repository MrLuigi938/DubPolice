"""Write the mod's encrypted resource descriptor; the game ignores unencrypted ones.

Usage: write_resdesc.py <MainMenu.cs> <install dir> <set name>
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ectt import Blowfish7
from ttarch4 import load_key
from variants import desc, encrypt

source, install, name = sys.argv[1:4]
bf = Blowfish7(load_key(source, "SMBTaS"))
blob = encrypt(bf, desc(name, "constant", f"SM2_pc_{name}_uncompressed.ttarch2"))
assert bf.decrypt(blob[4:], "<II").startswith(b"local set = {}")
with open(os.path.join(install, f"_resdesc_50_{name}.lua"), "wb") as f:
    f.write(blob)
print("encrypted descriptor written:", len(blob), "bytes")
