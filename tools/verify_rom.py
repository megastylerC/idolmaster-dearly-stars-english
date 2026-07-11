"""Verify a built ROM: every translated member decompresses and contains its English text."""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ez_extract import lz77_decompress
from bbq_text import extract_strings

rom = open(sys.argv[1], "rb").read()
fat_off, fat_size = struct.unpack_from("<II", rom, 0x48)
fnt_off = struct.unpack_from("<I", rom, 0x40)[0]


def find_file(target):
    def walk(dir_id, path):
        entry = fnt_off + (dir_id & 0xFFF) * 8
        pos = fnt_off + struct.unpack_from("<I", rom, entry)[0]
        fid = struct.unpack_from("<H", rom, entry + 4)[0]
        while True:
            tl = rom[pos]
            pos += 1
            if tl == 0:
                return None
            nm = rom[pos:pos + (tl & 0x7F)].decode("shift_jis")
            pos += tl & 0x7F
            if tl & 0x80:
                sub = struct.unpack_from("<H", rom, pos)[0]
                pos += 2
                r = walk(sub, path + "/" + nm)
                if r is not None:
                    return r
            else:
                if (path + "/" + nm).lstrip("/") == target:
                    s, e = struct.unpack_from("<II", rom, fat_off + fid * 8)
                    return rom[s:e]
                fid += 1
    return walk(0xF000, "")


checked = failed = 0
for arc in ("F_SCN", "F_TBL"):
    docs = {}
    for jp in glob.glob(os.path.join("translation", arc, "*.json")):
        doc = json.load(open(jp, encoding="utf-8"))
        tr = {l["i"]: l["en"] for l in doc["lines"] if l.get("en")}
        if tr:
            docs[os.path.basename(doc["file"].split("/", 1)[1])] = tr
    if not docs:
        continue
    idx = find_file(arc + ".IDX")
    bin_ = find_file(arc + ".BIN")
    data_end = struct.unpack_from("<I", bin_, 12)[0]
    names = bin_[data_end:]
    n = (len(idx) - 12) // 12
    for i in range(n - 1):
        off, sf, no = struct.unpack_from("<III", idx, 16 + i * 12)
        nm = names[no:names.index(b"\0", no)].decode("shift_jis")
        if nm not in docs:
            continue
        nxt = struct.unpack_from("<I", idx, 16 + (i + 1) * 12)[0]
        blob = lz77_decompress(bin_[off:nxt])
        assert len(blob) == sf & 0xFFFFFF, nm
        loc, strs = extract_strings(blob)
        for li, en in docs[nm].items():
            if strs[li] != en:
                print(f"MISMATCH {nm}[{li}]: {strs[li]!r} != {en!r}")
                failed += 1
        checked += 1

print(f"verified {checked} members, {failed} mismatches")
