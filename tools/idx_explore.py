import struct
import sys

idx = open(sys.argv[1], "rb").read()
bin_ = open(sys.argv[2], "rb").read()

print("IDX magic:", idx[:4], "BIN magic:", bin_[:4])
print("IDX size:", len(idx), "BIN size:", len(bin_))
print("IDX hdr:", idx[:16].hex(" "))
print("BIN hdr:", bin_[:32].hex(" "))

n = struct.unpack_from("<I", idx, 12)[0]
print("entry count field @0xC:", n)
body = len(idx) - 16
print("IDX body bytes:", body, "-> /12 =", body / 12, " /8 =", body / 8, " /16 =", body / 16)

# assume 12-byte entries after 16-byte header
entries = []
for i in range(body // 12):
    a, b, c = struct.unpack_from("<III", idx, 16 + i * 12)
    entries.append((a, b, c))

print("\nfirst 8 entries (a, b, c):")
for e in entries[:8]:
    print(f"  {e[0]:#10x} {e[1]:#10x} {e[2]:#10x}")
print("last 4 entries:")
for e in entries[-4:]:
    print(f"  {e[0]:#10x} {e[1]:#10x} {e[2]:#10x}")

# hypothesis: c = offset, a = uncompressed size, compressed size = next c - c
offs = [e[2] for e in entries]
print("\noffsets monotonic:", all(offs[i] < offs[i + 1] for i in range(len(offs) - 1)))
print("max offset:", hex(offs[-1]), "vs BIN size", hex(len(bin_)))

# peek at data of a few entries, assuming data starts at BIN offset 0x20 + c? or 0x10 + c?
for base in (0x0, 0x10, 0x20):
    e = entries[40]
    print(f"\nbase {base:#x}: entry40 (a={e[0]:#x} b={e[1]:#x} c={e[2]:#x}) data:",
          bin_[base + e[2]: base + e[2] + 16].hex(" "))
