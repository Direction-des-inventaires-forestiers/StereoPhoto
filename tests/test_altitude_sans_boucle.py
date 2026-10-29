# -*- coding: utf-8 -*-
"""Garde contre le retour de la boucle de rétroaction sur l'altitude.

`mouseMoveEvent()` et `wheelActionEvent()` calculent les positions image de la
croix à partir de `cursorAltitude`, puis cadrent les vues dessus. Y mesurer
ensuite l'altitude par la parallaxe entre les deux vues referme une boucle :
la mesure ne peut que rendre la valeur qui vient d'être écrite, aux arrondis
près (pixels entiers du défilement des vues, miroir de la vue droite), et ces
arrondis s'accumulent dans le même sens. L'altitude dérivait ainsi de plusieurs
milliers de mètres au fil d'une session, sans jamais remonter.

Le défaut est de structure et non de valeur : il ne se voit pas sur un appel
isolé, mais sur l'enchaînement de milliers de mouvements. Le test est donc lui
aussi structurel : il lit l'arbre syntaxique de `stereoPhoto.py` et vérifie que
les chemins de navigation ne mesurent plus l'altitude :

1. aucun chemin de navigation ne mesure l'altitude, ni par un appel à
   l'ancienne méthode `updateUserAltitude()`, retirée du module, ni par un
   appel direct à `calculateZ()` ;
2. la mesure de parallaxe n'a lieu qu'au chargement d'une paire, dans
   `setInitialCursorAltitude()`, et nulle part ailleurs dans la classe ;
3. `afficherAltitude()`, qui ne fait que rafraîchir le panneau, existe et
   n'écrit pas `cursorAltitude` ;
4. `wheelActionEvent()` pose l'altitude qu'elle a calculée, au lieu de la lire
   sur les vues.

Usage :
    python tests/test_altitude_sans_boucle.py [chemin/vers/src]

Sans argument, le module testé est `src/stereoPhoto.py`, résolu depuis la
racine du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Méthodes appelées à chaque mouvement de souris, à chaque cran de roulette ou
# à chaque chargement de paire : aucune ne doit mesurer l'altitude.
METHODES_DE_NAVIGATION = (
    "mouseMoveEvent",
    "wheelActionEvent",
    "setStartingView",
    "recadrerVuesSurCanevas",
    "keyboardZoom",
)

# Ancienne méthode de mesure, retirée du module : son nom reste surveillé pour
# que la boucle ne soit pas réintroduite sous sa forme d'origine.
MESURE = "updateUserAltitude"
AFFICHAGE = "afficherAltitude"
PARALLAXE = "calculateZ"

# Seule méthode autorisée à mesurer la parallaxe : une fois par paire chargée.
MESURE_LEGITIME = "setInitialCursorAltitude"


def methodes(chemin, classe_visee):
    """Retourne les méthodes d'une classe, par nom, sous forme de nœuds."""
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

    return {n.name: n for n in classe.body if isinstance(n, (ast.FunctionDef,))}


def appels_de_methode(noeud):
    """Noms des méthodes appelées sur self dans le corps d'une méthode."""
    appels = []
    for interne in ast.walk(noeud):
        if not isinstance(interne, ast.Call):
            continue
        cible = interne.func
        if (
            isinstance(cible, ast.Attribute)
            and isinstance(cible.value, ast.Name)
            and cible.value.id == "self"
        ):
            appels.append(cible.attr)
    return appels


def appelle_parallaxe(noeud):
    """Vrai si le corps d'une méthode appelle calculateZ(), sur quoi que ce soit.

    Le porteur n'est pas vérifié : `self.dualManager.calculateZ()` aujourd'hui,
    un gestionnaire rangé autrement demain : c'est l'appel à la mesure qui est
    surveillé, pas le chemin qui y mène.
    """
    for interne in ast.walk(noeud):
        if (
            isinstance(interne, ast.Call)
            and isinstance(interne.func, ast.Attribute)
            and interne.func.attr == PARALLAXE
        ):
            return True
    return False


def attributs_ecrits(noeud):
    """Noms des attributs de self assignés dans le corps d'une méthode."""
    ecrits = []
    for interne in ast.walk(noeud):
        cibles = []
        if isinstance(interne, ast.Assign):
            cibles = interne.targets
        elif isinstance(interne, (ast.AugAssign, ast.AnnAssign)):
            cibles = [interne.target]

        for cible in cibles:
            if (
                isinstance(cible, ast.Attribute)
                and isinstance(cible.value, ast.Name)
                and cible.value.id == "self"
            ):
                ecrits.append(cible.attr)
    return ecrits


def cas_navigation_sans_mesure(corps):
    """Aucun chemin de navigation ne mesure l'altitude."""
    echecs = []
    for nom in METHODES_DE_NAVIGATION:
        libelle = "%s() ne mesure pas l'altitude" % nom
        try:
            assert nom in corps, "méthode absente du module"
            appels = appels_de_methode(corps[nom])
            assert MESURE not in appels, (
                "appel à %s() : la boucle de rétroaction est refermée" % MESURE
            )
            assert not appelle_parallaxe(corps[nom]), (
                "appel à %s() : la boucle est refermée sans passer par %s()"
                % (PARALLAXE, MESURE)
            )
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-52s %s" % (libelle, erreur))
        else:
            print("OK     %-52s" % libelle)

    return echecs


def cas_mesure_unique(corps):
    """La parallaxe n'est mesurée qu'au chargement d'une paire."""
    echecs = []

    libelle = "la mesure de parallaxe n'a qu'un seul lieu"
    try:
        mesurent = sorted(nom for nom in corps if appelle_parallaxe(corps[nom]))
        assert mesurent == [MESURE_LEGITIME], (
            "méthode(s) mesurant la parallaxe : %s" % (", ".join(mesurent) or "aucune")
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    libelle = "la méthode de mesure d'origine est bien retirée"
    try:
        assert MESURE not in corps, (
            "%s() est de retour dans la classe : la boucle peut se refermer" % MESURE
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


def cas_affichage(corps):
    """L'affichage de l'altitude ne la recalcule pas."""
    echecs = []

    libelle = "%s() existe et n'écrit pas l'altitude" % AFFICHAGE
    try:
        assert AFFICHAGE in corps, "méthode absente du module"
        ecrits = attributs_ecrits(corps[AFFICHAGE])
        assert "cursorAltitude" not in ecrits, (
            "l'affichage écrit cursorAltitude : ce n'est plus un affichage"
        )
        appels = appels_de_methode(corps[AFFICHAGE])
        assert MESURE not in appels, "l'affichage appelle %s()" % MESURE
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    libelle = "les chemins de navigation rafraîchissent le panneau"
    try:
        sans_affichage = [
            nom
            for nom in ("mouseMoveEvent", "wheelActionEvent", "setStartingView")
            if nom in corps and AFFICHAGE not in appels_de_methode(corps[nom])
        ]
        assert not sans_affichage, "sans appel à %s() : %s" % (
            AFFICHAGE,
            ", ".join(sans_affichage),
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


def cas_roulette(corps):
    """La roulette pose l'altitude qu'elle a calculée."""
    echecs = []
    libelle = "wheelActionEvent() pose l'altitude du cran"
    try:
        assert "wheelActionEvent" in corps, "méthode absente du module"
        noeud = corps["wheelActionEvent"]
        assert "cursorAltitude" in attributs_ecrits(noeud), (
            "l'altitude n'est pas assignée : le cran de parallaxe est perdu"
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


def executer(dossier_source):
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    corps = methodes(chemin_app, "stereoPhoto")

    echecs = cas_navigation_sans_mesure(corps)
    echecs += cas_mesure_unique(corps)
    echecs += cas_affichage(corps)
    echecs += cas_roulette(corps)
    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Module testé : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nAucun chemin de navigation ne referme la boucle sur l'altitude.")
