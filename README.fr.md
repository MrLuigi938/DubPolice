<p align="center">
  <img src="assets/dub-police.svg" width="96" alt="Logo de Dub Police">
</p>

<h1 align="center">Dub Police</h1>

<p align="center">
  Les anciens jeux Sam &amp; Max parlaient français et allemand. Les remasters ne parlent plus qu'anglais. Dub Police ramène les enregistrements d'origine : pour la saison 1 directement depuis le remaster, pour les saisons 2 et 3 depuis votre ancienne version. De vrais comédiens de doublage, aucune voix d'IA.
</p>

<p align="center">
  <a href="https://blum.ing/dub-police/"><img src="https://img.shields.io/badge/Website-blum.ing%2Fdub--police-a3231b?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Site du projet"></a>
</p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.de.md">Deutsch</a> · <b>Français</b>
</p>

![La fenêtre de Dub Police](docs/images/window-fr.png)
<p align="center"><sub>Capture d'écran avec des dossiers d'exemple</sub></p>

## Points forts

- **Les voix d'origine** – les enregistrements de l'époque, ni nouveau doublage ni IA.
- **Les trois saisons** – Save the World, Beyond Time and Space et The Devil's Playhouse (cette dernière uniquement en allemand).
- **Les scènes attendent la fin de la phrase** – les phrases françaises et allemandes sont souvent plus longues que les anglaises. Les scènes leur laissent la place, pour que personne ne coupe la parole. Les voix ne sont jamais accélérées.
- **Lèvres et rythme suivent** – en allemand, les bouches suivent les mots allemands. En français, les mouvements de bouche anglais sont étirés à la longueur de la nouvelle phrase.
- **Phrases coupées réparées** – dans la saison 1 de 2007, environ un enregistrement sur dix s'arrête au milieu d'un mot. Dub Police utilise une prise complète de la même réplique par le même personnage, ou complète la fin avec la voix du même comédien.
- **Un son propre** – les anciens enregistrements sont soigneusement convertis au format actuel.
- **Votre jeu reste intact** – Dub Police ne fait qu'ajouter des fichiers. Un clic retire tout.
- **Simple** – vos jeux Steam sont trouvés automatiquement. Choisissez la saison, la langue et les épisodes, c'est tout.

## Ce qui est disponible

| Saison | Français | Allemand |
|---|---|---|
| **1** Save the World | ✓ 11 420 répliques sur 11 433 | ✓ 11 421 répliques sur 11 433 |
| **2** Beyond Time and Space | ✓ 11 457 répliques sur 11 477 | ✓ 11 457 répliques sur 11 477 |
| **3** The Devil's Playhouse | – pas de version française | ✓ 10 204 répliques sur 10 217 |

Les rares répliques restantes n'ont pas d'enregistrement ancien correspondant et restent en anglais.

## D'où viennent les anciennes voix

| Saison | Ancienne version nécessaire |
|---|---|
| **1** Save the World | **Rien de plus.** Le remaster contient les anciens épisodes de 2007 pour son mode rétro, dans la langue réglée dans Steam. Dub Police les trouve tout seul. Un disque ou une ancienne version installée fonctionne toujours. |
| **2** Beyond Time and Space | Votre ancienne version : dossier installé ou disque |
| **3** The Devil's Playhouse | Votre ancienne version : dossier installé |

Pour les saisons 2 et 3, les remasters ne contiennent les anciens épisodes qu'en anglais : les voix françaises et allemandes doivent donc venir de votre propre copie.

## Démarrage rapide

**Il vous faut :** Windows et un remaster sur Steam. Pour les saisons 2 et 3, aussi **votre propre copie de l'ancien jeu** dans la langue souhaitée. Elle n'est pas fournie.

1. Téléchargez `DubPolice.zip` depuis la [page des versions](https://github.com/MrLuigi938/DubPolice/releases/latest), décompressez-le dans le dossier de votre choix et fermez le jeu.
2. Lancez `DubPolice.exe` dans ce dossier. Choisissez la saison en haut à gauche et la langue en haut à droite (**Français**).
3. Vérifiez **Témoins**, votre ancienne version. Pour la saison 1, le champ est souvent déjà rempli : Steam installe les anciens épisodes avec le remaster pour son mode rétro, dans la langue choisie pour le jeu dans Steam. Sinon, sélectionnez le dossier installé ou, pour la saison 2, aussi le disque.
4. Choisissez les épisodes et cliquez sur **Installer les voix**. Une saison complète prend environ 12 à 23 minutes et occupe 620 à 810 Mo.
5. Réglez le jeu sur la même langue. Terminé.

## Documentation

| | |
|---|---|
| [Utilisation](docs/fr/usage.md) | Quelle ancienne version il vous faut, changer de langue, tout retirer, limites connues, dépannage |
| [Développement](docs/fr/development.md) | Compiler depuis les sources, fonctionnement, formats de fichiers |

## Bon à savoir

Dub Police est un projet de fan non officiel, sans lien avec Skunkape Games, Telltale Games ou Steve Purcell. Il ne contient aucune donnée de jeu. Il vous faut des copies légales du remaster et de l'ancienne version.

## Remerciements

Une partie des connaissances sur les formats vient des [TTG Tools](https://github.com/HeitorSpectre/TTG-Tools), un projet open source. Dub Police utilise [Speex](https://speex.org), [LAME](https://lame.sourceforge.io) via [lameenc](https://github.com/chrisstaite/lameenc), [NumPy](https://numpy.org), [7-Zip](https://www.7-zip.org) et [pywebview](https://pywebview.flowrl.com), ainsi que les polices Bangers et Special Elite. Leurs licences se trouvent dans [licenses/](licenses).

## Licence

Copyright © 2026 Luis Blum

Dub Police est un logiciel libre sous [licence publique générale GNU v3.0](LICENSE). Vous pouvez l'utiliser, le modifier et le partager, y compris à des fins commerciales, à condition de publier les versions modifiées sous la même licence avec leur code source.

La licence couvre le code propre à Dub Police. Elle ne couvre pas les jeux, leurs enregistrements, leurs noms et leurs personnages, ni l'illustration Sam & Max de l'arrière-plan de la fenêtre. Les composants tiers conservent leurs propres licences, voir [licenses/](licenses).

Dub Police a été créé avec l'aide de l'IA ([Claude](https://claude.ai) d'Anthropic).
