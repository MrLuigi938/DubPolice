"""IMA-ADPCM (Xbox layout, mono: 36-byte blocks) inside an FSB5 container."""
import array
import hashlib
import struct

STEP = [7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449, 494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767]
INDEX = [-1, -1, -1, -1, 2, 4, 6, 8]
RATE_CODES = {8000: 1, 11025: 2, 16000: 3, 22050: 5, 24000: 6, 32000: 7, 44100: 8, 48000: 9}
FRAME_BYTES = 36
FRAME_SAMPLES = 64
FSB_MODE_IMA = 7


def encode(pcm):
    """Encode samples in blocks; each block header restarts the decoder at a real sample."""
    out = bytearray()
    index = 0
    n = len(pcm)
    for start in range(0, n, FRAME_SAMPLES):
        block = list(pcm[start:start + FRAME_SAMPLES])
        block += [0] * (FRAME_SAMPLES - len(block))
        pred = block[0]
        out += struct.pack("<hBB", pred, index, 0)
        nibbles = []
        for sample in block:
            step = STEP[index]
            diff = sample - pred
            code = 0
            if diff < 0:
                code = 8
                diff = -diff
            delta = step >> 3
            if diff >= step:
                code |= 4
                diff -= step
                delta += step
            half = step >> 1
            if diff >= half:
                code |= 2
                diff -= half
                delta += half
            quarter = step >> 2
            if diff >= quarter:
                code |= 1
                delta += quarter
            pred = pred - delta if code & 8 else pred + delta
            pred = max(-32768, min(32767, pred))
            index = max(0, min(88, index + INDEX[code & 7]))
            nibbles.append(code)
        for i in range(0, FRAME_SAMPLES, 2):
            out.append(nibbles[i] | (nibbles[i + 1] << 4))
    return bytes(out)


def make_fsb5_ima(name, pcm, rate):
    raw = encode(pcm)
    samples = len(raw) // FRAME_BYTES * FRAME_SAMPLES
    sample_header = struct.pack("<Q", (RATE_CODES[rate] << 1) | (samples << 34))
    pad_data = raw + b"\0" * (-len(raw) % 32)
    names = struct.pack("<I", 4) + name.encode() + b"\0"
    names += b"\0" * (-(60 + len(sample_header) + len(names)) % 32)
    head = b"FSB5" + struct.pack("<6I", 1, 1, len(sample_header), len(names), len(pad_data), FSB_MODE_IMA)
    head += struct.pack("<IIII", 1, 0, 0, 0) + hashlib.md5(pad_data).digest()
    return head + sample_header + names + pad_data
