# Contributing

Thanks for helping translate Dearly Stars! This guide covers the workflow and the house style. Please skim all of it once before your first pull request — a couple of the rules (Shift-JIS, one-entry-per-index) will save you from subtle breakage.

## Setup

You need **Python 3** and your own legally-dumped Japanese ROM (game code VIMJ, MD5 `93F3A6080CC43329EBD6F92E7ED1E7B1`). Nothing to `pip install` — the tools use only the standard library.

```bash
python tools/nds_extract.py "your_rom.nds"   # -> extracted/  (your game data, git-ignored)
python tools/ez_extract.py                    # -> unpacked/   (git-ignored)
```

`extracted/` and `unpacked/` are your own game files. They are git-ignored and must never be committed.

## Claiming work

To avoid two people translating the same scene, **open an Issue (or comment on the tracking issue) saying which file(s) you're taking** before you start. Good units of work:

- One story chapter's scenes, e.g. all of `ERI_D01_*`.
- One table, e.g. `LETTERTABLEAIH` (Ai's fan letters).

Chapters play in **idol-rank order F → E → D → C → B → A** (A is the finale, not the start). The three routes are `AIH` (Ai Hidaka), `ERI` (Eri Mizutani), `RYO` (Ryo Akizuki).

## The translation loop

1. **See the Japanese** next to the current English:
   ```bash
   python -X utf8 tools/show_jp.py F_SCN/ERI_D01_MAIN01_MES.BBQ --todo
   ```
   Output is `index <TAB> japanese <TAB> english`. `--todo` hides lines already done.

2. **Fill in the English.** Two ways:
   - **Edit the JSON directly:** set the `"en"` field for each line index in `translation/F_SCN/<file>.json`.
   - **Write an apply script** (nice for a whole scene at once): copy `tools/apply_eri_e03b.py`, replace the `{index: "english"}` dict, and run it with `python -X utf8`. The script validates length and encoding as it writes. This is the recommended approach for large scenes.

   For a scene, the dialogue is in `<name>_MES.BBQ` and the on-screen **choice buttons** are in the file of the same name **without** `_MES`.

3. **Build and verify:**
   ```bash
   python tools/build_rom.py "your_rom.nds" DearlyStars_EN_test.nds
   python -X utf8 tools/verify_rom.py DearlyStars_EN_test.nds   # expect: 0 mismatches
   ```

4. **Play-test** the scene in melonDS (NDS mode) if you can, then open a PR with your changed `translation/*.json`. Don't commit built ROMs, `extracted/`, or `unpacked/` (they're git-ignored).

## Rules that matter

### One English entry per string index — never shift the numbering
Each line index maps to exactly one string. If an English line is too long to fit on screen, **put a `\n` inside that single string** — do **not** push the overflow onto the next index. Splitting one Japanese line across two indices silently misaligns every line after it, and the build won't catch it (all indices still have text). When in doubt, re-run `show_jp.py` and confirm the Japanese and English still line up, especially at the end of the file.

### Shift-JIS (cp932) only
The game renders text as Shift-JIS. Characters outside cp932 will fail the build. In practice:
- ❌ No `—` (em dash U+2014), no curly quotes `“ ” ‘ ’`, no `é`/accents.
- ✅ Use straight quotes `" '`, and write "cafe" not "café".
- The sequence **`―㌍`** (a long dash `―` U+2015 followed by U+330D) is the game's built-in wide dash glyph. **Copy it verbatim** where the Japanese has it; don't replace it with `--` or `—`.

The apply-script template checks this for you and reports any offending line.

### Length limits
The game wraps at a fixed width and won't reflow. Keep each displayed line within the limit for its context (the template warns if you exceed it):

| Context | Limit (halfwidth chars) |
|---|---|
| Dialogue (`*_MES`) | ~38 |
| Mail bodies (`ML_*`, `*_MAIL*`) | ≤30 |
| Fan letters (`LETTERTABLE*`) | ≤22 |
| Dance-panel descriptions | ≤26 |
| Song info panel | ≤22 |
| Choice buttons | ~13, usually split with `\n` |

## House style & glossary

- Western name order: **Eri Mizutani**, **Ai Hidaka**, **Ryo Akizuki**.
- Keep Japanese honorifics: `-san`, `-chan`, `senpai`.
- `上手 / 下手` (stage directions) → **stage left / stage right** (performer's view).
- Canonical character-name romanizations live in the translated `CHARDETAILTABLE` (in `translation/F_TBL`) — match those.

Key characters and terms:

| Japanese | English | Notes |
|---|---|---|
| 絵理 | Eri | net-idol handle **ELLIE** |
| サイネリア | Cineria | quirky netspeak; calls Eri "senpai" |
| 尾崎 / 尾崎玲子 | Ms. Ozaki / Reiko Ozaki | freelance producer |
| 石川社長 | President Ishikawa | 876 Pro |
| 真美 (manager) | Manami Okamoto | the manager. NOTE: the Futami twin 真美 = **Mami**, a different person |
| 日高愛 | Ai Hidaka | loud, earnest |
| 秋月涼 | Ryo Akizuki | has a character reveal — mind the `僕`/"boku" speech; ask before translating Ryo scenes |
| 営業 | promo work | |
| 流行情報 / 流行イメージ | trend info / trend image | |
| イメージレベル | image level | |
| レッスン | lessons | |
| 思い出 | Memories | |

Mail openers: `社長の石川です` → "President Ishikawa here." · `尾崎です` → "Ozaki here." · `マネージャーの真美です` → "It's Manami, your manager."

Costume categories: **CUTE&GIRLY** / **COOL&SEXY** / **COSMIC&FUNNY** (raise Vocal / Dance / Visual respectively).

When unsure about a name or term, grep `translation/F_TBL` for how it was rendered elsewhere, or ask in your Issue/PR.

## What not to translate

- `*_LIP` tables (lip-sync timing) — never translate.
- `LESVOICETABLE*` (the fill-in minigame) — it renders via a kana-only tile font, so ASCII shows as blanks. Left Japanese until the font is redrawn (Phase 2).
- Menu/UI **graphics** (big buttons, screen headers, logos) — these are images, not text; Phase 2.

## Maintainer notes

Cutting a release patch (`.xdelta`) needs `xdelta3` (not committed; grab the official build and drop it in `tools/bin/`). Diff the built ROM against a **clean original**:

```bash
tools/bin/xdelta3 -e -9 -f -B 268435456 -s "original_jp.nds" DearlyStars_EN_test.nds release.xdelta
```
