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

**folderManager.py** : Quelques fonctions pour la gestion des images importées

**paramStoring.json** : Fichier pour conserver de l’information entre les utilisations

**resources.py, resources.qrc**: fichier pour permettre d’afficher des petites icônes pour l’interface graphique. Les icônes sont dans le dossier Icons. Lorsque que tu installes QT, le script pyrcc5 va s’installer. Il permet de transformer le fichier QRC en fichier PY

**Fichier .UI** : Ces fichiers sont des fichiers a utilisé dans Qt Designer / Qt Creator. QT Designer s’installe sur ton poste lorsque tu installes QGIS. Il permet de faire la configuration de l’interface graphique. On transforme ensuite les fichiers UI en fichier PY avec le script pyuic5

**ui_getVectorLayer.py** : Petite fenêtre pour la sélection de la couche vectoriel

**ui_optionWindow.py** : Gestion de l’interface graphique pour le menu principale, quelques fonctions sur dans le ficher comme le drag and drop pour le fichier d’images ou le modèle numérique de terrain.

**ui_paramWindow.py** : Interface graphique pour le menu des paramètres ainsi que les fonctions pour le faire fonctionner.  

**worldManager.py** : Fichier qui contient les fonctions liées à la stéréoscopie/photogrammétrie. Il permet de transformer un point en coordonnée et vice-versa. Il permet aussi de calculer l’altitude Z à partir des deux images. 
