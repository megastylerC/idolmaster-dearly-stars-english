"""Count Shift-JIS Japanese text bytes per file across unpacked dirs + arm9."""
import os
import sys


def sjis_text_bytes(d):
    total = 0
    i = 0
    n = len(d)
    while i < n - 1:
        b1, b2 = d[i], d[i + 1]
        if (0x81 <= b1 <= 0x9F or 0xE0 <= b1 <= 0xEA) and (0x40 <= b2 <= 0xFC and b2 != 0x7F):
            # count only if part of a run of >= 3 SJIS chars
            j = i
            cnt = 0
            while j < n - 1:
                c1, c2 = d[j], d[j + 1]
                if (0x81 <= c1 <= 0x9F or 0xE0 <= c1 <= 0xEA) and (0x40 <= c2 <= 0xFC and c2 != 0x7F):
                    cnt += 1
                    j += 2
                elif c1 == 0x0A:
                    j += 1
                else:
                    break
            if cnt >= 3:
                total += (j - i)
            i = j if j > i else i + 1
        else:
            i += 1
    return total


results = []
for root in sys.argv[1:]:
    if os.path.isfile(root):
        d = open(root, "rb").read()
        results.append((sjis_text_bytes(d), root))
        continue
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn == "_manifest.txt":
                continue
            p = os.path.join(dirpath, fn)
            d = open(p, "rb").read()
            t = sjis_text_bytes(d)
            if t > 0:
                results.append((t, p))

results.sort(reverse=True)
print(f"{'JP bytes':>10}  file")
for t, p in results[:40]:
    print(f"{t:>10}  {p}")
print(f"\ntotal JP text bytes: {sum(t for t, _ in results)} across {len(results)} files")
