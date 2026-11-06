# Development

## Building from source

You need Python 3.10 or newer on Windows. The `bin/` folder needs three files that are not in the repository:

- `libspeex-1.dll` from the MSYS2 package `mingw-w64-x86_64-speex`
- `7z.exe` and `7z.dll` from a 7-Zip installation

Then:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

The program ends up in `dist/DubPolice.exe`. To run without a window:

```bash
python src/launcher.py --engine --game "<remaster folder>" --source "<old version>" --language french --episodes 101 102
```

```bash
python src/launcher.py --engine --game "<remaster folder>" --uninstall
```

`--language` is `german` (default) or `french`. `--no-deess` keeps the S sounds in German as recorded.

Game data never belongs in the repository, and `.gitignore` excludes it.

## Code layout

| Path | Content |
|---|---|
| `src/launcher.py` | Entry point of the exe: window or conversion |
| `src/gui.py` | Backend of the window: finding Steam games, choosing folders, starting and following a conversion |
| `src/ui/` | The window: HTML, CSS, JavaScript, fonts, background |
| `src/sammax_de.py` | The conversion: find sources, match lines, convert, install |
| `src/old_archive.py`, `src/ttarch4.py` | Reading the old archives |
| `src/ectt.py`, `src/nctt.py` | Reading the remaster's archives |
| `src/vox2wav.py` | Decoding old recordings |
| `src/enhance.py` | Sound clean-up, de-esser, MP3 inside FSB5 |
| `src/anm_patch.py` | Stretching lip files |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Timing of scenes |
| `src/keys.py` | Decryption keys for the game archives, from TTG Tools |
| `assets/` | The logo as SVG and ICO |

## How it works

1. Find the archives of each episode in the old version, and unpack them from the installer on a disc.
2. Match every remaster line to an old recording.
3. Decode the recording, clean up the sound and pack it as FSB5.
4. Fit lip files and scenes (chores) to the new length.
5. Write one archive and one control file per episode to `Archives`.

### Adding a language

The process depends only on the length and matching of recordings. A new language needs an entry in `SEASONS[...]["languages"]`, its name in `SOURCE_FOLDERS` in `gui.py`, its texts and tab in `fallakte.js`, the old version and a test. An episode holds one language at a time, with files named `*_{Language}Dub_*`. Italian and Spanish on the Season 2 disc have only subtitles and the English voices.

## Archives

| Format | Marker | Used by | Encryption |
|---|---|---|---|
| `.ttarch` version 2 | Number 2 at the start | Season 1 (2007), German and French | Blowfish table; metadata per block: every 32nd Blowfish, every 80th plain, the rest inverted |
| `.ttarch` without version | Table size at the start | Season 1, English disc (not supported) | as version 2 |
| `.ttarch` version 4 | Number 4 at the start | Season 2 (2009) | Blowfish table; zlib blocks |
| `.ttarch` version 9 | Number 9 at the start | Season 3 (2010) | Telltale's Blowfish variant; table and blocks partly compressed |
| `.ttarch2` | `ECTT` | Remaster, compressed | Telltale's Blowfish variant, then Deflate in 64 KB blocks |
| `.ttarch2` | `NCTT` | Remaster, raw | none |

In an `NCTT` archive, `4ATT` is followed by the size of the name table, the file count and 28 bytes per file: CRC64 of the lowercase name (ECMA-182), offset, size, 0, name block, name offset. Entries are sorted by CRC64, and the name table is padded to 64 KB.

Each old episode has its own key. Each remaster has one shared key.

## Loading archives

The game runs `_resdesc_*.lua` from the `Archives` folder at startup.

- **Control files must be encrypted** (`ESC LEo`). Unencrypted ones were ignored in testing.
- File names repeat between episodes, so an archive that is always active would overwrite other episodes.
- **Solution:** a second description of the episode's group with `descriptionPriority = 100`, listing the new archive first. It is derived from the episode's original control file.

The list of installed files is kept in `SamMax_GermanDub.json` in the game folder, whatever the language.

## Voices

- **2009 and 2010:** `.vox` with Speex at 32 kHz. Head `ERTM`, 20 bytes. The first packet is a comment, not sound.
- **2007:** Single `.vox` files next to the archive, head `NIBM`, 31 bytes. Every 64th packet is encrypted with the episode's key, starting with the comment packet. Without decryption, the decoder loses 20 ms of sound every 1.28 s. These folders hold no English recordings, but do hold the English texts.
- **Remaster:** `.wav` entries that are really FSB5 with Vorbis at about 8.4 kB/s.
- **Output:** FSB5 with MP3 (mode 11), 44.1 kHz, mono, 128 kbit/s. Each MP3 frame must be padded to 4 bytes, or FMOD decodes only the first frames. The encoder delays the sound by 1,105 samples (25 ms). The sample count in the head is `frames × 1152`, so line blocks include the delay.

### Sound clean-up (`src/enhance.py`)

Measured on 40 lines from Episode 301, the old recordings are close to the remaster in level and balance. The treatment is therefore gentle, and nothing is synthesised:

1. **Resolution:** resample to 44.1 kHz.
2. **Equaliser:** remove rumble below 70 Hz, about 2.5 dB of presence around 3 kHz and at 14 to 16 kHz.
3. **De-esser (German only, can be switched off):** 4.5 to 12 kHz is lowered only while its level is above a threshold 14 dB below the speech level; ratio 4:1, 10 dB at most. Below that band the level changes by 0.03 dB at most. The sharpness comes from the old recordings, not from the equaliser.
4. **Air:** a trace of the voice's own sibilance above 16 kHz, where the old recordings have nothing.
5. **Level:** +0.5 dB, with only rare peaks softly limited.

## Matching lines

`english.langdb` or `*_english.landb` link number, speaker and text. In Season 3, the numbers of the old version and the remaster are mostly the same. Otherwise lines are matched in this order:

1. **exact:** normalised text is unique
2. **same text:** several matches, then same speaker and closest length
3. **close:** text similarity of 0.92 or more, such as corrected typos

The results of each run are written to the work folder as `epNNN_lines.csv`.

**Borrowed recordings:** a language entry has two CRC64 fields for `.anm` and `.wav` after its number and hash. If they are set, it points to another line's recording; otherwise its own number applies. Such entries have no file of their own, but their chores still need the new length, or the sentence stops at the English length. In Seasons 2 and 3 this affected about 640 chores, mostly conversations and interactions.

## Lip files (`.anm`)

The length is a float at `20 + 12 × types + 16`. Times are in lists of `size, count` with 37-byte entries. Both are stretched proportionally.

## Chores (`.chore`)

- **Time blocks:** `start, end, loop char, scale` (13 bytes).
- **Keyframes:** `time, flag, mode, value`. The value can be 1 byte (switch), 4 bytes or text.
- **Time curve:** each track has a curve from 0 to 1 across its block.
- **Voice line:** its block is exactly as long as the recording in the original.
- **Active flag:** the third character after the block (`00100100` active, `00000100` off).
- **Nesting:** a chore can contain another. Its time curve counts in fractions of the inner chore's length.

### Rules that came out of testing

1. **Ignore disabled lines.** Otherwise the timeline shifts for no reason.
2. **A nested scene plays 1:1.** Outer and inner file need the same schedule.
3. **Move sounds, don't stretch them.**
4. **Move all keyframes, including short ones.** Forgotten switches fired events too early.
5. **Cutscenes pause at the end of a line:** a curve with a flat section holds camera and characters. This worked better than slowing everything down evenly.
6. **Never speed up voices.**
7. **Keep overlaps.** Lines that already overlap in the original, such as interruptions, aren't cut at the start of the next line.
8. **Pauses travel through all levels.** An outer scene takes over the inner scene's pauses, even with no line of its own. The time curve is read piece by piece, because many have more than two points. Only sections at more than double or less than half speed aren't carried over.
9. **A pause must finish before the end of its block and of its line.** Otherwise the end falls into the short ramp of the pause and moves only part of the way, which cuts the line and jumps to the next scene.
10. **A track ends at the next name or line.** Otherwise the sound fix overwrites the blocks of the following voice lines with the English length again.

Normal conversations stretch slightly during the line instead.

## Open questions

- **Doubled words:** earlier versions sometimes repeated words in cutscenes, mostly at camera changes. The cause was never found. They have not been reported with the current pause method.
- **Real lips:** the old `.anm` files are coded differently and aren't used yet.
- **German chores from 2010:** Season 3 contains its own German chores, which might serve as a timing template. This has not been investigated.
