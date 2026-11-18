# Benutzung

## Welche alte Version du brauchst

Dub Police liest die Stimmen aus deiner eigenen Kopie des alten Spiels, in der gewünschten Sprache. Das funktioniert:

| Season | Deutsch | Französisch |
|---|---|---|
| **1** Save the World (2007) | Das Remaster selbst oder der installierte Ordner | Das Remaster selbst oder der installierte Ordner |
| **2** Beyond Time and Space (2009) | Der installierte Ordner oder die Disc | Der installierte Ordner oder die Disc |
| **3** The Devil's Playhouse (2010) | Der installierte Ordner | keine französische Fassung vorhanden |

Wähle den Hauptordner des alten Spiels. Dub Police sucht darin selbst nach den richtigen Dateien. Die Disc von Season 2 enthält bereits beide Sprachen. Eine ISO kannst du einbinden und ihr Laufwerk auswählen.

**Season 1 ohne Disc:** Für den Retro-Modus installiert Steam die alten Episoden im Ordner des Remasters (`ep101` bis `ep106`), in der Sprache, die in Steam für das Spiel eingestellt ist. Dub Police findet sie selbst und füllt das Feld aus. Sie sind Byte für Byte dieselben wie auf den alten Discs. Season 2 und 3 bringen nur die englischen Retro-Episoden mit.

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

## Retro-Modus vertonen

Die Remaster von Season 2 und 3 bringen die Original-Episoden als Retro-Modus mit, aber nur auf Englisch. Hake **Retro-Version auch vertonen** an, damit auch sie die Stimmen und Texte deiner alten Version bekommen. Das dauert nur wenige Minuten. Entfernst du das Häkchen, spricht der Retro-Modus wieder Englisch.

| Season | Was geändert wird |
|---|---|
| **2** | Stimmen, Texte und angepasste Szenen in den Retro-Dateien. Eine Sicherung der englischen Fassung liegt im Ordner `DubPolice_Retro` im Spielordner. Umlaute stehen ausgeschrieben da („ae“, „oe“, „ue“, „ss“), weil diese Engine keine anderen Zeichen anzeigt. |
| **3** | Nur eine zusätzliche Datei `ep30x\Pack\0_0DubPolice.ttarch` pro Episode, mit Stimmen, Dialogtexten und angepassten Szenen. Die Untertitel zeigen echte Umlaute. |

**Season 1:** Steam liefert die Original-Episoden schon in der Sprache, die für das Spiel eingestellt ist. In jedem Episodenordner liegt aber zusätzlich ein vollständiges englisches Archiv, das das Spiel bevorzugt. Die Stimmen laufen dann mit dem englischen Timing und klingen abgehackt. **Retro-Version reparieren** benennt das englische Archiv in `SamMax10x_english.ttarch.DubPolice` um, dann nutzt das Spiel die passenden Szenen. Ausschalten benennt es zurück.

Im Retro-Modus von Season 3 werden auch die Menüs übersetzt. Wo die deutsche DVD-Fassung Menütexte englisch gelassen hatte, übernimmt Dub Police ihre Übersetzung desselben Begriffs von anderer Stelle oder setzt einen gängigen Begriff ein, etwa „Einstellungen“.

## Abzeichen im Hauptmenü

Nach der Installation klebt im Hauptmenü des Remasters ein Dub-Police-Abzeichen am Spiel-Logo: „Deutsch aktiv – viel Spaß!“ oder „Français activé – bon jeu !“, je nach der zuletzt installierten Sprache. Es steckt in einem eigenen kleinen Archiv. Das Original-Logo bleibt unverändert, und „Fall zu den Akten legen“ entfernt das Abzeichen wieder.

## Musik in Dialogpausen

Wartet eine Zwischensequenz auf einen längeren Satz, blendet die Musik 0,35 s vor der Pause aus und 0,45 s danach wieder ein. Ist **Musik in Dialogpausen ausblenden** aus, läuft sie stattdessen durch, kann dann aber vor dem Ende der Szene fertig sein. Die Einstellung gilt für die nächste Installation.

## Sprache wechseln

Jede Episode hat immer nur eine Sprache. Installierst du eine Episode in der anderen Sprache, ersetzt das die vorige. Andere Episoden bleiben unberührt, und die Liste zeigt, welche Sprache jede hat.

## Alles entfernen

**Fall zu den Akten legen** löscht nach einer Rückfrage alles, was Dub Police in dieser Season hinzugefügt hat. Das Spiel spricht danach wieder Englisch. Originaldateien werden nie verändert.

## Bekannte Grenzen

- **Szenen halten kurz an.** Ist ein Satz länger als der englische, wartet die Szene am Satzende, bis er fertig ist. In normalen Gesprächen wird die Szene stattdessen leicht gestreckt.
- **Lippen:** Die Mundformen werden aus dem deutschen oder französischen Text und der Lautstärke der Aufnahme berechnet. Sie folgen den Worten, sind aber nicht von Hand animiert. Im Retro-Modus von Season 3 bewegen sich die Münder wie im Englischen, weil die deutschen Lippen der DVD nicht zu dieser Engine passen.
- **Abgeschnittene Sätze in Season 1:** Etwa jede zehnte Aufnahme war schon 2007 abgeschnitten, auf Deutsch wie auf Französisch. Auf Deutsch werden rund 930 davon mit einer vollständigen Aufnahme oder einem ergänzten Ende desselben Sprechers repariert. Der Rest bleibt, wie er war, weil nichts gut genug passte. Etwa 600 Aufnahmen wurden 2007 nie synchronisiert und bleiben englisch, wie im alten Spiel.
- **Einige Sätze bleiben englisch**, weil keine alte Aufnahme dazu passt: bei Deutsch 40 in Season 1, 32 in Season 2 und 13 in Season 3.
- **Untertitel** kommen aus dem Remaster und können leicht von den alten Aufnahmen abweichen, weil das Remaster teils neue Übersetzungen hat.
- **Kurze Ausschnitte.** Manche Szenen spielen nur einen Teil einer anderen ab, etwa die Zukunftsvisionen in Episode 301. Das macht auch das Original, dort kann ein Satz mitten im Ausschnitt enden.
- **Retro-Modus von Season 3:** Weiche Bewegungskurven werden an Pausenstellen kurz gestreckt statt angehalten. Ein komprimierter Kanal in 4 Spuren, vermutlich Mimik, behält seine alten Zeiten.
- **Getestet mit** den Steam-Fassungen unter Windows. Alle französischen Episoden wurden gebaut und automatisch geprüft, aber noch nicht gespielt. Im Retro-Modus wurden Season 2 auf Deutsch und mehrere Episoden von Season 3 gespielt.

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
