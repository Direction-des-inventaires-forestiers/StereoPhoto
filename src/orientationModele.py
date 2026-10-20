# -*- coding: utf-8 -*-
"""Orientation de la caméra et direction du modèle voisin (plan 3A.3).

Quand la vue atteint le bord du modèle affiché, le modèle voisin à charger
dépend de l'orientation de la caméra : un bord franchi à gauche dans le repère
pixel de la photo ne mène au voisin « ouest » que si le nord est en haut. Les
fichiers `.par` donnent cette orientation par l'angle kappa, en pratique voisin
de 0°, ±90° ou ±180° à la tolérance près.

Ce module ne contient que la décision, sans dépendance à QGIS ni à Qt :
`stereoPhoto` lui passe des nombres et reçoit une direction, à charge pour lui
d'aller chercher la paire. C'est ce qui le rend vérifiable sans installer QGIS,
convention du dossier `tests/`.

La logique était auparavant écrite quatre fois de suite dans
`calculNextPairWithPos()`, une fois par orientation, avec une remarque du code
demandant l'extraction.
"""

# Les quatre bords du cadrage, dans le repère pixel de la photo de gauche, et
# dans l'ordre de priorité d'origine : au franchissement simultané de deux
# bords (un coin), c'est le premier de cette liste qui décide.
BORDS = ("xMin", "xMax", "yMin", "yMax")

# Les quatre directions de voisinage, telles que les nomme findNextPair().
DIRECTIONS = ("U", "D", "L", "R")

# Position du nord selon kappa, et direction du voisin pour chaque bord franchi.
# Chaque ligne est une rotation de la précédente : c'est la rotation de la
# caméra par rapport au nord géographique.
TABLES_ORIENTATION = {
    "nordAGauche": {"xMin": "U", "xMax": "D", "yMin": "R", "yMax": "L"},
    "nordADroite": {"xMin": "D", "xMax": "U", "yMin": "L", "yMax": "R"},
    "nordEnBas": {"xMin": "R", "xMax": "L", "yMin": "D", "yMax": "U"},
    "nordEnHaut": {"xMin": "L", "xMax": "R", "yMin": "U", "yMax": "D"},
}


def orientationCamera(kappaDeg, toleranceDeg):
    """Nomme la position du nord pour un angle kappa, en degrés.

    Hors des trois cas francs, l'orientation retenue est « nord en haut », qui
    est le cas de loin le plus fréquent et le repli d'origine.
    """
    if abs(kappaDeg + 90) < toleranceDeg:
        return "nordAGauche"
    if abs(kappaDeg - 90) < toleranceDeg:
        return "nordADroite"
    if abs(kappaDeg - 180) < toleranceDeg or abs(kappaDeg + 180) < toleranceDeg:
        return "nordEnBas"
    return "nordEnHaut"


def directionVoisin(kappaDeg, bord, toleranceDeg):
    """Direction du modèle voisin ('U', 'D', 'L' ou 'R') pour un bord franchi.

    `bord` est l'un des quatre noms de `BORDS`, exprimés dans le repère pixel
    de la photo de gauche.
    """
    if bord not in TABLES_ORIENTATION["nordEnHaut"]:
        raise ValueError("Bord inconnu : %r" % (bord,))
    return TABLES_ORIENTATION[orientationCamera(kappaDeg, toleranceDeg)][bord]


def directionProchainModele(
    kappaDeg, toleranceDeg, x, y, rangeX, rangeY, voisinDisponible
):
    """Direction du modèle à charger, ou None s'il n'y a rien à charger.

    `x` et `y` sont la position à tester dans le repère pixel de la photo de
    gauche : la croix en navigation synchronisée, le centre de la vue en
    hors-synchronisation. `rangeX` et `rangeY` sont les bornes du cadrage déjà
    rétrécies de la marge de bordure. `voisinDisponible` indique, par
    direction, si un modèle voisin existe.

    Un bord franchi vers une direction sans voisin n'arrête pas l'examen : les
    bords suivants sont encore essayés, comme dans le code d'origine.
    """
    franchi = {
        "xMin": x < rangeX[0],
        "xMax": x > rangeX[1],
        "yMin": y < rangeY[0],
        "yMax": y > rangeY[1],
    }
    for bord in BORDS:
        if not franchi[bord]:
            continue
        direction = directionVoisin(kappaDeg, bord, toleranceDeg)
        if voisinDisponible.get(direction):
            return direction
    return None
