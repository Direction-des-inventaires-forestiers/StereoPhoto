# -*- coding: utf-8 -*-
"""Gardes de forme du chemin d'écriture vectorielle.

Ce test ne vérifie aucun calcul : il vérifie la forme du code source, et c'est
voulu. Les deux règles que ces tests gardent ne se vérifient pas autrement
sans QGIS, et elles se perdraient à la première réécriture distraite.

**L'écriture passe par le tampon d'édition de la couche.** Le code d'origine
écrivait par `dataProvider().addFeature()`, hors du tampon, donc hors
d'atteinte de l'annulation, et refermait la session d'édition après chaque
geste par un `commitChanges()` immédiat, ce qui vidait la pile.
Les gardes ci-dessous interdisent le retour de ces deux chemins : aucune
écriture par le fournisseur de données dans `src/`, et un seul `commitChanges()`
dans tout le dépôt, celui de la fonction d'enregistrement. L'abandon d'un
tampon entier n'existe pas dans l'extension : il n'aurait aucun geste pour
l'atteindre, et QGIS l'offre déjà.

**Le répartiteur par table.** La cascade de `if`/`elif` de 133 lignes de
`mousePressEvent()` ne traitait que deux des trois types de géométrie, et un
clic qui ne remplissait aucune de ses conditions était perdu sans trace. Les
gardes vérifient que la cascade est partie et non doublée, et que la table de
`editionOutils` et celle de `stereoPhoto` se correspondent exactement : une clé
de traitement sans méthode donnerait un `KeyError` au clic, sur un geste
d'édition, c'est-à-dire au pire moment.

Chaque commande d'édition est enfin vérifiée appariée : une fonction qui ouvre
une commande doit savoir la fermer et la détruire, sans quoi un échec laisse la
couche avec une commande ouverte et l'annulation désaccordée.

Usage :
    python tests/test_edition_vecteur.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Méthodes d'écriture qui, appelées sur un fournisseur de données, contournent
# le tampon d'édition de la couche.
ECRITURES_FOURNISSEUR = (
    "addFeature",
    "addFeatures",
    "deleteFeatures",
    "deleteFeature",
    "changeGeometry",
    "changeGeometryValues",
    "changeAttributeValues",
)

# Appels qui ne doivent exister qu'en un seul endroit, et lequel.
APPELS_RESERVES = {
    "commitChanges": ("editionVecteur.py", "enregistrer"),
}

# Modules engendrés par pyuic5 ou pyrcc5, écartés comme par le contrôle de style.
FICHIERS_ECARTES = ("resources.py", "ui_enhancement.py", "ui_getVectorLayer.py")


def fichiers_source(dossier):
    for nom in sorted(os.listdir(dossier)):
        if not nom.endswith(".py") or nom in FICHIERS_ECARTES:
            continue
        yield nom, os.path.join(dossier, nom)


def arbre_de(chemin):
    return ast.parse(io.open(chemin, encoding="utf-8").read())


def fonction_englobante(arbre, noeud_vise):
    """Nom de la fonction qui contient un nœud, ou None."""
    for fonction in ast.walk(arbre):
        if not isinstance(fonction, ast.FunctionDef):
            continue
        for interne in ast.walk(fonction):
            if interne is noeud_vise:
                return fonction.name
    return None


def appels_nommes(arbre, nom):
    """Tous les nœuds d'appel d'une méthode de ce nom, quelle que soit la cible."""
    return [
        n
        for n in ast.walk(arbre)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr == nom
    ]


def casAucuneEcritureFournisseur(dossier):
    """Aucune écriture par dataProvider() : tout passe par le tampon."""
    echecs = []
    for nom, chemin in fichiers_source(dossier):
        arbre = arbre_de(chemin)
        for appel in ast.walk(arbre):
            if not isinstance(appel, ast.Call):
                continue
            if not isinstance(appel.func, ast.Attribute):
                continue
            if appel.func.attr not in ECRITURES_FOURNISSEUR:
                continue
            cible = appel.func.value
            # dataProvider().addFeature(...) : la cible est elle-même un appel
            # de dataProvider.
            if (
                isinstance(cible, ast.Call)
                and isinstance(cible.func, ast.Attribute)
                and cible.func.attr == "dataProvider"
            ):
                echecs.append(
                    "%s, %s() : écriture par le fournisseur de données, ligne %d"
                    % (nom, appel.func.attr, appel.lineno)
                )
    return echecs, "%d module(s) examiné(s)" % len(list(fichiers_source(dossier)))


def casAppelsReserves(dossier):
    """commitChanges() et rollBack() n'existent qu'à leur place."""
    echecs = []
    for appel, (fichierAttendu, fonctionAttendue) in APPELS_RESERVES.items():
        trouves = []
        for nom, chemin in fichiers_source(dossier):
            arbre = arbre_de(chemin)
            for noeud in appels_nommes(arbre, appel):
                trouves.append((nom, fonction_englobante(arbre, noeud), noeud.lineno))

        if not trouves:
            echecs.append("%s() n'existe plus nulle part" % appel)
            continue

        for nom, fonction, ligne in trouves:
            if nom != fichierAttendu or fonction != fonctionAttendue:
                echecs.append(
                    "%s() appelé dans %s, %s() ligne %d ; attendu dans %s, %s()"
                    % (appel, nom, fonction, ligne, fichierAttendu, fonctionAttendue)
                )

        if len(trouves) > 1:
            echecs.append(
                "%s() appelé %d fois ; un seul point d'écriture est attendu"
                % (appel, len(trouves))
            )
    return echecs, ", ".join(sorted(APPELS_RESERVES))


def casCommandesAppairees(dossier):
    """Une fonction qui ouvre une commande d'édition sait la fermer et la défaire."""
    echecs = []
    chemin = os.path.join(dossier, "editionVecteur.py")
    arbre = arbre_de(chemin)

    ouvertures = 0
    for fonction in ast.walk(arbre):
        if not isinstance(fonction, ast.FunctionDef):
            continue
        appels = {
            n.func.attr
            for n in ast.walk(fonction)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        if "beginEditCommand" not in appels:
            continue
        ouvertures += 1
        for attendu in ("endEditCommand", "destroyEditCommand"):
            if attendu not in appels:
                echecs.append(
                    "%s() ouvre une commande d'édition sans %s()"
                    % (fonction.name, attendu)
                )

    if not ouvertures:
        echecs.append("aucune commande d'édition : l'annulation ne groupe plus rien")
    return echecs, "%d fonction(s) ouvrant une commande" % ouvertures


def casEditionOuverteEnDernier(dossier):
    """Un refus ne doit pas laisser la couche en édition.

    Tout ce qu'une écriture peut refuser d'avance se calcule sans écrire : le
    compte des entités sélectionnées, leur relecture, la combinaison des
    géométries, la conformité au type de la couche. `ouvrirEdition()` doit donc
    venir après ces contrôles, et non avant. Relevé à l'usage : une fusion
    refusée faisait entrer la couche en édition, avec un tampon vide, et y
    restait.
    """
    echecs = []
    arbre = arbre_de(os.path.join(dossier, "editionVecteur.py"))

    verifies = 0
    for fonction in ast.walk(arbre):
        if not isinstance(fonction, ast.FunctionDef):
            continue

        ouvertures = [
            n.lineno
            for n in ast.walk(fonction)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "ouvrirEdition"
        ]
        if not ouvertures:
            continue

        controles = [
            n.lineno
            for n in ast.walk(fonction)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "conformerGeometrie"
        ]
        if not controles:
            continue

        verifies += 1
        if min(ouvertures) < max(controles):
            echecs.append(
                "%s() ouvre l'édition ligne %d, avant le contrôle de la "
                "géométrie ligne %d : un refus laisserait la couche en édition"
                % (fonction.name, min(ouvertures), max(controles))
            )

    if not verifies:
        echecs.append(
            "aucune fonction ne contrôle la géométrie avant d'ouvrir l'édition"
        )
    return echecs, "%d fonction(s) d'écriture" % verifies


def casCascadeRetiree(dossier):
    """mousePressEvent() ne compare plus ni type de géométrie ni bouton."""
    echecs = []
    arbre = arbre_de(os.path.join(dossier, "stereoPhoto.py"))
    methode = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "mousePressEvent"
        ),
        None,
    )
    if methode is None:
        return ["mousePressEvent() introuvable"], "méthode absente"

    interdits = {
        "PolygonGeometry",
        "PointGeometry",
        "LineGeometry",
        "LeftButton",
        "RightButton",
        "MiddleButton",
    }
    for noeud in ast.walk(methode):
        if isinstance(noeud, ast.Attribute) and noeud.attr in interdits:
            echecs.append(
                "mousePressEvent() compare encore %s, ligne %d"
                % (noeud.attr, noeud.lineno)
            )

    lignes = methode.end_lineno - methode.lineno + 1
    if lignes > 30:
        echecs.append(
            "mousePressEvent() fait %d lignes : la cascade semble revenue" % lignes
        )
    return echecs, "%d lignes" % lignes


def casTablesCorrespondantes(dossier):
    """La table de editionOutils et celle de stereoPhoto se correspondent."""
    echecs = []

    sys.path.insert(0, dossier)
    import editionOutils as mod

    declarees = {
        nom: valeur
        for nom, valeur in vars(mod).items()
        if nom.startswith("TRAITEMENT_") and isinstance(valeur, str)
    }

    arbre = arbre_de(os.path.join(dossier, "stereoPhoto.py"))
    table = None
    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Assign):
            continue
        for cible in noeud.targets:
            if isinstance(cible, ast.Attribute) and cible.attr == "tableTraitements":
                table = noeud.value
    if not isinstance(table, ast.Dict):
        return (
            ["la table des traitements de stereoPhoto n'est pas un littéral"],
            "table introuvable",
        )

    classe = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.ClassDef) and n.name == "stereoPhoto"
        ),
        None,
    )
    methodesClasse = {n.name for n in classe.body if isinstance(n, ast.FunctionDef)}

    posees = set()
    for cle, valeur in zip(table.keys, table.values):
        if not isinstance(cle, ast.Attribute) or not isinstance(valeur, ast.Attribute):
            echecs.append("entrée de table qui n'est pas (constante, méthode liée)")
            continue
        posees.add(cle.attr)

        if cle.attr not in declarees:
            echecs.append("clé %s absente de editionOutils" % cle.attr)
            continue

        attendu = declarees[cle.attr]
        if valeur.attr != attendu:
            echecs.append(
                "%s vaut %r mais est raccordée à self.%s : la méthode doit "
                "porter le nom de la clé" % (cle.attr, attendu, valeur.attr)
            )
        if valeur.attr not in methodesClasse:
            echecs.append(
                "self.%s n'est pas une méthode de stereoPhoto : KeyError au clic"
                % valeur.attr
            )

    for nom in sorted(set(declarees) - posees):
        echecs.append(
            "%s déclarée dans editionOutils, absente de la table de stereoPhoto" % nom
        )

    return echecs, "%d clés de traitement" % len(declarees)


def casCommandesDefaitesSurException(dossier):
    """Aucun chemin d'erreur ne laisse une commande d'édition ouverte.

    `casCommandesAppairees()` ci-dessus vérifie que les deux noms figurent dans
    la fonction, ce qu'une fonction satisfait sans que son `except` les
    atteigne. Relevé à la revue du Sprint A : les trois fonctions d'écriture
    journalisaient et sortaient de leur `except` sans défaire la commande
    ouverte dans le `try`.

    Ce que ça coûte : `QUndoStack::canUndo()` rend False tant qu'une macro est
    en cours. Une commande laissée ouverte grise donc le bouton Annuler et
    éteint `Ctrl+Z` pour le reste de la session, alors que l'enregistrement
    continue de fonctionner, et rien ne le dit à l'utilisateur.

    La garde porte sur chaque gestionnaire d'exception des fonctions qui
    ouvrent une commande. Elle n'exige pas que l'appel soit inconditionnel : le
    défaire sous un drapeau est la bonne façon, l'exception pouvant survenir
    avant l'ouverture.
    """
    echecs = []
    arbre = arbre_de(os.path.join(dossier, "editionVecteur.py"))

    gestionnaires = 0
    for fonction in ast.walk(arbre):
        if not isinstance(fonction, ast.FunctionDef):
            continue
        if not appels_nommes(fonction, "beginEditCommand"):
            continue

        for gestionnaire in ast.walk(fonction):
            if not isinstance(gestionnaire, ast.ExceptHandler):
                continue
            gestionnaires += 1
            if not appels_nommes(gestionnaire, "destroyEditCommand"):
                echecs.append(
                    "%s() : le gestionnaire d'exception de la ligne %d sort "
                    "sans destroyEditCommand()" % (fonction.name, gestionnaire.lineno)
                )

    if not gestionnaires:
        echecs.append(
            "aucun gestionnaire d'exception sur un chemin d'écriture : garde sans objet"
        )
    return echecs, "%d gestionnaire(s) d'exception" % gestionnaires


CAS = (
    ("aucune écriture par le fournisseur", casAucuneEcritureFournisseur),
    ("un seul point d'enregistrement", casAppelsReserves),
    ("commandes d'édition appairées", casCommandesAppairees),
    ("commandes défaites sur exception", casCommandesDefaitesSurException),
    ("édition ouverte après les contrôles", casEditionOuverteEnDernier),
    ("cascade de mousePressEvent retirée", casCascadeRetiree),
    ("tables de traitement correspondantes", casTablesCorrespondantes),
)


def executer(source):
    print("Modules testés : %s" % source)
    print()

    total = []
    for libelle, fonction in CAS:
        echecs, note = fonction(source)
        total.extend(echecs)
        print("%-6s %-44s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) relevé(s)." % len(total))
        return 1
    print("Le chemin d'écriture et le répartiteur gardent la forme décidée.")
    return 0


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    sys.exit(executer(source))
