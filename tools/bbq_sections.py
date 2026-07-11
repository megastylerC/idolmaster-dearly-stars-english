import struct
import sys

d = open(sys.argv[1], "rb").read()
out = open(sys.argv[2], "w", encoding="utf-8")

out.write(f"file size: {len(d):#x}\n")
out.write(f"magic: {d[:8]}\n")
# dump first 0x100 as u32 list with offsets
for off in range(8, 0x100, 4):
    v = struct.unpack_from("<I", d, off)[0]
    out.write(f"{off:#06x}: {v:#010x} ({v})\n")

# hexdump around interesting offsets
for label, start in (("0xb860", 0xB860), ("0xbe50", 0xBE50), ("0xbee0", 0xBEE0)):
    out.write(f"\n--- {label} ---\n")
    for row in range(start, min(start + 0x100, len(d)), 16):
        chunk = d[row:row + 16]
        hexs = " ".join(f"{b:02x}" for b in chunk)
        asc = "".join(chr(b) if 0x20 <= b < 0x7F else "." for b in chunk)
        out.write(f"{row:#08x}  {hexs:<48}  {asc}\n")
out.close()
print("done")
