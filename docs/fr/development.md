# Développement

## Compiler depuis les sources

Il vous faut Python 3.10 ou plus récent sous Windows. Le dossier `bin/` a besoin de trois fichiers qui ne sont pas dans le dépôt :

- `libspeex-1.dll` du paquet MSYS2 `mingw-w64-x86_64-speex`
- `7z.exe` et `7z.dll` d'une installation de 7-Zip

Ensuite :

```bash
powershell -ExecutionPolicy Bypass -File build.ps1
```

Le programme se trouve dans `dist/DubPolice.exe`. Sans fenêtre :

```bash
python src/launcher.py --engine --game "<dossier du remaster>" --source "<ancienne version>" --language french --episodes 101 102
```

```bash
python src/launcher.py --engine --game "<dossier du remaster>" --uninstall
```

`--language` vaut `german` (par défaut) ou `french`. En allemand, `--no-deess` conserve les « s » tels qu'enregistrés.

Les données de jeu n'ont pas leur place dans le dépôt, et `.gitignore` les exclut.

## Organisation du code

| Chemin | Contenu |
|---|---|
| `src/launcher.py` | Point d'entrée de l'exe : fenêtre ou conversion |
| `src/gui.py` | Backend de la fenêtre : trouver les jeux Steam, choisir les dossiers, lancer et suivre une conversion |
| `src/ui/` | La fenêtre : HTML, CSS, JavaScript, polices, arrière-plan |
| `src/sammax_de.py` | La conversion : trouver les sources, associer les répliques, convertir, installer |
| `src/old_archive.py`, `src/ttarch4.py` | Lecture des anciennes archives |
| `src/ectt.py`, `src/nctt.py` | Lecture des archives du remaster |
| `src/vox2wav.py` | Décodage des anciens enregistrements |
| `src/enhance.py` | Traitement du son, de-esser, MP3 dans FSB5 |
| `src/anm_patch.py` | Étirement des fichiers de lèvres |
| `src/chore_warp.py`, `src/chore_fit.py`, `src/port_schedule.py`, `src/curves.py` | Rythme des scènes |
| `src/keys.py` | Clés de déchiffrement des archives du jeu, issues de TTG Tools |
| `assets/` | Le logo en SVG et ICO |

## Fonctionnement

1. Trouver les archives de chaque épisode dans l'ancienne version et, sur un disque, les extraire de l'installateur.
2. Associer chaque réplique du remaster à un ancien enregistrement.
3. Décoder l'enregistrement, traiter le son et l'empaqueter en FSB5.
4. Adapter les fichiers de lèvres et les scènes (chorégraphies) à la nouvelle longueur.
5. Écrire une archive et un fichier de contrôle par épisode dans `Archives`.

### Ajouter une langue

Le processus ne dépend que de la longueur et de l'association des enregistrements. Une nouvelle langue a besoin d'une entrée dans `SEASONS[...]["languages"]`, de son nom dans `SOURCE_FOLDERS` de `gui.py`, de ses textes et de son onglet dans `fallakte.js`, de l'ancienne version et d'un test. Un épisode n'a qu'une langue à la fois, avec des fichiers nommés `*_{Langue}Dub_*`. Sur le disque de la saison 2, l'italien et l'espagnol n'ont que des sous-titres et les voix anglaises.

## Archives

| Format | Marqueur | Utilisation | Chiffrement |
|---|---|---|---|
| `.ttarch` version 2 | Nombre 2 au début | Saison 1 (2007), français et allemand | Table Blowfish ; métadonnées par bloc : un sur 32 en Blowfish, un sur 80 en clair, le reste inversé |
| `.ttarch` sans version | Taille de la table au début | Saison 1, disque anglais (non pris en charge) | comme la version 2 |
| `.ttarch` version 4 | Nombre 4 au début | Saison 2 (2009) | Table Blowfish ; blocs zlib |
| `.ttarch` version 9 | Nombre 9 au début | Saison 3 (2010) | Variante Blowfish de Telltale ; table et blocs en partie compressés |
| `.ttarch2` | `ECTT` | Remaster, compressé | Variante Blowfish de Telltale, puis Deflate par blocs de 64 Ko |
| `.ttarch2` | `NCTT` | Remaster, brut | aucun |

Dans une archive `NCTT`, `4ATT` est suivi de la taille de la table des noms, du nombre de fichiers et de 28 octets par fichier : CRC64 du nom en minuscules (ECMA-182), position, taille, 0, bloc de nom, position du nom. Les entrées sont triées par CRC64, et la table des noms est complétée à 64 Ko.

Chaque ancien épisode a sa propre clé, chaque remaster une clé commune.

## Chargement des archives

Au démarrage, le jeu exécute les `_resdesc_*.lua` du dossier `Archives`.

- **Les fichiers de contrôle doivent être chiffrés** (`ESC LEo`). Ceux qui ne l'étaient pas ont été ignorés lors des tests.
- Les noms de fichiers se répètent entre les épisodes, une archive toujours active écraserait donc les autres épisodes.
- **Solution :** une seconde description du groupe de l'épisode avec `descriptionPriority = 100`, qui cite la nouvelle archive en premier. Elle est dérivée du fichier de contrôle d'origine.

La liste des fichiers installés se trouve dans `SamMax_GermanDub.json` dans le dossier du jeu, quelle que soit la langue.

## Voix

- **2009 et 2010 :** `.vox` en Speex à 32 kHz. En-tête `ERTM`, 20 octets. Le premier paquet est un commentaire, pas du son.
- **2007 :** des `.vox` individuels à côté de l'archive, en-tête `NIBM`, 31 octets. Un paquet sur 64 est chiffré avec la clé de l'épisode, à commencer par le paquet de commentaire. Sans déchiffrement, le décodeur perd 20 ms de son toutes les 1,28 s. Ces dossiers ne contiennent pas d'enregistrements anglais, mais bien les textes anglais.
- **Remaster :** des entrées `.wav` qui sont en réalité du FSB5 avec Vorbis, environ 8,4 ko/s.
- **Sortie :** FSB5 avec MP3 (mode 11), 44,1 kHz, mono, 128 kbit/s. Chaque trame MP3 doit être complétée à 4 octets, sinon FMOD ne décode que les premières trames. L'encodeur retarde le son de 1 105 échantillons (25 ms). Le nombre d'échantillons de l'en-tête vaut `trames × 1152`, les blocs de répliques incluent donc ce retard.

### Traitement du son (`src/enhance.py`)

Mesurés sur 40 répliques de l'épisode 301, les anciens enregistrements sont proches du remaster en niveau et en équilibre. Le traitement est donc discret, et rien n'est synthétisé :

1. **Résolution :** rééchantillonnage à 44,1 kHz.
2. **Égaliseur :** suppression des grondements sous 70 Hz, environ 2,5 dB de présence autour de 3 kHz et entre 14 et 16 kHz.
3. **De-esser (allemand uniquement, désactivable) :** la bande de 4,5 à 12 kHz n'est atténuée que lorsque son niveau dépasse un seuil situé 14 dB sous le niveau de la parole ; rapport 4:1, 10 dB au maximum. En dessous, le niveau change de 0,03 dB au plus. Le côté sifflant vient des anciens enregistrements, pas de l'égaliseur.
4. **Air :** une trace des sifflantes de la voix elle-même au-dessus de 16 kHz, où les anciens enregistrements n'ont plus rien.
5. **Niveau :** +0,5 dB, seuls de rares pics sont limités en douceur.

## Association des répliques

`english.langdb` ou `*_english.landb` relient numéro, personnage et texte. Pour la saison 3, les numéros de l'ancienne version et du remaster sont en grande partie identiques. Sinon, l'association se fait dans cet ordre :

1. **exact :** texte normalisé unique
2. **same text :** plusieurs correspondances, puis même personnage et durée la plus proche
3. **close :** similarité de texte d'au moins 0,92, par exemple des fautes corrigées

Les résultats de chaque passage sont écrits dans le dossier de travail sous le nom `epNNN_lines.csv`.

**Enregistrements empruntés :** après son numéro et son hash, une entrée de langue a deux champs CRC64 pour `.anm` et `.wav`. S'ils sont remplis, elle pointe vers l'enregistrement d'une autre réplique ; sinon son propre numéro s'applique. Ces entrées n'ont pas de fichier propre, mais leurs chorégraphies ont quand même besoin de la nouvelle longueur, sinon la phrase s'arrête à la longueur anglaise. Dans les saisons 2 et 3, cela concernait environ 640 chorégraphies, surtout des conversations et des interactions.

## Fichiers de lèvres (`.anm`)

La longueur est un flottant à `20 + 12 × types + 16`. Les instants se trouvent dans des listes `taille, nombre` avec des entrées de 37 octets. Les deux sont étirés proportionnellement.

## Chorégraphies (`.chore`)

- **Blocs de temps :** `début, fin, caractère de boucle, échelle` (13 octets).
- **Images clés :** `temps, drapeau, mode, valeur`. La valeur peut faire 1 octet (interrupteur), 4 octets ou être un texte.
- **Courbe de temps :** chaque piste a une courbe de 0 à 1 sur son bloc.
- **Réplique :** dans l'original, son bloc a exactement la longueur de l'enregistrement.
- **Drapeau d'activité :** le troisième caractère après le bloc (`00100100` actif, `00000100` inactif).
- **Imbrication :** une chorégraphie peut en contenir une autre. Sa courbe de temps compte en fractions de la longueur de la chorégraphie interne.

### Règles issues des tests

1. **Ignorer les répliques désactivées.** Sinon la chronologie se décale sans raison.
2. **Une scène imbriquée joue 1:1.** Le fichier externe et l'interne ont besoin du même calendrier.
3. **Déplacer les sons, sans les étirer.**
4. **Déplacer toutes les images clés, même courtes.** Des interrupteurs oubliés déclenchaient des événements trop tôt.
5. **Les cinématiques marquent une pause en fin de réplique :** une courbe avec une partie plate immobilise caméra et personnages. C'était mieux qu'un ralentissement uniforme.
6. **Ne jamais accélérer les voix.**
7. **Conserver les chevauchements.** Les répliques qui se chevauchent déjà dans l'original, comme les interruptions, ne sont pas coupées au début de la suivante.
8. **Les pauses traversent tous les niveaux.** Une scène externe reprend les pauses de la scène interne, même sans réplique propre. La courbe de temps est lue par morceaux, car beaucoup ont plus de deux points. Seules les parties à plus du double ou à moins de la moitié de la vitesse ne sont pas reprises.
9. **Une pause doit finir avant la fin de son bloc et de sa réplique.** Sinon la fin tombe dans la courte rampe de la pause et ne se déplace que d'une fraction, ce qui coupe la phrase et passe à la scène suivante.
10. **Une piste se termine au nom ou à la réplique suivante.** Sinon la correction du son réécrit les blocs des répliques suivantes avec la longueur anglaise.

Les conversations normales s'étirent plutôt légèrement pendant la réplique.

## Questions ouvertes

- **Mots doublés :** d'anciennes versions répétaient parfois des mots dans les cinématiques, surtout aux changements de caméra. La cause n'a jamais été trouvée. Ils n'ont plus été signalés avec la méthode de pauses actuelle.
- **Vraies lèvres :** les anciens `.anm` sont codés autrement et ne sont pas encore utilisés.
- **Chorégraphies allemandes de 2010 :** la saison 3 contient ses propres chorégraphies allemandes, qui pourraient servir de modèle de rythme. Cela n'a pas été étudié.
