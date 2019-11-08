# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-colorWindow.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
import resources


class Ui_colorWindow(object):
    def setupUi(self, colorWindow):
        colorWindow.setObjectName("colorWindow")
        colorWindow.resize(1070, 703)
        self.centralwidget = QtWidgets.QWidget(colorWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(150, 100, 551, 511))
        self.graphicsView.setObjectName("graphicsView")
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(50, 120, 61, 16))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.centralwidget)
        self.label_2.setGeometry(QtCore.QRect(50, 170, 71, 16))
        self.label_2.setObjectName("label_2")
        self.label_3 = QtWidgets.QLabel(self.centralwidget)
        self.label_3.setGeometry(QtCore.QRect(50, 220, 61, 16))
        self.label_3.setObjectName("label_3")
        self.spinBoxContrast = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.spinBoxContrast.setGeometry(QtCore.QRect(50, 140, 62, 22))
        self.spinBoxContrast.setMinimum(-1.0)
        self.spinBoxContrast.setMaximum(4.0)
        self.spinBoxContrast.setSingleStep(0.05)
        self.spinBoxContrast.setObjectName("spinBoxContrast")
        self.spinBoxLuminosite = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.spinBoxLuminosite.setGeometry(QtCore.QRect(50, 190, 62, 22))
        self.spinBoxLuminosite.setMinimum(-1.0)
        self.spinBoxLuminosite.setMaximum(4.0)
        self.spinBoxLuminosite.setSingleStep(0.05)
        self.spinBoxLuminosite.setObjectName("spinBoxLuminosite")
        self.spinBoxSaturation = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.spinBoxSaturation.setGeometry(QtCore.QRect(50, 240, 62, 22))
        self.spinBoxSaturation.setMinimum(-1.0)
        self.spinBoxSaturation.setMaximum(4.0)
        self.spinBoxSaturation.setSingleStep(0.05)
        self.spinBoxSaturation.setObjectName("spinBoxSaturation")
        self.spinBoxRed = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxRed.setGeometry(QtCore.QRect(50, 370, 61, 22))
        self.spinBoxRed.setMinimum(-100)
        self.spinBoxRed.setMaximum(100)
        self.spinBoxRed.setSingleStep(5)
        self.spinBoxRed.setObjectName("spinBoxRed")
        self.spinBoxGreen = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxGreen.setGeometry(QtCore.QRect(50, 430, 61, 22))
        self.spinBoxGreen.setMinimum(-100)
        self.spinBoxGreen.setMaximum(100)
        self.spinBoxGreen.setSingleStep(5)
        self.spinBoxGreen.setObjectName("spinBoxGreen")
        self.spinBoxBlue = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxBlue.setGeometry(QtCore.QRect(50, 490, 61, 22))
        self.spinBoxBlue.setMinimum(-100)
        self.spinBoxBlue.setMaximum(100)
        self.spinBoxBlue.setSingleStep(5)
        self.spinBoxBlue.setObjectName("spinBoxBlue")
        self.spinBoxNettete = QtWidgets.QDoubleSpinBox(self.centralwidget)
        self.spinBoxNettete.setGeometry(QtCore.QRect(50, 300, 62, 22))
        self.spinBoxNettete.setMinimum(-1.0)
        self.spinBoxNettete.setMaximum(4.0)
        self.spinBoxNettete.setSingleStep(0.05)
        self.spinBoxNettete.setObjectName("spinBoxNettete")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(50, 280, 47, 13))
        self.label_4.setObjectName("label_4")
        self.checkBoxMinMax = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBoxMinMax.setGeometry(QtCore.QRect(50, 530, 70, 17))
        self.checkBoxMinMax.setObjectName("checkBoxMinMax")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(50, 350, 47, 13))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(50, 410, 47, 13))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setGeometry(QtCore.QRect(50, 470, 47, 13))
        self.label_7.setObjectName("label_7")
        self.buttonBoxReset = QtWidgets.QDialogButtonBox(self.centralwidget)
        self.buttonBoxReset.setGeometry(QtCore.QRect(40, 570, 81, 23))
        self.buttonBoxReset.setStandardButtons(QtWidgets.QDialogButtonBox.Reset)
        self.buttonBoxReset.setObjectName("buttonBoxReset")
        self.groupBox = dropedit(self.centralwidget)
        self.groupBox.setGeometry(QtCore.QRect(20, 10, 1041, 71))
        self.groupBox.setTitle("")
        self.groupBox.setObjectName("groupBox")
        self.lineEdit = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit.setGeometry(QtCore.QRect(200, 40, 661, 20))
        self.lineEdit.setObjectName("lineEdit")
        self.toolButton = QtWidgets.QToolButton(self.groupBox)
        self.toolButton.setGeometry(QtCore.QRect(860, 40, 25, 19))
        self.toolButton.setObjectName("toolButton")
        self.label_9 = QtWidgets.QLabel(self.groupBox)
        self.label_9.setGeometry(QtCore.QRect(420, 10, 251, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")
        self.saveAll = QtWidgets.QPushButton(self.centralwidget)
        self.saveAll.setGeometry(QtCore.QRect(880, 630, 91, 23))
        self.saveAll.setEnabled(False)
        self.saveAll.setObjectName("saveAll")
        self.tableView = QtWidgets.QTableView(self.centralwidget)
        self.tableView.setGeometry(QtCore.QRect(740, 130, 311, 481))
        self.tableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableView.setAutoScroll(False)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setVisible(False)
        self.tableView.verticalHeader().setVisible(False)
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setGeometry(QtCore.QRect(780, 100, 231, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.saveSelection = QtWidgets.QPushButton(self.centralwidget)
        self.saveSelection.setGeometry(QtCore.QRect(720, 630, 141, 23))
        self.saveSelection.setEnabled(False)
        self.saveSelection.setObjectName("saveSelection")
        self.saveCurrent = QtWidgets.QPushButton(self.centralwidget)
        self.saveCurrent.setGeometry(QtCore.QRect(550, 630, 151, 23))
        self.saveCurrent.setEnabled(False)
        self.saveCurrent.setObjectName("saveCurrent")
        self.saveImage = QtWidgets.QLabel(self.centralwidget)
        self.saveImage.setGeometry(QtCore.QRect(990, 625, 21, 31))
        self.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")
        self.saveImage.setText("")
        self.saveImage.setObjectName("saveImage")
        colorWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(colorWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 1070, 21))
        self.menubar.setObjectName("menubar")
        colorWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(colorWindow)
        self.statusbar.setObjectName("statusbar")
        colorWindow.setStatusBar(self.statusbar)

        self.retranslateUi(colorWindow)
        QtCore.QMetaObject.connectSlotsByName(colorWindow)

    def retranslateUi(self, colorWindow):
        _translate = QtCore.QCoreApplication.translate
        colorWindow.setWindowTitle(_translate("colorWindow", "Rehaussement des couleurs"))
        self.label.setText(_translate("colorWindow", "Constraste"))
        self.label_2.setText(_translate("colorWindow", "Luminosité"))
        self.label_3.setText(_translate("colorWindow", "Saturation"))
        self.label_4.setText(_translate("colorWindow", "Netteté"))
        self.checkBoxMinMax.setText(_translate("colorWindow", "Min/Max"))
        self.label_5.setText(_translate("colorWindow", "Rouge"))
        self.label_6.setText(_translate("colorWindow", "Vert"))
        self.label_7.setText(_translate("colorWindow", "Bleu"))
        self.toolButton.setText(_translate("colorWindow", "..."))
        self.label_9.setText(_translate("colorWindow", "Importation du dossier de photos"))
        self.saveAll.setText(_translate("colorWindow", "Enregistrer Tout"))
        self.label_8.setText(_translate("colorWindow", "Liste des photos dans le dossier"))
        self.saveSelection.setText(_translate("colorWindow", "Enregistrer une sélection"))
        self.saveCurrent.setText(_translate("colorWindow", "Enregistrer l\'image en cours"))


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


class tableModel(QtCore.QAbstractListModel):
    def __init__(self, data):
        super(tableModel,self).__init__()
        self.data = data

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.data) 
 
    def data(self, index, role): 
        if index.isValid() and role == QtCore.Qt.DisplayRole:
            return QtCore.QVariant(self.data[index.row()])
        else: 
            return QtCore.QVariant()

class colorWindow(QtWidgets.QMainWindow): 

    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_colorWindow()
        self.ui.setupUi(self)