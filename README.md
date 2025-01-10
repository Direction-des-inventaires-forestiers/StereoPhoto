# StereoPhoto
StereoPhoto est une extension expérimentale disponible dans QGIS qui permet la visualisation d'une paire de photographies aériennes en stéréoscopie.
L'application a été développée par la Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts).

Pour toute question supplémentaire ou si vous désirez participer au développement de StereoPhoto, contacter l'adresse suivante : inventaires.forestiers@mrnf.gouv.qc.ca 

# Installation 
L'extension est disponible dans le menu Extensions -> Intaller/Gérer les extensions de QGIS. Il faut s'assurer que la cocher la case Afficher les extensions expérimentales dans la section Paramètres du menu Extensions. Ensuite, faire la recherche de StereoPhoto dans la fenêtre Toutes du menu et puis l'installer. 

# Première utilisation 

Pour utiliser l'application, il est nécessaire d'ajouter un dossier d'images qui contient les fichiers de format TIF ainsi que leur fichier PAR dans l'application. Le fichier PAR associé doit avoir le même nom que son fichier TIF. Il est possible de naviguer entre les images avec une navigation fluide.

Un rehaussement peut être appliquer sur les images observés. Le contraste, la luminosité, la saturation et la netteté peuvent être modifier. Il est possible d'ajouter l'intensité des pixels rouges, verts et bleus. Il est aussi possible d'appliquer un filtre min/max pour une zone sélectionnée. 

Pour le bon fonctionnement, il est nécessaire d'avoir un stéréorestituteur (Type Planar) formé de deux moniteurs séparés d’un miroir semi-transparent ainsi que des lunettes polarisées appropriées. Il est important de faire la sélection des écrans dans le menu des paramètres de l'extension. L'image qui est appelée l'image de gauche dans l'application représente l'image qui doit apparaître sur l'écran du bas du stéréorestituteur. L'application fonctionne sans carte graphique compatible avec l’affichage stéréoscopique et ne fonctionne pas pour un système actif de vision stéréoscopique. 

Il est possible de faire l'affichage de vecteurs sur les images. Tout simplement importer une couche vectorielle dans QGIS pour pouvoir la sélectionner dans l'application. Le positionnement des polygones de la couche vectorielle peut être améliorer avec l'ajout d'un modèle numérique de terrain qui peut être importer dans l'application via un fichier de format TIF ou VRT. L'ajout d'un modèle numérique de terrain est recommandé mais pas obligatoire. Le modèle numérique de terrain permet aussi de dessiner un nouveau polygone et de découper des polygones existants. Il est important que tous les fichiers utilisés (la couche vectorielle, le modèle numérique de terrain et le fichier PAR) soit sur le même système de coordonnées.  


# Guide de la première utilisation

### En effectuant les étapes de la première utilisation, si vous rencontrez un problème lors du déroulement, vous pouvez utiliser le texte de l'étape pour l'ajouter dans votre billet dans la section Issues si vous rapportez le problème.


Ouvrir le fichier de photo

    Choisir la paire d'image dans QGIS avec le bouton Trouver la paire, l'utilisateur doit être à une échelle rapprocher de l'image qu'il désire utiliser (SCR du projet doit être le bon pour le fonctionnement du bouton
    OU
    Utiliser le bouton Parcourir la liste pour choisir une image spécifique 

Ouvrir le menu des paramètres 

    Choix des écrans
    Cocher Flip si la carte graphique est stéréoscopique
    Choisir les touches raccourcis Zoom, Déplacement Y, Dessin 

Importer une couche vectorielle de polygone, la couche doit être dans QGIS, le SCR du projet sera modifié pour utiliser celui de la couche 
Si vous voulez utiliser la valeur d'altitude (Z) disponible dans le polygone 3D, cochez la case Afficher Altitude 

Utiliser l'outil de Rehaussement 
    Utiliser la fonction Min/Max
    ET/OU
    Utiliser les options de contraste, luminosité, netteté et saturation
    ET/OU
    Ajouter/Retirer du rouge, vert,  bleu 


Importer un modèle numérique de terrain format TIF ou VRT
Sélectionner le bouton Découper **Recommander**
Le bouton Dessiner est pour ajouter un nouveau polygone 

Cliquer sur le bouton Naviguer 

**Début du mode Navigation**

Les images s'affichent sur leur écran respectif
Lorsque je regarde les images avec les écrans et son miroir, je vois dans une perspective 3D
Les images se superpose d'une manière qui est agréable de regarder
La portion des images affichées sur chaque écran est la même 
Un curseur en forme de croix s'affiche au milieu de l'écran


Déplacement de base
    La souris permet d'aller dans toutes les directions
    Il est possible de Zoom In/Out avec la roulette et la touche CTRL 
    F5-F12 différent niveau de Zoom 
    Il est possible de déphaser les images pour changer l'altitude avec la roulette de la souris 

Pour quitter le mode Navigation, appuyer sur la touche Escape (Échap) 

Navigation entre les paires d'images
    Lorsque je me déplace sur les images 3D, je vois ma position apparaître dans QGIS 
    L'échelle de QGIS correspond grossièrement avec celle de l'application 
    Lorsque ma position dans QGIS atteint les bordures de la vue courant, la fenêtre QGIS change de place avec le positionnement au milieu de la fenêtre 
    Lorsque que j'atteins les bordures d'une image (Bordure du 2% du périmètre) la paire d'image change
    La nouvelle paire d'image qui correspond belle et bien à l'image voisine s'affiche
    La position sur la nouvelle paire d'image est la même que sur l'ancienne
    

Les polygones s'affichent sur les images et leur position est juste 
 
Outil de dessin Découper 
    Commencer par placer un premier point avec le clic gauche de la souris
    Continuer votre trace en ajoutant autant de point que nécessaire
    Placer le dernier point avec le clic gauche et terminer la dessin de la ligne avec le clic droit
    Le résultat apparait dans l'application et dans QGIS, le/les polygones sont bien découpé





