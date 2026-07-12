# THE iDOLM@STER: Dearly Stars — English Translation

A work-in-progress English fan translation of **THE iDOLM@STER: Dearly Stars** (Nintendo DS, Japan, game code VIMJ).

This repository holds the **translation data and the tools** that turn it into a patch. It contains **no game ROM and no Japanese game text** — you bring your own legally-dumped Japanese cartridge, and the tools read the original text from it locally.

- **Players:** grab the latest patch from the [Releases page](../../releases/latest) and apply it to your own ROM. See [How to apply the patch](#how-to-apply-the-patch).
- **Translators / contributors:** see [CONTRIBUTING.md](CONTRIBUTING.md) for the full workflow and house style. A short version is [below](#contributing-quick-start).

## Translation status

| Area | Status |
|---|---|
| System UI (menus, save/load, mail, lessons, auditions, stage editor, Wi-Fi/Wireless, errors) | ✅ Complete |
| Eri Mizutani — opening + chapters F & E (story, side scenes, auditions, story mails) + recurring scenes | ✅ Complete |
| Tables (episode titles, songs, costumes, accessories, dance panels, fan letters, system mails) | ✅ Complete |
| Menu/UI graphics — title & story menus, common buttons, PDA management UI, status screens, result banners (redrawn art) | ✅ Complete |
| Vocal-lesson minigame — kana tiles redrawn as romaji, fully playable | ✅ Complete |
| Eri — chapters D through A | ⬜ Not started |
| Ai Hidaka route | ⬜ Not started |
| Ryo Akizuki route | ⬜ Not started |
| Remaining graphics (stage-editor UI, wireless labels, episode-title & song logos) | ⬜ Phase 2 (ongoing) |

## How it works

The game stores its text in a few different places, and the build patches all of them from one folder of JSON files:

1. **Story & table text** lives in `.BBQ` bytecode files packed inside `EZT`/`EZP` archive pairs (`F_SCN`, `F_TBL`). Each file's string pool is dumped to `translation/<ARC>/<file>.json` as a list of indexed lines; you fill in the English.
2. **System UI text** lives in the BLZ-compressed ARM9 binary and its overlays. Those strings are patched in place (English must fit the original byte length) and stored decompressed.
3. **UI graphics** (menu buttons, screen headers, minigame tiles) are images in `.GLD` texture files inside the `F_AGL` archive. `tools/gld_export.py` dumps them to PNG, the `tools/apply_gfx_*.py` scripts render the English art, and `tools/gld_import.py` re-encodes it (quantized to each image's original palette). Rendered from your own extracted files at build time — no game art is stored in this repo.
4. `build_rom.py` rebuilds the archives, patches the binaries, relocates the changed data into the ROM's end padding, fixes the file table and header, and writes a new `.nds`.
5. `verify_rom.py` reads every translated string back out of the built ROM to confirm a clean round-trip.

The English text renders natively — the game's fonts already include full ASCII. Full technical details are in [docs/FORMATS.md](docs/FORMATS.md).

## Repository layout

```
translation/        English text, keyed by string index (NO Japanese — see below)
  F_SCN/            story scenes (dialogue = *_MES.BBQ, choice buttons = same name w/o _MES)
  F_TBL/            tables + story-mail bodies
  overlays/         system-UI overlay strings (by byte offset)
  arm9/             ARM9 system strings (by byte offset)
tools/              the extraction / build / verify pipeline (Python 3)
docs/FORMATS.md     reverse-engineered file formats
CONTRIBUTING.md     translator workflow + house style + glossary
```

### Why there's no Japanese in here

The `translation/*.json` files contain only the **English** (`"en"`) for each line, keyed by index/offset. The original Japanese is the game's copyrighted script, so it is **not** stored here. While translating you view the Japanese live from your own ROM with `tools/show_jp.py` (below). The build never needs the Japanese, so the English-only data produces a byte-identical ROM.

## Contributing quick start

You need **Python 3** and your own dump of the Japanese ROM.

```bash
# 1. Verify your ROM, then unpack it locally (creates extracted/ and unpacked/,
#    both git-ignored — this is your own game data, never committed).
python tools/nds_extract.py "your_dearly_stars_jp.nds"
python tools/ez_extract.py

# 2. Pick a file to work on and see the Japanese next to the current English.
#    --todo shows only lines still needing translation.
python -X utf8 tools/show_jp.py F_SCN/ERI_D01_MAIN01_MES.BBQ --todo

# 3. Fill in the "en" fields in translation/F_SCN/ERI_D01_MAIN01_MES.BBQ.json
#    (or write an apply script — see tools/apply_eri_e03b.py for the pattern).

# 4. (optional) render the English UI graphics too — needs Pillow, and
#    Arial Bold at C:/Windows/Fonts (edit FONT in apply_gfx_batch1.py on
#    other platforms). Skip this if you're only translating text.
python -X utf8 tools/apply_gfx_batch1.py
python -X utf8 tools/apply_gfx_batch2.py
python -X utf8 tools/apply_gfx_batch3.py
python -X utf8 tools/apply_gfx_lesson_tiles.py
python -X utf8 tools/gld_import.py

# 5. Build and verify.
python tools/build_rom.py "your_dearly_stars_jp.nds" DearlyStars_EN_test.nds
python -X utf8 tools/verify_rom.py DearlyStars_EN_test.nds   # expect 0 mismatches

# 6. Open a pull request with your changed translation/*.json.
```

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before starting — it covers claiming files (so two people don't collide), the character-name glossary, line-length limits, the Shift-JIS character constraints, and a common pitfall (keeping one English entry per string index).

## How to apply the patch

You need your own dump of the Japanese ROM. Verify it first:
  - MD5: `93F3A6080CC43329EBD6F92E7ED1E7B1`
  - SHA-1: `5AC0A9F9BC3CB5A1E2AF04C1F9F5A954D3617908`

Easiest (any OS, in your browser):
1. Open [RomPatcher.js](https://www.marcrobledo.com/RomPatcher.js/)
2. ROM file: select your Japanese `.nds`
3. Patch file: select the `.xdelta` from the latest release
4. Press **Apply patch** and save the result.

Desktop alternatives: xdelta UI, Delta Patcher.

## How to play

- Use a DS emulator in **NDS mode** — [melonDS](https://melonds.kuribo64.net/) is recommended (this patch is tested on it). DeSmuME also works.
- **DSi mode will not boot** (DSi security hashes are not fixed). Run it as a normal DS game.
- **Save with the in-game save feature only.** Emulator savestates break between patch versions; in-game saves carry over fine.
- When updating to a new patch version, always apply it to a **clean copy of the original ROM**, not a previously patched one.

## Reporting problems

Open an [Issue](../../issues) with a **screenshot** and where you were in the game. Most useful:

- Japanese text in an area marked ✅ above
- Text overflowing its box, cut off, or garbled characters
- Freezes or crashes (mention your emulator and whether a savestate was involved)
- Awkward or unclear English

## Credits

This translation is being made with the help of [Claude Code](https://claude.com/claude-code) (Anthropic) — reverse engineering, translation, and tooling.

## Legal

This is a non-commercial fan project, unaffiliated with Bandai Namco. THE iDOLM@STER and all related characters are property of Bandai Namco Entertainment. No copyrighted game data is distributed here — the tools and the English translation only, requiring an original copy of the game to use.

The tools and English translation text are released under the [MIT License](LICENSE).
