"""
Paramètres de configuration du plugin StereoPhoto

Toute valeur qui influence le comportement de l'application est déclarée ici,
nommée avec son rôle et son unité. Une valeur modifiée ici s'applique à tous
les modules qui l'utilisent.
"""

# Découverte des paires de photos (gestionDossier.py) et navigation (stereoPhoto.py)

# Tolérance (degrés) autour d'un angle kappa de ±90° ou ±180° pour déterminer
# l'orientation de la caméra (photo en portrait ou paysage, position du nord)
PAR_CAMERA_ORIENTATION_TOLERANCE_DEG = 10

# Écart maximal en Y (mètres) entre deux photos pour les considérer dans la même
# ligne de vol lors de la recherche d'une paire à partir d'une coordonnée
PAR_PAIR_PROXIMITY_BUFFER_M = 500

# Écart en Y (mètres) qui sépare les voisins gauche/droite (sous le seuil)
# des voisins haut/bas (au-delà du seuil)
PAR_DIRECTION_BUFFER_M = 500

# Chevauchement minimal (ratio de la plus petite emprise) pour retenir un voisin haut/bas
PAR_MIN_OVERLAP_RATIO = 0.05

# Navigation (navigationQgsMapTool.py, stereoPhoto.py)

# Comportement de navigation à l'ouverture d'une session :
#   False : les photos se déplacent sous un curseur immobile au centre de la vue
#   True  : le curseur se déplace sur les photos, qui restent fixes
# Le photo-interprète bascule d'un comportement à l'autre en cours de session,
# par le bouton « Débarrer le curseur » de la barre d'outils ou par la touche C.
NAVIGATION_CURSEUR_LIBRE_PAR_DEFAUT = False

# Zone sûre du piège à souris, en mode synchronisé : tant que le curseur y
# reste, aucun recentrage n'a lieu. La marge est une part de la dimension du
# canevas, bornée en pixels, pour que la zone garde une taille utilisable aussi
# bien sur le grand canevas du poste de stéréoscopie que sur un canevas réduit
# par les panneaux latéraux.
NAVIGATION_ZONE_SURE_MARGE_RATIO = 0.2
NAVIGATION_ZONE_SURE_MARGE_MIN_PX = 20
NAVIGATION_ZONE_SURE_MARGE_MAX_PX = 150

# Côté minimal (pixels) sous lequel la zone sûre est jugée inutilisable. Le
# piège est alors levé explicitement, et la condition journalisée : sans zone,
# le curseur n'est jamais ramené au centre et sa course se limite à la taille
# du canevas, ce qui rend la navigation impraticable sans rien signaler.
NAVIGATION_ZONE_SURE_COTE_MIN_PX = 60

# Délai (millisecondes) avant que la condition de canevas trop petit soit
# portée au bandeau de QGIS. L'alerte est différée, et la minuterie relancée à
# chaque redimensionnement : la taille du canevas n'est stable ni au montage de
# la fenêtre de QGIS, ni pendant que l'utilisateur déplace un panneau latéral,
# et un état de passage n'a pas à encombrer le bandeau. Seule une condition qui
# tient encore après ce délai demande une action de l'utilisateur.
NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS = 1500

# Délai maximal (millisecondes) d'attente de l'arrêt d'un thread d'affichage,
# au changement de modèle ou à la fermeture. L'attente est bornée pour que
# l'interface ne puisse pas rester figée sur un thread qui ne se termine pas.
# Au-delà du délai, le thread est conservé le temps qu'il finisse plutôt que
# relâché : c'est le relâchement d'un QThread en cours d'exécution qui fait
# interrompre le processus par Qt, et non l'attente.
NAVIGATION_ARRET_THREAD_DELAI_MAX_MS = 5000

# Diagnostic du piège à souris : intervalle (secondes) entre deux traces du
# nombre de recentrages, et taux (recentrages par seconde) au-delà duquel la
# trace passe d'un message de mise au point à un message d'information.
NAVIGATION_TRACE_RECENTRAGE_INTERVALLE_S = 2.0
NAVIGATION_TRACE_RECENTRAGE_SEUIL_PAR_S = 10.0

# Système de référence des coordonnées (stereoPhoto.py, gestionDossier.py)

# SCR des données photogrammétriques du mandat : NAD83(CSRS) / MTM zone 6.
# Valeur reprise de gestionDossier.save_bbox_to_gpkg(), où elle était en dur
# depuis l'origine du code ; à confirmer auprès de la DIF pour les secteurs
# hors de la zone 6, un SCR projeté déjà posé sur le projet étant de toute
# façon conservé tel quel.
# Les fichiers PAR portent des coordonnées projetées en mètres, et tout le
# calcul de navigation (conversion coordonnée ↔ pixel image, accord d'échelle
# entre le canevas et les vues photo) suppose des mètres. Un projet QGIS dans
# un SCR géographique (degrés) fausse ce calcul d'un facteur d'environ 100 000
# sans qu'aucune erreur ne soit levée : la navigation paraît figée.
DONNEES_SCR_EPSG = 2948

# Édition vectorielle (stereoPhoto.py, editionOutils.py, editionVecteur.py)

# Outil d'édition actif à l'ouverture d'une session. Valeurs admises : les
# constantes OUTIL_* de editionOutils.py. « ajouter » reprend le comportement
# des versions où le tracé était le seul geste offert.
# Le photo-interprète change d'outil par la barre d'outils en cours de session.
EDITION_OUTIL_PAR_DEFAUT = "ajouter"

# Rayon de désignation d'une entité au clic, en pixels de canevas. Converti en
# unités terrain à chaque clic par mapUnitsPerPixel() : la tolérance suit donc
# l'échelle, et vaut autant de pixels à l'écran stéréo qu'au canevas, les deux
# échelles étant accordées par setExtent2Canvas().
EDITION_SELECTION_TOLERANCE_PX = 8

# Épaisseur du trait des entités sélectionnées dans les vues photo (pixels
# écran). Plus épais que GEOMETRY_PEN_WIDTH_PX, la surbrillance étant tracée
# par-dessus la géométrie qu'elle désigne.
EDITION_SELECTION_PEN_WIDTH_PX = 7

# Couleur du trait des entités sélectionnées dans les vues photo. Reprend le
# jaune de la sélection de QGIS, pour que les deux écrans et le canevas
# désignent la même entité de la même façon.
EDITION_SELECTION_COULEUR = "#ffff00"

# Interface graphique (stereoPhoto.py)

# Épaisseur du trait de la ligne en cours de tracé (pixels écran)
DRAW_LINE_PEN_WIDTH_PX = 4

# Épaisseur du trait des géométries des couches vectorielles affichées (pixels écran)
GEOMETRY_PEN_WIDTH_PX = 4

# Rayon des points des couches vectorielles affichées (pixels de l'image)
GEOMETRY_POINT_RADIUS_PX = 9

# Journalisation (journal.py)

# Niveau minimal des messages écrits au journal : DEBUG, INFO, WARNING ou ERROR
JOURNAL_NIVEAU_DEFAUT = "INFO"

# Nombre de jours de conservation des fichiers de journal archivés
JOURNAL_RETENTION_JOURS = 90

# Sous-dossier des journaux, sous le dossier de profil QGIS de l'utilisateur
JOURNAL_SOUS_DOSSIER = "stereophoto/logs"

# Sous-dossier où sont déplacés les fichiers des journées précédentes
JOURNAL_SOUS_DOSSIER_ARCHIVE = "archive"

# Préfixe du nom des fichiers de journal, suivi de la date (stereophoto-AAAA-MM-JJ.log)
JOURNAL_PREFIXE_FICHIER = "stereophoto"
