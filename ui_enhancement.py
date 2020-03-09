# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-enhancement.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets
from . import resources


class Ui_enhanceWindow(object):
    def setupUi(self, enhanceWindow):
        enhanceWindow.setObjectName("enhanceWindow")
        enhanceWindow.resize(1070, 750)
        self.centralwidget = QtWidgets.QWidget(enhanceWindow)
        self.centralwidget.setObjectName("centralwidget")
        #self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView = graphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(150, 40, 881, 561))
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setObjectName("graphicsView")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(50, 30, 61, 16))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(50, 80, 71, 16))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(50, 130, 61, 16))
        self.label_3.setObjectName("label_3")
        self.spinBoxRed = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxRed.setGeometry(QtCore.QRect(50, 270, 61, 22))
        self.spinBoxRed.setMinimum(-100)
        self.spinBoxRed.setMaximum(100)
        self.spinBoxRed.setSingleStep(5)
        self.spinBoxRed.setObjectName("spinBoxRed")
        self.spinBoxGreen = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxGreen.setGeometry(QtCore.QRect(50, 330, 61, 22))
        self.spinBoxGreen.setMinimum(-100)
        self.spinBoxGreen.setMaximum(100)
        self.spinBoxGreen.setSingleStep(5)
        self.spinBoxGreen.setObjectName("spinBoxGreen")
        self.spinBoxBlue = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxBlue.setGeometry(QtCore.QRect(50, 390, 61, 22))
        self.spinBoxBlue.setMinimum(-100)
        self.spinBoxBlue.setMaximum(100)
        self.spinBoxBlue.setSingleStep(5)
        self.spinBoxBlue.setObjectName("spinBoxBlue")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(50, 180, 47, 13))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(50, 250, 47, 13))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(50, 310, 47, 13))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setGeometry(QtCore.QRect(50, 370, 47, 13))
        self.label_7.setObjectName("label_7")
        self.buttonBoxReset = QtWidgets.QDialogButtonBox(self.centralwidget)
        self.buttonBoxReset.setGeometry(QtCore.QRect(40, 550, 81, 23))
        self.buttonBoxReset.setStandardButtons(QtWidgets.QDialogButtonBox.Reset)
        self.buttonBoxReset.setObjectName("buttonBoxReset")
        self.applyButton = QtWidgets.QPushButton(self.centralwidget)
        self.applyButton.setGeometry(QtCore.QRect(860, 630, 71, 23))
        self.applyButton.setObjectName("applyButton")
        self.spinBoxContrast = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxContrast.setGeometry(QtCore.QRect(50, 50, 62, 22))
        self.spinBoxContrast.setMinimum(-100)
        self.spinBoxContrast.setMaximum(100)
        self.spinBoxContrast.setSingleStep(5)
        self.spinBoxContrast.setObjectName("spinBoxContrast")
        self.spinBoxLuminosite = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxLuminosite.setGeometry(QtCore.QRect(50, 100, 62, 22))
        self.spinBoxLuminosite.setMinimum(-100)
        self.spinBoxLuminosite.setMaximum(100)
        self.spinBoxLuminosite.setSingleStep(5)
        self.spinBoxLuminosite.setObjectName("spinBoxLuminosite")
        self.spinBoxSaturation = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxSaturation.setGeometry(QtCore.QRect(50, 150, 62, 22))
        self.spinBoxSaturation.setMinimum(-100)
        self.spinBoxSaturation.setMaximum(100)
        self.spinBoxSaturation.setSingleStep(5)
        self.spinBoxSaturation.setObjectName("spinBoxSaturation")
        self.spinBoxNettete = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxNettete.setGeometry(QtCore.QRect(50, 200, 62, 22))
        self.spinBoxNettete.setMinimum(-100)
        self.spinBoxNettete.setMaximum(100)
        self.spinBoxNettete.setSingleStep(5)
        self.spinBoxNettete.setObjectName("spinBoxNettete")
        self.zoomInButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomInButton.setEnabled(False)
        self.zoomInButton.setGeometry(QtCore.QRect(160, 620, 30, 30))
        self.zoomInButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/Anaglyph/Icons/zoomIn.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomInButton.setIcon(icon)
        self.zoomInButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomInButton.setObjectName("zoomInButton")
        self.zoomOutButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomOutButton.setEnabled(False)
        self.zoomOutButton.setGeometry(QtCore.QRect(200, 620, 30, 30))
        self.zoomOutButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/Anaglyph/Icons/zoomOut.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomOutButton.setIcon(icon1)
        self.zoomOutButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomOutButton.setObjectName("zoomOutButton")
        self.zoomPanButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomPanButton.setEnabled(False)
        self.zoomPanButton.setGeometry(QtCore.QRect(240, 620, 30, 30))
        self.zoomPanButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/Anaglyph/Icons/panOption.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomPanButton.setIcon(icon2)
        self.zoomPanButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomPanButton.setCheckable(True)
        self.zoomPanButton.setObjectName("zoomPanButton")
        self.groupBoxMinMax = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBoxMinMax.setEnabled(True)
        self.groupBoxMinMax.setGeometry(QtCore.QRect(20, 435, 120, 101))
        self.groupBoxMinMax.setCheckable(True)
        self.groupBoxMinMax.setChecked(False)
        self.groupBoxMinMax.setObjectName("groupBoxMinMax")
        self.radioButtonComplete = QtWidgets.QRadioButton(self.groupBoxMinMax)
        self.radioButtonComplete.setEnabled(False)
        self.radioButtonComplete.setGeometry(QtCore.QRect(20, 25, 91, 17))
        self.radioButtonComplete.setChecked(True)
        self.radioButtonComplete.setObjectName("radioButtonComplete")
        self.radioButtonCurrent = QtWidgets.QRadioButton(self.groupBoxMinMax)
        self.radioButtonCurrent.setEnabled(False)
        self.radioButtonCurrent.setGeometry(QtCore.QRect(20, 50, 91, 17))
        self.radioButtonCurrent.setObjectName("radioButtonCurrent")
        self.currentStatusButton = QtWidgets.QPushButton(self.groupBoxMinMax)
        self.currentStatusButton.setEnabled(False)
        self.currentStatusButton.setGeometry(QtCore.QRect(20, 70, 75, 23))
        self.currentStatusButton.setObjectName("currentStatusButton")
        self.cancelButton = QtWidgets.QPushButton(self.centralwidget)
        self.cancelButton.setGeometry(QtCore.QRect(940, 630, 75, 23))
        self.cancelButton.setObjectName("cancelButton")
        self.groupBoxPicture = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBoxPicture.setGeometry(QtCore.QRect(30, 590, 81, 61))
        self.groupBoxPicture.setTitle("")
        self.groupBoxPicture.setObjectName("groupBoxPicture")
        self.radioButtonPremiere = QtWidgets.QRadioButton(self.groupBoxPicture)
        self.radioButtonPremiere.setGeometry(QtCore.QRect(10, 20, 82, 17))
        self.radioButtonPremiere.setChecked(True)
        self.radioButtonPremiere.setObjectName("radioButtonPremiere")
        self.radioButtonDeuxieme = QtWidgets.QRadioButton(self.groupBoxPicture)
        self.radioButtonDeuxieme.setGeometry(QtCore.QRect(10, 40, 82, 17))
        self.radioButtonDeuxieme.setObjectName("radioButtonDeuxieme")
        enhanceWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(enhanceWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1070, 21))
        self.menubar.setObjectName("menubar")
        enhanceWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(enhanceWindow)
        self.statusbar.setObjectName("statusbar")
        enhanceWindow.setStatusBar(self.statusbar)

        self.retranslateUi(enhanceWindow)
        QtCore.QMetaObject.connectSlotsByName(enhanceWindow)

    def retranslateUi(self, enhanceWindow):
        _translate = QtCore.QCoreApplication.translate
        enhanceWindow.setWindowTitle(_translate("enhanceWindow", "Rehaussement des couleurs"))
        self.label.setText(_translate("enhanceWindow", "Constraste"))
        self.label_2.setText(_translate("enhanceWindow", "Luminosité"))
        self.label_3.setText(_translate("enhanceWindow", "Saturation"))
        self.label_4.setText(_translate("enhanceWindow", "Netteté"))
        self.label_5.setText(_translate("enhanceWindow", "Rouge"))
        self.label_6.setText(_translate("enhanceWindow", "Vert"))
        self.label_7.setText(_translate("enhanceWindow", "Bleu"))
        self.applyButton.setText(_translate("enhanceWindow", "Appliquer"))
        self.groupBoxMinMax.setTitle(_translate("enhanceWindow", "Min/Max"))
        self.radioButtonComplete.setText(_translate("enhanceWindow", "Vue complète"))
        self.radioButtonCurrent.setText(_translate("enhanceWindow", "Vue courrante"))
        self.currentStatusButton.setText(_translate("enhanceWindow", "Conserver"))
        self.cancelButton.setText(_translate("enhanceWindow", "Annuler"))
        self.radioButtonPremiere.setText(_translate("enhanceWindow", "Photo 1"))
        self.radioButtonDeuxieme.setText(_translate("enhanceWindow", "Photo 2"))


class graphicsView(QtWidgets.QGraphicsView):
    def __init__(self, parent=None):
        super(graphicsView, self).__init__(parent)
    
    def resizeEvent(self, ev):
        QtWidgets.QGraphicsView.resizeEvent(self, ev)
        self.fitInView(self.sceneRect(), QtCore.Qt.KeepAspectRatio)
  

class enhanceWindow(QtWidgets.QMainWindow): 
    def __init__(self):
        super(enhanceWindow, self).__init__()
        self.ui = Ui_enhanceWindow()
        self.initSize = self.size()
        self.ui.setupUi(self)

    
    #Revoir cette méthode, semble inversé le state un fois lancé, jamais State maximized quand on le max seulement quand on réduit ---> à décalage!
    def resizeEvent(self, event) :
        QtWidgets.QMainWindow.resizeEvent(self, event)
        if self.windowState() == QtCore.Qt.WindowMaximized:
            if event.size().width() > 1070 :

                #Taille original 1070,750
                difX = event.size().width() - event.oldSize().width()
                self.pixelX = difX
                difY = event.size().height() - event.oldSize().height()
                self.pixelY = difY


                #Augmenter 2e param pour déplacer vers le bas
                geo = self.ui.zoomPanButton.geometry()
                self.ui.zoomPanButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.zoomInButton.geometry()
                self.ui.zoomInButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.zoomOutButton.geometry()
                self.ui.zoomOutButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                #Augmenter 1er et 2e param pour déplacer vers droite et bas
                geo = self.ui.cancelButton.geometry()
                self.ui.cancelButton.setGeometry(QtCore.QRect(geo.x()+difX, geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.applyButton.geometry()
                self.ui.applyButton.setGeometry(QtCore.QRect(geo.x()+difX, geo.y()+difY, geo.width(), geo.height()))

                #Augmenter 3e et 4e param pour augmenter la taille vers la droite et vers le bas
                geo = self.ui.graphicsView.geometry()
                self.ui.graphicsView.setGeometry(QtCore.QRect(geo.x(), geo.y(), geo.width()+difX, geo.height()+difY))





                
        