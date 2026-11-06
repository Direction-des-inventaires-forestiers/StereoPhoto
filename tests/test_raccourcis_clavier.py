# -*- coding: utf-8 -*-
"""Test de la table des raccourcis clavier et de sa résolution.

Le défaut que ce test garde n'est pas une erreur de calcul, c'est une rigidité
doublée d'une fragilité. Les sept raccourcis de la navigation étaient des
littéraux dans une cascade de `if`/`elif`, et l'intercepteur clavier de la
navigation avalant tout, ils étaient le seul accès clavier aux outils : les
figer dans le code fermait cet accès à qui n'avait pas le clavier ni les
habitudes du poste d'origine. En les rendant lisibles depuis le fichier de
paramètres, on ouvre en revanche la porte à un fichier mal écrit, et une
session ne doit jamais échouer à s'ouvrir pour une touche mal orthographiée.

Le test couvre donc deux choses :

1. **La table et sa résolution**, dans `src/raccourcisClavier.py`, module pur
   qui s'importe directement. Chaque forme de fichier mal écrit — touche
   inconnue, touche en double, action inconnue, groupe de zoom de mauvaise
   taille, section qui n'est pas un dictionnaire — doit donner une table
   utilisable et un avertissement nommant la faute. Et la désaffectation
   volontaire d'une touche, qui ressemble à une erreur mais n'en est pas, ne
   doit produire aucun avertissement : c'est ce contrôle qui distingue les deux.
2. **La frontière avec Qt**, dans `src/stereoPhoto.py`, où les noms de touches
   deviennent des constantes de Qt. Les deux tables sont lues par analyse
   syntaxique, parce qu'une touche sans nom — ou un nom sans touche — est un
   raccourci que personne ne peut déclencher, et que rien d'autre ne le
   signalerait.

L'attendu est recopié ici, et non importé du module testé : une table qui se
vérifierait contre elle-même ne vérifierait rien.

Usage :
    python tests/test_raccourcis_clavier.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import json
import os
import re
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Touches par défaut attendues, recopiées. Le groupe de zoom est une seule
# entrée et non huit : c'est la forme qui doit tenir.
ATTENDU = {
    "bascule_fenetre": "Échap",
    "zoom": ("F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"),
    "outil_selectionner": "1",
    "outil_ajouter": "2",
    "outil_combiner": "3",
    "outil_decouper": "4",
    "bascule_trace": "",
    "suivi_mnt": "M",
    "curseur_libre": "C",
    "annuler": "Ctrl+Z",
    "enregistrer": "Ctrl+S",
}

# Clés d'outil attendues, recopiées d'editionOutils. Le test croise les deux
# modules purs, qui ne s'importent pas l'un l'autre.
OUTILS_ATTENDUS = ("selectionner", "ajouter", "combiner", "decouper")

# Écritures qui doivent être acceptées, et la forme canonique attendue.
NORMALISATIONS = (
    ("ctrl+z", "Ctrl+Z"),
    ("Ctrl+Z", "Ctrl+Z"),
    ("CTRL + Z", "Ctrl+Z"),
    ("  ctrl  +  z  ", "Ctrl+Z"),
    ("alt+ctrl+z", "Ctrl+Alt+Z"),
    ("Échap", "Échap"),
    ("echap", "Échap"),
    ("esc", "Échap"),
    ("ESCAPE", "Échap"),
    ("f5", "F5"),
    ("retour arriere", "Retour arrière"),
    ("entree", "Retour"),
    ("+", "+"),
    ("ctrl++", "Ctrl++"),
)

# Écritures qui doivent être refusées, chacune pour une raison distincte.
REFUS = (
    "maj+a",
    "shift+a",
    "meta+a",
    "",
    "   ",
    None,
    42,
    True,
    ["F5"],
    "ctrl+ctrl+z",
    "ctrl+",
    "ctrl",
    "F13",
    "&",
    "Pomme",
)


def verifier(echecs, condition, message, *args):
    """Ajoute un écart si la condition n'est pas remplie."""
    if not condition:
        echecs.append(message % args if args else message)


def casTableConforme(mod):
    """Les touches par défaut valent celles attendues, dans la forme attendue."""
    echecs = []

    verifier(
        echecs,
        set(mod.TOUCHES_PAR_DEFAUT) == set(ATTENDU),
        "actions de la table : %r au lieu de %r",
        sorted(mod.TOUCHES_PAR_DEFAUT),
        sorted(ATTENDU),
    )

    for action, attendu in sorted(ATTENDU.items()):
        obtenu = mod.TOUCHES_PAR_DEFAUT.get(action)
        verifier(
            echecs,
            obtenu == attendu,
            "défaut de « %s » : %r au lieu de %r",
            action,
            obtenu,
            attendu,
        )

    verifier(
        echecs,
        isinstance(mod.TOUCHES_PAR_DEFAUT["zoom"], tuple),
        "le groupe de zoom doit être un tuple, et non huit entrées séparées",
    )

    return echecs, "onze actions, groupe de zoom en une entrée"


def casActionsDeclarees(mod):
    """L'ordre de départage est déclaré, complet et sans doublon."""
    echecs = []

    verifier(
        echecs,
        len(mod.ACTIONS) == len(set(mod.ACTIONS)),
        "ACTIONS porte un doublon : le départage d'un conflit en dépend",
    )
    verifier(
        echecs,
        set(mod.ACTIONS) == set(mod.TOUCHES_PAR_DEFAUT),
        "ACTIONS et TOUCHES_PAR_DEFAUT divergent : %r",
        set(mod.ACTIONS) ^ set(mod.TOUCHES_PAR_DEFAUT),
    )
    verifier(
        echecs,
        mod.ACTIONS.index(mod.ACTION_ZOOM) <= 1,
        "le groupe de zoom doit être résolu tôt : il se replie le plus mal",
    )

    for action, argument in sorted(mod.ARGUMENTS.items()):
        verifier(
            echecs,
            action in mod.TOUCHES_PAR_DEFAUT,
            "ARGUMENTS nomme « %s », qui n'est pas une action",
            action,
        )
        verifier(
            echecs,
            argument in OUTILS_ATTENDUS,
            "argument de « %s » : %r n'est pas une clé d'outil",
            action,
            argument,
        )

    return echecs, "ordre déclaré, arguments d'outil"


def casActionsOutil(mod, editionOutils):
    """Les quatre outils d'édition ont chacun leur action, et pas un de plus."""
    echecs = []

    verifier(
        echecs,
        set(editionOutils.OUTILS) == set(OUTILS_ATTENDUS),
        "editionOutils.OUTILS a changé : %r",
        editionOutils.OUTILS,
    )
    verifier(
        echecs,
        set(mod.ACTIONS_OUTIL) == set(editionOutils.OUTILS),
        "outils sans raccourci ou raccourci sans outil : %r",
        set(mod.ACTIONS_OUTIL) ^ set(editionOutils.OUTILS),
    )
    for cle, action in sorted(mod.ACTIONS_OUTIL.items()):
        verifier(
            echecs,
            action in mod.TOUCHES_PAR_DEFAUT,
            "l'outil « %s » renvoie à « %s », qui n'est pas une action",
            cle,
            action,
        )

    return echecs, "les deux modules purs croisés"


def casDefautsCoherents(mod, config):
    """Chaque défaut est une touche connue, canonique, et réclamée une seule fois."""
    echecs = []

    verifier(
        echecs,
        mod.NIVEAUX_ZOOM == len(config.NAVIGATION_ZOOM_NIVEAUX),
        "%d touches de zoom pour %d niveaux : des niveaux seraient inatteignables",
        mod.NIVEAUX_ZOOM,
        len(config.NAVIGATION_ZOOM_NIVEAUX),
    )
    verifier(
        echecs,
        len(mod.TOUCHES_CONNUES) == len(set(mod.TOUCHES_CONNUES)),
        "TOUCHES_CONNUES porte un doublon",
    )

    reclamees = {}
    for action in mod.ACTIONS:
        valeur = mod.TOUCHES_PAR_DEFAUT[action]
        noms = valeur if isinstance(valeur, tuple) else ([valeur] if valeur else [])
        for nom in noms:
            verifier(
                echecs,
                nom in mod.TOUCHES_CONNUES or mod.SEPARATEUR in nom,
                "défaut de « %s » : %r hors du vocabulaire des touches",
                action,
                nom,
            )
            # La forme canonique est un point fixe de la normalisation : sans
            # cela, un défaut ne se comparerait pas à lui-même relu du fichier.
            verifier(
                echecs,
                mod.normaliser(nom) == nom,
                "défaut de « %s » : %r n'est pas sous forme canonique (%r)",
                action,
                nom,
                mod.normaliser(nom),
            )
            verifier(
                echecs,
                nom not in reclamees,
                "touche %s réclamée par « %s » et « %s » dès les défauts",
                nom,
                reclamees.get(nom),
                action,
            )
            reclamees[nom] = action

    return echecs, "vocabulaire, forme canonique, aucun doublon"


def casFichierLivre(mod, source):
    """Le fichier de paramètres livré porte la section, égale aux défauts.

    C'est le fichier que l'utilisateur édite : s'il ne portait pas la section,
    il n'aurait aucun moyen de savoir quelles actions sont modifiables ni sous
    quel nom.
    """
    echecs = []
    chemin = os.path.join(source, "paramStoring.json")

    try:
        charge = json.load(io.open(chemin, encoding="utf-8"))
    except (OSError, ValueError) as souci:
        return ["paramStoring.json illisible : %s" % souci], "fichier illisible"

    section = charge.get(mod.CLE_SECTION)
    verifier(
        echecs,
        section is not None,
        "paramStoring.json ne porte pas la section « %s »",
        mod.CLE_SECTION,
    )
    if section is not None:
        verifier(
            echecs,
            section == mod.sectionParDefaut(),
            "la section livrée diverge des défauts du code : %r",
            section,
        )

    return echecs, "section livrée, accordée au code"


def casSectionParDefaut(mod):
    """La section rendue est neuve, sérialisable, et n'aliase pas la table.

    Elle part dans le dictionnaire de paramètres que l'extension réécrit à
    chaque fermeture de session : un tuple n'y survivrait pas à l'aller-retour,
    et une référence partagée laisserait une modification du fichier contaminer
    les défauts du code.
    """
    echecs = []

    section = mod.sectionParDefaut()
    verifier(
        echecs,
        section == json.loads(json.dumps(section)),
        "la section ne survit pas à un aller-retour JSON",
    )
    for action, valeur in sorted(section.items()):
        verifier(
            echecs,
            not isinstance(valeur, tuple),
            "« %s » rendu en tuple : non sérialisable en JSON",
            action,
        )

    section["suivi_mnt"] = "ZZZ"
    section["zoom"].append("F1")
    verifier(
        echecs,
        mod.TOUCHES_PAR_DEFAUT["suivi_mnt"] == "M",
        "modifier la section rendue a modifié les défauts du module",
    )
    verifier(
        echecs,
        len(mod.TOUCHES_PAR_DEFAUT["zoom"]) == mod.NIVEAUX_ZOOM,
        "le groupe de zoom des défauts a été modifié par l'appelant",
    )
    verifier(
        echecs,
        mod.sectionParDefaut()["suivi_mnt"] == "M",
        "deux appels de sectionParDefaut() ne rendent pas le même état",
    )

    return echecs, "neuve, sérialisable, non aliasée"


def casNormalisation(mod):
    """Casse, accents, espaces et ordre des modificateurs sont absorbés."""
    echecs = []

    for texte, attendu in NORMALISATIONS:
        obtenu = mod.normaliser(texte)
        verifier(
            echecs,
            obtenu == attendu,
            "normaliser(%r) : %r au lieu de %r",
            texte,
            obtenu,
            attendu,
        )

    for texte in REFUS:
        obtenu = mod.normaliser(texte)
        verifier(
            echecs,
            obtenu is None,
            "normaliser(%r) : %r au lieu d'un refus",
            texte,
            obtenu,
        )

    return echecs, "%d écritures acceptées, %d refusées" % (
        len(NORMALISATIONS),
        len(REFUS),
    )


def casRaisonDuRefus(mod):
    """Un refus dit pourquoi, et distingue le choix de la faute de frappe.

    Un modificateur non pris en charge n'est pas une touche mal orthographiée :
    qui écrit « Maj+A » a fait un choix, et doit lire qu'il est refusé plutôt
    que de chercher sa faute. Sans ce contrôle, la liste des modificateurs
    refusés n'aurait aucun effet observable et pourrait disparaître sans que
    rien ne le signale.
    """
    echecs = []

    for texte, attendu in (
        ("Maj+M", "modificateur"),
        ("Shift+A", "modificateur"),
        ("meta+a", "modificateur"),
        ("Pomme", "touche inconnue"),
        ("F13", "touche inconnue"),
        (42, "texte"),
    ):
        raison = mod.raisonDuRefus(texte)
        verifier(
            echecs,
            attendu in raison,
            "refus de %r : %r ne parle pas de %r",
            texte,
            raison,
            attendu,
        )

    for texte in ("Ctrl+Z", "M", "f5", "esc"):
        verifier(
            echecs,
            mod.raisonDuRefus(texte) == "",
            "écriture valide %r donnée pour refusée : %r",
            texte,
            mod.raisonDuRefus(texte),
        )

    # L'avertissement porté au journal reprend la raison : c'est le seul
    # endroit où l'utilisateur peut la lire.
    _, _, avertissements = mod.resoudre({"suivi_mnt": "Maj+M"})
    verifier(
        echecs,
        len(avertissements) == 1 and "modificateur" in avertissements[0],
        "avertissement d'un modificateur refusé : %r",
        avertissements,
    )
    _, _, avertissements = mod.resoudre({"suivi_mnt": "Pomme"})
    verifier(
        echecs,
        len(avertissements) == 1 and "modificateur" not in avertissements[0],
        "une touche inconnue ne doit pas être imputée à un modificateur : %r",
        avertissements,
    )

    return echecs, "modificateur refusé, faute de frappe, écriture valide"


def casReplis(mod):
    """Chaque forme de fichier mal écrit donne une table utilisable.

    Le nombre d'avertissements compte autant que la table : c'est lui qui
    sépare la désaffectation volontaire, qui est muette, de la touche inconnue,
    qui doit parler.
    """
    echecs = []

    def resoudre(titre, brut, attentes, avertissements_attendus):
        touches, inverses, avertissements = mod.resoudre(brut)
        verifier(
            echecs,
            len(avertissements) == avertissements_attendus,
            "%s : %d avertissement(s) au lieu de %d — %r",
            titre,
            len(avertissements),
            avertissements_attendus,
            avertissements,
        )
        for action, attendu in attentes.items():
            obtenu = touches.get(action)
            verifier(
                echecs,
                obtenu == attendu,
                "%s : « %s » vaut %r au lieu de %r",
                titre,
                action,
                obtenu,
                attendu,
            )
        return touches, inverses

    defauts = {action: ATTENDU[action] for action in ATTENDU}

    resoudre("section absente", None, defauts, 0)
    resoudre("section vide", {}, defauts, 0)
    # Un fichier écrit par une version antérieure ne porte pas une action
    # ajoutée depuis : avertir serait du bruit à chaque mise à jour.
    resoudre("action absente du fichier", {"curseur_libre": "C"}, defauts, 0)
    resoudre("désaffectation par chaîne vide", {"suivi_mnt": ""}, {"suivi_mnt": ""}, 0)
    resoudre("désaffectation par null", {"suivi_mnt": None}, {"suivi_mnt": ""}, 0)
    resoudre("touche inconnue", {"suivi_mnt": "Pomme"}, {"suivi_mnt": "M"}, 1)
    resoudre("modificateur refusé", {"suivi_mnt": "Maj+M"}, {"suivi_mnt": "M"}, 1)
    # Le perdant reste sans touche : lui rendre son défaut ressusciterait un
    # raccourci que l'utilisateur a peut-être déplacé exprès.
    resoudre(
        "touche en double",
        {"suivi_mnt": "C"},
        {"suivi_mnt": "C", "curseur_libre": ""},
        1,
    )
    resoudre("action inconnue", {"zoom_arriere": "F3"}, defauts, 1)
    resoudre("section qui n'est pas un dictionnaire", [], defauts, 1)
    resoudre("section textuelle", "F5", defauts, 1)

    # Le groupe de zoom se replie en entier : un repli par élément laisserait
    # des niveaux inatteignables sans qu'on puisse dire lesquels.
    for titre, groupe in (
        ("groupe trop court", ["F5", "F6", "F7"]),
        ("groupe trop long", ["F%d" % n for n in range(1, 10)]),
        ("groupe qui n'est pas une liste", "F5"),
        # Huit noms distincts dont un seul invalide : sans quoi c'est la règle
        # du doublon qui répondrait, et celle de la touche inconnue ne serait
        # jamais éprouvée.
        (
            "groupe portant une touche inconnue",
            ["F5", "F6", "F7", "F8", "F9", "F10", "F11", "F13"],
        ),
        (
            "groupe portant un doublon",
            ["F5", "F5", "F7", "F8", "F9", "F10", "F11", "F12"],
        ),
    ):
        touches, _ = resoudre(titre, {"zoom": groupe}, {}, 1)
        verifier(
            echecs,
            touches["zoom"] == ATTENDU["zoom"],
            "%s : le groupe devrait se replier en entier, obtenu %r",
            titre,
            touches["zoom"],
        )

    # Le repli du groupe doit être global, et pas élément par élément. Les sept
    # premières touches ci-dessous ne sont pas celles du défaut : un repli par
    # élément rendrait un groupe mêlé, que le contrôle précédent ne distinguait
    # pas du défaut, ses touches valides étant justement celles du défaut.
    touches, _ = resoudre(
        "groupe presque valide",
        {"zoom": ["1", "2", "3", "4", "5", "6", "7", "F13"]},
        {},
        1,
    )
    verifier(
        echecs,
        touches["zoom"] == ATTENDU["zoom"],
        "repli du groupe : %r au lieu du défaut entier — un repli par élément "
        "laisserait un groupe mêlé",
        touches["zoom"],
    )

    # Un groupe valide mais non contigu est honoré ; il prend alors les touches
    # des outils, qui le signalent et restent sans touche.
    touches, inverses = resoudre(
        "groupe non contigu",
        {"zoom": [str(n) for n in range(1, 9)]},
        {"outil_selectionner": "", "outil_ajouter": ""},
        4,
    )
    verifier(
        echecs,
        inverses.get("1") == ("zoom", 0),
        "groupe non contigu : la touche 1 devrait porter le premier niveau",
    )

    return echecs, "absence, désaffectation, doublon, groupe"


def casTableInverse(mod):
    """La table inverse est une bijection, et tous les niveaux sont atteignables."""
    echecs = []

    touches, inverses, _ = mod.resoudre({})

    attendues = set()
    for action in mod.ACTIONS:
        valeur = touches[action]
        if isinstance(valeur, tuple):
            attendues.update(valeur)
        elif valeur:
            attendues.add(valeur)

    verifier(
        echecs,
        set(inverses) == attendues,
        "table inverse et table directe divergent : %r",
        set(inverses) ^ attendues,
    )

    niveaux = sorted(
        argument for action, argument in inverses.values() if action == mod.ACTION_ZOOM
    )
    verifier(
        echecs,
        niveaux == list(range(mod.NIVEAUX_ZOOM)),
        "niveaux de zoom atteignables : %r au lieu de 0 à %d",
        niveaux,
        mod.NIVEAUX_ZOOM - 1,
    )

    for cle, action in sorted(mod.ACTIONS_OUTIL.items()):
        nom = touches[action]
        verifier(
            echecs,
            inverses.get(nom) == (action, cle),
            "la touche %s de « %s » ne porte pas la clé d'outil %r",
            nom,
            action,
            cle,
        )

    for nom, (action, argument) in sorted(inverses.items()):
        if action in (mod.ACTION_ZOOM,) or action in mod.ARGUMENTS:
            continue
        verifier(
            echecs,
            argument is None,
            "la touche %s de « %s » porte un argument inattendu : %r",
            nom,
            action,
            argument,
        )

    return echecs, "bijection, huit niveaux, clés d'outil"


def casLecture(mod):
    """Aucune forme de fichier n'empêche l'ouverture d'une session."""
    echecs = []

    with tempfile.TemporaryDirectory() as dossier:
        chemin = os.path.join(dossier, "paramStoring.json")

        formes = (
            ("fichier absent", None, 1),
            ("JSON tronqué", '{\n  "raccourcis": {', 1),
            ("JSON qui est une liste", "[]", 1),
            ("fichier vide", "", 1),
            ("section absente du fichier", '{"position": {}}', 0),
            ("section saine", '{"raccourcis": {"suivi_mnt": "T"}}', 0),
        )

        for titre, contenu, avertissements_attendus in formes:
            if contenu is None:
                if os.path.exists(chemin):
                    os.remove(chemin)
            else:
                io.open(chemin, "w", encoding="utf-8").write(contenu)

            try:
                touches, inverses, avertissements = mod.lire(chemin)
            except Exception as souci:
                echecs.append("%s : lire() a levé %r" % (titre, souci))
                continue

            verifier(
                echecs,
                len(avertissements) == avertissements_attendus,
                "%s : %d avertissement(s) au lieu de %d",
                titre,
                len(avertissements),
                avertissements_attendus,
            )
            verifier(
                echecs,
                set(touches) == set(ATTENDU),
                "%s : la table rendue est incomplète",
                titre,
            )
            verifier(
                echecs,
                touches["curseur_libre"] == "C",
                "%s : le défaut de curseur_libre devrait tenir",
                titre,
            )

        io.open(chemin, "w", encoding="utf-8").write(
            '{"raccourcis": {"suivi_mnt": "T"}}'
        )
        touches, inverses, _ = mod.lire(chemin)
        verifier(
            echecs,
            touches["suivi_mnt"] == "T",
            "section saine : la touche du fichier devrait être retenue, obtenu %r",
            touches["suivi_mnt"],
        )
        verifier(
            echecs,
            "M" not in inverses,
            "section saine : l'ancienne touche M devrait avoir cessé de répondre",
        )

    return echecs, "absent, tronqué, liste, vide, sain"


def casAnnonces(mod):
    """Les textes montrés nomment la touche, ou se taisent s'il n'y en a pas."""
    echecs = []

    for nom, attendu in (
        ("M", "touche M"),
        ("Ctrl+Z", "Ctrl+Z"),
        ("Ctrl+Alt+Z", "Ctrl+Alt+Z"),
        ("", ""),
        (None, ""),
    ):
        obtenu = mod.annonce(nom)
        verifier(
            echecs,
            obtenu == attendu,
            "annonce(%r) : %r au lieu de %r",
            nom,
            obtenu,
            attendu,
        )

    for noms, attendu in (
        (("F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12"), "F5 à F12"),
        (("F5", "F7", "F9"), "F5, F7, F9"),
        (("F5",), "F5"),
        ((), ""),
        (None, ""),
    ):
        obtenu = mod.annonceGroupe(noms)
        verifier(
            echecs,
            obtenu == attendu,
            "annonceGroupe(%r) : %r au lieu de %r",
            noms,
            obtenu,
            attendu,
        )

    return echecs, "plage, énumération, silence"


# --- Moitié frontière : la traduction vers Qt, dans stereoPhoto -------------
#
# Valeurs numériques des constantes de Qt, pour que le test s'exécute sans Qt
# installé. Elles viennent de Qt::Key et de Qt::KeyboardModifier et ne changent
# pas d'une version à l'autre : ce sont celles que l'extension reçoit.
KEY_ESCAPE = 0x01000000
KEY_F1 = 0x01000030
KEY_F2 = 0x01000031
KEY_F5 = 0x01000034
KEY_F12 = 0x0100003B
KEY_F13 = 0x0100003C
KEY_0 = 0x30
KEY_1 = 0x31
KEY_2 = 0x32
KEY_3 = 0x33
KEY_4 = 0x34
KEY_A = 0x41
KEY_C = 0x43
KEY_M = 0x4D
KEY_S = 0x53
KEY_Z = 0x5A

NO_MODIFIER = 0x00000000
SHIFT_MODIFIER = 0x02000000
CONTROL_MODIFIER = 0x04000000
ALT_MODIFIER = 0x08000000
KEYPAD_MODIFIER = 0x20000000

TYPE_EVENEMENT_PRESSE = 6
TYPE_EVENEMENT_RELACHE = 7

# Sous-ensemble de la table de traduction, pour le bouchon. La vraie table est
# vérifiée à part, par analyse syntaxique : la recopier en entier ici ne
# vérifierait rien de plus et devrait suivre chaque ajout.
TOUCHES_QT_BOUCHON = {
    KEY_ESCAPE: "Échap",
    KEY_F1: "F1",
    KEY_F2: "F2",
    KEY_F5: "F5",
    KEY_F12: "F12",
    KEY_0: "0",
    KEY_1: "1",
    KEY_2: "2",
    KEY_3: "3",
    KEY_4: "4",
    KEY_A: "A",
    KEY_C: "C",
    KEY_M: "M",
    KEY_S: "S",
    KEY_Z: "Z",
}


def motifTouchesEnDur(noms):
    """Motif d'une touche nommée dans une chaîne montrée à l'utilisateur.

    Construit depuis le vocabulaire du module, et non devine : un motif
    approximatif comme « touche suivie d'une lettre » attrapait « touche sans
    effet » dans un message de journal, et aurait manqué « touche Échap », dont
    la première lettre n'est pas dans l'alphabet latin de base.

    Les noms les plus longs passent d'abord : sans quoi « Retour » coifferait
    « Retour arrière », que l'alternance n'essaierait jamais.
    """
    alternatives = "|".join(
        re.escape(nom) for nom in sorted(noms, key=len, reverse=True)
    )
    # Fin de mot écrite en négation explicite, et espace en classe de
    # caractères : le motif reste lisible d'un bloc, et « touche M » se
    # distingue de « touche Majuscule » sans ambiguïté.
    return re.compile(
        "(?i)(?:touche[ ]+|Ctrl[+]|Alt[+])(?:%s)(?![A-Za-z0-9])" % alternatives
        + "|F[0-9]+ à F[0-9]+"
    )


# Fichiers qui ne doivent plus porter de touche en littéral. raccourcisClavier
# en est exclu : c'est le seul endroit où ces chaînes ont leur place.
FICHIERS_SANS_TOUCHE = (
    "stereoPhoto.py",
    "ui_widgetStereoPhoto.py",
    "editionOutils.py",
    "ui-optionWindow.ui",
)


class EvenementClavierBouchon:
    """Le QKeyEvent réduit à ce que la frontière en lit."""

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


class QtBouchon:
    """Les modificateurs que la frontière lit, et rien de plus."""

    ControlModifier = CONTROL_MODIFIER
    AltModifier = ALT_MODIFIER


class QEventBouchon:
    KeyPress = TYPE_EVENEMENT_PRESSE
    KeyRelease = TYPE_EVENEMENT_RELACHE


class JournalBouchon:
    """Retient les lignes, pour vérifier qu'un silence n'en est pas un."""

    def __init__(self):
        self.lignes = []

    def _noter(self, niveau):
        def ecrire(message, *args):
            self.lignes.append((niveau, message % args if args else message))

        return ecrire

    def __getattr__(self, nom):
        return self._noter(nom)


class ApplicationBouchon:
    """stereoPhoto réduit à ce que les méthodes de frontière sollicitent.

    `TOUCHES_QT` et `MODIFICATEURS_QT` sont des attributs de classe, que
    l'extraction d'une fonction n'emporte pas : le bouchon les fournit, et la
    vraie table est vérifiée par analyse syntaxique.
    """

    TOUCHES_QT = TOUCHES_QT_BOUCHON
    MODIFICATEURS_QT = (
        (CONTROL_MODIFIER, "Ctrl"),
        (ALT_MODIFIER, "Alt"),
    )

    def __init__(self, mod, brut=None):
        self.journal = JournalBouchon()
        self.appels = []
        self.raccourcis, self.raccourcisInverses, _ = mod.resoudre(brut)
        self.tableRaccourcis = {
            action: self._recepteur(action) for action in mod.ACTIONS
        }

    def _recepteur(self, action):
        def appeler(*arguments):
            self.appels.append(
                "%s:%r" % (action, arguments[0]) if arguments else action
            )

        return appeler


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
        raise AssertionError("classe %s introuvable" % classe_visee)

    corps = [
        n
        for n in classe.body
        if isinstance(n, ast.FunctionDef) and n.name in methodes_visees
    ]
    manquantes = set(methodes_visees) - {n.name for n in corps}
    if manquantes:
        raise AssertionError(
            "méthode(s) %s introuvable(s)" % ", ".join(sorted(manquantes))
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in methodes_visees}


def monter(source, brut=None):
    """Monte la frontière du clavier avec ses bouchons."""
    import raccourcisClavier as mod

    espace = {
        "raccourcisClavier": mod,
        "Qt": QtBouchon,
        "QEvent": QEventBouchon,
    }
    methodes = extraire_methodes(
        os.path.join(source, "stereoPhoto.py"),
        "stereoPhoto",
        ("nomTouche", "keyboardHandler", "executerRaccourci", "codesTouches"),
        espace,
    )
    app = ApplicationBouchon(mod, brut)
    for nom, fonction in methodes.items():
        setattr(app, nom, fonction.__get__(app, ApplicationBouchon))
    return app


def _constantes_de_fichier(chemin):
    """Chaînes littérales d'un fichier Python, docstrings écartées.

    Les docstrings sont écartées parce qu'elles expliquent le mécanisme et
    citent des exemples de touches : les y interdire ferait échouer le banc à
    chaque reformulation de commentaire, sans rien garder d'utile.
    """
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    docstrings = set()
    for noeud in ast.walk(arbre):
        if not isinstance(
            noeud, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            continue
        corps = getattr(noeud, "body", None) or []
        if (
            corps
            and isinstance(corps[0], ast.Expr)
            and isinstance(corps[0].value, ast.Constant)
            and isinstance(corps[0].value.value, str)
        ):
            docstrings.add(id(corps[0].value))

    return [
        n.value
        for n in ast.walk(arbre)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and id(n) not in docstrings
    ]


def casFrontiereQt(mod, source):
    """La table de traduction couvre exactement le vocabulaire des touches.

    C'est la garde qui porte le plus : une touche sans nom, ou un nom sans
    touche, est un raccourci que l'utilisateur peut écrire dans le fichier et
    que personne ne peut déclencher. Rien d'autre ne le signalerait.
    """
    echecs = []
    chemin = os.path.join(source, "stereoPhoto.py")
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())

    table = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.Assign)
            and any(isinstance(c, ast.Name) and c.id == "TOUCHES_QT" for c in n.targets)
        ),
        None,
    )
    if table is None:
        return ["TOUCHES_QT introuvable dans stereoPhoto"], "table absente"

    if not isinstance(table.value, ast.Dict):
        return [
            "TOUCHES_QT n'est pas un littéral : la garde ne peut plus la lire"
        ], "table calculée"

    codes = []
    noms = []
    for cle, valeur in zip(table.value.keys, table.value.values):
        if not isinstance(cle, ast.Attribute) or not cle.attr.startswith("Key_"):
            echecs.append("clé de TOUCHES_QT qui n'est pas une touche de Qt")
            continue
        if not isinstance(valeur, ast.Constant):
            echecs.append("valeur calculée pour %s : la garde ne la lit pas" % cle.attr)
            continue
        codes.append(cle.attr)
        noms.append(valeur.value)

    verifier(
        echecs,
        len(codes) == len(set(codes)),
        "TOUCHES_QT porte deux fois la même touche de Qt",
    )
    verifier(
        echecs,
        len(noms) == len(set(noms)),
        "TOUCHES_QT porte deux fois le même nom : %r",
        sorted({n for n in noms if noms.count(n) > 1}),
    )

    sans_touche = set(mod.TOUCHES_CONNUES) - set(noms)
    verifier(
        echecs,
        not sans_touche,
        "noms affectables qu'aucune touche de Qt ne porte : %r",
        sorted(sans_touche),
    )
    sans_nom = set(noms) - set(mod.TOUCHES_CONNUES)
    verifier(
        echecs,
        not sans_nom,
        "touches traduites vers un nom hors du vocabulaire : %r",
        sorted(sans_nom),
    )

    modificateurs = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(c, ast.Name) and c.id == "MODIFICATEURS_QT"
                for c in n.targets
            )
        ),
        None,
    )
    if modificateurs is None:
        echecs.append("MODIFICATEURS_QT introuvable")
    else:
        etiquettes = [
            e.attr
            for e in ast.walk(modificateurs.value)
            if isinstance(e, ast.Attribute) and e.attr.startswith("MODIFICATEUR_")
        ]
        verifier(
            echecs,
            len(etiquettes) == len(mod.MODIFICATEURS),
            "%d modificateur(s) traduits pour %d déclarés",
            len(etiquettes),
            len(mod.MODIFICATEURS),
        )

    return echecs, "%d touches traduites, %d modificateurs" % (
        len(codes),
        len(mod.MODIFICATEURS),
    )


def casTableDesRecepteurs(mod, source):
    """Chaque action déclarée a un récepteur, et chaque récepteur une action."""
    echecs = []
    chemin = os.path.join(source, "stereoPhoto.py")
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())

    table = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(c, ast.Attribute) and c.attr == "tableRaccourcis"
                for c in n.targets
            )
        ),
        None,
    )
    if table is None or not isinstance(table.value, ast.Dict):
        return ["tableRaccourcis introuvable ou calculée"], "table absente"

    actions = [
        c.attr
        for c in table.value.keys
        if isinstance(c, ast.Attribute) and c.attr.startswith("ACTION_")
    ]
    attendues = [
        nom
        for nom in dir(mod)
        if nom.startswith("ACTION_") and getattr(mod, nom) in mod.ACTIONS
    ]

    verifier(
        echecs,
        set(actions) == set(attendues),
        "actions sans récepteur ou récepteur sans action : %r",
        sorted(set(actions) ^ set(attendues)),
    )
    verifier(
        echecs,
        len(actions) == len(set(actions)),
        "une action a deux récepteurs",
    )
    for valeur in table.value.values:
        verifier(
            echecs,
            isinstance(valeur, ast.Attribute),
            "récepteur qui n'est pas une méthode nommée : le contrôle de style "
            "et le banc ne le verraient pas",
        )

    return echecs, "%d récepteurs nommés" % len(actions)


def casNomTouche(mod, source):
    """Le nom composé suit le masque : Ctrl et Alt comptent, le reste non."""
    echecs = []
    app = monter(source)

    for titre, touche, modificateurs, attendu in (
        ("touche nue", KEY_M, NO_MODIFIER, "M"),
        ("avec Ctrl", KEY_Z, CONTROL_MODIFIER, "Ctrl+Z"),
        ("avec Alt", KEY_Z, ALT_MODIFIER, "Alt+Z"),
        (
            "Ctrl et Alt, ordre canonique",
            KEY_Z,
            CONTROL_MODIFIER | ALT_MODIFIER,
            "Ctrl+Alt+Z",
        ),
        # Comportement d'origine conservé : la cascade testait la présence de
        # Ctrl sans exclure les autres modificateurs.
        ("Maj effacée du masque", KEY_Z, CONTROL_MODIFIER | SHIFT_MODIFIER, "Ctrl+Z"),
        ("Maj seule effacée", KEY_M, SHIFT_MODIFIER, "M"),
        # Le « 1 » du pavé numérique doit désigner le même raccourci que celui
        # de la rangée des chiffres, sans quoi il devient inerte en silence.
        ("pavé numérique effacé", KEY_1, KEYPAD_MODIFIER, "1"),
        (
            "pavé numérique avec Ctrl",
            KEY_1,
            KEYPAD_MODIFIER | CONTROL_MODIFIER,
            "Ctrl+1",
        ),
        ("touche hors vocabulaire", KEY_F13, NO_MODIFIER, None),
    ):
        obtenu = app.nomTouche(EvenementClavierBouchon(touche, modificateurs))
        verifier(
            echecs,
            obtenu == attendu,
            "%s : %r au lieu de %r",
            titre,
            obtenu,
            attendu,
        )

    # Tout nom composé doit se relire : sans cela, une touche nommée par la
    # frontière ne se retrouverait pas dans une table lue du fichier.
    for touche, modificateurs in ((KEY_Z, CONTROL_MODIFIER), (KEY_M, NO_MODIFIER)):
        nom = app.nomTouche(EvenementClavierBouchon(touche, modificateurs))
        verifier(
            echecs,
            mod.normaliser(nom) == nom,
            "le nom composé %r n'est pas sous forme canonique",
            nom,
        )

    return echecs, "masque, ordre, pavé numérique"


def casRoutageParLaTable(mod, source):
    """Chaque touche affectée atteint son récepteur, et aucune autre ne bouge."""
    echecs = []
    app = monter(source)

    def frapper(touche, modificateurs=NO_MODIFIER, presse=True):
        app.appels = []
        evenement = EvenementClavierBouchon(touche, modificateurs, presse)
        app.keyboardHandler(evenement)
        return app.appels, evenement

    for titre, touche, modificateurs, attendu in (
        ("bascule de fenêtre", KEY_ESCAPE, NO_MODIFIER, ["bascule_fenetre"]),
        ("premier niveau de zoom", KEY_F5, NO_MODIFIER, ["zoom:0"]),
        ("dernier niveau de zoom", KEY_F12, NO_MODIFIER, ["zoom:7"]),
        (
            "outil Sélectionner",
            KEY_1,
            NO_MODIFIER,
            ["outil_selectionner:'selectionner'"],
        ),
        ("outil Ajouter", KEY_2, NO_MODIFIER, ["outil_ajouter:'ajouter'"]),
        ("outil Combiner", KEY_3, NO_MODIFIER, ["outil_combiner:'combiner'"]),
        ("outil Découper", KEY_4, NO_MODIFIER, ["outil_decouper:'decouper'"]),
        ("suivi du MNT", KEY_M, NO_MODIFIER, ["suivi_mnt"]),
        ("curseur libre", KEY_C, NO_MODIFIER, ["curseur_libre"]),
        ("annulation", KEY_Z, CONTROL_MODIFIER, ["annuler"]),
        ("enregistrement", KEY_S, CONTROL_MODIFIER, ["enregistrer"]),
    ):
        appels, evenement = frapper(touche, modificateurs)
        verifier(
            echecs,
            appels == attendu,
            "%s : %r au lieu de %r",
            titre,
            appels,
            attendu,
        )
        verifier(
            echecs,
            evenement.accepte == 1,
            "%s : l'événement devrait être accepté une fois",
            titre,
        )

    # Les modificateurs sont exigés là où ils l'étaient.
    for titre, touche in (("Z seul", KEY_Z), ("S seul", KEY_S)):
        appels, _ = frapper(touche, NO_MODIFIER)
        verifier(echecs, appels == [], "%s : ne devrait rien déclencher", titre)

    # Une touche sans affectation est inerte, mais l'événement est accepté :
    # c'est l'interception volontaire de la navigation, et elle ne dépend pas
    # du contenu de la table.
    appels, evenement = frapper(KEY_A, NO_MODIFIER)
    verifier(echecs, appels == [], "touche non affectée : ne devrait rien déclencher")
    verifier(
        echecs,
        evenement.accepte == 1,
        "touche non affectée : l'événement doit rester accepté",
    )

    appels, evenement = frapper(KEY_F13, NO_MODIFIER)
    verifier(echecs, appels == [], "touche hors vocabulaire : rien ne doit bouger")
    verifier(
        echecs,
        evenement.accepte == 1,
        "touche hors vocabulaire : l'événement doit rester accepté",
    )

    # Un relâchement de touche ne déclenche rien.
    appels, _ = frapper(KEY_ESCAPE, NO_MODIFIER, presse=False)
    verifier(echecs, appels == [], "relâchement de touche : ne devrait rien déclencher")

    # La bascule de tracé n'a pas de touche par défaut : rien ne doit la joindre.
    affectees = [action for action, _ in app.raccourcisInverses.values()]
    verifier(
        echecs,
        mod.ACTION_BASCULE_TRACE not in affectees,
        "la bascule de tracé ne devrait avoir aucune touche par défaut",
    )

    return echecs, "onze touches routées, gardes et silences"


def casRoutagePersonnalise(mod, source):
    """Le routage suit la table, et non les anciens littéraux.

    C'est le contrôle qui porte la tâche : un `elif event.key() == Qt.Key_M`
    oublié dans la cascade passerait tous les autres contrôles et tomberait
    sur celui-ci.
    """
    echecs = []
    app = monter(
        source,
        {
            "suivi_mnt": "Ctrl+M",
            "annuler": "F2",
            "curseur_libre": "",
            "bascule_trace": "A",
        },
    )

    def frapper(touche, modificateurs=NO_MODIFIER):
        app.appels = []
        app.keyboardHandler(EvenementClavierBouchon(touche, modificateurs))
        return app.appels

    for titre, touche, modificateurs, attendu in (
        ("suivi du MNT déplacé sur Ctrl+M", KEY_M, CONTROL_MODIFIER, ["suivi_mnt"]),
        ("ancienne touche du MNT devenue muette", KEY_M, NO_MODIFIER, []),
        ("annulation déplacée sur F2", KEY_F2, NO_MODIFIER, ["annuler"]),
        ("ancien raccourci d'annulation devenu muet", KEY_Z, CONTROL_MODIFIER, []),
        ("curseur libre désaffecté", KEY_C, NO_MODIFIER, []),
        ("bascule de tracé dotée d'une touche", KEY_A, NO_MODIFIER, ["bascule_trace"]),
        # Ce qui n'a pas été touché doit continuer de répondre.
        ("bascule de fenêtre inchangée", KEY_ESCAPE, NO_MODIFIER, ["bascule_fenetre"]),
        ("zoom inchangé", KEY_F5, NO_MODIFIER, ["zoom:0"]),
    ):
        appels = frapper(touche, modificateurs)
        verifier(
            echecs,
            appels == attendu,
            "%s : %r au lieu de %r",
            titre,
            appels,
            attendu,
        )

    # Une action sans récepteur ne doit pas lever, mais laisser une trace.
    app.tableRaccourcis.pop(mod.ACTION_BASCULE_FENETRE)
    app.journal.lignes = []
    try:
        app.keyboardHandler(EvenementClavierBouchon(KEY_ESCAPE))
    except Exception as souci:
        echecs.append("action sans récepteur : a levé %r" % souci)
    else:
        verifier(
            echecs,
            any("sans récepteur" in ligne for _, ligne in app.journal.lignes),
            "action sans récepteur : rien au journal",
        )

    return echecs, "table suivie, anciens littéraux muets"


def casCodesTouches(mod, source):
    """Les codes rendus pour un outil qui lit le clavier lui-même."""
    echecs = []

    app = monter(source)
    codes = app.codesTouches(mod.ACTION_BASCULE_FENETRE)
    verifier(
        echecs,
        codes == frozenset([KEY_ESCAPE]),
        "bascule par défaut : %r au lieu du seul code de la touche de bascule",
        codes,
    )

    verifier(
        echecs,
        app.codesTouches(mod.ACTION_BASCULE_TRACE) == frozenset(),
        "action sans touche : aucun code ne devrait sortir",
    )

    zoom = app.codesTouches(mod.ACTION_ZOOM)
    verifier(
        echecs,
        KEY_F5 in zoom and KEY_F12 in zoom,
        "groupe de zoom : les codes du premier et du dernier niveau devraient "
        "sortir, obtenu %d code(s)",
        len(zoom),
    )

    # Le modificateur est perdu pour cet usage, et c'est journalisé plutôt que
    # tu : un raccourci à modificateur répondra aussi sans lui dans cet état.
    app = monter(source, {"bascule_fenetre": "Ctrl+Échap"})
    app.journal.lignes = []
    codes = app.codesTouches(mod.ACTION_BASCULE_FENETRE)
    verifier(
        echecs,
        codes == frozenset([KEY_ESCAPE]),
        "bascule avec modificateur : %r au lieu du code de la touche seule",
        codes,
    )
    verifier(
        echecs,
        any("modificateur" in ligne for _, ligne in app.journal.lignes),
        "modificateur perdu : devrait être journalisé",
    )

    return echecs, "touche seule, groupe, modificateur perdu"


def casGardesPermanentes(mod, source):
    """Aucune touche ne revient en dur, ni dans le code ni dans un texte."""
    echecs = []

    # 1. La cascade littérale ne doit pas revenir.
    for fichier, methode in (
        ("stereoPhoto.py", "keyboardHandler"),
        ("horsSyncQgsMapTool.py", "keyPressEvent"),
    ):
        chemin = os.path.join(source, fichier)
        arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
        vise = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == methode
            ),
            None,
        )
        if vise is None:
            echecs.append("%s introuvable dans %s" % (methode, fichier))
            continue
        litterales = [
            n.attr
            for n in ast.walk(vise)
            if isinstance(n, ast.Attribute) and n.attr.startswith("Key_")
        ]
        verifier(
            echecs,
            not litterales,
            "%s compare encore des touches de Qt en dur : %r",
            methode,
            litterales,
        )

    # 2. Aucun texte montré ne nomme une touche.
    motif = motifTouchesEnDur(mod.TOUCHES_CONNUES)
    for fichier in FICHIERS_SANS_TOUCHE:
        chemin = os.path.join(source, fichier)
        if fichier.endswith(".ui"):
            contenu = io.open(chemin, encoding="utf-8").read()
            fautifs = [ligne for ligne in contenu.split("\n") if motif.search(ligne)]
        else:
            fautifs = [
                texte for texte in _constantes_de_fichier(chemin) if motif.search(texte)
            ]
        verifier(
            echecs,
            not fautifs,
            "%s nomme une touche en littéral : %r",
            fichier,
            fautifs[:3],
        )

    # 3. La section doit être posée dans le fichier de paramètres, sans quoi
    #    l'utilisateur d'un fichier antérieur ne la verrait jamais apparaître.
    chemin = os.path.join(source, "stereoPhoto.py")
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    run = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "run"
        ),
        None,
    )
    if run is None:
        echecs.append("run introuvable")
    else:
        pose = [
            n
            for n in ast.walk(run)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "setdefault"
            and any(
                isinstance(a, ast.Attribute) and a.attr == "CLE_SECTION" for a in n.args
            )
        ]
        verifier(
            echecs,
            pose,
            "run() ne pose pas la section des raccourcis dans les paramètres",
        )

    # 4. La table doit être relue à l'ouverture d'une session, sans quoi une
    #    touche modifiée exigerait de recharger l'extension.
    for methode in ("initGui", "run"):
        vise = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == methode
            ),
            None,
        )
        lectures = [
            n
            for n in ast.walk(vise)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "chargerRaccourcis"
        ]
        verifier(
            echecs,
            lectures,
            "%s ne lit pas la table des raccourcis",
            methode,
        )

    return echecs, "cascade, textes, section, relecture"


# Les cas, dans l'ordre d'exécution. Le troisième élément nomme ce que le cas
# reçoit en plus du module testé : « source » le dossier des sources, « outils »
# et « config » les deux modules purs croisés.
CAS = (
    ("conformité de la table", casTableConforme, None),
    ("ordre de départage déclaré", casActionsDeclarees, None),
    ("outils d'édition croisés", casActionsOutil, "outils"),
    ("cohérence des défauts", casDefautsCoherents, "config"),
    ("section livrée dans le fichier", casFichierLivre, "source"),
    ("section rendue aux appelants", casSectionParDefaut, None),
    ("normalisation des écritures", casNormalisation, None),
    ("raison d'un refus", casRaisonDuRefus, None),
    ("replis d'un fichier mal écrit", casReplis, None),
    ("table inverse", casTableInverse, None),
    ("lecture du fichier", casLecture, None),
    ("annonce des touches", casAnnonces, None),
    ("traduction vers les touches de Qt", casFrontiereQt, "source"),
    ("récepteurs des actions", casTableDesRecepteurs, "source"),
    ("composition du nom d'une touche", casNomTouche, "source"),
    ("routage par la table", casRoutageParLaTable, "source"),
    ("routage d'une table personnalisée", casRoutagePersonnalise, "source"),
    ("codes rendus hors synchronisation", casCodesTouches, "source"),
    ("gardes permanentes", casGardesPermanentes, "source"),
)


def executer(source):
    sys.path.insert(0, source)
    import config
    import editionOutils
    import raccourcisClavier as mod

    print("Modules testés : %s" % source)
    print()

    supplements = {"source": source, "outils": editionOutils, "config": config}

    total = []
    for libelle, fonction, supplement in CAS:
        arguments = (mod,) if supplement is None else (mod, supplements[supplement])
        echecs, note = fonction(*arguments)
        total.extend(echecs)
        print("%-6s %-44s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) relevé(s)." % len(total))
        return 1
    print("Les raccourcis suivent la table, et aucun fichier ne la fait lever.")
    return 0


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    sys.exit(executer(source))
