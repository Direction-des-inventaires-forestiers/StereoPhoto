# StereoPhoto
StereoPhoto est une extension expérimentale disponible dans QGIS qui permet la visualisation d'une paire de photographies aériennes en stéréoscopie.
L'application a été développée par la Direction des Inventaires Forestiers (Ministère des Ressources naturelles et des Forêts).

Pour toute question supplémentaire ou si vous désirez participer au développement de StereoPhoto, contacter l'adresse suivante : inventaires.forestiers@mrnf.gouv.qc.ca 

Afin de faciliter l'installation ainsi que la première utilisation, il est recommandé d'utiliser [le guide d'utilisation.](guideUtilisationStereoPhoto_v0_1_3.pdf) Le guide peut être utilisé pour envoyer des commentaires à notre adresse courriel. 

Le texte dans le document peut aussi être utilisé lorsque vous créez un nouveau billet dans la section **Issues**. Quatres types de billets sont disponibles : 

- Nouvelle fonctionnalité
- Question générale
- Question sur les fonctionnalités existantes
- Signaler un problème

# Fichier de test

Un fichier contenant une paire d'image ainsi que les fichiers «.par» associé est disponible sur [ce dépôt.](fichierTest/) Ce fichier démontre comment le dossier d'image devrait être assemblé pour être compatible avec l'application. 

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