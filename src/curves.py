"""Give a chore's animation time curves intermediate points, so long tracks follow the lines exactly.

A curve is a key list: <size:u32><count:u32> then 13-byte records (time, flag, mode, value), preceded by a
property symbol. Two enclosing size fields, 29 bytes apart, share one end; the meta header holds the total.
"""
import re
import struct

from chore_warp import is_retro
from port_schedule import apply_map

TIME_PROPERTY = bytes.fromhex("55 d3 dc a6 0f a3 d6 4b")
RETRO_TIME_PROPERTY = b"\x04\x00\x00\x00time"  # the retro release names it in plain text, also 8 bytes
TWO_KEYS = bytes.fromhex("22 00 00 00 02 00 00 00")
MIN_SPACING = 0.05


def time_property(d):
    return RETRO_TIME_PROPERTY if is_retro(d) else TIME_PROPERTY


def curve_start(d, t):
    """The key list of the time property named at `t`, or None. Episode 205 keeps one more byte before it."""
    for offset in (20, 21) if is_retro(d) else (20,):
        if t + offset + 8 <= len(d):
            size, keys = struct.unpack_from("<II", d, t + offset)
            if keys >= 1 and size == 8 + 13 * keys:
                return t + offset
    return None


def find_curves(d):
    found = (curve_start(d, m.start()) for m in re.finditer(re.escape(time_property(d)), d))
    return [c for c in found if c is not None and d[c:c + 8] == TWO_KEYS]


def enclosing(d, c):
    """The two size fields around curve `c`: closest pair, 29 bytes apart, with the same end.

    In the retro release the outer one is followed by one or two numbers, the chore's name in plain text, a zero and the
    inner one."""
    if is_retro(d):
        for inner in range(c - 4, max(c - 2000, 8), -1):
            end = inner + struct.unpack_from("<I", d, inner)[0]
            if not c + 34 <= end <= len(d):
                continue
            for outer in range(inner - 12, max(inner - 600, 0), -1):
                if outer + struct.unpack_from("<I", d, outer)[0] != end:
                    continue
                for gap in (8, 12):
                    block, ln = struct.unpack_from("<II", d, outer + gap)
                    if block == ln + 8 and outer + gap + 4 + block == inner:
                        return outer, inner
        raise ValueError(f"no enclosing size fields for curve at {c}")
    for inner in range(c - 4, max(c - 2000, 33), -1):
        size_i = struct.unpack_from("<I", d, inner)[0]
        size_o = struct.unpack_from("<I", d, inner - 29)[0]
        end = inner + size_i
        if c + 34 <= end <= len(d) and inner - 29 + size_o == end:
            return inner - 29, inner
    raise ValueError(f"no enclosing size fields for curve at {c}")


def refine(original, patched, table, lines, protected=()):
    """Insert points into every curve the table bends, except lines and `protected` (sounds, nested chores)."""
    xs = table[0]
    line_ranges = [(pos, limit) for _, pos, _, limit in lines] + [(p, l) for p, l in protected if original[p:p + 8]]
    work = bytearray(patched)
    changed = points = 0
    total_added = 0
    for c in sorted(find_curves(original), reverse=True):
        if any(p < c < l for p, l in line_ranges):
            continue
        a = struct.unpack_from("<f", original, c + 8)[0]
        b = struct.unpack_from("<f", original, c + 21)[0]
        if struct.unpack_from("<f", original, c + 17)[0] != 0.0 or struct.unpack_from("<f", original, c + 30)[0] != 1.0 or b <= a:
            continue
        chosen = []
        for x in xs:
            # Two original times close together can still be a long way apart after mapping: that is a pause.
            if a + MIN_SPACING < x < b - MIN_SPACING and (
                not chosen or x - chosen[-1] >= MIN_SPACING or apply_map(table, x) - apply_map(table, chosen[-1]) >= MIN_SPACING
            ):
                chosen.append(x)
        # Only bends matter: drop points the straight line already passes through.
        ta, tb = apply_map(table, a), apply_map(table, b)
        chosen = [x for x in chosen if abs(apply_map(table, x) - (ta + (tb - ta) * (x - a) / (b - a))) > 0.005]
        if not chosen:
            continue
        outer, inner = enclosing(original, c)
        mode = original[c + 12:c + 17]
        extra = bytearray()
        last = ta
        for x in chosen:
            t = apply_map(table, x)
            if t <= last:
                continue
            extra += struct.pack("<f", t) + b"\x31" + mode[1:] + struct.pack("<f", (x - a) / (b - a))
            last = t
        count = len(extra) // 13
        if not count:
            continue
        # Offsets are unchanged in `work` here because curves are handled from the end of the file.
        work[c + 21:c + 21] = extra
        struct.pack_into("<II", work, c, 34 + len(extra), 2 + count)
        for field in (outer, inner):
            struct.pack_into("<I", work, field, struct.unpack_from("<I", work, field)[0] + len(extra))
        total_added += len(extra)
        changed += 1
        points += count
    if not is_retro(original):  # the retro files have no total size in their header
        struct.pack_into("<I", work, 4, struct.unpack_from("<I", work, 4)[0] + total_added)
    return bytes(work), changed, points
