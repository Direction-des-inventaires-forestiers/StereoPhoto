# StereoPhoto
StereoPhoto est une extension expérimentale disponible dans QGIS qui permet la visualisation d'une paire de photographies aériennes en stéréoscopie.
L'application a été développée par la Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts).

Pour toute question supplémentaire ou si vous désirez participer au développement de StereoPhoto, contacter l'adresse suivante : inventaires.forestiers@mrnf.gouv.qc.ca 

# Installation 
L'extension est disponible dans le menu Extensions -> Intaller/Gérer les extensions de QGIS. Il faut s'assurer que la cocher la case Afficher les extensions expérimentales dans la section Paramètres du menu Extensions. Ensuite, faire la recherche de StereoPhoto dans la fenêtre Toutes du menu et puis l'installer. 

# Utilisation
Pour utiliser l'application, il est nécessaire d'ajouter un dossier d'images qui contient les fichiers de format TIF ainsi que leur fichier PAR dans l'application. Le fichier PAR associé doit avoir le même nom que son fichier TIF. Il est possible de naviguer entre les images avec une navigation fluide.

Un rehaussement peut être appliquer sur les images observés. Le contraste, la luminosité, la saturation et la netteté peuvent être modifier. Il est possible d'ajouter l'intensité des pixels rouges, verts et bleus. Il est aussi possible d'appliquer un filtre min/max pour une zone sélectionnée. 

Pour le bon fonctionnement, il est nécessaire d'avoir un stéréorestituteur (Type Planar) formé de deux moniteurs séparés d’un miroir semi-transparent ainsi que des lunettes polarisées appropriées. Il est important de faire la sélection des écrans dans le menu des paramètres de l'extension. L'image qui est appelée l'image de gauche dans l'application représente l'image qui doit apparaître sur l'écran du bas du stéréorestituteur. L'application fonctionne sans carte graphique compatible avec l’affichage stéréoscopique et ne fonctionne pas pour un système actif de vision stéréoscopique. 

Il est possible de faire l'affichage de vecteurs sur les images. Tout simplement importer une couche vectorielle dans QGIS pour pouvoir la sélectionner dans l'application. Le positionnement des polygones de la couche vectorielle peut être améliorer avec l'ajout d'un modèle numérique de terrain qui peut être importer dans l'application via un fichier de format TIF ou VRT. L'ajout d'un modèle numérique de terrain est recommandé mais pas obligatoire. Le modèle numérique de terrain permet aussi de dessiner un nouveau polygone et de découper des polygones existants. Il est important que tous les fichiers utilisés (la couche vectorielle, le modèle numérique de terrain et le fichier PAR) soit sur le même système de coordonnées.  