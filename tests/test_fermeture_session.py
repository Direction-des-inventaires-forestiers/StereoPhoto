# -*- coding: utf-8 -*-
"""Test de la fermeture de la session de navigation.

Deux défauts relevés à l'usage sont gardés ici.

**Réentrance de `optWindowClose()`.** `optWindow.close()` déclenche le
`closeEvent` du panneau, qui réémet `closeWindow`, lui-même raccordé à
`optWindowClose()`. L'appel imbriqué atteignait `setChecked(False)`, donc le
`del self.optWindow` de `run()`, et l'appel extérieur trouvait ensuite
l'attribut disparu : `AttributeError` à la fermeture du panneau par son `X`.
`closeAllSideWindows()` avait reçu sa garde ; celle-ci lui manquait.

**Changement de projet pendant la navigation.** Le greffon ne se raccordait à
aucun signal de `QgsProject` : changer de projet ne fermait rien, les vues
photo restaient ouvertes sur un projet sans le SCR des photos, et le fichier de
paramètres de la session n'était pas écrit.

Les deux méthodes sont extraites du fichier source par analyse syntaxique, puis
exécutées avec des bouchons : aucune dépendance à QGIS ni à Qt n'est
nécessaire.

Usage :
    python tests/test_fermeture_session.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")


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
            "méthode(s) %s introuvable(s) dans %s.%s"
            % (", ".join(sorted(manquantes)), classe_visee, chemin)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in methodes_visees}


class JournalBouchon:
    def __init__(self):
        self.messages = []

    def _noter(self, niveau):
        def ecrire(gabarit, *args):
            self.messages.append((niveau, gabarit % args if args else gabarit))

        return ecrire

    def __getattr__(self, nom):
        if nom in ("debug", "info", "warning", "error", "exception"):
            return self._noter(nom)
        raise AttributeError(nom)


class ActionBouchon:
    """QAction cochable : le décochage exécute le récepteur, comme Qt le fait."""

    def __init__(self, coche, au_decochage=None):
        self._coche = coche
        self.au_decochage = au_decochage
        self.decochages = 0

    def isChecked(self):
        return self._coche

    def setChecked(self, valeur):
        change = valeur != self._coche
        self._coche = valeur
        if change and not valeur:
            self.decochages += 1
            if self.au_decochage is not None:
                self.au_decochage()


class VectorWindowBouchon:
    def __init__(self):
        self.fermetures = 0

    def close(self):
        self.fermetures += 1


class OptWindowBouchon:
    """Panneau d'options : close() réémet closeWindow, comme son closeEvent."""

    def __init__(self, au_close=None):
        self.vectorWindow = VectorWindowBouchon()
        self.au_close = au_close
        self.fermetures = 0
        self.parametres_ecrits = 0

    def close(self):
        self.fermetures += 1
        if self.au_close is not None:
            self.au_close()

    def saveParamFile(self):
        self.parametres_ecrits += 1


class ApplicationBouchon:
    """Porte le strict nécessaire aux deux méthodes extraites."""

    def __init__(self, journal):
        self.journal = journal
        self.fermetureSessionEnCours = False
        self.fermetureEnCours = False
        self.enableShow = False
        self.appels = []
        self.vues_memorisees = 0
        self.panneaux_retires = 0
        self.setLastView_leve = False
        self.vectorLayer = None
        self.vectorLayerName = None

    # La question du sort des modifications n'est pas sous test ici, son appel
    # est relevé. La fermeture ne doit pas en dépendre pour aboutir.
    def demanderSortEditions(self):
        self.appels.append("demanderSortEditions")

    def rompreRaccordementCouche(self):
        self.appels.append("rompreRaccordementCouche")

    # closeAllSideWindows() n'est pas sous test ici : son effet est relevé.
    def closeAllSideWindows(self):
        self.appels.append("closeAllSideWindows")
        self.optWindow.saveParamFile()

    def setLastView(self):
        self.vues_memorisees += 1
        if self.setLastView_leve:
            # Reproduit ce que faisait setLastView() sur une altitude
            # indéterminée : un TypeError depuis pixelToCoord().
            raise TypeError("unsupported operand type(s) for -: 'NoneType' and 'float'")


def verifier(libelle, echecs, controle):
    try:
        controle()
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-54s %s" % (libelle, erreur))
    except Exception as erreur:
        # Une exception autre qu'une assertion est elle-même le constat : c'est
        # l'AttributeError que ce test garde. On la rapporte au lieu de laisser
        # remonter une trace, pour que le rejeu sur une version d'avant le
        # correctif reste lisible.
        echecs.append((libelle, erreur))
        print("ECHEC  %-54s %s : %s" % (libelle, type(erreur).__name__, erreur))
    else:
        print("OK     %-54s" % libelle)


def monter(chemin_app, alertes, methodes_voulues):
    """Monte les méthodes demandées avec leurs bouchons, et rend l'application.

    Les méthodes sont extraites une à une : un scénario ne doit pas échouer
    parce qu'une méthode étrangère à son objet manque au fichier source.
    """
    journal = JournalBouchon()
    app = ApplicationBouchon(journal)

    def avertir_utilisateur(message, *args, **kwargs):
        alertes.append(message)

    class EditionVecteurBouchon:
        """Le module d'écriture, réduit à ce que la fermeture lui demande."""

        @staticmethod
        def modificationsEnAttente(_couche):
            return False, 0

    espace = {
        "avertir_utilisateur": avertir_utilisateur,
        "editionVecteur": EditionVecteurBouchon,
    }
    methodes = extraire_methodes(chemin_app, "stereoPhoto", methodes_voulues, espace)
    return methodes, app, journal


def executer(dossier_source):
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    echecs = []

    # --- Réentrance : le closeEvent du panneau rappelle optWindowClose() ----
    def reentrance_absorbee():
        alertes = []
        methodes, app, journal = monter(chemin_app, alertes, ("optWindowClose",))
        fermer = methodes["optWindowClose"]

        # Le panneau réémet closeWindow à sa fermeture, et le décochage de
        # l'action exécute run(), dont le `del self.optWindow`.
        def au_close():
            fermer(app)

        def au_decochage():
            # run() : retire le panneau, rappelle optWindowClose(), puis libère
            # l'attribut. C'est cette libération qui cassait l'appel extérieur.
            app.panneaux_retires += 1
            fermer(app)
            del app.optWindow

        app.optWindow = OptWindowBouchon(au_close=au_close)
        app.actionMainMenu = ActionBouchon(True, au_decochage=au_decochage)

        # L'appel ne doit pas lever, et la session doit être fermée.
        fermer(app)

        assert app.actionMainMenu.decochages == 1, (
            "%d décochage(s) au lieu d'un" % app.actionMainMenu.decochages
        )
        assert not app.fermetureSessionEnCours, "la garde reste levée après coup"
        assert app.panneaux_retires == 1, (
            "%d retrait(s) de panneau" % app.panneaux_retires
        )

    verifier(
        "Réentrance de optWindowClose() : absorbée, sans AttributeError",
        echecs,
        reentrance_absorbee,
    )

    # --- La garde laisse passer un second appel légitime, plus tard ---------
    def garde_relachee():
        alertes = []
        methodes, app, journal = monter(chemin_app, alertes, ("optWindowClose",))
        fermer = methodes["optWindowClose"]
        app.optWindow = OptWindowBouchon()
        app.actionMainMenu = ActionBouchon(False)

        fermer(app)
        assert not app.fermetureSessionEnCours, "la garde reste levée"
        premier = app.optWindow.fermetures
        fermer(app)
        assert app.optWindow.fermetures == premier + 1, (
            "le second appel, hors réentrance, doit agir"
        )

    verifier("Garde relâchée : un appel ultérieur agit encore", echecs, garde_relachee)

    # --- Panneau déjà libéré : aucun accès à l'attribut disparu -------------
    def panneau_absent():
        alertes = []
        methodes, app, journal = monter(chemin_app, alertes, ("optWindowClose",))
        fermer = methodes["optWindowClose"]
        app.actionMainMenu = ActionBouchon(False)
        # Pas d'attribut optWindow du tout : la méthode doit se retirer sans
        # lever, le cas se présentant quand run() l'a déjà libéré.
        app.closeAllSideWindows = lambda: app.appels.append("closeAllSideWindows")
        fermer(app)
        assert "closeAllSideWindows" in app.appels, "la démolition n'a pas eu lieu"

    verifier("Panneau déjà libéré : aucune AttributeError", echecs, panneau_absent)

    # --- Changement de projet, session ouverte : démolition et paramètres ---
    def projet_change_session_ouverte():
        alertes = []
        methodes, app, journal = monter(
            chemin_app, alertes, ("optWindowClose", "projetChange")
        )
        fermer = methodes["optWindowClose"]
        projetChange = methodes["projetChange"]

        def au_decochage():
            app.panneaux_retires += 1
            fermer(app)

        app.optWindow = OptWindowBouchon()
        app.actionMainMenu = ActionBouchon(True, au_decochage=au_decochage)
        app.enableShow = True

        projetChange(app)

        assert app.actionMainMenu.decochages == 1, "la session n'est pas fermée"
        assert app.optWindow.parametres_ecrits == 1, (
            "%d écriture(s) du fichier de paramètres" % app.optWindow.parametres_ecrits
        )
        assert app.vues_memorisees == 1, (
            "la vue courante n'est pas mémorisée avant la démolition"
        )
        assert len(alertes) == 1, "%d message(s) à l'utilisateur" % len(alertes)
        assert any(n == "info" for n, _ in journal.messages), "aucune trace au journal"

    verifier(
        "Projet changé, session ouverte : fermée et paramètres écrits",
        echecs,
        projet_change_session_ouverte,
    )

    # --- Changement de projet sans session : rien ne doit se produire ------
    def projet_change_sans_session():
        alertes = []
        methodes, app, journal = monter(chemin_app, alertes, ("projetChange",))
        projetChange = methodes["projetChange"]
        app.optWindow = OptWindowBouchon()
        app.actionMainMenu = ActionBouchon(False)

        projetChange(app)

        assert app.actionMainMenu.decochages == 0, "un décochage a eu lieu"
        assert app.optWindow.parametres_ecrits == 0, "des paramètres ont été écrits"
        assert alertes == [], "un message a été porté : %r" % (alertes,)

    verifier(
        "Projet changé sans session : aucun effet", echecs, projet_change_sans_session
    )

    # --- Mémorisation impossible : la fermeture doit aboutir quand même ----
    def memorisation_impossible():
        alertes = []
        methodes, app, journal = monter(
            chemin_app, alertes, ("optWindowClose", "projetChange")
        )
        fermer = methodes["optWindowClose"]
        projetChange = methodes["projetChange"]

        def au_decochage():
            app.panneaux_retires += 1
            fermer(app)

        app.optWindow = OptWindowBouchon()
        app.actionMainMenu = ActionBouchon(True, au_decochage=au_decochage)
        app.enableShow = True
        # L'altitude du curseur est indéterminée : setLastView() levait alors un
        # TypeError, qui partait vers la fenêtre d'erreur de QGIS et bloquait la
        # session derrière un dialogue modal, la fermeture n'ayant pas lieu.
        app.setLastView_leve = True

        projetChange(app)

        assert app.actionMainMenu.decochages == 1, (
            "la session n'est pas fermée : la mémorisation de la vue ne doit "
            "pas emporter la démolition"
        )
        assert app.optWindow.parametres_ecrits == 1, (
            "le fichier de paramètres n'est pas écrit"
        )

    verifier(
        "Vue non mémorisable : la fermeture aboutit quand même",
        echecs,
        memorisation_impossible,
    )

    # --- Garde permanente : le greffon se raccorde bien au projet ------------
    def raccordement_au_projet():
        source = io.open(chemin_app, encoding="utf-8").read()
        arbre = ast.parse(source)

        def methode(nom):
            return next(
                (
                    n
                    for n in ast.walk(arbre)
                    if isinstance(n, ast.FunctionDef) and n.name == nom
                ),
                None,
            )

        def mentionne(noeud, attribut, terminal):
            if noeud is None:
                return False
            for interne in ast.walk(noeud):
                if (
                    isinstance(interne, ast.Attribute)
                    and interne.attr == terminal
                    and isinstance(interne.value, ast.Attribute)
                    and interne.value.attr == attribut
                ):
                    return True
            return False

        assert mentionne(methode("initGui"), "cleared", "connect"), (
            "initGui() ne raccorde pas le signal cleared de QgsProject"
        )
        assert mentionne(methode("unload"), "cleared", "disconnect"), (
            "unload() ne rompt pas le raccordement : les connexions "
            "s'empileraient au rechargement de l'extension"
        )

    verifier(
        "Garde : raccordement au projet posé et rompu",
        echecs,
        raccordement_au_projet,
    )

    # --- Garde permanente : optWindowClose() porte une garde de réentrance --
    def garde_presente():
        source = io.open(chemin_app, encoding="utf-8").read()
        arbre = ast.parse(source)
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "optWindowClose"
            ),
            None,
        )
        assert methode is not None, "optWindowClose() introuvable"
        lus = {
            n.attr
            for n in ast.walk(methode)
            if isinstance(n, ast.Attribute) and n.attr.startswith("fermeture")
        }
        assert "fermetureSessionEnCours" in lus, (
            "optWindowClose() n'a pas de garde de réentrance propre : %r" % (lus,)
        )

    verifier(
        "Garde : optWindowClose() porte sa garde de réentrance",
        echecs,
        garde_presente,
    )

    # --- Le sort des modifications est demandé avant la démolition, et ------
    # jamais après : la couche et son tampon doivent encore être là pour que
    # la question ait un sens.
    def question_avant_demolition():
        alertes = []
        methodes, app, journal = monter(chemin_app, alertes, ("optWindowClose",))
        app.optWindow = OptWindowBouchon()
        app.actionMainMenu = ActionBouchon(False)

        methodes["optWindowClose"](app)

        assert "demanderSortEditions" in app.appels, (
            "le sort des modifications en attente n'est pas demandé : %r"
            % (app.appels,)
        )
        assert app.appels.index("demanderSortEditions") < app.appels.index(
            "closeAllSideWindows"
        ), "la question arrive après la démolition : %r" % (app.appels,)

    verifier(
        "Modifications en attente : question avant la démolition",
        echecs,
        question_avant_demolition,
    )

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print(
        "\nLa fermeture de la session résiste à la réentrance et au changement de projet."
    )
