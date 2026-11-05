# Technik

Alles hier wurde an Season 2 ermittelt, durch Lesen der Dateien und Tests im Spiel. Wo etwas nur eine
Vermutung ist, steht das dabei.

## Ablauf

1. Die drei Archive jeder Episode aus der alten Version finden, bei einer Disc aus dem Installer entpacken.
2. Jede Sprachzeile des Remasters über den englischen Text einer alten Aufnahme zuordnen.
3. Die deutsche Aufnahme dekodieren und als FSB5 neu verpacken.
4. Lippen-Datei und Choreografien an die deutsche Länge anpassen.
5. Ein Archiv und eine Steuerdatei pro Episode nach `Archives` schreiben.

## Archive

| Format | Kennung | Verwendung | Verschlüsselung |
|---|---|---|---|
| `.ttarch` Version 4 | Zahl 4 am Anfang | Spiele von 2009 | Blowfish, Tabelle; Blöcke zlib |
| `.ttarch2` | `ECTT` | Remaster, komprimiert | Telltale-Blowfish-Variante, dann Deflate in 64-KB-Blöcken |
| `.ttarch2` | `NCTT` | Remaster, roh | keine |

Im `NCTT`-Archiv folgen auf `4ATT` die Größe der Namenstabelle, die Dateizahl und 28 Byte je Datei:
CRC64 des kleingeschriebenen Namens (ECMA-182), Offset, Größe, 0, Namensblock, Namensoffset. Die Einträge sind nach
der CRC64 sortiert, die Namenstabelle ist auf 64 KB aufgefüllt.

Jede Episode von 2009 hat einen eigenen Schlüssel, das Remaster einen gemeinsamen.

## Laden von Archiven

Das Spiel führt beim Start `_resdesc_*.lua` im Ordner `Archives` aus.

- **Steuerdateien müssen verschlüsselt sein** (`ESC LEo`). Unverschlüsselte wurden im Test ignoriert, obwohl
  `_resdesc_50_version_200.lua` selbst unverschlüsselt ist.
- Dateinamen wiederholen sich zwischen den Episoden (165 Choreografien, 95 Sprachdatenbanken). Ein immer aktives
  Archiv würde also andere Episoden überschreiben.
- **Lösung:** Eine zweite Beschreibung der Gruppe `SamMax20x` mit `descriptionPriority = 100`, die das deutsche Archiv
  zuerst nennt. Im Test wird das Archiv geöffnet, und die Stimmen haben Vorrang.

## Sprache

- **Alt:** `.vox` mit Speex, 32 kHz. Das erste Paket ist ein Kommentar, kein Ton. Manche Dateien haben am Ende ein
  überzähliges Byte.
- **Remaster:** `.wav`-Einträge, tatsächlich FSB5 mit Vorbis, etwa 8,4 kB/s. Die Nummern unterscheiden sich von denen
  von 2009.
- **Mod:** FSB5 mit IMA-ADPCM (Modus 7, 36-Byte-Blöcke für 64 Samples), 17,6 kB/s. Vorher wurde PCM genutzt; das spielte
  ebenfalls, die Doppler gab es mit beiden Formaten.

## Zuordnung der Zeilen

`english.langdb` (alt) und `*_english.landb` (Remaster) verbinden Nummer, Sprecher und Text. Zugeordnet wird:

1. **exact:** normalisierter Text eindeutig
2. **same text:** Text mehrfach vorhanden, dann gleicher Sprecher und ähnlichste Dauer
3. **close:** Textähnlichkeit ab 0,92, etwa korrigierte Tippfehler

Die Ergebnisse jedes Laufs landen im Arbeitsordner als `epNNN_lines.csv`.

## Lippen-Dateien (`.anm`)

Die Länge steht als Float bei `20 + 12 × Typen + 16`. Die Zeitpunkte stehen in Listen aus `Größe, Anzahl` und 37-Byte-Einträgen.
Für die deutsche Länge wird beides proportional gestreckt.

## Choreografien (`.chore`)

- **Zeitblöcke:** `Start, Ende, Loop-Zeichen, Skalierung` (13 Byte).
- **Keyframes:** `Zeit, Flag, Modus, Wert`. Der Wert kann 1 Byte (Schalter), 4 Byte oder Text sein.
- **Zeitkurve:** Jede Spur hat eine Kurve von 0 bis 1 über ihren Block.
- **Sprachzeile:** Ihr Block ist im Original genau so lang wie die Aufnahme, und ihre Daten enden am ersten Block.
- **Aktiv-Flag:** Das dritte Zeichen hinter dem Block (`00100100` aktiv, `00000100` aus).
- **Verschachtelung:** Eine Choreografie kann eine andere enthalten. `env_office_cs_opening_e1_56` enthält
  `cs_Opening`; die Zeilen der äußeren sind größtenteils abgeschaltet.

### Regeln, die sich im Test ergeben haben

1. **Abgeschaltete Zeilen ignorieren.** Sonst verschiebt sich die Zeitachse ohne Grund.
2. **Eine verschachtelte Szene läuft 1:1.** Äußere und innere Datei brauchen denselben Zeitplan.
3. **Sound nur verschieben, nicht dehnen.**
4. **Alle Keyframes verschieben, auch kurze.** Vergessene Schalter lösten Ereignisse zu früh aus, etwa den Laser in der
   Eröffnung.
5. **Zwischensequenzen pausieren am Zeilenende:** Eine Kurve mit waagerechtem Stück hält Kamera und Figuren an.
   Das wirkte besser als gleichmäßiges Verlangsamen.
6. **Stimmen nicht beschleunigen.** Bewusst verworfen.

Normale Dialoge werden stattdessen während der Zeile leicht gestreckt.

## Was Telltale 2009 gemacht hat

Für drei Szenen von Episode 201 gibt es eigene deutsche Choreografien, darunter `cs_opening.chore`. Sie läuft
80,44 statt 70 s: Lange Animationen wurden gleichmäßig verlangsamt, die Zeilen von Hand gesetzt. Die Musikspur blieb
gleich. Der Ansatz wurde im Remaster versucht und durch die Pausen ersetzt.

## Offene Fragen

- **Woher kommen die Doppler?** Sie treten vor allem bei Kamerawechseln auf. Widerlegt: Doppelung in der Datei, Blöcke
  länger als der Ton, PCM-Datenrate. Eine Aufnahme der Szene und ein Vergleich mit den Sprachdateien wäre der nächste Schritt.
- **Warum läuft die Eröffnung von 201 schlechter als andere Szenen?** Vermutlich wegen ihrer langen Spuren und der
  Verschachtelung, das ist aber nicht belegt.
- **Echte deutsche Lippen:** Die alten `.anm` sind anders kodiert und bisher nicht übernommen.
- **Season 1 und 3:** Noch nicht untersucht.
