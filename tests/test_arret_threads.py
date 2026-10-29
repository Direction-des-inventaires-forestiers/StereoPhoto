# -*- coding: utf-8 -*-
"""Test de l'arrêt des threads d'affichage au changement de modèle.

`removeCurrentScene()` conditionnait son attente au drapeau
`showThreadInProcess`, puis relâchait la dernière référence Python du thread.
Or ce drapeau est posé et retiré *dans* `run()`, donc sur le thread de travail :
il est faux entre `start()` et l'entrée dans `run()` (de 24 à 98 ms, mesuré
sur quatorze changements de modèle), puis de nouveau entre son retrait dans le
`finally` de `run()` et la fin réelle du thread. Dans ces deux fenêtres,
l'attente était sautée et un QThread en cours d'exécution se faisait détruire :
Qt interrompait alors le processus, sans trace au journal.

La condition doit porter sur `isRunning()`, seul état que le thread tient
lui-même. L'attente est bornée pour ne pas figer l'interface, mais un thread
encore vivant au bout du délai est **conservé** plutôt que relâché : c'est le
relâchement qui tue le processus, pas l'attente.

Les méthodes sont extraites du fichier source par analyse syntaxique, puis
exécutées avec des bouchons : aucune dépendance à QGIS ni à Qt n'est
nécessaire.

Usage :
    python tests/test_arret_threads.py [chemin/vers/src]

Sans argument, les modules testés sont ceux de `src/`, résolus depuis la racine
du dépôt. Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

METHODES = ("arreterThreadAffichage", "purgerThreadsEnArret", "removeCurrentScene")


def lire_constante(chemin, nom):
    """Retourne la valeur littérale d'une constante de module."""
    arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
    for noeud in arbre.body:
        if isinstance(noeud, ast.Assign):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id == nom:
                    return ast.literal_eval(noeud.value)
    raise AssertionError("constante %s absente de %s" % (nom, chemin))


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
            % (", ".join(sorted(manquantes)), classe_visee)
        )
    exec(compile(ast.Module(body=corps, type_ignores=[]), "<extrait>", "exec"), espace)
    return {nom: espace[nom] for nom in methodes_visees}


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


class ThreadBouchon:
    """QThread d'affichage : l'état réel et le drapeau sont dissociés.

    C'est la dissociation qui porte le défaut : `tourne` est ce que Qt sait du
    thread, `showThreadInProcess` ce que `run()` en a écrit.
    """

    def __init__(self, tourne, drapeau, fin_a_l_attente=True):
        self._tourne = tourne
        self.showThreadInProcess = drapeau
        self.fin_a_l_attente = fin_a_l_attente
        self.keepRunning = True
        self.signaux_coupes = False
        self.attentes = []

    def isRunning(self):
        return self._tourne

    def blockSignals(self, valeur):
        self.signaux_coupes = valeur

    def wait(self, delai=None):
        self.attentes.append(delai)
        if self.fin_a_l_attente:
            self._tourne = False
            return True
        return False


class ApplicationBouchon:
    def __init__(self, journal):
        self.journal = journal
        self.threadsEnArret = []
        self.tSeekLeft = None
        self.tSeekRight = None
        self.groupes_reinitialises = []


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


DELAI_DE_REPLI = 5000


def monter(dossier_source, methodes_voulues=METHODES):
    """Monte les méthodes demandées avec leurs bouchons.

    La constante de délai et les méthodes du correctif peuvent manquer : c'est
    le cas sur une version d'avant, et le rejeu doit alors échouer sur le
    comportement, non sur un fichier incomplet.
    """
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    chemin_config = os.path.join(dossier_source, "config.py")
    try:
        delai = lire_constante(chemin_config, "NAVIGATION_ARRET_THREAD_DELAI_MAX_MS")
    except AssertionError:
        delai = DELAI_DE_REPLI

    class ApplicationBouchonQt:
        """QApplication : seul processEvents() est sollicité."""

        @staticmethod
        def processEvents():
            return None

    espace = {
        "NAVIGATION_ARRET_THREAD_DELAI_MAX_MS": delai,
        "QApplication": ApplicationBouchonQt,
        "hasattr": hasattr,
    }
    methodes = extraire_methodes(chemin_app, "stereoPhoto", methodes_voulues, espace)
    journal = JournalBouchon()
    return methodes, ApplicationBouchon(journal), journal, delai


def executer(dossier_source):
    echecs = []
    chemin_app = os.path.join(dossier_source, "stereoPhoto.py")
    chemin_enh = os.path.join(dossier_source, "enhanceManager.py")

    # --- La fenêtre du défaut : drapeau faux, thread en cours ---------------
    def fenetre_du_defaut():
        methodes, app, journal, delai = monter(dossier_source)
        arreter = methodes["arreterThreadAffichage"]
        # L'état exact mesuré juste après start() : run() n'a pas encore levé
        # son drapeau, mais Qt tient déjà le thread pour démarré.
        thread = ThreadBouchon(tourne=True, drapeau=False)

        arreter(app, thread)

        assert thread.attentes, (
            "aucune attente alors que le thread tourne : c'est la fenêtre de "
            "24 à 98 ms où le processus se faisait interrompre"
        )
        assert thread.signaux_coupes is True, "les signaux ne sont pas coupés"
        assert thread.keepRunning is False, "l'arrêt n'est pas demandé"
        assert app.threadsEnArret == [], (
            "le thread s'est terminé, il n'a pas à être conservé"
        )

    verifier(
        "Drapeau faux et thread en cours : attente quand même",
        echecs,
        fenetre_du_defaut,
    )

    # --- Thread terminé : aucune attente, relâchement immédiat --------------
    def thread_termine():
        methodes, app, journal, delai = monter(dossier_source)
        arreter = methodes["arreterThreadAffichage"]
        thread = ThreadBouchon(tourne=False, drapeau=False)

        arreter(app, thread)

        assert thread.attentes == [], "attente inutile sur un thread terminé : %r" % (
            thread.attentes,
        )
        assert thread.signaux_coupes is True, "les signaux ne sont pas coupés"
        assert app.threadsEnArret == [], "un thread terminé a été conservé"

    verifier("Thread terminé : aucune attente", echecs, thread_termine)

    # --- Drapeau vrai : l'attente a lieu, comme avant -----------------------
    def drapeau_vrai():
        methodes, app, journal, delai = monter(dossier_source)
        arreter = methodes["arreterThreadAffichage"]
        thread = ThreadBouchon(tourne=True, drapeau=True)

        arreter(app, thread)

        assert thread.attentes == [delai], (
            "l'attente doit être bornée au délai de configuration : %r"
            % (thread.attentes,)
        )

    verifier("Drapeau vrai : attente bornée au délai", echecs, drapeau_vrai)

    # --- Délai dépassé : le thread est conservé, non relâché ----------------
    def delai_depasse():
        methodes, app, journal, delai = monter(dossier_source)
        arreter = methodes["arreterThreadAffichage"]
        thread = ThreadBouchon(tourne=True, drapeau=True, fin_a_l_attente=False)

        arreter(app, thread)

        assert app.threadsEnArret == [thread], (
            "un thread encore vivant doit être conservé, non relâché : c'est "
            "le relâchement qui fait interrompre le processus"
        )
        avertissements = [m for n, m in journal.messages if n == "warning"]
        assert len(avertissements) == 1, (
            "%d avertissement(s) : la condition doit laisser une trace"
            % len(avertissements)
        )

    verifier(
        "Délai dépassé : thread conservé et condition tracée", echecs, delai_depasse
    )

    # --- Purge : les terminés sont relâchés, les autres gardés -------------
    def purge():
        methodes, app, journal, delai = monter(dossier_source)
        purger = methodes["purgerThreadsEnArret"]
        fini = ThreadBouchon(tourne=False, drapeau=False)
        vivant = ThreadBouchon(tourne=True, drapeau=True)
        app.threadsEnArret = [fini, vivant]

        purger(app)

        assert app.threadsEnArret == [vivant], (
            "le terminé doit être relâché et le vivant gardé : %r"
            % (app.threadsEnArret,)
        )

    verifier("Purge : terminés relâchés, vivants gardés", echecs, purge)

    # --- removeCurrentScene() : arrêt avant relâchement, des deux côtés ----
    def scene_retiree():
        methodes, app, journal, delai = monter(dossier_source)
        retirer = methodes["removeCurrentScene"]
        app.arreterThreadAffichage = lambda t: methodes["arreterThreadAffichage"](
            app, t
        )
        app.purgerThreadsEnArret = lambda: methodes["purgerThreadsEnArret"](app)
        gauche = ThreadBouchon(tourne=True, drapeau=False)
        droite = ThreadBouchon(tourne=True, drapeau=False)
        app.tSeekLeft = gauche
        app.tSeekRight = droite

        retirer(app)

        assert gauche.attentes and droite.attentes, (
            "les deux threads doivent être attendus : gauche %r, droite %r"
            % (gauche.attentes, droite.attentes)
        )
        assert app.tSeekLeft is None and app.tSeekRight is None, (
            "les références doivent être relâchées après l'arrêt"
        )

    verifier(
        "removeCurrentScene() : arrêt des deux threads avant relâchement",
        echecs,
        scene_retiree,
    )

    # --- removeCurrentScene() sans thread : aucun effet de bord ------------
    def scene_sans_thread():
        methodes, app, journal, delai = monter(dossier_source)
        retirer = methodes["removeCurrentScene"]
        app.arreterThreadAffichage = lambda t: methodes["arreterThreadAffichage"](
            app, t
        )
        app.purgerThreadsEnArret = lambda: methodes["purgerThreadsEnArret"](app)

        retirer(app)

        assert app.tSeekLeft is None and app.tSeekRight is None, "état inattendu"

    verifier("removeCurrentScene() sans thread : sans effet", echecs, scene_sans_thread)

    # --- Le defaut, par le haut : removeCurrentScene() sur le drapeau faux --
    def scene_attend_thread_en_cours():
        # Ce scénario ne monte que removeCurrentScene(), et vaut donc aussi sur
        # une version d'avant le correctif : c'est lui qui montre le défaut.
        methodes, app, journal, delai = monter(dossier_source, ("removeCurrentScene",))
        retirer = methodes["removeCurrentScene"]

        # Les auxiliaires du correctif sont fournis s'ils existent ; sinon des
        # inertes, pour que removeCurrentScene() soit jugée sur sa seule logique.
        try:
            aides, _, _, _ = monter(
                dossier_source,
                ("arreterThreadAffichage", "purgerThreadsEnArret"),
            )
            app.arreterThreadAffichage = lambda t: aides["arreterThreadAffichage"](
                app, t
            )
            app.purgerThreadsEnArret = lambda: aides["purgerThreadsEnArret"](app)
        except AssertionError:
            app.arreterThreadAffichage = lambda t: None
            app.purgerThreadsEnArret = lambda: None

        # L'état mesuré juste après start() : Qt tient le thread pour démarré,
        # run() n'a pas encore levé son drapeau.
        gauche = ThreadBouchon(tourne=True, drapeau=False)
        app.tSeekLeft = gauche
        app.tSeekRight = None

        retirer(app)

        assert gauche.attentes, (
            "le thread tournait et n'a pas été attendu : sa dernière référence "
            "est relâchée en cours d'exécution, et Qt interrompt le processus"
        )

    verifier(
        "removeCurrentScene() attend un thread en cours, drapeau faux",
        echecs,
        scene_attend_thread_en_cours,
    )

    # --- Garde permanente : plus aucune décision prise sur le drapeau ------
    def drapeau_hors_decision():
        fautifs = []
        for chemin, classe, methodes_visees in (
            (
                chemin_app,
                "stereoPhoto",
                ("removeCurrentScene", "arreterThreadAffichage"),
            ),
            (chemin_enh, "enhanceManager", ("removeCurrentScene",)),
        ):
            arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
            cl = next(
                (
                    n
                    for n in ast.walk(arbre)
                    if isinstance(n, ast.ClassDef) and n.name == classe
                ),
                None,
            )
            assert cl is not None, "classe %s introuvable" % classe
            for methode in cl.body:
                if (
                    not isinstance(methode, ast.FunctionDef)
                    or methode.name not in methodes_visees
                ):
                    continue
                # Un `if` dont le test lit showThreadInProcess décide d'un
                # arrêt ou d'une destruction sur un état non fiable.
                for noeud in ast.walk(methode):
                    if not isinstance(noeud, ast.If):
                        continue
                    for interne in ast.walk(noeud.test):
                        if (
                            isinstance(interne, ast.Attribute)
                            and interne.attr == "showThreadInProcess"
                        ):
                            fautifs.append(
                                "%s.%s l.%d" % (classe, methode.name, noeud.lineno)
                            )
        assert not fautifs, "décision prise sur showThreadInProcess : %s" % ", ".join(
            fautifs
        )

    verifier(
        "Garde : aucune décision d'arrêt prise sur showThreadInProcess",
        echecs,
        drapeau_hors_decision,
    )

    # --- Garde permanente : l'attente est conditionnée à isRunning() -------
    def attente_sur_isrunning():
        absents = []
        for chemin, classe, methode_visee in (
            (chemin_app, "stereoPhoto", "arreterThreadAffichage"),
            (chemin_enh, "enhanceManager", "removeCurrentScene"),
        ):
            arbre = ast.parse(io.open(chemin, encoding="utf-8").read())
            cl = next(
                (
                    n
                    for n in ast.walk(arbre)
                    if isinstance(n, ast.ClassDef) and n.name == classe
                ),
                None,
            )
            methode = next(
                (
                    n
                    for n in (cl.body if cl else [])
                    if isinstance(n, ast.FunctionDef) and n.name == methode_visee
                ),
                None,
            )
            if methode is None:
                absents.append("%s.%s introuvable" % (classe, methode_visee))
                continue
            appels = {
                n.func.attr
                for n in ast.walk(methode)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            }
            if "isRunning" not in appels:
                absents.append(
                    "%s.%s ne consulte pas isRunning()" % (classe, methode_visee)
                )
            if "wait" not in appels:
                absents.append("%s.%s n'attend pas le thread" % (classe, methode_visee))
        assert not absents, "; ".join(absents)

    verifier(
        "Garde : attente conditionnée à isRunning() aux deux endroits",
        echecs,
        attente_sur_isrunning,
    )

    return echecs


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT
    print("Modules testés : %s\n" % source)
    problemes = executer(source)
    if problemes:
        print("\n%d scénario(s) en échec." % len(problemes))
        sys.exit(1)
    print("\nAucun QThread d'affichage n'est relâché en cours d'exécution.")
