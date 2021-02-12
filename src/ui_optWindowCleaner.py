# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-optionWindow_VersionDossierImage.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
import os
from qgis.utils import iface
from qgis.core import QgsMapLayerType, QgsWkbTypes
from . import resources
from .ui_getVectorLayer import getVectorLayer


class Ui_optionWindow(object):
    def setupUi(self, optionWindow):
        optionWindow.setObjectName("optionWindow")
        optionWindow.resize(440, 476)
        self.groupBoxLeft = QtWidgets.QGroupBox(optionWindow)
        self.groupBoxLeft.setGeometry(QtCore.QRect(10, 60, 201, 171))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.groupBoxLeft.setFont(font)
        self.groupBoxLeft.setObjectName("groupBoxLeft")
        self.graphicsViewLeft = QtWidgets.QGraphicsView(self.groupBoxLeft)
        self.graphicsViewLeft.setGeometry(QtCore.QRect(10, 70, 181, 91))
        self.graphicsViewLeft.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewLeft.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewLeft.setObjectName("graphicsViewLeft")
        self.label_8 = QtWidgets.QLabel(self.groupBoxLeft)
        self.label_8.setGeometry(QtCore.QRect(20, 45, 91, 16))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.spinBoxLeftScreen = QtWidgets.QSpinBox(self.groupBoxLeft)
        self.spinBoxLeftScreen.setGeometry(QtCore.QRect(131, 45, 51, 22))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.spinBoxLeftScreen.setFont(font)
        self.spinBoxLeftScreen.setMaximum(0)
        self.spinBoxLeftScreen.setObjectName("spinBoxLeftScreen")
        self.labelLeftName = QtWidgets.QLabel(self.groupBoxLeft)
        self.labelLeftName.setGeometry(QtCore.QRect(20, 20, 171, 20))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.labelLeftName.setFont(font)
        self.labelLeftName.setText("")
        self.labelLeftName.setObjectName("labelLeftName")
        self.groupBoxRight = QtWidgets.QGroupBox(optionWindow)
        self.groupBoxRight.setGeometry(QtCore.QRect(220, 60, 201, 171))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.groupBoxRight.setFont(font)
        self.groupBoxRight.setObjectName("groupBoxRight")
        self.graphicsViewRight = QtWidgets.QGraphicsView(self.groupBoxRight)
        self.graphicsViewRight.setGeometry(QtCore.QRect(10, 70, 181, 91))
        self.graphicsViewRight.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewRight.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewRight.setObjectName("graphicsViewRight")
        self.label_9 = QtWidgets.QLabel(self.groupBoxRight)
        self.label_9.setGeometry(QtCore.QRect(20, 45, 91, 16))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.spinBoxRightScreen = QtWidgets.QSpinBox(self.groupBoxRight)
        self.spinBoxRightScreen.setGeometry(QtCore.QRect(131, 45, 51, 22))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.spinBoxRightScreen.setFont(font)
        self.spinBoxRightScreen.setMaximum(0)
        self.spinBoxRightScreen.setObjectName("spinBoxRightScreen")
        self.labelRightName = QtWidgets.QLabel(self.groupBoxRight)
        self.labelRightName.setGeometry(QtCore.QRect(20, 20, 161, 16))
        font = QtGui.QFont()
        font.setPointSize(9)
        font.setBold(True)
        font.setWeight(75)
        self.labelRightName.setFont(font)
        self.labelRightName.setText("")
        self.labelRightName.setObjectName("labelRightName")
        self.enhanceButton = QtWidgets.QPushButton(optionWindow)
        self.enhanceButton.setEnabled(False)
        self.enhanceButton.setGeometry(QtCore.QRect(190, 270, 71, 23))
        self.enhanceButton.setCheckable(False)
        self.enhanceButton.setObjectName("enhanceButton")
        self.pushButtonShowPicture = QtWidgets.QPushButton(optionWindow)
        self.pushButtonShowPicture.setEnabled(False)
        self.pushButtonShowPicture.setGeometry(QtCore.QRect(320, 240, 81, 23))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.pushButtonShowPicture.setFont(font)
        #self.pushButtonShowPicture.setCheckable(True)
        self.pushButtonShowPicture.setObjectName("pushButtonShowPicture")
        self.label_7 = QtWidgets.QLabel(optionWindow)
        self.label_7.setGeometry(QtCore.QRect(170, 430, 91, 16))
        self.label_7.setObjectName("label_7")
        self.lineEditCurrentZ = QtWidgets.QLineEdit(optionWindow)
        self.lineEditCurrentZ.setGeometry(QtCore.QRect(280, 430, 81, 20))
        self.lineEditCurrentZ.setReadOnly(True)
        self.lineEditCurrentZ.setObjectName("lineEditCurrentZ")
        self.label_10 = QtWidgets.QLabel(optionWindow)
        self.label_10.setGeometry(QtCore.QRect(200, 310, 141, 16))
        self.label_10.setObjectName("label_10")
        self.spinBoxRecouvrementH = QtWidgets.QSpinBox(optionWindow)
        self.spinBoxRecouvrementH.setGeometry(QtCore.QRect(330, 310, 51, 22))
        self.spinBoxRecouvrementH.setMaximum(100)
        self.spinBoxRecouvrementH.setProperty("value", 60)
        self.spinBoxRecouvrementH.setObjectName("spinBoxRecouvrementH")
        self.label_14 = QtWidgets.QLabel(optionWindow)
        self.label_14.setGeometry(QtCore.QRect(200, 340, 171, 20))
        self.label_14.setObjectName("label_14")
        self.spinBoxRecouvrementV = QtWidgets.QSpinBox(optionWindow)
        self.spinBoxRecouvrementV.setGeometry(QtCore.QRect(360, 340, 51, 22))
        self.spinBoxRecouvrementV.setMaximum(100)
        self.spinBoxRecouvrementV.setProperty("value", 100)
        self.spinBoxRecouvrementV.setObjectName("spinBoxRecouvrementV")
        self.groupBoxMoveLine = QtWidgets.QGroupBox(optionWindow)
        self.groupBoxMoveLine.setGeometry(QtCore.QRect(10, 330, 141, 121))
        self.groupBoxMoveLine.setObjectName("groupBoxMoveLine")
        self.spinBoxMoveInY = QtWidgets.QSpinBox(self.groupBoxMoveLine)
        self.spinBoxMoveInY.setGeometry(QtCore.QRect(75, 90, 51, 22))
        self.spinBoxMoveInY.setObjectName("spinBoxMoveInY")
        self.spinBoxMoveInX = QtWidgets.QSpinBox(self.groupBoxMoveLine)
        self.spinBoxMoveInX.setGeometry(QtCore.QRect(75, 60, 51, 22))
        self.spinBoxMoveInX.setProperty("value", 5)
        self.spinBoxMoveInX.setObjectName("spinBoxMoveInX")
        self.checkBoxMoveLeft = QtWidgets.QCheckBox(self.groupBoxMoveLine)
        self.checkBoxMoveLeft.setGeometry(QtCore.QRect(10, 30, 61, 18))
        self.checkBoxMoveLeft.setChecked(True)
        self.checkBoxMoveLeft.setObjectName("checkBoxMoveLeft")
        self.checkBoxMoveRight = QtWidgets.QCheckBox(self.groupBoxMoveLine)
        self.checkBoxMoveRight.setGeometry(QtCore.QRect(70, 30, 51, 18))
        self.checkBoxMoveRight.setChecked(True)
        self.checkBoxMoveRight.setObjectName("checkBoxMoveRight")
        self.label_16 = QtWidgets.QLabel(self.groupBoxMoveLine)
        self.label_16.setGeometry(QtCore.QRect(5, 60, 71, 16))
        self.label_16.setObjectName("label_16")
        self.label_17 = QtWidgets.QLabel(self.groupBoxMoveLine)
        self.label_17.setGeometry(QtCore.QRect(10, 90, 61, 16))
        self.label_17.setObjectName("label_17")
        self.pushButtonShowIDList = QtWidgets.QPushButton(optionWindow)
        self.pushButtonShowIDList.setEnabled(False)
        self.pushButtonShowIDList.setGeometry(QtCore.QRect(190, 240, 101, 23))
        self.pushButtonShowIDList.setObjectName("pushButtonShowIDList")
        self.toolButtonOuest = QtWidgets.QToolButton(optionWindow)
        self.toolButtonOuest.setEnabled(False)
        self.toolButtonOuest.setGeometry(QtCore.QRect(40, 270, 61, 23))
        self.toolButtonOuest.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolButtonOuest.setAutoRaise(False)
        self.toolButtonOuest.setArrowType(QtCore.Qt.LeftArrow)
        self.toolButtonOuest.setObjectName("toolButtonOuest")
        self.toolButtonEst = QtWidgets.QToolButton(optionWindow)
        self.toolButtonEst.setEnabled(False)
        self.toolButtonEst.setGeometry(QtCore.QRect(120, 270, 51, 23))
        self.toolButtonEst.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolButtonEst.setAutoRaise(False)
        self.toolButtonEst.setArrowType(QtCore.Qt.RightArrow)
        self.toolButtonEst.setObjectName("toolButtonEst")
        self.toolButtonNord = QtWidgets.QToolButton(optionWindow)
        self.toolButtonNord.setEnabled(False)
        self.toolButtonNord.setGeometry(QtCore.QRect(80, 240, 61, 23))
        self.toolButtonNord.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolButtonNord.setAutoRaise(False)
        self.toolButtonNord.setArrowType(QtCore.Qt.UpArrow)
        self.toolButtonNord.setObjectName("toolButtonNord")
        self.toolButtonSud = QtWidgets.QToolButton(optionWindow)
        self.toolButtonSud.setEnabled(False)
        self.toolButtonSud.setGeometry(QtCore.QRect(80, 300, 61, 23))
        self.toolButtonSud.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toolButtonSud.setAutoRaise(False)
        self.toolButtonSud.setArrowType(QtCore.Qt.DownArrow)
        self.toolButtonSud.setObjectName("toolButtonSud")
        self.importLineVectorLayer = QtWidgets.QLineEdit(optionWindow)
        self.importLineVectorLayer.setEnabled(True)
        self.importLineVectorLayer.setGeometry(QtCore.QRect(160, 390, 146, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.importLineVectorLayer.setFont(font)
        self.importLineVectorLayer.setText("")
        self.importLineVectorLayer.setReadOnly(True)
        self.importLineVectorLayer.setObjectName("importLineVectorLayer")
        self.importToolVectorLayer = QtWidgets.QToolButton(optionWindow)
        self.importToolVectorLayer.setGeometry(QtCore.QRect(305, 390, 25, 19))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.importToolVectorLayer.setFont(font)
        self.importToolVectorLayer.setObjectName("importToolVectorLayer")
        self.pushButtonRemoveShape = QtWidgets.QPushButton(optionWindow)
        self.pushButtonRemoveShape.setEnabled(False)
        self.pushButtonRemoveShape.setGeometry(QtCore.QRect(340, 390, 91, 23))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.pushButtonRemoveShape.setFont(font)
        self.pushButtonRemoveShape.setObjectName("pushButtonRemoveShape")
        self.groupBoxMainPath = dropedit(optionWindow)
        self.groupBoxMainPath.setGeometry(QtCore.QRect(10, 10, 401, 45))
        self.groupBoxMainPath.setObjectName("groupBoxMainPath")
        self.importLineProject = QtWidgets.QLineEdit(self.groupBoxMainPath)
        self.importLineProject.setGeometry(QtCore.QRect(40, 20, 231, 20))
        self.importLineProject.setText("")
        self.importLineProject.setReadOnly(True)
        self.importLineProject.setObjectName("importLineProject")
        self.importToolProject = QtWidgets.QToolButton(self.groupBoxMainPath)
        self.importToolProject.setGeometry(QtCore.QRect(270, 20, 25, 19))
        self.importToolProject.setObjectName("importToolProject")
        self.label_3 = QtWidgets.QLabel(self.groupBoxMainPath)
        self.label_3.setEnabled(False)
        self.label_3.setGeometry(QtCore.QRect(320, 20, 61, 20))
        self.label_3.setObjectName("label_3")
        self.label_4 = QtWidgets.QLabel(self.groupBoxMainPath)
        self.label_4.setEnabled(False)
        self.label_4.setGeometry(QtCore.QRect(320, 10, 61, 16))
        self.label_4.setObjectName("label_4")
        self.label_11 = QtWidgets.QLabel(optionWindow)
        self.label_11.setGeometry(QtCore.QRect(160, 370, 91, 16))
        self.label_11.setObjectName("label_11")
        self.groupBoxRight.raise_()
        self.groupBoxLeft.raise_()
        self.enhanceButton.raise_()
        self.pushButtonShowPicture.raise_()
        self.label_7.raise_()
        self.lineEditCurrentZ.raise_()
        self.label_10.raise_()
        self.spinBoxRecouvrementH.raise_()
        self.label_14.raise_()
        self.spinBoxRecouvrementV.raise_()
        self.groupBoxMoveLine.raise_()
        self.pushButtonShowIDList.raise_()
        self.toolButtonOuest.raise_()
        self.toolButtonEst.raise_()
        self.toolButtonNord.raise_()
        self.toolButtonSud.raise_()
        self.importLineVectorLayer.raise_()
        self.importToolVectorLayer.raise_()
        self.pushButtonRemoveShape.raise_()
        self.groupBoxMainPath.raise_()
        self.label_11.raise_()

        self.retranslateUi(optionWindow)
        QtCore.QMetaObject.connectSlotsByName(optionWindow)

    def retranslateUi(self, optionWindow):
        _translate = QtCore.QCoreApplication.translate
        optionWindow.setWindowTitle(_translate("optionWindow", "Menu des options"))
        self.groupBoxLeft.setTitle(_translate("optionWindow", "Image Gauche"))
        self.label_8.setText(_translate("optionWindow", "Numéro de l\'écran :"))
        self.groupBoxRight.setTitle(_translate("optionWindow", "Image Droite"))
        self.label_9.setText(_translate("optionWindow", "Numéro de l\'écran :"))
        self.enhanceButton.setText(_translate("optionWindow", "Rehausser"))
        self.pushButtonShowPicture.setText(_translate("optionWindow", "Naviguer"))
        self.label_7.setText(_translate("optionWindow", "Valeur Z du centre: "))
        self.label_10.setText(_translate("optionWindow", "Recouvrement Horizontal :"))
        self.label_14.setText(_translate("optionWindow", "Recouvrement Vertical (SHIFT) :"))
        self.groupBoxMoveLine.setTitle(_translate("optionWindow", "Déplacement Lignes (Z)"))
        self.checkBoxMoveLeft.setText(_translate("optionWindow", "Gauche"))
        self.checkBoxMoveRight.setText(_translate("optionWindow", "Droite"))
        self.label_16.setText(_translate("optionWindow", "Horizontal (X)"))
        self.label_17.setText(_translate("optionWindow", "Vertical (Y)"))
        self.pushButtonShowIDList.setText(_translate("optionWindow", "Parcourir la liste"))
        self.toolButtonOuest.setText(_translate("optionWindow", "Ouest"))
        self.toolButtonEst.setText(_translate("optionWindow", "Est"))
        self.toolButtonNord.setText(_translate("optionWindow", "Nord"))
        self.toolButtonSud.setText(_translate("optionWindow", "Sud"))
        self.importToolVectorLayer.setText(_translate("optionWindow", "..."))
        self.pushButtonRemoveShape.setText(_translate("optionWindow", "Retirer la couche"))
        self.groupBoxMainPath.setTitle(_translate("optionWindow", "Chemin vers les photos"))
        self.importToolProject.setText(_translate("optionWindow", "..."))
        self.label_3.setText(_translate("optionWindow", "Rotation"))
        self.label_4.setText(_translate("optionWindow", "Effet miroir"))
        self.label_11.setText(_translate("optionWindow", "Polygone 3D"))

class dropedit(QtWidgets.QGroupBox):   

    def __init__(self, parent=None):
        super(dropedit, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        event.accept()
        
    def dropEvent(self, event):
        fileURL = event.mimeData().urls()[0].toString()
        try :
            fileName = fileURL.split('file:///')[1]
        except :
            fileName = fileURL.split('file:')[1]
        if os.path.isdir(fileName):
            for child in self.children(): 
                if child.metaObject().className() == "QLineEdit":
                    child.setText(fileName)

class optionWindow(QtWidgets.QMainWindow): 
    closeWindow = pyqtSignal()
    keyDrawEvent = pyqtSignal(str)
    def __init__(self):
        super(QtWidgets.QMainWindow, self).__init__()
        self.ui = Ui_optionWindow()
        self.ui.setupUi(self)
        self.ui.importToolProject.clicked.connect(self.showImportDirectory)
        self.ui.importToolVectorLayer.clicked.connect(self.showImportVector)
        self.ctrlClick = False
        self.shiftClick = False
        self.altClick = False
        self.shapePath = ""
        self.vLayer = None

    #
    def showImportDirectory(self) :
        fname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Import directory of aerial picture', os.path.dirname(os.path.abspath(__file__)))
        if fname:
            self.ui.importLineProject.setText(fname)

            
    #Ouvre une fenêtre de Qt pour choisir la couche de polygones
    def showImportVector(self):
        self.dictLayerName = {}
        for item in iface.mapCanvas().layers():
            if item.type() == QgsMapLayerType.VectorLayer and item.geometryType() == QgsWkbTypes.PolygonGeometry: 
                self.dictLayerName[item.name()] = item
        
        if self.dictLayerName : 
            self.vectorWindow = getVectorLayer(self.dictLayerName)
            self.vectorWindow.show()
            self.vectorWindow.ui.buttonBox.accepted.connect(self.importVectorAccept)
            self.vectorWindow.ui.buttonBox.rejected.connect(self.importVectorCancel)

        else :
            #No Current VectorLayer
            return

    #Création de l'objet qui réprésente la couche vectorielle
    def importVectorAccept(self):
        vLayerName = self.vectorWindow.ui.listWidget.selectedItems()[0].text()
        self.vLayer = self.dictLayerName[vLayerName]
        self.ui.importLineVectorLayer.setText(vLayerName)
        self.vectorWindow.close()

    def importVectorCancel(self):
        self.vectorWindow.close()

    def closeEvent(self,event):
        self.closeWindow.emit()

    #Fonction appelé lorsqu'une touche du clavier est appuyée
    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.ctrlClick = True
        elif event.key() == QtCore.Qt.Key_Shift :
            self.shiftClick = True
        elif event.key() == QtCore.Qt.Key_Z:    
            self.altClick = True
        elif event.key() == QtCore.Qt.Key_W:
            self.keyDrawEvent.emit("N")
        elif event.key() == QtCore.Qt.Key_A :
            self.keyDrawEvent.emit("O") 
        elif event.key() == QtCore.Qt.Key_S :
            self.keyDrawEvent.emit("S") 
        elif event.key() == QtCore.Qt.Key_D :
            self.keyDrawEvent.emit("E") 
        elif event.key() == QtCore.Qt.Key_Escape:
            self.keyDrawEvent.emit("ESC")

    def keyReleaseEvent(self, event):
        self.ctrlClick = False
        self.shiftClick = False
        self.altClick = False

