# Utilisation

## Quelle ancienne version il vous faut

Dub Police lit les voix dans votre propre copie de l'ancien jeu, dans la langue souhaitée. Voici ce qui fonctionne :

| Saison | Français | Allemand |
|---|---|---|
| **1** Save the World (2007) | Le remaster lui-même, ou le dossier installé | Le remaster lui-même, ou le dossier installé |
| **2** Beyond Time and Space (2009) | Le dossier installé ou le disque | Le dossier installé ou le disque |
| **3** The Devil's Playhouse (2010) | pas de version française | Le dossier installé |

Sélectionnez le dossier principal de l'ancien jeu. Dub Police y cherche lui-même les bons fichiers. Le disque de la saison 2 contient déjà les deux langues. Vous pouvez monter une image ISO et sélectionner son lecteur.

**Saison 1 sans disque :** pour son mode rétro, Steam installe les anciens épisodes dans le dossier du remaster (`ep101` à `ep106`), dans la langue choisie pour le jeu dans Steam. Dub Police les trouve tout seul et remplit le champ. Ils sont identiques, octet pour octet, à ceux des anciens disques. Les saisons 2 et 3 ne fournissent que les épisodes rétro anglais.

**Astuce :** Dub Police cherche aussi un dossier `Quelldaten` à côté du programme, trié comme `Quelldaten\Französisch\Season 1` ou `Quelldaten\Deutsch\Season 2`. Si vos données s'y trouvent, le champ se remplit tout seul.

## Installation

1. Fermez le jeu. Tant qu'il tourne, Dub Police ne lance pas la conversion.
2. Décompressez `DubPolice.zip` et lancez `DubPolice.exe`. Le dossier `_internal` doit rester à côté. Le premier démarrage peut prendre un moment, le temps que Windows vérifie les nouveaux fichiers.
3. Choisissez la saison en haut à gauche et la langue en haut à droite. Toute la fenêtre change de langue.
4. Vérifiez les deux chemins :
   - **Scène de crime** est votre remaster. Les jeux Steam sont trouvés automatiquement.
   - **Témoins** est votre ancienne version.
5. Choisissez les épisodes et lancez l'installation.
6. Dans le jeu, réglez la langue sur celle que vous avez installée.

Une saison complète prend environ 12 à 23 minutes sur le PC de test et occupe 620 à 810 Mo. Vous pouvez annuler à tout moment. Le jeu n'est modifié qu'à la toute fin, quand tous les épisodes choisis sont prêts.

## Doubler le mode rétro

Les remasters des saisons 2 et 3 contiennent les épisodes d'origine sous forme de mode rétro, mais seulement en anglais. Cochez **Doubler aussi la version rétro** pour qu'ils reçoivent eux aussi les voix et les textes de votre ancienne version. Cela ne prend que quelques minutes. Décochée, le mode rétro reparle anglais.

| Saison | Ce qui est modifié |
|---|---|
| **2** | Voix, textes et scènes adaptées dans les fichiers rétro. Une sauvegarde de la version anglaise reste dans le dossier `DubPolice_Retro` du jeu. Les accents sont retirés (« é » devient « e »), car ce moteur n'affiche pas d'autres caractères. |
| **3** | Un seul fichier supplémentaire `ep30x\Pack\0_0DubPolice.ttarch` par épisode, avec les voix, les textes des dialogues et les scènes adaptées. Il n'existe qu'en allemand. |

**Saison 1 :** Steam fournit déjà les épisodes d'origine dans la langue choisie pour le jeu. Chaque dossier d'épisode contient pourtant aussi une archive anglaise complète, que le jeu préfère. Les voix sont alors jouées avec le minutage anglais et paraissent hachées. **Réparer la version rétro** renomme l'archive anglaise en `SamMax10x_english.ttarch.DubPolice`, et le jeu utilise les scènes correspondantes. Décocher la renomme à nouveau.

## Le badge du menu principal

Après l'installation, un badge Dub Police est collé sur le logo du jeu dans le menu principal du remaster : « Français activé – bon jeu ! » ou « Deutsch aktiv – viel Spaß! », selon la dernière langue installée. Il se trouve dans une petite archive à part. Le logo d'origine reste intact, et **Classer l'affaire** retire le badge.

Dans le mode rétro de la saison 3, les menus sont aussi traduits en allemand.

## La musique pendant les pauses

Quand une cinématique attend une réplique plus longue, la musique s'estompe 0,35 s avant la pause et revient 0,45 s après. Avec **Couper la musique pendant les pauses** décoché, elle continue, mais peut alors se terminer avant la scène. Le réglage vaut pour la prochaine installation.

## Changer de langue

Chaque épisode n'a qu'une langue à la fois. Si vous installez un épisode dans l'autre langue, elle remplace la précédente. Les autres épisodes ne changent pas, et la liste indique la langue de chacun.

## Tout retirer

**Classer l'affaire** supprime, après confirmation, tout ce que Dub Police a ajouté à cette saison. Le jeu reparle alors anglais. Les fichiers d'origine ne sont jamais modifiés.

## Limites connues

- **Les scènes marquent de courtes pauses.** Quand une phrase est plus longue que l'anglaise, la scène attend à la fin de la phrase. Dans les conversations normales, la scène s'étire légèrement à la place.
- **Les lèvres :** en allemand, les formes de bouche sont calculées à partir du texte allemand et du volume de l'enregistrement. Elles suivent les mots, mais ne sont pas animées à la main. En français, elles sont calculées de la même façon à partir du texte français.
- **Phrases coupées dans la saison 1 :** environ un enregistrement sur dix était déjà coupé en 2007, en français comme en allemand. En allemand, environ 930 d’entre eux sont réparés avec une prise complète ou une fin complétée du même comédien. Les autres restent tels quels, faute de correspondance assez bonne. Environ 600 enregistrements n'ont jamais été doublés en 2007 et restent en anglais, comme dans l'ancien jeu.
- **Quelques répliques restent en anglais**, faute d'ancien enregistrement correspondant.
- **Les sous-titres** viennent du remaster et peuvent différer légèrement des anciens enregistrements, car le remaster a en partie de nouvelles traductions.
- **Courts extraits.** Certaines scènes ne jouent qu'une partie d'une autre, comme les visions du futur de l'épisode 301. L'original fait de même, donc une phrase peut s'y arrêter en plein extrait.
- **Mode rétro de la saison 3 :** les courbes de mouvement douces sont brièvement étirées aux pauses au lieu de s'arrêter. Un canal compressé dans 4 pistes, probablement les expressions, garde son ancien minutage.
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
