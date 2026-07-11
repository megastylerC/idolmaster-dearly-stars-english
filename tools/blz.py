# -*- coding: utf-8 -*-
"""Nitro BLZ ("bottom LZ") codec used for NDS arm9 binaries and overlays.

Compressed images end with an 8-byte footer:
  u32 compInfo   = (headerLen << 24) | compressedDataLen
  u32 extraSize  = decompressedLen - fileLen
Decompression runs backward from the end of the file.
"""
import struct


def is_blz(data):
    if len(data) < 8:
        return False
    comp_info, extra = struct.unpack_from("<II", data, len(data) - 8)
    header_len = comp_info >> 24
    comp_len = comp_info & 0xFFFFFF
    if header_len < 8 or header_len > 0x20 or extra == 0:
        return False
    return comp_len <= len(data)


def decompress(data):
    """Decompress a BLZ image (whole file, e.g. arm9.bin). Returns bytes."""
    comp_info, extra = struct.unpack_from("<II", data, len(data) - 8)
    header_len = comp_info >> 24
    comp_len = comp_info & 0xFFFFFF
    if header_len == 0:
        return data  # stored
    out_len = len(data) + extra
    # region [len-comp_len, len-header_len) is compressed, read backward
    src = bytearray(data[len(data) - comp_len:len(data) - header_len])
    out = bytearray(out_len - (len(data) - comp_len))
    src_pos = len(src)
    out_pos = len(out)
    while out_pos > 0 and src_pos > 0:
        src_pos -= 1
        flags = src[src_pos]
        for bit in range(8):
            if out_pos <= 0 or src_pos <= 0:
                break
            if flags & (0x80 >> bit):
                # two info bytes are read walking backward: high byte sits at
                # the higher address
                src_pos -= 2
                info = (src[src_pos + 1] << 8) | src[src_pos]
                length = (info >> 12) + 3
                disp = (info & 0xFFF) + 3
                for _ in range(length):
                    out_pos -= 1
                    out[out_pos] = out[out_pos + disp] if out_pos + disp < len(out) else 0
            else:
                src_pos -= 1
                out_pos -= 1
                out[out_pos] = src[src_pos]
    return data[:len(data) - comp_len] + bytes(out)


if __name__ == "__main__":
    import sys
    raw = open(sys.argv[1], "rb").read()
    print("is_blz:", is_blz(raw))
    if is_blz(raw):
        dec = decompress(raw)
        print("decompressed", len(raw), "->", len(dec))
        if len(sys.argv) > 2:
            open(sys.argv[2], "wb").write(dec)
