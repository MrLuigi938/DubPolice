# Entwicklung

## Aus dem Quellcode bauen

Du brauchst Python 3.10 oder neuer unter Windows. Der Ordner `bin/` braucht drei Dateien, die nicht im Repository liegen:

- `libspeex-1.dll` aus dem MSYS2-Paket `mingw-w64-x86_64-speex`
- `7z.exe` und `7z.dll` aus einer 7-Zip-Installation

Danach:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

Das Programm landet in `dist/DubPolice.exe`. Ohne Fenster:

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --source "<alte Version>" --language french --episodes 101 102
```

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --uninstall
```

`--language` ist `german` (Standard) oder `french`. Mit `--no-deess` bleiben die S-Laute bei Deutsch wie aufgenommen.

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
| `src/anm_patch.py` | Lippen-Dateien strecken |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Timing der Szenen |
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

Die Ergebnisse jedes Laufs landen im Arbeitsordner als `epNNN_lines.csv`.

**Geliehene Aufnahmen:** Ein Sprach-Eintrag hat nach Nummer und Hash zwei CRC64-Felder für `.anm` und `.wav`. Sind sie gesetzt, verweist er auf die Aufnahme einer anderen Zeile, sonst gilt die eigene Nummer. Solche Einträge haben keine eigene Datei, ihre Choreografien brauchen aber trotzdem die neue Länge. Sonst bricht der Satz bei der englischen Länge ab. In Season 2 und 3 betraf das rund 640 Choreografien, meist Gespräche und Interaktionen.

## Lippen-Dateien (`.anm`)

Die Länge steht als Float bei `20 + 12 × Typen + 16`. Die Zeitpunkte stehen in Listen aus `Größe, Anzahl` und 37-Byte-Einträgen. Beides wird proportional gestreckt.

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

## Offene Fragen

- **Doppelte Wörter:** Frühere Versionen wiederholten in Zwischensequenzen manchmal Wörter, meist bei Kamerawechseln. Die Ursache wurde nie gefunden. Mit der aktuellen Pausen-Methode wurden sie nicht mehr gemeldet.
- **Echte Lippen:** Die alten `.anm` sind anders kodiert und werden noch nicht genutzt.
- **Deutsche Choreografien von 2010:** Season 3 enthält eigene deutsche Choreografien, die als Zeitvorlage taugen könnten. Das ist nicht untersucht.
