# -*- coding: utf-8 -*-
"""Résolution des gestes d'édition vectorielle.

Trois décisions sont réunies ici, et aucune n'a besoin de QGIS ni de Qt :

1. **Quel traitement un clic déclenche**, à partir de l'outil actif, du type de
   géométrie de la couche éditable, du bouton de la souris et de la présence
   d'un tracé en cours. C'était auparavant une cascade de `if`/`elif` de
   133 lignes dans `mousePressEvent()`, qui ne traitait que deux des trois
   types et laissait un clic sans effet et sans trace quand aucune condition
   n'était remplie.
2. **Quelle entité un clic désigne**, parmi les candidats trouvés dans la
   tolérance. Les distances sont mesurées par QGIS, mais le départage est une
   décision, et c'est elle qui doit être reproductible : deux clics au même
   endroit doivent désigner la même entité.
3. **Quelle altitude part dans la géométrie**, ou pourquoi l'écriture est
   refusée.

Les clés sont des chaînes, jamais `QgsWkbTypes.PolygonGeometry` ni
`Qt.LeftButton` : la traduction se fait à la frontière, dans `stereoPhoto`.
C'est ce qui rend le module vérifiable sans installer QGIS, suivant la
convention du dossier `tests/` et le précédent de `orientationModele.py`.
"""

import math

# Les quatre outils d'édition, dans l'ordre de la barre d'outils.
OUTIL_SELECTIONNER = "selectionner"
OUTIL_AJOUTER = "ajouter"
OUTIL_COMBINER = "combiner"
OUTIL_DECOUPER = "decouper"

OUTILS = (OUTIL_SELECTIONNER, OUTIL_AJOUTER, OUTIL_COMBINER, OUTIL_DECOUPER)

# Les outils qui travaillent par tracé point par point : eux seuls accumulent
# des sommets, et eux seuls donnent une portée aux radios Dessiner et Découper.
OUTILS_DE_TRACE = (OUTIL_AJOUTER, OUTIL_DECOUPER)

# Les trois types de géométrie des couches éditables.
TYPE_POINT = "point"
TYPE_LIGNE = "ligne"
TYPE_POLYGONE = "polygone"

TYPES = (TYPE_POINT, TYPE_LIGNE, TYPE_POLYGONE)

# Priorité de désignation : sur une pile de géométries, le plus ponctuel gagne.
PRIORITE_TYPE = {TYPE_POINT: 0, TYPE_LIGNE: 1, TYPE_POLYGONE: 2}

BOUTON_GAUCHE = "gauche"
BOUTON_DROIT = "droit"
BOUTON_MILIEU = "milieu"

BOUTONS = (BOUTON_GAUCHE, BOUTON_DROIT, BOUTON_MILIEU)

# Le bouton du milieu ne porte aucun geste d'édition : il est réservé au
# déplacement « main » de l'état hors-synchronisation (horsSyncQgsMapTool).
# Son silence est voulu, ce n'est pas un oubli de la table.
BOUTONS_SANS_EFFET = {
    BOUTON_MILIEU: "réservé au déplacement en hors-synchronisation",
}

# Clés de traitement. Chacune a sa méthode dans stereoPhoto, nommée de même.
TRAITEMENT_SELECTIONNER = "selectionner"
TRAITEMENT_VIDER_SELECTION = "viderSelection"
TRAITEMENT_AJOUTER_POINT = "ajouterPoint"
TRAITEMENT_POSER_SOMMET = "poserSommet"
TRAITEMENT_CLORE_LIGNE = "cloreLigne"
TRAITEMENT_CLORE_POLYGONE = "clorePolygone"
TRAITEMENT_CLORE_DECOUPE = "cloreDecoupe"
TRAITEMENT_FUSIONNER = "fusionnerSelection"

# (outil, type, bouton) vers (clé hors tracé, clé pendant un tracé).
#
# Deux colonnes parce que le même bouton ne fait pas la même chose selon qu'un
# tracé est commencé ou non : le clic droit clôt un tracé en cours et ne fait
# rien quand aucun sommet n'est posé. C'est la garde `len(listDrawCoord) > 0`
# de l'ancienne cascade, devenue une entrée de table.
TABLE_TRAITEMENTS = {
    # Sélectionner : le clic gauche désigne, le clic droit vide la sélection.
    (OUTIL_SELECTIONNER, TYPE_POINT, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_SELECTIONNER, TYPE_POINT, BOUTON_DROIT): (
        TRAITEMENT_VIDER_SELECTION,
        TRAITEMENT_VIDER_SELECTION,
    ),
    (OUTIL_SELECTIONNER, TYPE_LIGNE, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_SELECTIONNER, TYPE_LIGNE, BOUTON_DROIT): (
        TRAITEMENT_VIDER_SELECTION,
        TRAITEMENT_VIDER_SELECTION,
    ),
    (OUTIL_SELECTIONNER, TYPE_POLYGONE, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_SELECTIONNER, TYPE_POLYGONE, BOUTON_DROIT): (
        TRAITEMENT_VIDER_SELECTION,
        TRAITEMENT_VIDER_SELECTION,
    ),
    # Ajouter : un point se pose d'un seul clic, une ligne et un polygone se
    # tracent sommet par sommet et se closent au clic droit.
    (OUTIL_AJOUTER, TYPE_POINT, BOUTON_GAUCHE): (
        TRAITEMENT_AJOUTER_POINT,
        TRAITEMENT_AJOUTER_POINT,
    ),
    (OUTIL_AJOUTER, TYPE_LIGNE, BOUTON_GAUCHE): (
        TRAITEMENT_POSER_SOMMET,
        TRAITEMENT_POSER_SOMMET,
    ),
    (OUTIL_AJOUTER, TYPE_LIGNE, BOUTON_DROIT): (None, TRAITEMENT_CLORE_LIGNE),
    (OUTIL_AJOUTER, TYPE_POLYGONE, BOUTON_GAUCHE): (
        TRAITEMENT_POSER_SOMMET,
        TRAITEMENT_POSER_SOMMET,
    ),
    (OUTIL_AJOUTER, TYPE_POLYGONE, BOUTON_DROIT): (None, TRAITEMENT_CLORE_POLYGONE),
    # Combiner : le clic gauche désigne les entités, le clic droit fusionne.
    # Même geste pour les trois types, comme la fusion des entités
    # sélectionnées de QGIS.
    (OUTIL_COMBINER, TYPE_POINT, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_COMBINER, TYPE_POINT, BOUTON_DROIT): (
        TRAITEMENT_FUSIONNER,
        TRAITEMENT_FUSIONNER,
    ),
    (OUTIL_COMBINER, TYPE_LIGNE, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_COMBINER, TYPE_LIGNE, BOUTON_DROIT): (
        TRAITEMENT_FUSIONNER,
        TRAITEMENT_FUSIONNER,
    ),
    (OUTIL_COMBINER, TYPE_POLYGONE, BOUTON_GAUCHE): (
        TRAITEMENT_SELECTIONNER,
        TRAITEMENT_SELECTIONNER,
    ),
    (OUTIL_COMBINER, TYPE_POLYGONE, BOUTON_DROIT): (
        TRAITEMENT_FUSIONNER,
        TRAITEMENT_FUSIONNER,
    ),
    # Découper : la ligne de coupe se trace comme un polygone et se clôt au
    # clic droit. Comportement d'origine, conservé sans changement.
    (OUTIL_DECOUPER, TYPE_POLYGONE, BOUTON_GAUCHE): (
        TRAITEMENT_POSER_SOMMET,
        TRAITEMENT_POSER_SOMMET,
    ),
    (OUTIL_DECOUPER, TYPE_POLYGONE, BOUTON_DROIT): (None, TRAITEMENT_CLORE_DECOUPE),
}

# Couples (outil, type) qui n'ont aucun sens, avec le message à porter au
# bandeau. L'ancienne cascade ne disait rien dans ces cas : un clic sur une
# couche de lignes n'avait aucun effet et ne laissait aucune trace.
MOTIFS_REFUS = {
    (OUTIL_DECOUPER, TYPE_POINT): (
        "L'outil Découper ne s'applique pas à une couche de points."
    ),
    (OUTIL_DECOUPER, TYPE_LIGNE): ("Le découpage de lignes n'est pas offert."),
}

# Gestes volontairement inertes, qui ne méritent pas de message : un clic droit
# sous l'outil Ajouter sur une couche de points n'a rien à clore.
GESTES_SANS_EFFET = frozenset(
    [
        (OUTIL_AJOUTER, TYPE_POINT, BOUTON_DROIT),
    ]
)

MOTIF_TYPE_INCONNU = (
    "La couche choisie n'est ni ponctuelle, ni linéaire, ni polygonale : "
    "elle ne peut pas être éditée par StereoPhoto."
)

# La touche du suivi du MNT est configurable : le message ne peut donc pas la
# nommer lui-même, sans quoi il mentirait dès qu'elle est changée. L'appelant la
# demande à la table des raccourcis et la passe formatée ; ce module ne connaît
# ni la table ni les noms de touches, comme il ne connaît pas les boutons de la
# souris.
GABARIT_ALTITUDE_INDETERMINEE = (
    "Altitude indéterminée : la couche porte une altitude (Z) et aucune "
    "altitude n'est disponible. Régler la parallaxe à la roulette, ou activer "
    "le suivi du MNT%s, avant d'ajouter une géométrie."
)

MOTIF_ALTITUDE_NON_FINIE = (
    "Altitude hors domaine : la mesure de parallaxe n'a pas abouti à une "
    "valeur utilisable. Régler la parallaxe à la roulette avant d'ajouter une "
    "géométrie."
)


def motifAltitudeIndeterminee(annonceSuiviMnt=""):
    """Phrase de refus, qui nomme la touche du suivi du MNT si elle en a une.

    `annonceSuiviMnt` est un fragment déjà rendu — « touche M », « Ctrl+M » —
    que l'appelant tire de la table des raccourcis. Vide, la phrase ne parle
    pas du clavier : c'est le cas quand l'action n'a aucune touche affectée, et
    annoncer un raccourci inexistant serait pire que de se taire.
    """
    return GABARIT_ALTITUDE_INDETERMINEE % (
        " (%s)" % annonceSuiviMnt if annonceSuiviMnt else ""
    )


def resoudreTraitement(outil, typeGeometrie, bouton, traceEnCours):
    """Nomme le traitement d'un clic, ou dit pourquoi il n'y en a pas.

    Retourne un couple `(clé de traitement ou None, motif)`. Un motif vide
    signifie un silence voulu : le geste est inerte et l'utilisateur n'a pas à
    être averti. Un motif non vide est destiné au bandeau de QGIS.
    """
    if bouton in BOUTONS_SANS_EFFET:
        return None, ""

    if typeGeometrie not in TYPES:
        return None, MOTIF_TYPE_INCONNU

    motif = MOTIFS_REFUS.get((outil, typeGeometrie))
    if motif:
        return None, motif

    gestes = TABLE_TRAITEMENTS.get((outil, typeGeometrie, bouton))
    if gestes is None:
        return None, ""

    return gestes[1 if traceEnCours else 0], ""


def choisirEntite(candidats):
    """Désigne une entité parmi les candidats, ou None si la liste est vide.

    Chaque candidat est un dictionnaire portant `fid`, `type`, `distance`,
    `contient` et `mesure` (aire d'un polygone, longueur d'une ligne, 0 pour un
    point). Les mesures viennent de QGIS ; seul le départage est ici.

    Ordre des critères : le type le plus ponctuel, puis l'entité qui contient
    le clic avant celle qui en est seulement proche, puis la plus courte
    distance, puis la plus petite mesure, et enfin le plus petit identifiant.
    Ce dernier critère n'est pas un ornement : sans lui, deux entités
    superposées et de même taille se désigneraient au hasard de l'ordre de
    lecture de la couche, et un clic répété au même endroit ne donnerait pas
    deux fois le même résultat.
    """
    if not candidats:
        return None
    return min(candidats, key=_rang)


def _rang(candidat):
    return (
        PRIORITE_TYPE.get(candidat.get("type"), len(PRIORITE_TYPE)),
        0 if candidat.get("contient") else 1,
        candidat.get("distance", 0.0),
        candidat.get("mesure", 0.0),
        candidat.get("fid"),
    )


def altitudeEcriture(coucheAUnZ, altitude, annonceSuiviMnt=""):
    """Dit quelle altitude écrire, ou pourquoi l'écriture est refusée.

    Retourne `(autorise, altitude, motif)`. L'altitude écrite est celle que
    la session porte, celle que le photo-interprète règle à la
    roulette ou laisse suivre le MNT, et non une lecture du MNT prise au
    passage. C'est aussi celle que la croix affiche, donc celle qu'il croit
    mesurer.

    Une couche sans Z n'a besoin d'aucune altitude : le MNT n'est alors pas
    exigé pour éditer. Une couche avec Z et une altitude indéterminée ou hors
    domaine ferme l'écriture, plutôt que de laisser passer un None ou un infini
    dans la géométrie.
    """
    if not coucheAUnZ:
        return True, None, ""

    if altitude is None:
        return False, None, motifAltitudeIndeterminee(annonceSuiviMnt)

    try:
        valeur = float(altitude)
    except (TypeError, ValueError):
        return False, None, motifAltitudeIndeterminee(annonceSuiviMnt)

    if not math.isfinite(valeur):
        return False, None, MOTIF_ALTITUDE_NON_FINIE

    return True, valeur, ""
