# -*- coding: utf-8 -*-
"""Test de la répartition des clics de souris.

`tests/test_table_outils.py` vérifie la table des gestes toute seule. Ce test
vérifie la suite : que `stereoPhoto` consulte bien cette table et qu'il appelle
le traitement qu'elle nomme. Entre les deux se trouvent les deux tables de
traduction de la classe, qui font passer des boutons de Qt et des types de
géométrie de QGIS aux clés de la table, et c'est là qu'une case oubliée
rendrait un geste inerte sans que la table elle-même soit en cause.

Le clavier était éprouvé ici aussi, du temps où ses sept touches étaient des
littéraux dans une cascade de `if`/`elif`. Il a sa table et son fichier depuis,
et son routage est éprouvé par `tests/test_raccourcis_clavier.py` : garder les
deux aurait fait éprouver le même routage à deux endroits, qui auraient
divergé.

Quatre familles de cas :

1. Le clic : les trente-six combinaisons arrivent au traitement que la table
   nomme, dans les deux états de tracé.
2. Les gardes du clic : refus porté à l'utilisateur, silence qui reste muet,
   aucune couche choisie.
3. Les deux tables de traduction de la classe, lues par analyse syntaxique :
   elles doivent couvrir les trois boutons et les trois types.
4. La représentation de l'outil actif : les actions de la barre, seules, et
   aucun libellé qui nomme une touche en littéral.

La méthode est extraite du fichier source par analyse syntaxique, puis exécutée
avec des bouchons. `editionOutils` est importé pour de vrai, lui : c'est le
module sous test de l'autre fichier, et le prendre en bouchon ici ne
vérifierait plus le raccordement entre les deux.

Usage :
    python tests/test_repartition_gestes.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Valeur numérique du modificateur vide de Qt, pour que le test s'exécute sans
# Qt installé. Les clics voyagent avec leurs modificateurs depuis que la
# sélection additive en a besoin.
NO_MODIFIER = 0x00000000

# Une touche nommée dans un libellé de la barre d'outils : « touche 1 »,
# « Ctrl+S ». Plus aucun libellé ne doit en porter, les raccourcis étant
# configurables et composés par annoncerRaccourcis().
MOTIF_TOUCHE = re.compile(r"(?i)touche\s+[A-Z0-9]|Ctrl\+[A-Z]|Alt\+[A-Z]")


def extraire_methodes(chemin, classe_visee, methodes_visees, espace):
    """Retourne des méthodes d'une classe, isolées de leur module."""
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
        if isinstance(n, ast.FunctionDef) and n.name in methodes_visees
    ]
    manquantes = set(methodes_visees) - {n.name for n in corps}
    if manquantes:
        raise AssertionError(
            "méthode(s) %s introuvable(s) dans %s"
            % (", ".join(sorted(manquantes)), classe_visee)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in methodes_visees}


class QtBouchon:
    """Les constantes de Qt que la méthode lit, et rien de plus."""

    NoModifier = NO_MODIFIER

    def modifiers(self):
        return self._modificateurs

    def accept(self):
        self.accepte += 1


class ActionBouchon:
    def __init__(self):
        self.bascules = 0

    def toggle(self):
        self.bascules += 1


class OptWindowBouchon:
    def __init__(self, mntArr=None):
        self.mntArr = mntArr


class ApplicationBouchon:
    """Porte le strict nécessaire aux deux méthodes extraites."""

    def __init__(self, typeGeometrie="polygone", mntArr=None):
        self.appels = []
        self.enableDraw = True
        self.vectorLayer = object()
        self.vectorLayerName = "couche d'essai"
        self.outilActif = "ajouter"
        self.traceEnCours = False
        self.horsSynchronisation = False
        self._typeGeometrie = typeGeometrie
        self.optWindow = OptWindowBouchon(mntArr)
        self.actionSuivreMNT = ActionBouchon()
        self.actionUnlockCursor = ActionBouchon()

        # Les boutons sont déjà des clés de editionOutils : la traduction de la
        # classe est vérifiée à part, par analyse syntaxique.
        self.BOUTONS_QT = {"gauche": "gauche", "droit": "droit", "milieu": "milieu"}

        self.tableTraitements = {
            cle: (lambda pos, mod, _c=cle: self.appels.append(_c))
            for cle in (
                "selectionner",
                "viderSelection",
                "ajouterPoint",
                "poserSommet",
                "cloreLigne",
                "clorePolygone",
                "cloreDecoupe",
                "fusionnerSelection",
            )
        }

    def typeGeometrieCouche(self):
        return self._typeGeometrie

    # Récepteurs du clavier, relevés et non exécutés.
    def retourNavigationPhoto(self):
        self.appels.append("retourNavigationPhoto")

    def windowHandler(self, fenetre):
        self.appels.append("windowHandler:%s" % fenetre)

    def keyboardZoom(self, valeur):
        self.appels.append("keyboardZoom:%d" % valeur)

    def basculerOutilTrace(self):
        self.appels.append("basculerOutilTrace")

    def annulerEdition(self):
        self.appels.append("annulerEdition")

    def enregistrerEdition(self):
        self.appels.append("enregistrerEdition")


def monter(chemin_app, methodes_voulues, alertes):
    """Monte les méthodes demandées, et rend leur espace de noms."""
    sys.path.insert(0, os.path.dirname(chemin_app))
    import editionOutils

    def avertir_utilisateur(message, *args, **kwargs):
        alertes.append(message)

    espace = {
        "editionOutils": editionOutils,
        "avertir_utilisateur": avertir_utilisateur,
        "Qt": QtBouchon,
    }
    methodes = extraire_methodes(chemin_app, "stereoPhoto", methodes_voulues, espace)
    return methodes, editionOutils


def casRoutageDuClic(chemin_app):
    """Les 36 combinaisons arrivent au traitement que la table nomme."""
    echecs = []
    alertes = []
    methodes, editionOutils = monter(chemin_app, ("mousePressEvent",), alertes)
    cliquer = methodes["mousePressEvent"]

    for outil in editionOutils.OUTILS:
        for typeGeo in editionOutils.TYPES:
            for bouton in editionOutils.BOUTONS:
                for trace in (False, True):
                    attendu, _motif = editionOutils.resoudreTraitement(
                        outil, typeGeo, bouton, trace
                    )
                    app = ApplicationBouchon(typeGeometrie=typeGeo)
                    app.outilActif = outil
                    app.traceEnCours = trace
                    cliquer(app, bouton, (0.0, 0.0), NO_MODIFIER)
                    obtenu = app.appels[0] if app.appels else None
                    if obtenu != attendu:
                        echecs.append(
                            "%s/%s/%s, tracé %s : %r au lieu de %r"
                            % (outil, typeGeo, bouton, trace, obtenu, attendu)
                        )
                    if len(app.appels) > 1:
                        echecs.append(
                            "%s/%s/%s : %d traitements pour un clic"
                            % (outil, typeGeo, bouton, len(app.appels))
                        )
    return echecs, "36 combinaisons x 2 états de tracé"


def casGardesDuClic(chemin_app):
    """Refus porté à l'utilisateur, silence muet, aucune couche choisie."""
    echecs = []
    alertes = []
    methodes, _mod = monter(chemin_app, ("mousePressEvent",), alertes)
    cliquer = methodes["mousePressEvent"]

    # Refus : l'outil Découper sur une couche de points porte un message.
    app = ApplicationBouchon(typeGeometrie="point")
    app.outilActif = "decouper"
    del alertes[:]
    cliquer(app, "gauche", (0.0, 0.0), NO_MODIFIER)
    if app.appels:
        echecs.append("découper sur points : traitement %r exécuté" % app.appels)
    if len(alertes) != 1:
        echecs.append("découper sur points : %d message(s) au lieu d'un" % len(alertes))

    # Silence : le clic droit sous Ajouter sur une couche de points ne dit rien.
    app = ApplicationBouchon(typeGeometrie="point")
    app.outilActif = "ajouter"
    del alertes[:]
    cliquer(app, "droit", (0.0, 0.0), NO_MODIFIER)
    if app.appels or alertes:
        echecs.append(
            "ajouter/point/droit : %r exécuté, %d message(s)"
            % (app.appels, len(alertes))
        )

    # Bouton du milieu : réservé au déplacement, aucun message non plus.
    app = ApplicationBouchon()
    del alertes[:]
    cliquer(app, "milieu", (0.0, 0.0), NO_MODIFIER)
    if app.appels or alertes:
        echecs.append(
            "bouton du milieu : %r, %d message(s)" % (app.appels, len(alertes))
        )

    # Aucune couche choisie : le clic ne va nulle part, et sans message.
    for description, reglage in (
        ("enableDraw faux", {"enableDraw": False}),
        ("aucune couche", {"vectorLayer": None}),
    ):
        app = ApplicationBouchon()
        for nom, valeur in reglage.items():
            setattr(app, nom, valeur)
        del alertes[:]
        cliquer(app, "gauche", (0.0, 0.0), NO_MODIFIER)
        if app.appels or alertes:
            echecs.append(
                "%s : %r exécuté, %d message(s)"
                % (description, app.appels, len(alertes))
            )

    return echecs, "refus, silence, bouton du milieu, aucune couche"


def casTablesDeTraduction(chemin_app):
    """Les deux tables de la classe couvrent les trois boutons et les trois types.

    Lues par analyse syntaxique : leurs clés sont des attributs de Qt et de
    QgsWkbTypes, que ce test n'a pas. Une case oubliée ici rendrait un geste
    inerte sans que la table des gestes soit en cause.
    """
    echecs = []
    sys.path.insert(0, os.path.dirname(chemin_app))
    import editionOutils

    arbre = ast.parse(io.open(chemin_app, encoding="utf-8").read())
    classe = next(
        n
        for n in ast.walk(arbre)
        if isinstance(n, ast.ClassDef) and n.name == "stereoPhoto"
    )

    tables = {}
    for noeud in classe.body:
        if not isinstance(noeud, ast.Assign):
            continue
        for cible in noeud.targets:
            if isinstance(cible, ast.Name) and isinstance(noeud.value, ast.Dict):
                tables[cible.id] = noeud.value

    attendus = {
        "BOUTONS_QT": (
            {"LeftButton", "RightButton", "MiddleButton"},
            set(editionOutils.BOUTONS),
        ),
        "TYPES_GEOMETRIE_QGIS": (
            {"PointGeometry", "LineGeometry", "PolygonGeometry"},
            set(editionOutils.TYPES),
        ),
    }

    for nom, (clesAttendues, valeursAttendues) in attendus.items():
        table = tables.get(nom)
        if table is None:
            echecs.append("%s introuvable dans le corps de la classe" % nom)
            continue

        cles = {c.attr for c in table.keys if isinstance(c, ast.Attribute)}
        valeurs = {v.attr for v in table.values if isinstance(v, ast.Attribute)}

        manquantes = clesAttendues - cles
        if manquantes:
            echecs.append("%s : clé(s) absente(s) %s" % (nom, sorted(manquantes)))

        # Les valeurs sont des constantes de editionOutils : on compare ce
        # qu'elles valent, pas leur nom.
        valeursReelles = {
            getattr(editionOutils, v) for v in valeurs if hasattr(editionOutils, v)
        }
        if valeursReelles != valeursAttendues:
            echecs.append(
                "%s : valeurs %s au lieu de %s"
                % (nom, sorted(valeursReelles), sorted(valeursAttendues))
            )

    return echecs, "%d tables" % len(attendus)


def casOutilSansDoublon(chemin_app):
    """L'outil actif n'a qu'une représentation : les actions de la barre.

    Le panneau portait deux radios, Dessiner et Découper, qui ne disaient que
    la moitié de l'état : un couple exclusif ne représente pas quatre outils,
    et il fallait les accorder dans les deux sens à chaque changement d'outil,
    de couche et de session. La barre les a remplacées.

    L'alternance de la touche 1 était annoncée par leurs infobulles, et ce
    contrôle exigeait que les deux outils qu'elle alterne la portent. Les
    raccourcis sont depuis devenus configurables : plus aucun libellé ne peut
    nommer une touche, sans quoi il mentirait dès la première
    personnalisation. L'intention est la même — le clavier reste annoncé dans
    l'interface — mais c'est la table qui le fait, et c'est désormais
    l'absence de littéral qui est vérifiée.
    """
    echecs = []
    dossier = os.path.dirname(chemin_app)
    for nom in sorted(os.listdir(dossier)):
        if not nom.endswith((".py", ".ui")):
            continue
        source = io.open(os.path.join(dossier, nom), encoding="utf-8").read()
        for radio in ("radioButtonDraw", "radioButtonCut"):
            if radio in source:
                echecs.append("%s renvoie encore à %s" % (nom, radio))

    arbre = ast.parse(io.open(chemin_app, encoding="utf-8").read())
    initGui = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "initGui"
        ),
        None,
    )
    if initGui is None:
        echecs.append("initGui introuvable")
        return echecs, "fonction absente"

    libelles = [
        n.value
        for n in ast.walk(initGui)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]
    for libelle in libelles:
        if MOTIF_TOUCHE.search(libelle):
            echecs.append(
                "libellé d'initGui nommant une touche : %r — la mention vient "
                "de la table, par annoncerRaccourcis()" % libelle
            )

    # Les quatre outils doivent être nommés dans la table des raccourcis, sans
    # quoi ils n'auraient aucun accès clavier pendant la navigation.
    appels = [
        n
        for n in ast.walk(initGui)
        if isinstance(n, ast.Attribute) and n.attr == "ACTIONS_OUTIL"
    ]
    if not appels:
        echecs.append(
            "initGui ne consulte pas ACTIONS_OUTIL : les outils n'auraient "
            "aucune touche annoncée"
        )

    return echecs, "une seule représentation, aucune touche en littéral"


CAS = (
    ("routage des clics", casRoutageDuClic),
    ("gardes du clic", casGardesDuClic),
    ("tables de traduction de la classe", casTablesDeTraduction),
    ("outil sans doublon", casOutilSansDoublon),
)


def executer(source):
    chemin_app = os.path.join(source, "stereoPhoto.py")
    print("Modules testés : %s" % source)
    print()

    total = []
    for libelle, fonction in CAS:
        echecs, note = fonction(chemin_app)
        total.extend(echecs)
        print("%-6s %-44s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) relevé(s)." % len(total))
        return 1
    print("Les clics et les touches arrivent à leur traitement.")
    return 0


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    sys.exit(executer(source))
