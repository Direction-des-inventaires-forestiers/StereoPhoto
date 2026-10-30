# -*- coding: utf-8 -*-
"""Test de la lecture d'altitude dans la fenêtre de MNT chargée.

`getAltitude()` lisait la fenêtre de MNT en indexant le tableau numpy, et
traitait la sortie de fenêtre par un `except` sur l'indexation. Or numpy ne lève
que pour un indice **supérieur ou égal** à la taille de l'axe : un indice
négatif compris dans cette taille est une indexation valide, qui désigne une
cellule à partir de la fin de l'axe. Un sommet sorti au nord ou à l'ouest de la
fenêtre recevait donc l'altitude du bord opposé du MNT, sans lever, sans être
compté au résumé de fin de traitement, et sans retomber sur le calcul
stéréoscopique.

Mesuré en session sur une fenêtre de 132 × 68 pixels : un sommet à une colonne à
l'ouest rendait 374,55 m là où le repli stéréoscopique donnait 631,65 m.

La garde porte désormais sur des bornes explicites, comme
`optWindow.readMNTWithCoord()` le fait déjà de son côté.

La méthode est extraite du fichier source par analyse syntaxique et exécutée
avec des bouchons, sur un vrai tableau numpy : aucune dépendance à QGIS ni à Qt
n'est nécessaire.

Usage :
    python tests/test_altitude_mnt.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import math
import os
import sys

import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Fenêtre d'essai : 20 lignes sur 10 colonnes, altitude croissante d'ouest en
# est, pour que la valeur du bord opposé se distingue sans ambiguïté de celle
# attendue. Origine du MNT en (1000, 5000), pas de 10 m.
NB_LIGNES, NB_COLONNES = 20, 10
GEO = (1000.0, 10.0, 0.0, 5000.0, 0.0, -10.0)
PX_START, PY_START = 5, 3
NODATA = -9999.0
ALTITUDE_STEREO = 777.0


def fenetre_essai():
    """Tableau dont chaque cellule porte une altitude distincte."""
    valeurs = np.arange(NB_LIGNES * NB_COLONNES, dtype=np.float32)
    return valeurs.reshape(NB_LIGNES, NB_COLONNES) + 100.0


def coord_pour_indice(iy, ix):
    """Coordonnée terrain tombant au centre de la cellule (iy, ix)."""
    x = GEO[0] + (ix + PX_START + 0.5) * GEO[1]
    y = GEO[3] + (iy + PY_START + 0.5) * GEO[5]
    return x, y


def extraire_methode(chemin, classe_visee, methode_visee, espace):
    """Retourne une méthode d'une classe, isolée de son module."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    classe = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.ClassDef) and n.name == classe_visee
        ),
        None,
    )
    if classe is None:
        raise AssertionError("classe %s introuvable dans %s" % (classe_visee, chemin))

    corps = [
        n
        for n in classe.body
        if isinstance(n, ast.FunctionDef) and n.name == methode_visee
    ]
    if not corps:
        raise AssertionError(
            "méthode %s.%s introuvable" % (classe_visee, methode_visee)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return espace[methode_visee]


class JournalBouchon:
    def __init__(self):
        self.messages = []

    def _noter(self, niveau):
        def ecrire(gabarit, *args, **kwargs):
            self.messages.append((niveau, gabarit % args if args else gabarit))

        return ecrire

    def __getattr__(self, nom):
        if nom in ("debug", "info", "warning", "error", "exception"):
            return self._noter(nom)
        raise AttributeError(nom)


class GestionnaireBouchon:
    """pictureManager : coordToPixel() n'a pas à être juste, seulement appelé."""

    def coordToPixel(self, coord, altitude):
        return (0.0, 0.0)


class DualBouchon:
    """dualManager : rend l'altitude du repli stéréoscopique."""

    def __init__(self):
        self.appels = 0

    def calculateZ(self, pl, pr):
        self.appels += 1
        return ALTITUDE_STEREO


class ThreadBouchon:
    """Le strict nécessaire à getAltitude()."""

    def __init__(self, fenetre):
        self.mntPath = "/mnt/essai.tif"
        self.mntArr = fenetre
        self.mntGeo = GEO
        self.pxStart = PX_START
        self.pyStart = PY_START
        self.mntNodata = NODATA
        self.nbSommetsHorsMNT = 0
        self.initAltitude = 500.0
        self.leftManager = GestionnaireBouchon()
        self.rightManager = GestionnaireBouchon()
        self.dualManag = DualBouchon()


def verifier(libelle, echecs, controle):
    try:
        controle()
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-54s %s" % (libelle, erreur))
    except Exception as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-54s %s : %s" % (libelle, type(erreur).__name__, erreur))
    else:
        print("OK     %-54s" % libelle)


def monter(dossier_source):
    chemin = os.path.join(dossier_source, "drawFunction.py")
    journal = JournalBouchon()
    espace = {"math": math, "np": np, "_journal": journal}
    methode = extraire_methode(chemin, "calculatePolygon", "getAltitude", espace)
    return methode, ThreadBouchon(fenetre_essai()), journal


def executer(dossier_source):
    echecs = []
    chemin = os.path.join(dossier_source, "drawFunction.py")

    # --- Sommet dans la fenêtre : l'altitude du MNT est rendue -------------
    def dans_la_fenetre():
        getAltitude, th, journal = monter(dossier_source)
        x, y = coord_pour_indice(10, 4)
        attendu = float(th.mntArr[10, 4])

        obtenu = getAltitude(th, x, y)

        assert abs(float(obtenu) - attendu) < 1e-6, "%r au lieu de %r" % (
            obtenu,
            attendu,
        )
        assert th.nbSommetsHorsMNT == 0, "sommet compté à tort hors MNT"
        assert th.dualManag.appels == 0, "repli stéréoscopique appelé à tort"

    verifier("Sommet dans la fenêtre : altitude du MNT", echecs, dans_la_fenetre)

    # --- Les quatre sorties de fenêtre, dont les deux qui étaient muettes --
    sorties = (
        ("une ligne au nord", -1, 4),
        ("une colonne à l'ouest", 10, -1),
        ("cinq lignes au nord", -5, 4),
        ("juste au sud", NB_LIGNES, 4),
        ("juste à l'est", 10, NB_COLONNES),
        ("très loin au nord", -NB_LIGNES - 50, 4),
    )

    def sortie(etiquette, iy, ix):
        def controle():
            getAltitude, th, journal = monter(dossier_source)
            x, y = coord_pour_indice(iy, ix)
            # Valeur que numpy rendrait pour cet indice, si rien ne bornait.
            try:
                valeur_enroulee = float(th.mntArr[iy, ix])
            except IndexError:
                valeur_enroulee = None

            obtenu = getAltitude(th, x, y)

            assert th.nbSommetsHorsMNT == 1, (
                "sommet hors fenêtre non compté (%d)" % th.nbSommetsHorsMNT
            )
            assert abs(float(obtenu) - ALTITUDE_STEREO) < 1e-6, (
                "l'altitude doit retomber sur le calcul stéréoscopique "
                "(%r), et non venir du MNT : %r" % (ALTITUDE_STEREO, obtenu)
            )
            if valeur_enroulee is not None:
                assert abs(float(obtenu) - valeur_enroulee) > 1e-6, (
                    "l'altitude rendue est celle du bord opposé du tableau "
                    "(%r) : l'indice négatif n'est pas borné" % valeur_enroulee
                )

        return controle

    for etiquette, iy, ix in sorties:
        verifier(
            "Sortie de fenêtre, %s : comptée et repliée" % etiquette,
            echecs,
            sortie(etiquette, iy, ix),
        )

    # --- Cellule nodata : repli stéréoscopique, comportement conservé ------
    def cellule_nodata():
        getAltitude, th, journal = monter(dossier_source)
        th.mntArr[7, 2] = NODATA
        x, y = coord_pour_indice(7, 2)

        obtenu = getAltitude(th, x, y)

        assert abs(float(obtenu) - ALTITUDE_STEREO) < 1e-6, (
            "une cellule nodata doit mener au repli stéréoscopique : %r" % obtenu
        )

    verifier("Cellule nodata : repli stéréoscopique", echecs, cellule_nodata)

    # --- Altitude de la couche fournie : elle a priorité -------------------
    def altitude_de_la_couche():
        getAltitude, th, journal = monter(dossier_source)
        x, y = coord_pour_indice(NB_LIGNES + 3, 4)

        obtenu = getAltitude(th, x, y, z=321.0)

        assert abs(float(obtenu) - 321.0) < 1e-6, (
            "l'altitude passée en argument doit primer : %r" % obtenu
        )
        assert th.dualManag.appels == 0, "repli stéréoscopique appelé à tort"

    verifier(
        "Altitude de la couche fournie : elle prime", echecs, altitude_de_la_couche
    )

    # --- Le compte cumule, pour le résumé de fin de traitement -------------
    def compte_cumule():
        getAltitude, th, journal = monter(dossier_source)
        for iy, ix in ((-1, 4), (10, -1), (NB_LIGNES, 4), (10, NB_COLONNES)):
            x, y = coord_pour_indice(iy, ix)
            getAltitude(th, x, y)
        # Un sommet dans la fenêtre ne doit pas incrémenter le compte.
        x, y = coord_pour_indice(10, 4)
        getAltitude(th, x, y)

        assert th.nbSommetsHorsMNT == 4, (
            "%d sommets comptés au lieu de 4" % th.nbSommetsHorsMNT
        )
        debogages = [m for n, m in journal.messages if n == "debug"]
        assert len(debogages) == 4, (
            "%d ligne(s) de débogage : une par sommet hors fenêtre, pas plus"
            % len(debogages)
        )

    verifier("Compte cumulé : un par sommet hors fenêtre", echecs, compte_cumule)

    # --- Fenêtre absente : traité comme hors MNT, sans lever ---------------
    def fenetre_absente():
        getAltitude, th, journal = monter(dossier_source)
        th.mntArr = None
        x, y = coord_pour_indice(10, 4)

        obtenu = getAltitude(th, x, y)

        assert abs(float(obtenu) - ALTITUDE_STEREO) < 1e-6, (
            "sans fenêtre, l'altitude doit venir de la stéréoscopie : %r" % obtenu
        )
        assert th.nbSommetsHorsMNT == 1, "le sommet n'est pas compté"

    verifier("Fenêtre absente : hors MNT, sans lever", echecs, fenetre_absente)

    # --- Garde permanente : les deux indices sont bornés explicitement -----
    def bornes_explicites():
        arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "getAltitude"
            ),
            None,
        )
        assert methode is not None, "getAltitude() introuvable"

        # La forme attendue est une comparaison chaînée 0 <= i < taille, sur
        # les deux axes : deux comparaisons à trois opérandes au moins.
        chainees = [
            n
            for n in ast.walk(methode)
            if isinstance(n, ast.Compare) and len(n.comparators) == 2
        ]
        assert len(chainees) >= 2, (
            "les deux indices doivent être bornés explicitement, et non "
            "remis à un except sur l'indexation : %d comparaison(s) chaînée(s) "
            "trouvée(s)" % len(chainees)
        )
        # La taille du tableau doit être consultée.
        formes = [
            n
            for n in ast.walk(methode)
            if isinstance(n, ast.Attribute) and n.attr == "shape"
        ]
        assert formes, "la taille de la fenêtre (.shape) n'est pas consultée"

    verifier("Garde : les deux indices bornés explicitement", echecs, bornes_explicites)

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nAucun sommet hors de la fenêtre de MNT ne reçoit l'altitude d'ailleurs.")
