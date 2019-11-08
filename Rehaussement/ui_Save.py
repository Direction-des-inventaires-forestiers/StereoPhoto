# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-Save.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_widget(object):
    def setupUi(self, widget):
        widget.setObjectName("widget")
        widget.resize(351, 404)
        self.buttonBox = QtWidgets.QDialogButtonBox(widget)
        self.buttonBox.setGeometry(QtCore.QRect(180, 370, 156, 23))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")
        self.listWidget = QtWidgets.QListWidget(widget)
        self.listWidget.setGeometry(QtCore.QRect(30, 50, 291, 311))
        self.listWidget.setObjectName("listWidget")
        item = QtWidgets.QListWidgetItem()
        item.setCheckState(QtCore.Qt.Unchecked)
        #item = self.listWidget.item(0)
        item.setText("Exemple")
        self.listWidget.addItem(item)
        self.label_9 = QtWidgets.QLabel(widget)
        self.label_9.setGeometry(QtCore.QRect(120, 10, 121, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label_9.setFont(font)
        self.label_9.setObjectName("label_9")

        self.retranslateUi(widget)
        QtCore.QMetaObject.connectSlotsByName(widget)

    def retranslateUi(self, widget):
        _translate = QtCore.QCoreApplication.translate
        widget.setWindowTitle(_translate("widget", "Sauvegarde de la sélection"))
        self.label_9.setText(_translate("widget", "Liste des photos"))
        
        #__sortingEnabled = self.listWidget.isSortingEnabled()
        #self.listWidget.setSortingEnabled(False)
        #item = self.listWidget.item(0)
        #item.setText(_translate("widget", "Exemple"))
        #self.listWidget.setSortingEnabled(__sortingEnabled)
        


