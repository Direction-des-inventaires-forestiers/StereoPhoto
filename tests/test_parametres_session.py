# -*- coding: utf-8 -*-
"""Test de l'enregistrement et de la relecture des paramètres de session.

Trois défauts enchaînés, relevés à l'usage le 2026-10-22 dès qu'un MNT réel a
été employé.

1. **Une valeur numpy dans les paramètres.** L'altitude lue dans le MNT sort de
   numpy en `float32`. Portée jusqu'à `ParamDict` par `setLastView()`, elle
   faisait lever `json.dump()` : « Object of type float32 is not JSON
   serializable ». Avant le MNT réel, l'altitude venait du calcul
   stéréoscopique, en `float` natif, et le défaut dormait.

2. **Une écriture non atomique.** `saveParamFile()` ouvrait le fichier de
   destination en écriture — ce qui le vide — puis sérialisait dedans. La levée
   ci-dessus laissait donc un JSON tronqué : `{ "position": { "longitude":`.

3. **Une lecture sans repli.** `loadParamFile()` lisait sans gestion d'erreur :
   sur ce fichier tronqué, `run()` s'arrêtait en chemin, `optWindow` restait
   sans `rehaussementParam`, et l'extension devenait inutilisable jusqu'à
   réparation du fichier à la main.

Les trois sont gardés ici. Les méthodes sont extraites du fichier source par
analyse syntaxique : aucune dépendance à QGIS ni à Qt n'est nécessaire.

Usage :
    python tests/test_parametres_session.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import copy
import io
import json
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

# Structure de repli, pour pouvoir monter les méthodes d'une version du code
# qui ne déclare pas encore ses valeurs par défaut.
DEFAUTS_DE_REPLI = {
    "position": {"longitude": 0.0, "latitude": 0.0, "altitude": 0.0, "scale": 0.0},
    "stereoscope": {"ecran_bas": 0, "ecran_haut": 0, "miroir_OFF": False},
    "info_raster": {"mnt_file": "", "image_dir": "", "user_image": ""},
    "rehaussement": [0, 0, 0, 0, 0, 0, 0, False, False, []],
}


class Float32Bouchon(float):
    """Valeur non sérialisable par json, comme numpy.float32.

    `json.dump()` ne sérialise que les types exacts qu'il connaît : une
    sous-classe de `float` suffit à reproduire le refus, sans dépendre de
    numpy.
    """

    pass


def _refuser_les_sous_classes(o):
    raise TypeError("Object of type %s is not JSON serializable" % type(o).__name__)


def serialiser_strictement(objet, fichier, **kwargs):
    """json.dump() qui refuse toute sous-classe de float, comme pour numpy.

    Les arguments nommés de json.dump() sont acceptés et transmis : les deux
    versions du code appellent avec indent et ensure_ascii.
    """

    def convertir(valeur):
        if isinstance(valeur, dict):
            return {k: convertir(v) for k, v in valeur.items()}
        if isinstance(valeur, list):
            return [convertir(v) for v in valeur]
        if isinstance(valeur, float) and type(valeur) is not float:
            _refuser_les_sous_classes(valeur)
        return valeur

    kwargs.setdefault("indent", 2)
    kwargs.setdefault("ensure_ascii", False)
    json.dump(convertir(objet), fichier, **kwargs)


def lire_constante(chemin, nom):
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id == nom:
                    return ast.literal_eval(noeud.value)
    raise AssertionError("constante %s absente de %s" % (nom, chemin))


def extraire_methodes(chemin, classe_visee, methodes_visees, espace):
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
            "méthode(s) %s introuvable(s) dans %s"
            % (", ".join(sorted(manquantes)), classe_visee)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in methodes_visees}


class JournalBouchon:
    def __init__(self):
        self.messages = []

    def _noter(self, niveau):
        def ecrire(gabarit, *args, **kwargs):
            self.messages.append((niveau, gabarit % args if args else gabarit))

        return ecrire

    def __getattr__(self, nom):
        if nom in ("debug", "info", "warning", "error", "exception"):
            return self._noter(nom)
        raise AttributeError(nom)


class SpinBoxBouchon:
    def __init__(self):
        self._v = 0
        self._max = 0

    def value(self):
        return self._v

    def setValue(self, v):
        self._v = v

    def setMaximum(self, v):
        self._max = v


class CaseBouchon:
    def __init__(self):
        self._c = False

    def isChecked(self):
        return self._c

    def setChecked(self, v):
        self._c = v

    def setEnabled(self, v):
        pass


class ChampBouchon:
    def __init__(self):
        self._t = ""

    def text(self):
        return self._t

    def setText(self, t):
        self._t = t


class UiBouchon:
    def __init__(self):
        self.spinBoxUpScreen = SpinBoxBouchon()
        self.spinBoxDownScreen = SpinBoxBouchon()
        self.checkBoxFlip = CaseBouchon()
        self.radioButtonCut = CaseBouchon()
        self.radioButtonDraw = CaseBouchon()
        self.pushButtonRemoveMNT = CaseBouchon()
        self.importLineProject = ChampBouchon()
        self.importLineMNT = ChampBouchon()
        self.labelLeftName = ChampBouchon()


class PanneauBouchon:
    """optionWindow réduit à ce que les deux méthodes sollicitent."""

    def __init__(self, chemin_json):
        self.JSONPath = chemin_json
        self.ui = UiBouchon()
        self.currentMNTPath = ""
        self.rehaussementParam = None
        self.ParamDict = {}
        self.currentNoValidKey = []


def verifier(libelle, echecs, controle):
    try:
        controle()
    except AssertionError as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-56s %s" % (libelle, erreur))
    except Exception as erreur:
        echecs.append((libelle, erreur))
        print("ECHEC  %-56s %s : %s" % (libelle, type(erreur).__name__, erreur))
    else:
        print("OK     %-56s" % libelle)


def monter(dossier_source, chemin_json, strict=False):
    """Monte loadParamFile() et saveParamFile() avec leurs bouchons."""
    chemin = os.path.join(dossier_source, "ui_widgetStereoPhoto.py")
    try:
        defauts = lire_constante(chemin, "PARAMETRES_PAR_DEFAUT")
    except AssertionError:
        # Version d'avant le correctif : la constante de repli n'existe pas.
        # Le montage se poursuit avec la même structure, pour que le rejeu
        # échoue sur le comportement et non sur un fichier incomplet.
        defauts = copy.deepcopy(DEFAUTS_DE_REPLI)
    journal = JournalBouchon()

    class ApplicationBouchonQt:
        class QApplication:
            @staticmethod
            def desktop():
                class Bureau:
                    @staticmethod
                    def screenCount():
                        return 1

                return Bureau()

    module_json = type(
        "JsonBouchon",
        (),
        {
            "load": staticmethod(json.load),
            "dump": staticmethod(serialiser_strictement if strict else json.dump),
        },
    )

    espace = {
        "json": module_json,
        "os": os,
        "copy": copy,
        "_journal": journal,
        "QtWidgets": ApplicationBouchonQt,
        "PARAMETRES_PAR_DEFAUT": defauts,
    }
    methodes = extraire_methodes(
        chemin, "optionWindow", ("loadParamFile", "saveParamFile"), espace
    )
    return methodes, PanneauBouchon(chemin_json), journal, defauts


def executer(dossier_source):
    echecs = []
    chemin_src = os.path.join(dossier_source, "ui_widgetStereoPhoto.py")

    # --- Le fichier n'est pas détruit par un échec de sérialisation --------
    def ecriture_atomique():
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "paramStoring.json")
            valide = {
                "position": {
                    "longitude": 1.0,
                    "latitude": 2.0,
                    "altitude": 3.0,
                    "scale": 4.0,
                },
                "stereoscope": {
                    "ecran_bas": 0,
                    "ecran_haut": 1,
                    "miroir_OFF": True,
                },
                "info_raster": {
                    "mnt_file": "",
                    "image_dir": "/photos",
                    "user_image": "",
                },
                "rehaussement": [1, 2, 3, 0, 0, 0, 0, False, False, []],
            }
            io.open(chemin, "w", encoding="utf-8").write(json.dumps(valide))

            # Sérialisation stricte, et une altitude non sérialisable : c'est
            # exactement la situation qui détruisait le fichier.
            methodes, panneau, journal, _ = monter(dossier_source, chemin, strict=True)
            panneau.ParamDict = copy.deepcopy(valide)
            panneau.ParamDict["position"]["altitude"] = Float32Bouchon(932.05)
            panneau.rehaussementParam = valide["rehaussement"]

            methodes["saveParamFile"](panneau)

            # Le fichier doit être resté intact et lisible.
            relu = json.load(io.open(chemin, encoding="utf-8"))
            assert relu == valide, (
                "le fichier a été modifié ou détruit par un enregistrement en "
                "échec : %r" % (relu,)
            )
            assert not os.path.exists(chemin + ".nouveau"), (
                "le fichier provisoire n'est pas nettoyé"
            )
            assert any(n == "exception" for n, _ in journal.messages), (
                "l'échec d'enregistrement n'est pas journalisé"
            )

    verifier(
        "Échec de sérialisation : le fichier survit intact",
        echecs,
        ecriture_atomique,
    )

    # --- Un enregistrement normal remplace bien le contenu ----------------
    def ecriture_normale():
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "paramStoring.json")
            methodes, panneau, journal, defauts = monter(dossier_source, chemin)
            panneau.ParamDict = copy.deepcopy(defauts)
            panneau.rehaussementParam = [9, 8, 7, 0, 0, 0, 0, False, False, []]
            panneau.ui.spinBoxUpScreen.setValue(2)
            panneau.ui.importLineProject.setText("/photos/2016")

            methodes["saveParamFile"](panneau)

            relu = json.load(io.open(chemin, encoding="utf-8"))
            assert relu["stereoscope"]["ecran_haut"] == 2, (
                "l'écran du haut n'est pas enregistré : %r" % (relu,)
            )
            assert relu["info_raster"]["image_dir"] == "/photos/2016", (
                "le dossier d'images n'est pas enregistré"
            )
            assert relu["rehaussement"][0] == 9, "le rehaussement n'est pas enregistré"

    verifier("Enregistrement normal : contenu écrit", echecs, ecriture_normale)

    # --- Un fichier tronqué ne doit pas empêcher d'ouvrir une session -----
    def lecture_fichier_tronque():
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "paramStoring.json")
            # Exactement ce qu'un enregistrement interrompu laissait derrière.
            io.open(chemin, "w", encoding="utf-8").write(
                '{\n  "position": {\n    "longitude": '
            )
            methodes, panneau, journal, defauts = monter(dossier_source, chemin)

            methodes["loadParamFile"](panneau)

            assert panneau.rehaussementParam == defauts["rehaussement"], (
                "les paramètres de rehaussement ne reprennent pas leur valeur "
                "par défaut : %r" % (panneau.rehaussementParam,)
            )
            assert panneau.ParamDict["position"] == defauts["position"], (
                "la position ne reprend pas sa valeur par défaut"
            )
            assert any(n == "exception" for n, _ in journal.messages), (
                "la lecture en échec n'est pas journalisée"
            )

    verifier(
        "Fichier tronqué : session ouvrable, valeurs par défaut",
        echecs,
        lecture_fichier_tronque,
    )

    # --- Un fichier absent se comporte de même ----------------------------
    def lecture_fichier_absent():
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "absent.json")
            methodes, panneau, journal, defauts = monter(dossier_source, chemin)

            methodes["loadParamFile"](panneau)

            assert panneau.rehaussementParam == defauts["rehaussement"], (
                "valeurs par défaut non appliquées sur fichier absent"
            )

    verifier(
        "Fichier absent : session ouvrable, valeurs par défaut",
        echecs,
        lecture_fichier_absent,
    )

    # --- Une section incomplète reprend ses défauts, le reste est gardé ---
    def section_incomplete():
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "paramStoring.json")
            # « stereoscope » ampute de miroir_OFF, et « position » absente.
            io.open(chemin, "w", encoding="utf-8").write(
                json.dumps(
                    {
                        "stereoscope": {"ecran_bas": 1, "ecran_haut": 1},
                        "info_raster": {
                            "mnt_file": "",
                            "image_dir": "/photos",
                            "user_image": "",
                        },
                        "rehaussement": [5, 0, 0, 0, 0, 0, 0, False, False, []],
                    }
                )
            )
            methodes, panneau, journal, defauts = monter(dossier_source, chemin)

            methodes["loadParamFile"](panneau)

            assert (
                panneau.ParamDict["stereoscope"]["miroir_OFF"]
                == defauts["stereoscope"]["miroir_OFF"]
            ), "la clé absente ne reprend pas sa valeur par défaut"
            assert panneau.ParamDict["stereoscope"]["ecran_bas"] == 1, (
                "la clé présente n'est pas conservée"
            )
            assert panneau.ParamDict["position"] == defauts["position"], (
                "la section absente ne reprend pas ses valeurs par défaut"
            )
            assert panneau.ParamDict["rehaussement"][0] == 5, (
                "la section présente n'est pas conservée"
            )

    verifier(
        "Section incomplète : défauts par clé, reste conservé",
        echecs,
        section_incomplete,
    )

    # --- Garde permanente : l'altitude part en type natif -----------------
    def altitude_convertie():
        chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
        arbre = ast.parse(io.open(chemin_app, encoding="utf-8").read())
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "setLastView"
            ),
            None,
        )
        assert methode is not None, "setLastView() introuvable"

        # Chaque écriture dans ParamDict["position"] doit passer par float().
        nus = []
        for noeud in ast.walk(methode):
            if not isinstance(noeud, ast.Assign):
                continue
            for cible in noeud.targets:
                if not isinstance(cible, ast.Subscript):
                    continue
                if "ParamDict" not in ast.dump(cible):
                    continue
                converti = (
                    isinstance(noeud.value, ast.Call)
                    and isinstance(noeud.value.func, ast.Name)
                    and noeud.value.func.id == "float"
                )
                if not converti:
                    nus.append(noeud.lineno)
        assert not nus, (
            "valeur écrite dans ParamDict sans conversion en type natif, "
            "lignes %s : une valeur numpy y ferait lever json.dump()"
            % ", ".join(str(n) for n in nus)
        )

    verifier(
        "Garde : l'altitude mémorisée part en type natif",
        echecs,
        altitude_convertie,
    )

    # --- Garde permanente : la lecture du MNT rend un float natif ---------
    def lecture_mnt_native():
        arbre = ast.parse(io.open(chemin_src, encoding="utf-8").read())
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "readMNTWithCoord"
            ),
            None,
        )
        assert methode is not None, "readMNTWithCoord() introuvable"
        conversions = [
            n
            for n in ast.walk(methode)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "float"
        ]
        assert conversions, (
            "readMNTWithCoord() rend la valeur numpy telle quelle : c'est le "
            "seul point d'entrée du MNT dans l'extension, la conversion y "
            "dispense tous les appelants d'y penser"
        )

    verifier(
        "Garde : readMNTWithCoord() rend un float natif",
        echecs,
        lecture_mnt_native,
    )

    # --- Garde permanente : l'écriture passe par un fichier provisoire ----
    def ecriture_par_substitution():
        arbre = ast.parse(io.open(chemin_src, encoding="utf-8").read())
        methode = next(
            (
                n
                for n in ast.walk(arbre)
                if isinstance(n, ast.FunctionDef) and n.name == "saveParamFile"
            ),
            None,
        )
        assert methode is not None, "saveParamFile() introuvable"
        appels = {
            n.func.attr
            for n in ast.walk(methode)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        assert "replace" in appels, (
            "saveParamFile() n'emploie pas os.replace() : écrire directement "
            "dans le fichier de destination le vide avant de sérialiser, et "
            "toute levée en cours le laisse tronqué"
        )

    verifier(
        "Garde : enregistrement par substitution atomique",
        echecs,
        ecriture_par_substitution,
    )

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nLes paramètres de session survivent à un échec d'enregistrement.")
