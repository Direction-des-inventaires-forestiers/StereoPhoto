# -*- coding: utf-8 -*-
"""Écriture dans les couches vectorielles.

Toutes les écritures de l'extension passent par ici, et toutes passent par
l'API de la couche et son tampon d'édition.

Ce qui a changé. Les primitives d'origine, dans `drawFunction.py`, écrivaient
par `dataProvider().addFeature()` entre un `startEditing()` et un
`commitChanges()` immédiat. Écrire par le fournisseur de données va
directement au fichier : l'ajout échappait au tampon, donc
l'annulation était sans effet. Et le `commitChanges()` immédiat des trois
autres refermait la session après chaque geste, ce qui vidait la pile
d'annulation. Multiplier les outils d'édition sur ce chemin aurait multiplié
les gestes irréversibles.

Ici, la session d'édition s'ouvre au premier geste d'écriture et reste ouverte.
Chaque geste est une commande d'édition nommée, donc une frappe d'annulation,
et l'enregistrement est un geste explicite de l'utilisateur.

Trois conséquences de forme, que le banc de tests garde :
aucun `dataProvider()` d'écriture dans le dépôt, aucun `commitChanges()`
ailleurs que dans `enregistrer()`, et aucune sortie de fonction qui laisse une
commande d'édition ouverte. Cette dernière compte autant que les deux autres :
`QUndoStack::canUndo()` rend False tant qu'une macro est en cours, de sorte
qu'une commande oubliée sur un chemin d'erreur désactive l'annulation de la
couche pour le reste de la session, sans que rien ne le signale. Le drapeau
`commandeOuverte` des trois fonctions d'écriture sert à cela, et à ne pas
défaire une commande qui n'a pas été ouverte : l'exception peut survenir avant
le `beginEditCommand()`, et `destroyEditCommand()` défait alors le geste
précédent.

Le module ne porte que ce que les outils d'édition appellent. La suppression
d'entités et l'abandon d'un tampon entier n'en font pas partie : les écrire
sans qu'aucun geste ne les atteigne aurait ajouté du code inatteignable.
QGIS offre les deux, dans l'état atteint après la touche Échap.
"""

from qgis.core import (
    Qgis,
    QgsLineString,
    QgsVectorDataProvider,
    QgsVectorLayerEditUtils,
    QgsVectorLayerUtils,
    QgsWkbTypes,
)
from qgis.utils import iface

import logging

from .journal import obtenir_journal, avertir_utilisateur

# Journal du module; le préfixe « _ » le réserve à l'usage interne
_journal = obtenir_journal(__name__)


def ouvrirEdition(couche):
    """Ouvre la session d'édition de la couche, si elle ne l'est pas déjà.

    L'ouverture est paresseuse, au premier geste d'écriture, et non à la
    désignation de la couche : le panneau d'options désigne une couche éditable
    par défaut, souvent sans intention de l'utilisateur.

    Retourne False et avertit si la couche n'accepte pas l'écriture. Le code
    d'origine ne contrôlait aucun de ces retours : sur une couche en lecture
    seule, le geste était perdu sans un mot.
    """
    if couche is None:
        return False

    if couche.isEditable():
        return True

    if not couche.isValid():
        avertir_utilisateur(
            "La couche « %s » n'est pas valide : aucune modification possible."
            % couche.name()
        )
        return False

    capacites = couche.dataProvider().capabilities()
    manquantes = [
        libelle
        for libelle, drapeau in (
            ("ajout d'entités", QgsVectorDataProvider.AddFeatures),
            ("modification de géométries", QgsVectorDataProvider.ChangeGeometries),
            ("suppression d'entités", QgsVectorDataProvider.DeleteFeatures),
        )
        if not capacites & drapeau
    ]
    if manquantes:
        avertir_utilisateur(
            "La couche « %s » n'accepte pas l'écriture (%s) : elle est en "
            "lecture seule, ou son fichier est verrouillé."
            % (couche.name(), ", ".join(manquantes))
        )
        _journal.warning(
            "Couche %s en lecture seule ; capacités manquantes : %s",
            couche.name(),
            ", ".join(manquantes),
        )
        return False

    if not couche.startEditing():
        avertir_utilisateur(
            "La session d'édition de la couche « %s » n'a pas pu s'ouvrir."
            % couche.name()
        )
        _journal.warning("startEditing() refusé sur la couche %s", couche.name())
        return False

    _journal.info("Session d'édition ouverte sur la couche %s", couche.name())
    return True


def conformerGeometrie(couche, geometrie):
    """Accorde une géométrie au type de la couche, ou dit pourquoi c'est non.

    Retourne `(géométrie ou None, motif)`. Quatre écarts possibles entre ce que
    le geste produit et ce que la couche porte, dont aucun n'était vérifié :

    - couche multipartie et géométrie simple : la géométrie est convertie, sans
      quoi certains fournisseurs refusent l'entité à l'enregistrement, donc
      longtemps après le geste ;
    - couche simple et géométrie multipartie : refus immédiat. C'est le cas de
      la fusion de deux entités disjointes dans un shapefile de polygones ;
    - couche sans Z et géométrie avec Z : la cote est retirée ;
    - couche avec Z et géométrie sans Z : signalé au journal, la garde
      d'altitude devant l'avoir écarté en amont.
    """
    if geometrie is None or geometrie.isNull() or geometrie.isEmpty():
        return None, "La géométrie obtenue est vide."

    typeCouche = couche.wkbType()
    coucheMultiple = QgsWkbTypes.isMultiType(typeCouche)
    geoMultiple = QgsWkbTypes.isMultiType(geometrie.wkbType())

    if coucheMultiple and not geoMultiple:
        if not geometrie.convertToMultiType():
            return None, "La géométrie n'a pas pu être convertie en multipartie."

    if geoMultiple and not coucheMultiple:
        return None, (
            "La couche « %s » ne porte qu'une partie par entité : le résultat, "
            "qui en compte plusieurs, ne peut pas y être écrit. Fusionner des "
            "entités jointives, ou choisir une couche multipartie." % couche.name()
        )

    coucheAUnZ = QgsWkbTypes.hasZ(typeCouche)
    geoAUnZ = QgsWkbTypes.hasZ(geometrie.wkbType())

    if geoAUnZ and not coucheAUnZ:
        geometrie.get().dropZValue()
    elif coucheAUnZ and not geoAUnZ:
        _journal.warning(
            "Géométrie sans altitude écrite dans la couche %s, qui porte un Z",
            couche.name(),
        )

    return geometrie, ""


def ajouterEntite(couche, geometrie, ouvrirFormulaire=False):
    """Ajoute une entité par le tampon d'édition de la couche.

    `QgsVectorLayerUtils.createFeature()` honore les valeurs par défaut et les
    contraintes des champs, ce que l'ancien `addPolygon()` ne faisait pas : il
    écrivait une entité sans aucun champ.

    Avec `ouvrirFormulaire`, le formulaire d'attributs de QGIS s'ouvre après
    l'ajout, et son refus annule l'ajout par la pile d'annulation. Le code
    d'origine écrivait l'entité par le fournisseur puis la supprimait par le
    fournisseur en cas de refus : deux écritures directes, et une entité qui
    avait réellement existé dans le fichier.

    Retourne l'entité ajoutée, ou None.
    """
    geometrie, motif = conformerGeometrie(couche, geometrie)
    if geometrie is None:
        avertir_utilisateur(motif)
        return None

    if not ouvrirEdition(couche):
        return None

    commandeOuverte = False
    try:
        entite = QgsVectorLayerUtils.createFeature(couche, geometrie)
        couche.beginEditCommand("StereoPhoto : ajout d'une entité")
        commandeOuverte = True
        if not couche.addFeature(entite):
            couche.destroyEditCommand()
            commandeOuverte = False
            avertir_utilisateur(
                "L'entité n'a pas pu être ajoutée à la couche « %s »." % couche.name()
            )
            _journal.warning("addFeature() refusé sur la couche %s", couche.name())
            return None
        couche.endEditCommand()
        commandeOuverte = False
    except Exception:
        if commandeOuverte:
            couche.destroyEditCommand()
        _journal.exception(
            "Échec de l'ajout d'une entité à la couche %s", couche.name()
        )
        avertir_utilisateur(
            "L'ajout d'une entité a échoué. Voir le journal de l'extension."
        )
        return None

    if ouvrirFormulaire and not iface.openFeatureForm(couche, entite):
        # Formulaire refusé : la commande d'édition entière est défaite, donc
        # l'entité disparaît du tampon sans jamais avoir atteint le fichier.
        annulerDernier(couche)
        _journal.info("Ajout annulé : formulaire d'attributs refusé")
        return None

    couche.triggerRepaint()
    return entite


def fusionnerSelection(couche):
    """Fusionne les entités sélectionnées en une seule.

    Même sémantique que « Fusionner les entités sélectionnées » de QGIS, et
    même geste pour les trois types de géométrie : les géométries sont
    combinées, les attributs de la première entité sont conservés, les autres
    entités sont supprimées.

    « La première » est celle dont l'identifiant est le plus petit, et non la
    première cliquée : la fusion doit donner le même résultat quel que soit
    l'ordre des clics.

    Tout tient dans une seule commande d'édition : une frappe d'annulation
    défait la fusion entière, et non la suppression de la dernière entité
    seule. L'ancien `mergePolygon()` ne combinait que deux géométries, puis
    refermait la session d'édition.

    La session d'édition n'est ouverte qu'une fois la géométrie fusionnée
    obtenue et acceptée. Tout ce qui précède se calcule sans écrire, et un refus
    ne doit rien laisser derrière lui : ouvrir la session d'abord faisait entrer
    la couche en édition même quand la fusion était refusée.
    """
    identifiants = sorted(couche.selectedFeatureIds())
    if len(identifiants) < 2:
        avertir_utilisateur(
            "Sélectionner au moins deux entités avant de les combiner : %d "
            "entité(s) sélectionnée(s)." % len(identifiants)
        )
        return False

    commandeOuverte = False
    try:
        entites = {f.id(): f for f in couche.getFeatures(identifiants)}
        manquants = [fid for fid in identifiants if fid not in entites]
        if manquants:
            avertir_utilisateur(
                "Entité(s) introuvable(s) dans la couche : la sélection a "
                "changé depuis le dernier clic."
            )
            _journal.warning("Entités sélectionnées introuvables : %s", manquants)
            return False

        geometrie = entites[identifiants[0]].geometry()
        for fid in identifiants[1:]:
            geometrie = geometrie.combine(entites[fid].geometry())
            if geometrie is None or geometrie.isNull():
                avertir_utilisateur(
                    "La combinaison des géométries a échoué : aucune "
                    "modification n'a été faite."
                )
                _journal.warning("combine() a rendu une géométrie nulle")
                return False

        geometrie, motif = conformerGeometrie(couche, geometrie)
        if geometrie is None:
            avertir_utilisateur(motif)
            return False

        if not ouvrirEdition(couche):
            return False

        couche.beginEditCommand(
            "StereoPhoto : fusion de %d entités" % len(identifiants)
        )
        commandeOuverte = True
        if not couche.changeGeometry(identifiants[0], geometrie):
            couche.destroyEditCommand()
            commandeOuverte = False
            avertir_utilisateur("La géométrie fusionnée n'a pas pu être écrite.")
            _journal.warning("changeGeometry() refusé sur %s", couche.name())
            return False
        if not couche.deleteFeatures(identifiants[1:]):
            couche.destroyEditCommand()
            commandeOuverte = False
            avertir_utilisateur(
                "Les entités absorbées n'ont pas pu être supprimées : la "
                "fusion est abandonnée."
            )
            _journal.warning("deleteFeatures() refusé sur %s", couche.name())
            return False
        couche.endEditCommand()
        commandeOuverte = False
    except Exception:
        if commandeOuverte:
            couche.destroyEditCommand()
        _journal.exception("Échec de la fusion sur la couche %s", couche.name())
        avertir_utilisateur("La fusion a échoué. Voir le journal de l'extension.")
        return False

    couche.selectByIds([identifiants[0]])
    couche.triggerRepaint()
    _journal.info(
        "Fusion de %d entités de la couche %s dans l'entité %s",
        len(identifiants),
        couche.name(),
        identifiants[0],
    )
    avertir_utilisateur(
        "%d entités combinées en une seule." % len(identifiants), niveau=20
    )
    return True


def decouper(couche, sommets):
    """Découpe les entités traversées par la ligne de coupe.

    `sommets` est une liste de `QgsPoint`, portant l'altitude du curseur quand
    la couche a un Z. Ils sont réunis en `QgsLineString` et passés à la
    variante de `splitFeatures()` qui accepte une courbe : celle qui prend une
    liste de `QgsPointXY`, seule employée par l'ancien `cutPolygon()`, est
    dépréciée depuis QGIS 3.12 et sera retirée en QGIS 4, et elle perd
    l'altitude de la ligne de coupe. Mesuré sur QGIS 3.44 : la variante qui
    accepte une liste de `QgsPoint` n'est pas atteignable depuis Python, PyQt
    résolvant toute liste vers la variante `QgsPointXY`.

    Le comportement, lui, ne change pas : la coupe s'applique à toutes les
    entités traversées, et la sélection est vidée au préalable, comme avant.
    """
    if len(sommets) < 2:
        avertir_utilisateur("Une ligne de coupe demande au moins deux sommets.")
        return False

    if not ouvrirEdition(couche):
        return False

    commandeOuverte = False
    try:
        couche.removeSelection()
        couche.beginEditCommand("StereoPhoto : découpage")
        commandeOuverte = True
        utils = QgsVectorLayerEditUtils(couche)
        resultat = utils.splitFeatures(QgsLineString(sommets), False, False)
        # La variante courbe rend un couple (résultat, points de topologie).
        if isinstance(resultat, tuple):
            resultat = resultat[0]

        if resultat != Qgis.GeometryOperationResult.Success:
            couche.destroyEditCommand()
            commandeOuverte = False
            # Le code d'origine ne laissait aucune trace de cet échec : ni
            # enregistrement, ni retour en arrière, ni message.
            avertir_utilisateur(
                "Le découpage n'a rien coupé (code %s). Vérifier que la ligne "
                "traverse bien une entité de part en part." % resultat
            )
            _journal.warning("splitFeatures() a rendu %s", resultat)
            return False

        couche.endEditCommand()
        commandeOuverte = False
    except Exception:
        if commandeOuverte:
            couche.destroyEditCommand()
        _journal.exception("Échec du découpage sur la couche %s", couche.name())
        avertir_utilisateur("Le découpage a échoué. Voir le journal de l'extension.")
        return False

    couche.triggerRepaint()
    _journal.info("Découpage appliqué sur la couche %s", couche.name())
    return True


def modificationsEnAttente(couche):
    """Dit si la couche porte des modifications non enregistrées, et combien."""
    try:
        if couche is None or not couche.isEditable() or not couche.isModified():
            return False, 0

        tampon = couche.editBuffer()
        if tampon is None:
            return True, 0

        nombre = (
            len(tampon.addedFeatures())
            + len(tampon.changedGeometries())
            + len(tampon.deletedFeatureIds())
            + len(tampon.changedAttributeValues())
        )
        return True, nombre
    except RuntimeError:
        # Couche déjà détruite par QGIS : cas du changement de projet, où cette
        # fonction est interrogée pendant la démolition.
        _journal.debug("Couche détruite : modifications en attente indéterminables")
        return False, 0


def enregistrer(couche):
    """Enregistre les modifications en attente. Seul `commitChanges()` du dépôt.

    La session d'édition est réouverte aussitôt : l'enregistrement est un point
    de sauvegarde, pas la fin du travail. Le photo-interprète continue de
    tracer sur la même couche sans avoir à rouvrir quoi que ce soit.
    """
    enAttente, nombre = modificationsEnAttente(couche)
    if not enAttente:
        avertir_utilisateur("Aucune modification à enregistrer.", niveau=logging.INFO)
        return False

    if not couche.commitChanges():
        erreurs = couche.commitErrors()
        _journal.error(
            "Échec de l'enregistrement de la couche %s : %s",
            couche.name(),
            " | ".join(erreurs),
        )
        avertir_utilisateur(
            "L'enregistrement de la couche « %s » a échoué : %s"
            % (couche.name(), erreurs[0] if erreurs else "cause inconnue")
        )
        return False

    _journal.info(
        "%d modification(s) enregistrée(s) sur la couche %s", nombre, couche.name()
    )
    avertir_utilisateur(
        "%d modification(s) enregistrée(s) sur « %s »." % (nombre, couche.name()),
        niveau=logging.INFO,
    )
    couche.startEditing()
    couche.triggerRepaint()
    return True


def annulerDernier(couche):
    """Défait le dernier geste d'édition, par la pile d'annulation de la couche.

    L'intercepteur clavier de la navigation avale tout `KeyPress` et tout
    `ShortcutOverride` : aucun raccourci natif de QGIS ne répond pendant la
    navigation synchronisée, y compris celui de l'annulation. Elle passe donc
    par cette fonction, appelée par le bouton de la barre d'outils et par
    `keyboardHandler()`, qui résout la touche par la table des raccourcis.
    """
    if couche is None or not couche.isEditable():
        return False

    pile = couche.undoStack()
    if not pile.canUndo():
        avertir_utilisateur("Aucun geste d'édition à annuler.", niveau=logging.INFO)
        return False

    libelle = pile.undoText()
    pile.undo()
    couche.triggerRepaint()
    _journal.info("Geste d'édition annulé : %s", libelle)
    return True


def entitesDansRectangle(couche, rectangle):
    """Entités de la couche dans un rectangle, tampon d'édition compris.

    `getFeatures()` traverse le tampon : une entité tout juste tracée et non
    encore enregistrée est donc sélectionnable, ce qui est la condition pour
    pouvoir la fusionner.
    """
    try:
        return list(couche.getFeatures(rectangle))
    except Exception:
        _journal.exception(
            "Lecture des entités impossible sur la couche %s", couche.name()
        )
        return []
