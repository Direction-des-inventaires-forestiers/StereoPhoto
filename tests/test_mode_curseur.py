# -*- coding: utf-8 -*-
"""Test de la bascule entre les deux comportements de navigation.

Couvre les deux pièces qui décident du comportement, sans
passer par l'interface :

1. `navigationMapTool.recenterMouse()`, le piège à souris. En mode synchronisé
   il recentre la carte et téléporte le curseur ; en mode curseur libre il doit
   être inerte, sans quoi les photos continueraient de défiler.
2. `stereoPhoto.afficherAltitude()`, l'affichage de l'altitude au panneau.
   Elle est portée par les deux modes et ne doit jamais être recalculée depuis
   la position des vues : seul son affichage est ici en
   jeu, avec le repli « N/D » quand la parallaxe est incalculable.

Les deux fonctions sont extraites de leur fichier source par analyse
syntaxique, puis exécutées avec des bouchons : aucune dépendance à QGIS, Qt,
GDAL ni numpy n'est nécessaire.

Usage :
    python tests/test_mode_curseur.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys
import types

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")


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
            "méthode %s.%s introuvable dans %s" % (classe_visee, methode_visee, chemin)
        )

    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return espace[methode_visee]


class CanevasBouchon:
    def __init__(self):
        self.centres = []
        self.rafraichissements = 0

    def setCenter(self, coord):
        self.centres.append(coord)

    def refresh(self):
        self.rafraichissements += 1


class CurseurBouchon:
    """Remplace QCursor : relève les téléportations du curseur système."""

    positions = []

    @classmethod
    def setPos(cls, position):
        cls.positions.append(position)


class OutilBouchon:
    """Porte l'état que recenterMouse() lit, sans la machinerie de QgsMapTool."""

    def __init__(self, curseurLibre):
        self.curseurLibre = curseurLibre
        self.canvas = CanevasBouchon()
        self.centerGlobalPos = (640, 400)
        self.currentMouseCoord = (381000.0, 5391500.0)
        self.lastEmittedCoord = None
        self.ignoringSyntheticMove = False
        self.recentrages = 0

    def clearSyntheticGuard(self):
        self.ignoringSyntheticMove = False

    def tracerRecentrages(self):
        # Diagnostic du piège : compté ici, sans journalisation.
        self.recentrages += 1


class EtiquetteBouchon:
    def __init__(self):
        self.texte = None

    def setText(self, valeur):
        self.texte = valeur


class ApplicationBouchon:
    """Porte l'état que afficherAltitude() lit sur la classe stereoPhoto."""

    def __init__(self, altitude=212.5):
        self.etiquette = EtiquetteBouchon()
        self.optWindow = types.SimpleNamespace(
            ui=types.SimpleNamespace(labelAltitude=self.etiquette)
        )
        self.cursorAltitude = altitude


def cas_piege_a_souris(chemin_outil):
    """Le piège à souris agit en mode synchronisé, pas en mode curseur libre."""
    echecs = []

    for libelle, curseurLibre, recentrage_attendu in (
        ("mode synchronisé : le piège agit", False, True),
        ("mode curseur libre : le piège est inerte", True, False),
    ):
        espace = {
            "QCursor": CurseurBouchon,
            "QCoreApplication": types.SimpleNamespace(processEvents=lambda *a: None),
            "QEventLoop": types.SimpleNamespace(ExcludeUserInputEvents=0),
            "QTimer": types.SimpleNamespace(singleShot=lambda delai, rappel: rappel()),
        }
        recenterMouse = extraire_methode(
            chemin_outil, "navigationMapTool", "recenterMouse", espace
        )

        outil = OutilBouchon(curseurLibre)
        CurseurBouchon.positions = []
        recenterMouse(outil)

        recentre = bool(outil.canvas.centres) or bool(CurseurBouchon.positions)
        try:
            assert recentre == recentrage_attendu, (
                "recentrage %s : carte recentrée %d fois, curseur déplacé %d fois"
                % (
                    "attendu mais absent" if recentrage_attendu else "effectué à tort",
                    len(outil.canvas.centres),
                    len(CurseurBouchon.positions),
                )
            )
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-52s %s" % (libelle, erreur))
        else:
            print("OK     %-52s" % libelle)

    return echecs


def cas_altitude(chemin_app):
    """L'altitude est affichée telle qu'elle est portée, jamais recalculée."""
    echecs = []
    espace = {}
    afficherAltitude = extraire_methode(
        chemin_app, "stereoPhoto", "afficherAltitude", espace
    )

    # L'altitude portée est affichée à trois décimales, dans les deux modes :
    # ni la position des vues ni celle de la croix n'entrent dans son calcul.
    libelle = "altitude portée : affichée telle quelle"
    app = ApplicationBouchon(altitude=212.5)
    try:
        afficherAltitude(app)
        assert app.cursorAltitude == 212.5, "altitude modifiée par l'affichage : %r" % (
            app.cursorAltitude,
        )
        assert app.etiquette.texte == "212.500", "étiquette %r" % (app.etiquette.texte,)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Une altitude négative s'affiche comme les autres : c'est la dérive de #48
    # qui était en cause, pas la valeur, qui peut être sous le niveau de la mer.
    libelle = "altitude négative : affichée sans traitement"
    app = ApplicationBouchon(altitude=-12.25)
    try:
        afficherAltitude(app)
        assert app.etiquette.texte == "-12.250", "étiquette %r" % (app.etiquette.texte,)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Altitude indéterminée : le repli « N/D » doit tenir dans les deux
    # modes, la parallaxe pouvant être incalculable où que soit la croix.
    libelle = "altitude indéterminée : repli « N/D »"
    app = ApplicationBouchon(altitude=None)
    try:
        afficherAltitude(app)
        assert app.etiquette.texte == "N/D", "étiquette %r" % (app.etiquette.texte,)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


def executer(dossier_source):
    chemin_outil = os.path.join(dossier_source, "navigationQgsMapTool.py")
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")

    echecs = cas_piege_a_souris(chemin_outil)
    echecs += cas_altitude(chemin_app)
    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nLes deux comportements de navigation se distinguent comme prévu.")
