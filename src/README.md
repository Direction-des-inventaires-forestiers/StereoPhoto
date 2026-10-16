# Explication des fichiers de StereoPhoto
**stereophoto.py** : Ce fichier est le fichier principal de l’application, il contrôle les différentes interfaces graphiques. Le fichier contient beaucoup de fonction pour différente fonctionnalités. Du haut vers le bas, voici ce que les fonctionnalités gérer par le fichier. 

- Initialisation des variables et connexion des actions de l’interface graphique principale (menu optionWindow qui apparait dans QGIS quand on ouvre l’extension)

- Gestion de l’importation d’un nouveau fichier d’image, on parcourt le dossier pour trouver les images et leur fichier PAR. On trouve les paires d’images possible ainsi que les 4 voisins de chaque image.

- Création des « graphicsWindow » qui affiche la paire d’image, les fenêtres vont interagir avec la souris et le clavier. Les images sont chargées en qualité réduite pour commencer afin d’avoir un aperçu, le chargement de l’image avec la meilleure qualité se fait par thread qui charge une petite zone à la fois pour que la zone visualisée par l’utilisateur soit chargée en premier si possible. L’interface graphique se trouve dans le fichier ui_graphicsWindow.py 

- Gestion de l’importation d’un fichier vectoriel, il doit être déjà ouvert dans QGIS. Le SIG du fichier vectoriel sélectionner sera appliquer à QGIS directement puisqu’on ne peut pas le déterminer avec les images et les fichiers PAR

- Gestion de l’affichage des polygones

- Gestion de la sélection de la fenêtre, du clavier et de la souris

- Fonction pour calculer une coordonnée à partir d’un point sur l’image

- Gestion du curseur qui suit la position en temps réel dans QGIS

**init.py, metadata.txt** : obligatoire pour tous les plugins QGIS

**drawFunction.py** : Fichier pour les fonctions lié à la gestion de la couche vectorielle. Les fonctions pour éditer les polygones sont dans ce fichier

**enhanceManager.py** : Fichier pour l’interface graphique de rehaussement et pour les fonctions de rehaussement. La classe imageEnhancing fait le rehaussement. Le dossier Rehaussement contient l’application de rehaussement qui peut être utiliser de manière indépendante. Dans le passé, j’ai développé l’application de rehaussement qui permettait de rehausser des images et de les enregistrer. J’ai par la suite ajouté le module de rehaussement directement dans l’application. Ui_enhancement.py contient le code pour l’interface graphique

**paramStoring.json** : Fichier pour conserver de l’information entre les utilisations

**resources.py, resources.qrc**: fichier pour permettre d’afficher des petites icônes pour l’interface graphique. Les icônes sont dans le dossier Icons. Lorsque que tu installes QT, le script pyrcc5 va s’installer. Il permet de transformer le fichier QRC en fichier PY

**Fichier .UI** : Ces fichiers sont des fichiers a utilisé dans Qt Designer / Qt Creator. QT Designer s’installe sur ton poste lorsque tu installes QGIS. Il permet de faire la configuration de l’interface graphique. On transforme ensuite les fichiers UI en fichier PY avec le script pyuic5

**ui_getVectorLayer.py** : Petite fenêtre pour la sélection de la couche vectoriel

**ui_widgetStereoPhoto.py** : Gestion de l’interface graphique pour le menu principal et pour le menu des paramètres, avec les fonctions qui les font fonctionner. On y trouve aussi quelques fonctions comme le drag and drop pour le fichier d’images ou le modèle numérique de terrain. La classe optionWindow est celle que stereoPhoto.py utilise. Ce fichier portait auparavant les noms ui_optionWindow.py et ui_paramWindow.py.

**gestionDossier.py** : Fichier pour le parcours d’un dossier de photos : lecture des fichiers PAR, recherche des paires possibles, des quatre voisins de chaque image et de la paire la plus proche d’une coordonnée. Le calcul du chevauchement entre deux photos s’y trouve également.

**parFile.py** : Lecture des fichiers PAR, au même endroit pour tous les modules. Le fichier PAR accompagne chaque photo et décrit la caméra qui l’a prise : transformation affine, focale, position, orientation, taille du pixel. Le module ne dépend ni de QGIS ni de Qt, ce qui le rend directement testable.

**config.py** : Les valeurs qui influencent l’affichage et la navigation, regroupées en un seul endroit et nommées avec leur rôle et leur unité : tolérance d’orientation de la caméra, tampons de recherche des paires, chevauchement minimal, épaisseurs de trait, rayon des points, réglages du journal.

**journal.py** : Journalisation de l’extension dans des fichiers, sous le profil QGIS de l’utilisateur (`stereophoto/logs`). Un fichier par jour, archivé au changement de journée et conservé 90 jours. Les messages vont aussi dans l’onglet StereoPhoto du panneau des journaux de QGIS. À utiliser à la place de print(), dont la sortie est perdue hors de la console Python.

**worldManager.py** : Fichier qui contient les fonctions liées à la stéréoscopie/photogrammétrie. Il permet de transformer un point en coordonnée et vice-versa. Il permet aussi de calculer l’altitude Z à partir des deux images. 

**ui_graphicsWindow.py** : Fichier qui contient un object QGraphicsView qui permet l'affichage d'un image. Il fait la gestion de l'affichage des différentes pyramides d'images, du curseur et du déplacement lors de la navigation¸

**navigationQgsMapTool.py** : Outil MapTool compatible avec QGIS qui permet d'envoyer les signals de clavier et de souris ainsi que d'emprisonner la souris à l'intérieur du canvas QGIS