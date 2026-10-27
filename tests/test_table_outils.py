# -*- coding: utf-8 -*-
"""Test de la table des gestes d'édition.

Couvre `src/editionOutils.py`, qui remplace la cascade de `if`/`elif` de 133
lignes de `mousePressEvent()`. Le défaut que ce test garde n'est pas une erreur
de calcul, c'est un trou : l'ancienne cascade ne traitait que les polygones et
les points, et un clic qui ne remplissait aucune de ses deux conditions
n'avait aucun effet et ne laissait aucune trace. Un clic sur une couche de
lignes était donc perdu en silence.

Le test vérifie donc d'abord l'exhaustivité : chacune des trente-six
combinaisons (quatre outils, trois types de géométrie, trois boutons) doit
aboutir à un traitement nommé, à un refus motivé, ou à un silence déclaré, et
jamais à rien du tout.

Quatre familles de cas :

1. Exhaustivité des trente-six combinaisons, et cohérence des clés de
   traitement avec les constantes du module.
2. Non-régression du découpage, seul outil offert avant cette tâche.
3. Les gardes d'état : clôture sans tracé en cours, bouton du milieu réservé au
   déplacement hors-synchronisation.
4. Les refus motivés et le type de géométrie non pris en charge.

Le module testé n'a aucune dépendance à QGIS ni à Qt : il s'importe
directement, sans l'extraction par analyse syntaxique qu'imposent les autres
tests du dossier.

Usage :
    python tests/test_table_outils.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Attendu recopié ici, et non importé du module testé : une table qui se
# vérifierait contre elle-même ne vérifierait rien. Clés : (outil, type,
# bouton). Valeurs : (clé hors tracé, clé pendant un tracé).
ATTENDU = {
    ("selectionner", "point", "gauche"): ("selectionner", "selectionner"),
    ("selectionner", "point", "droit"): ("viderSelection", "viderSelection"),
    ("selectionner", "ligne", "gauche"): ("selectionner", "selectionner"),
    ("selectionner", "ligne", "droit"): ("viderSelection", "viderSelection"),
    ("selectionner", "polygone", "gauche"): ("selectionner", "selectionner"),
    ("selectionner", "polygone", "droit"): ("viderSelection", "viderSelection"),
    ("ajouter", "point", "gauche"): ("ajouterPoint", "ajouterPoint"),
    ("ajouter", "ligne", "gauche"): ("poserSommet", "poserSommet"),
    ("ajouter", "ligne", "droit"): (None, "cloreLigne"),
    ("ajouter", "polygone", "gauche"): ("poserSommet", "poserSommet"),
    ("ajouter", "polygone", "droit"): (None, "clorePolygone"),
    ("combiner", "point", "gauche"): ("selectionner", "selectionner"),
    ("combiner", "point", "droit"): ("fusionnerSelection", "fusionnerSelection"),
    ("combiner", "ligne", "gauche"): ("selectionner", "selectionner"),
    ("combiner", "ligne", "droit"): ("fusionnerSelection", "fusionnerSelection"),
    ("combiner", "polygone", "gauche"): ("selectionner", "selectionner"),
    ("combiner", "polygone", "droit"): ("fusionnerSelection", "fusionnerSelection"),
    ("decouper", "polygone", "gauche"): ("poserSommet", "poserSommet"),
    ("decouper", "polygone", "droit"): (None, "cloreDecoupe"),
}

# Couples (outil, type) attendus comme refusés, avec un message à l'utilisateur.
REFUS_ATTENDUS = (
    ("decouper", "point"),
    ("decouper", "ligne"),
)

# Gestes attendus comme inertes et muets.
SILENCES_ATTENDUS = (("ajouter", "point", "droit"),)

OUTILS = ("selectionner", "ajouter", "combiner", "decouper")
TYPES = ("point", "ligne", "polygone")
BOUTONS = ("gauche", "droit", "milieu")


def casTableComplete(mod):
    """Les trente-six combinaisons aboutissent toutes à quelque chose."""
    echecs = []
    for outil in OUTILS:
        for typeGeo in TYPES:
            for bouton in BOUTONS:
                combinaison = (outil, typeGeo, bouton)
                for traceEnCours in (False, True):
                    cle, motif = mod.resoudreTraitement(
                        outil, typeGeo, bouton, traceEnCours
                    )
                    if cle is not None or motif:
                        continue
                    # Rien n'est rendu : le silence doit avoir été déclaré.
                    declare = (
                        bouton in mod.BOUTONS_SANS_EFFET
                        or combinaison in SILENCES_ATTENDUS
                        or (combinaison in ATTENDU and not traceEnCours)
                    )
                    if not declare:
                        echecs.append(
                            "%s, tracé en cours %s : aucun traitement, aucun "
                            "motif, aucun silence déclaré" % (combinaison, traceEnCours)
                        )
    return echecs, "36 combinaisons x 2 états de tracé"


def casTableConforme(mod):
    """Chaque combinaison rend le traitement attendu, dans les deux états."""
    echecs = []
    for combinaison, attendu in ATTENDU.items():
        outil, typeGeo, bouton = combinaison
        for indice, traceEnCours in enumerate((False, True)):
            cle, motif = mod.resoudreTraitement(outil, typeGeo, bouton, traceEnCours)
            if cle != attendu[indice]:
                echecs.append(
                    "%s, tracé en cours %s : %r au lieu de %r"
                    % (combinaison, traceEnCours, cle, attendu[indice])
                )
            if motif:
                echecs.append("%s : motif inattendu %r" % (combinaison, motif))
    return echecs, "%d entrées de table" % len(ATTENDU)


def casClesConnues(mod):
    """Toute clé rendue par la table est une constante déclarée du module."""
    echecs = []
    declarees = set(
        valeur
        for nom, valeur in vars(mod).items()
        if nom.startswith("TRAITEMENT_") and isinstance(valeur, str)
    )
    rendues = set()
    for gestes in mod.TABLE_TRAITEMENTS.values():
        rendues.update(cle for cle in gestes if cle is not None)

    for cle in sorted(rendues - declarees):
        echecs.append("clé %r rendue par la table, sans constante TRAITEMENT_" % cle)
    for cle in sorted(declarees - rendues):
        echecs.append(
            "constante TRAITEMENT_ %r qu'aucune entrée de table ne rend" % cle
        )
    return echecs, "%d clés" % len(rendues)


def casDecoupageInchange(mod):
    """Non-régression : le découpage garde le geste qu'il avait."""
    echecs = []
    cle, _ = mod.resoudreTraitement("decouper", "polygone", "gauche", False)
    if cle != "poserSommet":
        echecs.append("clic gauche sur polygone : %r au lieu de poserSommet" % cle)

    cle, _ = mod.resoudreTraitement("decouper", "polygone", "droit", True)
    if cle != "cloreDecoupe":
        echecs.append("clic droit pendant un tracé : %r au lieu de cloreDecoupe" % cle)

    cle, motif = mod.resoudreTraitement("decouper", "polygone", "droit", False)
    if cle is not None or motif:
        echecs.append(
            "clic droit sans tracé : %r, motif %r, au lieu d'un silence" % (cle, motif)
        )
    return echecs, "tracé, clôture, clic droit sans sommet"


def casClotureSansTrace(mod):
    """Un clic droit sans sommet posé ne clôt rien et ne dit rien."""
    echecs = []
    for typeGeo in ("ligne", "polygone"):
        cle, motif = mod.resoudreTraitement("ajouter", typeGeo, "droit", False)
        if cle is not None or motif:
            echecs.append(
                "ajouter %s, clic droit sans tracé : %r, motif %r"
                % (typeGeo, cle, motif)
            )
    return echecs, "ligne et polygone"


def casBoutonMilieu(mod):
    """Le bouton du milieu ne porte aucun geste d'édition, jamais."""
    echecs = []
    for outil in OUTILS:
        for typeGeo in TYPES:
            for traceEnCours in (False, True):
                cle, motif = mod.resoudreTraitement(
                    outil, typeGeo, "milieu", traceEnCours
                )
                if cle is not None:
                    echecs.append(
                        "%s/%s : le bouton du milieu rend %r" % (outil, typeGeo, cle)
                    )
                if motif:
                    echecs.append(
                        "%s/%s : le bouton du milieu porte un message"
                        % (outil, typeGeo)
                    )
    for combinaison in mod.TABLE_TRAITEMENTS:
        if combinaison[2] == "milieu":
            echecs.append("la table porte une entrée %s" % (combinaison,))
    return echecs, "12 combinaisons x 2 états de tracé"


def casRefusMotives(mod):
    """Les cases impossibles portent un message, au lieu d'un silence."""
    echecs = []
    for outil, typeGeo in REFUS_ATTENDUS:
        for bouton in ("gauche", "droit"):
            cle, motif = mod.resoudreTraitement(outil, typeGeo, bouton, False)
            if cle is not None:
                echecs.append(
                    "%s/%s/%s : traitement %r rendu" % (outil, typeGeo, bouton, cle)
                )
            if not motif:
                echecs.append(
                    "%s/%s/%s : refus sans message" % (outil, typeGeo, bouton)
                )
    return echecs, "%d couples refusés" % len(REFUS_ATTENDUS)


def casTypeInconnu(mod):
    """Une couche sans type exploitable est refusée avec un message."""
    echecs = []
    for typeGeo in (None, "", "raster", "NullGeometry"):
        cle, motif = mod.resoudreTraitement("ajouter", typeGeo, "gauche", False)
        if cle is not None:
            echecs.append("type %r : traitement %r rendu" % (typeGeo, cle))
        if not motif:
            echecs.append("type %r : refus sans message" % (typeGeo,))
    return echecs, "4 types non pris en charge"


def casAltitudeEcriture(mod):
    """Garde d'altitude : aucune cote indéterminée ne part dans une géométrie."""
    echecs = []

    autorise, z, motif = mod.altitudeEcriture(False, None)
    if not autorise or z is not None or motif:
        echecs.append("couche 2D sans altitude : %r" % ((autorise, z, motif),))

    autorise, z, motif = mod.altitudeEcriture(False, 142.5)
    if not autorise or z is not None:
        echecs.append("couche 2D avec altitude : la cote devrait être écartée")

    autorise, z, motif = mod.altitudeEcriture(True, None)
    if autorise or not motif:
        echecs.append("couche Z sans altitude : devrait être refusée avec message")

    for valeur in (float("inf"), float("-inf"), float("nan")):
        autorise, z, motif = mod.altitudeEcriture(True, valeur)
        if autorise or not motif:
            echecs.append("couche Z, altitude %r : devrait être refusée" % valeur)

    autorise, z, motif = mod.altitudeEcriture(True, "pas un nombre")
    if autorise or not motif:
        echecs.append("couche Z, altitude non numérique : devrait être refusée")

    # Une altitude négative est valide : le Saint-Laurent et ses battures.
    for valeur in (-12.5, 0.0, 311.25):
        autorise, z, motif = mod.altitudeEcriture(True, valeur)
        if not autorise or z != valeur or motif:
            echecs.append("couche Z, altitude %r : devrait être acceptée" % valeur)

    return echecs, "2D, absente, non finie, non numérique, valide"


def casDepartageEntite(mod):
    """Le départage d'une entité désignée est reproductible."""
    echecs = []

    if mod.choisirEntite([]) is not None:
        echecs.append("liste vide : devrait rendre None")

    # Deux polygones superposés et de même taille : le plus petit identifiant.
    pile = [
        {
            "fid": 9,
            "type": "polygone",
            "distance": 0.0,
            "contient": True,
            "mesure": 50.0,
        },
        {
            "fid": 3,
            "type": "polygone",
            "distance": 0.0,
            "contient": True,
            "mesure": 50.0,
        },
    ]
    for ordre in (pile, list(reversed(pile))):
        choisi = mod.choisirEntite(ordre)
        if choisi["fid"] != 3:
            echecs.append("égalité parfaite : fid %r au lieu de 3" % choisi["fid"])

    # Le plus petit polygone gagne sur le plus grand qui le contient.
    choisi = mod.choisirEntite(
        [
            {
                "fid": 1,
                "type": "polygone",
                "distance": 0.0,
                "contient": True,
                "mesure": 9e4,
            },
            {
                "fid": 2,
                "type": "polygone",
                "distance": 0.0,
                "contient": True,
                "mesure": 12.0,
            },
        ]
    )
    if choisi["fid"] != 2:
        echecs.append("polygones emboîtés : le plus petit devrait gagner")

    # L'entité qui contient le clic gagne sur celle qui en est proche.
    choisi = mod.choisirEntite(
        [
            {
                "fid": 1,
                "type": "polygone",
                "distance": 1.5,
                "contient": False,
                "mesure": 4.0,
            },
            {
                "fid": 2,
                "type": "polygone",
                "distance": 0.0,
                "contient": True,
                "mesure": 9e4,
            },
        ]
    )
    if choisi["fid"] != 2:
        echecs.append("clic dans un polygone : le contenant devrait gagner")

    # Hors de toute entité, le plus proche gagne.
    choisi = mod.choisirEntite(
        [
            {
                "fid": 1,
                "type": "ligne",
                "distance": 4.2,
                "contient": False,
                "mesure": 80.0,
            },
            {
                "fid": 2,
                "type": "ligne",
                "distance": 0.9,
                "contient": False,
                "mesure": 80.0,
            },
        ]
    )
    if choisi["fid"] != 2:
        echecs.append("clic hors de tout : le plus proche devrait gagner")

    # Priorité au type le plus ponctuel, à distance égale.
    choisi = mod.choisirEntite(
        [
            {
                "fid": 1,
                "type": "polygone",
                "distance": 0.0,
                "contient": True,
                "mesure": 10.0,
            },
            {
                "fid": 2,
                "type": "ligne",
                "distance": 0.0,
                "contient": False,
                "mesure": 10.0,
            },
            {
                "fid": 3,
                "type": "point",
                "distance": 0.0,
                "contient": False,
                "mesure": 0.0,
            },
        ]
    )
    if choisi["fid"] != 3:
        echecs.append("types mêlés : le point devrait gagner")

    return echecs, "vide, égalité, emboîtement, proximité, priorité"


CAS = (
    ("exhaustivité de la table", casTableComplete),
    ("conformité de la table", casTableConforme),
    ("clés de traitement déclarées", casClesConnues),
    ("non-régression du découpage", casDecoupageInchange),
    ("clôture sans sommet posé", casClotureSansTrace),
    ("bouton du milieu réservé", casBoutonMilieu),
    ("refus motivés", casRefusMotives),
    ("type de géométrie non pris en charge", casTypeInconnu),
    ("garde d'altitude", casAltitudeEcriture),
    ("départage de l'entité désignée", casDepartageEntite),
)


def executer(source):
    sys.path.insert(0, source)
    import editionOutils as mod

    print("Module testé : %s" % os.path.join(source, "editionOutils.py"))
    print()

    total = []
    for libelle, fonction in CAS:
        echecs, note = fonction(mod)
        total.extend(echecs)
        print("%-6s %-44s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) relevé(s)." % len(total))
        return 1
    print("La table des gestes d'édition est complète et reproductible.")
    return 0


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    sys.exit(executer(source))
