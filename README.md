# StereoPhoto
StereoPhoto est une extension QGIS pour la photo-interprétation qui permet la visualisation d'une paire de photographies aériennes en stéréoscopie.
L'application a été développée par la Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts, Québec).

Pour toute question supplémentaire ou si vous désirez participer au développement de StereoPhoto, contacter l'adresse suivante : inventaires.forestiers@mrnf.gouv.qc.ca 

# Première utilisation

Afin de faciliter l'installation ainsi que la première utilisation, il est recommandé d'utiliser [le guide d'utilisation.](guideUtilisationStereoPhoto_v0_2_0.pdf) Le guide peut être utilisé pour envoyer des commentaires à notre adresse courriel. 

Sans avoir recours au guide d'utilisation voici les éléments importants à considérer lors de la première utilisation : 

- Les fichiers d'orientation (.PAR) doivent se situer dans le même dossier que les photographies aériennes (.TIF)
- Le système de coordonnée de référence (SCR) à utiliser doit être imposé avant de lancer la navigation
- Pour une navigation en stéréoscopie fonctionnelle, QGIS ne doit pas être dans son état inital, le canvas doit être activé via l'ajout d'une couche quelconque
- L'ajout d'une couche vectorielle via le menu des couches de l'application changera automatiquement le système de coordonnée
- Les images, les couches vectorielles et le modèle numérique de terrain doivent tous utiliser le même système de coordonnée  
- La sélection manuelle des écrans du stéréoscope doit se faire via le choix de leur numéro d'écran, le bouton **Voir Écran** permet d'aider à la sélection 
- Pour faire l'affichage de couches vectorielles lors de la navigation, elles doivent être ajoutées et être actives dans QGIS
- L'importation d'un modèle numérique de terrain permet d'afficher les couches avec une plus grande précision ainsi que l'édition de celle-ci 

# Faire un signalement

Advenant le cas ou vous rencontrez un problème ou vous avez un question concernant le logiciel. Il est possible de créer un nouveau billet dans la section **Issues**. Quatres types de billets sont disponibles : 

- Nouvelle fonctionnalité
- Question générale
- Question sur les fonctionnalités existantes
- Signaler un problème

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

# StereoPhoto - English Version  

StereoPhoto is a QGIS plugin for photo-interpretation that allows the visualization of a pair of aerial photographs in stereoscopy.
The application was developed by the Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts, Québec).

For any additional questions or if you wish to participate in the development of StereoPhoto, please contact the following address: inventaires.forestiers@mrnf.gouv.qc.ca


# First Use

To facilitate installation and first-time use, it is recommended to use the [user guide.](guideUtilisationStereoPhoto_v0_2_0.pdf) The guide is only available in french. The guide can be used to send comments to our email address. 

Without using the user guide, here are the important elements to consider during first-time use: 

- Orientation files (.PAR) must be located in the same folder as the aerial photographs (.TIF).
- The coordinate reference system (CRS) to be used must be set before starting navigation.
- For functional stereoscopic navigation, QGIS must not be in its initial state; the canvas must be activated by adding any layer.
- Adding a vector layer via the application's layer menu will automatically change the coordinate system.
- Images, vector layers, and the digital terrain model must all use the same coordinate system.  
- Manual selection of the stereoscope screens must be done by choosing their screen number; the **Voir Écran** button helps with the selection. 
- To display vector layers during navigation, they must be added and active in QGIS.
- Importing a digital terrain model allows layers to be displayed and edited with greater precision. 

# Reporting an Issue

In the event that you encounter a problem or have a question regarding the software, it is possible to create a new ticket in the **Issues** section. Four types of tickets are available: 

- New feature - Nouvelle fonctionnalité
- General question - Question générale
- Question about existing features - Question sur les fonctionnalités existantes
- Report a problem - Signaler un problème

# Test Files

A file containing a pair of images as well as the associated ".par" files is available on [this repository.](fichierTest/) This file demonstrates how the image folder should be assembled to be compatible with the application. 

The values in the ".par" file that are mandatory for the application to function are as follows: 

- $PARAFFINE00
- $PARINVAFF00 
- $FOC00 
- $XYZ00
- $OPK00

Optional values in the ".par" file: 

- $FSCALE00
- $PPA
- $PIXELSIZE
