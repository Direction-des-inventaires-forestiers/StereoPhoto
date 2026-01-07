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
        colorWindow.resize(1070, 750)
        self.centralwidget = QtWidgets.QWidget(colorWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(150, 100, 551, 511))
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
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
        self.spinBoxRed = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxRed.setGeometry(QtCore.QRect(50, 360, 61, 22))
        self.spinBoxRed.setMinimum(-100)
        self.spinBoxRed.setMaximum(100)
        self.spinBoxRed.setSingleStep(5)
        self.spinBoxRed.setObjectName("spinBoxRed")
        self.spinBoxGreen = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxGreen.setGeometry(QtCore.QRect(50, 420, 61, 22))
        self.spinBoxGreen.setMinimum(-100)
        self.spinBoxGreen.setMaximum(100)
        self.spinBoxGreen.setSingleStep(5)
        self.spinBoxGreen.setObjectName("spinBoxGreen")
        self.spinBoxBlue = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxBlue.setGeometry(QtCore.QRect(50, 480, 61, 22))
        self.spinBoxBlue.setMinimum(-100)
        self.spinBoxBlue.setMaximum(100)
        self.spinBoxBlue.setSingleStep(5)
        self.spinBoxBlue.setObjectName("spinBoxBlue")
        self.label_4 = QtWidgets.QLabel(self.centralwidget)
        self.label_4.setGeometry(QtCore.QRect(50, 270, 47, 13))
        self.label_4.setObjectName("label_4")
        self.label_5 = QtWidgets.QLabel(self.centralwidget)
        self.label_5.setGeometry(QtCore.QRect(50, 340, 47, 13))
        self.label_5.setObjectName("label_5")
        self.label_6 = QtWidgets.QLabel(self.centralwidget)
        self.label_6.setGeometry(QtCore.QRect(50, 400, 47, 13))
        self.label_6.setObjectName("label_6")
        self.label_7 = QtWidgets.QLabel(self.centralwidget)
        self.label_7.setGeometry(QtCore.QRect(50, 460, 47, 13))
        self.label_7.setObjectName("label_7")
        self.buttonBoxReset = QtWidgets.QDialogButtonBox(self.centralwidget)
        self.buttonBoxReset.setGeometry(QtCore.QRect(40, 640, 81, 23))
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
        self.saveButton = QtWidgets.QPushButton(self.centralwidget)
        self.saveButton.setEnabled(False)
        self.saveButton.setGeometry(QtCore.QRect(880, 630, 91, 23))
        self.saveButton.setObjectName("saveButton")
        self.tableView = QtWidgets.QTableView(self.centralwidget)
        self.tableView.setGeometry(QtCore.QRect(740, 130, 311, 481))
        self.tableView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.tableView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tableView.setAutoScroll(False)
        self.tableView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.tableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
        self.tableView.setObjectName("tableView")
        self.tableView.horizontalHeader().setVisible(False)
        self.tableView.verticalHeader().setVisible(False)
        self.label_8 = QtWidgets.QLabel(self.centralwidget)
        self.label_8.setGeometry(QtCore.QRect(780, 100, 231, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_8.setFont(font)
        self.label_8.setObjectName("label_8")
        self.saveImage = QtWidgets.QLabel(self.centralwidget)
        self.saveImage.setGeometry(QtCore.QRect(990, 625, 21, 31))
        self.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")
        self.saveImage.setText("")
        self.saveImage.setObjectName("saveImage")
        self.checkBoxSave = QtWidgets.QCheckBox(self.centralwidget)
        self.checkBoxSave.setEnabled(True)
        self.checkBoxSave.setGeometry(QtCore.QRect(1035, 110, 16, 17))
        self.checkBoxSave.setText("")
        self.checkBoxSave.setObjectName("checkBoxSave")
        self.checkBoxSave.setVisible(False)
        self.spinBoxContrast = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxContrast.setGeometry(QtCore.QRect(50, 140, 62, 22))
        self.spinBoxContrast.setMinimum(-100)
        self.spinBoxContrast.setMaximum(100)
        self.spinBoxContrast.setSingleStep(5)
        self.spinBoxContrast.setObjectName("spinBoxContrast")
        self.spinBoxLuminosite = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxLuminosite.setGeometry(QtCore.QRect(50, 190, 62, 22))
        self.spinBoxLuminosite.setMinimum(-100)
        self.spinBoxLuminosite.setMaximum(100)
        self.spinBoxLuminosite.setSingleStep(5)
        self.spinBoxLuminosite.setObjectName("spinBoxLuminosite")
        self.spinBoxSaturation = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxSaturation.setGeometry(QtCore.QRect(50, 240, 62, 22))
        self.spinBoxSaturation.setMinimum(-100)
        self.spinBoxSaturation.setMaximum(100)
        self.spinBoxSaturation.setSingleStep(5)
        self.spinBoxSaturation.setObjectName("spinBoxSaturation")
        self.spinBoxNettete = QtWidgets.QSpinBox(self.centralwidget)
        self.spinBoxNettete.setGeometry(QtCore.QRect(50, 290, 62, 22))
        self.spinBoxNettete.setMinimum(-100)
        self.spinBoxNettete.setMaximum(100)
        self.spinBoxNettete.setSingleStep(5)
        self.spinBoxNettete.setObjectName("spinBoxNettete")
        self.zoomInButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomInButton.setEnabled(False)
        self.zoomInButton.setGeometry(QtCore.QRect(160, 620, 30, 30))
        self.zoomInButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap(":/Rehaussement/Icons/zoomIn.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomInButton.setIcon(icon)
        self.zoomInButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomInButton.setObjectName("zoomInButton")
        self.zoomOutButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomOutButton.setEnabled(False)
        self.zoomOutButton.setGeometry(QtCore.QRect(200, 620, 30, 30))
        self.zoomOutButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon1 = QtGui.QIcon()
        icon1.addPixmap(QtGui.QPixmap(":/Rehaussement/Icons/zoomOut.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomOutButton.setIcon(icon1)
        self.zoomOutButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomOutButton.setObjectName("zoomOutButton")
        self.zoomPanButton = QtWidgets.QPushButton(self.centralwidget)
        self.zoomPanButton.setEnabled(False)
        self.zoomPanButton.setGeometry(QtCore.QRect(240, 620, 30, 30))
        self.zoomPanButton.setStyleSheet("background-color:rgba(200, 200, 200);")
        icon2 = QtGui.QIcon()
        icon2.addPixmap(QtGui.QPixmap(":/Rehaussement/Icons/panOption.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.zoomPanButton.setIcon(icon2)
        self.zoomPanButton.setIconSize(QtCore.QSize(30, 30))
        self.zoomPanButton.setCheckable(True)
        self.zoomPanButton.setObjectName("zoomPanButton")
        self.groupBoxMinMax = QtWidgets.QGroupBox(self.centralwidget)
        self.groupBoxMinMax.setEnabled(True)
        self.groupBoxMinMax.setGeometry(QtCore.QRect(20, 525, 120, 101))
        self.groupBoxMinMax.setCheckable(True)
        self.groupBoxMinMax.setChecked(False)
        self.groupBoxMinMax.setObjectName("groupBoxMinMax")
        self.radioButtonComplete = QtWidgets.QRadioButton(self.groupBoxMinMax)
        self.radioButtonComplete.setEnabled(False)
        self.radioButtonComplete.setGeometry(QtCore.QRect(20, 25, 82, 17))
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
        self.label_5.setText(_translate("colorWindow", "Rouge"))
        self.label_6.setText(_translate("colorWindow", "Vert"))
        self.label_7.setText(_translate("colorWindow", "Bleu"))
        self.toolButton.setText(_translate("colorWindow", "..."))
        self.label_9.setText(_translate("colorWindow", "Importation du dossier de photos"))
        self.saveButton.setText(_translate("colorWindow", "Enregistrer"))
        self.label_8.setText(_translate("colorWindow", "Liste des photos dans le dossier"))
        self.groupBoxMinMax.setTitle(_translate("colorWindow", "Min/Max"))
        self.radioButtonComplete.setText(_translate("colorWindow", "Vue complète"))
        self.radioButtonCurrent.setText(_translate("colorWindow", "Vue courante"))
        self.currentStatusButton.setText(_translate("colorWindow", "Conserver"))




class dropedit(QtWidgets.QGroupBox):   
    dropHappen = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        super(dropedit, self).__init__(parent)
        self.setAcceptDrops(True)
        self.importList = []

    def dragEnterEvent(self, event):
        event.accept()
        
    def dropEvent(self, event):
        self.importList = event.mimeData().urls()
        fileURL = event.mimeData().urls()[0].toString()
        try :
            fileName = fileURL.split('file:///')[1]
        except :
            fileName = fileURL.split('file:')[1]
        for child in self.children(): 
            if child.metaObject().className() == "QLineEdit":
                child.setText(fileName)
                self.dropHappen.emit()


class tableModel(QtCore.QAbstractTableModel):
    def __init__(self, data):
        super(tableModel,self).__init__()
        self.data = data
        self.currentSelect = (0,0)

    def rowCount(self, parent=QtCore.QModelIndex()): 
        return len(self.data) 

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def flags(self, index):
        if index.isValid() and index.column() == 1 : 
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable       
        else : 
            return QtCore.Qt.ItemFlags(QtCore.QAbstractTableModel.flags(self, index))

 
    def data(self, index, role): 
        if index.isValid(): #and role == QtCore.Qt.DisplayRole:
            if index.column() == 0 and role == QtCore.Qt.DisplayRole:
                return QtCore.QVariant(self.data[index.row()][0])
            if index.column() == 1 and role == QtCore.Qt.CheckStateRole:
                if self.data[index.row()][1].isChecked() :
                    return QtCore.Qt.Checked
                else : 
                    return QtCore.Qt.Unchecked
            if role == QtCore.Qt.BackgroundRole and (index.row(), index.column()) == self.currentSelect:
                return QtGui.QBrush(QtGui.QColor(30,144,255))
            if role == QtCore.Qt.BackgroundRole and (index.row(), index.column()) != self.currentSelect:
                return QtGui.QBrush(QtGui.QColor(255,255,255))

        else: 
            return QtCore.QVariant()

    
    def setData(self, index, value, role): 
        if index.isValid():
            if index.column() == 1 and role == QtCore.Qt.CheckStateRole:
                if value == 0 :
                    self.data[index.row()][1].setChecked(False)
                if value == 2 : 
                    self.data[index.row()][1].setChecked(True)
            self.dataChanged.emit(index, index)
            return True
        return False


class colorWindow(QtWidgets.QMainWindow): 
    def __init__(self):
        super(colorWindow,self).__init__()
        self.ui = Ui_colorWindow()
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

                #Augmenter 1er param pour déplacer au centre de la fenetre vers la droite
                geo = self.ui.label_9.geometry()
                self.ui.label_9.setGeometry(QtCore.QRect(geo.x()+int(difX/2), geo.y(), geo.width(), geo.height()))
                
                geo = self.ui.lineEdit.geometry()
                self.ui.lineEdit.setGeometry(QtCore.QRect(geo.x()+int(difX/2), geo.y(), geo.width(), geo.height()))
                
                geo = self.ui.toolButton.geometry()
                self.ui.toolButton.setGeometry(QtCore.QRect(geo.x()+int(difX/2), geo.y(), geo.width(), geo.height()))

                #augmenter 3e param pour augmenter la taille vers la droite
                geo = self.ui.groupBox.geometry()
                self.ui.groupBox.setGeometry(QtCore.QRect(geo.x(), geo.y(), geo.width()+difX, geo.height()))

                #Augmenter 1er param pour déplacer vers la droite
                geo = self.ui.label_8.geometry()
                self.ui.label_8.setGeometry(QtCore.QRect(geo.x()+difX, geo.y(), geo.width(), geo.height()))

                geo = self.ui.checkBoxSave.geometry()
                self.ui.checkBoxSave.setGeometry(QtCore.QRect(geo.x()+difX, geo.y(), geo.width(), geo.height()))

                #Augmenter 2e param pour déplacer vers le bas
                geo = self.ui.zoomPanButton.geometry()
                self.ui.zoomPanButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.zoomInButton.geometry()
                self.ui.zoomInButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.zoomOutButton.geometry()
                self.ui.zoomOutButton.setGeometry(QtCore.QRect(geo.x(), geo.y()+difY, geo.width(), geo.height()))

                #Augmenter 1er et 2e param pour déplacer vers droite et bas
                geo = self.ui.saveImage.geometry()
                self.ui.saveImage.setGeometry(QtCore.QRect(geo.x()+difX, geo.y()+difY, geo.width(), geo.height()))

                geo = self.ui.saveButton.geometry()
                self.ui.saveButton.setGeometry(QtCore.QRect(geo.x()+difX, geo.y()+difY, geo.width(), geo.height()))

                #Augmenter 1er et 4e param pour déplacer vers la droite et augmenter la taille vers le bas
                geo = self.ui.tableView.geometry()
                self.ui.tableView.setGeometry(QtCore.QRect(geo.x()+difX, geo.y(), geo.width(), geo.height()+difY))

                #Augmenter 3e et 4e param pour augmenter la taille vers la droite et vers le bas
                geo = self.ui.graphicsView.geometry()
                self.ui.graphicsView.setGeometry(QtCore.QRect(geo.x(), geo.y(), geo.width()+difX, geo.height()+difY))





                
        