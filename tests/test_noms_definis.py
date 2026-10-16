# -*- coding: utf-8 -*-
"""Garde contre les noms lus sans avoir été assignés (registre NAV-01).

Rejoue le défaut relevé le 2026-10-16 pendant l'analyse 3A.1 du Sprint A :
l'assignation `gwR = self.graphWindowRight.ui.graphicsView` avait disparu de
`updateUserAltitude()` et de `keyboardZoom()` au commit 2b2665b, alors que
`gwR` y est lu deux lignes plus loin. `updateUserAltitude()` étant appelée par
`mouseMoveEvent()`, le `NameError` tombait au premier mouvement de souris en
navigation.

Pourquoi un test plutôt que le contrôle de style : `pyproject.toml` ignore
`F403` et `F405` le temps que l'issue A8 soit traitée, et l'inférence des noms
non définis est abandonnée dès qu'un import étoile est présent dans le fichier.
Les quatre modules couverts ici sont précisément ceux qui portent des imports
étoile, donc ceux que le contrôle automatique ne protège pas.

Principe : le test refait l'analyse des portées (module, classe, fonction,
lambda) et relève les noms lus qui ne sont liés nulle part. Les imports étoile
de modules du dépôt sont résolus en lisant le module voisin ; ceux de QGIS et
de Qt ne peuvent pas l'être, donc les noms qu'ils fournissent sont figés dans
l'inventaire `NOMS_QGIS_ET_QT` ci-dessous. Tout nom non résolu absent de cet
inventaire est un défaut.

L'inventaire est lui-même contrôlé : il ne peut contenir que des noms de la
forme de ceux qu'exportent QGIS et Qt. Sans quoi il suffirait d'y ajouter le
nom d'une variable locale pour faire taire le test.

Ce fichier devient superflu quand A8 retire les imports étoile et que `F403` et
`F405` sortent de la liste `ignore` : le contrôle de style signalera les noms
non définis de lui-même.

Usage :
    python tests/test_noms_definis.py [chemin/vers/module.py ...]

Sans argument, les modules testés sont les quatre porteurs d'imports étoile de
`src/`, résolus depuis la racine du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import builtins
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Les quatre modules de src/ qui portent des imports étoile, donc les quatre
# que `ruff check` ne protège pas contre les noms non définis.
MODULES_DEFAUT = (
    os.path.join(RACINE, "src", "stereoPhoto.py"),
    os.path.join(RACINE, "src", "drawFunction.py"),
    os.path.join(RACINE, "src", "enhanceManager.py"),
    os.path.join(RACINE, "src", "navigationQgsMapTool.py"),
)

# Noms fournis par les imports étoile de QGIS et de Qt, qui ne peuvent pas être
# résolus sans installer QGIS. Relevé du 2026-10-16 sur les quatre modules.
# Un nom retiré du code peut rester ici sans conséquence ; un nom ajouté au code
# doit être ajouté ici, et seulement s'il vient bien de QGIS ou de Qt.
NOMS_QGIS_ET_QT = frozenset(
    (
        "QAction",
        "QApplication",
        "QBrush",
        "QColor",
        "QCoreApplication",
        "QCursor",
        "QEvent",
        "QEventLoop",
        "QGraphicsEllipseItem",
        "QGraphicsLineItem",
        "QGraphicsPathItem",
        "QGraphicsPixmapItem",
        "QGraphicsPolygonItem",
        "QGraphicsRectItem",
        "QGraphicsScene",
        "QGraphicsView",
        "QGuiApplication",
        "QIcon",
        "QImage",
        "QKeyEvent",
        "QLineF",
        "QObject",
        "QPainterPath",
        "QPen",
        "QPixmap",
        "QPoint",
        "QPointF",
        "QPolygonF",
        "QRectF",
        "QThread",
        "QTimer",
        "QTransform",
        "QVariant",
        "QgsCoordinateReferenceSystem",
        "QgsFeature",
        "QgsField",
        "QgsFields",
        "QgsGeometry",
        "QgsLineString",
        "QgsMapLayerType",
        "QgsPoint",
        "QgsPointXY",
        "QgsProject",
        "QgsRectangle",
        "QgsVectorFileWriter",
        "QgsVectorLayerEditUtils",
        "QgsWkbTypes",
        "Qt",
        "QtCore",
        "pyqtSignal",
        "qApp",
    )
)

# Noms en minuscule qu'exportent réellement Qt et QGIS. Hors de cette liste, un
# nom de l'inventaire doit avoir la forme d'une classe de Qt (« QAction »), d'une
# classe de QGIS (« QgsPointXY ») ou d'un module de Qt (« Qt », « QtCore »).
MINUSCULES_ADMISES = frozenset(
    ("qApp", "qVersion", "qrgb", "pyqtSignal", "pyqtSlot", "pyqtProperty", "iface")
)

# Noeuds qui ouvrent une portée de noms.
PORTEES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)

NOMS_IMPLICITES = frozenset(("__name__", "__file__", "__doc__", "__spec__"))


def lire(chemin):
    return ast.parse(io.open(chemin, encoding="utf-8").read())


def corps(noeud):
    """Corps du noeud, toujours sous forme de liste (`Lambda` n'en a qu'un)."""
    valeur = noeud.body
    return valeur if isinstance(valeur, list) else [valeur]


def sous_arbre_meme_portee(racine):
    """Noeuds du sous-arbre de `racine`, sans entrer dans les portées filles."""
    if isinstance(racine, PORTEES):
        return []
    vus = []
    pile = [racine]
    while pile:
        noeud = pile.pop()
        vus.append(noeud)
        for enfant in ast.iter_child_nodes(noeud):
            if isinstance(enfant, PORTEES):
                continue
            pile.append(enfant)
    return vus


def noeuds_portee(noeud):
    """Noeuds appartenant à la portée de `noeud`, portées filles exclues."""
    out = []
    for instruction in corps(noeud):
        out.extend(sous_arbre_meme_portee(instruction))
    return out


def parametres(noeud):
    """Noms des paramètres d'une fonction ou d'une lambda."""
    out = set()
    arguments = getattr(noeud, "args", None)
    if not isinstance(arguments, ast.arguments):
        return out
    declares = (
        list(getattr(arguments, "posonlyargs", []))
        + list(arguments.args)
        + list(arguments.kwonlyargs)
    )
    for argument in declares:
        out.add(argument.arg)
    if arguments.vararg:
        out.add(arguments.vararg.arg)
    if arguments.kwarg:
        out.add(arguments.kwarg.arg)
    return out


def noms_lies(noeud):
    """Noms liés dans la portée de `noeud` : paramètres, assignations, imports."""
    out = parametres(noeud)
    for instruction in corps(noeud):
        if isinstance(instruction, PORTEES):
            # Une portée fille ne lie que son propre nom dans la portée mère.
            nom = getattr(instruction, "name", None)
            if nom:
                out.add(nom)
            continue
        for n in sous_arbre_meme_portee(instruction):
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
                out.add(n.id)
            elif isinstance(n, (ast.Import, ast.ImportFrom)):
                for alias in n.names:
                    if alias.name != "*":
                        out.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                out.update(n.names)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                out.add(n.name)
            elif isinstance(n, ast.ExceptHandler) and n.name:
                out.add(n.name)
    return out


def noms_charges(noeud):
    """Noms lus dans la portée de `noeud`, avec les lignes où ils sont lus."""
    out = {}
    for n in noeuds_portee(noeud):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.setdefault(n.id, set()).add(n.lineno)
    return out


def portees_filles(noeud):
    """Portées déclarées directement dans la portée de `noeud`."""
    out = []
    for instruction in corps(noeud):
        pile = [instruction]
        while pile:
            n = pile.pop()
            if isinstance(n, PORTEES):
                out.append(n)
                continue
            for enfant in ast.iter_child_nodes(n):
                pile.append(enfant)
    return out


def noms_publics(chemin):
    """Noms de niveau module qu'un import étoile de ce fichier fournirait."""
    return {n for n in noms_lies(lire(chemin)) if not n.startswith("_")}


def noms_des_etoiles_locales(chemin):
    """Noms fournis par les imports étoile de modules voisins du dépôt."""
    dossier = os.path.dirname(os.path.abspath(chemin))
    out = set()
    for n in ast.walk(lire(chemin)):
        if not isinstance(n, ast.ImportFrom):
            continue
        if not any(alias.name == "*" for alias in n.names):
            continue
        if n.level and n.module:
            voisin = os.path.join(dossier, n.module + ".py")
            if os.path.exists(voisin):
                out |= noms_publics(voisin)
    return out


def noms_non_resolus(chemin):
    """Noms lus sans être liés dans aucune portée visible, et leurs lignes.

    Retourne {nom: [lignes triées]}. Toutes les occurrences sont relevées, et
    non la première seulement : un même nom peut manquer dans plusieurs
    méthodes, comme `gwR` l'était dans deux.
    """
    arbre = lire(chemin)
    globaux = (
        noms_lies(arbre)
        | set(dir(builtins))
        | noms_des_etoiles_locales(chemin)
        | NOMS_IMPLICITES
    )
    trouves = {}

    def relever(noeud, visibles):
        for nom, lignes in noms_charges(noeud).items():
            if nom not in visibles:
                trouves.setdefault(nom, set()).update(lignes)
        for fille in portees_filles(noeud):
            relever(fille, visibles | noms_lies(fille))

    relever(arbre, globaux)
    return {nom: sorted(lignes) for nom, lignes in trouves.items()}


def forme_de_qgis_ou_qt(nom):
    """Vrai si `nom` a la forme d'un symbole exporté par QGIS ou par Qt."""
    if nom in MINUSCULES_ADMISES:
        return True
    if nom == "Qt":  # le module de constantes, Qt.LeftButton et les autres
        return True
    if nom.startswith("Qgs") and len(nom) > 3 and nom[3].isupper():
        return True  # classe de QGIS : QgsPointXY, QgsWkbTypes
    if nom.startswith("Qt") and len(nom) > 2 and nom[2].isupper():
        return True  # module de Qt : QtCore, QtGui
    if len(nom) > 1 and nom[0] == "Q" and nom[1].isupper():
        return True  # classe de Qt : QAction, QPointF
    return False


def controler_inventaire():
    """Vérifie que l'inventaire ne contient que des noms de QGIS ou de Qt."""
    return [nom for nom in sorted(NOMS_QGIS_ET_QT) if not forme_de_qgis_ou_qt(nom)]


def executer(cibles):
    """Retourne (noms non définis, défauts de l'inventaire)."""
    defauts = []
    suspects = controler_inventaire()

    if suspects:
        print(
            "ECHEC  %-32s %d nom(s) sans la forme de QGIS ni de Qt : %s"
            % ("inventaire", len(suspects), ", ".join(suspects))
        )
    else:
        print(
            "OK     %-32s %d noms, tous de la forme de QGIS ou de Qt"
            % ("inventaire", len(NOMS_QGIS_ET_QT))
        )

    for chemin in cibles:
        nom_court = os.path.basename(chemin)
        if not os.path.exists(chemin):
            defauts.append((nom_court, None, "fichier absent"))
            print("ECHEC  %-32s fichier absent" % nom_court)
            continue

        non_resolus = noms_non_resolus(chemin)
        inconnus = [
            (ligne, nom)
            for nom, lignes in non_resolus.items()
            if nom not in NOMS_QGIS_ET_QT
            for ligne in lignes
        ]
        if inconnus:
            for ligne, nom in sorted(inconnus):
                defauts.append((nom_court, ligne, nom))
                print(
                    "ECHEC  %-32s %s lu sans assignation, l.%d"
                    % (nom_court, nom, ligne)
                )
        else:
            print(
                "OK     %-32s %d noms lus, tous liés ou fournis par QGIS et Qt"
                % (nom_court, len(non_resolus))
            )

    return defauts, suspects


if __name__ == "__main__":
    modules = sys.argv[1:] or list(MODULES_DEFAUT)
    print("Modules testés : %d\n" % len(modules))
    noms_fautifs, inventaire_fautif = executer(modules)

    if noms_fautifs:
        print(
            "\n%d nom(s) lu(s) sans assignation : chacun lève NameError dès que "
            "la ligne est atteinte." % len(noms_fautifs)
        )
    if inventaire_fautif:
        print(
            "\nInventaire à revoir : %d nom(s) n'ont pas la forme d'un symbole de "
            "QGIS ni de Qt. Un nom de variable locale n'a pas à y figurer."
            % len(inventaire_fautif)
        )
    if noms_fautifs or inventaire_fautif:
        sys.exit(1)

    print("\nAucun nom lu sans assignation dans les %d modules." % len(modules))
