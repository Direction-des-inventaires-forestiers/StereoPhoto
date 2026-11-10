# StereoPhoto
StereoPhoto est une extension QGIS pour la photo-interprétation qui permet la visualisation d'une paire de photographies aériennes en stéréoscopie. L'application a été développée par la Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts, Québec).

Pour toute question supplémentaire ou si vous désirez participer au développement de StereoPhoto, contacter l'adresse suivante : inventaires.forestiers@mrnf.gouv.qc.ca 

# Première utilisation

Afin de faciliter l'installation ainsi que la première utilisation, il est recommandé d'utiliser [le guide d'utilisation.](guideUtilisationStereoPhoto_v0_2_0.pdf) Le guide peut être utilisé pour envoyer des commentaires à notre adresse courriel. 

Sans avoir recours au guide d'utilisation voici les éléments importants à considérer lors de la première utilisation : 

- Les fichiers d'orientation (.PAR) doivent se situer dans le même dossier que les photographies aériennes (.TIF)
- Le système de coordonnées de référence (SCR) à utiliser doit être imposé avant de lancer la navigation
- Pour une navigation en stéréoscopie fonctionnelle, QGIS ne doit pas être dans son état initial, le canevas doit être activé via l'ajout d'une couche quelconque
- L'ajout d'une couche vectorielle via le menu des couches de l'application changera automatiquement le système de coordonnées, à condition que la couche soit dans un système projeté ; une couche en coordonnées géographiques est refusée
- Les images, les couches vectorielles et le modèle numérique de terrain doivent tous utiliser le même système de coordonnées
- La sélection manuelle des écrans du stéréoscope doit se faire via le choix de leur numéro d'écran, le bouton **Voir Écran** permet d'aider à la sélection 
- Pour faire l'affichage de couches vectorielles lors de la navigation, elles doivent être ajoutées et être actives dans QGIS
- L'importation d'un modèle numérique de terrain permet d'afficher et d'éditer les couches avec une plus grande précision

# Navigation

Deux comportements de navigation, et un troisième état.

**Les photos se déplacent sous le curseur**, qui reste au centre de la vue (Défaut). 

**Le curseur se déplace sur les photos**, qui restent fixes. Le bouton **Débarrer le curseur** de la barre d'outils, ou la touche `C`, bascule d'un comportement à l'autre en cours de session.

**Hors synchronisation.** `Échap` quitte les photos pour QGIS. Les deux vues restent affichées et suivent le canevas, mais ne le commandent plus :

- la roulette zoome, au lieu de régler la parallaxe ;
- le bouton du milieu déplace la carte, comme la navigation principale de QGIS ;
- le modèle photo change de lui-même quand la vue atteint la limite du modèle affiché, le voisin étant choisi selon l'orientation de la caméra ;
- les raccourcis de QGIS répondent de nouveau, l'interception du clavier étant levée le temps de cet état.

`Échap` ramène à la navigation synchronisée. Choisir un outil dans une barre d'outils de QGIS en sort également, comme pour n'importe quel outil de carte.

# Édition des couches vectorielles

Quatre outils, dans la barre d'outils de l'extension. L'outil **Ajouter** est actif à l'ouverture d'une session.

| Outil | Geste | Couches |
|---|---|---|
| **Sélectionner** | Le clic gauche désigne l'entité sous le curseur, le clic droit vide la sélection. `Ctrl` ou `Maj` ajoute à la sélection au lieu de la remplacer | points, lignes, polygones |
| **Ajouter** | Un clic pose un point ou démarre le traçade d'une ligne, ou d'un polygone. le clic droit clôt le traçage | points, lignes, polygones |
| **Combiner** | Les clics gauches désignent les entités, le clic droit les réunit en une seule, qui garde les attributs de la première | points, lignes, polygones |
| **Découper** | La ligne de coupe se trace sommet par sommet, et le clic droit l'applique aux entités traversées de part en part | polygones |

Toujours sur le fonctionnement, l'entité désignée est mise en évidence dans les deux vues photo autant que dans le canevas. La sélection de QGIS et celle de l'extension sont la même et une entité sélectionnée dans la table d'attributs s'allume donc aussi dans les photos.

Ce qu'il faut savoir de l'écriture :

- la session d'édition de la couche s'ouvre au premier geste et reste ouverte. Rien n'est écrit dans le fichier avant un enregistrement explicite, par `Ctrl+S` ou par le bouton **Enregistrer** ;
- `Ctrl+Z`, ou le bouton **Annuler**, défait un geste complet. Note : une fusion revient d'un coup, avec l'entité qu'elle avait absorbée ;
- à la fermeture de la session, ou au changement de couche, l'extension propose d'enregistrer ce qui reste en attente. Décliner la sauvegarde ne perd rien, car le tampon appartient à la couche et QGIS le conserve jusqu'à son enregistrement ;
- sur une couche qui porte une altitude (Z), la cote écrite est celle du curseur, celle qu'affiche la croix. Quand elle est indéterminée, l'écriture est refusée avec un message : régler la parallaxe à la roulette, ou activer le suivi du modèle numérique de terrain par la touche `M` ;
- un tracé sous **Ajouter** produit toujours une entité neuve, même s'il touche ou recoupe ses voisines.

Le choix de l'outil se fait dans la barre d'outils, ou par les touches `1` à `4`, selon les paramètres de l'extension.

# Raccourcis clavier

Pendant la navigation stéréo, l'extension intercepte tout le clavier : les raccourcis de QGIS ne répondent pas, et ceux du tableau ci-dessous sont le seul accès clavier aux outils.

| Touche | Action |
|---|---|
| `Échap` | Basculer entre QGIS et les photos, dans les deux sens |
| `F5` à `F12` | Les huit niveaux de zoom, du plus fort (`F5`) à l'image entière (`F12`) |
| `1` | Outil Sélectionner |
| `2` | Outil Ajouter |
| `3` | Outil Combiner |
| `4` | Outil Découper |
| `M` | Suivre le modèle numérique de terrain |
| `C` | Débarrer le curseur |
| `Ctrl+Z` | Annuler le dernier geste d'édition |
| `Ctrl+S` | Enregistrer les modifications de la couche |

Chaque bouton de la barre d'outils annonce sa touche dans son infobulle, et celle du bouton **Naviguer** rappelle les raccourcis de la navigation. Les infobulles suivent le tableau : si une touche est changée, elles l'annoncent.

## Changer une touche

Les touches se modifient dans la section `raccourcis` du fichier `paramStoring.json`, qui se trouve dans le dossier de l'extension, sous le profil QGIS. Une touche s'écrit par son nom : une lettre, un chiffre, `Échap`, `F1` à `F12`, une flèche (`Gauche`, `Droite`, `Haut`, `Bas`), `Espace`, `Tab`, `Retour`, `Retour arrière`, `Suppr`, `Inser`, `Début`, `Fin`, `PgHaut`, `PgBas`, `+` ou `-`. La casse et les accents sont sans importance, et `Ctrl` ou `Alt` peuvent précéder le nom, par exemple `Ctrl+M`.

Le changement prend effet à l'ouverture de la session suivante ; il n'est pas nécessaire de recharger l'extension. Une valeur laissée vide retire la touche de l'action, qui reste accessible par son bouton.

Une touche mal orthographiée, ou affectée à deux actions, n'empêche jamais une session de s'ouvrir : la valeur par défaut s'applique, un message paraît dans le bandeau de QGIS et le détail est inscrit dans l'onglet **StereoPhoto** du panneau des journaux. Le fichier n'est pas corrigé automatiquement, afin que la ligne fautive reste visible et puisse être relue.

Deux mises en garde. Le zoom est un groupe de huit touches, à donner en entier : une liste d'une autre longueur est ignorée et les huit touches par défaut s'appliquent. Et le déploiement de l'extension, qui recopie le dossier des sources dans le profil QGIS, écrase ce fichier comme il écrase les autres paramètres : conserver une copie des touches personnalisées avant une mise à jour.

Une interface de configuration de ces touches est prévue ; d'ici là, le fichier de paramètres est le seul moyen de les changer.

# Faire un signalement

Si vous rencontrez un problème ou avez une question concernant le logiciel, il est possible de créer un nouveau billet dans la section **Issues**. Quatre types de billets sont disponibles : 

- Nouvelle fonctionnalité
- Question générale
- Question sur les fonctionnalités existantes
- Signaler un problème

# Contribuer au code

Le code Python suit la norme PEP 8. Elle est appliquée par [ruff](https://docs.astral.sh/ruff/), qui met le code en forme et signale les défauts réels : les règles retenues et la raison de chaque choix sont dans `pyproject.toml`.

Installation, une seule fois par poste :

```bash
pip install pre-commit
pre-commit install
git config blame.ignoreRevsFile .git-blame-ignore-revs
```

Ensuite, à retenir :

- Le commit s'arrête si le code n'est pas conforme. Quand ruff a corrigé le fichier lui-même, relire la correction, faire `git add` et relancer le commit ; sinon, corriger ce qu'il indique.
- Pour vérifier tout le dépôt sans committer : `pre-commit run --all-files`.
- Les mêmes vérifications sont rejouées sur chaque demande de tirage par le flux `Style` : un commit fait avec `--no-verify` y sera signalé.
- La dernière commande d'installation écarte le commit de reformatage initial de la vue *blame*, pour que chaque ligne reste attribuée à son dernier changement réel.
- Trois fichiers de `src/` sont hors contrôle parce qu'ils sont générés, par pyrcc5 ou pyuic5 : `resources.py`, `ui_enhancement.py` et `ui_getVectorLayer.py`. Ils se régénèrent, ils ne se corrigent pas à la main. Les dossiers `NavigationSansGeoRef` et `Rehaussement`, qui sont des applications distinctes, sont également exclus.
- Quand un constat est justifié mais que le code doit rester tel quel, l'écarter ligne par ligne avec `# noqa: CODE` suivi de la raison. C'est le cas de `from . import resources`, jamais utilisé en apparence, mais qui enregistre les icônes auprès de Qt.
- Pour passer à une version plus récente de ruff : `pre-commit autoupdate`, puis committer `.pre-commit-config.yaml`. La version est figée là pour que tous les postes et le flux `Style` appliquent les mêmes règles.

# Exécuter les tests automatisés

Les tests du dossier `tests/` s'exécutent un par un, sans QGIS ni dépendance à installer. Ils lisent le module visé dans `src/` et sortent avec un code non nul en cas d'échec.

```bash
python tests/executer_tous.py
```

Le lanceur enchaîne tous les fichiers du dossier, agrège les codes de sortie et compte les contrôles. Un fichier s'exécute aussi seul, pour ne rejouer qu'un module :

```bash
python tests/test_raccourcis_clavier.py
```

Les mêmes tests sont rejoués sur chaque demande de tirage par le flux `Tests`, à côté du flux `Style`.

# Fichier de test

Un fichier contenant une paire d'image ainsi que les fichiers «.par» associés est disponible sur [ce dépôt.](fichierTest/) Ce fichier démontre comment le dossier d'image devrait être assemblé pour être compatible avec l'application. 

Les valeurs du fichier «.par» qui sont obligatoires pour le fonctionnement de l'application sont les suivantes : 

- $PARAFFINE00
- $PARINVAFF00 
- $FOC00 
- $XYZ00
- $OPK00

Les valeurs du fichier «.par» qui sont facultatives : 

- $FSCALE00
- $PPA
- $PIXELSIZE
