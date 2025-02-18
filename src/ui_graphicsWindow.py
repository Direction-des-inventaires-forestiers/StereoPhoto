# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui-graphicsWindow.ui'
#
# Created by: PyQt5 UI code generator 5.12.2
#
# WARNING! All changes made in this file will be lost!

from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt
import os

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
        self.graphicsView.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.graphicsView.setBackgroundBrush(QtGui.QBrush(QtGui.QColor(182,182,182)))
        self.graphicsView.setObjectName("graphicsView")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(170, 110, 1000, 1200))
        self.widget.setObjectName("widget")
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
    keyPressed = QtCore.pyqtSignal(QtGui.QKeyEvent)
    def __init__(self, nom):
        QtWidgets.QMainWindow.__init__(self)
        self.ui = Ui_graphicsWindow()
        self.ui.setupUi(self, nom)
        self.ui.graphicsView.resizeEvent = self.gwResizeEvent
        self.currentRect = None
        self.myRect = QtCore.QRect()
        self.myPen = QtGui.QPen()
        self.rayon = 20
        self.ui.widget.paintEvent = self.draw
        
        cursorPath =  ":/Anaglyph/Icons/cursor3x3.png"
        cursorImage = QtGui.QImage(cursorPath)
        cursorPix = QtGui.QPixmap.fromImage(cursorImage)
        self.invisibleCursor = QtGui.QCursor(cursorPix)
        self.normalCursor = self.cursor()
        #self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint | Qt.WindowMaximizeButtonHint | Qt.WindowMinimizeButtonHint)

    def keyPressEvent(self, event):
        if self.isActiveWindow() : self.keyPressed.emit(event)
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if self.isActiveWindow() : self.keyPressed.emit(event)
        super().keyReleaseEvent(event)

    #Détermine la position du curseur 
    def cursorRectInit(self, x, y, extra=0):
        x = int(x/2) 
        y = int(y/2)
        r = self.rayon
        self.myRect = QtCore.QRect(x-r, y-r, 2*r, 2*r)
        self.vLine = QtCore.QLineF(x-r, y, x+r, y)
        self.hLine = QtCore.QLineF(x, y-r, x, y+r)
        self.ui.widget.update()

    #Fonction qui dessine le curseur au centre de l'image
    def draw(self, event):
        p = QtGui.QPainter()
        p.begin(self.ui.widget)
        pen = QtGui.QPen(QtGui.QColor(0, 255, 255),3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        rect = self.myRect
        p.setPen(pen)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        #p.drawEllipse(rect)
        p.drawLine(self.vLine) 
        p.drawLine(self.hLine)
        p.end()

    def gwResizeEvent(self, event):
        if self.currentRect :
            self.ui.graphicsView.fitInView(self.currentRect, Qt.KeepAspectRatio)
        QtWidgets.QGraphicsView.resizeEvent(self.ui.graphicsView,event)