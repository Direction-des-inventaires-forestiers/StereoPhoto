# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-optionWindow.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import pyqtSignal
import os
from . import resources

class Ui_optionWindow(object):
    def setupUi(self, optionWindow):
        optionWindow.setObjectName("optionWindow")
        optionWindow.resize(436, 533)
        self.label_5 = QtWidgets.QLabel(optionWindow)
        self.label_5.setGeometry(QtCore.QRect(70, 10, 91, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_5.setFont(font)
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(optionWindow)
        self.label_6.setGeometry(QtCore.QRect(270, 10, 91, 16))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_6.setFont(font)
        self.label_6.setObjectName("label_6")
        self.groupBoxLeft = dropedit(optionWindow)
        self.groupBoxLeft.setGeometry(QtCore.QRect(10, 30, 201, 271))
        self.groupBoxLeft.setTitle("")
        self.groupBoxLeft.setObjectName("groupBoxLeft")
        self.importLineLeft = QtWidgets.QLineEdit(self.groupBoxLeft)
        self.importLineLeft.setGeometry(QtCore.QRect(10, 30, 161, 20))
        self.importLineLeft.setText("")
        self.importLineLeft.setReadOnly(True)
        self.importLineLeft.setObjectName("importLineLeft")
        self.importToolLeft = QtWidgets.QToolButton(self.groupBoxLeft)
        self.importToolLeft.setGeometry(QtCore.QRect(170, 30, 25, 19))
        self.importToolLeft.setObjectName("importToolLeft")
        self.boxOrientationLeft = QtWidgets.QComboBox(self.groupBoxLeft)
        self.boxOrientationLeft.setEnabled(False)
        self.boxOrientationLeft.setGeometry(QtCore.QRect(85, 60, 101, 22))
        self.boxOrientationLeft.setObjectName("boxOrientationLeft")
        self.boxOrientationLeft.addItem("")
        self.boxOrientationLeft.addItem("")
        self.boxOrientationLeft.addItem("")
        self.boxOrientationLeft.addItem("")
        self.label = QtWidgets.QLabel(self.groupBoxLeft)
        self.label.setEnabled(False)
        self.label.setGeometry(QtCore.QRect(10, 60, 61, 20))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.groupBoxLeft)
        self.label_2.setEnabled(False)
        self.label_2.setGeometry(QtCore.QRect(10, 100, 61, 16))
        self.label_2.setObjectName("label_2")
        self.boxMiroirLeft = QtWidgets.QComboBox(self.groupBoxLeft)
        self.boxMiroirLeft.setEnabled(False)
        self.boxMiroirLeft.setGeometry(QtCore.QRect(85, 100, 101, 22))
        self.boxMiroirLeft.setObjectName("boxMiroirLeft")
        self.boxMiroirLeft.addItem("")
        self.boxMiroirLeft.addItem("")
        self.boxMiroirLeft.addItem("")
        self.importButtonLeft = QtWidgets.QPushButton(self.groupBoxLeft)
        self.importButtonLeft.setEnabled(False)
        self.importButtonLeft.setGeometry(QtCore.QRect(65, 230, 75, 23))
        self.importButtonLeft.setObjectName("importButtonLeft")
        self.graphicsViewLeft = QtWidgets.QGraphicsView(self.groupBoxLeft)
        self.graphicsViewLeft.setGeometry(QtCore.QRect(10, 130, 181, 91))
        self.graphicsViewLeft.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewLeft.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewLeft.setObjectName("graphicsViewLeft")
        self.importDoneLeft = QtWidgets.QLabel(self.groupBoxLeft)
        self.importDoneLeft.setGeometry(QtCore.QRect(150, 233, 21, 16))
        self.importDoneLeft.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")
        self.importDoneLeft.setText("")
        self.importDoneLeft.setObjectName("importDoneLeft")
        self.groupBoxRight = dropedit(optionWindow)
        self.groupBoxRight.setGeometry(QtCore.QRect(220, 30, 201, 271))
        self.groupBoxRight.setTitle("")
        self.groupBoxRight.setObjectName("groupBoxRight")
        self.importLineRight = QtWidgets.QLineEdit(self.groupBoxRight)
        self.importLineRight.setGeometry(QtCore.QRect(10, 30, 161, 20))
        self.importLineRight.setText("")
        self.importLineRight.setReadOnly(True)
        self.importLineRight.setObjectName("importLineRight")
        self.importToolRight = QtWidgets.QToolButton(self.groupBoxRight)
        self.importToolRight.setGeometry(QtCore.QRect(170, 30, 25, 19))
        self.importToolRight.setObjectName("importToolRight")
        self.label_4 = QtWidgets.QLabel(self.groupBoxRight)
        self.label_4.setEnabled(False)
        self.label_4.setGeometry(QtCore.QRect(10, 100, 61, 16))
        self.label_4.setObjectName("label_4")
        self.label_3 = QtWidgets.QLabel(self.groupBoxRight)
        self.label_3.setEnabled(False)
        self.label_3.setGeometry(QtCore.QRect(10, 60, 61, 20))
        self.label_3.setObjectName("label_3")
        self.boxMiroirRight = QtWidgets.QComboBox(self.groupBoxRight)
        self.boxMiroirRight.setEnabled(False)
        self.boxMiroirRight.setGeometry(QtCore.QRect(85, 100, 101, 22))
        self.boxMiroirRight.setObjectName("boxMiroirRight")
        self.boxMiroirRight.addItem("")
        self.boxMiroirRight.addItem("")
        self.boxMiroirRight.addItem("")
        self.boxOrientationRight = QtWidgets.QComboBox(self.groupBoxRight)
        self.boxOrientationRight.setEnabled(False)
        self.boxOrientationRight.setGeometry(QtCore.QRect(85, 60, 101, 22))
        self.boxOrientationRight.setObjectName("boxOrientationRight")
        self.boxOrientationRight.addItem("")
        self.boxOrientationRight.addItem("")
        self.boxOrientationRight.addItem("")
        self.boxOrientationRight.addItem("")
        self.importButtonRight = QtWidgets.QPushButton(self.groupBoxRight)
        self.importButtonRight.setEnabled(False)
        self.importButtonRight.setGeometry(QtCore.QRect(65, 230, 75, 23))
        self.importButtonRight.setObjectName("importButtonRight")
        self.graphicsViewRight = QtWidgets.QGraphicsView(self.groupBoxRight)
        self.graphicsViewRight.setGeometry(QtCore.QRect(10, 130, 181, 91))
        self.graphicsViewRight.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewRight.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsViewRight.setObjectName("graphicsViewRight")
        self.importDoneRight = QtWidgets.QLabel(self.groupBoxRight)
        self.importDoneRight.setGeometry(QtCore.QRect(150, 233, 21, 16))
        self.importDoneRight.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")
        self.importDoneRight.setText("")
        self.importDoneRight.setObjectName("importDoneRight")
        self.enhanceButton = QtWidgets.QPushButton(optionWindow)
        self.enhanceButton.setEnabled(False)
        self.enhanceButton.setGeometry(QtCore.QRect(240, 320, 71, 23))
        self.enhanceButton.setCheckable(False)
        self.enhanceButton.setObjectName("enhanceButton")
        self.affichageButton = QtWidgets.QPushButton(optionWindow)
        self.affichageButton.setEnabled(False)
        self.affichageButton.setGeometry(QtCore.QRect(120, 320, 71, 23))
        self.affichageButton.setObjectName("affichageButton")
        self.groupBoxShape = QtWidgets.QGroupBox(optionWindow)
        self.groupBoxShape.setEnabled(True)
        self.groupBoxShape.setGeometry(QtCore.QRect(150, 350, 251, 161))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.groupBoxShape.setFont(font)
        self.groupBoxShape.setObjectName("groupBoxShape")
        self.importLineVectorLayer = QtWidgets.QLineEdit(self.groupBoxShape)
        self.importLineVectorLayer.setEnabled(True)
        self.importLineVectorLayer.setGeometry(QtCore.QRect(10, 40, 206, 20))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.importLineVectorLayer.setFont(font)
        self.importLineVectorLayer.setText("")
        self.importLineVectorLayer.setReadOnly(True)
        self.importLineVectorLayer.setObjectName("importLineVectorLayer")
        self.importToolVectorLayer = QtWidgets.QToolButton(self.groupBoxShape)
        self.importToolVectorLayer.setGeometry(QtCore.QRect(215, 40, 25, 19))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.importToolVectorLayer.setFont(font)
        self.importToolVectorLayer.setObjectName("importToolVectorLayer")
        self.drawButton = QtWidgets.QPushButton(self.groupBoxShape)
        self.drawButton.setEnabled(False)
        self.drawButton.setGeometry(QtCore.QRect(10, 70, 111, 23))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.drawButton.setFont(font)
        self.drawButton.setCheckable(True)
        self.drawButton.setObjectName("drawButton")
        self.cutButton = QtWidgets.QPushButton(self.groupBoxShape)
        self.cutButton.setEnabled(False)
        self.cutButton.setGeometry(QtCore.QRect(130, 70, 111, 23))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.cutButton.setFont(font)
        self.cutButton.setCheckable(True)
        self.cutButton.setObjectName("cutButton")
        self.radioButtonMerge = QtWidgets.QRadioButton(self.groupBoxShape)
        self.radioButtonMerge.setEnabled(True)
        self.radioButtonMerge.setGeometry(QtCore.QRect(45, 110, 121, 17))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.radioButtonMerge.setFont(font)
        self.radioButtonMerge.setChecked(True)
        self.radioButtonMerge.setObjectName("radioButtonMerge")
        self.radioButtonAuto = QtWidgets.QRadioButton(self.groupBoxShape)
        self.radioButtonAuto.setGeometry(QtCore.QRect(45, 130, 131, 17))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.radioButtonAuto.setFont(font)
        self.radioButtonAuto.setObjectName("radioButtonAuto")
        self.panButton = QtWidgets.QPushButton(optionWindow)
        self.panButton.setEnabled(False)
        self.panButton.setGeometry(QtCore.QRect(40, 410, 81, 23))
        font = QtGui.QFont()
        font.setPointSize(8)
        font.setBold(False)
        font.setWeight(50)
        self.panButton.setFont(font)
        self.panButton.setCheckable(True)
        self.panButton.setObjectName("panButton")
        self.groupBoxRight.raise_()
        self.label_5.raise_()
        self.label_6.raise_()
        self.groupBoxLeft.raise_()
        self.enhanceButton.raise_()
        self.affichageButton.raise_()
        self.groupBoxShape.raise_()
        self.panButton.raise_()

        self.retranslateUi(optionWindow)
        self.boxMiroirRight.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(optionWindow)

    def retranslateUi(self, optionWindow):
        _translate = QtCore.QCoreApplication.translate
        optionWindow.setWindowTitle(_translate("optionWindow", "Menu des options"))
        self.label_5.setText(_translate("optionWindow", "Image Gauche"))
        self.label_6.setText(_translate("optionWindow", "Image Droite"))
        self.importToolLeft.setText(_translate("optionWindow", "..."))
        self.boxOrientationLeft.setItemText(0, _translate("optionWindow", "0°"))
        self.boxOrientationLeft.setItemText(1, _translate("optionWindow", "90°"))
        self.boxOrientationLeft.setItemText(2, _translate("optionWindow", "180°"))
        self.boxOrientationLeft.setItemText(3, _translate("optionWindow", "270°"))
        self.label.setText(_translate("optionWindow", "Rotation"))
        self.label_2.setText(_translate("optionWindow", "Effet miroir"))
        self.boxMiroirLeft.setItemText(0, _translate("optionWindow", "Aucun"))
        self.boxMiroirLeft.setItemText(1, _translate("optionWindow", "Horizontal"))
        self.boxMiroirLeft.setItemText(2, _translate("optionWindow", "Vertical"))
        self.importButtonLeft.setText(_translate("optionWindow", "Import"))
        self.importToolRight.setText(_translate("optionWindow", "..."))
        self.label_4.setText(_translate("optionWindow", "Effet miroir"))
        self.label_3.setText(_translate("optionWindow", "Rotation"))
        self.boxMiroirRight.setItemText(0, _translate("optionWindow", "Aucun"))
        self.boxMiroirRight.setItemText(1, _translate("optionWindow", "Horizontal"))
        self.boxMiroirRight.setItemText(2, _translate("optionWindow", "Vertical"))
        self.boxOrientationRight.setItemText(0, _translate("optionWindow", "0°"))
        self.boxOrientationRight.setItemText(1, _translate("optionWindow", "90°"))
        self.boxOrientationRight.setItemText(2, _translate("optionWindow", "180°"))
        self.boxOrientationRight.setItemText(3, _translate("optionWindow", "270°"))
        self.importButtonRight.setText(_translate("optionWindow", "Import"))
        self.enhanceButton.setText(_translate("optionWindow", "Rehausser"))
        self.affichageButton.setText(_translate("optionWindow", "Afficher"))
        self.groupBoxShape.setTitle(_translate("optionWindow", "Traçage"))
        self.importToolVectorLayer.setText(_translate("optionWindow", "..."))
        self.drawButton.setText(_translate("optionWindow", "Ajouter Polygon (1)"))
        self.cutButton.setText(_translate("optionWindow", "Couper Polygon (2)"))
        self.radioButtonMerge.setText(_translate("optionWindow", "Merge Polygon (3)"))
        self.radioButtonAuto.setText(_translate("optionWindow", "Automatic Polygon (3)"))
        self.panButton.setText(_translate("optionWindow", "Naviguer"))



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
        self.ui.importToolRight.clicked.connect(self.showImportRight)
        self.ui.importToolLeft.clicked.connect(self.showImportLeft)
        self.ui.importToolVectorLayer.clicked.connect(self.showImportVector)
        self.ctrlClick = False
        self.shapePath = ""

    def showImportRight(self) :
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Import picture', os.path.dirname(os.path.abspath(__file__)),"Image (*.png, *.jpg, *.tif)")[0]
        if fname:
            self.ui.importLineRight.setText(fname)

    def showImportLeft(self) :
        fname = QtWidgets.QFileDialog.getOpenFileName(self, 'Import picture', os.path.dirname(os.path.abspath(__file__)), "Image (*.png, *.jpg, *.tif)")[0]
        if fname:
            self.ui.importLineLeft.setText(fname)
            
    def showImportVector(self):
        fname = QtWidgets.QFileDialog.getSaveFileName(self, 'Choose a path for your Vector Layer',  os.path.dirname(os.path.abspath(__file__)), "File (*.shp)")[0]
        if fname:
            self.ui.importLineVectorLayer.setText(fname)


    def closeEvent(self,event):
        self.closeWindow.emit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Control:
            self.ctrlClick = True
        elif event.key() == QtCore.Qt.Key_1:
            self.keyDrawEvent.emit("1")
        elif event.key() == QtCore.Qt.Key_2 :
            self.keyDrawEvent.emit("2") 
        elif event.key() == QtCore.Qt.Key_3:
            self.keyDrawEvent.emit("3")
        elif event.key() == QtCore.Qt.Key_Escape:
            self.keyDrawEvent.emit("ESC")

    def keyReleaseEvent(self, event):
        self.ctrlClick = False







