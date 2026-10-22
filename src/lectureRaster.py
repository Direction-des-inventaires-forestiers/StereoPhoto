# -*- coding: utf-8 -*-
"""Ouverture d'un raster par GDAL, sous les deux conventions d'erreur.

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
