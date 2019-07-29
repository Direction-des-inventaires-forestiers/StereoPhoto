# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-graphicsWindow.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt


class Ui_graphicsWindow(object):
    def setupUi(self, graphicsWindow, nom):
        graphicsWindow.setObjectName("graphicsWindow")
        graphicsWindow.resize(800, 600)
        self.centralwidget = QtWidgets.QWidget(graphicsWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(0, 0, 791, 551))
        self.graphicsView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.graphicsView.setObjectName("graphicsView")
        graphicsWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(graphicsWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 800, 21))
        self.menubar.setObjectName("menubar")
        graphicsWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(graphicsWindow)
        self.statusbar.setObjectName("statusbar")
        graphicsWindow.setStatusBar(self.statusbar)

        self.retranslateUi(graphicsWindow, nom)
        QtCore.QMetaObject.connectSlotsByName(graphicsWindow)

    def retranslateUi(self, graphicsWindow, nom):
        _translate = QtCore.QCoreApplication.translate
        graphicsWindow.setWindowTitle(_translate("graphicsWindow", nom))

class graphicsWindow(QtWidgets.QMainWindow): 
    def __init__(self, nom):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_graphicsWindow()
        self.ui.setupUi(self, nom)
        #self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)


