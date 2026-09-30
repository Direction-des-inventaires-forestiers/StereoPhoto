# -*- coding: utf-8 -*-
"""Test du bornage des rectangles de chargement de tuiles (registre P1-I).

Rejoue le scénario du journal du 2026-09-29 : la vue de la fenêtre d'affichage
se retrouve entièrement hors de l'image, `calculate_load_rects()` produit des
rectangles hors raster, et `fetch_tile()` les passe tels quels à GDAL, qui lève
« Access window out of range in RasterIO() ».

Le test extrait `calculate_load_rects()` et `load_tiled_rect()` du fichier source
par analyse syntaxique, puis les exécute avec des bouchons : aucune dépendance à
QGIS, GDAL, numpy ni Qt n'est nécessaire.

Usage :
    python tests/test_bornage_tuiles.py [chemin/vers/enhanceManager.py]

Sans argument, le module testé est src/enhanceManager.py, résolu depuis
la racine du dépôt. Sortie 0 si tout passe, 1 sinon.

Dimensions reprises des fichiers PAR réels q16033_052 et q16033_053 :
image 11310 x 17310, aperçus 5655 x 8655 (niveau 0) et 2828 x 4328 (niveau 1).
Les deux ratios d'échelle diffèrent (11310/2828 = 3,99929 contre
17310/4328 = 3,99954), ce que le test couvre aussi.
"""

import ast
import io
import os
import sys
import types
from math import ceil

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DEFAUT = os.path.join(RACINE, "src", "enhanceManager.py")

FONCTIONS_TESTEES = ("calculate_load_rects", "load_tiled_rect")


def extraire_fonctions(chemin):
    """Retourne les fonctions voulues de threadShow, isolées de leur module."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    classe = next((n for n in ast.walk(arbre)
                   if isinstance(n, ast.ClassDef) and n.name == "threadShow"), None)
    if classe is None:
        raise AssertionError("classe threadShow introuvable dans %s" % chemin)

    corps = [n for n in classe.body
             if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS_TESTEES]
    manquantes = set(FONCTIONS_TESTEES) - {n.name for n in corps}
    if manquantes:
        raise AssertionError("fonctions introuvables : %s" % ", ".join(sorted(manquantes)))

    espace = {
        "ceil": ceil,
        "_journal": JournalBouchon(),
        "np": types.SimpleNamespace(ascontiguousarray=lambda a: a),
        "QThread": types.SimpleNamespace(msleep=lambda n: None),
        "QImage": ImageBouchon,
    }
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return espace


class ImageBouchon:
    """Remplace QImage : la tuile est convertie dans le fil de lecture depuis
    la fusion de nextV. Seules la construction et copy() sont utilisées ici."""

    Format_RGB888 = 13

    def __init__(self, *args):
        self.args = args

    def copy(self):
        return self


class TuileBouchon:
    """Tuile retournée par fetch_tile() : QImage n'en lit que le tampon."""

    data = memoryview(b"")


class JournalBouchon:
    def __init__(self):
        self.lignes = []

    def _noter(self, msg, *a):
        self.lignes.append(msg % a if a else msg)

    debug = _noter
    warning = _noter


class BandeBouchon:
    def __init__(self, x, y):
        self.XSize, self.YSize = x, y


class DsBouchon:
    def __init__(self, apercus):
        self.apercus = apercus

    def GetRasterBand(self, i):
        return self

    def GetOverview(self, i):
        return self.apercus[i]


class RectBouchon:
    """Remplace QRectF : gauche, haut, droite, bas."""

    def __init__(self, gauche, haut, droite, bas):
        self._v = (gauche, haut, droite, bas)

    def left(self):
        return self._v[0]

    def top(self):
        return self._v[1]

    def right(self):
        return self._v[2]

    def bottom(self):
        return self._v[3]


class ThreadBouchon:
    """Reprend les attributs de threadShow utilisés par les deux fonctions."""

    width, height = 11310, 17310
    target_tile_size = 512
    keepRunning = True
    perform_Enhancing = False

    def __init__(self, sceneRect, cropValue):
        self.sceneRect = sceneRect
        self.cropValue = cropValue
        self.ds = DsBouchon({0: BandeBouchon(5655, 8655), 1: BandeBouchon(2828, 4328)})
        self.demandes = []
        self.newImage = types.SimpleNamespace(emit=lambda *a: None)

    def fetch_tile(self, x, y, w, h, ovr_index):
        """Vérifie chaque fenêtre de lecture comme GDAL le ferait."""
        self.demandes.append((x, y, w, h, ovr_index))
        if ovr_index == -1:
            maxX, maxY = self.width, self.height
        else:
            maxX = self.ds.apercus[ovr_index].XSize
            maxY = self.ds.apercus[ovr_index].YSize
        assert x >= 0 and y >= 0, "offset négatif : %r" % ((x, y, w, h, ovr_index),)
        assert w > 0 and h > 0, "taille nulle ou négative : %r" % ((x, y, w, h),)
        assert x + w <= maxX and y + h <= maxY, (
            "hors raster : (%d,%d) de %dx%d sur %dx%d" % (x, y, w, h, maxX, maxY))
        return TuileBouchon()

    def applyEnhancements(self, tuile, params):
        return tuile


#Rognage plausible du recouvrement pour q16033_053 (calculé : X 4538 -> 11310).
ROGNAGE = (0, 0, 6772, 17310)

#Chaque cas : libellé, vue en pixels image, avertissement « hors zone » attendu.
CAS = (
    ("vue très à gauche de l'image (cas du journal)", RectBouchon(-99500, 0, -98224, 1000), True),
    ("vue très en dessous de l'image", RectBouchon(1000, 98000, 2000, 99000), True),
    ("vue très à droite de l'image", RectBouchon(98000, 100, 99000, 900), True),
    ("vue normale, centre de l'image", RectBouchon(3000, 8000, 4000, 9000), False),
    ("vue couvrant toute l'image", RectBouchon(-2000, -2000, 13000, 19000), False),
)


def executer(chemin):
    espace = extraire_fonctions(chemin)
    journal = espace["_journal"]
    for nom, fonction in list(espace.items()):
        if isinstance(fonction, types.FunctionType):
            setattr(ThreadBouchon, nom, fonction)

    echecs = []
    for libelle, vue, alerte_attendue in CAS:
        journal.lignes = []
        objet = ThreadBouchon(vue, ROGNAGE)
        try:
            rects = objet.calculate_load_rects()
            for rect in rects:
                assert rect[0] >= 0 and rect[1] >= 0, "rectangle négatif %r" % (rect,)
                assert rect[2] <= ROGNAGE[2] and rect[3] <= ROGNAGE[3], (
                    "rectangle hors rognage %r" % (rect,))
            for indice in range(5):
                for apercu in (1, 0, -1):
                    objet.load_tiled_rect(rects[indice], ovr_index=apercu, groupId=0)

            alertes = [l for l in journal.lignes if l.startswith("Vue hors")]
            assert bool(alertes) == alerte_attendue, (
                "avertissement « hors zone » %s"
                % ("attendu mais absent" if alerte_attendue else "émis à tort"))
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-45s %s" % (libelle, erreur))
        else:
            print("OK     %-45s %d tuiles lues" % (libelle, len(objet.demandes)))

    return echecs


if __name__ == "__main__":
    cible = sys.argv[1] if len(sys.argv) > 1 else MODULE_DEFAUT
    print("Module testé : %s\n" % cible)
    problemes = executer(cible)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nAucune lecture hors raster sur les %d scénarios." % len(CAS))
