# -*- coding: utf-8 -*-
"""Garde sur l'altitude du curseur confrontée au MNT au chargement d'une paire.

La position de la dernière vue est écrite dans le fichier de paramètres et
restaurée à l'ouverture du dossier. `setInitialCursorAltitude()` la préfère au
MNT : son altitude revenait donc à chaque ouverture, quel que soit le terrain
sous la paire chargée, et rien ne la confrontait au sol.

Mesuré à l'usage : altitude du curseur à 45 m pour un terrain à 487 m. La
croix est projetée dans les vues photo à l'altitude du curseur, alors que les
géométries le sont à celle du MNT. Les deux se séparent alors à l'écran du
déplacement dû au relief, qui vaut la distance au nadir multipliée par l'écart
d'altitude et divisée par la hauteur de vol. Sur cette paire, 442 m d'écart
pour 4900 m de hauteur de vol : neuf pour cent de la distance au nadir, soit
30 m au sol à 330 m du nadir et 90 m à un kilomètre.

Ce n'est pas qu'un défaut d'affichage. La coordonnée écrite est celle du
curseur de QGIS, juste par construction ; c'est la croix des vues photo qui
est déplacée. Le photo-interprète qui vise une entité dans la photo saisit donc
une position fausse d'autant, sans que rien ne le signale.

`accorderAltitudeAuTerrain()` est extraite du fichier source par analyse
syntaxique, puis exécutée avec des bouchons : aucune dépendance à QGIS ni à Qt
n'est nécessaire. Le seuil est lu dans `config.py`, et non recopié ici : un
seuil changé d'un côté seulement ferait échouer les cas de frontière.

Usage :
    python tests/test_altitude_accordee_mnt.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

METHODE = "accorderAltitudeAuTerrain"
CONSTANTE = "NAVIGATION_ECART_ALTITUDE_MNT_MAX_M"

# Valeurs du secteur de test de la DIF, relevées en session : la paire
# q16033_052 / q16033_053 et le MNT du MERN.
ALTITUDE_SOL = 487.38
ALTITUDE_HERITEE = 45.35
CENTRE_DECOUPE = (7000.0, 7000.0)
COORD_CENTRE = (379785.2, 5391566.7)
COORD_VUE_MEMORISEE = (380100.0, 5391200.0)


def lire(chemin):
    return io.open(chemin, encoding="utf-8").read()


def extraire_methode(chemin, classe_visee, methode_visee, espace):
    """Retourne une méthode d'une classe, isolée de son module."""
    arbre = ast.parse(lire(chemin))
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
            "méthode %s introuvable dans %s" % (methode_visee, classe_visee)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return espace[methode_visee]


def lire_constante(chemin, nom):
    """Valeur d'une constante de module, prise au fichier et non recopiée."""
    for noeud in ast.parse(lire(chemin)).body:
        if isinstance(noeud, ast.Assign) and isinstance(noeud.value, ast.Constant):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id == nom:
                    return noeud.value.value
    raise AssertionError("constante %s introuvable dans %s" % (nom, chemin))


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


class OptWindowBouchon:
    """Le panneau réduit à la lecture du MNT, et au relevé de l'endroit lu."""

    def __init__(self, altitudeSol, mntCharge=True, nodata=-9999.0):
        self.mntArr = object() if mntCharge else None
        self.mntNodata = nodata
        self.altitudeSol = altitudeSol
        self.positionsLues = []

    def readMNTWithCoord(self, position):
        self.positionsLues.append(tuple(position))
        return self.altitudeSol


class ManagerBouchon:
    """Projection d'un pixel vers le sol, réduite à ce que la méthode demande."""

    def __init__(self):
        self.appels = []

    def pixelToCoord(self, pixel, altitude):
        self.appels.append((tuple(pixel), altitude))
        return COORD_CENTRE


class ApplicationBouchon:
    def __init__(self, altitudeCurseur, altitudeSol, mntCharge=True, vueMemorisee=()):
        self.journal = JournalBouchon()
        self.cursorAltitude = altitudeCurseur
        self.lastCurrentView = vueMemorisee
        self.optWindow = OptWindowBouchon(altitudeSol, mntCharge)
        self.leftPictureManager = ManagerBouchon()
        self.leftParID = "q16033_053_rgb"


def verifier(libelle, echecs, controle):
    try:
        controle()
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    except Exception as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s : %s" % (libelle, type(erreur).__name__, erreur))
    else:
        print("OK     %-52s" % libelle)


def executer(dossier_source):
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    chemin_config = os.path.join(dossier_source, "config.py")
    echecs = []

    seuil = lire_constante(chemin_config, CONSTANTE)
    accorder = extraire_methode(
        chemin_app,
        "stereoPhoto",
        METHODE,
        {CONSTANTE: seuil, "__builtins__": __builtins__},
    )

    # --- L'altitude héritée d'une autre session est ramenée au terrain ------
    def altitude_heritee_corrigee():
        app = ApplicationBouchon(ALTITUDE_HERITEE, ALTITUDE_SOL)
        accorder(app, CENTRE_DECOUPE)

        assert app.cursorAltitude == ALTITUDE_SOL, (
            "altitude restée à %s au lieu d'être ramenée à %s"
            % (app.cursorAltitude, ALTITUDE_SOL)
        )
        avertissements = [m for n, m in app.journal.messages if n == "warning"]
        assert len(avertissements) == 1, (
            "%d avertissement(s) au journal, un seul attendu" % len(avertissements)
        )
        assert "442" in avertissements[0], (
            "l'écart n'est pas chiffré dans la trace : %r" % avertissements[0]
        )

    verifier(
        "Altitude héritée loin du terrain : ramenée au MNT",
        echecs,
        altitude_heritee_corrigee,
    )

    # --- Un écart sous le seuil est le fait du photo-interprète -------------
    def ecart_sous_le_seuil_conserve():
        depart = ALTITUDE_SOL - (seuil / 2.0)
        app = ApplicationBouchon(depart, ALTITUDE_SOL)
        accorder(app, CENTRE_DECOUPE)

        assert app.cursorAltitude == depart, (
            "altitude modifiée pour %s m d'écart, sous le seuil de %s m"
            % (seuil / 2.0, seuil)
        )
        assert not app.journal.messages, (
            "trace au journal pour un écart toléré : %r" % (app.journal.messages,)
        )

    verifier(
        "Écart sous le seuil : altitude conservée, sans trace",
        echecs,
        ecart_sous_le_seuil_conserve,
    )

    # --- La frontière appartient au photo-interprète ------------------------
    def ecart_egal_au_seuil_conserve():
        depart = ALTITUDE_SOL - seuil
        app = ApplicationBouchon(depart, ALTITUDE_SOL)
        accorder(app, CENTRE_DECOUPE)

        assert app.cursorAltitude == depart, (
            "altitude modifiée pour un écart exactement égal au seuil de %s m" % seuil
        )

    verifier(
        "Écart égal au seuil : altitude conservée",
        echecs,
        ecart_egal_au_seuil_conserve,
    )

    # --- Sans MNT, il n'y a rien à confronter -------------------------------
    def sans_mnt_rien_a_confronter():
        app = ApplicationBouchon(ALTITUDE_HERITEE, ALTITUDE_SOL, mntCharge=False)
        accorder(app, CENTRE_DECOUPE)

        assert app.cursorAltitude == ALTITUDE_HERITEE, (
            "altitude modifiée sans MNT chargé : %s" % app.cursorAltitude
        )
        assert not app.optWindow.positionsLues, (
            "le MNT est lu alors qu'il n'est pas chargé"
        )

    verifier(
        "Aucun MNT chargé : la mesure de parallaxe garde le dernier mot",
        echecs,
        sans_mnt_rien_a_confronter,
    )

    # --- Altitude indéterminée et MNT sans valeur ---------------------------
    def valeurs_absentes_laissees_telles():
        app = ApplicationBouchon(None, ALTITUDE_SOL)
        accorder(app, CENTRE_DECOUPE)
        assert app.cursorAltitude is None, (
            "altitude indéterminée remplacée par %s" % app.cursorAltitude
        )

        app = ApplicationBouchon(ALTITUDE_HERITEE, None)
        accorder(app, CENTRE_DECOUPE)
        assert app.cursorAltitude == ALTITUDE_HERITEE, (
            "altitude modifiée alors que le MNT ne rend rien"
        )

        app = ApplicationBouchon(ALTITUDE_HERITEE, -9999.0)
        accorder(app, CENTRE_DECOUPE)
        assert app.cursorAltitude == ALTITUDE_HERITEE, (
            "la valeur d'absence du MNT a été prise pour une altitude"
        )

    verifier(
        "Altitude ou MNT sans valeur : rien n'est corrigé",
        echecs,
        valeurs_absentes_laissees_telles,
    )

    # --- Le MNT est lu là où la vue va se poser -----------------------------
    def position_lue_suit_la_vue():
        app = ApplicationBouchon(
            ALTITUDE_HERITEE,
            ALTITUDE_SOL,
            vueMemorisee=COORD_VUE_MEMORISEE + (ALTITUDE_HERITEE, 1.0),
        )
        accorder(app, CENTRE_DECOUPE)
        assert app.optWindow.positionsLues == [COORD_VUE_MEMORISEE], (
            "le MNT est lu en %r au lieu de la position mémorisée %r"
            % (app.optWindow.positionsLues, COORD_VUE_MEMORISEE)
        )
        assert not app.leftPictureManager.appels, (
            "le centre de la découpe est projeté alors qu'une vue est mémorisée"
        )

        app = ApplicationBouchon(ALTITUDE_HERITEE, ALTITUDE_SOL)
        accorder(app, CENTRE_DECOUPE)
        assert app.leftPictureManager.appels == [(CENTRE_DECOUPE, ALTITUDE_HERITEE)], (
            "sans vue mémorisée, le centre de la découpe n'est pas projeté : %r"
            % (app.leftPictureManager.appels,)
        )
        assert app.optWindow.positionsLues == [COORD_CENTRE], (
            "le MNT n'est pas lu au centre du modèle : %r"
            % (app.optWindow.positionsLues,)
        )

    verifier(
        "Le MNT est lu là où la vue va se poser",
        echecs,
        position_lue_suit_la_vue,
    )

    # --- La confrontation a bien lieu au chargement de la paire -------------
    def appelee_au_chargement():
        source = lire(chemin_app)
        arbre = ast.parse(source)
        amont = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef)
                and n.name == "setInitialCursorAltitude"
            ),
            None,
        )
        assert amont is not None, "setInitialCursorAltitude introuvable"
        extrait = ast.get_source_segment(source, amont) or ""
        assert METHODE in extrait, (
            "setInitialCursorAltitude ne confronte pas l'altitude au terrain : "
            "la cascade rendrait de nouveau la vue mémorisée sans contrôle"
        )

        lignes = extrait.splitlines()
        rang_accord = next(i for i, ligne in enumerate(lignes) if METHODE in ligne)
        rang_affichage = next(
            (i for i, ligne in enumerate(lignes) if "afficherAltitude" in ligne), None
        )
        assert rang_affichage is not None, "l'altitude n'est plus portée au panneau"
        assert rang_accord < rang_affichage, (
            "le panneau affiche l'altitude avant qu'elle soit corrigée"
        )

    verifier(
        "Confrontation posée dans la cascade, avant l'affichage",
        echecs,
        appelee_au_chargement,
    )

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nL'altitude du curseur est confrontée au terrain sous la paire.")
