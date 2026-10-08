# -*- coding: utf-8 -*-
"""Test de la recherche de paire par position (registre P1-J).

Rejoue l'erreur relevée en test manuel le 2026-09-30 : le centre du canevas
QGIS se trouvait à environ 10 730 km de la zone des photos, aucune distance ne
passait sous la sentinelle `minDist = 9999999`, `minID` restait vide et
`int(minID.split('_')[1])` levait « IndexError: list index out of range ».

Le test extrait `numeroPhoto()` et `findPairWithCoord()` du fichier source par
analyse syntaxique, puis les exécute avec des bouchons : aucune dépendance à
QGIS, GDAL, numpy ni Qt n'est nécessaire.

Usage :
    python tests/test_recherche_paire.py [chemin/vers/gestionDossier.py]

Sans argument, le module testé est src/gestionDossier.py, résolu depuis la
racine du dépôt. Sortie 0 si tout passe, 1 sinon.

Coordonnées reprises de la séance : photos du dossier 2016 autour de
(381008.901, 5391518.301) en EPSG:32198, centre du canevas à
(9017716.330, -962310.819).
"""

import ast
import io
import math
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_DEFAUT = os.path.join(RACINE, "src", "gestionDossier.py")

FONCTIONS_TESTEES = ("numeroPhoto", "findPairWithCoord")

#Valeur de config.PAR_PAIR_PROXIMITY_BUFFER_M au moment du test.
BUFFER_M = 500

#Seuil appliqué par stereoPhoto.findPairWithPosition() au résultat.
SEUIL_APPELANT_M = 7500


class JournalBouchon:
    def __init__(self):
        self.lignes = []

    def _noter(self, msg, *a):
        self.lignes.append(msg % a if a else msg)

    debug = _noter
    warning = _noter


def extraire_fonctions(chemin):
    """Retourne les fonctions voulues du module, isolées de leurs imports."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    corps = [n for n in arbre.body
             if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS_TESTEES]
    manquantes = set(FONCTIONS_TESTEES) - {n.name for n in corps}
    if manquantes:
        raise AssertionError("fonctions introuvables : %s" % ", ".join(sorted(manquantes)))

    espace = {
        "math": math,
        "_journal": JournalBouchon(),
        "PAR_PAIR_PROXIMITY_BUFFER_M": BUFFER_M,
    }
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return espace


def ligne_de_vol(prefixe, premier, nombre, x0, y0, pas=300.0):
    """Photos alignées en X, espacées de `pas` mètres, comme une ligne de vol."""
    return {"%s_%03d_rgb" % (prefixe, premier + i):
            (x0 + i * pas, y0, 0, 0, 0, 0) for i in range(nombre)}


#Zone réelle de la séance : 207 photos du dossier 2016, en EPSG:32198.
PHOTOS = ligne_de_vol("q16033", 52, 207, 381008.901, 5391518.301)

#Centre du canevas relevé au moment de l'erreur, dans le même CRS.
VUE_LOINTAINE = (9017716.330220249, -962310.8192603509)
VUE_PROCHE = (381608.901, 5391518.301)


def cas_vue_lointaine(espace):
    """Le cas du journal : plus de 10 000 km, aucune exception attendue."""
    identifiant, distance = espace["findPairWithCoord"](PHOTOS, VUE_LOINTAINE)
    assert distance > SEUIL_APPELANT_M, (
        "distance %r sous le seuil de l'appelant : la vue serait acceptée" % distance)
    assert identifiant == "" or distance > 1e7, (
        "résultat inattendu pour une vue hors zone : %r" % ((identifiant, distance),))
    return "distance %.0f m, rejetée par l'appelant" % distance


def cas_dictionnaire_vide(espace):
    """Aucune photo : la recherche doit répondre, pas planter."""
    identifiant, distance = espace["findPairWithCoord"]({}, VUE_PROCHE)
    assert identifiant == "", "identifiant non vide sur un dossier vide : %r" % identifiant
    assert distance == math.inf, "distance finie sur un dossier vide : %r" % distance
    return "('', inf)"


def cas_vue_proche(espace):
    """Non-régression : en régime normal, la paire attendue est retournée.

    La vue est centrée sur q16033_054_rgb, dont les deux voisins de numéro sont
    à égale distance : la fonction conserve alors la photo la plus proche, le
    départage par `leftDist < rightDist` étant faux à égalité.
    """
    identifiant, distance = espace["findPairWithCoord"](PHOTOS, VUE_PROCHE)
    assert identifiant == "q16033_054_rgb", "photo inattendue : %r" % identifiant
    assert distance < SEUIL_APPELANT_M, "distance %r au-dessus du seuil" % distance
    return "%s à %.0f m" % (identifiant, distance)


def cas_identifiant_hors_convention(espace):
    """Un nom sans numéro ne doit pas interrompre la recherche."""
    photos = dict(PHOTOS)
    photos["photo_sans_numero"] = (381608.901, 5391518.301, 0, 0, 0, 0)
    identifiant, distance = espace["findPairWithCoord"](photos, VUE_PROCHE)
    assert identifiant, "aucune photo retenue alors qu'une est à distance nulle"
    return "retenu %s, sans exception" % identifiant


def cas_voisin_hors_convention(espace):
    """Un voisin sans numéro est écarté du calcul, les autres sont conservés."""
    photos = dict(PHOTOS)
    photos["voisin_hs"] = (381308.901, 5391518.301, 0, 0, 0, 0)
    identifiant, _ = espace["findPairWithCoord"](photos, VUE_PROCHE)
    assert identifiant != "", "recherche interrompue par un voisin hors convention"
    return "retenu %s" % identifiant


def cas_distance_indefinie(espace):
    """Une bbox portant NaN ne doit pas laisser minID vide puis planter."""
    photos = {"q16033_052_rgb": (float("nan"), float("nan"), 0, 0, 0, 0)}
    identifiant, distance = espace["findPairWithCoord"](photos, VUE_PROCHE)
    assert identifiant == "", "photo retenue malgré une distance indéfinie : %r" % identifiant
    assert distance == math.inf, "distance %r au lieu de inf" % distance
    return "('', inf)"


CAS = (
    ("vue à 10 730 km de la zone (cas du journal)", cas_vue_lointaine),
    ("dossier sans photo", cas_dictionnaire_vide),
    ("vue sur la zone, régime normal", cas_vue_proche),
    ("photo la plus proche hors convention", cas_identifiant_hors_convention),
    ("voisin hors convention", cas_voisin_hors_convention),
    ("distance indéfinie (NaN)", cas_distance_indefinie),
)


def executer(chemin):
    espace = extraire_fonctions(chemin)
    echecs = []
    for libelle, fonction in CAS:
        try:
            detail = fonction(espace)
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-45s %s" % (libelle, erreur))
        except Exception as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-45s %s: %s" % (libelle, type(erreur).__name__, erreur))
        else:
            print("OK     %-45s %s" % (libelle, detail))
    return echecs


if __name__ == "__main__":
    cible = sys.argv[1] if len(sys.argv) > 1 else MODULE_DEFAUT
    print("Module testé : %s\n" % cible)
    problemes = executer(cible)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nAucune exception sur les %d scénarios." % len(CAS))
