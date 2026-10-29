# -*- coding: utf-8 -*-
"""Test de la répartition des gestes : clics de souris et touches.

`tests/test_table_outils.py` vérifie la table des gestes toute seule. Ce test
vérifie la suite : que `stereoPhoto` consulte bien cette table et qu'il appelle
le traitement qu'elle nomme. Entre les deux se trouvent les deux tables de
traduction de la classe, qui font passer des boutons de Qt et des types de
géométrie de QGIS aux clés de la table, et c'est là qu'une case oubliée
rendrait un geste inerte sans que la table elle-même soit en cause.

Même chose pour le clavier. Les sept touches traitées sont des littéraux dans
une cascade de `if`/`elif`, et l'intercepteur de la navigation avale tout le
clavier : une touche qui n'arrive pas à son traitement ne laisse aucune trace,
et aucun raccourci de QGIS ne vient compenser. `Ctrl+Z` et `Ctrl+S` sont les
deux seuls accès à l'annulation et à l'enregistrement pendant la navigation.

Quatre familles de cas :

1. Le clic : les trente-six combinaisons arrivent au traitement que la table
   nomme, dans les deux états de tracé.
2. Les gardes du clic : refus porté à l'utilisateur, silence qui reste muet,
   aucune couche choisie.
3. Les deux tables de traduction de la classe, lues par analyse syntaxique :
   elles doivent couvrir les trois boutons et les trois types.
4. La touche : chaque touche traitée atteint son traitement, un relâchement de
   touche ne déclenche rien, et `Ctrl+Z` comme `Ctrl+S` exigent le
   modificateur.

Les deux méthodes sont extraites du fichier source par analyse syntaxique, puis
exécutées avec des bouchons. `editionOutils` est importé pour de vrai, lui :
c'est le module sous test de l'autre fichier, et le prendre en bouchon ici ne
vérifierait plus le raccordement entre les deux.

Usage :
    python tests/test_repartition_gestes.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Valeurs numériques des constantes de Qt employées par keyboardHandler, pour
# que le test s'exécute sans Qt installé. Elles viennent de Qt::Key et de
# Qt::KeyboardModifier, et ne changent pas d'une version à l'autre : ce sont
# les valeurs que l'extension reçoit réellement.
KEY_ESCAPE = 0x01000000
KEY_F5 = 0x01000034
KEY_F13 = 0x0100003C
KEY_1 = 0x31
KEY_C = 0x43
KEY_M = 0x4D
KEY_S = 0x53
KEY_Z = 0x5A
KEY_A = 0x41
NO_MODIFIER = 0x00000000
CONTROL_MODIFIER = 0x04000000

TYPE_EVENEMENT_PRESSE = 6
TYPE_EVENEMENT_RELACHE = 7


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
    """Les constantes de Qt que les deux méthodes lisent, et rien de plus."""

    Key_Escape = KEY_ESCAPE
    Key_F5 = KEY_F5
    Key_F13 = KEY_F13
    Key_1 = KEY_1
    Key_C = KEY_C
    Key_M = KEY_M
    Key_S = KEY_S
    Key_Z = KEY_Z
    ControlModifier = CONTROL_MODIFIER
    NoModifier = NO_MODIFIER


class QEventBouchon:
    KeyPress = TYPE_EVENEMENT_PRESSE
    KeyRelease = TYPE_EVENEMENT_RELACHE


class EvenementClavierBouchon:
    def __init__(self, touche, modificateurs=NO_MODIFIER, presse=True):
        self._touche = touche
        self._modificateurs = modificateurs
        self._type = TYPE_EVENEMENT_PRESSE if presse else TYPE_EVENEMENT_RELACHE
        self.accepte = 0

    def type(self):
        return self._type

    def key(self):
        return self._touche

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
        "QEvent": QEventBouchon,
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


def casRoutageDesTouches(chemin_app):
    """Chaque touche traitée atteint son traitement."""
    echecs = []
    alertes = []
    methodes, _mod = monter(chemin_app, ("keyboardHandler",), alertes)
    traiter = methodes["keyboardHandler"]

    def verifier(description, touche, modificateurs, attendu, **reglages):
        app = ApplicationBouchon(**reglages.pop("bouchon", {}))
        for nom, valeur in reglages.items():
            setattr(app, nom, valeur)
        evenement = EvenementClavierBouchon(touche, modificateurs)
        traiter(app, evenement)
        if app.appels != attendu:
            echecs.append("%s : %r au lieu de %r" % (description, app.appels, attendu))
        if not evenement.accepte:
            echecs.append("%s : l'événement n'a pas été accepté" % description)
        return app

    verifier(
        "Échap en navigation synchronisée",
        KEY_ESCAPE,
        NO_MODIFIER,
        ["windowHandler:qgis"],
    )
    verifier(
        "Échap en hors-synchronisation",
        KEY_ESCAPE,
        NO_MODIFIER,
        ["retourNavigationPhoto"],
        horsSynchronisation=True,
    )
    verifier("F5, premier niveau de zoom", KEY_F5, NO_MODIFIER, ["keyboardZoom:0"])
    verifier(
        "F12, dernier niveau de zoom", KEY_F13 - 1, NO_MODIFIER, ["keyboardZoom:7"]
    )
    verifier("touche 1, outil de tracé", KEY_1, NO_MODIFIER, ["basculerOutilTrace"])
    verifier("Ctrl+Z, annulation", KEY_Z, CONTROL_MODIFIER, ["annulerEdition"])
    verifier("Ctrl+S, enregistrement", KEY_S, CONTROL_MODIFIER, ["enregistrerEdition"])

    # F13 est hors de l'intervalle de zoom : la touche doit rester inerte.
    verifier("F13, hors des huit niveaux", KEY_F13, NO_MODIFIER, [])

    # M ne bascule le suivi du MNT que si un MNT est chargé.
    app = ApplicationBouchon(mntArr=None)
    traiter(app, EvenementClavierBouchon(KEY_M, NO_MODIFIER))
    if app.actionSuivreMNT.bascules:
        echecs.append("M sans MNT chargé : le suivi a basculé")

    app = ApplicationBouchon(mntArr=[[0.0]])
    traiter(app, EvenementClavierBouchon(KEY_M, NO_MODIFIER))
    if app.actionSuivreMNT.bascules != 1:
        echecs.append(
            "M avec MNT chargé : %d bascule(s) au lieu d'une"
            % app.actionSuivreMNT.bascules
        )

    app = ApplicationBouchon()
    traiter(app, EvenementClavierBouchon(KEY_C, NO_MODIFIER))
    if app.actionUnlockCursor.bascules != 1:
        echecs.append(
            "C : %d bascule(s) au lieu d'une" % app.actionUnlockCursor.bascules
        )

    return echecs, "Échap, F5-F12, 1, Ctrl+Z, Ctrl+S, M, C"


def casGardesDesTouches(chemin_app):
    """Un relâchement ne déclenche rien, et les raccourcis exigent Ctrl."""
    echecs = []
    alertes = []
    methodes, _mod = monter(chemin_app, ("keyboardHandler",), alertes)
    traiter = methodes["keyboardHandler"]

    # Relâchement de touche : aucune des branches ne doit s'exécuter, sans
    # quoi un geste serait joué deux fois par frappe.
    for touche, nom in ((KEY_ESCAPE, "Échap"), (KEY_1, "1"), (KEY_Z, "Z")):
        app = ApplicationBouchon()
        traiter(app, EvenementClavierBouchon(touche, CONTROL_MODIFIER, presse=False))
        if app.appels or app.actionSuivreMNT.bascules:
            echecs.append("relâchement de %s : %r exécuté" % (nom, app.appels))

    # Z et S sans Ctrl ne sont pas des raccourcis d'édition : une saisie de
    # texte ne doit pas annuler le travail.
    for touche, nom in ((KEY_Z, "Z"), (KEY_S, "S")):
        app = ApplicationBouchon()
        traiter(app, EvenementClavierBouchon(touche, NO_MODIFIER))
        if app.appels:
            echecs.append("%s sans Ctrl : %r exécuté" % (nom, app.appels))

    # Une touche sans branche reste inerte, et l'événement est accepté quand
    # même : c'est l'interception volontaire de la navigation.
    app = ApplicationBouchon()
    evenement = EvenementClavierBouchon(KEY_A, NO_MODIFIER)
    traiter(app, evenement)
    if app.appels:
        echecs.append("touche A : %r exécuté" % app.appels)
    if not evenement.accepte:
        echecs.append("touche A : l'événement n'a pas été accepté")

    return echecs, "relâchements, Z et S sans Ctrl, touche sans branche"


def casOutilSansDoublon(chemin_app):
    """L'outil actif n'a qu'une représentation : les actions de la barre.

    Le panneau portait deux radios, Dessiner et Découper, qui ne disaient que
    la moitié de l'état : un couple exclusif ne représente pas quatre outils,
    et il fallait les accorder dans les deux sens à chaque changement d'outil,
    de couche et de session. La barre les a remplacées.

    L'alternance de la touche 1 était annoncée par leurs infobulles. Les deux
    outils qu'elle alterne doivent donc la porter, sans quoi le raccourci
    disparaît de l'interface avec les radios.
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
    annonces = [libelle for libelle in libelles if "touche 1" in libelle]
    if len(annonces) < 2:
        echecs.append(
            "%d libellé(s) annonçant la touche 1 : les deux outils qu'elle "
            "alterne doivent la porter" % len(annonces)
        )
    return echecs, "une seule représentation, alternance annoncée"


CAS = (
    ("routage des clics", casRoutageDuClic),
    ("gardes du clic", casGardesDuClic),
    ("tables de traduction de la classe", casTablesDeTraduction),
    ("routage des touches", casRoutageDesTouches),
    ("gardes du clavier", casGardesDesTouches),
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
