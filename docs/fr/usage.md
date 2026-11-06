# Utilisation

## Quelle ancienne version il vous faut

Dub Police lit les voix dans votre propre copie de l'ancien jeu, dans la langue souhaitée. Voici ce qui fonctionne :

| Saison | Français | Allemand |
|---|---|---|
| **1** Save the World (2007) | Le dossier installé | Le dossier installé |
| **2** Beyond Time and Space (2009) | Le dossier installé ou le disque | Le dossier installé ou le disque |
| **3** The Devil's Playhouse (2010) | pas de version française | Le dossier installé |

Sélectionnez le dossier principal de l'ancien jeu. Dub Police y cherche lui-même les bons fichiers. Le disque de la saison 2 contient déjà les deux langues. Vous pouvez monter une image ISO et sélectionner son lecteur.

**Astuce :** Dub Police cherche aussi un dossier `Quelldaten` à côté du programme, trié comme `Quelldaten\Französisch\Season 1` ou `Quelldaten\Deutsch\Season 2`. Si vos données s'y trouvent, le champ se remplit tout seul.

## Installation

1. Fermez le jeu. Tant qu'il tourne, Dub Police ne lance pas la conversion.
2. Lancez `DubPolice.exe`. Le premier démarrage peut prendre jusqu'à une demi-minute, le temps que Windows vérifie le nouveau fichier.
3. Choisissez la saison en haut à gauche et la langue en haut à droite. Toute la fenêtre change de langue.
4. Vérifiez les deux chemins :
   - **Scène de crime** est votre remaster. Les jeux Steam sont trouvés automatiquement.
   - **Témoins** est votre ancienne version.
5. Choisissez les épisodes et lancez l'installation.
6. Dans le jeu, réglez la langue sur celle que vous avez installée.

Une saison complète prend environ 12 à 23 minutes sur le PC de test et occupe 620 à 810 Mo. Vous pouvez annuler à tout moment. Le jeu n'est modifié qu'à la toute fin, quand tous les épisodes choisis sont prêts.

## Changer de langue

Chaque épisode n'a qu'une langue à la fois. Si vous installez un épisode dans l'autre langue, elle remplace la précédente. Les autres épisodes ne changent pas, et la liste indique la langue de chacun.

## Tout retirer

**Classer l'affaire** supprime, après confirmation, tout ce que Dub Police a ajouté à cette saison. Le jeu reparle alors anglais. Les fichiers d'origine ne sont jamais modifiés.

## Limites connues

- **Les scènes marquent de courtes pauses.** Quand une phrase est plus longue que l'anglaise, la scène attend à la fin de la phrase. Dans les conversations normales, la scène s'étire légèrement à la place.
- **Les lèvres** sont des animations anglaises étirées, pas les anciennes animations françaises ou allemandes.
- **Quelques répliques restent en anglais**, faute d'ancien enregistrement correspondant.
- **Les sous-titres** viennent du remaster et peuvent différer légèrement des anciens enregistrements, car le remaster a en partie de nouvelles traductions.
- **Courts extraits.** Certaines scènes ne jouent qu'une partie d'une autre, comme les visions du futur de l'épisode 301. L'original fait de même, donc une phrase peut s'y arrêter en plein extrait.
- **La musique** peut se décaler légèrement de l'image dans les longues scènes, car elle continue pendant que la scène attend.
- **Testé avec** les versions Steam sous Windows. Tous les épisodes français ont été construits et vérifiés automatiquement, mais pas encore joués.
- **Le correcteur de « s » sifflants** n'existe que pour l'allemand. En français, les voix restent telles quelles sur ce point.

## Dépannage

| Problème | Solution |
|---|---|
| Le jeu parle toujours anglais | Réglez la langue du jeu sur celle que vous avez installée, puis redémarrez-le. |
| « Bitte zuerst das Spiel schließen » | Le jeu tourne encore. Fermez-le et réessayez. |
| « kein unterstützter Remaster-Ordner » | Sélectionnez le dossier principal du remaster, celui qui contient `SamMax100.exe`, `SamMax200.exe` ou `SamMax300.exe`. |
| « nicht vollständig gefunden » | Il manque des fichiers pour cette langue et ces épisodes dans le dossier choisi. Vérifiez que la version est bien dans cette langue. |
| Le bouton d'installation reste gris | Vérifiez les deux chemins et choisissez au moins un épisode. |
| La fenêtre ne s'ouvre pas | Installez le [runtime WebView2](https://developer.microsoft.com/microsoft-edge/webview2/) de Microsoft. |
| Windows affiche un avertissement | Le programme n'est pas signé, Windows peut donc vous avertir. |

La fenêtre est en français, mais les messages de la conversion elle-même restent en allemand, y compris les détails d'erreur.
