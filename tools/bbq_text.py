"""Locate and extract the string pool of a .BBQ file.

Header tail contains: ..., 7, tblOff, count, poolOff, poolSize, ...
where tblOff/poolOff are relative to the file position of the '7' marker
(verified: tblOff + count*4 == poolOff always; pool is at end of file).
The string offset table holds u32 offsets into the pool; strings are
null-terminated Shift-JIS with 0x0A newlines.
"""
import struct
import sys


def find_pool(d):
    """Return (marker_base, tbl_off, count, pool_off, pool_size) absolute, or None."""
    size = len(d)
    for base in range(0x18, min(0x200, size - 20), 4):
        if struct.unpack_from("<I", d, base)[0] != 7:
            continue
        tbl, count, pool, psize = struct.unpack_from("<IIII", d, base + 4)
        if count == 0 or count > 100000 or psize == 0:
            continue
        if tbl + count * 4 != pool:
            continue
        a_tbl, a_pool = base + tbl, base + pool
        if a_pool + psize > size or size - (a_pool + psize) > 0x40:
            continue
        # validate: offsets monotonic non-decreasing, in range
        offs = list(struct.unpack_from(f"<{count}I", d, a_tbl))
        if any(o > psize for o in offs):
            continue
        if any(offs[i] > offs[i + 1] for i in range(count - 1)):
            continue
        return base, a_tbl, count, a_pool, psize
    return None


def extract_strings(d):
    loc = find_pool(d)
    if loc is None:
        return None
    base, a_tbl, count, a_pool, psize = loc
    offs = struct.unpack_from(f"<{count}I", d, a_tbl)
    out = []
    for o in offs:
        end = d.index(b"\0", a_pool + o)
        out.append(d[a_pool + o:end].decode("cp932", "backslashreplace"))
    return loc, out


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read()
    res = extract_strings(d)
    out = open(sys.argv[2], "w", encoding="utf-8") if len(sys.argv) > 2 else sys.stdout
    if res is None:
        print("no string pool found", file=out)
    else:
        (base, a_tbl, count, a_pool, psize), strs = res
        print(f"marker@{base:#x} tbl@{a_tbl:#x} count={count} pool@{a_pool:#x} size={psize:#x}", file=out)
        for i, s in enumerate(strs):
            print(f"[{i}] {s!r}", file=out)
