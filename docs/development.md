# Development

## Building from source

You need Python 3.10 or newer on Windows. The `bin/` folder needs three files that are not in the repository:

- `libspeex-1.dll` from the MSYS2 package `mingw-w64-x86_64-speex`
- `7z.exe` and `7z.dll` from a 7-Zip installation

Then:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

The program ends up in the folder `dist/DubPolice`, ready to share as `dist/DubPolice.zip`. It is built as a folder rather than a single exe, because virus scanners flag self-extracting exes far more often. To run without a window:

```bash
python src/launcher.py --engine --game "<remaster folder>" --source "<old version>" --language french --episodes 101 102
```

```bash
python src/launcher.py --engine --game "<remaster folder>" --uninstall
```

`--language` is `german` (default) or `french`. `--no-deess` keeps the S sounds in German as recorded. `--music-continuous` lets the music run on through dialog pauses. `--retro on` or `--retro off` only dubs the retro mode or makes it English again.

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
| `src/repair.py` | Repairing cut-off takes |
| `src/undubbed.py` | Season 1 takes left in English in 2007 |
| `src/lipsync.py` | German and French mouth shapes, gadgets, bone lips |
| `src/anm_patch.py` | Stretching lip files |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Timing of scenes |
| `src/badge.py` | Badge on the main menu, BC3 textures |
| `src/retro1.py` | Season 1 retro mode |
| `src/retro.py` | Season 2 retro mode |
| `src/retro3.py` | Season 3 retro mode: archive, dialogs, menu texts |
| `src/chore_mtre.py` | Reading and adapting scenes of the Season 3 retro engine |
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
| `.ttarch` version 8 | Number 8 at the start | Season 3 retro mode (Steam) | Telltale's Blowfish variant or none; data partly obscured |
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
4. **dubbed text:** the remaster's own German or French subtitle matches the text of an old recording
5. **similar:** last resort for the same speaker: an unused recording whose English text scores at least 0.6 and clearly beats the next one; only for lines of 12 characters or more

Takes of 0.25 s or less are often cut off in the old game. If the same speaker has a complete take of the same dubbed text, it is used instead (**whole take**). Lines are also looked up in the season's shared `Common` archive, where standard replies live.

Every voice gets 0.15 s of silence at the end, like the English recordings; without it the game cut off the last letters.

The results of each run are written to the work folder as `epNNN_lines.csv`.

**Borrowed recordings:** a language entry has two CRC64 fields for `.anm` and `.wav` after its number and hash. If they are set, it points to another line's recording; otherwise its own number applies. Such entries have no file of their own, but their chores still need the new length, or the sentence stops at the English length. In Seasons 2 and 3 this affected about 640 chores, mostly conversations and interactions.

## Lip files (`.anm`)

The length is a float at `20 + 12 × types + 16`. Times are in lists of `size, count` with 37-byte entries. Both are stretched proportionally.

An entry is `time, flag 0x31, 01 00 00 00 1c 00 00 00, shape, ramp in, hold, ramp out, weight`. The shape is the CRC64 of its lower-case name (`aa`, `ee`, `fv`, `i`, `ll`, `mm`, `nn`, `o`, `sh`, `th`, `u`), which picks the character's `*_phoneme_*.anm`. Two sizes cover the list: the body size at byte 4 and a 24-bit size right after the length.

### German mouth shapes (`src/lipsync.py`)

For German, each line gets its own list instead of the stretched English one:

1. Spelling rules turn the old recording's German text into shapes, such as `sch` to SH or `au` to AA then U.
2. The recording's loudness per 1/30 s decides where they go: each shape takes a share of the loudness, vowels twice as much, so open vowels land on loud syllables.
3. At most one shape every 0.1 s; where several crowd together, the clearest wins (vowels, then lips closing). Long ramps let the mouth glide.

The old German `.anm` files of 2007 move bones of the old faces and are not used.

## Cut-off takes (`src/repair.py`)

About one take in ten of Season 1, German and French alike, ends while the voice is still loud. The 2007 German lip files have the same length, so the recordings were cut before they went into the game. A take counts as cut off when its last 20 ms are louder than 30 % of its average level. Then, using takes of any episode by the same speaker:

1. **Whole take:** the same text in a take that ends properly.
2. **Graft:** a take whose last word ends the same way. The donor's last word is searched for the spot that sounds most like the end of the cut take (log spectrum in 32 bands, 60 ms), its rest is level-matched and cross-faded in. At most 0.35 s are added, and grafts that fit poorly are not made.

Takes that the 2007 releases left in English are the same file in German and French; `src/undubbed.py` lists them, and they never serve as a replacement.

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

## Badge on the main menu (`src/badge.py`)

The logo on the main menu is a texture in the UI archive (`ui_logoSamMaxSaveTheWorld`, `ui_logoSamMaxBeyondTimeAndSpace`, `ui_logoSamMaxTheDevilsPlayhouse`): BC3 (DXT5), one level, 1024 × 1024 or 2048 × 1024. Dub Police decodes it, places the badge at the lower right of the lettering and encodes again only the 4×4 blocks the badge touches. All other blocks keep their original bytes. The badges are drawn once at their final size (fonts Bangers and Special Elite) and kept as RGBA in `src/ui/badges`.

The changed logo goes into `<prefix>_pc_UI_DubPolice_uncompressed.ttarch2`. `_resdesc_51_UIDubPolice.lua` is a second description of the UI set with `descriptionPriority = 100` that lists this archive first, derived from `_resdesc_50_UI.lua` like the episodes'.

## Season 1 retro mode (`src/retro1.py`)

Steam puts two complete archives in each episode folder, `SamMax10x_english.ttarch` and the one in the game's language, each with its own chores. The game prefers the English one, so the dubbed voices play with English timing and get cut off. `--retro on` renames the English archive to `….ttarch.DubPolice`, `--retro off` and `--uninstall` rename it back. Nothing is deleted.

## Retro mode

`--retro on` dubs the remaster's original episodes, `--retro off` makes them English again. Which episodes are dubbed is kept under `retro` in `SamMax_GermanDub.json`. `--uninstall` restores them as well.

### Season 2 (`src/retro.py`)

- **Archive:** one flat archive per episode (`SamMax20x_english.ttarch`, version 2). Data files are obscured block by block after 4 marker bytes: `aadeaf64` (episode 205) with 0x100-byte blocks, every 8th Blowfish, the rest inverted; any other marker with 0x80-byte blocks, every 32nd Blowfish, every 80th raw, the rest inverted.
- **Installing:** changed files are appended to the archive and the table points to them. The English table and the replaced voices are kept in `DubPolice_Retro`, so everything can be restored byte for byte.
- **Texts:** `english.langdb` gets the old version's text. The engine shows nothing outside ASCII, so German umlauts are written out and accents are dropped.
- **Scenes:** names are stored as plain text after their length, lines are called `<number>.langres`, time curves are called `time`. Scenes are adapted with the same pause logic as the remaster.

### Season 3 (`src/retro3.py`, `src/chore_mtre.py`)

**Archive.** Each episode loads every `.ttarch` in `ep30x\Pack`. Of two files with the same name, the archive that sorts first wins, like Telltale's patches `0_…` before the data `1_…`. Dub Police writes `0_0DubPolice.ttarch`: version 8, unencrypted, uncompressed, built like `0_8patch.ttarch` from episode 305, with the two build numbers from the episode's data archive. The files of episode 302 and some patches start with `aadeaf64` instead of `ERTM` and are obscured as in Season 2, with Telltale's Blowfish variant.

**Dialogs (`.dlog`).** Subtitles are in a table: `size, count`, then per line `number, number, reference, lip name, voice name, block[size, 1, speaker, text, 8 bytes], 8 bytes`. An empty block is `8, 0`. 20 bytes before the table is an enclosing block whose size grows too. The voice is named after the line number; the `.vox` from the German version plays directly.

**Scenes (`.chore`).** After `ERTM` and the type list (12 bytes per type) come name, length, number of tracks and agents. Each track is: `group, length, version, priority, flags, name, control animation, block list, 8 switches, properties, …`. The block list is `size, count` and per block `start, end, loop character, scale`.

The control animation:

```
u32 size, u32 version (4|5), u32 flags, u64 name, u32 0, f32 0
u32 inner size (= size − 28), u32 channels, u32 pool, u32 types
per type: u64 type, u32 0, u16 channels of this type, u16 type version
per channel its body, per channel u32 flags (high byte: 1 time, 2 weight, 4 mover, 5 property), u16 0
per channel u64 name, u32 0
```

- **Key list:** `u16 count`, then per key `value, f32 time`, then 2 bits per key for the blend to the next: 0 step, 1 straight line, 3 smooth curve.
- **Types:** number (4), on/off (1), vector (12) and rotation (16), as key list or single value; texts (`u32 length` + text) as key list or single value; two blocked strings (a reference to a scene) as key list or single value. One compressed type (`a4e0fd8b…`, 4 tracks) is not decoded. The channels before it are still moved in place.
- **Pool:** per key list `4 + round_up4((value size + 4) × n) + 4 × ((n − 1) // 16)` bytes, texts with 4 bytes per key. The formula holds for all 161,406 control animations. A pool that is too small makes the game crash while loading.
- **Nested scenes:** the time channel counts in shares of the inner length. That length is stored once more before the track's name.

**Pauses.** The pauses come from the same calculation as for the remaster. Every time after a pause moves by its length. Channels that step or run in straight lines get two hold keys. Smooth curves are only moved, as their formula is unknown. Line tracks are stretched to the new length. Volume channels of sounds go to 0 during pauses. Nested scenes are adapted first; the outer scene pauses with them without stopping the inner time.

**Checks.** In all 12,454 scenes the number of tracks found matches the header, and every scene is written back byte for byte identical when nothing changes. After adapting, it is checked that every German line fits, every pause stands still, values match the original and the pools are right.

**What testing taught:**

1. **Only exact reading works.** Heuristic searches for key lists hit the wrong bytes and broke the scenes further.
2. **The pool has to be right,** or the game crashes when a new game starts.
3. **Respect the blend type.** A hold key in the middle of a step moved the camera into empty space.
4. **Find every track.** Empty control animations and unknown types left tracks out, which then ran on the old timing. Scenes overlapped.
5. **Do not skip unknown channels entirely.** The narrator's visibility sat before a compressed channel and still had to move.

## Open questions

- **Doubled words:** earlier versions sometimes repeated words in cutscenes, mostly at camera changes. The cause was never found. They have not been reported with the current pause method.
- **German chores from 2010:** investigated. Telltale only adapted 5 Season 3 scenes to the German lines back then, stretching every time in the scene. They are no template, but confirmed which values are times.
- **Compressed channel of the Season 3 retro** (`a4e0fd8b…`), probably facial expressions: not decoded yet.
