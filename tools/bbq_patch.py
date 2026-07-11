"""Rebuild a BBQ file's string pool with translated text from a JSON doc.

Strings with "en" set are replaced; others keep the Japanese original.
The offset table stays at the same file position (count is unchanged);
only the pool bytes, the pool-size header field, and file padding change.
"""
import json
import struct
import sys

from bbq_text import find_pool


def patch_bbq(d, translations):
    """d: original bytes; translations: {index: english}. Returns new bytes."""
    loc = find_pool(d)
    if loc is None:
        raise ValueError("no string pool")
    base, a_tbl, count, a_pool, psize = loc
    offs = struct.unpack_from(f"<{count}I", d, a_tbl)

    new_pool = bytearray()
    new_offs = []
    for i in range(count):
        end = d.index(b"\0", a_pool + offs[i])
        raw = d[a_pool + offs[i]:end]
        if i in translations:
            raw = translations[i].encode("cp932")
        new_offs.append(len(new_pool))
        new_pool += raw + b"\0"

    out = bytearray(d[:a_tbl])
    out += struct.pack(f"<{count}I", *new_offs)
    assert len(out) == a_pool
    out += new_pool
    # pad to 4-byte alignment plus the same slack the original had beyond the pool
    while len(out) % 4:
        out.append(0)
    # update pool-size field (base+16): header stores it relative to marker layout
    struct.pack_into("<I", out, base + 16, len(new_pool))
    return bytes(out)


if __name__ == "__main__":
    bbq_path, json_path, out_path = sys.argv[1:4]
    doc = json.load(open(json_path, encoding="utf-8"))
    tr = {l["i"]: l["en"] for l in doc["lines"] if l.get("en")}
    d = open(bbq_path, "rb").read()
    open(out_path, "wb").write(patch_bbq(d, tr))
    print(f"patched {len(tr)} strings -> {out_path}")
