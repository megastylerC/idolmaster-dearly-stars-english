"""NDS LZ77 (type 0x10) compress/decompress."""


def decompress(data):
    if data[0] != 0x10:
        raise ValueError(f"not LZ77 (type byte {data[0]:#x})")
    size = data[1] | data[2] << 8 | data[3] << 16
    out = bytearray()
    pos = 4
    while len(out) < size:
        flags = data[pos]
        pos += 1
        for bit in range(8):
            if len(out) >= size:
                break
            if flags & (0x80 >> bit):
                b1, b2 = data[pos], data[pos + 1]
                pos += 2
                length = (b1 >> 4) + 3
                disp = ((b1 & 0xF) << 8 | b2) + 1
                for _ in range(length):
                    out.append(out[-disp])
            else:
                out.append(data[pos])
                pos += 1
    return bytes(out)


def compress(data):
    n = len(data)
    if n >= 1 << 24:
        raise ValueError("too large")
    out = bytearray([0x10, n & 0xFF, (n >> 8) & 0xFF, (n >> 16) & 0xFF])
    # index positions of 3-byte sequences for fast match search
    anchors = {}
    pos = 0
    while pos < n:
        flag_idx = len(out)
        out.append(0)
        flags = 0
        for bit in range(8):
            if pos >= n:
                break
            best_len = 0
            best_disp = 0
            if pos + 3 <= n:
                key = data[pos:pos + 3]
                cands = anchors.get(key, ())
                lo = pos - 0x1000
                for cand in reversed(cands):
                    if cand < lo:
                        break
                    length = 3
                    maxlen = min(18, n - pos)
                    while length < maxlen and data[cand + length] == data[pos + length]:
                        length += 1
                    if length > best_len:
                        best_len = length
                        best_disp = pos - cand
                        if length == maxlen:
                            break
            if best_len >= 3:
                flags |= 0x80 >> bit
                disp = best_disp - 1
                out.append(((best_len - 3) << 4) | (disp >> 8))
                out.append(disp & 0xFF)
                for k in range(best_len):
                    if pos + 3 <= n:
                        anchors.setdefault(bytes(data[pos:pos + 3]), []).append(pos)
                    pos += 1
            else:
                out.append(data[pos])
                if pos + 3 <= n:
                    anchors.setdefault(bytes(data[pos:pos + 3]), []).append(pos)
                pos += 1
        out[flag_idx] = flags
    # pad to 4 bytes like the originals
    while len(out) % 4:
        out.append(0)
    return bytes(out)


if __name__ == "__main__":
    import os
    # roundtrip self-test
    for blob in (b"", b"a", b"hello hello hello hello", os.urandom(1000),
                 open(__file__, "rb").read() * 3):
        assert decompress(compress(blob)) == blob
    print("roundtrip OK")
