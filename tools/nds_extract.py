"""Extract the filesystem (and ARM binaries/overlays) from a .nds ROM.

Usage: python tools/nds_extract.py <your_rom.nds> [outdir]
  outdir defaults to extracted/
"""
import os
import struct
import sys

if len(sys.argv) < 2:
    sys.exit("usage: python tools/nds_extract.py <your_rom.nds> [outdir=extracted]")
ROM = sys.argv[1]
OUT = sys.argv[2] if len(sys.argv) > 2 else "extracted"

with open(ROM, "rb") as f:
    rom = f.read()


def u32(off):
    return struct.unpack_from("<I", rom, off)[0]


def u16(off):
    return struct.unpack_from("<H", rom, off)[0]


game_title = rom[0:12].split(b"\0")[0].decode("ascii", "replace")
game_code = rom[12:16].decode("ascii", "replace")
print(f"Title: {game_title}  Code: {game_code}")

arm9_off, arm9_entry, arm9_ram, arm9_size = u32(0x20), u32(0x24), u32(0x28), u32(0x2C)
arm7_off, arm7_entry, arm7_ram, arm7_size = u32(0x30), u32(0x34), u32(0x38), u32(0x3C)
fnt_off, fnt_size = u32(0x40), u32(0x44)
fat_off, fat_size = u32(0x48), u32(0x4C)
ov9_off, ov9_size = u32(0x50), u32(0x54)
ov7_off, ov7_size = u32(0x58), u32(0x5C)

print(f"ARM9 @ {arm9_off:#x} size {arm9_size:#x} | ARM7 @ {arm7_off:#x} size {arm7_size:#x}")
print(f"FNT @ {fnt_off:#x} size {fnt_size:#x} | FAT @ {fat_off:#x} size {fat_size:#x} ({fat_size // 8} files)")

os.makedirs(OUT, exist_ok=True)
sysdir = os.path.join(OUT, "_system")
os.makedirs(sysdir, exist_ok=True)

with open(os.path.join(sysdir, "arm9.bin"), "wb") as f:
    f.write(rom[arm9_off:arm9_off + arm9_size])
with open(os.path.join(sysdir, "arm7.bin"), "wb") as f:
    f.write(rom[arm7_off:arm7_off + arm7_size])
with open(os.path.join(sysdir, "header.bin"), "wb") as f:
    f.write(rom[0:0x4000])
if ov9_size:
    with open(os.path.join(sysdir, "arm9_overlay_table.bin"), "wb") as f:
        f.write(rom[ov9_off:ov9_off + ov9_size])
if ov7_size:
    with open(os.path.join(sysdir, "arm7_overlay_table.bin"), "wb") as f:
        f.write(rom[ov7_off:ov7_off + ov7_size])

# FAT
fat = []
for i in range(fat_size // 8):
    start = u32(fat_off + i * 8)
    end = u32(fat_off + i * 8 + 4)
    fat.append((start, end))

# Overlay files come first in the FAT; note which file IDs are overlays
overlay_ids = set()
for tbl_off, tbl_size, name in ((ov9_off, ov9_size, "arm9"), (ov7_off, ov7_size, "arm7")):
    ovdir = os.path.join(sysdir, f"{name}_overlays")
    if tbl_size:
        os.makedirs(ovdir, exist_ok=True)
    for i in range(tbl_size // 32):
        e = tbl_off + i * 32
        ov_id = u32(e)
        file_id = u32(e + 0x18)
        overlay_ids.add(file_id)
        s, t = fat[file_id]
        with open(os.path.join(ovdir, f"overlay_{ov_id:04d}.bin"), "wb") as f:
            f.write(rom[s:t])

# FNT: walk directory tree
def walk(dir_id, path):
    entry = fnt_off + (dir_id & 0xFFF) * 8
    sub_off = fnt_off + u32(entry)
    file_id = u16(entry + 4)
    pos = sub_off
    while True:
        type_len = rom[pos]
        pos += 1
        if type_len == 0:
            break
        name_len = type_len & 0x7F
        name = rom[pos:pos + name_len].decode("shift_jis", "replace")
        pos += name_len
        if type_len & 0x80:
            sub_id = u16(pos)
            pos += 2
            walk(sub_id, path + "/" + name)
        else:
            s, t = fat[file_id]
            full = os.path.join(OUT, "data", *(path + "/" + name).strip("/").split("/"))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "wb") as f:
                f.write(rom[s:t])
            file_id += 1


walk(0xF000, "")

count = sum(len(fs) for _, _, fs in os.walk(os.path.join(OUT, "data")))
print(f"Extracted {count} files to {OUT}/data (+ system files in {OUT}/_system)")
