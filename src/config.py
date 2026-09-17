'''
Paramètres de configuration du plugin StereoPhoto

Toute valeur qui influence le comportement de l'application est déclarée ici,
nommée avec son rôle et son unité. Une valeur modifiée ici s'applique à tous
les modules qui l'utilisent.
'''

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
