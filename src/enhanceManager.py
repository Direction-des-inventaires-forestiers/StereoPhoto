'''
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient plusieurs classes qui réalise le traitement d'imageries des fichiers TIF de grandes tailles

La première classe (enhanceManager) gère la QMainWindow qui offre un interface utilisateur de rehaussement
Sur la MainWindow il est possible de :
    - modifier le constraste, la saturation, la luminosité et la netteté
    - ajouter du rouge, du vert ou du bleu dans l'image. 
    - couper les valeurs RGB en dessous de 5% et au dessus de 95% de l'histogramme
    - effectuer l'opération Min/Max en considérant seulement la région observée seulement 
    - Zoom et Pan disponible avec la souris pour faciliter la navigation et l'observation
    - Changer entre les deux photos importées dans le menu des options
    - Appliquer le rehaussement sur les photos affichées sur les écrans planars

La deuxième classe (threadShow) gère l'affichage des images de grandes résolutions via un thread
Elle s'occupe de modifier les images en fonctions des paramètres demandés (rehaussement, rotation, miroir)
La photo en cours est affiché en 3 temps. Chaque itération du thread augmente la résolution de l'image 
se qui permet d'observer la photo rehaussée dans son entièreté
Elle expédie l'image par petite portion.

La troisième classe (imageEnhancing) réalise les fonctions de traitement d'image
Elle applique le constraste, la saturation, la luminosité et la netteté, l'ajout de couleur et le facteur min/max

La fonction pictureLayout réalise les effets de rotation et de miroir

Optimisation futur 
    Gestion des photos à 4 couches (RGBA) et à une seule couche (Grayscale)
'''

import numpy as np

from qgis.gui import *
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *


from .ui_enhancement import enhanceWindow
import sys, os, time, threading, traceback, gc
from scipy.ndimage import uniform_filter
from osgeo import gdal
from math import ceil


#Gestionnaire de la QMainWindow qui permet le rehaussement d'image
class enhanceManager(QObject):
    listParamSignal = pyqtSignal(list)
    def __init__(self, pathLeft, pathRight, listParam=[],nameLeft='',nameRight=''):
        QObject.__init__(self)
        self.pathLeft = pathLeft
        self.pathRight = pathRight

        self.prevListParam = listParam
    
        self.colorWindow = enhanceWindow()
        self.colorWindow.ui.radioButtonPremiere.setText(nameLeft)
        self.colorWindow.ui.radioButtonDeuxieme.setText(nameRight)
        self.colorWindow.ui.radioButtonCurrent.toggled.connect(self.currentViewActivate)
        self.colorWindow.ui.radioButtonPremiere.toggled.connect(self.switchPicture)
        self.colorWindow.ui.currentStatusButton.pressed.connect(self.keepCurrentView)
        self.colorWindow.ui.applyButton.pressed.connect(self.applyEnhance)
        self.colorWindow.ui.cancelButton.pressed.connect(self.cancelEnhance)
        self.colorWindow.closeEvent = self.cancelEnhance
        
        self.spinBoxesTimer = QTimer(self)
        self.spinBoxesTimer.setSingleShot(True)
        self.spinBoxesTimer.timeout.connect(self.enhancePicture)
        
        self.scene = QGraphicsScene(self.colorWindow.ui.graphicsView)
        self.colorWindow.ui.graphicsView.setScene(self.scene)
        self.colorWindow.show()

        self.statusKeepCurrentView = False

        self.colorWindow.ui.zoomInButton.clicked.connect(self.zoomIn)
        self.colorWindow.ui.zoomOutButton.clicked.connect(self.zoomOut)
        
        self.colorWindow.setWindowState(Qt.WindowMaximized)

        self.zoomState = 0
        self.setConnection(True)
        self.colorWindow.ui.buttonBoxReset.clicked.connect(self.reset)
        
        if self.prevListParam :
            self.reset("set")
        else:
            self.reset()
    
    #Remet la photo à son affichage d'origine ou à l'état en cours du rehaussement
    def reset(self, setBox=False) : 
        self.setConnection(False)
        if setBox == "set" :
            self.setBoxValues() 
        else :
            self.resetBox()
        self.enhancePicture("reset")
        self.setConnection(True)

    def removeCurrentScene(self) : 

        if hasattr(self, "tSeek"):
            if self.tSeek.showThreadInProcess : 
                self.tSeek.blockSignals(True)
                self.tSeek.keepRunning = False
                self.tSeek.wait()
                self.tSeek.showThreadInProcess = False
            del self.tSeek
        
        for item in list(self.scene.items()):
            if isinstance(item, QGraphicsPixmapItem):
                self.scene.removeItem(item)
        
        gc.collect()
        QApplication.processEvents()

    #Fonction appeler pour démarrer le rehaussement
    #Elle affiche le rehaussement sur une version de basse résolution 
    #puis lance un thread pour gérer les images de plus grande résolution
    #Elle peut annoncer au thread d'annuler son processus 
    #si elle désire repartir le traitement avec des nouveaux paramètres
    def enhancePicture(self, ajustView=False):

        self.removeCurrentScene()
        
        self.getBoxValues(ajustView)
        if self.colorWindow.ui.radioButtonPremiere.isChecked():        
            currentPath = self.pathLeft
        else :
            currentPath = self.pathRight

        pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
        GV = self.colorWindow.ui.graphicsView
        pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
        self.tSeek = threadShow(currentPath, pointZero, pointMax, self.listParam)
        self.tSeek.newImage.connect(self.addPixmap)
        self.tSeek.finished.connect(self.seekDone)
        self.tSeek.setOverview()
        
        self.tSeek.start(QThread.IdlePriority)
        
        if ajustView == "reset":
            self.colorWindow.ui.graphicsView.fitInView(self.tSeek.rect, Qt.KeepAspectRatio)
            self.zoomState = 0

        
    #Fonction appelée par le emit du thread pour ajouter une portion de l'image sur l'affichage
    def addPixmap(self, pixmap, scaleFactor, topX, topY) :
        d = self.colorWindow.ui.graphicsView.scene().addPixmap(pixmap)
        d.setScale(scaleFactor)
        d.setOffset(topX, topY)
    
    #Fonction exécutée lorsque le thread d'affichage se termine
    #Elle relance le thread avec la même résolution si une requête a été faite sinon
    #elle relance le thread avec une plus grande résolution d'image 
    def seekDone(self):
        sender = self.sender()
        sender.showThreadInProcess = False
        gc.collect()
        QApplication.processEvents()

    #Fonction qui permet de réaliser le Pan 
    def mMoveEvent(self, ev):
        if self.colorWindow.ui.zoomPanButton.isChecked() :
            gView = self.colorWindow.ui.graphicsView
            delta = ev.pos() - self.panPosition
            gView.horizontalScrollBar().setValue(gView.horizontalScrollBar().value() - delta.x())
            gView.verticalScrollBar().setValue(gView.verticalScrollBar().value() - delta.y())
            self.panPosition = ev.pos()

    #Fonction qui détecte que la souris a été cliquée pour faire le Pan, elle enregistre la position
    def mPressEvent(self, ev):
        self.panPosition = ev.pos()
        self.pressPosition = ev.pos()

    #Fonction qui détecte que la souris a été relâchée à la fin du Pan
    def mReleaseEvent(self, ev):
        if self.colorWindow.ui.zoomPanButton.isChecked():
            #Conserver et additioner le delta? 
            delta = ev.pos() - self.pressPosition
            if abs(delta.x()) > 100 or abs(delta.y()) > 100 :
                if self.colorWindow.ui.radioButtonCurrent.isChecked() and self.statusKeepCurrentView == False :
                    self.enhancePicture(1)  

    #Fonction qui permet le zoom avec la roulette de la souris
    #Elle permet aussi de "zoomer" en considérant la position de la souris comme point central
    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        
        oldPos = self.colorWindow.ui.graphicsView.mapToScene(event.pos())
        
        if factor > 1 : 
            self.zoomIn(True)
        else :
            self.zoomOut(True)

        newPos = self.colorWindow.ui.graphicsView.mapToScene(event.pos())
        delta = newPos - oldPos

        self.colorWindow.ui.graphicsView.setTransformationAnchor(QGraphicsView.NoAnchor)
        self.colorWindow.ui.graphicsView.translate(delta.x(), delta.y())
        self.colorWindow.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        if self.colorWindow.ui.radioButtonCurrent.isChecked() and self.statusKeepCurrentView == False:
            self.enhancePicture(1)
    
    #Fonction qui permet d'agrandir la taille de l'image via un Zoom avant
    def zoomIn(self, pressed):

        self.zoomState += 1
        ZoomInFactor = 1.1874
        self.colorWindow.ui.graphicsView.scale(ZoomInFactor, ZoomInFactor)
        
    #Fonction qui permet de réduire la taille de l'image via un Zoom arrière
    def zoomOut(self, pressed):

        self.zoomState -= 1

        if self.zoomState > -2 :
            ZoomOutFactor = 0.8421
            self.colorWindow.ui.graphicsView.scale(ZoomOutFactor,ZoomOutFactor)

        else : 
            self.zoomState = -1 
    
    #Retourne les paramètres de rehaussement désirés
    def applyEnhance(self) : 
        self.getBoxValues()
        self.listParamSignal.emit(self.listParam)
        self.cancelEnhance()

    #Ferme la fenêtre sans conserver les paramètres modifiés
    def cancelEnhance(self,event=None):
        self.removeCurrentScene()
        self.scene.clear()
        self.colorWindow.close()

    def closeEvent(self,event):
        self.cancelEnhance()

    #Permet de changer la photo selon les 2 déjà importées
    def switchPicture(self, value) :
        self.enhancePicture("reset")
        
    #Fonction appellée quand le checkbox min/max est utilisé
    #Active les radios button du groupBox Min/Max
    def minmaxActivate(self, value):
        self.colorWindow.ui.radioButtonCurrent.setEnabled(False)
        self.colorWindow.ui.radioButtonComplete.setEnabled(value)
        self.enhancePicture(value)

    #Fonction pour activer le bouton de conservation de l'histogramme 
    def currentViewActivate(self, value):
        self.colorWindow.ui.currentStatusButton.setEnabled(value)
        self.enhancePicture(value)

    #Gestion du choix de la conservation des valeurs min/max de l'histogramme
    def keepCurrentView(self):
        self.statusKeepCurrentView = not self.statusKeepCurrentView
        if self.statusKeepCurrentView :
            self.colorWindow.ui.currentStatusButton.setText("Modifier")
        else :
            self.colorWindow.ui.currentStatusButton.setText("Conserver")
            self.enhancePicture(True)

    def startSpinboxesTimer(self,value):
        self.spinBoxesTimer.start(250)
    
    #Active/Desactive les connections des différents objets (boutons) de l'application
    def setConnection(self, enable) : 

        self.colorWindow.ui.zoomInButton.setEnabled(enable)
        self.colorWindow.ui.zoomOutButton.setEnabled(enable)
        self.colorWindow.ui.zoomPanButton.setEnabled(enable)

        if enable : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxSaturation.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxNettete.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxRed.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxGreen.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxBlue.valueChanged.connect(self.startSpinboxesTimer)
            self.colorWindow.ui.groupBoxMinMax.toggled.connect(self.minmaxActivate)
            self.colorWindow.ui.graphicsView.mouseMoveEvent = self.mMoveEvent
            self.colorWindow.ui.graphicsView.mousePressEvent = self.mPressEvent
            self.colorWindow.ui.graphicsView.mouseReleaseEvent = self.mReleaseEvent
            self.colorWindow.ui.graphicsView.wheelEvent = self.wheelEvent   
        else : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.disconnect(self.startSpinboxesTimer)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.disconnect(self.startSpinboxesTimer)   
            self.colorWindow.ui.spinBoxSaturation.valueChanged.disconnect(self.startSpinboxesTimer)   
            self.colorWindow.ui.spinBoxNettete.valueChanged.disconnect(self.startSpinboxesTimer)  
            self.colorWindow.ui.spinBoxRed.valueChanged.disconnect(self.startSpinboxesTimer) 
            self.colorWindow.ui.spinBoxGreen.valueChanged.disconnect(self.startSpinboxesTimer) 
            self.colorWindow.ui.spinBoxBlue.valueChanged.disconnect(self.startSpinboxesTimer) 
            self.colorWindow.ui.groupBoxMinMax.toggled.disconnect(self.minmaxActivate)
            self.colorWindow.ui.graphicsView.mouseMoveEvent = QGraphicsView.mouseMoveEvent 
            self.colorWindow.ui.graphicsView.mousePressEvent = QGraphicsView.mousePressEvent
            self.colorWindow.ui.graphicsView.wheelEvent = QGraphicsView.wheelEvent
            self.colorWindow.ui.graphicsView.mouseReleaseEvent = QGraphicsView.mouseReleaseEvent

    #Permet de mettre les paramètres de rehaussement à leur origine
    def resetBox(self) : 
        self.colorWindow.ui.spinBoxContrast.setValue(0)
        self.colorWindow.ui.spinBoxLuminosite.setValue(0)   
        self.colorWindow.ui.spinBoxSaturation.setValue(0)   
        self.colorWindow.ui.spinBoxNettete.setValue(0)  
        self.colorWindow.ui.spinBoxRed.setValue(0) 
        self.colorWindow.ui.spinBoxGreen.setValue(0) 
        self.colorWindow.ui.spinBoxBlue.setValue(0) 
        self.colorWindow.ui.groupBoxMinMax.setChecked(False)
    
    #Retourne les valeurs des paramètres de rehaussement dans une liste
    def getBoxValues(self, changePixVal=False): 
        con = self.colorWindow.ui.spinBoxContrast.value()
        lum = self.colorWindow.ui.spinBoxLuminosite.value()   
        sat = self.colorWindow.ui.spinBoxSaturation.value()   
        net = self.colorWindow.ui.spinBoxNettete.value()  
        red = self.colorWindow.ui.spinBoxRed.value() 
        gre = self.colorWindow.ui.spinBoxGreen.value() 
        blu = self.colorWindow.ui.spinBoxBlue.value() 
        bmm = self.colorWindow.ui.groupBoxMinMax.isChecked()
        
        cv = self.colorWindow.ui.radioButtonCurrent.isChecked()

        pix = []

        #Cas activiation avec les boutons MIN/MAX (push et radio buttons et checkbox) du GUI
        if cv and changePixVal and self.statusKeepCurrentView == False :
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            pix = self.calculHistogram(pointZero, pointMax)
            self.currentPixVal = pix

        #Cas activation avec les options de rehaussement (spinBox)
        #Avec un certain recule je ne suis pas certain que cette option soit pertinante puisqu'on pert l'histogramme qu'on souhaite conserver
        #Aucune influence sans déplacement, y a-t-il une raison pour avoir cette fonctionnalité? À réfléchir
        elif cv and self.statusKeepCurrentView and type(changePixVal) is int:
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            pix = self.calculHistogram(pointZero, pointMax)
            self.currentPixVal = pix
       
        elif cv :
            pix = self.currentPixVal

        self.listParam = [con, lum, sat, net, red, gre, blu, bmm, cv, pix]

    #Fonction pour rétablir les anciennes valeurs de rehaussement sauvegardées lors de la fermeture par le bouton Appliquer
    def setBoxValues(self) :

        self.colorWindow.ui.spinBoxContrast.setValue(self.prevListParam[0])
        self.colorWindow.ui.spinBoxLuminosite.setValue(self.prevListParam[1])   
        self.colorWindow.ui.spinBoxSaturation.setValue(self.prevListParam[2])   
        self.colorWindow.ui.spinBoxNettete.setValue(self.prevListParam[3])  
        self.colorWindow.ui.spinBoxRed.setValue(self.prevListParam[4]) 
        self.colorWindow.ui.spinBoxGreen.setValue(self.prevListParam[5]) 
        self.colorWindow.ui.spinBoxBlue.setValue(self.prevListParam[6])
        self.colorWindow.ui.groupBoxMinMax.setChecked(self.prevListParam[7])

        if self.prevListParam[7] :
            self.colorWindow.ui.radioButtonCurrent.setEnabled(False)
            self.colorWindow.ui.radioButtonComplete.setEnabled(True)
            if self.prevListParam[8] :
                self.statusKeepCurrentView = True
                self.colorWindow.ui.currentStatusButton.setText("Modifier")
                self.colorWindow.ui.currentStatusButton.setEnabled(True)
                self.colorWindow.ui.groupBoxMinMax.setChecked(True)
                self.colorWindow.ui.radioButtonCurrent.toggled.disconnect(self.currentViewActivate)
                self.colorWindow.ui.radioButtonCurrent.setChecked(False)
                self.colorWindow.ui.radioButtonCurrent.toggled.connect(self.currentViewActivate)
                self.currentPixVal = self.prevListParam[9]
                    

            
    #Calcul de l'histogramme sur une portion de la photo lorsque l'on veut conserver le min/max pour la vue courante
    def calculHistogram(self, top, low):

        return [0,255,0,255,0,255]
        h = self.picture.crop((top.x(), top.y(), low.x(), low.y())).histogram()
        a = sum(h)
        cutValue = [round(a*0.05/3), round(a*0.95/3), round(a*1.05/3), round(a*1.95/3), round(a*2.05/3), round(a*2.95/3)]
        pixValue = []
        b = 0
        c = 0
        for i in range(len(h)):
            b += h[i] 
            if b > cutValue[c] : 
                i = i % 256
                pixValue.append(i)
                c += 1
                if c == 6 :
                    break
        return pixValue
    
class threadShow(QThread):
    newImage = pyqtSignal(QPixmap, float, int, int)
    
    def __init__(self, picturePath, pointZero, pointMax, listParam, cropValue=None):
        super().__init__()
        self.picturePath = picturePath
        self.pointZero = pointZero
        self.pointMax = pointMax
        self.listParam = listParam
        self.cropValue = cropValue
        self.perform_Enhancing = True if self.listParam[:8] != [0,0,0,0,0,0,0,False] else False
        self.keepRunning = True
        self.showThreadInProcess = False 

        # Open GDAL dataset ONCE here
        gdal.SetCacheMax(256 * 1024 * 1024)
        self.ds = gdal.Open(self.picturePath, gdal.GA_ReadOnly)
        self.height = self.ds.RasterYSize
        self.width = self.ds.RasterXSize
        self.rect = QRectF(0,0,self.width,self.height)
        if self.ds is None:
            raise ValueError("Cannot open image")
        
    def setOverview(self) : 
        
        self.stats, overViewArray = self.get_global_stats_from_overview()

        if overViewArray is not None: 
            overViewArray = self.applyEnhancements(overViewArray,self.listParam)
            he, wi, _ = overViewArray.shape
            q_image = QImage(overViewArray.data, wi, he, wi*3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scale = min(self.width/self.widthOverview, self.height/self.heightOverview)
            self.newImage.emit(pixmap, scale, self.overviewStartX, self.overviewStartY)
        
        
        
    
    def run(self):

        self.showThreadInProcess = True 
        maxX, maxY = 2048,2048 
        
        if self.cropValue is not None:
            x0 = self.cropValue[0]
            y0 = self.cropValue[1]
            x1 = self.cropValue[2]
            y1 = self.cropValue[3]
        else:
            x0 = 0
            y0 = 0
            x1 = self.width
            y1 = self.height

        topX = max(x0, int(self.pointZero.x() - 1024))
        topY = max(y0, int(self.pointZero.y() - 1024))
        lowX = min(x1, int(self.pointMax.x() + 1024))
        lowY = min(y1, int(self.pointMax.y() + 1024))


        middleRect = [topX, topY, lowX, lowY]
        firstRect = [x0,y0,topX, y1]
        secondRect = [lowX, y0, x1, y1]
        thridRect = [topX, y0, lowX, topY]
        fourthRect = [topX, lowY, lowX, y1]
        
        rects = [middleRect, firstRect, secondRect, thridRect, fourthRect]

        for item in rects:
            nbDivX = ceil((item[2] - item[0]) / maxX)
            nbDivY = ceil((item[3] - item[1]) / maxY)
            currentTopX, currentTopY = item[0], item[1]
            
            for x in range(nbDivX):
                currentLowX = min(currentTopX + maxX, item[2])
                for y in range(nbDivY):
                    if not self.keepRunning:
                        return
                    currentLowY = min(currentTopY + maxY, item[3])
                    
                    # Load ONLY this tile from disk
                    tile_width = currentLowX - currentTopX
                    tile_height = currentLowY - currentTopY
                    
                    tile = self.loadImageTile(
                        xoff=currentTopX,
                        yoff=currentTopY,
                        xsize=tile_width,
                        ysize=tile_height
                    )
                    if self.perform_Enhancing : tile = self.applyEnhancements(tile,self.listParam)
                    h, w, _ = tile.shape
                    q_image = QImage(tile.data, w, h, w*3, QImage.Format_RGB888)
                    pixmap = QPixmap.fromImage(q_image)

                    self.newImage.emit(pixmap, 1, currentTopX, currentTopY)
                    
                    del tile
                    
                    currentTopY += maxY
                currentTopX += maxX
                currentTopY = item[1]
    
    def loadImageTile(self, xoff=0, yoff=0, xsize=None, ysize=None, bands=[1,2,3]):
        """Load a specific tile from the GDAL dataset"""
        if xsize is None:
            xsize = self.ds.RasterXSize - xoff
        if ysize is None:
            ysize = self.ds.RasterYSize - yoff

        band_arrays = []
        for idx in bands:
            band = self.ds.GetRasterBand(idx)
            arr = band.ReadAsArray(xoff, yoff, xsize, ysize)
            band_arrays.append(arr)
        img = np.stack(band_arrays, axis=2) 
        return img 

    def applyEnhancements(self, arr, params):
        arr = arr.astype(np.float32, copy=False)

        # --- Min–Max Stretch ---
        if params[7]:  # stretch flag
            stats = []
            if self.stats is None : 
                for c in range(3) : 
                    ch = arr[:,:,c]
                    low, high = np.percentile(ch, [5, 95])
                    stats.append((low, high))

            else : stats = self.stats

            lows  = np.array([s[0] for s in self.stats], np.float32).reshape(1,1,3)
            highs = np.array([s[1] for s in self.stats], np.float32).reshape(1,1,3)

            # In-place: (arr - lows) / (highs - lows) * 255
            arr -= lows               
            arr /= (highs - lows)  
            arr *= 255.0    
        

        # Contrast
        contrast = params[0]
        if contrast != 0:
            if contrast > 0:
                if contrast < 50:
                    factor = 1 + (0.02 * contrast)  # 1.0 to 2.0
                elif contrast < 80:
                    factor = 2 + (0.1 * (contrast - 50))  # 2.0 to 5.0
                else:
                    factor = 5 + (contrast - 80)  # 5.0 to 25.0
            else:
                factor = 1 + (contrast / 100)

            # Convert to grayscale using PIL weights
            grayscale = (arr[:, :, 0] * 0.299 + 
                        arr[:, :, 1] * 0.587 + 
                        arr[:, :, 2] * 0.114)
            
            # Get mean of grayscale
            mean = float(grayscale.mean())
            for c in range(3):
                channel = arr[:, :, c]
                channel[:] = mean + (channel - mean) * factor

        #Saturation
        saturation = params[2]
        if saturation != 0:

            if saturation > 0:
                factor = 1 + (0.05 * saturation)
            else:
                factor = 1 + (saturation / 100)
            
            # Convert to grayscale using PIL weights
            grayscale = (arr[:, :, 0] * 0.299 + 
                        arr[:, :, 1] * 0.587 + 
                        arr[:, :, 2] * 0.114)
            
            
            for c in range(3):
                channel = arr[:, :, c]
                channel[:] = grayscale + (channel - grayscale) * factor


        # R/G/B adjustment
        for i, ch_param in enumerate(params[4:7]):
            if ch_param != 0:
                factor = 1.0 + (ch_param / 100.0)
                arr[:,:,i] *= factor


        # Sharpness 
        sharpness = params[3]
        if sharpness != 0:
            sharp_factor = sharpness / 10.0 + 1  
            blurred = uniform_filter(arr,size=(3, 3, 1))
            arr[:] = blurred + (arr - blurred) * sharp_factor
                  
        # Brightness
        brightness = params[1]
        if brightness != 0:
            arr += 128 * (brightness / 100.0)

        # Final clamp
        np.clip(arr, 0, 255, out=arr)

        return arr.astype(np.uint8, copy=False)


    
    def get_global_stats_from_overview(self,band_numbers=[1,2,3], lower=5, upper=95):
        stats = []
        band_arrays = []
        for bandNumber in band_numbers:
            band = self.ds.GetRasterBand(bandNumber)

            ovr_count = band.GetOverviewCount()
            if ovr_count > 0:
                ovr_band = band.GetOverview(3)
                self.widthOverview = ovr_band.XSize
                self.heightOverview = ovr_band.YSize
                if self.cropValue is not None: 
                    
                    scale = min(self.width/self.widthOverview, self.height/self.heightOverview)
                    oX = max(0,int(self.cropValue[0]/ scale))
                    oY = max(0,int(self.cropValue[1]/ scale))
                    sX = min(self.widthOverview ,int((self.cropValue[2] - self.cropValue[0])/ scale))
                    sY = min(self.heightOverview,int((self.cropValue[3] - self.cropValue[1])/ scale))

                    arr = ovr_band.ReadAsArray(oX,oY,sX,sY).astype(np.float32)
                    self.overviewStartX = oX
                    self.overviewStartY = oY 

                
                else : 
                    arr = ovr_band.ReadAsArray().astype(np.float32)
                    self.overviewStartX = 0
                    self.overviewStartY = 0 

            else:
                return None, None

            arr_flat = arr[np.isfinite(arr)]

            # percentile min/max stretch values
            low, high = np.percentile(arr_flat, [lower, upper])

            stats.append((low, high))

            band_arrays.append(arr)
        
        img = np.stack(band_arrays, axis=2)
        return stats, img
    
