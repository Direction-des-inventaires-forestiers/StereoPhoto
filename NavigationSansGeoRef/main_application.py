#from PIL import Image, ImageDraw, ImageEnhance
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_graphicsWindow import graphicsWindow
import sys, os, time, threading, math
from osgeo import gdal, ogr, osr

class app(QApplication):
    def __init__(self, argv):
        QApplication.__init__(self,argv)

        self.numeroEcranBas = 1
        self.numeroEcranHaut = 2

        self.cheminImageBas = 'c:/Users/PINFR1/OneDrive - BuroVirtuel/_Documents_U$/Photos/q18067_171_rgb.tif'
        self.cheminImageHaut = 'c:/Users/PINFR1/OneDrive - BuroVirtuel/_Documents_U$/Photos/q18067_172_rgb.tif'

        self.effetMirroir = False

        self.graphWindowHaut = graphicsWindow("Écran du haut")
        self.graphWindowBas = graphicsWindow("Écran du bas")

        self.ouvrirFenetresStereo()
        self.afficherImages()

        self.ecranActif = 'haut' #vs haut
        self.angleRotHaut = 0
        self.angleRotBas = 0

        self.graphWindowHaut.show()
        self.graphWindowHaut.ui.graphicsView.show()
        self.graphWindowBas.show()
        self.graphWindowBas.ui.graphicsView.show()

        self.zoomState = 0
        self.zoomActif = False
        self.mouvementActif = False 
        self.ignoreMouseAction = False
        self.activerFonctionSouris()

    def ouvrirFenetresStereo(self) : 

        self.screenLeft = QApplication.desktop().screenGeometry(self.numeroEcranBas)
        self.screenRight = QApplication.desktop().screenGeometry(self.numeroEcranHaut)

        self.panCenterLeft = (int(self.screenLeft.width()/2), int(self.screenLeft.height()/2))
        self.panCenterRight = (int(self.screenRight.width()/2), int(self.screenRight.height()/2))

        self.lastX = self.panCenterLeft[0]
        self.lastY = self.panCenterLeft[1] - 22

        self.leftScreenCenter = (self.screenLeft.x() + int(self.screenLeft.width()/2), self.screenLeft.y() + int(self.screenLeft.height()/2))
        
        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height())
        
        
        self.graphWindowHaut.setWindowState(Qt.WindowMaximized)
        self.graphWindowHaut.ui.graphicsView.setGeometry(rect)
        self.graphWindowHaut.ui.widget.setGeometry(rect)
        self.graphWindowHaut.move(QPoint(self.screenRight.x(), self.screenRight.y()))
        self.graphWindowHaut.cursorRectInit(self.screenRight.width(), self.screenRight.height())
        self.graphWindowHaut.keyPressed.connect(self.keyboardHandler)
        self.graphWindowHaut.setFocusPolicy(Qt.StrongFocus) 

        
        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height())

        self.graphWindowBas.setWindowState(Qt.WindowMaximized)
        self.graphWindowBas.ui.graphicsView.setGeometry(rect)
        self.graphWindowBas.ui.widget.setGeometry(rect)
        self.graphWindowBas.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))
        self.graphWindowBas.cursorRectInit(self.screenLeft.width(), self.screenLeft.height())
        self.graphWindowBas.keyPressed.connect(self.keyboardHandler)
        self.graphWindowBas.setFocusPolicy(Qt.StrongFocus) 

        

    def afficherImages(self) : 

        #Récupération de la taille complète des images
        dsBas = gdal.Open(self.cheminImageBas)
        dsHaut = gdal.Open(self.cheminImageHaut)  
        self.sizeBas = (dsBas.RasterXSize, dsBas.RasterYSize)
        self.sizeHaut = (dsHaut.RasterXSize, dsHaut.RasterYSize)
        
        self.leftRect = QRectF(0, 0, self.sizeBas[0], self.sizeBas[1])
        self.rightRect = QRectF(0, 0, self.sizeHaut[0], self.sizeHaut[1]) 
        self.graphWindowBas.currentRect = self.leftRect
        self.graphWindowHaut.currentRect = self.rightRect

        if self.effetMirroir : 
            mirror_transform = QTransform()
            mirror_transform.scale(-1, 1)
            mirror_transform.translate(-self.sizeHaut[0], 0)
            self.graphWindowHaut.ui.graphicsView.setTransform(mirror_transform)    

        r = dsBas.GetRasterBand(1).ReadAsArray()
        g = dsBas.GetRasterBand(2).ReadAsArray()
        b = dsBas.GetRasterBand(3).ReadAsArray()

        # Stack bands into RGB image (uint8)
        arr = np.dstack((r, g, b)).astype(np.uint8)

        # Convert to QImage
        bytes_per_line = 3 * self.sizeBas[0]
        q_image = QImage(arr.data, self.sizeBas[0], self.sizeBas[1], bytes_per_line, QImage.Format_RGB888)


        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        scene.addPixmap(QPixmap.fromImage(q_image))      
        self.graphWindowBas.ui.graphicsView.setScene(scene)
        dsBas = None
        
        r = dsHaut.GetRasterBand(1).ReadAsArray()
        g = dsHaut.GetRasterBand(2).ReadAsArray()
        b = dsHaut.GetRasterBand(3).ReadAsArray()

        # Stack bands into RGB image (uint8)
        arr = np.dstack((r, g, b)).astype(np.uint8)

        # Convert to QImage
        bytes_per_line = 3 * self.sizeHaut[0]
        q_image = QImage(arr.data, self.sizeHaut[0], self.sizeHaut[1], bytes_per_line, QImage.Format_RGB888)


        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        scene.addPixmap(QPixmap.fromImage(q_image))      
        self.graphWindowHaut.ui.graphicsView.setScene(scene)
        dsHaut = None

    def keyboardHandler(self, event):
        if event.type() == QEvent.KeyPress :
            if event.key() == Qt.Key_Escape :
                self.graphWindowHaut.close()
                self.graphWindowBas.close()

            elif event.key() == Qt.Key_Control : self.zoomActif = True
            elif event.key() == Qt.Key_Shift : self.mouvementActif = True 
            elif event.key() == Qt.Key_1 : self.changerEcranActif()
        else : 
            self.zoomActif = False
            self.mouvementActif = False 

    def changerEcranActif(self) :
        if self.ecranActif == 'bas' : self.ecranActif = 'haut'
        elif self.ecranActif == 'haut' : self.ecranActif = 'bas'

    def activerFonctionSouris(self) : 
        
        QCursor.setPos(self.graphWindowBas.ui.graphicsView.mapToGlobal(self.graphWindowBas.ui.graphicsView.rect().center()))
        self.graphWindowBas.ui.widget.setMouseTracking(True)
        self.graphWindowBas.activateWindow()
        self.graphWindowBas.ui.widget.mouseMoveEvent = self.moveEvent
        #self.graphWindowBas.ui.widget.mousePressEvent = self.pressEvent
        self.graphWindowBas.ui.widget.wheelEvent = self.wheelEvent
        self.graphWindowBas.setCursor(Qt.BlankCursor)

    def moveEvent(self,event) : 
        
        if self.ignoreMouseAction : 
            self.ignoreMouseAction = False
            return

        self.deltaX = int((event.x()-self.lastX)/2)
        self.lastX = event.x()
        self.deltaY = int((event.y()-self.lastY)/2)
        self.lastY = event.y()
        basView = self.graphWindowBas.ui.graphicsView
        hautView = self.graphWindowHaut.ui.graphicsView

        lhv = basView.horizontalScrollBar().value() + self.deltaX
        lvv = basView.verticalScrollBar().value() + self.deltaY

        rhv = hautView.horizontalScrollBar().value() - self.deltaX if self.effetMirroir else hautView.horizontalScrollBar().value() + self.deltaX
        rvv = hautView.verticalScrollBar().value() + self.deltaY

        if self.mouvementActif and self.ecranActif == 'bas' :
            basView.horizontalScrollBar().setValue(lhv)
            basView.verticalScrollBar().setValue(lvv) 

        elif self.mouvementActif and self.ecranActif == 'haut' : 
            hautView.horizontalScrollBar().setValue(rhv)
            hautView.verticalScrollBar().setValue(rvv)
        
        else : 
            basView.horizontalScrollBar().setValue(lhv)
            basView.verticalScrollBar().setValue(lvv)

            hautView.horizontalScrollBar().setValue(rhv)
            hautView.verticalScrollBar().setValue(rvv)


        pixRange = 200
        cursor_pos = basView.mapFromGlobal(QCursor.pos())
        centerView = basView.rect().center()
        if cursor_pos.x() <= pixRange or cursor_pos.x() >= basView.width()-pixRange or cursor_pos.y() <= pixRange or cursor_pos.y() >= basView.height()-pixRange:
            self.ignoreMouseAction = True
            QCursor.setPos(basView.mapToGlobal(centerView))
            self.lastX = centerView.x()
            self.lastY = centerView.y()


    #def pressEvent(self,event) : pass

    def wheelEvent(self,event) : 
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        
        if self.zoomActif : 
            if factor > 1 : 
                self.zoomState += 1
                ZoomInFactor = 1.1874
                self.graphWindowBas.ui.graphicsView.scale(ZoomInFactor, ZoomInFactor)
                self.graphWindowHaut.ui.graphicsView.scale(ZoomInFactor,ZoomInFactor)
            
            else :
                self.zoomState -= 1

                if self.zoomState > -2 :
                    ZoomOutFactor = 0.8421
                    self.graphWindowBas.ui.graphicsView.scale(ZoomOutFactor,ZoomOutFactor)
                    self.graphWindowHaut.ui.graphicsView.scale(ZoomOutFactor,ZoomOutFactor)

                else : 
                    self.zoomState = -1 

        elif self.mouvementActif : 
            if self.ecranActif == 'bas' : 
                currentWindow = self.graphWindowBas
                currentAngle = self.angleRotBas
                center_x = self.sizeBas[0]/2
                center_y = self.sizeBas[1]/2
            
            elif self.ecranActif == 'haut' : 
                currentWindow = self.graphWindowHaut
                currentAngle = self.angleRotHaut
                center_x = self.sizeHaut[0]/2
                center_y = self.sizeHaut[1]/2
            else : return

            transform = currentWindow.ui.graphicsView.transform()

            if factor > 1 : currentAngle += 1 
            else : currentAngle -= 1

            scale_x = math.hypot(transform.m11(), transform.m21())
            scale_y = math.hypot(transform.m12(), transform.m22())
            
            new_transform = QTransform()

            if self.effetMirroir and self.ecranActif == 'haut' : 
                new_transform.scale(-1, 1)
                new_transform.translate(-self.sizeHaut[0], 0)

            new_transform.translate(center_x, center_y)
            new_transform.rotate(currentAngle)
            new_transform.translate(-center_x, -center_y)

            new_transform.scale(scale_x, scale_y)

            currentWindow.ui.graphicsView.setTransform(new_transform)

            if self.ecranActif == 'bas' : self.angleRotBas = currentAngle
            elif self.ecranActif == 'haut' : self.angleRotHaut = currentAngle

        else : 
            basView = self.graphWindowBas.ui.graphicsView
            hautView = self.graphWindowHaut.ui.graphicsView
            if factor < 1 : 
                basView.verticalScrollBar().setValue(basView.verticalScrollBar().value() - 1)
                hautView.verticalScrollBar().setValue(hautView.verticalScrollBar().value() - 1)
                hautView.horizontalScrollBar().setValue(hautView.horizontalScrollBar().value() - 1)
                
            else :
                basView.verticalScrollBar().setValue(basView.verticalScrollBar().value() + 1)
                hautView.verticalScrollBar().setValue(hautView.verticalScrollBar().value() + 1)
                hautView.horizontalScrollBar().setValue(hautView.horizontalScrollBar().value() + 1)

if __name__ == '__main__' : 
    app = app(sys.argv)
    sys.exit(app.exec_())

exit()



