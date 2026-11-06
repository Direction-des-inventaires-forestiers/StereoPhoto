# -*- coding: utf-8 -*-
"""Table des raccourcis clavier, et résolution de ce qu'un fichier en dit.

Les raccourcis étaient sept littéraux dans une cascade de `if`/`elif` de
`keyboardHandler()`. Pendant la navigation, l'intercepteur clavier avale tout
`KeyPress` et tout `ShortcutOverride` : aucun raccourci natif de QGIS ne répond,
et ces touches sont le seul accès clavier aux outils. Les figer dans le code
fermait donc l'accès clavier à toute personne dont les habitudes ou le clavier
diffèrent de ceux du poste d'origine.

Trois décisions sont réunies ici, et aucune n'a besoin de QGIS ni de Qt :

1. **Quelle touche commande quelle action**, et réciproquement.
2. **Comment un nom de touche s'écrit**, pour qu'un fichier de paramètres édité
   à la main soit lu de la même façon quelles que soient la casse, les accents
   et les espaces.
3. **Ce qu'on fait d'un fichier mal écrit** : une session ne doit jamais échouer
   à s'ouvrir à cause d'une touche mal orthographiée, et l'utilisateur doit
   pouvoir comprendre pourquoi sa touche ne répond pas.

Les clés sont des chaînes, jamais `Qt.Key_M` ni `Qt.ControlModifier` : la
traduction se fait à la frontière, dans `stereoPhoto`, qui porte seule la
correspondance vers les constantes de Qt. C'est ce qui rend le module vérifiable
sans installer QGIS, suivant la convention du dossier `tests/` et le précédent
d'`editionOutils.py`.

Ce module est aussi le seul endroit du dépôt où un nom de touche a sa place en
chaîne littérale : partout ailleurs, un texte montré à l'utilisateur compose sa
mention de touche en la demandant à la table, sans quoi il mentirait dès la
première personnalisation.
"""

import json
import unicodedata

# Clé de la section dans le fichier de paramètres de l'extension.
CLE_SECTION = "raccourcis"

# Les onze actions accessibles au clavier.
ACTION_BASCULE_FENETRE = "bascule_fenetre"
ACTION_ZOOM = "zoom"
ACTION_OUTIL_SELECTIONNER = "outil_selectionner"
ACTION_OUTIL_AJOUTER = "outil_ajouter"
ACTION_OUTIL_COMBINER = "outil_combiner"
ACTION_OUTIL_DECOUPER = "outil_decouper"
ACTION_BASCULE_TRACE = "bascule_trace"
ACTION_SUIVI_MNT = "suivi_mnt"
ACTION_CURSEUR_LIBRE = "curseur_libre"
ACTION_ANNULER = "annuler"
ACTION_ENREGISTRER = "enregistrer"

# L'ordre est celui du départage d'un conflit : la première action de ce tuple
# qui réclame une touche la garde. Il est donc déclaré, et non laissé à l'ordre
# de parcours d'un dictionnaire : deux lectures du même fichier doivent donner
# la même table. Le zoom vient tôt, son groupe de huit étant celui qui se
# replierait le plus mal.
ACTIONS = (
    ACTION_BASCULE_FENETRE,
    ACTION_ZOOM,
    ACTION_OUTIL_SELECTIONNER,
    ACTION_OUTIL_AJOUTER,
    ACTION_OUTIL_COMBINER,
    ACTION_OUTIL_DECOUPER,
    ACTION_BASCULE_TRACE,
    ACTION_SUIVI_MNT,
    ACTION_CURSEUR_LIBRE,
    ACTION_ANNULER,
    ACTION_ENREGISTRER,
)

# Clé d'outil d'editionOutils vers l'action qui l'active. Les clés sont
# recopiées et non importées : ce module reste sans dépendance, et le banc de
# tests croise les deux listes plutôt que de les laisser se vérifier l'une par
# l'autre.
ACTIONS_OUTIL = {
    "selectionner": ACTION_OUTIL_SELECTIONNER,
    "ajouter": ACTION_OUTIL_AJOUTER,
    "combiner": ACTION_OUTIL_COMBINER,
    "decouper": ACTION_OUTIL_DECOUPER,
}

# Argument passé à la méthode de l'action. Les quatre actions d'outil portent la
# clé de leur outil ; les autres n'en ont pas, et le zoom reçoit son niveau au
# moment de la résolution.
ARGUMENTS = {action: cle for cle, action in ACTIONS_OUTIL.items()}

# Nombre de niveaux de zoom au clavier, donc de touches dans le groupe. Doit
# valoir len(NAVIGATION_ZOOM_NIVEAUX) de config.py ; le banc le vérifie.
NIVEAUX_ZOOM = 8

# Modificateurs retenus, dans l'ordre canonique d'écriture.
#
# Maj est volontairement absente, et refusée à la lecture. Trois raisons : sur
# plusieurs dispositions de clavier, dont le français canadien, Maj et un
# chiffre ne rendent pas la touche du chiffre mais celle du symbole, si bien
# qu'un tel raccourci configuré ne répondrait jamais ; QGIS occupe déjà
# beaucoup de combinaisons Maj ; et ce modificateur accompagne la sélection
# additive à la souris, où il a déjà un sens.
MODIFICATEUR_CTRL = "Ctrl"
MODIFICATEUR_ALT = "Alt"
MODIFICATEURS = (MODIFICATEUR_CTRL, MODIFICATEUR_ALT)

SEPARATEUR = "+"

# Vocabulaire des touches affectables, dans l'ordre. L'ordre sert à reconnaître
# une plage contiguë, pour qu'un groupe de huit touches s'annonce comme une
# plage plutôt qu'en énumération.
#
# Des touches que QGIS emploie par ailleurs y figurent (F1 pour l'aide, Tab pour
# le parcours des champs, Suppr pour la suppression d'entités) : pendant la
# navigation l'intercepteur les avale de toute façon, et un vocabulaire amputé
# n'aurait pas de frontière défendable. En hors-synchronisation, en revanche,
# elles gardent leur sens dans QGIS, l'intercepteur n'y étant pas posé.
TOUCHES_CONNUES = (
    "Échap",
    "F1",
    "F2",
    "F3",
    "F4",
    "F5",
    "F6",
    "F7",
    "F8",
    "F9",
    "F10",
    "F11",
    "F12",
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
    "X",
    "Y",
    "Z",
    "Gauche",
    "Droite",
    "Haut",
    "Bas",
    "PgHaut",
    "PgBas",
    "Début",
    "Fin",
    "Espace",
    "Tab",
    "Retour",
    "Retour arrière",
    "Suppr",
    "Inser",
    "+",
    "-",
)

# Touches par défaut. Ce sont les valeurs livrées dans le fichier de paramètres,
# et le repli de toute entrée que le fichier ne donne pas ou donne mal.
#
# Les quatre outils d'édition se désignent directement, dans l'ordre de la barre
# d'outils. La bascule entre Ajouter et Découper, qui portait la touche 1 quand
# ces deux outils étaient les seuls, n'a plus de touche : les désigner
# directement fait tout ce que la bascule faisait, et davantage. L'entrée reste
# déclarée pour qu'une touche puisse lui être rendue.
TOUCHES_PAR_DEFAUT = {
    ACTION_BASCULE_FENETRE: "Échap",
    ACTION_ZOOM: ("F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"),
    ACTION_OUTIL_SELECTIONNER: "1",
    ACTION_OUTIL_AJOUTER: "2",
    ACTION_OUTIL_COMBINER: "3",
    ACTION_OUTIL_DECOUPER: "4",
    ACTION_BASCULE_TRACE: "",
    ACTION_SUIVI_MNT: "M",
    ACTION_CURSEUR_LIBRE: "C",
    ACTION_ANNULER: "Ctrl+Z",
    ACTION_ENREGISTRER: "Ctrl+S",
}

# Orthographes acceptées à la lecture, vers la forme canonique. Les clés sont
# déjà repliées par _replier() : sans accent, sans casse, sans espace.
SYNONYMES = {
    "esc": "Échap",
    "escape": "Échap",
    "echappement": "Échap",
    "left": "Gauche",
    "right": "Droite",
    "up": "Haut",
    "down": "Bas",
    "pageup": "PgHaut",
    "pgup": "PgHaut",
    "pagehaut": "PgHaut",
    "pagedown": "PgBas",
    "pgdn": "PgBas",
    "pagebas": "PgBas",
    "home": "Début",
    "end": "Fin",
    "space": "Espace",
    "enter": "Retour",
    "return": "Retour",
    "entree": "Retour",
    "backspace": "Retour arrière",
    "del": "Suppr",
    "delete": "Suppr",
    "suppression": "Suppr",
    "insert": "Inser",
    "plus": "+",
    "moins": "-",
    "minus": "-",
}

# Orthographes acceptées des modificateurs, repliées de même.
SYNONYMES_MODIFICATEURS = {
    "ctrl": MODIFICATEUR_CTRL,
    "control": MODIFICATEUR_CTRL,
    "controle": MODIFICATEUR_CTRL,
    "alt": MODIFICATEUR_ALT,
}

# Modificateurs reconnus mais refusés. Les nommer vaut mieux que de les traiter
# comme une faute de frappe : qui écrit « Maj+A » a besoin de savoir que ce
# n'est pas une erreur d'écriture mais un refus.
MODIFICATEURS_REFUSES = frozenset(["maj", "shift", "meta", "super", "cmd", "win"])

_TOUCHES_VALIDES = frozenset(TOUCHES_CONNUES)


def _replier(texte):
    """Forme de comparaison d'un fragment : sans accent, sans casse, sans espace."""
    sans_accent = "".join(
        c
        for c in unicodedata.normalize("NFD", texte)
        if unicodedata.category(c) != "Mn"
    )
    return "".join(sans_accent.split()).lower()


# Forme repliée de chaque touche connue vers sa forme canonique.
_CANONIQUES = {_replier(nom): nom for nom in TOUCHES_CONNUES}


def normaliser(texte):
    """Nom de touche canonique, ou None si le texte n'en désigne aucun.

    Accepte « ctrl+z », « Ctrl+Z », « CTRL + Z », « Échap », « echap », « esc »
    et « f5 » : la comparaison ignore la casse, les accents et les espaces
    autour des éléments. Les modificateurs reconnus sont Ctrl et Alt, rendus
    dans cet ordre quel que soit celui de l'écriture.

    Rend None, et ne lève jamais, sur une valeur vide, non textuelle, un
    modificateur répété, un modificateur sans touche, un modificateur refusé, ou
    un nom absent de TOUCHES_CONNUES.
    """
    if not isinstance(texte, str):
        return None

    fragments = texte.split(SEPARATEUR)
    # Le séparateur est aussi un nom de touche : « + » et « Ctrl++ » se
    # découpent en laissant un fragment vide à la fin, qui désigne la touche.
    if len(fragments) > 1 and texte.strip().endswith(SEPARATEUR):
        fragments = fragments[:-1]
        fragments[-1] = fragments[-1] + SEPARATEUR

    modificateurs = []
    nom = None
    for rang, fragment in enumerate(fragments):
        replie = _replier(fragment)
        if not replie:
            return None

        if rang < len(fragments) - 1:
            if replie in MODIFICATEURS_REFUSES:
                return None
            modificateur = SYNONYMES_MODIFICATEURS.get(replie)
            if modificateur is None or modificateur in modificateurs:
                return None
            modificateurs.append(modificateur)
            continue

        nom = SYNONYMES.get(replie) or _CANONIQUES.get(replie)

    if nom not in _TOUCHES_VALIDES:
        return None

    ordonnes = [m for m in MODIFICATEURS if m in modificateurs]
    return SEPARATEUR.join(ordonnes + [nom])


def raisonDuRefus(texte):
    """Dit pourquoi une écriture a été refusée, en une phrase pour le journal.

    `normaliser()` rend None sans distinguer les cas, ce qui suffit pour
    décider mais pas pour expliquer. Un modificateur non pris en charge n'est
    pas une faute de frappe : qui écrit « Maj+A » a fait un choix, et doit lire
    que ce choix est refusé plutôt que de croire s'être trompé de touche.

    Rend la chaîne vide quand l'écriture est valide.
    """
    if not isinstance(texte, str):
        return "une touche s'écrit en texte"

    if normaliser(texte) is not None:
        return ""

    fragments = texte.split(SEPARATEUR)
    for fragment in fragments[:-1]:
        replie = _replier(fragment)
        if replie in MODIFICATEURS_REFUSES:
            return "le modificateur %s n'est pas pris en charge" % fragment.strip()

    return "touche inconnue"


def annonce(nom):
    """Fragment de phrase qui nomme une touche, pour un texte montré.

    « M » donne « touche M », « Ctrl+Z » donne « Ctrl+Z », et une action sans
    touche donne la chaîne vide : l'appelant compose alors une phrase qui ne
    parle pas du clavier, plutôt que d'annoncer un raccourci inexistant.
    """
    if not nom:
        return ""
    if SEPARATEUR in nom:
        return nom
    return "touche %s" % nom


def annonceGroupe(noms):
    """Fragment de phrase pour un groupe de touches.

    Rend une plage quand les noms se suivent dans TOUCHES_CONNUES,
    l'énumération sinon, et la chaîne vide pour un groupe vide.
    """
    noms = [nom for nom in (noms or ()) if nom]
    if not noms:
        return ""
    if len(noms) == 1:
        return noms[0]

    if not all(nom in _TOUCHES_VALIDES for nom in noms):
        return ", ".join(noms)

    rangs = [TOUCHES_CONNUES.index(nom) for nom in noms]
    if rangs == list(range(rangs[0], rangs[0] + len(rangs))):
        return "%s à %s" % (noms[0], noms[-1])
    return ", ".join(noms)


def sectionParDefaut():
    """Section « raccourcis » prête à écrire dans le fichier de paramètres.

    Dict neuf, et sans tuple : TOUCHES_PAR_DEFAUT ne doit jamais se retrouver
    aliasée dans le dictionnaire de paramètres que l'extension réécrit à chaque
    fermeture de session.
    """
    section = {}
    for action in ACTIONS:
        valeur = TOUCHES_PAR_DEFAUT[action]
        section[action] = list(valeur) if isinstance(valeur, tuple) else valeur
    return section


def _resoudreGroupeZoom(brut, avertissements):
    """Résout le groupe de touches du zoom, ou le replie en entier.

    Le repli est global et non par élément : un groupe partiellement replié
    laisserait des niveaux de zoom inatteignables sans qu'on puisse dire
    lesquels, et remettre un seul élément depuis le défaut risquerait un doublon
    avec une touche que l'utilisateur a déplacée.
    """
    defaut = TOUCHES_PAR_DEFAUT[ACTION_ZOOM]

    if brut is None:
        return defaut

    if isinstance(brut, str) or not isinstance(brut, (list, tuple)):
        avertissements.append(
            "Raccourci « %s » : une liste de %d touches est attendue, valeurs "
            "par défaut appliquées au groupe." % (ACTION_ZOOM, NIVEAUX_ZOOM)
        )
        return defaut

    if len(brut) != NIVEAUX_ZOOM:
        avertissements.append(
            "Raccourci « %s » : %d touche(s) donnée(s) pour %d niveaux de zoom, "
            "valeurs par défaut appliquées au groupe."
            % (ACTION_ZOOM, len(brut), NIVEAUX_ZOOM)
        )
        return defaut

    noms = []
    for valeur in brut:
        nom = normaliser(valeur)
        if nom is None:
            avertissements.append(
                "Raccourci « %s » : %s (%r), valeurs par défaut appliquées au "
                "groupe." % (ACTION_ZOOM, raisonDuRefus(valeur), valeur)
            )
            return defaut
        if nom in noms:
            avertissements.append(
                "Raccourci « %s » : la touche %s est donnée deux fois, valeurs "
                "par défaut appliquées au groupe." % (ACTION_ZOOM, nom)
            )
            return defaut
        noms.append(nom)

    return tuple(noms)


def resoudre(brut):
    """Résout la section lue en deux tables et une liste d'avertissements.

    Rend `(touches, inverses, avertissements)` :

    - `touches` : action vers nom canonique, pour les onze actions. La valeur
      est la chaîne vide quand l'action n'a aucune touche, et un tuple de noms
      pour le zoom.
    - `inverses` : nom canonique vers `(action, argument)`. L'argument vaut None
      sauf pour le zoom, où il porte le niveau, et pour les quatre outils, où il
      porte la clé d'outil. Un seul mécanisme de répartition suffit ainsi aux
      deux.
    - `avertissements` : phrases déjà formatées. Vide quand la section est
      saine, section absente comprise.

    Ne lève jamais : une section qui n'est pas un dictionnaire vaut une section
    absente.
    """
    avertissements = []

    if brut is None:
        brut = {}
    elif not isinstance(brut, dict):
        avertissements.append(
            "Section « %s » : un dictionnaire d'actions est attendu, valeurs par "
            "défaut appliquées." % CLE_SECTION
        )
        brut = {}

    for cle in brut:
        if cle not in TOUCHES_PAR_DEFAUT:
            avertissements.append(
                "Raccourci « %s » : action inconnue, ligne sans effet." % cle
            )

    touches = {}
    inverses = {}

    for action in ACTIONS:
        if action == ACTION_ZOOM:
            groupe = _resoudreGroupeZoom(brut.get(action), avertissements)
            retenu = []
            for niveau, nom in enumerate(groupe):
                occupant = inverses.get(nom)
                if occupant is not None:
                    avertissements.append(
                        "Raccourci « %s » : la touche %s est déjà celle de "
                        "« %s », ce niveau de zoom reste sans touche."
                        % (action, nom, occupant[0])
                    )
                    continue
                inverses[nom] = (action, niveau)
                retenu.append(nom)
            touches[action] = tuple(retenu)
            continue

        if action not in brut:
            nom = normaliser(TOUCHES_PAR_DEFAUT[action])
        else:
            valeur = brut[action]
            # Valeur vide : désaffectation volontaire, et non une erreur. C'est
            # l'état par défaut de la bascule de tracé.
            if valeur is None or (isinstance(valeur, str) and not valeur.strip()):
                touches[action] = ""
                continue
            nom = normaliser(valeur)
            if nom is None:
                avertissements.append(
                    "Raccourci « %s » : %s. Valeur %r écartée, valeur par "
                    "défaut appliquée." % (action, raisonDuRefus(valeur), valeur)
                )
                nom = normaliser(TOUCHES_PAR_DEFAUT[action])

        if nom is None:
            # Le défaut de l'action est vide : rien à affecter.
            touches[action] = ""
            continue

        occupant = inverses.get(nom)
        if occupant is not None:
            # Le perdant reste sans touche, plutôt que de retomber sur son
            # défaut : lui rendre sa touche d'origine ressusciterait un
            # raccourci que l'utilisateur a peut-être déplacé exprès. Sans
            # touche, l'action le montre dans l'interface, son libellé perdant
            # sa mention.
            avertissements.append(
                "Raccourci « %s » : la touche %s est déjà celle de « %s », "
                "« %s » reste sans touche." % (action, nom, occupant[0], action)
            )
            touches[action] = ""
            continue

        touches[action] = nom
        inverses[nom] = (action, ARGUMENTS.get(action))

    return touches, inverses, avertissements


def lire(chemin):
    """Lit le fichier de paramètres et en résout la section des raccourcis.

    Même contrat que resoudre(). Un fichier absent, illisible ou tronqué vaut
    une section absente : les touches par défaut s'appliquent, et l'ouverture de
    l'extension n'est jamais empêchée par le fichier de paramètres.
    """
    try:
        with open(chemin, encoding="utf-8") as f:
            charge = json.load(f)
    except (OSError, ValueError):
        touches, inverses, avertissements = resoudre({})
        avertissements.append(
            "Paramètres illisibles, raccourcis par défaut appliqués : %s" % chemin
        )
        return touches, inverses, avertissements

    if not isinstance(charge, dict):
        # Le fichier est lisible mais ce n'est pas un dictionnaire de sections :
        # anomalie à signaler, et non une section simplement absente.
        touches, inverses, avertissements = resoudre({})
        avertissements.append(
            "Paramètres inattendus, raccourcis par défaut appliqués : %s" % chemin
        )
        return touches, inverses, avertissements

    return resoudre(charge.get(CLE_SECTION))
