# -*- coding: utf-8 -*-
"""Test de la zone sûre du piège à souris (navigation synchronisée, EF-03).

Le piège à souris ne recentre le curseur que lorsqu'il sort de la zone sûre.
Avec une marge fixe de 150 px, cette zone exigeait un canevas de plus de 300 px
de côté : remplie au poste de stéréoscopie, la condition tombe sur un canevas
réduit par les panneaux latéraux, et la zone dégénérait en rectangle vide.
PyQt5 rendant un QRect vide faux, la garde booléenne de `eventFilter()` cessait
alors de laisser passer le recentrage — sans que rien ne le signale. Le curseur
n'était donc plus jamais ramené au centre, et sa course se limitait à la taille
du canevas : mesuré à 98 x 28 px en session sur un poste à un seul écran, ce
qui rend la navigation impraticable.

Le test couvre les trois pièces de la correction :

1. `margeZoneSure()` — la marge suit une part de la dimension du canevas,
   bornée en pixels, et reste à 150 px sur un grand canevas.
2. `updateSafeZone()` — la zone est mise à None sous le côté minimal, et
   rétablie dès que le canevas grandit.
3. L'avertissement est porté au bandeau de QGIS, une seule fois par transition,
   avec les dimensions du canevas et la marche à suivre : la condition demande
   une action de l'utilisateur, et le journal n'est pas consulté en cours de
   photo-interprétation. Le rétablissement, lui, reste au journal.
4. `avertirZoneSureLevee()` — l'avertissement est différé par une minuterie que
   `updateSafeZone()` relance à chaque recalcul : le canevas passe par des
   tailles minuscules au montage de la fenêtre de QGIS et pendant le
   déplacement d'un panneau, et ces états de passage n'ont pas à encombrer le
   bandeau. Un canevas agrandi avant l'échéance n'avertit donc jamais.

Les deux méthodes sont extraites du fichier source par analyse syntaxique, puis
exécutées avec des bouchons : aucune dépendance à QGIS ni à Qt n'est
nécessaire. Les constantes sont lues dans `config.py` de la même façon, afin
que le test suive un réglage modifié.

Usage :
    python tests/test_zone_sure.py [chemin/vers/src]

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
            "méthode(s) %s introuvable(s) dans %s"
            % (", ".join(sorted(manquantes)), chemin)
        )

    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)

    extraites = {}
    for nom in methodes_visees:
        fonction = espace[nom]
        # Les décorateurs sont conservés par l'extraction : une méthode statique
        # arrive ici sous la forme d'un objet staticmethod.
        extraites[nom] = getattr(fonction, "__func__", fonction)
    return extraites


def lire_constantes(chemin, prefixe):
    """Retourne les constantes littérales d'un module dont le nom a ce préfixe."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    valeurs = {}
    for noeud in arbre.body:
        if not isinstance(noeud, ast.Assign):
            continue
        for cible in noeud.targets:
            if isinstance(cible, ast.Name) and cible.id.startswith(prefixe):
                valeurs[cible.id] = ast.literal_eval(noeud.value)
    return valeurs


class PointBouchon:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class RectBouchon:
    """Remplace QRect : seules les opérations du calcul de la zone sont là."""

    def __init__(self, largeur, hauteur, gauche=0, haut=0):
        self._largeur, self._hauteur = largeur, hauteur
        self._gauche, self._haut = gauche, haut

    def width(self):
        return self._largeur

    def height(self):
        return self._hauteur

    def adjusted(self, dGauche, dHaut, dDroite, dBas):
        return RectBouchon(
            self._largeur - dGauche + dDroite,
            self._hauteur - dHaut + dBas,
            self._gauche + dGauche,
            self._haut + dHaut,
        )

    def center(self):
        return PointBouchon(
            self._gauche + self._largeur // 2, self._haut + self._hauteur // 2
        )


class ViewportBouchon:
    def __init__(self, rect):
        self._rect = rect

    def rect(self):
        return self._rect

    def mapToGlobal(self, point):
        return point


class CanevasBouchon:
    def __init__(self, largeur, hauteur):
        self.redimensionner(largeur, hauteur)

    def redimensionner(self, largeur, hauteur):
        self.vue = ViewportBouchon(RectBouchon(largeur, hauteur))

    def viewport(self):
        return self.vue


class JournalBouchon:
    """Retient le niveau de chaque message, sans rien écrire."""

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

    def niveaux(self, niveau):
        return [message for message in self.messages if message[0] == niveau]


class BandeauBouchon:
    """Remplace avertir_utilisateur() : relève les messages et leur durée."""

    def __init__(self):
        self.messages = []

    def __call__(self, message, niveau=logging.WARNING, duree_secondes=8):
        self.messages.append((niveau, message, duree_secondes))


class MinuterieBouchon:
    """Remplace le QTimer de l'alerte : retient l'état et le dernier délai.

    Le déclenchement n'est pas simulé par le bouchon : le test appelle
    `avertirZoneSureLevee()` lui-même, ce qui permet de vérifier aussi bien
    l'échéance atteinte que la minuterie arrêtée avant son terme.
    """

    def __init__(self):
        self.active = False
        self.delai = None
        self.departs = 0

    def start(self, delai):
        self.active = True
        self.delai = delai
        self.departs += 1

    def stop(self):
        self.active = False

    def isActive(self):
        return self.active


class OutilBouchon:
    """Porte les seuls attributs que `updateSafeZone()` lit et écrit."""

    def __init__(self, canvas, margeZoneSure):
        self.canvas = canvas
        self.safeRect = None
        self.zoneSureLevee = False
        self.centerGlobalPos = None
        self.margeZoneSure = margeZoneSure
        self.minuterieAlerteZoneSure = MinuterieBouchon()
        self.alerteZoneSureAffichee = False


def cas_marges(chemin_outil, constantes):
    """La marge suit la dimension du canevas, entre ses deux bornes."""
    espace = dict(constantes)
    margeZoneSure = extraire_methodes(
        chemin_outil, "navigationMapTool", ["margeZoneSure"], espace
    )["margeZoneSure"]

    ratio = constantes["NAVIGATION_ZONE_SURE_MARGE_RATIO"]
    minimum = constantes["NAVIGATION_ZONE_SURE_MARGE_MIN_PX"]
    maximum = constantes["NAVIGATION_ZONE_SURE_MARGE_MAX_PX"]

    scenarios = [
        ("grand canevas plafonné à la marge d'origine", 1920, maximum),
        ("canevas moyen proportionnel", 600, int(600 * ratio)),
        ("petit canevas proportionnel", 300, int(300 * ratio)),
        ("canevas minuscule au plancher", 50, minimum),
        ("canevas de dimension nulle au plancher", 0, minimum),
    ]

    echecs = []
    for libelle, dimension, attendu in scenarios:
        try:
            obtenu = margeZoneSure(dimension)
            assert obtenu == attendu, "%d px attendus, %d obtenus" % (attendu, obtenu)
            assert minimum <= obtenu <= maximum, "marge hors bornes : %d px" % obtenu
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-52s %s" % (libelle, erreur))
        else:
            print("OK     %-52s %d px" % (libelle, obtenu))

    return echecs


def cas_zone(chemin_outil, constantes):
    """La zone est utilisable là où la marge fixe la faisait dégénérer."""
    espace = dict(constantes)
    journal = JournalBouchon()
    bandeau = BandeauBouchon()
    espace["journal"] = journal
    espace["avertir_utilisateur"] = bandeau
    methodes = extraire_methodes(
        chemin_outil,
        "navigationMapTool",
        ["margeZoneSure", "updateSafeZone", "avertirZoneSureLevee"],
        espace,
    )
    margeZoneSure = methodes["margeZoneSure"]
    updateSafeZone = methodes["updateSafeZone"]
    avertirZoneSureLevee = methodes["avertirZoneSureLevee"]
    coteMin = constantes["NAVIGATION_ZONE_SURE_COTE_MIN_PX"]
    delai = constantes["NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS"]

    echecs = []

    # Les trois dernières tailles donnaient une zone vide ou négative avec la
    # marge fixe de 150 px.
    for largeur, hauteur in [(1920, 1080), (600, 400), (320, 300), (300, 200)]:
        libelle = "zone utilisable sur un canevas de %dx%d" % (largeur, hauteur)
        outil = OutilBouchon(CanevasBouchon(largeur, hauteur), margeZoneSure)
        try:
            updateSafeZone(outil)
            assert outil.safeRect is not None, "zone levée alors qu'elle est utilisable"
            assert outil.safeRect.width() >= coteMin, (
                "largeur de zone de %d px" % outil.safeRect.width()
            )
            assert outil.safeRect.height() >= coteMin, (
                "hauteur de zone de %d px" % outil.safeRect.height()
            )
            assert not outil.zoneSureLevee, "drapeau de zone levée posé à tort"
            assert outil.centerGlobalPos is not None, "centre du canevas non calculé"
        except AssertionError as erreur:
            echecs.append((libelle, erreur))
            print("ECHEC  %-52s %s" % (libelle, erreur))
        else:
            print(
                "OK     %-52s %dx%d"
                % (libelle, outil.safeRect.width(), outil.safeRect.height())
            )

    # Canevas trop petit pour toute zone : le piège est levé tout de suite, mais
    # l'alerte attend l'échéance de la minuterie — la disposition de la fenêtre
    # de QGIS n'est pas encore stabilisée au premier calcul.
    libelle = "piège levé : alerte armée, bandeau encore vide"
    outil = OutilBouchon(CanevasBouchon(100, 80), margeZoneSure)
    del journal.messages[:]
    del bandeau.messages[:]
    try:
        updateSafeZone(outil)
        assert outil.safeRect is None, "zone conservée alors qu'elle est inutilisable"
        assert outil.zoneSureLevee, "drapeau de zone levée non posé"
        assert bandeau.messages == [], "alerte immédiate : %r" % (bandeau.messages,)
        assert outil.minuterieAlerteZoneSure.isActive(), "minuterie non armée"
        assert outil.minuterieAlerteZoneSure.delai == delai, (
            "délai %r au lieu de %r" % (outil.minuterieAlerteZoneSure.delai, delai)
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s %d ms" % (libelle, delai))

    # Échéance atteinte sur un canevas resté petit : la condition est portée au
    # bandeau de QGIS, elle demande une action de l'utilisateur.
    libelle = "échéance atteinte : avertissement au bandeau de QGIS"
    try:
        avertirZoneSureLevee(outil)
        assert len(bandeau.messages) == 1, "%d message(s) au bandeau" % len(
            bandeau.messages
        )
        niveau, message, duree = bandeau.messages[0]
        assert niveau >= logging.WARNING, "niveau %r" % (niveau,)
        assert "100x80" in message, "les dimensions du canevas ne sont pas nommées"
        assert "Agrandir" in message, "le message ne dit pas quoi faire"
        assert duree == 0, "durée %r : le message doit rester jusqu'à sa fermeture" % (
            duree,
        )

        # Deuxième calcul sans changement, puis seconde échéance : le message
        # ne doit pas se répéter tant que le canevas n'a pas grandi.
        updateSafeZone(outil)
        avertirZoneSureLevee(outil)
        assert len(bandeau.messages) == 1, "message répété : %d" % len(bandeau.messages)
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Taille de passage, celle du montage de la fenêtre ou d'un panneau en cours
    # de déplacement : le canevas est agrandi avant l'échéance, et rien n'est
    # porté au bandeau même si la minuterie arrive malgré tout à son terme.
    libelle = "taille de passage : aucune alerte après l'agrandissement"
    passage = OutilBouchon(CanevasBouchon(98, 28), margeZoneSure)
    del journal.messages[:]
    del bandeau.messages[:]
    try:
        updateSafeZone(passage)
        assert passage.minuterieAlerteZoneSure.isActive(), "minuterie non armée"
        passage.canvas.redimensionner(1600, 1200)
        updateSafeZone(passage)
        assert not passage.minuterieAlerteZoneSure.isActive(), (
            "minuterie encore armée sur un canevas redevenu grand"
        )
        avertirZoneSureLevee(passage)
        assert bandeau.messages == [], "alerte sur un état de passage : %r" % (
            bandeau.messages,
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    # Le canevas grandit : la zone revient. Le rétablissement reste au journal,
    # l'utilisateur venant d'agrandir le canevas lui-même.
    libelle = "piège rétabli : trace au journal, pas au bandeau"
    del journal.messages[:]
    del bandeau.messages[:]
    try:
        outil.canvas.redimensionner(1600, 1200)
        updateSafeZone(outil)
        assert outil.safeRect is not None, "zone non rétablie"
        assert not outil.zoneSureLevee, "drapeau de zone levée non retiré"
        assert not outil.alerteZoneSureAffichee, (
            "alerte toujours tenue pour affichée : une dégradation ultérieure "
            "ne serait plus signalée"
        )
        assert len(journal.niveaux("info")) == 1, "%d trace(s) de rétablissement" % len(
            journal.niveaux("info")
        )
        assert bandeau.messages == [], "le rétablissement encombre le bandeau : %r" % (
            bandeau.messages,
        )
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)

    return echecs


def executer(dossier_source):
    chemin_outil = os.path.join(dossier_source, "navigationQgsMapTool.py")
    chemin_config = os.path.join(dossier_source, "config.py")
    constantes = lire_constantes(chemin_config, "NAVIGATION_ZONE_SURE_")

    attendues = {
        "NAVIGATION_ZONE_SURE_MARGE_RATIO",
        "NAVIGATION_ZONE_SURE_MARGE_MIN_PX",
        "NAVIGATION_ZONE_SURE_MARGE_MAX_PX",
        "NAVIGATION_ZONE_SURE_COTE_MIN_PX",
        "NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS",
    }
    manquantes = attendues - set(constantes)
    if manquantes:
        raise AssertionError(
            "constante(s) absente(s) de config.py : %s" % ", ".join(sorted(manquantes))
        )

    echecs = cas_marges(chemin_outil, constantes)
    echecs += cas_zone(chemin_outil, constantes)
    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nLa zone sûre tient sur un petit canevas et le piège se lève au besoin.")
