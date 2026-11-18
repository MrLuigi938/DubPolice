"""Season 3 retro chores (Telltale MetaStream ERTM, 2010): make room for longer dubbed lines by pausing the scene.

Each resource of such a chore (an animation, a line, a sound, a camera, a nested chore) carries a control animation:
value channels keyed in chore time, among them its Time channel (how far into the resource it is) and its Weight.
The resource's blocks follow it. Making room for a line works like in the other releases: every time after a pause
moves later by the pause, and every keyed channel keeps its value through the pause, so the scene stands still while
the voice finishes. A line itself is stretched to its new end instead, so its voice and subtitle last to the end.

Layout of a control animation (all little-endian):
    u32 size (including itself), u32 version (4 or 5), u32 flags, u64 name, u32 0, f32 0,
    u32 inner size = size - 28, u32 channels, u32 pool, u32 types,
    per type: u64 type, u32 0, u16 channels of this type, u16 type version,
    per channel its body, per channel u32 flags (high byte: 1 time, 2 weight, 5 property), u16 0,
    per channel u64 name + u32 0.
A keyed body is u16 count, then count times (value, f32 time), then a byte per four keys (2 bits per key).
The pool is what the game sets aside for the keys: per keyed channel 4 bytes, its keys (value and time) rounded up to
4 bytes, and 4 more for every started 16 keys after the first (see pool_size; it holds for every control animation of
all five episodes). A wrong pool makes the game crash when it loads the chore.
"""
import math
import struct

U = lambda d, p: struct.unpack_from("<I", d, p)[0]  # noqa: E731
H = lambda d, p: struct.unpack_from("<H", d, p)[0]  # noqa: E731

KEYED = {  # type: value size
    bytes.fromhex("01f826ba8473ac79"): 4,   # float
    bytes.fromhex("f415b75b1d0e7a7f"): 4,   # float
    bytes.fromhex("dadab229610be9c0"): 1,   # bool
    bytes.fromhex("3c32c4a5db4b8a10"): 12,  # Vector3
    bytes.fromhex("14ef2b292e3630df"): 16,  # Quaternion
    bytes.fromhex("5876fc832a6f949a"): 16,  # Quaternion
}
SINGLE = {
    bytes.fromhex("7d4cfedb536d2344"): 4, bytes.fromhex("92c8bafab9ebf180"): 4,
    bytes.fromhex("dd09eaeae649f0d1"): 1, bytes.fromhex("a13ee2c006c8776b"): 12,
    bytes.fromhex("685bf348f928bfe2"): 16, bytes.fromhex("eeb75c833acecace"): 16,
}
SINGLE_TEXT = {bytes.fromhex(h) for h in ("5db0ebea01758786", "8e695041c68a7de6", "56dfcc86e6f5259d",
                                         "4789938320a67332")}
KEYED_TEXT = {bytes.fromhex(h) for h in ("9e41503844607b3a", "3bb17e53b8360123", "78aa8c59bf824c49",
                                        "60b8099272ff80f8")}  # (u32 length + text, f32 time) per key
PAIR = bytes.fromhex("d842a138ce055125")         # two blocked strings
KEYED_PAIR = bytes.fromhex("c7bcafec6109fb8e")   # (two blocked strings, f32 time) per key
SMOOTH = {4, 12, 16}  # value sizes that blend between keys and so need hold keys: float, Vector3, Quaternion
TIME, WEIGHT = 1, 2


class Channel:
    def __init__(self, kind, type_hash, raw=b"", size=0, keys=None, kinds=None):
        self.kind = kind          # "keyed", "text keys", "pair keys" or "fixed"
        self.type = type_hash
        self.raw = raw            # fixed channels: their bytes as they are
        self.size = size          # keyed: value size
        self.keys = keys or []    # [(value bytes, time)]
        self.kinds = kinds or []  # 2 bits per key
        self.flags = 0
        self.name = b""


def _keys(d, q, value_at):
    """Keys of a keyed body at q: value_at(q) gives where the time follows a value starting at q."""
    count = H(d, q)
    q += 2
    keys = []
    for _ in range(count):
        t_at = value_at(q)
        keys.append((d[q:t_at], struct.unpack_from("<f", d, t_at)[0]))
        q = t_at + 4
    nbytes = -(-count // 4)
    bits = d[q:q + nbytes]
    kinds = [(bits[i // 4] >> (2 * (i % 4))) & 3 for i in range(count)]
    return keys, kinds, q + nbytes


def pool_size(ch, n):
    """Bytes the game sets aside for a keyed channel with n keys."""
    if not n:
        return 4
    per_key = ch.size + 4 if ch.kind == "keyed" else 4
    return 4 + -(-per_key * n // 4) * 4 + 4 * ((n - 1) // 16)


def _blocked_pair_end(d, q):
    for _ in range(2):
        q += U(d, q)
    return q


class Animation:
    """A parsed control animation; `serialize` gives it back, byte for byte when nothing was changed."""

    def __init__(self, d, p):
        self.at = p
        size = U(d, p)
        if not (44 <= size <= len(d) - p and U(d, p + 4) in (4, 5) and U(d, p + 28) == size - 28):
            raise ValueError("keine Steuer-Animation")
        self.end = p + size
        self.head = d[p + 4:p + 28]
        self.raw = d[p:self.end]
        self.opaque = False
        try:
            self._read(d, p)
        except (ValueError, struct.error, IndexError) as err:
            if str(err) != "unbekannter Kanaltyp":
                raise ValueError(str(err))
            # One channel type is not known (compressed, 4 control animations in all five episodes). The channels
            # before it are read and can be moved in time where they are; it and all after it stay as they are.
            self.opaque = True
            self.prefix = self.channels
            self.channels = []
            self.keyed_count = {}

    def _read(self, d, p):
        inner = p + 28
        self.total, self.pool, types = U(d, inner + 4), U(d, inner + 8), U(d, inner + 12)
        q = inner + 16
        self.types = []
        for _ in range(types):
            self.types.append((d[q:q + 8], d[q + 8:q + 12], H(d, q + 12), d[q + 14:q + 16]))
            q += 16
        self.channels = []
        self.values_at = q
        for type_hash, _pad, count, _ver in self.types:
            for _ in range(count):
                if type_hash in KEYED:
                    n = KEYED[type_hash]
                    keys, kinds, e = _keys(d, q, lambda x, n=n: x + n)
                    self.channels.append(Channel("keyed", type_hash, size=n, keys=keys, kinds=kinds))
                elif type_hash in KEYED_TEXT:
                    keys, kinds, e = _keys(d, q, lambda x: x + 4 + U(d, x))
                    self.channels.append(Channel("text keys", type_hash, keys=keys, kinds=kinds))
                elif type_hash == KEYED_PAIR:
                    keys, kinds, e = _keys(d, q, lambda x: _blocked_pair_end(d, x))
                    self.channels.append(Channel("pair keys", type_hash, keys=keys, kinds=kinds))
                elif type_hash in SINGLE:
                    e = q + SINGLE[type_hash]
                    self.channels.append(Channel("fixed", type_hash, raw=d[q:e]))
                elif type_hash in SINGLE_TEXT:
                    e = q + 4 + U(d, q)
                    self.channels.append(Channel("fixed", type_hash, raw=d[q:e]))
                elif type_hash == PAIR:
                    e = _blocked_pair_end(d, q)
                    self.channels.append(Channel("fixed", type_hash, raw=d[q:e]))
                else:
                    self.prefix_end = q
                    raise ValueError("unbekannter Kanaltyp")
                q = e
        for ch in self.channels:
            ch.flags = U(d, q)
            q += 4
        if H(d, q) != 0:
            raise ValueError("unerwarteter Aufbau")
        q += 2
        for ch in self.channels:
            ch.name = d[q:q + 12]
            q += 12
        if q != self.end:
            raise ValueError("Steuer-Animation nicht vollständig gelesen")
        if self.total != len(self.channels):
            raise ValueError("Kanalzahl stimmt nicht")
        self.keyed_count = {id(ch): len(ch.keys) for ch in self.channels}

    def move_prefix(self, pauses):
        """An opaque animation: move the keys of the channels that can be read, in place (no keys added)."""
        for ch in self.prefix:
            if ch.kind != "fixed":
                ch.keys = [(v, pauses.map(t)) for v, t in ch.keys]

    @staticmethod
    def _body(ch):
        if ch.kind == "fixed":
            return ch.raw
        body = bytearray(struct.pack("<H", len(ch.keys)))
        for value, t in ch.keys:
            body += value + struct.pack("<f", t)
        bits = bytearray(-(-len(ch.keys) // 4))
        for i, k in enumerate(ch.kinds):
            bits[i // 4] |= (k & 3) << (2 * (i % 4))
        return bytes(body + bits)

    def serialize(self):
        if self.opaque:
            start, end = self.values_at - self.at, self.prefix_end - self.at
            prefix = b"".join(self._body(ch) for ch in self.prefix)
            if len(prefix) != end - start:
                raise ValueError("Steuer-Animation darf ihre Größe nicht ändern")
            return self.raw[:start] + prefix + self.raw[end:]
        body = bytearray()
        for type_hash, pad, count, ver in self.types:
            body += type_hash + pad + struct.pack("<H", count) + ver
        pool = self.pool
        for ch in self.channels:
            if ch.kind == "fixed":
                body += ch.raw
                continue
            body += struct.pack("<H", len(ch.keys))
            for value, t in ch.keys:
                body += value + struct.pack("<f", t)
            bits = bytearray(-(-len(ch.keys) // 4))
            for i, k in enumerate(ch.kinds):
                bits[i // 4] |= (k & 3) << (2 * (i % 4))
            body += bits
            added = len(ch.keys) - self.keyed_count[id(ch)]
            if added:
                if ch.kind != "keyed":
                    raise ValueError("Schlüssel nur in Zahlenkanälen einfügen")
                pool += pool_size(ch, len(ch.keys)) - pool_size(ch, self.keyed_count[id(ch)])
        for ch in self.channels:
            body += struct.pack("<I", ch.flags)
        body += b"\0\0"
        for ch in self.channels:
            body += ch.name
        inner = struct.pack("<III", len(self.channels), pool, len(self.types)) + bytes(body)
        inner = struct.pack("<I", len(inner) + 4) + inner
        return struct.pack("<I", 28 + len(inner)) + self.head + inner


def _string_before(d, end):
    """Start of the blocked string (u32 size, u32 length, text) that ends at `end`, or None."""
    for length in range(0, min(260, end - 8)):
        q = end - 8 - length
        if U(d, q) == 8 + length and U(d, q + 4) == length:
            return q
    return None


class Resource:
    def __init__(self, d, anim_at):
        self.anim = Animation(d, anim_at)
        name_at = _string_before(d, anim_at)
        if name_at is None:
            raise ValueError("Ressourcenname nicht gefunden")
        self.name = d[name_at + 8:anim_at].decode("latin-1").lower()
        self.length_at = name_at - 20
        b = self.anim.end
        count = U(d, b + 4)
        if U(d, b) != 8 + 13 * count:
            raise ValueError("Blockliste fehlt")
        self.blocks_at = b + 8
        self.blocks = [struct.unpack_from("<ff", d, self.blocks_at + 13 * i) for i in range(count)]
        self.flags = d[b + 8 + 13 * count:b + 8 + 13 * count + 8]
        self.enabled = self.flags[2:3] == b"1"


def resources(d):
    """All resources of a Season 3 retro chore, in file order. Raises ValueError if one does not read cleanly."""
    out = []
    i = 8
    n = len(d)
    while i < n - 40:
        size = U(d, i)
        if 44 <= size < n - i and U(d, i + 4) in (4, 5) and U(d, i + 28) == size - 28:
            try:
                r = Resource(d, i)
            except ValueError:
                i += 1
                continue
            out.append(r)
            i = r.anim.end
            continue
        i += 1
    return out


# ---------------------------------------------------------------- retiming


class Pauses:
    """Pauses in original chore time: [(at, seconds)]. A time strictly after `at` moves later by `seconds`."""

    def __init__(self, events):
        self.events = sorted((at, extra) for at, extra in events if extra > 0)

    def map(self, t):
        shift = sum(extra for at, extra in self.events if at < t)
        return t + shift if shift else t  # leaves -0.0 as it is

    def inside(self, lo, hi):
        return [(at, extra) for at, extra in self.events if lo < at < hi]


def _lerp(value_a, value_b, size, f):
    if size == 4:
        a, b = struct.unpack("<f", value_a)[0], struct.unpack("<f", value_b)[0]
        return struct.pack("<f", a + (b - a) * f)
    n = size // 4
    a, b = struct.unpack(f"<{n}f", value_a), struct.unpack(f"<{n}f", value_b)
    if n == 4 and sum(x * y for x, y in zip(a, b)) < 0:
        b = tuple(-x for x in b)
    out = [x + (y - x) * f for x, y in zip(a, b)]
    if n == 4:
        norm = math.sqrt(sum(x * x for x in out)) or 1.0
        out = [x / norm for x in out]
    return struct.pack(f"<{n}f", *out)


# How a key leads to the next one (2 bits per key, for the stretch that starts at it): bool channels use only STEP,
# time channels only LINE, weights mostly CURVE.
STEP, LINE, CURVE = 0, 1, 3


def segment(ch, t):
    """Index of the key whose stretch holds time t (the last key at or before it), or None before the first."""
    found = None
    for i, (_v, tk) in enumerate(ch.keys):
        if tk <= t:
            found = i
        else:
            break
    return found


def value_at(ch, t):
    """The channel's value at time t, as bytes. A STEP stretch keeps its value until the next key, a LINE stretch
    blends in a straight line; a CURVE is taken as straight too (only used where that is close enough)."""
    keys = ch.keys
    if t <= keys[0][1]:
        return keys[0][0]
    i = segment(ch, t)
    if i is None or i + 1 >= len(keys):
        return keys[-1][0]
    (va, ta), (vb, tb) = keys[i], keys[i + 1]
    if tb == ta or ch.kind != "keyed" or ch.size not in SMOOTH or ch.kinds[i] == STEP:
        return va
    return _lerp(va, vb, ch.size, (t - ta) / (tb - ta))


def hold_channel(ch, pauses):
    """Move the keys of a channel to new time and keep its value through every pause.

    Only stretches that run in a straight line or step get hold keys: a curve's shape depends on its neighbours in a
    way not known here, so a curve is stretched over the pause instead (like Telltale did in the German release)."""
    if not ch.keys:
        return
    old = list(ch.keys)
    kinds = list(ch.kinds)
    new = [(v, pauses.map(t), k) for (v, t), k in zip(old, kinds)]
    if ch.kind == "keyed" and ch.size in SMOOTH and len(old) > 1:
        for at, extra in pauses.inside(old[0][1], old[-1][1]):
            i = segment(ch, at)
            if i is None or kinds[i] not in (STEP, LINE):
                continue
            v = value_at(ch, at)
            k = kinds[i]
            start = pauses.map(at)
            if not any(abs(t - at) < 1e-6 for _v, t in old):
                new.append((v, start, k))
            new.append((v, start + extra, k))
    new.sort(key=lambda x: x[1])
    ch.keys = [(v, t) for v, t, _k in new]
    ch.kinds = [k for _v, _t, k in new]


def stretch_channel(ch, s, e, s2, e2, pauses):
    """A line's own channels: keys within its block stretch to the new block, others move like the rest."""
    def where(t):
        if s <= t <= e and e > s:
            return s2 + (t - s) * (e2 - s2) / (e - s)
        return pauses.map(t)
    ch.keys = [(v, where(t)) for v, t in ch.keys]


class Kid:
    """A nested chore that got longer: its old and new length and its own pauses (in its own time)."""

    def __init__(self, old_length, pauses):
        self.old_length = old_length
        self.pauses = pauses
        self.new_length = pauses.map(old_length)

    def extra_at(self, k):
        return sum(extra for at, extra in self.pauses.events if abs(at - k) < 0.02)


def _float(v):
    return struct.unpack("<f", v)[0]


def kid_time_segments(ch):
    """[(t0, t1, v0, v1)] of a nested chore's Time channel, where its value runs from v0 to v1."""
    keys = [(_float(v), t) for v, t in ch.keys]
    return [(ta, tb, va, vb) for (va, ta), (vb, tb) in zip(keys, keys[1:]) if tb > ta]


def kid_events(r, kid):
    """Where the outer chore must pause for its nested chore `r`: [(outer time, seconds)]."""
    out = []
    for ch in r.anim.channels:
        if ch.kind != "keyed" or ch.size != 4 or ch.flags >> 24 != TIME:
            continue
        for at, extra in kid.pauses.events:
            for ta, tb, va, vb in kid_time_segments(ch):
                lo, hi = va * kid.old_length, vb * kid.old_length
                if hi > lo and lo <= at <= hi:
                    t = ta + (at - lo) / (hi - lo) * (tb - ta)
                    if any(s - 0.05 <= t <= e + 0.05 for s, e in r.blocks):
                        out.append((t, extra))
    return out


def retime_kid_time(ch, pauses, kid):
    """A nested chore's Time channel (a share of its length): new length, its own pauses play through, others hold."""
    old = [(_float(v), t) for v, t in ch.keys]
    kinds = list(ch.kinds)
    L, N = kid.old_length, kid.new_length

    def share(k):
        # A time right at one of the nested chore's pauses counts as before it, like the outer chore's own keys.
        return (k + sum(extra for at, extra in kid.pauses.events if at < k - 1e-3)) / N

    new = [(share(v * L), pauses.map(t), k) for (v, t), k in zip(old, kinds)]
    for at, extra in pauses.inside(old[0][1], old[-1][1]):
        v = _float(value_at(ch, at))
        k = kinds[max(i for i, (_v, t) in enumerate(old) if t <= at)]
        start = pauses.map(at)
        own = min(kid.extra_at(v * L), extra)
        first = share(v * L)
        if not any(abs(t - at) < 1e-6 for _v, t in old):
            new.append((first, start, k))
        if own > 0:
            new.append((first + own / N, start + own, k))
        if extra > own:
            new.append((first + own / N, start + extra, k))
    new.sort(key=lambda x: x[1])
    ch.keys = [(struct.pack("<f", v), t) for v, t, _k in new]
    ch.kinds = [k for _v, _t, k in new]


SOUNDS = (".wav", ".aud", ".vox")
FADE_OUT = 0.35   # seconds a sound fades out before a pause, while it still plays
FADE_IN = 0.45    # seconds it fades back in after the pause
MIN_PAUSE = 0.09  # shorter pauses are not heard


def is_music(name):
    return name.startswith("mus_")


def silence_channel(ch, pauses):
    """A held sound repeats its last moment, so its weight fades out before each pause and back in after it.
    Pauses closer together than the two fades stay silent in between. Works on the already moved keys."""
    spans = []
    for at, extra in pauses.events:
        if extra < MIN_PAUSE:
            continue
        h0 = pauses.map(at)
        h1 = h0 + extra
        if spans and h0 - spans[-1][1] < FADE_OUT + FADE_IN:
            spans[-1] = (spans[-1][0], h1)
        else:
            spans.append((h0, h1))
    if not spans or len(ch.keys) < 1:
        return
    first, last = ch.keys[0][1], ch.keys[-1][1]
    for h0, h1 in spans:
        if h1 <= first or h0 >= last:
            continue
        a, b = max(first, h0 - FADE_OUT), min(last, h1 + FADE_IN)
        va, vb = value_at(ch, a), value_at(ch, b)
        k = LINE  # the fades run in straight lines
        zero = struct.pack("<f", 0.0)
        if b <= h1:
            # The sound ends within the pause: it stays silent from there on.
            keep = [(v, t, kk) for (v, t), kk in zip(ch.keys, ch.kinds) if t <= a]
            keep += [(va, a, k), (zero, max(a, h0), k), (zero, h1, k)]
        else:
            keep = [(v, t, kk) for (v, t), kk in zip(ch.keys, ch.kinds) if not a < t < b]
            keep += [(va, a, k), (zero, max(a, h0), k), (zero, h1, k), (vb, b, k)]
        keep.sort(key=lambda x: x[1])
        ch.keys = [(v, t) for v, t, _k in keep]
        ch.kinds = [kk for _v, _t, kk in keep]


def shift_channel(ch, s, pauses):
    """Music that keeps playing: its keys move with its start and run on at normal speed."""
    shift = pauses.map(s) - s
    if shift:
        ch.keys = [(v, t + shift) for v, t in ch.keys]


def retime(d, pauses, is_line, chore_length_at, kids=None, music_pause=True):
    """The chore with every resource moved to new time. `is_line(name)` tells line resources (stretched, not held);
    `kids` maps nested chores that got longer to their Kid. Sounds fade out during pauses; music keeps running
    instead when `music_pause` is off.

    Returns (new data, report counts)."""
    kids = kids or {}
    res = resources(d)
    out = bytearray()
    pos = 0
    counts = {"resources": len(res), "held channels": 0, "lines": 0}
    for r in res:
        base, seg = len(out), pos
        out += d[pos:r.anim.at]
        line = is_line(r.name)
        if r.anim.opaque:
            r.anim.move_prefix(pauses)
            counts["opaque"] = counts.get("opaque", 0) + 1
        elif line and r.blocks:
            s, e = r.blocks[0]
            s2, e2 = pauses.map(s), pauses.map(e)
            for ch in r.anim.channels:
                if ch.kind != "fixed":
                    stretch_channel(ch, s, e, s2, e2, pauses)
            counts["lines"] += 1
        elif r.name.endswith(SOUNDS) and is_music(r.name) and not music_pause and r.blocks:
            for ch in r.anim.channels:
                if ch.kind != "fixed" and ch.keys:
                    shift_channel(ch, r.blocks[0][0], pauses)
            counts["music running"] = counts.get("music running", 0) + 1
        else:
            kid = kids.get(r.name)
            for ch in r.anim.channels:
                if ch.kind == "fixed" or not ch.keys:
                    continue
                if kid and ch.kind == "keyed" and ch.size == 4 and ch.flags >> 24 == TIME:
                    retime_kid_time(ch, pauses, kid)
                    counts["nested"] = counts.get("nested", 0) + 1
                    continue
                before = len(ch.keys)
                hold_channel(ch, pauses)
                counts["held channels"] += len(ch.keys) != before
                if r.name.endswith(SOUNDS) and ch.kind == "keyed" and ch.size == 4 and ch.flags >> 24 == WEIGHT:
                    silence_channel(ch, pauses)
                    counts["silenced sounds"] = counts.get("silenced sounds", 0) + 1
        anim = r.anim.serialize()
        out += anim
        pos = r.anim.end
        # Blocks and the resource length keep their size and are rewritten in place below.
        block_list = bytearray(d[r.anim.end:r.blocks_at + 13 * len(r.blocks)])
        for i, (s, e) in enumerate(r.blocks):
            struct.pack_into("<ff", block_list, 8 + 13 * i, pauses.map(s), pauses.map(e))
        out += block_list
        pos = r.blocks_at + 13 * len(r.blocks)
        if line and r.blocks and r.length_at >= seg:
            # A line's own length sits before its name; it is the length of its block.
            s, e = r.blocks[0]
            old_len = struct.unpack_from("<f", d, r.length_at)[0]
            grow = (pauses.map(e) - e) - (pauses.map(s) - s)
            if abs(old_len - (e - s)) < 0.01 and grow:
                struct.pack_into("<f", out, base + r.length_at - seg, old_len + grow)
        kid = kids.get(r.name)
        if kid and r.length_at >= seg:
            # A nested chore's length sits before its name; some originals keep a slightly different one.
            old_len = struct.unpack_from("<f", d, r.length_at)[0]
            if kid.old_length > 0 and 0.9 < old_len / kid.old_length < 1.1:
                struct.pack_into("<f", out, base + r.length_at - seg, old_len * kid.new_length / kid.old_length)
    out += d[pos:]
    length = struct.unpack_from("<f", d, chore_length_at)[0]
    struct.pack_into("<f", out, chore_length_at, pauses.map(length))
    return bytes(out), counts


# ---------------------------------------------------------------- a whole episode

STEP = 0.002


def line_id(name):
    """The line id of a line resource such as 174080015.lang, or None."""
    if name.endswith(".lang") and name[:-5].isdigit():
        return int(name[:-5])
    return None


def own_events(res, seconds):
    """Pauses a chore needs for its own lines: at each line's end (or where the next line cuts in), the time the
    dubbed line lacks."""
    spans = sorted((r.blocks[0][0], r.blocks[0][1], line_id(r.name)) for r in res
                   if line_id(r.name) is not None and r.enabled and r.blocks)
    events = []
    for s, e, rid in spans:
        if rid not in seconds:
            continue
        extra = seconds[rid] - (e - s)
        if extra > 0:
            end = min([e] + [s2 for s2, _e2, _r in spans if s2 > s + 0.001])
            events.append((max(s, end - STEP), extra))
    return events


def merge(events):
    out = []
    for at, extra in sorted(events):
        if out and at - out[-1][0] < 0.02:
            out[-1] = (out[-1][0], max(out[-1][1], extra))
        else:
            out.append((at, extra))
    return out


def fit(chores, seconds, chore_length, music_pause=True):
    """Fit dubbed lines into the chores of one Season 3 retro episode.

    `chores` maps lower-case names to plain data, `seconds` line ids to dubbed lengths, `chore_length(data)` gives
    (offset, value) of a chore's length. Returns ({name: new data}, {name: [(at, extra)]})."""
    parsed = {}

    def res_of(n):
        if n not in parsed:
            try:
                parsed[n] = resources(chores[n])
            except ValueError:
                parsed[n] = None
        return parsed[n]

    with_lines = {n for n, d in chores.items() if b".lang" in d}
    memo = {}

    def plan(n, path=()):
        if n in memo:
            return memo[n]
        if n in path:
            return []
        memo[n] = []
        res = res_of(n)
        if res is None:
            return []
        events = own_events(res, seconds) if n in with_lines else []
        kids = {}
        for r in res:
            if r.name.endswith(".chore") and r.name in chores and r.name != n:
                kid_events_here = plan(r.name, path + (n,))
                if kid_events_here:
                    kid = Kid(chore_length(chores[r.name])[1], Pauses(kid_events_here))
                    kids[r.name] = kid
                    events += kid_events(r, kid)
        memo[n] = merge(events)
        kids_of[n] = kids
        return memo[n]

    kids_of = {}
    # Only chores that play lines, or play chores that do, can need pauses.
    candidates = set(with_lines)
    grew = True
    while grew:
        grew = False
        names = [k.encode("latin-1") for k in candidates]
        for n, d in chores.items():
            if n not in candidates and any(k in d.lower() for k in names if k != n.encode("latin-1")):
                candidates.add(n)
                grew = True
    out = {}
    for n in sorted(candidates):
        events = plan(n)
        if not events:
            continue
        d = chores[n]
        new, _counts = retime(d, Pauses(events), lambda name: line_id(name) is not None,
                              chore_length(d)[0], kids_of.get(n, {}), music_pause)
        out[n] = new
    return out, memo
