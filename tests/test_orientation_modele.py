# -*- coding: utf-8 -*-
"""Test de la table d'orientation du changement de modèle.

Couvre `src/orientationModele.py`, extrait de `calculNextPairWithPos()` : pour
chacune des quatre orientations de caméra que donne l'angle kappa, chaque bord
de cadrage franchi doit mener au bon modèle voisin. Une erreur dans cette table
ne se voit pas en lecture : elle se manifeste par un saut vers le mauvais
modèle, au bout d'une heure de photo-interprétation.

Trois familles de cas :

1. Les seize combinaisons orientation x bord, comparées à la table d'origine
   recopiée ici indépendamment du module testé.
2. Les bornes de tolérance : juste en deçà d'un pivot l'orientation franche
   s'applique, juste au-delà c'est le repli « nord en haut ».
3. Le comportement d'ensemble : coin franchi, voisin absent, aucun bord
   franchi.

Le module testé n'a aucune dépendance à QGIS ni à Qt : il s'importe
directement, sans l'extraction par analyse syntaxique qu'imposent les autres
tests du dossier.

Usage :
    python tests/test_orientation_modele.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

TOLERANCE = 10  # PAR_CAMERA_ORIENTATION_TOLERANCE_DEG de config.py

# Attendu, recopié de la version d'origine de calculNextPairWithPos() et non
# importé du module testé : une table qui se vérifierait contre elle-même ne
# vérifierait rien.
ATTENDU = {
    -90: {"xMin": "U", "xMax": "D", "yMin": "R", "yMax": "L"},
    90: {"xMin": "D", "xMax": "U", "yMin": "L", "yMax": "R"},
    180: {"xMin": "R", "xMax": "L", "yMin": "D", "yMax": "U"},
    -180: {"xMin": "R", "xMax": "L", "yMin": "D", "yMax": "U"},
    0: {"xMin": "L", "xMax": "R", "yMin": "U", "yMax": "D"},
}

LIBELLE_KAPPA = {
    -90: "nord à gauche",
    90: "nord à droite",
    180: "nord en bas",
    -180: "nord en bas (kappa négatif)",
    0: "nord en haut",
}

TOUS_VOISINS = {"U": True, "D": True, "L": True, "R": True}

# Un point et des bornes qui placent ce point au-delà d'un seul bord.
RANGE_X = (100.0, 900.0)
RANGE_Y = (200.0, 800.0)
POINT_PAR_BORD = {
    "xMin": (50.0, 500.0),
    "xMax": (950.0, 500.0),
    "yMin": (500.0, 150.0),
    "yMax": (500.0, 850.0),
}


def casTableComplete(mod):
    """Les seize combinaisons orientation x bord."""
    echecs = []
    for kappa, attenduParBord in ATTENDU.items():
        for bord, attendu in attenduParBord.items():
            obtenu = mod.directionVoisin(kappa, bord, TOLERANCE)
            if obtenu != attendu:
                echecs.append(
                    "kappa %s (%s), bord %s : %s au lieu de %s"
                    % (kappa, LIBELLE_KAPPA[kappa], bord, obtenu, attendu)
                )
    return echecs, "%d combinaisons" % sum(len(v) for v in ATTENDU.values())


def casBornesTolerance(mod):
    """Le basculement d'orientation se fait bien à la tolérance."""
    echecs = []
    epsilon = 0.5
    for pivot, orientation in ((-90, "nordAGauche"), (90, "nordADroite")):
        for ecart in (-(TOLERANCE - epsilon), TOLERANCE - epsilon):
            kappa = pivot + ecart
            obtenu = mod.orientationCamera(kappa, TOLERANCE)
            if obtenu != orientation:
                echecs.append(
                    "kappa %.1f : %s au lieu de %s" % (kappa, obtenu, orientation)
                )
        for ecart in (-(TOLERANCE + epsilon), TOLERANCE + epsilon):
            kappa = pivot + ecart
            obtenu = mod.orientationCamera(kappa, TOLERANCE)
            if obtenu != "nordEnHaut":
                echecs.append(
                    "kappa %.1f hors tolérance : %s au lieu du repli nordEnHaut"
                    % (kappa, obtenu)
                )

    # ±180 : les deux signes mènent au même cas, et 180 - tolérance au repli.
    for kappa in (180.0, -180.0, 179.0, -179.0):
        if mod.orientationCamera(kappa, TOLERANCE) != "nordEnBas":
            echecs.append("kappa %.1f : nord en bas attendu" % kappa)
    for kappa in (165.0, -165.0, 0.0, 9.0):
        if mod.orientationCamera(kappa, TOLERANCE) != "nordEnHaut":
            echecs.append("kappa %.1f : repli nord en haut attendu" % kappa)

    return echecs, "pivots ±90, ±180 et repli"


def casDecisionComplete(mod):
    """directionProchainModele() sur un point, bornes et voisinage réels."""
    echecs = []

    # Chaque bord franchi seul, nord en haut, tous les voisins présents.
    for bord, (x, y) in POINT_PAR_BORD.items():
        attendu = ATTENDU[0][bord]
        obtenu = mod.directionProchainModele(
            0, TOLERANCE, x, y, RANGE_X, RANGE_Y, TOUS_VOISINS
        )
        if obtenu != attendu:
            echecs.append("bord %s : %s au lieu de %s" % (bord, obtenu, attendu))

    # Aucun bord franchi : rien à charger.
    if (
        mod.directionProchainModele(
            0, TOLERANCE, 500.0, 500.0, RANGE_X, RANGE_Y, TOUS_VOISINS
        )
        is not None
    ):
        echecs.append("point au centre : aucune direction attendue")

    # Coin bas-gauche, nord en haut : xMin passe avant yMin, comme à l'origine.
    obtenu = mod.directionProchainModele(
        0, TOLERANCE, 50.0, 150.0, RANGE_X, RANGE_Y, TOUS_VOISINS
    )
    if obtenu != "L":
        echecs.append(
            "coin xMin+yMin : L attendu (priorité des bords), reçu %s" % obtenu
        )

    # Même coin, voisin gauche absent : l'examen continue et retient yMin.
    sansGauche = dict(TOUS_VOISINS, L=False)
    obtenu = mod.directionProchainModele(
        0, TOLERANCE, 50.0, 150.0, RANGE_X, RANGE_Y, sansGauche
    )
    if obtenu != "U":
        echecs.append("coin sans voisin gauche : U attendu, reçu %s" % obtenu)

    # Bord franchi, aucun voisin : rien ne se charge, pas d'exception.
    aucunVoisin = {"U": False, "D": False, "L": False, "R": False}
    if (
        mod.directionProchainModele(
            0, TOLERANCE, 50.0, 500.0, RANGE_X, RANGE_Y, aucunVoisin
        )
        is not None
    ):
        echecs.append("aucun voisin : aucune direction attendue")

    return echecs, "bords, coin, voisin absent, centre"


def casBordInconnu(mod):
    """Un nom de bord erroné doit lever, pas renvoyer une direction au hasard."""
    try:
        mod.directionVoisin(0, "xMinimum", TOLERANCE)
    except ValueError:
        return [], "ValueError levée"
    return ["aucune exception sur un nom de bord inconnu"], ""


CAS = (
    ("table complète : 4 orientations x 4 bords", casTableComplete),
    ("bornes de la tolérance kappa", casBornesTolerance),
    ("décision complète sur un point", casDecisionComplete),
    ("nom de bord inconnu", casBordInconnu),
)


def executer(source):
    sys.path.insert(0, source)
    import orientationModele as mod

    print("Module testé : %s" % os.path.join(source, "orientationModele.py"))
    print()

    total = []
    for libelle, fonction in CAS:
        echecs, note = fonction(mod)
        total.extend(echecs)
        print("%-6s %-44s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) à la table d'origine." % len(total))
        return 1
    print("La table d'orientation est conforme au comportement d'origine.")
    return 0


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    sys.exit(executer(source))
