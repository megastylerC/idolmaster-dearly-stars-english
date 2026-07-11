"""Count SJIS dialogue-bracket markers per file to locate the main script."""
import os
import sys

MARKERS = (b"\x81\x75", b"\x81\x76", b"\x81\x41", b"\x81\x42")  # 「 」 、 。

results = []
for root in sys.argv[1:]:
    targets = []
    if os.path.isfile(root):
        targets = [root]
    else:
        for dp, _, fs in os.walk(root):
            targets += [os.path.join(dp, f) for f in fs if f != "_manifest.txt"]
    for p in targets:
        d = open(p, "rb").read()
        score = sum(d.count(m) for m in MARKERS)
        if score >= 20:
            results.append((score, p))

results.sort(reverse=True)
for s, p in results[:50]:
    print(f"{s:>7}  {p}")
print(f"\n{len(results)} files with score>=20")
