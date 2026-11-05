# Sam & Max TTG Converter

Bringt die deutschen Stimmen der alten **Sam & Max Season 2** (Telltale, 2009) in das Remaster
**Sam & Max: Beyond Time and Space** von Skunkape Games.

Das Remaster hat deutsche Untertitel, aber nur englische Sprachausgabe. Das Werkzeug liest die eigene
Kopie der alten deutschen Version und baut daraus pro Episode ein zusätzliches Archiv. Keine
Originaldatei des Spiels wird verändert.

> **Status: Prototyp.** Die Episoden 201 bis 204 wurden im Spiel angespielt und laufen laut Test
> größtenteils gut. Episode 205 wurde umgewandelt, im Spiel aber noch nicht getestet.
> Offene Punkte stehen unter [Bekannte Probleme](#bekannte-probleme).

## Benutzung

1. Das Spiel schließen.
2. `SamMaxDeutsch.exe` starten.
3. Die Steam-Fassung wird automatisch gefunden. Sonst den Remaster-Ordner und die alte deutsche Version anklicken und auswählen (installierter Ordner oder gemountete Disc).
4. Episoden wählen und **Deutsche Stimmen installieren** klicken.
5. Im Spiel die Sprache auf Deutsch stellen.

Alle fünf Episoden dauern auf dem Testrechner etwa 10 Minuten und belegen rund 720 MB.
**Fall zu den Akten legen** löscht nach einer Rückfrage alles, was das Werkzeug installiert hat.

Das Fenster braucht die [WebView2-Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) von Microsoft,
die auf aktuellen Windows-Systemen meist schon vorhanden ist. Die Reiter für Season 1 und 3 sind noch gesperrt.

Ohne Fenster:

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --source "<alte deutsche Version>" --episodes 201 202
```

```bash
python src/launcher.py --engine --game "<Remaster-Ordner>" --uninstall
```

## Ergebnis des letzten Laufs

| Episode | Sprachzeilen im Remaster | Deutsch zugeordnet | Zwischensequenzen mit Pausen |
|---|---:|---:|---:|
| 201 | 2.450 | 2.445 | 38 |
| 202 | 1.882 | 1.876 | 41 |
| 203 | 2.322 | 2.312 | 44 |
| 204 | 2.193 | 2.187 | 44 |
| 205 | 2.630 | 2.625 | 75 |
| **Summe** | **11.477** | **11.445** | **242** |

## Bekannte Probleme

- **Doppler:** In Zwischensequenzen werden manchmal Wörter doppelt gesprochen, meist bei Kamerawechseln. Die
  Ursache ist nicht geklärt.
- **Musik:** In der Eröffnung von Episode 201 gibt es Aussetzer. Die Musikspur läuft unverändert durch und passt
  in der längeren Szene nicht mehr ganz zum Bild.
- **Eröffnung von Episode 201:** Sie läuft weniger flüssig als die Zwischensequenzen der anderen Episoden.
- **Stillstand:** Zwischensequenzen halten am Satzende an, wenn die deutsche Zeile länger ist.
- **Zu lange Zeilen:** An 249 Stellen ist eine Zeile länger als ihr Platz und kann am Ende abgeschnitten werden.
- **Lippen:** Die Mundbewegungen sind gestreckte englische Animationen, nicht die alten deutschen.
- **Getestete Versionen:** Bisher nur die Steam-Fassung und eine deutsche Disc-Fassung.

## Aus dem Quellcode bauen

Voraussetzung ist Python 3.10 oder neuer unter Windows. Der Ordner `bin/` braucht drei Dateien, die nicht im
Repository liegen:

- `libspeex-1.dll` aus dem MSYS2-Paket `mingw-w64-x86_64-speex`
- `7z.exe` und `7z.dll` aus einer 7-Zip-Installation

Die Lizenztexte liegen in `licenses/`. Danach:

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

Die Exe landet in `dist/`.

## Was nicht ins Repository gehört

Die alten und neuen Spieldaten sind urheberrechtlich geschützt. Archive, Sprachdateien, Tabellen mit Spieltexten
und die fertige Exe bleiben außerhalb; `.gitignore` schließt sie aus.

**`src/keys.py` enthält die Entschlüsselungs-Schlüssel der Spieldateien.** Vor einer Veröffentlichung des
Repositorys oder der Exe sollte geklärt werden, ob das rechtlich in Ordnung ist. Das gilt auch für
`src/ui/hintergrund.jpg`, das auf Original-Artwork von Sam & Max beruht.

## Aufbau

| Pfad | Inhalt |
|---|---|
| `src/launcher.py` | Einstieg der Exe: Fenster oder Umwandlung |
| `src/gui.py` | Backend des Fensters: Steam-Erkennung, Ordnerauswahl, Umwandlung starten und verfolgen |
| `src/ui/` | Oberfläche im Fallakte-Stil: HTML, CSS, JavaScript, Schriften, Hintergrund |
| `src/sammax_de.py` | Ablauf: Quellen finden, Zeilen zuordnen, umwandeln, installieren |
| `src/old_archive.py`, `src/ttarch4.py` | Archive von 2009 lesen |
| `src/ectt.py`, `src/nctt.py` | Archive des Remasters lesen |
| `src/vox2wav.py`, `src/ima.py` | Sprache dekodieren und neu verpacken |
| `src/anm_patch.py` | Lippen-Dateien strecken |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Zeitachsen der Choreografien |
| `docs/TECHNIK.md` | Dateiformate und Erkenntnisse |
| `research/` | Analyse-Skripte aus der Entwicklung, nicht Teil des Programms |

## Danksagung

Die Schlüssel und Teile des Formatwissens stammen aus den Open-Source-[TTG Tools](https://github.com/HeitorSpectre/TTG-Tools).
Das Werkzeug nutzt [Speex](https://speex.org), [7-Zip](https://www.7-zip.org) und
[pywebview](https://pywebview.flowrl.com), dazu die Schriften Bangers (OFL) und Special Elite (Apache 2.0).

Noch ist keine Lizenz für diesen Code festgelegt.
