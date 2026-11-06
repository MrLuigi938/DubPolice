"""Move a remaster chore onto Telltale's German timing from 2009. Voices keep their original speed."""
import bisect
import struct

from chore_fit import line_resources
from chore_warp import EDGE, chore_info, find_times


def old_times(buf):
    """All time values of a 2009 chore, in file order: keyframes and block edges."""
    out = []
    for i in range(0, len(buf) - 13):
        s = struct.unpack_from("<f", buf, i)[0]
        if buf[i + 4] in (0x30, 0x31) and buf[i + 5:i + 9] in (b"\x02\0\0\0", b"\x01\0\0\0") and -1 <= s < 400:
            out.append(s)
        elif 0 <= s < 400 and buf[i + 8] in (0x30, 0x31) and buf[i + 9:i + 13] == b"\0\0\x80\x3f":
            e = struct.unpack_from("<f", buf, i + 4)[0]
            if s < e < 400:
                out += [s, e]
    return out


def time_map(en, de):
    """Build the English -> German mapping from two 2009 chores with the same structure."""
    a, b = old_times(en), old_times(de)
    if len(a) != len(b):
        raise ValueError(f"old chores differ in structure: {len(a)} vs {len(b)}")
    return pairs_to_map(zip(a, b))


def pairs_to_map(pairs):
    table = {}
    for x, y in pairs:
        table.setdefault(round(x, 3), round(y, 3))
    xs = sorted(table)
    ys = [table[x] for x in xs]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1])
    return xs, ys


def apply_map(table, t):
    xs, ys = table
    if t <= xs[0]:
        return t + ys[0] - xs[0]
    if t >= xs[-1]:
        return t + ys[-1] - xs[-1]
    i = bisect.bisect_right(xs, t)
    x0, x1, y0, y1 = xs[i - 1], xs[i], ys[i - 1], ys[i]
    return y0 if x1 == x0 else y0 + (y1 - y0) * (t - x0) / (x1 - x0)


def port(d, hashes, seconds, table):
    """Return (patched chore, report, new length). Every time value follows the table."""
    body, length_at, length = chore_info(d)
    blocks, keys, _ = find_times(d, body, length)
    lines = line_resources(d, hashes, blocks)
    out = bytearray(d)
    for b in blocks:
        s, e = struct.unpack_from("<ff", d, b)
        struct.pack_into("<ff", out, b, apply_map(table, s), apply_map(table, e))
    for k in keys:
        struct.pack_into("<f", out, k, apply_map(table, struct.unpack_from("<f", d, k)[0]))
    new_length = apply_map(table, length)

    # Switched-off lines never play, so they cannot limit a line that does.
    starts = sorted(struct.unpack_from("<f", out, x[2])[0] for x in lines if d[x[2] + 15] == 0x31)
    report = []
    for rid, pos, block, limit in lines:
        if rid not in seconds:
            continue
        s, mapped_end = struct.unpack_from("<ff", out, block)
        # Like the original game: a line's block is exactly as long as its audio, never longer.
        wanted = s + seconds[rid]
        later = [x for x in starts if x > s + 1e-3]
        next_start = later[0] if later else None
        # Lines that already overlap in the original, like characters interrupting, may keep overlapping.
        overlaps = next_start is not None and next_start < mapped_end - 1e-3
        fits = next_start is None or wanted <= next_start + 1e-3 or overlaps
        end = wanted if fits else next_start
        delta = end - mapped_end
        if delta:
            for k in keys:
                if pos < k < limit:
                    t = struct.unpack_from("<f", out, k)[0]
                    if t >= mapped_end - EDGE:
                        struct.pack_into("<f", out, k, max(s, t + delta))
            struct.pack_into("<f", out, block + 4, end)
            mapped_end = end
        struct.pack_into("<f", out, pos + 8, seconds[rid])
        new_length = max(new_length, mapped_end)
        report.append((rid, s, mapped_end, seconds[rid], next_start, fits))
    struct.pack_into("<f", out, length_at, new_length)
    return bytes(out), report, new_length, lines
