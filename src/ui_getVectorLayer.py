# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-getLayer.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.core import *

# Colonnes du tableau de choix des couches. Nommées parce que deux fichiers les
# lisent : la fenêtre elle-même et importVectorAccept() dans
# ui_widgetStereoPhoto.py. Un indice nu se désaccorde en silence.
COLONNE_AFFICHER = 0
COLONNE_NOM = 1
COLONNE_COULEUR = 2
COLONNE_SYMBOLOGIE = 3
COLONNE_ALTITUDE = 4
COLONNE_EDITION = 5

# Hauteur sous laquelle le tableau ne descend plus quand la fenêtre est
# réduite : en deçà, il n'affiche plus une ligne entière.
HAUTEUR_TABLEAU_MINIMALE = 160

# Colonnes dont la largeur est posée d'après leur contenu. Le nom de couche en
# est exclu : il s'étire pour absorber la place libre.
COLONNES_A_MESURER = (
    COLONNE_AFFICHER,
    COLONNE_COULEUR,
    COLONNE_SYMBOLOGIE,
    COLONNE_ALTITUDE,
    COLONNE_EDITION,
)

# Marge laissée autour d'un contrôle dans sa colonne, en pixels.
MARGE_COLONNE = 10

# Fond des lignes dont la couche n'est pas affichée. Assez léger pour ne pas
# se confondre avec le surlignage de la ligne courante.
FOND_LIGNE_MASQUEE = "#ededed"

# Pictogramme de la reprise de couleur, pris au thème de QGIS. Le repli sur un
# libellé vaut pour un thème qui ne le porterait pas : un bouton vide ne dirait
# rien du tout.
PICTO_REPRISE = "mActionRefresh.svg"
LIBELLE_REPRISE = "Reprendre"
TAILLE_PICTO = 16


def styleBoutonCouleur(couleur):
    """Feuille de style d'un bouton de couleur, texte compris.

    Le bouton portait la couleur en fond sans toucher à la couleur du texte :
    la couleur noire, qui est celle par défaut, rendait « Choisir Couleur »
    illisible sur toutes les lignes à l'ouverture de la fenêtre.
    """
    texte = "#000000" if couleur.lightness() > 127 else "#ffffff"
    return "background-color: %s; color: %s;" % (couleur.name(), texte)


def couleurSymbologie(couche):
    """Couleur du premier symbole de la couche dans QGIS, ou None.

    Les vues photo dessinent chaque couche d'un seul trait : une symbologie
    par catégories ou par classes n'y est pas représentable, et c'est alors la
    couleur du premier symbole qui est reprise. Le nombre de symboles est
    rendu avec elle, pour que l'appelant puisse le dire.
    """
    try:
        rendu = couche.renderer()
        if rendu is None:
            return None, 0
        symboles = rendu.symbols(QgsRenderContext())
    except Exception:
        # Une symbologie que le rendu ne sait pas énumérer ne doit pas empêcher
        # de choisir une couleur à la main.
        return None, 0

    if not symboles:
        return None, 0
    return QtGui.QColor(symboles[0].color()), len(symboles)


class Ui_getVectorList(object):
    def setupUi(self, getVectorList):
        getVectorList.setObjectName("getVectorList")

        self.label = QtWidgets.QLabel(getVectorList)
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setObjectName("label")

        self.tableWidget = QtWidgets.QTableWidget(0, 6,getVectorList)
        # « Style » plutôt que « Symbologie » : l'en-tête commande la largeur de
        # la colonne, et le bouton qu'elle porte n'est qu'un pictogramme.
        self.tableWidget.setHorizontalHeaderLabels(["Afficher", "Nom de la couche", "Couleur", "Style", "Altitude 3D", "Édition"])
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        # Le surlignage de ligne ne désigne plus la couche d'édition, la colonne
        # Édition le fait. Laisser plusieurs lignes surlignées suggérerait un
        # choix multiple qui n'existe pas.
        self.tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        # Les numéros de ligne ne désignent rien et prennent de la largeur.
        self.tableWidget.verticalHeader().setVisible(False)
        header = self.tableWidget.horizontalHeader()
        # Les largeurs sont posées par ajusterLargeurColonnes(), qui mesure les
        # contrôles des cellules : le mode ResizeToContents les ignorerait.
        # Seul le nom de couche s'étire, pour absorber la place libre quand la
        # fenêtre est agrandie.
        for colonne in COLONNES_A_MESURER:
            header.setSectionResizeMode(colonne, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(COLONNE_NOM, QtWidgets.QHeaderView.Stretch)
        self.tableWidget.setObjectName("tableWidget")

        self.buttonBox = QtWidgets.QDialogButtonBox(getVectorList)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")

        # Mise en page, au lieu des géométries fixes d'origine : la fenêtre
        # s'accorde au tableau et le tableau suit quand on la redimensionne.
        # Avec des géométries fixes, les noms de couches du projet débordaient
        # d'une largeur figée, et agrandir la fenêtre n'y changeait rien.
        disposition = QtWidgets.QVBoxLayout(getVectorList)
        disposition.addWidget(self.label)
        disposition.addWidget(self.tableWidget)
        disposition.addWidget(self.buttonBox)

        self.retranslateUi(getVectorList)
        QtCore.QMetaObject.connectSlotsByName(getVectorList)

    def retranslateUi(self, getVectorList):
        _translate = QtCore.QCoreApplication.translate
        getVectorList.setWindowTitle(_translate("getVectorList", "Choix des couches"))
        self.label.setText(_translate("getVectorList", "Couches vectorielles"))


class getVectorLayerCustomList(QtWidgets.QDialog): 
    def __init__(self):
        super(getVectorLayerCustomList, self).__init__()
        self.ui = Ui_getVectorList()
        self.ui.setupUi(self)
        self.currentItemNames = []

        # Les couches par nom, pour que la reprise de couleur retrouve la
        # couche de sa ligne. Le tableau ne porte que des noms.
        self.couchesParNom = {}

        # Groupe exclusif : une seule couche reçoit les gestes d'édition et la
        # sélection. Le tableau porte le choix, au lieu de le déduire de la
        # ligne surlignée comme avant, ce que rien n'annonçait à l'écran.
        self.groupeEdition = QtWidgets.QButtonGroup(self)
        self.groupeEdition.setExclusive(True)

    def setItem(self,vectorLayers) :
        # Adding custom items to the list widget
        self.couchesParNom = dict(vectorLayers)
        currentVectorNames = []
        for cle in vectorLayers:
            currentVectorNames.append(cle)
            if cle not in self.currentItemNames : 
                row_position = self.ui.tableWidget.rowCount()
                self.ui.tableWidget.insertRow(row_position)

                # Column 0: checkbox
                checkbox_item = QtWidgets.QCheckBox()
                checkbox_item.setChecked(False)
                checkbox_item.toggled.connect(self.majColonneEdition)
                self.ui.tableWidget.setCellWidget(row_position, COLONNE_AFFICHER, checkbox_item)

                # Column 1: name text
                name_item = QtWidgets.QTableWidgetItem(cle)
                self.ui.tableWidget.setItem(row_position, COLONNE_NOM, name_item)

                # Column 2: color button
                # La couleur de départ est celle de la symbologie de QGIS : le
                # noir d'origine n'était celui d'aucune couche, et obligeait à
                # choisir une couleur pour chaque ligne avant toute chose.
                couleurDepart, _ = couleurSymbologie(vectorLayers[cle])
                if couleurDepart is None:
                    couleurDepart = QtGui.QColor(0,0,0)
                color_button = QtWidgets.QPushButton("Choisir Couleur")
                color_button.setStyleSheet(styleBoutonCouleur(couleurDepart))
                color_button.setProperty("color", couleurDepart)
                color_button.clicked.connect(self.choose_color)
                self.ui.tableWidget.setCellWidget(row_position, COLONNE_COULEUR, color_button)

                # Column 3: reprise de la couleur de la symbologie de QGIS
                bouton_symbologie = QtWidgets.QPushButton()
                picto = QgsApplication.getThemeIcon(PICTO_REPRISE)
                if picto.isNull():
                    bouton_symbologie.setText(LIBELLE_REPRISE)
                else:
                    bouton_symbologie.setIcon(picto)
                    bouton_symbologie.setIconSize(
                        QtCore.QSize(TAILLE_PICTO, TAILLE_PICTO)
                    )
                bouton_symbologie.setToolTip(
                    "Reprendre la couleur de la symbologie de cette couche "
                    "dans QGIS, telle qu'elle est maintenant."
                )
                bouton_symbologie.clicked.connect(self.reprendreCouleurSymbologie)
                self.ui.tableWidget.setCellWidget(
                    row_position, COLONNE_SYMBOLOGIE, bouton_symbologie
                )

                # Column 3: altitude checkbox
                checkbox_3d = QtWidgets.QCheckBox()
                checkbox_3d.setChecked(False)
                if QgsWkbTypes.hasZ(vectorLayers[cle].wkbType()) : checkbox_3d.setEnabled(True)
                else : checkbox_3d.setEnabled(False)

                self.ui.tableWidget.setCellWidget(row_position, COLONNE_ALTITUDE, checkbox_3d)

                # Column 4: couche recevant l'édition et la sélection
                radio_edition = QtWidgets.QRadioButton()
                radio_edition.setEnabled(False)
                radio_edition.setToolTip(
                    "Couche qui reçoit la sélection et les gestes d'édition. "
                    "Elle doit être affichée."
                )
                self.groupeEdition.addButton(radio_edition)
                self.ui.tableWidget.setCellWidget(row_position, COLONNE_EDITION, radio_edition)

                self.currentItemNames.append(cle)

        for currentItem in self.currentItemNames[:] :
            if currentItem not in currentVectorNames :
                for row in reversed(range(self.ui.tableWidget.rowCount())):
                    item = self.ui.tableWidget.item(row, COLONNE_NOM)
                    if item and item.text() == currentItem:
                        radio = self.ui.tableWidget.cellWidget(row, COLONNE_EDITION)
                        if radio is not None:
                            self.groupeEdition.removeButton(radio)
                        self.ui.tableWidget.removeRow(row)
                        self.currentItemNames.remove(currentItem)
                        break

        self.majColonneEdition()
        self.ajusterTaille()

    def ajusterTaille(self):
        """Accorde la fenêtre au tableau, pour éviter les barres de défilement.

        Les noms de couches du projet vont de « Secteur » à « Peuplements
        (carte écoforestière à jour) » : aucune largeur figée ne convient. La
        largeur demandée est donc celle du contenu, bornée à l'écran, où la
        barre horizontale redevient inévitable.
        """
        tableau = self.ui.tableWidget
        self.ajusterLargeurColonnes()

        largeur = sum(
            tableau.sizeHintForColumn(colonne)
            if colonne == COLONNE_NOM
            else tableau.columnWidth(colonne)
            for colonne in range(tableau.columnCount())
        )
        largeur += 2 * tableau.frameWidth()

        hauteur = tableau.horizontalHeader().height() + 2 * tableau.frameWidth()
        hauteur += sum(tableau.rowHeight(ligne) for ligne in range(tableau.rowCount()))

        # L'écran borne les deux dimensions. La hauteur est la plus exposée :
        # le projet de test porte seize couches, et rien n'en limite le nombre.
        ecran = self.screen() if hasattr(self, "screen") else None
        disponible = ecran.availableGeometry() if ecran is not None else None
        if disponible is not None:
            hauteurMax = int(disponible.height() * 0.7)
            if hauteur > hauteurMax:
                # Le défilement vertical prend sur la largeur utile : sans ce
                # supplément, la barre horizontale apparaît pour quelques pixels.
                largeur += tableau.verticalScrollBar().sizeHint().width()
                hauteur = hauteurMax
            largeur = min(largeur, int(disponible.width() * 0.9))

        # La taille demandée au tableau devient celle de la fenêtre, la mise en
        # page lui ajoutant l'étiquette, les boutons et ses marges. La hauteur
        # est relâchée ensuite, pour que la fenêtre reste réductible ; la
        # largeur reste contrainte, c'est elle qui portait le débordement.
        tableau.setMinimumSize(largeur, hauteur)
        self.adjustSize()
        tableau.setMinimumHeight(min(hauteur, HAUTEUR_TABLEAU_MINIMALE))
        self.centrerIndicateurs()

    def ajusterLargeurColonnes(self):
        """Donne à chaque colonne la largeur de ce qu'elle porte réellement.

        `resizeColumnsToContents` ne mesure que les cellules de texte : les
        contrôles posés par `setCellWidget` lui sont invisibles. La colonne
        Couleur se réglait donc sur son en-tête, et le bouton « Choisir
        Couleur » s'y trouvait tronqué.
        """
        tableau = self.ui.tableWidget
        for colonne in COLONNES_A_MESURER:
            voulue = tableau.horizontalHeader().sectionSizeHint(colonne)
            for ligne in range(tableau.rowCount()):
                controle = tableau.cellWidget(ligne, colonne)
                if controle is not None:
                    voulue = max(
                        voulue, controle.sizeHint().width() + MARGE_COLONNE
                    )
            tableau.setColumnWidth(colonne, voulue)

    def centrerIndicateurs(self):
        """Centre les cases et les radios dans leur colonne.

        Un contrôle sans texte dessine son indicateur au bord gauche de la
        cellule, alors que la cellule fait trois fois sa largeur : cliquer au
        milieu de la colonne ne faisait rien, et rien ne le laissait voir.
        Mesuré à 14 pixels d'indicateur dans une colonne de 49.

        La marge est recalculée à chaque ajustement plutôt que fixée : la
        largeur des colonnes suit le texte des en-têtes et la résolution de
        l'écran.
        """
        tableau = self.ui.tableWidget
        metriques = (
            (COLONNE_AFFICHER, QtWidgets.QStyle.PM_IndicatorWidth),
            (COLONNE_ALTITUDE, QtWidgets.QStyle.PM_IndicatorWidth),
            (COLONNE_EDITION, QtWidgets.QStyle.PM_ExclusiveIndicatorWidth),
        )

        for colonne, metrique in metriques:
            largeurColonne = tableau.columnWidth(colonne)
            for ligne in range(tableau.rowCount()):
                controle = tableau.cellWidget(ligne, colonne)
                if controle is None:
                    continue
                largeurIndicateur = controle.style().pixelMetric(
                    metrique, None, controle
                )
                marge = max(0, (largeurColonne - largeurIndicateur) // 2)
                controle.setStyleSheet("margin-left: %dpx;" % marge)

    def majColonneEdition(self):
        """Accorde la colonne Édition à la colonne Afficher.

        Une couche non affichée ne peut pas être la couche d'édition : la
        surbrillance de la sélection est tirée des formes déjà projetées dans
        les vues photo, et une couche masquée n'en a aucune.

        Le repli pose le choix sur la première couche affichée quand aucune
        n'est désignée. Cocher une seule couche reste donc un seul geste, comme
        avant, et la fenêtre ne peut pas être validée sans couche d'édition.
        """
        premierePossible = None
        dejaDesignee = None

        for ligne in range(self.ui.tableWidget.rowCount()):
            case = self.ui.tableWidget.cellWidget(ligne, COLONNE_AFFICHER)
            radio = self.ui.tableWidget.cellWidget(ligne, COLONNE_EDITION)
            if case is None or radio is None:
                continue

            affichee = case.isChecked()
            radio.setEnabled(affichee)

            # Un bouton rendu inactif garde son état coché, et un groupe
            # exclusif refuse de décocher son seul bouton retenu : il faut
            # lever l'exclusivité le temps du décochage.
            if not affichee and radio.isChecked():
                self.groupeEdition.setExclusive(False)
                radio.setChecked(False)
                self.groupeEdition.setExclusive(True)

            if affichee and premierePossible is None:
                premierePossible = radio
            if radio.isChecked():
                dejaDesignee = radio

        if dejaDesignee is None and premierePossible is not None:
            premierePossible.setChecked(True)

        self.majFondDesLignes()

    def majFondDesLignes(self):
        """Teinte les lignes dont la couche n'est pas affichée.

        La case à cocher est le seul signe qu'une couche sera dessinée, et son
        indicateur fait quatorze pixels dans un tableau de seize lignes : la
        liste des couches affichées ne se lit pas d'un coup d'oeil. Le fond
        rend l'état visible à la ligne entière.

        Les cellules sans contenu n'ont pas d'objet d'article, le tableau ne
        portant que des contrôles : il faut en poser un pour qu'elles puissent
        recevoir un fond. Il est rendu non sélectionnable, n'ayant rien à dire.
        """
        tableau = self.ui.tableWidget
        masque = QtGui.QBrush(QtGui.QColor(FOND_LIGNE_MASQUEE))
        aucun = QtGui.QBrush()

        for ligne in range(tableau.rowCount()):
            case = tableau.cellWidget(ligne, COLONNE_AFFICHER)
            if case is None:
                continue

            fond = aucun if case.isChecked() else masque
            for colonne in range(tableau.columnCount()):
                item = tableau.item(ligne, colonne)
                if item is None:
                    item = QtWidgets.QTableWidgetItem()
                    item.setFlags(QtCore.Qt.ItemIsEnabled)
                    tableau.setItem(ligne, colonne, item)
                item.setBackground(fond)

    def nomCoucheEdition(self):
        """Nom de la couche désignée pour l'édition, chaîne vide si aucune."""
        for ligne in range(self.ui.tableWidget.rowCount()):
            radio = self.ui.tableWidget.cellWidget(ligne, COLONNE_EDITION)
            if radio is not None and radio.isChecked():
                item = self.ui.tableWidget.item(ligne, COLONNE_NOM)
                return item.text() if item else ""
        return ""

    def ligneDuControle(self, controle, colonne):
        """Ligne portant ce contrôle, ou None.

        La ligne est retrouvée par le contrôle qui a émis le signal. Un indice
        capturé à la construction désignerait la mauvaise couche dès qu'une
        ligne au-dessus a été retirée, les lignes se décalant alors.
        """
        if controle is None:
            return None
        for ligne in range(self.ui.tableWidget.rowCount()):
            if self.ui.tableWidget.cellWidget(ligne, colonne) is controle:
                return ligne
        return None

    def poserCouleur(self, ligne, couleur):
        """Pose une couleur sur le bouton de couleur d'une ligne."""
        bouton = self.ui.tableWidget.cellWidget(ligne, COLONNE_COULEUR)
        if bouton is None:
            return
        bouton.setStyleSheet(styleBoutonCouleur(couleur))
        bouton.setProperty("color", couleur)

    def choose_color(self):
        bouton = self.sender()
        ligne = self.ligneDuControle(bouton, COLONNE_COULEUR)
        if ligne is None:
            return

        color = QtWidgets.QColorDialog.getColor(
            bouton.property("color") or QtGui.QColor(0, 0, 0), self
        )
        if color.isValid():
            self.poserCouleur(ligne, color)

    def reprendreCouleurSymbologie(self):
        """Reprend la couleur de la symbologie de QGIS pour cette couche.

        La couleur de départ vient déjà de la symbologie. Ce bouton sert au
        cas où elle a changé dans QGIS depuis, la fenêtre ne reconstruisant
        que les lignes des couches qu'elle ne connaissait pas encore.
        """
        ligne = self.ligneDuControle(self.sender(), COLONNE_SYMBOLOGIE)
        if ligne is None:
            return

        item = self.ui.tableWidget.item(ligne, COLONNE_NOM)
        couche = self.couchesParNom.get(item.text()) if item is not None else None
        if couche is None:
            return

        couleur, nombre = couleurSymbologie(couche)
        if couleur is None:
            QtWidgets.QMessageBox.information(
                self,
                "Symbologie",
                "La symbologie de « %s » ne rend aucune couleur. "
                "Choisir la couleur à la main." % item.text(),
            )
            return

        self.poserCouleur(ligne, couleur)
        if nombre > 1:
            QtWidgets.QMessageBox.information(
                self,
                "Symbologie",
                "« %s » porte %d symboles dans QGIS. Les vues photo dessinent "
                "une couche d'un seul trait : c'est la couleur du premier "
                "symbole qui est reprise." % (item.text(), nombre),
            )


class Ui_getImageList(object):
    def setupUi(self, getImageList):
        getImageList.setObjectName("getImageList")
        getImageList.resize(351, 358)
        self.buttonBox = QtWidgets.QDialogButtonBox(getImageList)
        self.buttonBox.setGeometry(QtCore.QRect(180, 320, 156, 23))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")
        self.listWidget = QtWidgets.QListWidget(getImageList)
        self.listWidget.setGeometry(QtCore.QRect(30, 50, 291, 261))
        self.listWidget.setObjectName("listWidget")
        self.label = QtWidgets.QLabel(getImageList)
        self.label.setGeometry(QtCore.QRect(50, 10, 260, 21)) 
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.retranslateUi(getImageList)
        QtCore.QMetaObject.connectSlotsByName(getImageList)

    def retranslateUi(self, getImageList):
        _translate = QtCore.QCoreApplication.translate
        getImageList.setWindowTitle(_translate("getImageList", "Choix de l'image"))
        self.label.setText(_translate("getImageList", "Image disponible dans le dossier"))

class getImageListDialog(QtWidgets.QDialog): 
    def __init__(self, dictName,currentName):
        super(getImageListDialog, self).__init__()
        self.ui = Ui_getImageList()
        self.ui.setupUi(self)
        for cle in dictName:
            item = QtWidgets.QListWidgetItem()
            font = QtGui.QFont()
            font.setPointSize(12)
            item.setFont(font)
            item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsEnabled)
            item.setText(cle)
            self.ui.listWidget.addItem(item)
        
        if self.ui.listWidget.count() > 0:
            for i in range(self.ui.listWidget.count()):
                item = self.ui.listWidget.item(i)
                if item.text() == currentName :
                    self.ui.listWidget.setCurrentRow(i)
                    break
            
            else : self.ui.listWidget.setCurrentRow(0)
       