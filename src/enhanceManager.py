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
from PIL import Image, ImageDraw, ImageEnhance
import numpy as np

from qgis.gui import *
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *

from .ui_enhancement import enhanceWindow
import sys, os, time, qimage2ndarray, threading
from math import ceil

Image.MAX_IMAGE_PIXELS = 1000000000 

#from win32com.shell import shell, shellcon
#file to save current project shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + "\\appRehaussement"

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
        self.colorWindow.ui.graphicsView.show()
        self.colorWindow.show()

        self.showThreadInProcess = False
        self.newRequest = False
        self.statusKeepCurrentView = False

        self.colorWindow.ui.zoomInButton.clicked.connect(self.zoomIn)
        self.colorWindow.ui.zoomOutButton.clicked.connect(self.zoomOut)
        
        self.colorWindow.setWindowState(Qt.WindowMaximized)

        self.firstPicture = True
        self.loadPicture(self.pathLeft)
    
    #Fonction de lancement du chargement d'une nouvelle photo
    def loadPicture(self, path) : 
        self.picture = Image.open(path)

        if hasattr(self.picture, "n_frames") and self.picture.n_frames > 4:
            self.picture.seek(3)
            self.isTIF = True

        elif self.picture.size[0] > self.picture.size[1] :
            self.picture = self.picture.resize((1000,700))
            self.isTIF = False
        else :
            self.picture = self.picture.resize((700,1000))
            self.isTIF = False

        self.zoomState = 0

        if self.firstPicture : 
            self.setConnection(True)
            self.colorWindow.ui.buttonBoxReset.clicked.connect(self.reset)
            self.firstPicture = False
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

    #Fonction appeler pour démarrer le rehaussement
    #Elle affiche le rehaussement sur une version de basse résolution 
    #puis lance un thread pour gérer les images de plus grande résolution
    #Elle peut annoncer au thread d'annuler son processus 
    #si elle désire repartir le traitement avec des nouveaux paramètres
    def enhancePicture(self, ajustView):
        if hasattr(self, "tSeek"): 
            try :
                self.tSeek.newImage.disconnect(self.addPixmap)
            except: 
                pass
            self.tSeek.keepRunning = False

        self.getBoxValues(ajustView)
        t = imageEnhancing(self.picture, self.listParam)
        t.start()
        r = t.join()      
        p = Image.merge("RGB", (r[0],r[1],r[2]))   
        pictureArray = np.array(p)

        a = qimage2ndarray.array2qimage(pictureArray)
        scene = QGraphicsScene()
        scene.addPixmap(QPixmap.fromImage(a))
        self.colorWindow.ui.graphicsView.setScene(scene)

        if ajustView == "reset":
            self.colorWindow.ui.graphicsView.fitInView(self.colorWindow.ui.graphicsView.sceneRect(), Qt.KeepAspectRatio)
            self.zoomState = 0

        
        if self.isTIF :
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            if self.showThreadInProcess == False :
                self.threadSeekNewQuality(pointZero, pointMax, 4, 1, 0.25)
                self.showThreadInProcess = True
            else :
                self.newRequest = True
    
    #Fonction qui permet de lancer le thread d'affichage des images de plus grande qualité
    def threadSeekNewQuality(self, pointZero, pointMax, multiFactor, seekFactor, scaleFactor):

        if self.colorWindow.ui.radioButtonPremiere.isChecked():        
            currentPath = self.pathLeft
        else :
            currentPath = self.pathRight
        self.getBoxValues()
        self.tSeek = threadShow(currentPath, pointZero, pointMax, multiFactor, seekFactor, scaleFactor, self.listParam)
        self.tSeek.newImage.connect(self.addPixmap)
        self.tSeek.finished.connect(self.seekDone)
        self.showThreadInProcess = True
        self.newRequest = False
        self.tSeek.start(QThread.IdlePriority)
    
    #Fonction appelée par le emit du thread pour ajouter une portion de l'image sur l'affichage
    def addPixmap(self, pixmap, scaleFactor, topX, topY) :
        d = self.colorWindow.ui.graphicsView.scene().addPixmap(pixmap)
        d.setScale(scaleFactor)
        d.setOffset(topX, topY)
    
    #Fonction exécutée lorsque le thread d'affichage se termine
    #Elle relance le thread avec la même résolution si une requête a été faite sinon
    #elle relance le thread avec une plus grande résolution d'image 
    def seekDone(self):

        if self.newRequest : 
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekNewQuality(pointZero, pointMax, 4, 1, 0.25)

        elif self.tSeek.seekFactor == 1 :
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekNewQuality(pointZero, pointMax, 8, 0, 0.125)

        else :
            self.showThreadInProcess = False

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
    def cancelEnhance(self):
        scene = QGraphicsScene()
        self.colorWindow.ui.graphicsView.setScene(scene)
        self.colorWindow.close()

    #Permet de changer la photo selon les 2 déjà importées
    def switchPicture(self, value) :
        if self.colorWindow.ui.radioButtonPremiere.isChecked():
            self.loadPicture(self.pathLeft)
        else :
            self.loadPicture(self.pathRight)
        self.enhancePicture("reset")
        
    #Fonction appellée quand le checkbox min/max est utilisé
    #Active les radios button du groupBox Min/Max
    def minmaxActivate(self, value):
        self.colorWindow.ui.radioButtonCurrent.setEnabled(value)
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

    #Active/Desactive les connections des différents objets (boutons) de l'application
    def setConnection(self, enable) : 

        self.colorWindow.ui.zoomInButton.setEnabled(enable)
        self.colorWindow.ui.zoomOutButton.setEnabled(enable)
        self.colorWindow.ui.zoomPanButton.setEnabled(enable)

        if enable : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxSaturation.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxNettete.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxRed.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxGreen.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxBlue.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.groupBoxMinMax.toggled.connect(self.minmaxActivate)
            self.colorWindow.ui.graphicsView.mouseMoveEvent = self.mMoveEvent
            self.colorWindow.ui.graphicsView.mousePressEvent = self.mPressEvent
            self.colorWindow.ui.graphicsView.mouseReleaseEvent = self.mReleaseEvent
            self.colorWindow.ui.graphicsView.wheelEvent = self.wheelEvent   
        else : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.disconnect(self.enhancePicture)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.disconnect(self.enhancePicture)   
            self.colorWindow.ui.spinBoxSaturation.valueChanged.disconnect(self.enhancePicture)   
            self.colorWindow.ui.spinBoxNettete.valueChanged.disconnect(self.enhancePicture)  
            self.colorWindow.ui.spinBoxRed.valueChanged.disconnect(self.enhancePicture) 
            self.colorWindow.ui.spinBoxGreen.valueChanged.disconnect(self.enhancePicture) 
            self.colorWindow.ui.spinBoxBlue.valueChanged.disconnect(self.enhancePicture) 
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
            self.colorWindow.ui.radioButtonCurrent.setEnabled(True)
            self.colorWindow.ui.radioButtonComplete.setEnabled(True)
            if self.prevListParam[8] :
                self.statusKeepCurrentView = True
                self.colorWindow.ui.currentStatusButton.setText("Modifier")
                self.colorWindow.ui.currentStatusButton.setEnabled(True)
                self.colorWindow.ui.groupBoxMinMax.setChecked(True)
                self.colorWindow.ui.radioButtonCurrent.toggled.disconnect(self.currentViewActivate)
                self.colorWindow.ui.radioButtonCurrent.setChecked(True)
                self.colorWindow.ui.radioButtonCurrent.toggled.connect(self.currentViewActivate)
                self.currentPixVal = self.prevListParam[9]
                    

            
    #Calcul de l'histogramme sur une portion de la photo lorsque l'on veut conserver le min/max pour la vue courante
    def calculHistogram(self, top, low):

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
    
#Thread qui permet l'affichage, le rehaussement, la rotation et l'effet miroir des images de plus grandes résolutions
#Il ajoute des petites portions de l'image à chaque itération
#Il concidère toujours la vue courante dans la priorité d'affichage
class threadShow(QThread):
    newImage = pyqtSignal(QPixmap, float, int, int)
    def __init__(self, picture, pointZero, pointMax, multiFactor, seekFactor, scaleFactor, listParam, rotation=0, miroir=0, cropValue=None):
        QThread.__init__(self)
        self.picture = Image.open(picture)
        self.pointZero = pointZero
        self.pointMax = pointMax
        self.multiFactor = multiFactor
        self.seekFactor = seekFactor
        self.scaleFactor = scaleFactor
        self.listParam = listParam
        self.keepRunning = True
        self.rotation = rotation
        self.miroir = miroir
        self.cropValue = cropValue
    
    #Optimisation possible : Offrir le placement selon la proximité 
    def run(self):

        self.picture.seek(self.seekFactor)
        #Cause un bug dans le GUI, les spinboxs ne sont plus instantanées
        #Constraste netteté et saturation cause les plus gros ralentissements
        t = imageEnhancing(self.picture, self.listParam)
        t.start()
        r = t.join() 

        pictureEnhance = Image.merge("RGB",(r[0],r[1],r[2]))

        pictureAdjust = pictureLayout(pictureEnhance, self.rotation, self.miroir, False) 
        
        if self.cropValue:
            pictureAdjust = pictureAdjust.crop(self.cropValue)

        topX = round(self.pointZero.x()*self.multiFactor) if round(self.pointZero.x()*self.multiFactor) >= 0 else 0
        topY = round(self.pointZero.y()*self.multiFactor) if round(self.pointZero.y()*self.multiFactor) >= 0 else 0
        lowX = round(self.pointMax.x()*self.multiFactor)  if round(self.pointMax.x()*self.multiFactor) <= pictureAdjust.size[0] else pictureAdjust.size[0]
        lowY = round(self.pointMax.y()*self.multiFactor)  if round(self.pointMax.y()*self.multiFactor) <= pictureAdjust.size[1] else pictureAdjust.size[1]
        
        sizePixelX = abs(lowX - topX)
        sizePixelY = abs(lowY - topY)
     
        maxX = 750 
        maxY = 750

        middleRect = [topX, topY, lowX, lowY]
        firstRect = [0,0,topX, pictureAdjust.size[1]]
        secondRect = [lowX, 0, pictureAdjust.size[0], pictureAdjust.size[1]]
        thridRect = [topX, 0, topX+sizePixelX , topY]
        fourthRect = [topX, topY+sizePixelY, lowX, pictureAdjust.size[1]]

        rect = [middleRect, firstRect, secondRect, thridRect, fourthRect]
        for item in rect :

            nbDivX = ceil(abs(item[2] - item[0])/maxX)
            nbDivY = ceil(abs(item[3] - item[1])/maxY)

            currentTopX = item[0]
            currentTopY = item[1]
            
            for x in range(nbDivX) :
                
                currentLowX = currentTopX + maxX if (currentTopX + maxX) < item[2] else item[2]
                
                for y in range(nbDivY) : 

                    if self.keepRunning == False : 
                        self.picture.close()
                        return
                    
                    currentLowY = currentTopY + maxY if (currentTopY + maxY) < item[3] else item[3]
                    
                    cropPicture = np.array(pictureAdjust.crop((currentTopX,currentTopY,currentLowX,currentLowY)))

                    QtImg = qimage2ndarray.array2qimage(cropPicture)
                    
                    QtPixImg = QPixmap.fromImage(QtImg)

                    self.newImage.emit(QtPixImg, self.scaleFactor, currentTopX, currentTopY)

                    currentTopY += maxY
                
                currentTopX += maxX
                currentTopY = item[1]
        
        self.picture.close()


#Thread qui reçoit une image PIL ainsi que la liste des paramètres de rehaussement
#Le thread permet de réaliser le rehaussement
#Il retourne un objet list qui contient les trois couches de l'image  
class imageEnhancing(threading.Thread):

    def __init__(self, image, listParam, rotation=0, miroir=0):
        threading.Thread.__init__(self)
        self.image = image
        self.listParam = listParam
        self.rotation = rotation
        self.miroir = miroir

    def run(self):
        p = self.image

        if  self.listParam[0] != 0 :
            value =  self.listParam[0]
            if value > 0:
                if value < 50 :
                    p = ImageEnhance.Contrast(p).enhance(1 + (0.02*value))
                elif value < 80:
                    p = ImageEnhance.Contrast(p).enhance(2 + (0.1*(value-50)))
                else :
                    p = ImageEnhance.Contrast(p).enhance(5 + (value-80))

            else : 
                p = ImageEnhance.Contrast(p).enhance(1 +(value/100))


        if self.listParam[2] != 0 :    
            value = self.listParam[2]
            if value > 0 :
                p = ImageEnhance.Color(p).enhance(1 + (0.05 * value))
            else :
                p = ImageEnhance.Color(p).enhance(1 + int(value/100))

        if self.listParam[3] != 0 :
            p = ImageEnhance.Sharpness(p).enhance(self.listParam[3]/10 + 1)
        
        s = p.split()
        
        if self.listParam[7] : 

            if self.listParam[4] != 0 or self.listParam[1] != 0 :
                mr = s[0].point(self.redEnhance)
            else :
                mr = s[0]

            if self.listParam[5] != 0 or self.listParam[1] != 0 :
                mg = s[1].point(self.greenEnhance)
            else : 
                mg = s[1]

            if self.listParam[6] != 0 or self.listParam[1] != 0 :
                mb = s[2].point(self.blueEnhance)
            else :

                mb = s[2]
                
            if self.listParam[8] :
                self.pixValue = self.listParam[9]
            else :
                self.calculHistogram(mr,mg,mb)

            r = mr.point(self.redEqualization)
            g = mg.point(self.greenEqualization)
            b = mb.point(self.blueEqualization)

        
        else :
            if self.listParam[4] != 0 or self.listParam[1] != 0 :
                r = s[0].point(self.redEnhance)
            else :
                r = s[0]

            if self.listParam[5] != 0 or self.listParam[1] != 0 :
                g = s[1].point(self.greenEnhance)
            else : 
                g = s[1]

            if self.listParam[6] != 0 or self.listParam[1] != 0 :
                b = s[2].point(self.blueEnhance)
            else :
                b = s[2]

        self.ret = [r,g,b]

    #Fonction de fin de thread
    def join(self):
        threading.Thread.join(self)
        return self.ret
    
    #Modification de la couche Rouge, considère aussi la luminosité
    def redEnhance(self, value):
        if self.listParam[4] > 0 :
            return int(value * (1 + (self.listParam[4]/100))) + int(128*self.listParam[1]/100)
        else :
            return int(value * (1 - (0.5*(self.listParam[4]/-100)))) + int(128*self.listParam[1]/100)
    
    #Modification de la couche Verte, considère aussi la luminosité
    def greenEnhance(self, value):
        if self.listParam[5] > 0 :
            return int(value * (1 + (self.listParam[5]/100))) + int(128*self.listParam[1]/100)
        else :
            return int(value * (1 - (0.5*(self.listParam[5]/-100)))) + int(128*self.listParam[1]/100)

    #Modification de la couche Bleue, considère aussi la luminosité
    def blueEnhance(self, value):
        if self.listParam[6] > 0 :
            return int(value * (1 + (self.listParam[6]/100))) + int(128*self.listParam[1]/100)
        else :
            return int(value * (1 - (0.5*(self.listParam[6]/-100)))) + int(128*self.listParam[1]/100)


    #Modification de la couche Rouge selon le Min Max
    def redEqualization(self,value):
        oldMin = self.pixValue[0]
        oldMax = self.pixValue[1]
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    #Modification de la couche Verte selon le Min Max
    def greenEqualization(self,value):
        oldMin = self.pixValue[2]
        oldMax = self.pixValue[3]
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    #Modification de la couche Bleue selon le Min Max
    def blueEqualization(self,value):
        oldMin = self.pixValue[4]
        oldMax = self.pixValue[5] 
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    #Calcul de l'histogramme et repérage des valeur min et max dans les trois couleurs
    def calculHistogram(self, red, green, blue):

        redHis = red.histogram()
        redSum = sum(redHis)
        greenHis = green.histogram()
        greenSum = sum(greenHis)
        blueHis = blue.histogram()
        blueSum = sum(blueHis)
        cutValue = [round(redSum*0.05), round(redSum*0.95), round(greenSum*0.05), round(greenSum*0.95), round(blueSum*0.05), round(blueSum*0.95)]
        self.pixValue = []
        buff = 0
        count = 0
        for i in range(len(redHis)):
            buff += redHis[i] 
            if buff > cutValue[count] : 
                self.pixValue.append(i)
                count += 1
                if count == 2 :
                    break
        
        buff = 0
        for i in range(len(greenHis)):
            buff += greenHis[i] 
            if buff > cutValue[count] : 
                self.pixValue.append(i)
                count += 1
                if count == 4 :
                    break
        
        buff = 0
        for i in range(len(blueHis)):
            buff += blueHis[i] 
            if buff > cutValue[count] : 
                self.pixValue.append(i)
                count += 1
                if count == 6 :
                    break
    

#Fonction qui réalise une rotation et/ou un effet miroir d'une photo PIL
#Elle retourne une photo PIL ou une QImage selon le choix retQImage (True/False) 
def pictureLayout(picture, rotation, miroir, retQImage, cropValue=None):
    
    if rotation == 0 and miroir == 0 :
        pic = picture

    else :
        pic = picture
        if rotation == 3 :
            pic = pic.rotate(90, expand=1)
        elif rotation == 2 :
            pic = pic.rotate(180, expand=0)
        elif rotation == 1 :
            pic = pic.rotate(270, expand=1)
        
        if miroir == 1 :
            pic = pic.transpose(Image.FLIP_LEFT_RIGHT)
        elif miroir == 2 :
            pic = pic.transpose(Image.FLIP_TOP_BOTTOM)

    if cropValue:
        pic = pic.crop(cropValue)
        

    if retQImage : 
        npPicture = np.array(pic)
        qtI = qimage2ndarray.array2qimage(npPicture)
        return qtI
    else :
        return pic
