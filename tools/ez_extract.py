"""Unpack EZT/EZP archive pairs (F_*.IDX + F_*.BIN) from Idolmaster Dearly Stars.

IDX: 16-byte header (magic 'EZT\0', date, entry count), then 12-byte entries:
     offset u32 | (flags<<24 | uncompressed size) u32 | name-table offset u32
     Last entry is a terminator whose offset == data end (start of name table).
BIN: 16-byte header (magic 'EZP\0', date, data-end offset), data blobs,
     then a null-padded filename table at data-end.
Flag 0x10 = NDS LZ77 compressed blob, 0x00 with size 0 = empty file.

Usage: python ez_extract.py <name.IDX> <name.BIN> <outdir> [--manifest manifest.txt]
"""
import os
import struct
import sys


def lz77_decompress(data):
    """Standard NDS LZ77 (type 0x10)."""
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


def unpack(idx_path, bin_path, outdir):
    idx = open(idx_path, "rb").read()
    bin_ = open(bin_path, "rb").read()
    assert idx[:4] == b"EZT\0" and bin_[:4] == b"EZP\0", "bad magic"
    data_end = struct.unpack_from("<I", bin_, 12)[0]
    names = bin_[data_end:]

    n = (len(idx) - 16) // 12
    entries = [struct.unpack_from("<III", idx, 16 + i * 12) for i in range(n)]

    os.makedirs(outdir, exist_ok=True)
    manifest = []
    files = 0
    for i, (off, szflags, name_off) in enumerate(entries):
        if i == n - 1:  # terminator
            break
        flags = szflags >> 24
        usize = szflags & 0xFFFFFF
        name = names[name_off:names.index(b"\0", name_off)].decode("shift_jis")
        next_off = entries[i + 1][0]
        raw = bin_[off:next_off]
        if szflags == 0:
            payload = b""
        elif flags == 0x10:
            payload = lz77_decompress(raw)
            assert len(payload) == usize, f"{name}: size mismatch"
        elif flags == 0x00:
            payload = raw[:usize]
        else:
            raise ValueError(f"{name}: unknown flags {flags:#x}")
        with open(os.path.join(outdir, name), "wb") as f:
            f.write(payload)
        manifest.append(f"{i}\t{name}\t{flags:#04x}\t{usize}")
        files += 1
    return files, manifest


def unpack_one(idx_path, bin_path, outdir):
    files, manifest = unpack(idx_path, bin_path, outdir)
    with open(os.path.join(outdir, "_manifest.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(manifest) + "\n")
    print(f"{os.path.basename(bin_path)}: {files} files -> {outdir}")


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        unpack_one(*sys.argv[1:4])
    elif len(sys.argv) == 1:
        # Default: unpack the two text archives from extracted/ into unpacked/
        # (run tools/nds_extract.py first).
        if not os.path.isdir(os.path.join("extracted", "data")):
            sys.exit("extracted/data not found - run: python tools/nds_extract.py <your_rom.nds>")
        for arc in ("F_SCN", "F_TBL"):
            unpack_one(
                os.path.join("extracted", "data", arc + ".IDX"),
                os.path.join("extracted", "data", arc + ".BIN"),
                os.path.join("unpacked", arc),
            )
    else:
        sys.exit(
            "usage: python tools/ez_extract.py                       # F_SCN + F_TBL from extracted/\n"
            "       python tools/ez_extract.py <IDX> <BIN> <outdir>  # one archive, explicit paths"
        )
