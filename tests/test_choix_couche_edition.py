# -*- coding: utf-8 -*-
"""Test du choix de la couche d'édition dans la fenêtre des couches.

La fenêtre porte deux choix que rien ne distinguait : les cases « Afficher »
commandent ce qui se dessine, et la couche qui reçoit la sélection et les
gestes d'édition se déduisait de la ligne surlignée, par `currentRow()`.

Trois comportements mesurés sur ce code, et aucun n'était annonçable à
l'utilisateur :

1. Cocher une case ne déplaçait pas le surlignage, le clic étant consommé par
   la case. `currentRow()` restait à -1 et la couche d'édition était la
   première cochée dans l'ordre du tableau.
2. Le tableau acceptait plusieurs lignes surlignées, alors que `currentRow()`
   n'en rend qu'une : deux couches paraissaient retenues, une seule passait.
3. Surligner une ligne non cochée faisait retomber le code sur la première
   cochée, sans un mot. La couche surlignée et la couche d'édition
   différaient alors en silence.

La colonne « Édition », un bouton radio par ligne dans un groupe exclusif,
remplace la déduction. Ce test vérifie son accord avec la colonne
« Afficher », qui est la seule mécanique non triviale du lot : un bouton rendu
inactif garde son état coché, et un groupe exclusif de Qt refuse de décocher
son seul bouton retenu. Sans la levée d'exclusivité, masquer la couche
désignée la laisserait désignée.

`majColonneEdition` et `nomCoucheEdition` sont extraites du fichier source par
analyse syntaxique, puis exécutées contre des bouchons. Le bouchon de groupe
reproduit les deux refus de Qt nommés ci-dessus : c'est ce qui donne au test
sa prise sur le cas du masquage.

Usage :
    python tests/test_choix_couche_edition.py [chemin/vers/src]

Sortie 0 si tout passe, 1 sinon.
"""

import ast
import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_DEFAUT = os.path.join(RACINE, "src")

CLASSE = "getVectorLayerCustomList"
METHODES = ("majColonneEdition", "nomCoucheEdition")

COLONNE_AFFICHER = 0
COLONNE_NOM = 1
COLONNE_COULEUR = 2
COLONNE_ALTITUDE = 3
COLONNE_EDITION = 4


def lire(chemin):
    return io.open(chemin, encoding="utf-8").read()


def extraire_methodes(chemin, classe_visee, methodes_visees, espace):
    """Retourne des méthodes d'une classe, isolées de leur module."""
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


class GroupeBouchon:
    """Groupe de boutons de Qt, avec ses deux refus.

    Un groupe exclusif décoche les autres boutons quand l'un est coché, et
    refuse de décocher celui qu'il retient : `setChecked(False)` y est sans
    effet. Les deux sont reproduits, sinon le test perdrait sa prise.
    """

    def __init__(self):
        self.exclusif = True
        self.boutons = []

    def setExclusive(self, valeur):
        self.exclusif = bool(valeur)

    def addButton(self, bouton):
        self.boutons.append(bouton)
        bouton.groupe = self

    def removeButton(self, bouton):
        if bouton in self.boutons:
            self.boutons.remove(bouton)
            bouton.groupe = None

    def buttons(self):
        return list(self.boutons)


class RadioBouchon:
    def __init__(self):
        self.coche = False
        self.actif = True
        self.groupe = None
        self.infobulle = ""

    def isChecked(self):
        return self.coche

    def isEnabled(self):
        return self.actif

    def setEnabled(self, valeur):
        # Qt ne décoche pas un bouton rendu inactif : l'état coché survit.
        self.actif = bool(valeur)

    def setToolTip(self, texte):
        self.infobulle = texte

    def setChecked(self, valeur):
        if self.groupe is not None and self.groupe.exclusif:
            if not valeur:
                return
            for autre in self.groupe.boutons:
                if autre is not self:
                    autre.coche = False
        self.coche = bool(valeur)


class CaseBouchon:
    def __init__(self, cochee=False):
        self.coche = cochee

    def isChecked(self):
        return self.coche

    def setChecked(self, valeur):
        self.coche = bool(valeur)


class ItemBouchon:
    """QTableWidgetItem : son texte, son fond et ses drapeaux."""

    def __init__(self, texte=""):
        self.texte = texte
        self.fond = None
        self.drapeaux = None

    def text(self):
        return self.texte

    def setBackground(self, fond):
        self.fond = fond

    def setFlags(self, drapeaux):
        self.drapeaux = drapeaux


class QtCoreBouchon:
    class Qt:
        ItemIsEnabled = 0x20


class QtGuiBouchon:
    """Une couleur reste sa chaîne, une brosse vide reste None.

    Suffisant pour les deux seules questions posées au fond d'une cellule :
    teinté ou non, et de quelle teinte.
    """

    QColor = staticmethod(lambda valeur: valeur)
    QBrush = staticmethod(lambda couleur=None: couleur)


class QtWidgetsBouchon:
    QTableWidgetItem = ItemBouchon


class TableauBouchon:
    def __init__(self, noms, nombreColonnes):
        self.noms = list(noms)
        self.nombreColonnes = nombreColonnes
        self.cases = [CaseBouchon() for _ in self.noms]
        self.radios = [RadioBouchon() for _ in self.noms]
        self.articles = {
            (ligne, COLONNE_NOM): ItemBouchon(nom)
            for ligne, nom in enumerate(self.noms)
        }

    def rowCount(self):
        return len(self.noms)

    def columnCount(self):
        return self.nombreColonnes

    def cellWidget(self, ligne, colonne):
        if colonne == COLONNE_AFFICHER:
            return self.cases[ligne]
        if colonne == COLONNE_EDITION:
            return self.radios[ligne]
        return None

    def item(self, ligne, colonne):
        return self.articles.get((ligne, colonne))

    def setItem(self, ligne, colonne, article):
        self.articles[(ligne, colonne)] = article

    def fondsDeLaLigne(self, ligne):
        return [
            self.articles[(ligne, colonne)].fond
            for colonne in range(self.nombreColonnes)
            if (ligne, colonne) in self.articles
        ]


class FenetreBouchon:
    """La fenêtre réduite à ce que les méthodes extraites lisent."""

    def __init__(self, noms, methodes, nombreColonnes):
        self.ui = type("UiBouchon", (), {})()
        self.ui.tableWidget = TableauBouchon(noms, nombreColonnes)
        self.groupeEdition = GroupeBouchon()
        for radio in self.ui.tableWidget.radios:
            self.groupeEdition.addButton(radio)
        self._methodes = methodes

    def majColonneEdition(self):
        return self._methodes["majColonneEdition"](self)

    def majFondDesLignes(self):
        return self._methodes["majFondDesLignes"](self)

    def nomCoucheEdition(self):
        return self._methodes["nomCoucheEdition"](self)

    def afficher(self, ligne, valeur=True):
        """Reproduit le clic sur la case Afficher, signal compris."""
        self.ui.tableWidget.cases[ligne].setChecked(valeur)
        self.majColonneEdition()

    def designer(self, ligne):
        """Reproduit le clic sur le bouton radio de la colonne Édition."""
        radio = self.ui.tableWidget.radios[ligne]
        if not radio.isEnabled():
            return False
        radio.setChecked(True)
        return True

    def actifs(self):
        return [
            i for i, radio in enumerate(self.ui.tableWidget.radios) if radio.isEnabled()
        ]

    def coches(self):
        return [
            i for i, radio in enumerate(self.ui.tableWidget.radios) if radio.isChecked()
        ]


# Noms pris au projet de test de la DIF, pour que les cas se lisent comme la
# fenêtre les présente.
COUCHES = (
    "Saisie — polygones",
    "Saisie — lignes",
    "Saisie — points",
    "Peuplements (carte écoforestière à jour)",
    "Chemins (AQreseau+)",
)


def constantes_du_source(chemin):
    """Constantes de module déclarées par le fichier, pas celles du test.

    Les bouchons sont bâtis sur ces valeurs : une colonne renumérotée d'un côté
    seulement fait échouer les cas de comportement, et non seulement le
    contrôle de forme.
    """
    valeurs = {}
    for noeud in ast.parse(lire(chemin)).body:
        if isinstance(noeud, ast.Assign) and isinstance(noeud.value, ast.Constant):
            for cible in noeud.targets:
                if isinstance(cible, ast.Name) and cible.id.isupper():
                    valeurs[cible.id] = noeud.value.value
    return valeurs


def fenetre(chemin):
    constantes = constantes_du_source(chemin)
    espace = dict(constantes)
    espace.update(
        {
            "__builtins__": __builtins__,
            "QtCore": QtCoreBouchon,
            "QtGui": QtGuiBouchon,
            "QtWidgets": QtWidgetsBouchon,
        }
    )
    nombreColonnes = 1 + max(
        valeur for nom, valeur in constantes.items() if nom.startswith("COLONNE_")
    )
    return FenetreBouchon(
        COUCHES,
        extraire_methodes(chemin, CLASSE, METHODES, espace),
        nombreColonnes,
    )


def casAucuneCoucheAffichee(chemin_fenetre, chemin_widget, chemin_app):
    """Sans affichage, aucune couche ne peut recevoir l'édition."""
    echecs = []
    f = fenetre(chemin_fenetre)
    f.majColonneEdition()

    if f.actifs():
        echecs.append("radios actifs sans couche affichée : %s" % f.actifs())
    if f.coches():
        echecs.append("radios cochés sans couche affichée : %s" % f.coches())
    if f.nomCoucheEdition() != "":
        echecs.append(
            "couche d'édition désignée sans affichage : %r" % f.nomCoucheEdition()
        )
    return echecs, "aucun radio actif, aucune désignation"


def casRepliSurLaPremiereAffichee(chemin_fenetre, chemin_widget, chemin_app):
    """Cocher une seule couche reste un seul geste.

    Sans ce repli, la fenêtre pourrait être validée sans couche d'édition, et
    le photo-interprète cliquerait dans le vide sans rien pour l'expliquer.
    """
    echecs = []
    f = fenetre(chemin_fenetre)
    f.afficher(3)

    if f.actifs() != [3]:
        echecs.append("radios actifs attendus [3], obtenus %s" % f.actifs())
    if f.coches() != [3]:
        echecs.append("radio coché attendu [3], obtenu %s" % f.coches())
    if f.nomCoucheEdition() != COUCHES[3]:
        echecs.append(
            "couche d'édition attendue %r, obtenue %r"
            % (COUCHES[3], f.nomCoucheEdition())
        )

    # Une deuxième couche affichée ne déplace pas un choix déjà posé.
    f.afficher(0)
    if f.coches() != [3]:
        echecs.append(
            "la désignation a bougé à l'affichage d'une autre couche : %s" % f.coches()
        )
    if f.actifs() != [0, 3]:
        echecs.append("radios actifs attendus [0, 3], obtenus %s" % f.actifs())
    return echecs, "repli posé, puis stable"


def casDesignationExplicite(chemin_fenetre, chemin_widget, chemin_app):
    """Le radio désigne, et une seule couche à la fois."""
    echecs = []
    f = fenetre(chemin_fenetre)
    f.afficher(0)
    f.afficher(2)
    f.afficher(4)

    if not f.designer(2):
        echecs.append("radio de la ligne 2 inactif alors que la couche est affichée")
    if f.coches() != [2]:
        echecs.append("un seul radio attendu coché [2], obtenus %s" % f.coches())
    if f.nomCoucheEdition() != COUCHES[2]:
        echecs.append(
            "couche d'édition attendue %r, obtenue %r"
            % (COUCHES[2], f.nomCoucheEdition())
        )

    f.designer(4)
    if f.coches() != [4]:
        echecs.append("la désignation n'a pas suivi le second radio : %s" % f.coches())

    # Une couche masquée ne peut pas être désignée.
    if f.designer(1):
        echecs.append("radio de la ligne 1 actif alors que la couche est masquée")
    if f.coches() != [4]:
        echecs.append("une couche masquée a pris la désignation : %s" % f.coches())
    return echecs, "une désignation, portée par la couche affichée"


def casMasquageDeLaCoucheDesignee(chemin_fenetre, chemin_widget, chemin_app):
    """Masquer la couche désignée libère la désignation.

    C'est le cas que la levée d'exclusivité rend possible. Sans elle, le
    groupe refuse le décochage, le radio reste coché sur une couche invisible,
    et la surbrillance de la sélection n'a plus aucune forme où s'appliquer.
    """
    echecs = []
    f = fenetre(chemin_fenetre)
    f.afficher(1)
    f.afficher(3)
    f.designer(3)

    f.afficher(3, False)
    if f.coches() != [1]:
        echecs.append(
            "après masquage de la couche désignée, radios cochés %s, attendu [1]"
            % f.coches()
        )
    if f.nomCoucheEdition() != COUCHES[1]:
        echecs.append(
            "couche d'édition attendue %r, obtenue %r"
            % (COUCHES[1], f.nomCoucheEdition())
        )
    if f.actifs() != [1]:
        echecs.append("radios actifs attendus [1], obtenus %s" % f.actifs())

    # Tout masquer laisse la fenêtre sans couche d'édition, et le dit.
    f.afficher(1, False)
    if f.coches() or f.nomCoucheEdition() != "":
        echecs.append(
            "désignation survivante alors que rien n'est affiché : %s %r"
            % (f.coches(), f.nomCoucheEdition())
        )
    return echecs, "désignation libérée, repli sur ce qui reste"


def casLaLigneSurligneeNeDesignePlus(chemin_fenetre, chemin_widget, chemin_app):
    """La déduction par `currentRow()` ne doit pas revenir.

    C'était la source des trois comportements décrits en tête de fichier. Le
    contrôle porte sur la forme : `importVectorAccept` doit lire la colonne
    Édition et ne plus consulter le surlignage.
    """
    echecs = []
    source = lire(chemin_widget)
    arbre = ast.parse(source)
    fonction = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "importVectorAccept"
        ),
        None,
    )
    if fonction is None:
        echecs.append("importVectorAccept introuvable dans %s" % chemin_widget)
        return echecs, "fonction absente"

    extrait = ast.get_source_segment(source, fonction) or ""
    if "currentRow" in extrait:
        echecs.append("importVectorAccept consulte encore currentRow()")
    if "nomCoucheEdition" not in extrait:
        echecs.append("importVectorAccept ne lit pas la colonne Édition")

    # Les indices de colonnes sont nommés, les deux fichiers les partageant.
    fenetre_source = lire(chemin_fenetre)
    declarees = constantes_du_source(chemin_fenetre)
    attendues = {
        "COLONNE_AFFICHER": COLONNE_AFFICHER,
        "COLONNE_NOM": COLONNE_NOM,
        "COLONNE_COULEUR": COLONNE_COULEUR,
        "COLONNE_ALTITUDE": COLONNE_ALTITUDE,
        "COLONNE_EDITION": COLONNE_EDITION,
    }
    for nom, valeur in attendues.items():
        if nom not in declarees:
            echecs.append("constante %s non déclarée" % nom)
        elif declarees[nom] != valeur:
            echecs.append(
                "%s déclarée à %r, attendue à %r : les cas de comportement de "
                "ce fichier sont bâtis sur l'ordre des colonnes"
                % (nom, declarees[nom], valeur)
            )
        if nom not in extrait and nom != "COLONNE_EDITION":
            echecs.append("importVectorAccept n'emploie pas %s" % nom)

    if "QTableWidget(0, 5," not in fenetre_source:
        echecs.append("le tableau n'est pas construit avec cinq colonnes")
    if '"Édition"' not in fenetre_source:
        echecs.append("en-tête « Édition » absent du tableau")
    if "SingleSelection" not in fenetre_source:
        echecs.append(
            "le tableau accepte encore plusieurs lignes surlignées, "
            "ce qui suggère un choix multiple inexistant"
        )
    if "toggled.connect(self.majColonneEdition)" not in fenetre_source:
        echecs.append(
            "la case Afficher ne commande pas la colonne Édition : "
            "les deux colonnes se désaccorderaient"
        )
    return echecs, "colonne Édition lue, surlignage écarté"


def casSortiePourLaCouchePrecedente(chemin_fenetre, chemin_widget, chemin_app):
    """Changer de couche d'édition doit proposer d'enregistrer la précédente.

    Le tampon reste attaché à la couche quittée dans QGIS, mais la barre
    StereoPhoto ne le commande plus : sans la question, les modifications
    sortent du champ de vision sans être perdues, ce qui est pire.
    """
    echecs = []
    source = lire(chemin_app)
    arbre = ast.parse(source)
    fonction = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "mNewVectorLayer"
        ),
        None,
    )
    if fonction is None:
        echecs.append("mNewVectorLayer introuvable dans %s" % chemin_app)
        return echecs, "fonction absente"

    extrait = ast.get_source_segment(source, fonction) or ""
    lignes = extrait.splitlines()
    rang_question = next(
        (i for i, ligne in enumerate(lignes) if "demanderSortEditions" in ligne), None
    )
    rang_pose = next(
        (i for i, ligne in enumerate(lignes) if "self.vectorLayer = couche" in ligne),
        None,
    )

    if rang_question is None:
        echecs.append("mNewVectorLayer ne propose pas le sort des modifications")
    if rang_pose is None:
        echecs.append("mNewVectorLayer ne pose plus self.vectorLayer")
    if rang_question is not None and rang_pose is not None:
        if rang_question > rang_pose:
            echecs.append(
                "la question vient après la pose de la nouvelle couche : "
                "elle porterait sur la mauvaise"
            )
    return echecs, "question posée avant le changement de couche"


def casCouleurSansIndiceCapture(chemin_fenetre, chemin_widget, chemin_app):
    """Le bouton de couleur ne doit pas capturer son indice de ligne.

    Les lignes se décalent quand une couche quitte le projet : un indice
    capturé à la construction désignait alors la couleur d'une autre couche.
    """
    echecs = []
    source = lire(chemin_fenetre)
    arbre = ast.parse(source)
    methode = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "choose_color"
        ),
        None,
    )
    if methode is None:
        echecs.append("choose_color introuvable dans %s" % chemin_fenetre)
        return echecs, "méthode absente"

    arguments = [a.arg for a in methode.args.args if a.arg != "self"]
    if arguments:
        echecs.append(
            "choose_color reçoit encore %s : l'indice est capturé à la construction"
            % ", ".join(arguments)
        )
    if "r=row_position" in source:
        echecs.append("un indice de ligne est encore capturé dans une lambda")
    return echecs, "ligne retrouvée par le bouton émetteur"


def casFenetreAccordeeAuContenu(chemin_fenetre, chemin_widget, chemin_app):
    """La fenêtre doit s'accorder au tableau, sans barre de défilement.

    Les géométries fixes d'origine figeaient le tableau à 401 pixels de large,
    plus étroit que les noms de couches du projet, et agrandir la fenêtre n'y
    changeait rien : les colonnes ne suivaient pas.
    """
    echecs = []
    source = lire(chemin_fenetre)
    arbre = ast.parse(source)

    setup = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "setupUi"
        ),
        None,
    )
    if setup is None:
        echecs.append("setupUi introuvable dans %s" % chemin_fenetre)
        return echecs, "fonction absente"

    extrait = ast.get_source_segment(source, setup) or ""
    if "setGeometry" in extrait:
        echecs.append(
            "setupUi pose encore des géométries fixes : la fenêtre ne peut pas "
            "s'accorder au contenu"
        )
    if "QVBoxLayout" not in extrait:
        echecs.append("setupUi ne construit pas de mise en page")
    if "QHeaderView.Stretch" not in extrait:
        echecs.append(
            "aucune colonne ne s'étire : la place libre resterait vide à droite"
        )
    if "ajusterLargeurColonnes" not in source:
        echecs.append(
            "les largeurs de colonnes ne sont pas mesurées : les contrôles des "
            "cellules sont invisibles à resizeColumnsToContents"
        )
    if "sizeHint().width()" not in source:
        echecs.append(
            "la largeur des colonnes ignore la taille des contrôles qu'elles "
            "portent : le bouton de couleur s'y trouverait tronqué"
        )
    if "verticalHeader().setVisible(False)" not in extrait:
        echecs.append("les numéros de ligne prennent de la largeur pour rien")

    set_item = next(
        (
            n
            for n in ast.walk(arbre)
            if isinstance(n, ast.FunctionDef) and n.name == "setItem"
        ),
        None,
    )
    if set_item is None:
        echecs.append("setItem introuvable dans %s" % chemin_fenetre)
    elif "ajusterTaille" not in (ast.get_source_segment(source, set_item) or ""):
        echecs.append(
            "setItem ne réaccorde pas la fenêtre : la taille resterait celle "
            "du jeu de couches précédent"
        )

    if "centrerIndicateurs" not in source:
        echecs.append(
            "les indicateurs ne sont pas centrés : un clic au milieu de la "
            "colonne manquerait la case, qui se dessine au bord gauche"
        )
    if "styleBoutonCouleur" not in source:
        echecs.append(
            "la couleur du texte du bouton ne suit pas son fond : « Choisir "
            "Couleur » est illisible sur une couleur sombre"
        )
    if "availableGeometry" not in source:
        echecs.append(
            "la taille demandée n'est pas bornée à l'écran : un nom très long "
            "ou un projet très fourni donnerait une fenêtre hors écran"
        )
    return echecs, "mise en page, colonnes au contenu, taille bornée"


CAS = (
    ("aucune couche affichée", casAucuneCoucheAffichee),
    ("repli sur la première affichée", casRepliSurLaPremiereAffichee),
    ("désignation explicite", casDesignationExplicite),
    ("masquage de la couche désignée", casMasquageDeLaCoucheDesignee),
    ("la ligne surlignée ne désigne plus", casLaLigneSurligneeNeDesignePlus),
    ("sortie pour la couche précédente", casSortiePourLaCouchePrecedente),
    ("couleur sans indice capturé", casCouleurSansIndiceCapture),
    ("fenêtre accordée au contenu", casFenetreAccordeeAuContenu),
)


def executer(source):
    chemin_fenetre = os.path.join(source, "ui_getVectorLayer.py")
    chemin_widget = os.path.join(source, "ui_widgetStereoPhoto.py")
    chemin_app = os.path.join(source, "stereoPhoto.py")
    print("Modules testés : %s" % source)
    print()

    total = []
    for libelle, fonction in CAS:
        echecs, note = fonction(chemin_fenetre, chemin_widget, chemin_app)
        total.extend(echecs)
        print("%-6s %-38s %s" % ("OK" if not echecs else "ECHEC", libelle, note))
        for echec in echecs:
            print("       %s" % echec)

    print()
    if total:
        print("%d écart(s) relevé(s)." % len(total))
        return 1
    print("L'affichage et l'édition sont deux choix distincts.")
    return 0


if __name__ == "__main__":
    sys.exit(executer(sys.argv[1] if len(sys.argv) > 1 else SOURCE_DEFAUT))
