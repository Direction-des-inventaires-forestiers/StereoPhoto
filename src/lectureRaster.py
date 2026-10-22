# -*- coding: utf-8 -*-
"""Accès aux rasters : ouverture, et chargement d'une fenêtre de MNT.

Les deux fonctions sont ici parce qu'elles servent les mêmes appelants — la
lecture du MNT par le panneau d'options et par le thread de calcul des
géométries — et qu'aucune ne dépend de QGIS ni de Qt, deux de ces appelants
étant des threads.

## Ouverture d'un raster par GDAL, sous les deux conventions d'erreur.

`gdal.Open()` signale un fichier illisible de deux façons, selon l'état de
`gdal.UseExceptions()` :

- exceptions désactivées — il retourne `None` ;
- exceptions activées — il lève `RuntimeError`, et rien n'est retourné.

QGIS 3.44 les active, l'exécution hors de QGIS ne les active pas, et GDAL 4.0
les activera partout par défaut. Le même code tournant dans les deux contextes,
une garde posée sur une seule des deux conventions est inerte dans l'autre.
C'est ce qui laissait, en session QGIS, un dossier contenant une seule image
corrompue sans aucune paire, et un MNT illisible interrompre le chargement
d'une paire — sans trace au journal dans les deux cas, l'exception partant vers
la fenêtre d'erreur Python de QGIS.

`ouvrir_raster()` ramène les deux cas à un seul retour `None`, après avoir
journalisé le fichier en cause. Les appelants gardent leur `if ... is None`,
qui agit désormais dans les deux contextes.
"""

import math

import numpy as np
from osgeo import gdal

from .journal import obtenir_journal

_journal = obtenir_journal(__name__)


def motif_echec(erreur):
    """Première ligne du message de GDAL, ou le nom de l'exception à défaut.

    GDAL empile ses causes sur plusieurs lignes (« May be caused by: … »), ce
    qui rendrait le journal illisible.
    """

    texte = str(erreur).strip()
    if not texte:
        return type(erreur).__name__
    return texte.splitlines()[0]


def ouvrir_raster(chemin, mode=gdal.GA_ReadOnly):
    """Ouvre le raster et retourne son dataset, ou `None` s'il est illisible.

    L'échec laisse un avertissement nommant le fichier : c'est la seule trace
    dont dispose le support quand une donnée du terrain est en cause. Seule
    l'erreur d'ouverture de GDAL est interceptée ; toute autre exception
    remonte à l'appelant.

    L'appelant décide de la suite — écarter la donnée et poursuivre, revenir au
    calcul stéréoscopique, ou refuser la paire — et c'est à lui qu'il revient
    d'avertir l'utilisateur si la condition demande une action de sa part.
    """

    try:
        jeu = gdal.Open(chemin, mode)
    except RuntimeError as erreur:
        _journal.warning(
            "Raster illisible, écarté : %s — %s", chemin, motif_echec(erreur)
        )
        return None

    if jeu is None:
        _journal.warning("Raster illisible, écarté : %s", chemin)

    return jeu


def fenetre_mnt(bande, geo, taille, emprise, nodata, chemin=""):
    """Charge la fenêtre du MNT couvrant l'emprise, bornée au raster.

    `emprise` est `(xmin, ymin, xmax, ymax)`, dans l'unité du MNT. Retourne
    `(tableau, ix, iy)`, où `ix` et `iy` sont les indices de la cellule du
    raster qui occupe le coin supérieur gauche du tableau : c'est l'origine à
    laquelle les lecteurs rapportent leurs propres indices.

    Retourne `(None, 0, 0)` quand l'emprise ne recoupe pas le raster.

    **Le bornage précède l'allocation**, et non l'inverse. Calculée sur un MNT
    dont le pas n'est pas dans l'unité de l'emprise — un MNT en degrés contre
    des coordonnées de canevas en mètres, cas du MNT 1/20 000 du MERN chargé
    sans reprojection — la fenêtre demandée atteint des dizaines de millions de
    cellules par axe, et l'allocation épuise la mémoire avant qu'aucune
    vérification ait lieu : 9,9 Pio demandés, mesurés en session. Bornée
    d'abord, la fenêtre ne peut pas excéder la taille du raster, et le cas se
    règle de lui-même sans plafond arbitraire à choisir.

    Le pas du raster est supposé positif en X et négatif en Y, c'est-à-dire
    orienté au nord, comme l'étaient les deux calculs que cette fonction
    remplace.
    """

    xmin, ymin, xmax, ymax = emprise

    px_debut = math.floor((xmin - geo[0]) / geo[1])
    py_debut = math.floor((ymax - geo[3]) / geo[5])
    px_fin = math.floor((xmax - geo[0]) / geo[1])
    py_fin = math.floor((ymin - geo[3]) / geo[5])

    # Intersection avec le raster, établie avant toute allocation
    ix = max(0, px_debut)
    iy = max(0, py_debut)
    largeur = min(taille[0], px_fin) - ix
    hauteur = min(taille[1], py_fin) - iy

    if largeur <= 0 or hauteur <= 0:
        _journal.debug(
            "MNT sans recouvrement avec la vue, aucune fenêtre chargée : %s, "
            "fenêtre demandée (%s, %s) à (%s, %s) sur un raster de %sx%s",
            chemin,
            px_debut,
            py_debut,
            px_fin,
            py_fin,
            taille[0],
            taille[1],
        )
        return None, 0, 0

    tableau = np.full((hauteur, largeur), nodata, dtype=np.float32)
    try:
        lu = bande.ReadAsArray(ix, iy, largeur, hauteur)
        if lu is None:
            raise ValueError("ReadAsArray n'a rien rendu")
        tableau[:, :] = lu
    except Exception:
        # La fenêtre reste à nodata : les altitudes reviennent au calcul
        # stéréoscopique, et la trace nomme le fichier en cause.
        _journal.warning(
            "Lecture du MNT impossible, fenêtre laissée à nodata : "
            "%s, lecture (%s, %s) de %sx%s",
            chemin,
            ix,
            iy,
            largeur,
            hauteur,
            exc_info=True,
        )

    return tableau, ix, iy
