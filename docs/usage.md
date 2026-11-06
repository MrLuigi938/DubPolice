# Usage

## Which old version you need

Dub Police reads the voices from your own copy of the old game, in the language you want. Here is what works:

| Season | German | French |
|---|---|---|
| **1** Save the World (2007) | The installed folder | The installed folder |
| **2** Beyond Time and Space (2009) | The installed folder or the disc | The installed folder or the disc |
| **3** The Devil's Playhouse (2010) | The installed folder | not available yet |

Select the main folder of the old game. Dub Police searches it for the right files, so you don't have to pick them one by one. The Season 2 disc already contains both languages. Mount an ISO and select its drive.

**Tip:** Dub Police also looks for a folder named `Quelldaten` next to the program, sorted like `Quelldaten\Deutsch\Season 1` or `Quelldaten\Französisch\Season 2`. If it holds your data, the field fills in by itself.

## Installing

1. Close the game. Dub Police refuses to start while it is running.
2. Start `DubPolice.exe`. The first start can take up to half a minute while Windows checks the new file.
3. Choose the season at the top left and the language at the top right. The whole window follows the language.
4. Check the two paths:
   - **Tatort / Scène de crime** is your remaster. Steam games are found by themselves.
   - **Zeugen / Témoins** is your old version.
5. Choose your episodes and start the installation.
6. In the game, set the language to the one you installed.

A full season takes about 12 to 23 minutes on the test PC and uses 620 to 810 MB. You can cancel at any time. The game is only changed at the very end, once all chosen episodes are ready.

### Sharp S sounds (German only)

The old German recordings have quite sharp S sounds. **Scharfe S-Laute abmildern** softens them only at the moment they sound and leaves the rest of the voice alone. It is on by default. Switch it off to keep them as they were recorded.

## Changing the language

Each episode holds one language at a time. Install an episode in the other language and it replaces the old one. Other episodes are not affected, and the list shows which language each one has.

## Removing everything

**Fall zu den Akten legen / Classer l'affaire** deletes everything Dub Police has added to that season, after asking you. The game then speaks English again. Original game files are never changed.

## Known limits

- **Scenes pause briefly.** When a line is longer than the English one, the scene holds at the end of the sentence until it is finished. In normal conversations, the scene stretches slightly instead.
- **Lips** are stretched English animations, not the old German or French ones.
- **A few lines stay in English** because no old recording matches them: 40 in Season 1, 32 in Season 2 and 13 in Season 3 for German.
- **Subtitles** come from the remaster and can differ slightly from the old recordings, because the remaster partly has new translations.
- **Short excerpts.** Some scenes play only part of another scene, such as the visions of the future in Episode 301. The original does the same, so a sentence can end mid-excerpt there.
- **Music** can drift slightly from the picture in long scenes, as it keeps running while the scene waits.
- **Tested with** the Steam versions on Windows. French has only been checked automatically on two episodes so far and has not yet been played.

## Troubleshooting

| Problem | What to do |
|---|---|
| The game still speaks English | Set the language in the game to the one you installed, and restart it. |
| "Bitte zuerst das Spiel schließen" | The game is still running. Close it and try again. |
| "kein unterstützter Remaster-Ordner" | Select the main folder of the remaster, the one with `SamMax100.exe`, `SamMax200.exe` or `SamMax300.exe`. |
| "nicht vollständig gefunden" | The selected folder doesn't hold all the files for this language and these episodes. Check that the version really is in that language. |
| The install button stays grey | Check both paths and select at least one episode. |
| The window does not open | Install the [WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) from Microsoft. |
| Windows warns about the file | The program is not signed, so Windows may show a warning. |

Messages from the conversion itself are always in German, including error details.
