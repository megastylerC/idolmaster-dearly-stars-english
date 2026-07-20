"""Build a translated ROM.

1. For every translation/<ARC>/<file>.json with any "en" filled in,
   patch the BBQ string pool.
2. Rebuild the affected EZ archives (F_SCN.BIN/.IDX, F_TBL.BIN/.IDX),
   recompressing only changed members.  Graphics members edited via
   gld_import.py (patched/F_AGL/*.GLD) are picked up the same way.
3. Write a new .nds: original ROM with rebuilt archive files placed in the
   end-of-ROM padding, FAT entries retargeted, header CRC16 fixed.

Usage: python build_rom.py <original.nds> <output.nds>
"""
import glob
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
from bbq_patch import patch_bbq
from lz77 import compress
import blz
import blz_compress

ARCS = ("F_SCN", "F_TBL", "F_AGL")


def load_translations(arc):
    """{member filename: {index: en}} for members with any translation."""
    result = {}
    for jp in glob.glob(os.path.join("translation", arc, "*.json")):
        doc = json.load(open(jp, encoding="utf-8"))
        tr = {l["i"]: l["en"] for l in doc["lines"] if l.get("en")}
        if tr:
            member = os.path.basename(doc["file"].split("/", 1)[1])
            result[member] = tr
    return result


def rebuild_archive(idx_path, bin_path, replacements):
    """replacements: {name: new uncompressed bytes}. Returns (new_idx, new_bin)."""
    idx = open(idx_path, "rb").read()
    bin_ = open(bin_path, "rb").read()
    data_end = struct.unpack_from("<I", bin_, 12)[0]
    names_blob = bin_[data_end:]
    n = (len(idx) - 16) // 12
    entries = [struct.unpack_from("<III", idx, 16 + i * 12) for i in range(n)]

    def name_of(no):
        return names_blob[no:names_blob.index(b"\0", no)].decode("shift_jis")

    new_bin = bytearray(bin_[:16])
    new_idx = bytearray(idx[:16])
    replaced = 0
    for i, (off, szflags, name_off) in enumerate(entries[:-1]):
        name = name_of(name_off)
        cur_off = len(new_bin)
        if name in replacements:
            payload = replacements[name]
            comp = compress(payload)
            new_bin += comp
            szflags = (0x10 << 24) | len(payload)
            replaced += 1
        else:
            new_bin += bin_[off:entries[i + 1][0]]
        new_idx += struct.pack("<III", cur_off, szflags, name_off)
    # terminator + name table
    new_end = len(new_bin)
    new_idx += struct.pack("<III", new_end, 0, 0)
    new_bin += names_blob
    struct.pack_into("<I", new_bin, 12, new_end)
    assert replaced == len(replacements), f"missing members: {set(replacements) - {name_of(e[2]) for e in entries[:-1]}}"
    return bytes(new_idx), bytes(new_bin)


def crc16(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def build(rom_path, out_path):
    rom = bytearray(open(rom_path, "rb").read())
    fnt_off = struct.unpack_from("<I", rom, 0x40)[0]
    fat_off, fat_size = struct.unpack_from("<II", rom, 0x48)
    used = struct.unpack_from("<I", rom, 0x80)[0]

    # Captured before anything is patched: the header must come out of this
    # build byte-identical (see the relayout note at the end of build()).
    orig_head = bytes(rom[:0x15E])
    orig_starts = [struct.unpack_from("<I", rom, fat_off + i * 8)[0]
                   for i in range(fat_size // 8)]

    # File data must be packed above EVERY system structure, and they are not
    # contiguous on this cart: the overlay files sit at 0x89A00, below ARM7 /
    # FNT / FAT / banner.  (Using min(orig_starts) here overwrote the FAT and
    # banner with file data.)  The header is frozen, so all of these keep their
    # original offsets and we simply start after the highest one.
    _BANNER_SIZE = {1: 0x840, 2: 0x940, 3: 0xA00, 0x103: 0x23C0}
    banner_off = struct.unpack_from("<I", rom, 0x68)[0]
    banner_ver = struct.unpack_from("<H", rom, banner_off)[0]
    sys_end = max(
        struct.unpack_from("<I", rom, 0x20)[0] + struct.unpack_from("<I", rom, 0x2C)[0],
        struct.unpack_from("<I", rom, 0x50)[0] + struct.unpack_from("<I", rom, 0x54)[0],
        struct.unpack_from("<I", rom, 0x30)[0] + struct.unpack_from("<I", rom, 0x3C)[0],
        fnt_off + struct.unpack_from("<I", rom, 0x44)[0],
        fat_off + fat_size,
        banner_off + _BANNER_SIZE.get(banner_ver, 0x23C0),
    )
    data_start = (sys_end + 0x1FF) & ~0x1FF

    # map filename -> FAT file id by walking FNT root (files are in root's tree;
    # we only need top-level names like F_SCN.BIN)
    def find_file_id(target):
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
                        return fid
                    fid += 1
        return walk(0xF000, "")

    append_at = (used + 0x1FF) & ~0x1FF
    for arc in ARCS:
        repl = {}
        for member, tr in load_translations(arc).items():
            orig = open(os.path.join("unpacked", arc, member), "rb").read()
            repl[member] = patch_bbq(orig, tr)
        # binary members patched outside the BBQ pipeline (edited graphics)
        for p in glob.glob(os.path.join("patched", arc, "*")):
            repl[os.path.basename(p)] = open(p, "rb").read()
        if not repl:
            continue
        print(f"{arc}: {len(repl)} member(s) patched")
        new_idx, new_bin = rebuild_archive(
            os.path.join("extracted", "data", f"{arc}.IDX"),
            os.path.join("extracted", "data", f"{arc}.BIN"),
            repl,
        )
        for suffix, blob in ((".IDX", new_idx), (".BIN", new_bin)):
            fid = find_file_id(arc + suffix)
            assert fid is not None, arc + suffix
            start, end = struct.unpack_from("<II", rom, fat_off + fid * 8)
            if len(blob) <= end - start:
                rom[start:start + len(blob)] = blob
                struct.pack_into("<II", rom, fat_off + fid * 8, start, start + len(blob))
                print(f"  {arc}{suffix}: in place @{start:#x} ({len(blob)} bytes)")
            else:
                assert append_at + len(blob) <= len(rom), "no padding space left"
                rom[append_at:append_at + len(blob)] = blob
                struct.pack_into("<II", rom, fat_off + fid * 8, append_at, append_at + len(blob))
                print(f"  {arc}{suffix}: relocated @{append_at:#x} ({len(blob)} bytes)")
                append_at = (append_at + len(blob) + 0x1FF) & ~0x1FF

    # Overlay UI text (translation/overlays/overlay_NNNN.json): patch strings
    # in place in the decompressed image, then store the overlay UNCOMPRESSED
    # (relocated to padding) and clear the compressed flag in the overlay
    # table so the loader copies it as-is. EN must fit the JP byte length.
    ovt_off, ovt_size = struct.unpack_from("<II", rom, 0x50)
    for jp_path in sorted(glob.glob(os.path.join("translation", "overlays", "*.json"))):
        doc = json.load(open(jp_path, encoding="utf-8"))
        ov_id = doc["overlay"]
        entry = None
        for e_off in range(ovt_off, ovt_off + ovt_size, 32):
            if struct.unpack_from("<I", rom, e_off)[0] == ov_id:
                entry = e_off
                break
        assert entry is not None, f"overlay {ov_id} not in table"
        ram_size, file_id, comp_word = (struct.unpack_from("<I", rom, entry + 8)[0],
                                        struct.unpack_from("<I", rom, entry + 24)[0],
                                        struct.unpack_from("<I", rom, entry + 28)[0])
        ov_file = os.path.join("extracted", "_system", "arm9_overlays", f"overlay_{ov_id:04d}.bin")
        raw = open(ov_file, "rb").read()
        dec = bytearray(blz.decompress(raw) if blz.is_blz(raw) else raw)
        patched = 0
        for s in doc["strings"]:
            off = s["off"]
            # Length of the original NUL-terminated run at off. jp (when present)
            # is an optional integrity check; the repo ships en-only, so the
            # build must not depend on it.
            run_len = dec.index(b"\0", off) - off
            en_b = s["en"].encode("cp932")
            if "jp" in s:
                assert dec[off:off + run_len] == s["jp"].encode("cp932"), f"ov{ov_id} @{off:#x}: jp mismatch"
            assert len(en_b) <= run_len, f"ov{ov_id} @{off:#x}: en too long"
            dec[off:off + run_len] = en_b + b"\0" * (run_len - len(en_b))
            patched += 1
        if ram_size != len(dec):
            print(f"  warning: ov{ov_id} ramSize {ram_size:#x} != decompressed {len(dec):#x}")
        assert append_at + len(dec) <= len(rom), "no padding space left for overlay"
        rom[append_at:append_at + len(dec)] = dec
        struct.pack_into("<II", rom, fat_off + file_id * 8, append_at, append_at + len(dec))
        # clear compressed flag (bit0 of flags byte), zero compressed size
        struct.pack_into("<I", rom, entry + 28, (comp_word >> 24 & ~1) << 24)
        print(f"overlay_{ov_id:04d}: {patched} string(s) patched, stored uncompressed "
              f"@{append_at:#x} ({len(dec)} bytes)")
        append_at = (append_at + len(dec) + 0x1FF) & ~0x1FF

    # ARM9 system text (translation/arm9/arm9.json): patch strings in the
    # decompressed image, then BLZ-recompress to EXACTLY the original file size
    # and write it back in place at ROM 0x4000.
    #
    # The ARM9 must stay at 0x4000: that is where the cart secure area lives,
    # and real hardware (and flashcart loaders) boot through the secure-area
    # path, which emulators skip.  An earlier version of this tool stored the
    # ARM9 decompressed at the end of the ROM, which booted in DeSmuME/melonDS
    # but not on a DS - the header still advertised a secure area at 0x4000
    # while the ARM9 lived elsewhere.
    #
    # Hitting the original size exactly is what keeps this safe:
    #   * BLZ stores the first 0x4000 bytes raw, and that prefix IS the secure
    #     area, so it stays byte-identical (secure-area CRC 0x6C still valid).
    #   * The ModuleParams compressed-end u32 (8 bytes before the nitrocode
    #     magic) encodes ram_addr + compressed_size and itself lives inside
    #     that raw prefix - so an identical size means we never have to touch
    #     it, and the secure area really is untouched.
    #   * Header 0x20 / 0x2C / 0x6C all keep their original values.
    a9_json = os.path.join("translation", "arm9", "arm9.json")
    if os.path.exists(a9_json):
        doc = json.load(open(a9_json, encoding="utf-8"))
        raw = open(os.path.join("extracted", "_system", "arm9.bin"), "rb").read()
        orig_dec = blz.decompress(raw)
        dec = bytearray(orig_dec)
        ram_addr = struct.unpack_from("<I", rom, 0x28)[0]
        magic = dec.find(b"\x21\x06\xC0\xDE\xDE\xC0\x06\x21")
        assert magic > 8, "nitrocode magic not found in arm9"
        ce_val = struct.unpack_from("<I", dec, magic - 8)[0]
        assert ce_val == ram_addr + len(raw), \
            f"ModuleParams compressed-end {ce_val:#x} != ram+compsize {ram_addr + len(raw):#x}"
        for s in doc["strings"]:
            off = s["off"]
            run_len = dec.index(b"\0", off) - off
            en_b = s["en"].encode("cp932")
            if "jp" in s:
                assert dec[off:off + run_len] == s["jp"].encode("cp932"), f"arm9 @{off:#x}: jp mismatch"
            assert len(en_b) <= run_len, f"arm9 @{off:#x}: en too long"
            dec[off:off + run_len] = en_b + b"\0" * (run_len - len(en_b))
        dec = bytes(dec)
        assert len(dec) == len(orig_dec), "arm9 decompressed size must not change"
        first_change = next(i for i in range(len(dec)) if dec[i] != orig_dec[i])
        assert first_change >= 0x4000, "arm9 patch reaches into the secure area"
        # recompress_tail asserts its own round-trip before returning
        new_a9 = blz_compress.recompress_tail(dec, raw, 0x4000, first_change,
                                              pad_to=len(raw))
        assert struct.unpack_from("<I", rom, 0x20)[0] == 0x4000
        assert struct.unpack_from("<I", rom, 0x2C)[0] == len(new_a9)
        assert new_a9[:0x4000] == bytes(rom[0x4000:0x8000]), "secure area changed"
        rom[0x4000:0x4000 + len(new_a9)] = new_a9
        print(f"arm9: {len(doc['strings'])} string(s) patched, BLZ-recompressed "
              f"in place @0x4000 ({len(new_a9)} bytes, secure area intact)")

    # --- Compact relayout -------------------------------------------------
    # Everything above parks grown files in the end padding, which requires
    # widening used_size (0x80) and the NTR region limits (0x90/0x92) so the
    # data is inside the declared cart.  That works on emulators and FAILS on
    # real hardware, for two independent reasons found by bisecting on an R4:
    #
    #   1. The flashcart kernel identifies the cart by the header CRC16 at
    #      0x15E, using it as a database key - not as an integrity check.  Any
    #      value but the original is an unknown cart and it refuses to load
    #      ("errcode=-4"), even though the CRC is correctly recomputed.  So the
    #      first 0x15E bytes must stay byte-identical, which rules out touching
    #      0x80 / 0x90 / 0x92 at all.
    #   2. With the original (narrow) limits, reads past the boundary return
    #      garbage, so data parked in the padding is simply unreachable.
    #
    # Both point the same way: pack every file sequentially so it genuinely
    # lives below the original boundary, and leave the header alone.  Only
    # bytes 0x000-0x15D feed the CRC, so the overlay table (0x89800), ARM9,
    # FNT, FAT and file data are all still fair game.
    n_files = fat_size // 8
    blobs = []
    for i in range(n_files):
        s, e = struct.unpack_from("<II", rom, fat_off + i * 8)
        blobs.append((orig_starts[i], i, bytes(rom[s:e])))
    blobs.sort()                      # keep the original on-cart file ordering

    out = bytearray(b"\xFF" * len(rom))
    out[:data_start] = rom[:data_start]   # header, ARM9, overlay table, ARM7,
    pos = data_start                      # FNT, FAT, banner all stay put
    for _, fid, blob in blobs:
        struct.pack_into("<II", out, fat_off + fid * 8, pos, pos + len(blob))
        out[pos:pos + len(blob)] = blob
        pos = (pos + len(blob) + 0x1FF) & ~0x1FF

    assert pos <= used, f"relayout needs {pos:#x} > original used_size {used:#x}"
    assert out[:0x15E] == orig_head, "header changed - flashcart will reject it"
    assert struct.unpack_from("<H", out, 0x15E)[0] == crc16(out[:0x15E])

    # Read every file back through the new FAT and compare.  An earlier version
    # packed data over the top of the FAT and banner; nothing caught it until a
    # manual dump.  Verify the layout instead of trusting it.
    for _, fid, blob in blobs:
        s, e = struct.unpack_from("<II", out, fat_off + fid * 8)
        assert s >= data_start, f"file {fid} at {s:#x} overlaps the system area"
        assert e <= pos and e - s == len(blob), f"file {fid} FAT entry is wrong"
        assert bytes(out[s:e]) == blob, f"file {fid} content mismatch after relayout"
    for name, off, size in (("arm9", 0x20, 0x2C), ("arm7", 0x30, 0x3C)):
        a = struct.unpack_from("<I", out, off)[0]
        ln = struct.unpack_from("<I", out, size)[0]
        assert bytes(out[a:a + ln]) == bytes(rom[a:a + ln]), f"{name} was clobbered"
    assert bytes(out[fnt_off:fnt_off + struct.unpack_from("<I", out, 0x44)[0]]) == \
        bytes(rom[fnt_off:fnt_off + struct.unpack_from("<I", rom, 0x44)[0]]), "FNT clobbered"
    assert bytes(out[banner_off:banner_off + 0x840]) == \
        bytes(rom[banner_off:banner_off + 0x840]), "banner clobbered"
    print(f"relayout: {n_files} files packed into {pos:#x} "
          f"({pos / 1048576:.1f} MB), original limit {used:#x} "
          f"({used / 1048576:.1f} MB), header untouched")

    open(out_path, "wb").write(out)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
