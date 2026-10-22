# -*- coding: utf-8 -*-
"""Test de l'ouverture des rasters sous les deux conventions d'erreur de GDAL.

`gdal.Open()` signale un fichier illisible en retournant `None` quand
`gdal.UseExceptions()` est désactivé, et en levant `RuntimeError` quand il est
activé. QGIS 3.44 l'active, l'exécution hors de QGIS ne l'active pas, et
GDAL 4.0 l'activera partout. Une garde posée sur une seule des deux conventions
est donc inerte dans l'autre : c'est ce qui laissait, en session QGIS, un
dossier contenant une seule image corrompue sans aucune paire, et un MNT
illisible interrompre le chargement d'une paire, sans trace au journal.

Deux choses sont vérifiées ici :

- le comportement de `ouvrir_raster()` sous les deux conventions, la fonction
  étant extraite par analyse syntaxique et exécutée avec des bouchons ;
- la garde permanente : aucun des quatre sites qui ouvrent un raster n'appelle
  `gdal.Open()` directement, et la lecture du MNT efface bien la fenêtre du MNT
  précédent lorsqu'elle échoue.

Usage :
    python tests/test_lecture_raster.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Les quatre endroits qui ouvrent un raster, et la fonction qui les porte.
SITES = (
    ("gestionDossier.py", "getParDict"),
    ("ui_widgetStereoPhoto.py", "getMNTWithCoord"),
    ("enhanceManager.py", "__init__"),
    ("drawFunction.py", "run"),
)


def extraire_fonctions(chemin, noms, espace):
    """Exécute les fonctions nommées d'un module, isolées de leurs imports."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    corps = [n for n in arbre.body if isinstance(n, ast.FunctionDef) and n.name in noms]
    manquantes = set(noms) - {n.name for n in corps}
    if manquantes:
        raise AssertionError(
            "fonction(s) %s introuvable(s) dans %s"
            % (", ".join(sorted(manquantes)), chemin)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in noms}


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


class GdalBouchon:
    """Remplace le module gdal : Open() joue la convention demandée."""

    GA_ReadOnly = 0

    def __init__(self, resultat):
        # resultat : un dataset bouchon, None, ou une exception à lever.
        self.resultat = resultat
        self.appels = []

    def Open(self, chemin, mode):
        self.appels.append((chemin, mode))
        if isinstance(self.resultat, BaseException):
            raise self.resultat
        return self.resultat


def preparer(dossier_source, resultat):
    """Monte ouvrir_raster() et motif_echec() avec leurs bouchons."""
    chemin = os.path.join(dossier_source, "lectureRaster.py")
    journal = JournalBouchon()
    gdal = GdalBouchon(resultat)
    espace = {"gdal": gdal, "_journal": journal}
    fonctions = extraire_fonctions(chemin, ("ouvrir_raster", "motif_echec"), espace)
    return fonctions, journal, gdal


def verifier(libelle, echecs, controle):
    try:
        controle()
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
    else:
        print("OK     %-52s" % libelle)


def executer(dossier_source):
    echecs = []
    chemin_lecture = os.path.join(dossier_source, "lectureRaster.py")

    # Rejoué sur une version d'avant le correctif, l'utilitaire est absent :
    # on le dit plutôt que de laisser remonter une FileNotFoundError, et on
    # passe directement aux gardes structurelles, qui restent parlantes.
    if not os.path.exists(chemin_lecture):
        libelle = "lectureRaster.py présent"
        erreur = AssertionError("module absent de %s" % dossier_source)
        echecs.append((libelle, erreur))
        print("ECHEC  %-52s %s" % (libelle, erreur))
        return echecs + executer_gardes(dossier_source)

    # --- Convention « exceptions désactivées » : Open() retourne None --------
    def sans_exception():
        fonctions, journal, gdal = preparer(dossier_source, None)
        assert fonctions["ouvrir_raster"]("/photos/q16047_336_rgb.tif") is None, (
            "un retour None de gdal.Open() doit donner None"
        )
        avertissements = [m for n, m in journal.messages if n == "warning"]
        assert len(avertissements) == 1, "%d avertissement(s)" % len(avertissements)
        assert "q16047_336_rgb.tif" in avertissements[0], (
            "l'avertissement ne nomme pas le fichier : %r" % avertissements[0]
        )

    verifier("Retour None de GDAL : None rendu, fichier nommé", echecs, sans_exception)

    # --- Convention « exceptions activées » : Open() lève RuntimeError -------
    def avec_exception():
        erreur = RuntimeError(
            "q16047_336_rgb.tif: TIFFReadDirectory:Failed to read directory\n"
            "May be caused by: Can not read TIFF directory count"
        )
        fonctions, journal, gdal = preparer(dossier_source, erreur)
        assert fonctions["ouvrir_raster"]("/photos/q16047_336_rgb.tif") is None, (
            "un RuntimeError de gdal.Open() doit donner None, non se propager"
        )
        avertissements = [m for n, m in journal.messages if n == "warning"]
        assert len(avertissements) == 1, "%d avertissement(s)" % len(avertissements)
        assert "q16047_336_rgb.tif" in avertissements[0], (
            "l'avertissement ne nomme pas le fichier : %r" % avertissements[0]
        )
        assert "May be caused by" not in avertissements[0], (
            "les causes empilées de GDAL ne doivent pas inonder le journal"
        )

    verifier("RuntimeError de GDAL : None rendu, non propagé", echecs, avec_exception)

    # --- Succès : le dataset est rendu, le journal reste muet ----------------
    def succes():
        jeu = object()
        fonctions, journal, gdal = preparer(dossier_source, jeu)
        assert fonctions["ouvrir_raster"]("/photos/q16047_335_rgb.tif") is jeu, (
            "le dataset doit être rendu tel quel"
        )
        assert journal.messages == [], "journal non muet : %r" % (journal.messages,)
        assert gdal.appels == [("/photos/q16047_335_rgb.tif", gdal.GA_ReadOnly)], (
            "ouverture demandée : %r" % (gdal.appels,)
        )

    verifier("Succès : dataset rendu, aucun avertissement", echecs, succes)

    # --- Toute autre exception remonte à l'appelant --------------------------
    def autre_exception():
        fonctions, journal, gdal = preparer(dossier_source, MemoryError("mémoire"))
        try:
            fonctions["ouvrir_raster"]("/photos/q16047_335_rgb.tif")
        except MemoryError:
            return
        raise AssertionError(
            "une exception étrangère à l'ouverture ne doit pas être absorbée"
        )

    verifier("Exception étrangère : remonte à l'appelant", echecs, autre_exception)

    # --- motif_echec() ne garde que la première ligne ------------------------
    def motif():
        fonctions, _, _ = preparer(dossier_source, None)
        motif_echec = fonctions["motif_echec"]
        assert motif_echec(RuntimeError("une cause\nune autre")) == "une cause", (
            "seule la première ligne est retenue"
        )
        assert motif_echec(RuntimeError("")) == "RuntimeError", (
            "un message vide laisse place au nom de l'exception"
        )

    verifier("motif_echec() : première ligne seulement", echecs, motif)

    return echecs + executer_gardes(dossier_source)


def executer_gardes(dossier_source):
    """Gardes structurelles : elles valent aussi sur une version sans
    l'utilitaire, et disent alors ce qui manque.
    """
    echecs = []

    # --- Garde permanente : aucun appel direct à gdal.Open() hors utilitaire -
    def aucun_appel_direct():
        fautifs = []
        for fichier, _fonction in SITES:
            source = io.open(
                os.path.join(dossier_source, fichier), encoding="utf-8"
            ).read()
            arbre = ast.parse(source)
            for noeud in ast.walk(arbre):
                if (
                    isinstance(noeud, ast.Attribute)
                    and noeud.attr == "Open"
                    and isinstance(noeud.value, ast.Name)
                    and noeud.value.id == "gdal"
                ):
                    fautifs.append("%s l.%d" % (fichier, noeud.lineno))
        assert not fautifs, "gdal.Open() appelé directement : %s" % ", ".join(fautifs)

    verifier(
        "Garde : aucun gdal.Open() direct aux quatre sites", echecs, aucun_appel_direct
    )

    # --- Garde permanente : les quatre sites passent par l'utilitaire --------
    def tous_par_utilitaire():
        absents = []
        for fichier, fonction in SITES:
            source = io.open(
                os.path.join(dossier_source, fichier), encoding="utf-8"
            ).read()
            arbre = ast.parse(source)
            trouve = False
            for noeud in ast.walk(arbre):
                if not (
                    isinstance(noeud, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and noeud.name == fonction
                ):
                    continue
                for interne in ast.walk(noeud):
                    if (
                        isinstance(interne, ast.Call)
                        and isinstance(interne.func, ast.Name)
                        and interne.func.id == "ouvrir_raster"
                    ):
                        trouve = True
            if not trouve:
                absents.append("%s:%s" % (fichier, fonction))
        assert not absents, "n'appellent pas ouvrir_raster() : %s" % ", ".join(absents)

    verifier(
        "Garde : les quatre sites passent par ouvrir_raster()",
        echecs,
        tous_par_utilitaire,
    )

    # --- Garde permanente : la fenêtre du MNT précédent est effacée ----------
    def fenetre_mnt_effacee():
        source = io.open(
            os.path.join(dossier_source, "ui_widgetStereoPhoto.py"), encoding="utf-8"
        ).read()
        arbre = ast.parse(source)
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "getMNTWithCoord"
            ),
            None,
        )
        assert methode is not None, "getMNTWithCoord() introuvable"

        # La branche d'échec doit remettre self.mntArr à None : sans quoi
        # readMNTWithCoord() continue de rendre des altitudes lues dans le MNT
        # précédent, sans que rien ne signale qu'elles ne correspondent plus.
        remises = [
            n
            for n in ast.walk(methode)
            if isinstance(n, ast.Assign)
            and any(
                isinstance(c, ast.Attribute)
                and c.attr == "mntArr"
                and isinstance(c.value, ast.Name)
                and c.value.id == "self"
                for c in n.targets
            )
            and isinstance(n.value, ast.Constant)
            and n.value.value is None
        ]
        assert len(remises) >= 2, (
            "self.mntArr n'est remis à None qu'en %d endroit(s) : il le faut à "
            "l'absence de MNT et à l'échec de lecture" % len(remises)
        )

    verifier(
        "Garde : échec de lecture du MNT, fenêtre effacée",
        echecs,
        fenetre_mnt_effacee,
    )

    # --- L'utilitaire ne dépend ni de QGIS ni de Qt --------------------------
    def utilitaire_autonome():
        chemin_lecture = os.path.join(dossier_source, "lectureRaster.py")
        assert os.path.exists(chemin_lecture), "lectureRaster.py absent"
        source = io.open(chemin_lecture, encoding="utf-8").read()
        for interdit in ("qgis", "PyQt", "Qt"):
            assert interdit not in source, (
                "lectureRaster.py ne doit pas dépendre de %s : il sert aussi "
                "les threads" % interdit
            )

    verifier(
        "lectureRaster.py : sans dépendance à QGIS ni Qt", echecs, utilitaire_autonome
    )

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nLes rasters sont ouverts sous les deux conventions d'erreur de GDAL.")
