"""The Dub Police badge on the remaster's main menu: a sticker on the game's logo that says the dub is active.

The logo is a D3DTX texture in BC3 (DXT5): 16-byte blocks of 4x4 pixels, 8 bytes alpha, 8 bytes colour. Only the
blocks the badge touches are encoded again; all others keep their original bytes. The changed logo goes into a small
archive of its own, which a second description of the game's UI set lists first (like the episode archives).
The badges themselves are drawn once at their final size and ship in ui/badges.
"""
import os
import re
import struct

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
# Per season: UI archive, logo texture, where the badge's centre goes on it.
LOGOS = {
    "SM1": ("ui_logoSamMaxSaveTheWorld.d3dtx", (735, 890)),
    "SM2": ("ui_logoSamMaxBeyondTimeAndSpace.d3dtx", (760, 840)),
    "SM3": ("ui_logoSamMaxTheDevilsPlayhouse.d3dtx", (1430, 840)),
}
BC3 = 0x42


def _565(rgb):
    r, g, b = (np.clip(np.rint(rgb[..., i] * s / 255), 0, s).astype(np.uint32) for i, s in ((0, 31), (1, 63), (2, 31)))
    return (r << 11) | (g << 5) | b


def _from565(c):
    return np.stack([((c >> 11) & 31) * 255 / 31, ((c >> 5) & 63) * 255 / 63, (c & 31) * 255 / 31], -1)


def decode_bc3(data, w, h):
    """RGBA pixels (h, w, 4) of BC3 data."""
    blocks = np.frombuffer(data[:w * h], dtype=np.uint8).reshape(-1, 16)
    n = len(blocks)
    a0, a1 = blocks[:, 0].astype(np.float32), blocks[:, 1].astype(np.float32)
    bits = np.zeros(n, dtype=np.uint64)
    for i in range(6):
        bits |= blocks[:, 2 + i].astype(np.uint64) << np.uint64(8 * i)
    aidx = np.stack([(bits >> np.uint64(3 * i)) & np.uint64(7) for i in range(16)], 1).astype(np.int64)
    eight = a0 > a1
    apal = np.zeros((n, 8), np.float32)
    apal[:, 0], apal[:, 1] = a0, a1
    for k in range(2, 8):
        apal[:, k] = ((8 - k) * a0 + (k - 1) * a1) / 7
    six = ~eight
    for k in range(2, 6):
        apal[six, k] = ((6 - k) * a0[six] + (k - 1) * a1[six]) / 5
    apal[six, 6], apal[six, 7] = 0, 255
    alpha = apal[np.arange(n)[:, None], aidx]
    c0 = blocks[:, 8].astype(np.uint32) | (blocks[:, 9].astype(np.uint32) << 8)
    c1 = blocks[:, 10].astype(np.uint32) | (blocks[:, 11].astype(np.uint32) << 8)
    p0, p1 = _from565(c0), _from565(c1)
    four = (c0 > c1)[:, None]
    pal = np.stack([p0, p1, np.where(four, (2 * p0 + p1) / 3, (p0 + p1) / 2), np.where(four, (p0 + 2 * p1) / 3, 0)], 1)
    cbits = blocks[:, 12:16].copy().view(np.uint32)[:, 0]
    cidx = np.stack([(cbits >> (2 * i)) & 3 for i in range(16)], 1).astype(np.int64)
    rgb = pal[np.arange(n)[:, None], cidx]
    px = np.concatenate([rgb, alpha[:, :, None]], 2)
    return np.clip(np.rint(px), 0, 255).astype(np.uint8).reshape(h // 4, w // 4, 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4)


def encode_bc3_block(px):
    """16 bytes for one block of 16 RGBA pixels (16, 4)."""
    px = px.astype(np.float32)
    a = px[:, 3]
    amax, amin = int(round(a.max())), int(round(a.min()))
    if amax == amin:
        abytes = bytes([amax, amin]) + bytes(6)
    else:
        a0, a1 = max(amax, amin + 1), amin
        levels = np.array([a0, a1] + [((8 - k) * a0 + (k - 1) * a1) / 7 for k in range(2, 8)], np.float32)
        idx = np.abs(a[:, None] - levels[None, :]).argmin(1)
        bits = 0
        for i, v in enumerate(idx):
            bits |= int(v) << (3 * i)
        abytes = bytes([a0, a1]) + bits.to_bytes(6, "little")
    rgb = px[:, :3]
    weight = a > 8  # colour of invisible pixels does not matter
    pts = rgb[weight] if weight.any() else rgb
    mean = pts.mean(0)
    cov = np.cov((pts - mean).T) if len(pts) > 1 else np.eye(3)
    axis = np.linalg.eigh(cov)[1][:, -1] if np.isfinite(cov).all() and cov.any() else np.array([1.0, 1.0, 1.0]) / 3 ** 0.5
    proj = (pts - mean) @ axis
    e0, e1 = mean + axis * proj.max(), mean + axis * proj.min()
    c0, c1 = int(_565(e0)), int(_565(e1))
    if c0 < c1:
        c0, c1 = c1, c0
    if c0 == c1:
        cbits = 0
    else:
        p0, p1 = _from565(np.uint32(c0)), _from565(np.uint32(c1))
        pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3])
        idx = ((rgb[:, None, :] - pal[None, :, :]) ** 2).sum(2).argmin(1)
        cbits = 0
        for i, v in enumerate(idx):
            cbits |= int(v) << (2 * i)
    return abytes + c0.to_bytes(2, "little") + c1.to_bytes(2, "little") + cbits.to_bytes(4, "little")


def stick(texture, w, h, badge, cx, cy):
    """BC3 texture data (w x h) with the RGBA badge pasted, centred at (cx, cy). Returns (new data, pixels)."""
    img = decode_bc3(texture, w, h).astype(np.float32)
    b = badge.astype(np.float32)
    x0, y0 = int(cx - b.shape[1] / 2), int(cy - b.shape[0] / 2)
    x1, y1 = min(w, x0 + b.shape[1]), min(h, y0 + b.shape[0])
    bx0, by0 = max(0, -x0), max(0, -y0)
    x0, y0 = max(0, x0), max(0, y0)
    part = b[by0:by0 + (y1 - y0), bx0:bx0 + (x1 - x0)]
    ba = part[:, :, 3:4] / 255
    under = img[y0:y1, x0:x1]
    out_a = ba + under[:, :, 3:4] / 255 * (1 - ba)
    rgb = (part[:, :, :3] * ba + under[:, :, :3] * (under[:, :, 3:4] / 255) * (1 - ba)) / np.maximum(out_a, 1e-6)
    img[y0:y1, x0:x1, :3] = np.where(out_a > 0, rgb, under[:, :, :3])
    img[y0:y1, x0:x1, 3:4] = out_a * 255
    out = bytearray(texture[:w * h])
    pixels = np.clip(np.rint(img), 0, 255).astype(np.uint8)
    for by in range(y0 // 4, (y1 + 3) // 4):
        for bx in range(x0 // 4, (x1 + 3) // 4):
            block = pixels[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4].reshape(16, 4)
            i = (by * (w // 4) + bx) * 16
            out[i:i + 16] = encode_bc3_block(block)
    return bytes(out), pixels


def badge_image(language, folder=None):
    folder = folder or os.path.join(HERE, "ui", "badges")
    with np.load(os.path.join(folder, f"badge_{language}.npz")) as f:
        return f["rgba"]


def logo_with_badge(d3dtx, name, language, centre, folder=None):
    """The logo texture file with the badge on it, or None if it is not the expected single-level BC3 texture."""
    at = d3dtx.find(name.encode("latin-1"))
    if at < 0:
        return None
    at += len(name)
    mips, w, h = struct.unpack_from("<III", d3dtx, at + 13)
    fmt = struct.unpack_from("<I", d3dtx, at + 33)[0]
    if mips != 1 or fmt != BC3 or len(d3dtx) < w * h:
        return None
    data, _ = stick(d3dtx[-w * h:], w, h, badge_image(language, folder), *centre)
    return d3dtx[:-w * h] + data


def menu_files(season, game, language, ui_archive, key_cipher, encrypt, make_archive):
    """[(file name, data)] that put the badge on the main menu: the archive and its description.

    `ui_archive` reads the game's UI archive, `key_cipher` is the season's Blowfish, `encrypt` and `make_archive` are
    the helpers the episodes use."""
    prefix = season["prefix"]
    name, centre = LOGOS[prefix]
    logo = logo_with_badge(ui_archive.read(name), name, language, centre)
    if logo is None:
        raise ValueError("Logo des Menüs hat ein unerwartetes Format")
    archive_name = f"{prefix}_pc_UI_DubPolice_uncompressed.ttarch2"
    with open(os.path.join(game, "Archives", "_resdesc_50_UI.lua"), "rb") as f:
        original = f.read()
    text = key_cipher.decrypt(original[4:], "<II").decode("latin-1")
    text, priorities = re.subn(r"set\.descriptionPriority\s*=\s*\d+", "set.descriptionPriority = 100", text)
    text, lists = re.subn(r"(set\.gameDataArchives\s*=\s*\{\s*)",
                          lambda m: f'{m.group(1)}_currentDirectory .. "{archive_name}",\r\n    ', text)
    if priorities != 1 or lists != 1:
        raise ValueError("Die Steuerdatei des Menüs hat einen unbekannten Aufbau")
    return [(archive_name, make_archive({name: logo})),
            ("_resdesc_51_UIDubPolice.lua", encrypt(key_cipher, text.encode("latin-1")))]
