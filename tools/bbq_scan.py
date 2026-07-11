import sys

d = open(sys.argv[1], "rb").read()
out = open(sys.argv[2], "w", encoding="utf-8")

runs = []
i = 0
while i < len(d) - 1:
    start = i
    s = bytearray()
    while i < len(d) - 1:
        b1, b2 = d[i], d[i + 1]
        if (0x81 <= b1 <= 0x9F or 0xE0 <= b1 <= 0xEF) and (0x40 <= b2 <= 0xFC and b2 != 0x7F):
            s += bytes([b1, b2])
            i += 2
        elif 0x20 <= b1 < 0x7F:
            s.append(b1)
            i += 1
        else:
            break
    if len(s) >= 6:
        try:
            t = s.decode("shift_jis")
            if any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" for c in t):
                runs.append((start, len(s), t))
        except UnicodeDecodeError:
            pass
    i = max(i, start + 1)

out.write(f"text runs: {len(runs)}\n")
for off, ln, t in runs:
    out.write(f"{off:#08x} len={ln}  {t}\n")
out.close()
print(f"{len(runs)} runs written")
