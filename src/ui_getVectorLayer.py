# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-getLayer.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.core import *


class Ui_getVectorList(object):
    def setupUi(self, getVectorList):
        getVectorList.setObjectName("getVectorList")
        getVectorList.resize(391, 358)
        self.buttonBox = QtWidgets.QDialogButtonBox(getVectorList)
        self.buttonBox.setGeometry(QtCore.QRect(180, 320, 156, 23))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")
        self.tableWidget = QtWidgets.QTableWidget(0, 4,getVectorList)
        self.tableWidget.setHorizontalHeaderLabels(["Afficher", "Nom de la couche", "Couleur", "Altitude 3D"])
        self.tableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        header = self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents) 
        self.tableWidget.setColumnWidth(3, 70) 
        self.tableWidget.setGeometry(QtCore.QRect(30, 50, 331, 261))
        self.tableWidget.setObjectName("tableWidget")
        self.label = QtWidgets.QLabel(getVectorList)
        self.label.setGeometry(QtCore.QRect(120, 10, 260, 21)) 
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName("label")

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

    def setItem(self,vectorLayers) : 
        # Adding custom items to the list widget
        currentVectorNames = []
        for cle in vectorLayers:
            currentVectorNames.append(cle)
            if cle not in self.currentItemNames : 
                row_position = self.ui.tableWidget.rowCount()
                self.ui.tableWidget.insertRow(row_position)

                # Column 0: checkbox
                checkbox_item = QtWidgets.QCheckBox()
                checkbox_item.setChecked(False)
                self.ui.tableWidget.setCellWidget(row_position, 0, checkbox_item)

                # Column 1: name text
                name_item = QtWidgets.QTableWidgetItem(cle)
                self.ui.tableWidget.setItem(row_position, 1, name_item)

                # Column 2: color button
                color_button = QtWidgets.QPushButton("Choisir Couleur")
                color_button.setStyleSheet(f"background-color: {QtGui.QColor(0,0,0).name()};")
                color_button.setProperty("color", QtGui.QColor(0,0,0))
                color_button.clicked.connect(lambda _, r=row_position: self.choose_color(r))
                self.ui.tableWidget.setCellWidget(row_position, 2, color_button)

                # Column 3: altitude checkbox
                checkbox_3d = QtWidgets.QCheckBox()
                checkbox_3d.setChecked(False)
                if QgsWkbTypes.hasZ(vectorLayers[cle].wkbType()) : checkbox_3d.setEnabled(True)
                else : checkbox_3d.setEnabled(False)
        
                self.ui.tableWidget.setCellWidget(row_position, 3, checkbox_3d)

                self.currentItemNames.append(cle)

        for currentItem in self.currentItemNames[:] : 
            if currentItem not in currentVectorNames : 
                for row in reversed(range(self.ui.tableWidget.rowCount())):  
                    item = self.ui.tableWidget.item(row, 1)
                    if item and item.text() == currentItem:
                        self.ui.tableWidget.removeRow(row)
                        self.currentItemNames.remove(currentItem)
                        break

        
    def choose_color(self,row):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            button = self.ui.tableWidget.cellWidget(row, 2)
            if button: 
                button.setStyleSheet(f"background-color: {color.name()};")
                button.setProperty("color", color)
                

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
       