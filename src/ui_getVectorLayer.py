# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-getLayer.ui'
#
# Created by: PyQt5 UI code generator 5.14.1
#
# WARNING! All changes made in this file will be lost!


from qgis.PyQt import QtCore, QtGui, QtWidgets

class CustomListItem(QtWidgets.QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)

        # Checkbox
        self.checkbox = QtWidgets.QCheckBox()
        layout.addWidget(self.checkbox)

        # Text label
        self.label = QtWidgets.QLabel(text)
        layout.addWidget(self.label)

        # Color button
        self.color_button = QtWidgets.QPushButton("Choose Color")
        self.color_button.clicked.connect(self.choose_color)
        layout.addWidget(self.color_button)

        # Store the selected color
        self.color = QtGui.QColor(0,0,0)
        self.color_button.setStyleSheet(f"background-color: {self.color.name()};")

    def choose_color(self):
        color = QtWidgets.QColorDialog.getColor()
        if color.isValid():
            self.color = color
            self.color_button.setStyleSheet(f"background-color: {color.name()};")


class Ui_getVectorLayer(object):
    def setupUi(self, getVectorLayer):
        getVectorLayer.setObjectName("getVectorLayer")
        getVectorLayer.resize(351, 358)
        self.buttonBox = QtWidgets.QDialogButtonBox(getVectorLayer)
        self.buttonBox.setGeometry(QtCore.QRect(180, 320, 156, 23))
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        self.buttonBox.setObjectName("buttonBox")
        self.listWidget = QtWidgets.QListWidget(getVectorLayer)
        self.listWidget.setGeometry(QtCore.QRect(30, 50, 291, 261))
        self.listWidget.setObjectName("listWidget")
        #item = QtWidgets.QListWidgetItem()
        #font = QtGui.QFont()
        #font.setPointSize(12)
        #item.setFont(font)
        #item.setFlags(QtCore.Qt.ItemIsSelectable|QtCore.Qt.ItemIsDragEnabled|QtCore.Qt.ItemIsEnabled)
        #self.listWidget.addItem(item)
        self.label = QtWidgets.QLabel(getVectorLayer)
        self.label.setGeometry(QtCore.QRect(110, 10, 141, 21))
        font = QtGui.QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label.setObjectName("label")

        self.retranslateUi(getVectorLayer)
        QtCore.QMetaObject.connectSlotsByName(getVectorLayer)

    def retranslateUi(self, getVectorLayer):
        _translate = QtCore.QCoreApplication.translate
        getVectorLayer.setWindowTitle(_translate("getVectorLayer", "Choix de la couche"))
        __sortingEnabled = self.listWidget.isSortingEnabled()
        self.listWidget.setSortingEnabled(False)
        #item = self.listWidget.item(0)
        #item.setText(_translate("getVectorLayer", "New Item"))
        self.listWidget.setSortingEnabled(__sortingEnabled)
        self.label.setText(_translate("getVectorLayer", "Couche vectorielle"))

class getVectorLayerCustomList(QtWidgets.QDialog): 
    def __init__(self):
        super(getVectorLayerCustomList, self).__init__()
        self.ui = Ui_getVectorLayer()
        self.ui.setupUi(self)
        self.currentItemNames = []
    
    def setItem(self,dictName) : 
        # Adding custom items to the list widget
        for cle in dictName:
            if cle not in self.currentItemNames : 
                item = QtWidgets.QListWidgetItem()
                custom_widget = CustomListItem(cle)
                item.setSizeHint(custom_widget.sizeHint())
                self.ui.listWidget.addItem(item)
                self.ui.listWidget.setItemWidget(item, custom_widget)
                self.currentItemNames.append(cle)

        if self.ui.listWidget.count() > 0 and self.ui.listWidget.currentRow() == -1:
            self.ui.listWidget.setCurrentRow(0)

class getVectorLayer(QtWidgets.QDialog): 
    def __init__(self, dictName):
        super(getVectorLayer, self).__init__()
        self.ui = Ui_getVectorLayer()
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
            self.ui.listWidget.setCurrentRow(0)
       