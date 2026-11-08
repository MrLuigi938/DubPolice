# Benutzung

## Welche alte Version du brauchst

Dub Police liest die Stimmen aus deiner eigenen Kopie des alten Spiels, in der gewünschten Sprache. Das funktioniert:

| Season | Deutsch | Französisch |
|---|---|---|
| **1** Save the World (2007) | Der installierte Ordner | Der installierte Ordner |
| **2** Beyond Time and Space (2009) | Der installierte Ordner oder die Disc | Der installierte Ordner oder die Disc |
| **3** The Devil's Playhouse (2010) | Der installierte Ordner | keine französische Fassung vorhanden |

Wähle den Hauptordner des alten Spiels. Dub Police sucht darin selbst nach den richtigen Dateien. Die Disc von Season 2 enthält bereits beide Sprachen. Eine ISO kannst du einbinden und ihr Laufwerk auswählen.

**Tipp:** Dub Police sucht auch nach einem Ordner `Quelldaten` neben dem Programm, sortiert wie `Quelldaten\Deutsch\Season 1` oder `Quelldaten\Französisch\Season 2`. Liegen deine Daten dort, füllt sich das Feld von selbst.

## Installieren

1. Das Spiel schließen. Solange es läuft, startet Dub Police die Umwandlung nicht.
2. `DubPolice.zip` entpacken und `DubPolice.exe` starten. Der Ordner `_internal` muss daneben liegen bleiben. Der erste Start kann etwas dauern, weil Windows die neuen Dateien prüft.
3. Oben links die Season und oben rechts die Sprache wählen. Das ganze Fenster wechselt mit.
4. Die beiden Pfade prüfen:
   - **Tatort** ist dein Remaster. Steam-Spiele werden von selbst gefunden.
   - **Zeugen** ist deine alte Version.
5. Episoden wählen und die Installation starten.
6. Im Spiel die installierte Sprache einstellen.

Eine ganze Season dauert auf dem Testrechner etwa 12 bis 23 Minuten und belegt 620 bis 810 MB. Du kannst jederzeit abbrechen. Das Spiel wird erst ganz am Ende geändert, wenn alle gewählten Episoden fertig sind.

### Scharfe S-Laute (nur Deutsch)

Die alten deutschen Aufnahmen haben recht scharfe S-Laute. **Scharfe S-Laute abmildern** dämpft sie nur in dem Moment, in dem sie erklingen, und lässt den Rest der Stimme in Ruhe. Der Schalter ist vorausgewählt. Ausgeschaltet bleiben sie wie aufgenommen.

## Sprache wechseln

Jede Episode hat immer nur eine Sprache. Installierst du eine Episode in der anderen Sprache, ersetzt das die vorige. Andere Episoden bleiben unberührt, und die Liste zeigt, welche Sprache jede hat.

## Alles entfernen

**Fall zu den Akten legen** löscht nach einer Rückfrage alles, was Dub Police in dieser Season hinzugefügt hat. Das Spiel spricht danach wieder Englisch. Originaldateien werden nie verändert.

## Bekannte Grenzen

- **Szenen halten kurz an.** Ist ein Satz länger als der englische, wartet die Szene am Satzende, bis er fertig ist. In normalen Gesprächen wird die Szene stattdessen leicht gestreckt.
- **Lippen** sind gestreckte englische Animationen, nicht die alten deutschen oder französischen.
- **Einige Sätze bleiben englisch**, weil keine alte Aufnahme dazu passt: bei Deutsch 40 in Season 1, 32 in Season 2 und 13 in Season 3.
- **Untertitel** kommen aus dem Remaster und können leicht von den alten Aufnahmen abweichen, weil das Remaster teils neue Übersetzungen hat.
- **Kurze Ausschnitte.** Manche Szenen spielen nur einen Teil einer anderen ab, etwa die Zukunftsvisionen in Episode 301. Das macht auch das Original, dort kann ein Satz mitten im Ausschnitt enden.
- **Musik** kann in langen Szenen leicht vom Bild abweichen, weil sie weiterläuft, während die Szene wartet.
- **Getestet mit** den Steam-Fassungen unter Windows. Alle französischen Episoden wurden gebaut und automatisch geprüft, aber noch nicht gespielt.

## Hilfe bei Problemen

| Problem | Lösung |
|---|---|
| Das Spiel spricht weiter Englisch | Im Spiel die installierte Sprache einstellen und das Spiel neu starten. |
| „Bitte zuerst das Spiel schließen“ | Das Spiel läuft noch. Schließen und erneut versuchen. |
| „kein unterstützter Remaster-Ordner“ | Den Hauptordner des Remasters wählen, also den mit `SamMax100.exe`, `SamMax200.exe` oder `SamMax300.exe`. |
| „nicht vollständig gefunden“ | Im gewählten Ordner fehlen Dateien für diese Sprache und diese Episoden. Prüfe, ob die Version wirklich in dieser Sprache vorliegt. |
| Der Installieren-Knopf bleibt grau | Beide Pfade prüfen und mindestens eine Episode wählen. |
| Das Fenster öffnet sich nicht | Die [WebView2-Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) von Microsoft installieren. |
| Windows warnt vor der Datei | Das Programm ist nicht signiert, deshalb kann Windows warnen. |
