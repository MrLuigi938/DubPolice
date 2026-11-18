# Entwicklung

## Aus dem Quellcode bauen

Du brauchst Python 3.10 oder neuer unter Windows. Der Ordner `bin/` braucht drei Dateien, die nicht im Repository liegen:

- `libspeex-1.dll` aus dem MSYS2-Paket `mingw-w64-x86_64-speex`
- `7z.exe` und `7z.dll` aus einer 7-Zip-Installation

Danach:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

Das Programm landet im Ordner `dist/DubPolice`, fertig zum Weitergeben als `dist/DubPolice.zip`. Es wird als Ordner statt als einzelne Exe gebaut, weil Virenscanner sich selbst entpackende Exe-Dateien deutlich öfter melden. Ohne Fenster:

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --source "<alte Version>" --language french --episodes 101 102
```

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --uninstall
```

`--language` ist `german` (Standard) oder `french`. Mit `--no-deess` bleiben die S-Laute bei Deutsch wie aufgenommen. Mit `--music-continuous` läuft die Musik in Dialogpausen durch. `--retro on` oder `--retro off` vertont nur den Retro-Modus oder macht ihn wieder englisch.

Spieldaten gehören nie ins Repository, `.gitignore` schließt sie aus.

## Aufbau des Codes

| Pfad | Inhalt |
|---|---|
| `src/launcher.py` | Einstieg der Exe: Fenster oder Umwandlung |
| `src/gui.py` | Backend des Fensters: Steam-Spiele finden, Ordner wählen, Umwandlung starten und verfolgen |
| `src/ui/` | Das Fenster: HTML, CSS, JavaScript, Schriften, Hintergrund |
| `src/sammax_de.py` | Die Umwandlung: Quellen finden, Zeilen zuordnen, umwandeln, installieren |
| `src/old_archive.py`, `src/ttarch4.py` | Alte Archive lesen |
| `src/ectt.py`, `src/nctt.py` | Archive des Remasters lesen |
| `src/vox2wav.py` | Alte Aufnahmen dekodieren |
| `src/enhance.py` | Klangbearbeitung, De-Esser, MP3 in FSB5 |
| `src/repair.py` | Abgeschnittene Aufnahmen reparieren |
| `src/undubbed.py` | Aufnahmen von Season 1, die 2007 englisch blieben |
| `src/lipsync.py` | Deutsche und französische Mundformen, Geräte, Knochen-Lippen |
| `src/anm_patch.py` | Lippen-Dateien strecken |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Timing der Szenen |
| `src/badge.py` | Abzeichen im Hauptmenü, BC3-Texturen |
| `src/retro1.py` | Retro-Modus von Season 1 |
| `src/retro.py` | Retro-Modus von Season 2 |
| `src/retro3.py` | Retro-Modus von Season 3: Archiv, Dialoge, Menütexte |
| `src/chore_mtre.py` | Szenen der Season-3-Retro-Engine lesen und anpassen |
| `src/keys.py` | Schlüssel für die Spielarchive, aus den TTG Tools |
| `assets/` | Das Logo als SVG und ICO |

## So funktioniert es

1. Die Archive jeder Episode in der alten Version finden, bei einer Disc aus dem Installer entpacken.
2. Jede Remaster-Zeile einer alten Aufnahme zuordnen.
3. Die Aufnahme dekodieren, den Klang bearbeiten und als FSB5 verpacken.
4. Lippen-Dateien und Szenen (Choreografien) an die neue Länge anpassen.
5. Ein Archiv und eine Steuerdatei pro Episode nach `Archives` schreiben.

### Eine Sprache ergänzen

Der Ablauf hängt nur an Länge und Zuordnung der Aufnahmen. Eine neue Sprache braucht einen Eintrag in `SEASONS[...]["languages"]`, ihren Namen in `SOURCE_FOLDERS` in `gui.py`, Texte und Reiter in `fallakte.js`, die alte Version und einen Test. Eine Episode hält immer nur eine Sprache, die Dateien heißen `*_{Sprache}Dub_*`. Italienisch und Spanisch haben auf der Disc von Season 2 nur Untertitel und die englischen Stimmen.

## Archive

| Format | Kennung | Verwendung | Verschlüsselung |
|---|---|---|---|
| `.ttarch` Version 2 | Zahl 2 am Anfang | Season 1 (2007), Deutsch und Französisch | Blowfish-Tabelle; Metadaten blockweise: jeder 32. Blowfish, jeder 80. roh, der Rest invertiert |
| `.ttarch` ohne Version | Tabellengröße am Anfang | Season 1, englische Disc (nicht unterstützt) | wie Version 2 |
| `.ttarch` Version 4 | Zahl 4 am Anfang | Season 2 (2009) | Blowfish-Tabelle; zlib-Blöcke |
| `.ttarch` Version 8 | Zahl 8 am Anfang | Retro-Modus von Season 3 (Steam) | Telltale-Blowfish-Variante oder keine; Daten teils verschleiert |
| `.ttarch` Version 9 | Zahl 9 am Anfang | Season 3 (2010) | Telltale-Blowfish-Variante; Tabelle und Blöcke teils komprimiert |
| `.ttarch2` | `ECTT` | Remaster, komprimiert | Telltale-Blowfish-Variante, dann Deflate in 64-KB-Blöcken |
| `.ttarch2` | `NCTT` | Remaster, roh | keine |

Im `NCTT`-Archiv folgen auf `4ATT` die Größe der Namenstabelle, die Dateizahl und 28 Byte je Datei: CRC64 des kleingeschriebenen Namens (ECMA-182), Offset, Größe, 0, Namensblock, Namensoffset. Die Einträge sind nach der CRC64 sortiert, die Namenstabelle ist auf 64 KB aufgefüllt.

Jede alte Episode hat einen eigenen Schlüssel, jedes Remaster einen gemeinsamen.

## Laden von Archiven

Das Spiel führt beim Start `_resdesc_*.lua` im Ordner `Archives` aus.

- **Steuerdateien müssen verschlüsselt sein** (`ESC LEo`). Unverschlüsselte wurden im Test ignoriert.
- Dateinamen wiederholen sich zwischen den Episoden. Ein immer aktives Archiv würde also andere Episoden überschreiben.
- **Lösung:** Eine zweite Beschreibung der Episoden-Gruppe mit `descriptionPriority = 100`, die das neue Archiv zuerst nennt. Sie wird aus der Original-Steuerdatei der Episode abgeleitet.

Die Liste der installierten Dateien liegt unabhängig von der Sprache in `SamMax_GermanDub.json` im Spielordner.

## Sprache

- **2009 und 2010:** `.vox` mit Speex, 32 kHz. Kopf `ERTM`, 20 Byte. Das erste Paket ist ein Kommentar, kein Ton.
- **2007:** Einzelne `.vox` neben dem Archiv, Kopf `NIBM`, 31 Byte. Jedes 64. Paket ist mit dem Schlüssel der Episode verschlüsselt, angefangen beim Kommentar-Paket. Ohne Entschlüsselung fehlen dem Decoder alle 1,28 s 20 ms Ton. Diese Ordner enthalten keine englischen Aufnahmen, wohl aber die englischen Texte.
- **Remaster:** `.wav`-Einträge, tatsächlich FSB5 mit Vorbis, etwa 8,4 kB/s.
- **Ausgabe:** FSB5 mit MP3 (Modus 11), 44,1 kHz, mono, 128 kbit/s. Jedes MP3-Frame muss auf 4 Byte aufgefüllt sein, sonst dekodiert FMOD nur die ersten Frames. Der Encoder verzögert den Ton um 1.105 Samples (25 ms). Die Sample-Zahl im Kopf ist `Frames × 1152`, die Zeilenblöcke schließen die Verzögerung also ein.

### Klangbearbeitung (`src/enhance.py`)

Gemessen an 40 Zeilen aus Episode 301 liegen die alten Aufnahmen in Pegel und Balance nah am Remaster. Die Bearbeitung ist darum dezent, und nichts wird neu erzeugt:

1. **Auflösung:** auf 44,1 kHz umrechnen.
2. **Equalizer:** Rumpeln unter 70 Hz entfernen, etwa 2,5 dB Präsenz um 3 kHz und bei 14 bis 16 kHz.
3. **De-Esser (nur Deutsch, abschaltbar):** 4,5 bis 12 kHz werden nur gedämpft, solange der Pegel über einer Schwelle 14 dB unter dem Sprachpegel liegt; Verhältnis 4:1, höchstens 10 dB. Darunter ändert sich der Pegel um höchstens 0,03 dB. Die Schärfe stammt aus den alten Aufnahmen, nicht aus dem Equalizer.
4. **Luft:** eine Spur der eigenen S-Anteile über 16 kHz, wo die alten Aufnahmen nichts mehr haben.
5. **Pegel:** +0,5 dB, nur seltene Spitzen werden weich begrenzt.

## Zuordnung der Zeilen

`english.langdb` oder `*_english.landb` verbinden Nummer, Sprecher und Text. Bei Season 3 sind die Nummern in alter Version und Remaster weitgehend gleich. Sonst wird in dieser Reihenfolge zugeordnet:

1. **exact:** normalisierter Text eindeutig
2. **same text:** Text mehrfach vorhanden, dann gleicher Sprecher und ähnlichste Dauer
3. **close:** Textähnlichkeit ab 0,92, etwa korrigierte Tippfehler
4. **dubbed text:** Der deutsche oder französische Untertitel des Remasters passt zum Text einer alten Aufnahme
5. **similar:** letzter Ausweg bei gleichem Sprecher: eine unbenutzte Aufnahme, deren englischer Text mindestens 0,6 erreicht und die nächste deutlich schlägt; nur für Zeilen ab 12 Zeichen

Aufnahmen von 0,25 s oder weniger sind im alten Spiel oft abgeschnitten. Hat derselbe Sprecher eine vollständige Aufnahme desselben synchronisierten Texts, wird diese verwendet (**whole take**). Zeilen werden auch im gemeinsamen `Common`-Archiv der Season gesucht, wo Standardantworten liegen.

Jede Stimme bekommt am Ende 0,15 s Stille wie die englischen Aufnahmen; ohne sie schnitt das Spiel die letzten Buchstaben ab.

Die Ergebnisse jedes Laufs landen im Arbeitsordner als `epNNN_lines.csv`.

**Geliehene Aufnahmen:** Ein Sprach-Eintrag hat nach Nummer und Hash zwei CRC64-Felder für `.anm` und `.wav`. Sind sie gesetzt, verweist er auf die Aufnahme einer anderen Zeile, sonst gilt die eigene Nummer. Solche Einträge haben keine eigene Datei, ihre Choreografien brauchen aber trotzdem die neue Länge. Sonst bricht der Satz bei der englischen Länge ab. In Season 2 und 3 betraf das rund 640 Choreografien, meist Gespräche und Interaktionen.

## Lippen-Dateien (`.anm`)

Die Länge steht als Float bei `20 + 12 × Typen + 16`. Die Zeitpunkte stehen in Listen aus `Größe, Anzahl` und 37-Byte-Einträgen. Beides wird proportional gestreckt.

Ein Eintrag ist `Zeit, Flag 0x31, 01 00 00 00 1c 00 00 00, Mundform, Einblenden, Halten, Ausblenden, Gewicht`. Die Mundform ist die CRC64 ihres kleingeschriebenen Namens (`aa`, `ee`, `fv`, `i`, `ll`, `mm`, `nn`, `o`, `sh`, `th`, `u`) und wählt die `*_phoneme_*.anm` der Figur. Zwei Größen umfassen die Liste: die Größe des Inhalts bei Byte 4 und eine 24-Bit-Größe direkt nach der Länge.

### Deutsche Mundformen (`src/lipsync.py`)

Auf Deutsch bekommt jeder Satz eine eigene Liste statt der gestreckten englischen:

1. Schreibregeln machen aus dem deutschen Text der alten Aufnahme Mundformen, etwa `sch` zu SH oder `au` zu AA, dann U.
2. Die Lautstärke der Aufnahme je 1/30 s bestimmt, wo sie liegen: Jede Mundform bekommt einen Anteil der Lautstärke, Vokale doppelt so viel, damit offene Vokale auf lauten Silben landen.
3. Höchstens eine Mundform alle 0,1 s; drängen sich mehrere, gewinnt die deutlichste (Vokale, dann geschlossene Lippen). Lange Übergänge lassen den Mund gleiten.

Die alten deutschen `.anm` von 2007 bewegen Knochen der alten Gesichter und werden nicht verwendet.

## Abgeschnittene Aufnahmen (`src/repair.py`)

Etwa jede zehnte Aufnahme von Season 1 endet, während die Stimme noch laut ist, auf Deutsch wie auf Französisch. Die deutschen Lippen-Dateien von 2007 sind genauso lang, die Aufnahmen waren also schon vor dem Einbau ins Spiel gekürzt. Als abgeschnitten gilt eine Aufnahme, wenn ihre letzten 20 ms lauter als 30 % ihres Durchschnitts sind. Dann, mit Aufnahmen aller Episoden desselben Sprechers:

1. **Whole take:** derselbe Text in einer Aufnahme, die richtig endet.
2. **Graft:** eine Aufnahme, deren letztes Wort gleich endet. Im letzten Wort des Spenders wird die Stelle gesucht, die dem Ende der abgeschnittenen Aufnahme am ähnlichsten klingt (Log-Spektrum in 32 Bändern, 60 ms). Der Rest wird in der Lautstärke angeglichen und übergeblendet. Höchstens 0,35 s kommen dazu, schlecht passende Ergänzungen entfallen.

Aufnahmen, die 2007 englisch blieben, sind auf Deutsch und Französisch dieselbe Datei. `src/undubbed.py` listet sie auf, sie dienen nie als Ersatz.

## Choreografien (`.chore`)

- **Zeitblöcke:** `Start, Ende, Loop-Zeichen, Skalierung` (13 Byte).
- **Keyframes:** `Zeit, Flag, Modus, Wert`. Der Wert kann 1 Byte (Schalter), 4 Byte oder Text sein.
- **Zeitkurve:** Jede Spur hat eine Kurve von 0 bis 1 über ihren Block.
- **Sprachzeile:** Ihr Block ist im Original genau so lang wie die Aufnahme.
- **Aktiv-Flag:** Das dritte Zeichen hinter dem Block (`00100100` aktiv, `00000100` aus).
- **Verschachtelung:** Eine Choreografie kann eine andere enthalten. Ihre Zeitkurve zählt in Bruchteilen der Länge der inneren.

### Regeln, die sich im Test ergeben haben

1. **Abgeschaltete Zeilen ignorieren.** Sonst verschiebt sich die Zeitachse ohne Grund.
2. **Eine verschachtelte Szene läuft 1:1.** Äußere und innere Datei brauchen denselben Zeitplan.
3. **Sound nur verschieben, nicht dehnen.**
4. **Alle Keyframes verschieben, auch kurze.** Vergessene Schalter lösten Ereignisse zu früh aus.
5. **Zwischensequenzen pausieren am Zeilenende:** Eine Kurve mit waagerechtem Stück hält Kamera und Figuren an. Das wirkte besser als gleichmäßiges Verlangsamen.
6. **Stimmen nie beschleunigen.**
7. **Überlappungen behalten.** Zeilen, die sich schon im Original überlappen, etwa beim Ins-Wort-Fallen, werden nicht am Start der nächsten Zeile gekappt.
8. **Pausen wandern durch alle Ebenen.** Eine äußere Szene übernimmt die Pausen der inneren, auch ohne eigene Zeile. Die Zeitkurve wird stückweise gelesen, denn viele haben mehr als zwei Punkte. Nur Abschnitte mit mehr als doppeltem oder weniger als halbem Tempo werden nicht übertragen.
9. **Eine Pause muss vor dem Ende ihres Blocks und ihrer Zeile fertig sein.** Sonst fällt das Ende in die kurze Rampe der Pause und wandert nur um einen Bruchteil. Das schneidet den Satz ab und springt zur nächsten Szene.
10. **Eine Spur endet am nächsten Namen oder an der nächsten Zeile.** Sonst überschreibt die Sound-Korrektur die Blöcke folgender Sprachzeilen wieder mit der englischen Länge.

Normale Gespräche werden stattdessen während der Zeile leicht gestreckt.

## Abzeichen im Hauptmenü (`src/badge.py`)

Das Logo im Hauptmenü ist eine Textur im UI-Archiv (`ui_logoSamMaxSaveTheWorld`, `ui_logoSamMaxBeyondTimeAndSpace`, `ui_logoSamMaxTheDevilsPlayhouse`): BC3 (DXT5), eine Ebene, 1024 × 1024 bzw. 2048 × 1024. Dub Police dekodiert sie, setzt das Abzeichen rechts unten an den Schriftzug und kodiert nur die 4×4-Blöcke neu, die das Abzeichen berührt. Alle anderen Blöcke bleiben Byte für Byte original. Die Abzeichen sind einmal in ihrer Endgröße gezeichnet (Schrift Bangers und Special Elite) und liegen als RGBA in `src/ui/badges`.

Das geänderte Logo kommt in `<Prefix>_pc_UI_DubPolice_uncompressed.ttarch2`. `_resdesc_51_UIDubPolice.lua` ist eine zweite Beschreibung des UI-Satzes mit `descriptionPriority = 100`, die dieses Archiv zuerst nennt, abgeleitet aus `_resdesc_50_UI.lua` wie bei den Episoden.

## Retro-Modus von Season 1 (`src/retro1.py`)

Steam legt in jeden Episodenordner zwei vollständige Archive, `SamMax10x_english.ttarch` und das in der Spielsprache, jedes mit eigenen Choreografien. Das Spiel bevorzugt das englische, die synchronisierten Stimmen laufen dann mit englischem Timing und brechen ab. `--retro on` benennt das englische Archiv in `….ttarch.DubPolice` um, `--retro off` und `--uninstall` benennen es zurück. Gelöscht wird nichts.

## Retro-Modus

`--retro on` vertont die Original-Episoden des Remasters, `--retro off` macht sie wieder englisch. Welche Episoden vertont sind, steht unter `retro` in `SamMax_GermanDub.json`. `--uninstall` stellt sie ebenfalls wieder her.

### Season 2 (`src/retro.py`)

- **Archiv:** ein flaches Archiv pro Episode (`SamMax20x_english.ttarch`, Version 2). Datendateien sind nach 4 Kennbytes blockweise verschleiert: `aadeaf64` (Episode 205) mit Blöcken von 0x100 Byte, jeder 8. Blowfish, der Rest invertiert; jede andere Kennung mit Blöcken von 0x80, jeder 32. Blowfish, jeder 80. roh, der Rest invertiert.
- **Einbau:** Geänderte Dateien werden ans Archiv angehängt und die Tabelle zeigt auf sie. Die englische Tabelle und die ersetzten Stimmen liegen in `DubPolice_Retro`, damit sich alles Byte für Byte zurückstellen lässt.
- **Texte:** `english.langdb` bekommt den Text der alten Version. Die Engine zeigt nichts außerhalb von ASCII an, also werden Umlaute ausgeschrieben und Akzente entfernt.
- **Szenen:** Namen stehen im Klartext mit vorangestellter Länge, Zeilen heißen `<Nummer>.langres`, die Zeitkurven heißen `time`. Die Szenen werden mit derselben Pausen-Logik wie das Remaster angepasst.

### Season 3 (`src/retro3.py`, `src/chore_mtre.py`)

**Archiv.** Jede Episode lädt alle `.ttarch` in `ep30x\Pack`. Von zwei gleichnamigen Dateien gewinnt das Archiv, das alphabetisch zuerst kommt, wie Telltales Patches `0_…` vor den Daten `1_…`. Dub Police schreibt `0_0DubPolice.ttarch`: Version 8, unverschlüsselt, ohne Kompression, Aufbau wie das `0_8patch.ttarch` aus Episode 305, die beiden Build-Nummern aus dem Datenarchiv der Episode. Die Dateien von Episode 302 und einige Patches beginnen statt mit `ERTM` mit `aadeaf64` und sind wie bei Season 2 verschleiert, mit der Telltale-Blowfish-Variante.

**Dialoge (`.dlog`).** Die Untertitel stehen in einer Tabelle: `Größe, Anzahl`, dann je Zeile `Nummer, Nummer, Verweis, Lippen-Name, Stimmen-Name, Block[Größe, 1, Sprecher, Text, 8 Byte], 8 Byte`. Ein leerer Block ist `8, 0`. 20 Byte vor der Tabelle steht ein umschließender Block, dessen Größe mitwächst. Die Stimme heißt wie die Zeilennummer, `.vox` aus der deutschen Fassung wird direkt abgespielt.

**Szenen (`.chore`).** Nach `ERTM` und der Typliste (12 Byte je Typ) folgen Name, Länge, Zahl der Spuren und Agenten. Jede Spur ist: `Gruppe, Länge, Version, Priorität, Flags, Name, Steuer-Animation, Blockliste, 8 Schalter, Eigenschaften, …`. Die Blockliste ist `Größe, Anzahl` und je Block `Start, Ende, Loop-Zeichen, Skalierung`.

Die Steuer-Animation:

```
u32 Größe, u32 Version (4|5), u32 Flags, u64 Name, u32 0, f32 0
u32 Innengröße (= Größe − 28), u32 Kanäle, u32 Pool, u32 Typen
je Typ: u64 Typ, u32 0, u16 Kanäle dieses Typs, u16 Typ-Version
je Kanal sein Inhalt, je Kanal u32 Flags (oberes Byte: 1 Zeit, 2 Gewicht, 4 Bewegung, 5 Eigenschaft), u16 0
je Kanal u64 Name, u32 0
```

- **Zeitliste:** `u16 Anzahl`, dann je Schlüssel `Wert, f32 Zeit`, dann 2 Bit je Schlüssel für die Überblendung zum nächsten: 0 Sprung, 1 gerade Linie, 3 weiche Kurve.
- **Typen:** Zahl (4), Ja/Nein (1), Vektor (12) und Drehung (16) als Zeitliste oder Einzelwert; Texte (`u32 Länge` + Text) als Zeitliste oder Einzelwert; zwei Blockstrings (Verweis auf eine Szene) als Zeitliste oder Einzelwert. Ein komprimierter Typ (`a4e0fd8b…`, 4 Spuren) ist nicht entschlüsselt. Die Kanäle davor werden trotzdem an Ort und Stelle verschoben.
- **Pool:** je Zeitliste `4 + aufgerundet4((Wertgröße + 4) × n) + 4 × ((n − 1) // 16)` Byte, Texte mit 4 Byte je Schlüssel. Die Formel stimmt für alle 161.406 Steuer-Animationen. Ein zu kleiner Pool lässt das Spiel beim Laden abstürzen.
- **Eingebettete Szenen:** Der Zeit-Kanal zählt in Anteilen der inneren Länge. Vor dem Namen der Spur steht diese Länge noch einmal.

**Pausen.** Die Pausen kommen aus derselben Rechnung wie beim Remaster. Jede Zeit nach einer Pause wandert um deren Länge. Kanäle mit Sprung oder gerader Linie bekommen zwei Haltepunkte. Weiche Kurven werden nur verschoben, weil ihre Formel unbekannt ist. Satz-Spuren werden auf die neue Länge gedehnt. Lautstärke-Kanäle von Tönen gehen in Pausen auf 0. Eingebettete Szenen werden zuerst angepasst. Die äußere Szene macht deren Pausen mit, ohne die innere Zeit anzuhalten.

**Prüfungen.** In allen 12.454 Szenen stimmt die gefundene Spurenzahl mit dem Kopf überein, und jede Szene wird ohne Änderung Byte für Byte identisch zurückgeschrieben. Nach dem Anpassen wird geprüft: jeder deutsche Satz passt, jede Pause steht still, die Werte stimmen mit dem Original überein, die Pools stimmen.

**Was beim Testen herauskam:**

1. **Nur exaktes Lesen hilft.** Heuristische Suchen nach Zeitlisten trafen falsche Bytes und machten die Szenen kaputter.
2. **Der Pool muss stimmen,** sonst stürzt das Spiel beim Start eines neuen Spiels ab.
3. **Die Überblendart beachten.** Ein Haltepunkt mitten in einem Sprung-Abschnitt verschob die Kamera ins Leere.
4. **Alle Spuren finden.** Leere Steuer-Animationen und unbekannte Typen ließen Spuren aus, die dann zur alten Zeit liefen. Szenen überlappten deshalb.
5. **Unbekannte Kanäle nicht ganz liegen lassen.** Die Sichtbarkeit des Erzählers stand vor einem komprimierten Kanal und musste trotzdem mitwandern.

## Offene Fragen

- **Doppelte Wörter:** Frühere Versionen wiederholten in Zwischensequenzen manchmal Wörter, meist bei Kamerawechseln. Die Ursache wurde nie gefunden. Mit der aktuellen Pausen-Methode wurden sie nicht mehr gemeldet.
- **Deutsche Choreografien von 2010:** untersucht. Telltale hat damals nur 5 Szenen von Season 3 an die deutschen Sätze angepasst, dabei alle Zeiten der Szene gestreckt. Als Vorlage taugen sie nicht, sie bestätigten aber, welche Werte Zeiten sind.
- **Komprimierter Kanal der Season-3-Retro** (`a4e0fd8b…`), vermutlich Mimik: noch nicht entschlüsselt.
