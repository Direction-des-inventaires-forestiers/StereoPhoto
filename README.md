# Sterephoto
StereoPhoto est une application expérimentale disponible dans QGIS qui permet la visualisation d'une paire d'image en stéréoscopie.
L'application a été développée par la Direction des Inventaires Forestiers (MRNF).

Pour toute question supplémentaire, contacter l'adresse suivante : Frederick.Pineault@mrnf.gouv.qc.ca 

# Installation 
La librairie python [qimage2ndarray](https://pypi.org/project/qimage2ndarray/) doit être ajouter à QGIS pour faire fonctionner l'application. 

# Utilisation
Pour utiliser l'application, tout simplement importer un dossier d'images qui contient les fichiers de format TIF ainsi que leur fichier PAR. Les deux fichiers doivent avoir le même nom. Il est possible de naviguer entre les images avec une navigation fluide.

Un rehaussement peut être appliquer sur les images observés. Le contraste, la luminosité, la saturation et la netteté peuvent être modifier. Il est possible d'ajouter l'intensité des pixels rouges, verts et bleus. Il est aussi possible d'appliquer un filtre min/max pour une zone sélectionnée. 

L'application fonctionne sans carte graphique 3D. Il est tout simplement nécessaire d'avoir un écran de type Planar. Il est important de sélectionner les bons écrans dans le menu des paramètres. L'image de gauche devrait être sur l'écran du bas sur le Planar. 

Il est possible de faire l'affichage de vecteurs sur les images. Tout simplement importer un shapefile dans QGIS pour pouvoir le sélectionner dans l'application. Le positionnement des polygones de la couche vectorielle peut être améliorer avec l'ajout d'un modèle numérique de terrain qui peut être importer dans l'application via un fichier de format TIF ou VRT. L'ajout d'un modèle numérique de terrain est recommandé mais pas obligatoire. Le modèle numérique de terrain permet aussi de dessiner un nouveau polygone et de découper des polygones existants. Il est important que la couche vectorielle et le modèle numérique de terrain soit sur le même système de coordonnées que les coordonnées du fichier PAR.  