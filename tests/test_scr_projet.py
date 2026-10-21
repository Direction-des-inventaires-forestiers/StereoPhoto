# -*- coding: utf-8 -*-
"""Test de la garde sur le SCR du projet (décision D-18).

Tout le calcul de navigation suppose des coordonnées projetées en mètres : les
fichiers PAR en portent, `setExtent2Canvas()` accorde l'échelle du canevas sur
celle des vues en mètres par pixel, et `coordToPixel()` reçoit la coordonnée du
canevas telle quelle. Un projet dans un SCR géographique fait donc traiter des
degrés comme des mètres — le déplacement image tombe à environ 10⁻⁵ pixel par
pixel de souris, et la navigation paraît figée, sans qu'aucune erreur ne soit
levée. C'est l'état d'un projet neuf (WGS 84), et celui qu'on obtient dès que
les rasters ne déclarent aucun SCR.

`verifierScrProjet()` est extraite du fichier source par analyse syntaxique,
puis exécutée avec des bouchons : aucune dépendance à QGIS ni à Qt n'est
nécessaire.

Usage :
    python tests/test_scr_projet.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import logging
import os
import sys

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


def lire_constante(chemin, nom):
    """Retourne la valeur littérale d'une constante de module."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id == nom:
                    return ast.literal_eval(noeud.value)
    raise AssertionError("constante %s absente de %s" % (nom, chemin))


class ScrBouchon:
    """Remplace QgsCoordinateReferenceSystem : validité, nature, identifiant."""

    def __init__(self, authid, valide=True, geographique=False):
        self._authid = authid
        self._valide = valide
        self._geographique = geographique

    def isValid(self):
        return self._valide

    def isGeographic(self):
        return self._geographique

    def authid(self):
        return self._authid


class ProjetBouchon:
    """QgsProject.instance() : relève le SCR lu et les SCR posés."""

    def __init__(self, scr):
        self._scr = scr
        self.poses = []

    def crs(self):
        return self._scr

    def setCrs(self, scr):
        self.poses.append(scr)
        self._scr = scr


class FabriqueScrBouchon:
    """QgsCoordinateReferenceSystem : seule fromEpsgId() est utilisée."""

    def __init__(self, scr_rendu):
        self.scr_rendu = scr_rendu
        self.demandes = []

    def fromEpsgId(self, code):
        self.demandes.append(code)
        return self.scr_rendu


class JournalBouchon:
    def __init__(self):
        self.messages = []

    def _noter(self, niveau):
        def ecrire(*args):
            self.messages.append((niveau, args[0] if args else ""))

        return ecrire

    def __getattr__(self, nom):
        if nom in ("debug", "info", "warning", "error"):
            return self._noter(nom)
        raise AttributeError(nom)


class ApplicationBouchon:
    def __init__(self, journal):
        self.journal = journal


def preparer(chemin_app, chemin_config, scr_projet, scr_donnees):
    """Monte la méthode et ses bouchons, et rend le nécessaire aux assertions."""
    code = lire_constante(chemin_config, "DONNEES_SCR_EPSG")
    projet = ProjetBouchon(scr_projet)
    fabrique = FabriqueScrBouchon(scr_donnees)
    avertissements = []

    def avertir_utilisateur(message, niveau=logging.WARNING, duree_secondes=8):
        avertissements.append((niveau, message))

    espace = {
        "QgsProject": type("QgsProjectBouchon", (), {"instance": lambda: projet}),
        "QgsCoordinateReferenceSystem": fabrique,
        "DONNEES_SCR_EPSG": code,
        "avertir_utilisateur": avertir_utilisateur,
        "logging": logging,
    }
    methode = extraire_methode(chemin_app, "stereoPhoto", "verifierScrProjet", espace)
    journal = JournalBouchon()
    return methode, ApplicationBouchon(journal), projet, fabrique, avertissements, code


def executer(dossier_source):
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    chemin_config = os.path.join(dossier_source, "config.py")
    echecs = []

    projete = ScrBouchon("EPSG:2948")
    geographique = ScrBouchon("EPSG:4326", geographique=True)
    aucun = ScrBouchon("", valide=False)
    donnees = ScrBouchon("EPSG:2948")
    donnees_absent = ScrBouchon("", valide=False)

    # Un SCR projeté est laissé tel quel : le secteur peut être dans une autre
    # zone MTM que celle de la configuration.
    libelle = "SCR projeté : laissé intact, aucune alerte"
    methode, app, projet, fabrique, alertes, _ = preparer(
        chemin_app, chemin_config, projete, donnees
    )
    try:
        assert methode(app) is True, "la navigation est refusée à tort"
        assert projet.poses == [], "le SCR a été remplacé : %r" % (projet.poses,)
        assert alertes == [], "alerte émise à tort : %r" % (alertes,)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Projet neuf en WGS 84 : c'est le cas qui faisait paraître la navigation
    # figée. Le SCR est posé depuis la configuration et l'utilisateur averti.
    libelle = "SCR géographique : remplacé, utilisateur averti"
    methode, app, projet, fabrique, alertes, code = preparer(
        chemin_app, chemin_config, geographique, donnees
    )
    try:
        assert methode(app) is True, "la navigation est refusée alors qu'elle est"
        assert projet.poses == [donnees], "SCR posé : %r" % (projet.poses,)
        assert fabrique.demandes == [code], "code demandé : %r" % (fabrique.demandes,)
        assert len(alertes) == 1, "%d alerte(s)" % len(alertes)
        assert "EPSG:4326" in alertes[0][1], "l'ancien SCR n'est pas nommé"
        assert "EPSG:2948" in alertes[0][1], "le nouveau SCR n'est pas nommé"
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Aucun SCR valide : même traitement, sans nom d'ancien SCR à afficher.
    libelle = "SCR absent : remplacé sans masquer le cas"
    methode, app, projet, fabrique, alertes, _ = preparer(
        chemin_app, chemin_config, aucun, donnees
    )
    try:
        assert methode(app) is True, "la navigation est refusée à tort"
        assert projet.poses == [donnees], "SCR posé : %r" % (projet.poses,)
        assert len(alertes) == 1, "%d alerte(s)" % len(alertes)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Installation de QGIS sans la définition du SCR des données : la
    # navigation est refusée plutôt que lancée sur un référentiel faux.
    libelle = "SCR des données introuvable : navigation refusée"
    methode, app, projet, fabrique, alertes, _ = preparer(
        chemin_app, chemin_config, geographique, donnees_absent
    )
    try:
        assert methode(app) is False, "la navigation est permise à tort"
        assert projet.poses == [], "un SCR invalide a été posé : %r" % (projet.poses,)
        assert len(alertes) == 1, "%d alerte(s)" % len(alertes)
        assert alertes[0][0] >= logging.ERROR, "niveau %r" % (alertes[0][0],)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nLe SCR du projet est vérifié avant toute navigation.")
