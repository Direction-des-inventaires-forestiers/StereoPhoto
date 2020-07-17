'''
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient une classe de type QApplication qui permet l'affichage d'images de grandes tailles sur des 
écrans de type Planar

La classe stereoPhoto gère l'application complète via un interface utilisateur
L'application permet de :
    - Importer des fichiers TIF de grandes tailles via un drag n drop
    - Réaliser une rotation de 90°, 180° et 270°
    - Réaliser un effet miroir sur l'horizontal et la verticale
    - Afficher les deux images importées
    - Superposer automatiquement les images en fonction d'un pourcentage choisi par l'utilisateur
    - Offrir une interface de navigation qui permet le déplacement, le zoom (CTRL+Roulette) et le traçage (Click & 1,2,3,ESC) 
    - Offrir un déplacement de l'image de droite pour ajuster l'altitude (Roulette)
    - Rehausser les couleurs des images via une nouvelle fenêtre intéractive 
    - Traçage de forme géolocalisée
    - Communication avec QGIS
    - Utiliser un shapefile 2D déjà importé dans QGIS et afficher la région concernée
    - Afficher le Z du centre de l'image
    - Afficher les coordonnées XYZ lors d'un clic 
    - Permettre le choix des écrans

Le main permet tout simplement de lancer l'application

Plusieurs autres outils seront intégrés à cette application dans le futur :
    - Fonctionnalité de trace supplémentaire
    - Amélioration des fonctions de photogrammétrie 
    - Menu de choix de paramètres (curseur, keybinding, couleur des traces)
    - Affichage des zones supersposées seulement
    - Gestion de projet
    - Utiliser un shapefile 3D
    et bien d'autre

'''
from qgis.gui import *
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *

from PIL import Image, ImageDraw
import numpy as np
from . import resources

from .ui_optionWindow import optionWindow
from .ui_graphicsWindow import graphicsWindow 
from .worldManager import pictureManager, dualManager
from .enhanceManager import enhanceManager, threadShow, imageEnhancing, pictureLayout
from .drawFunction import *
import sys, os, time, math, qimage2ndarray, win32api

#Permet l'ouverture avec PIL de fichier énorme!
Image.MAX_IMAGE_PIXELS = 1000000000 

class stereoPhoto(object):

    #Fonction d'initilisation 
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

    #Place le bouton de l'application dans QGIS
    def initGui(self):
        urlPicture = ":/Anaglyph/Icons/icon.png"
        self.action = QAction(QIcon(urlPicture), "StereoPhoto", self.iface.mainWindow())
        
        self.action.triggered.connect(self.run)
         
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&StereoPhoto", self.action)

    #Retire le bouton de l'application dans QGIS
    def unload(self):
        self.iface.removePluginMenu("&StereoPhoto", self.action)
        self.iface.removeToolBarIcon(self.action)
        
    #Initialisation de l'application et des variables
    #Connection entre les boutons du menu d'options (mOpt) et leurs fonctions attitrées
    #Ouverture du menu d'options
    def run(self):

        self.leftOrientation = 0
        self.rightOrientation = 0
        self.leftMiroir = 0
        self.rightMiroir = 1


        self.leftName = False 
        self.rightName = False 
        self.anaglyphActivate = False 

        self.showThreadLeftInProcess = False
        self.newLeftRequest = False
        self.showThreadRightInProcess = False
        self.newRightRequest = False
        self.enableDraw = False
        self.enableShow = False

        self.polygonOnLeftScreen = []
        self.polygonOnRightScreen = []
        self.pointOnLeftScreen = []
        self.pointOnRightScreen = []

        self.listParam = [0, 0, 0, 0, 0, 0, 0, False, False, []]

        self.optWindow = optionWindow()

        self.optWindow.ui.boxMiroirLeft.currentIndexChanged.connect(self.mMiroirLeft)
        self.optWindow.ui.boxMiroirRight.currentIndexChanged.connect(self.mMiroirRight)
        self.optWindow.ui.boxOrientationLeft.currentIndexChanged.connect(self.mOrientationLeft)
        self.optWindow.ui.boxOrientationRight.currentIndexChanged.connect(self.mOrientationRight)
        self.optWindow.ui.importLineLeft.textChanged.connect(self.mNewLeftPic)
        self.optWindow.ui.importLineRight.textChanged.connect(self.mNewRightPic)
        self.optWindow.ui.importLineVectorLayer.textChanged.connect(self.mNewVectorLayer)
        
        self.optWindow.ui.importButtonLeft.clicked.connect(self.mImportLeft)
        self.optWindow.ui.importButtonRight.clicked.connect(self.mImportRight)
        
        self.optWindow.ui.panButton.clicked.connect(self.panClick)
        self.optWindow.ui.enhanceButton.clicked.connect(self.enhanceClick)
        self.optWindow.ui.radioPolygonLayer.toggled.connect(self.radioLayerManager)
        self.optWindow.keyDrawEvent.connect(self.keyboardHandler)

        self.optWindow.ui.affichageButton.clicked.connect(self.loadWindows)
        self.optWindow.closeWindow.connect(self.optWindowClose)

        nbScreen = QApplication.desktop().screenCount()-1
        self.optWindow.ui.spinBoxLeftScreen.setMaximum(nbScreen)
        self.optWindow.ui.spinBoxRightScreen.setMaximum(nbScreen)

        self.optWindow.show()
        

    #Fonction appelée lors de la fermeture du mOpt
    #Si l'on ferme le mOpt toutes les autres fenêtres Qt se ferment
    def optWindowClose(self):
        scene = QGraphicsScene()
        if hasattr(self, "graphWindowLeft"):
            self.graphWindowLeft.ui.graphicsView.setScene(scene)
            self.graphWindowLeft.close()
            del self.graphWindowLeft
        if hasattr(self, "graphWindowRight"):
            self.graphWindowRight.ui.graphicsView.setScene(scene)
            self.graphWindowRight.close()
            del self.graphWindowRight
        if hasattr(self, "enhanceManager"):
            self.enhanceManager.colorWindow.ui.graphicsView.setScene(scene)
            self.enhanceManager.colorWindow.close()
            del self.enhanceManager 
        self.optWindow.close()
        
    #Fonction de traitement d'image pour modifier l'orientation
    #Les angles de rotation possible sont 0, 90, 180 et 270
    def mOrientationLeft(self, value):
        self.leftOrientation = value
        QtImg = pictureLayout(self.demoLeftPic, self.leftOrientation, self.leftMiroir, True)
        scene = QGraphicsScene()
        scene.addPixmap(QPixmap.fromImage(QtImg))
        self.optWindow.ui.graphicsViewLeft.setScene(scene)
        self.optWindow.ui.graphicsViewLeft.fitInView(self.optWindow.ui.graphicsViewLeft.sceneRect(), Qt.KeepAspectRatio)

    #Idem à mOrientationLeft
    def mOrientationRight(self, value):
        self.rightOrientation = value
        QtImg = pictureLayout(self.demoRightPic, self.rightOrientation, self.rightMiroir, True)
        scene = QGraphicsScene()
        scene.addPixmap(QPixmap.fromImage(QtImg))
        self.optWindow.ui.graphicsViewRight.setScene(scene)
        self.optWindow.ui.graphicsViewRight.fitInView(self.optWindow.ui.graphicsViewRight.sceneRect(), Qt.KeepAspectRatio)
        
    #Fonction de traitement d'image pour ajouter un effet miroir à l'image
    #Deux modes sont possible, soit un effet miroir à l'horizontal et un à la verticale
    def mMiroirLeft(self, value):
        self.leftMiroir = value
        QtImg = pictureLayout(self.demoLeftPic, self.leftOrientation, self.leftMiroir, True)
        scene = QGraphicsScene()
        scene.addPixmap(QPixmap.fromImage(QtImg))
        self.optWindow.ui.graphicsViewLeft.setScene(scene)
        self.optWindow.ui.graphicsViewLeft.fitInView(self.optWindow.ui.graphicsViewLeft.sceneRect(), Qt.KeepAspectRatio)
        
    #Idem à mMiroirLeft
    def mMiroirRight(self,value):
        self.rightMiroir = value
        QtImg = pictureLayout(self.demoRightPic, self.rightOrientation, self.rightMiroir, True)
        scene = QGraphicsScene()
        scene.addPixmap(QPixmap.fromImage(QtImg))
        self.optWindow.ui.graphicsViewRight.setScene(scene)
        self.optWindow.ui.graphicsViewRight.fitInView(self.optWindow.ui.graphicsViewRight.sceneRect(), Qt.KeepAspectRatio)


    #Fonction réaliser lorsqu'une photo est importée 
    #Elle permet de rendre le panneau de fonctionnalité accessible à l'utilisateur 
    #pour le traitement d'image ainsi que le bouton d'importation
    #L'image est affiché en petit format pour permettre une visualisation du 
    #résultat qui sera produit suite à l'importation  
    #Si une nouvelle photo est importée, l'ancienne est fermée 
    #Création d'un pictureManager pour associer le fichier .par à la photo
    #Récupération du choix de l'écran pour l'affichage
    def mNewLeftPic(self) : 

        self.optWindow.ui.boxOrientationLeft.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirLeft.setCurrentIndex(0)

        self.intLeftScreen = self.optWindow.ui.spinBoxLeftScreen.value()
        self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)
        self.panCenterLeft = (int(self.screenLeft.width()/2), int(self.screenLeft.height()/2))
        self.leftScreenCenter = ( self.screenLeft.x() + int(self.screenLeft.width()/2), self.screenLeft.y() + int(self.screenLeft.height()/2))
          
        self.leftName = False
        self.optWindow.ui.affichageButton.setEnabled(False)

        try :
            del self.graphWindowLeft
            self.graphWindowRight.close()
        except :
            pass

        self.leftPic = Image.open(self.optWindow.ui.importLineLeft.text())
        self.demoLeftPic = Image.open(self.optWindow.ui.importLineLeft.text())

        if hasattr(self.demoLeftPic, "n_frames"): 
            for i in range(self.demoLeftPic.n_frames):
                self.demoLeftPic.seek(i)
                if self.demoLeftPic.size < (200,200) :
                    self.demoLeftPic.seek(i-1)
                    break

        elif self.leftPic.size[0] > self.leftPic.size[1] :
            self.demoLeftPic = self.leftPic.resize((300,200))
        else :
            self.demoLeftPic = self.leftPic.resize((200,300))

        draw = ImageDraw.Draw(self.demoLeftPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        
        npPicture = np.array(self.demoLeftPic)
        sceneLeft = QGraphicsScene()
        img = qimage2ndarray.array2qimage(npPicture)
        sceneLeft.addPixmap(QPixmap.fromImage(img))

        self.optWindow.ui.graphicsViewLeft.setScene(sceneLeft)
        self.optWindow.ui.graphicsViewLeft.show()
        self.optWindow.ui.graphicsViewLeft.fitInView(self.optWindow.ui.graphicsViewLeft.sceneRect(), Qt.KeepAspectRatio)
        self.optWindow.ui.label.setEnabled(True)
        self.optWindow.ui.label_2.setEnabled(True)
        self.optWindow.ui.boxMiroirLeft.setEnabled(True)        
        self.optWindow.ui.boxOrientationLeft.setEnabled(True)
        self.optWindow.ui.importButtonLeft.setEnabled(True)
        self.optWindow.ui.importDoneLeft.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")

        self.graphWindowLeft = graphicsWindow("Image Gauche")
        self.graphWindowLeft.setWindowState(Qt.WindowMaximized)
        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height())
        self.graphWindowLeft.ui.graphicsView.setGeometry(rect)
        self.graphWindowLeft.ui.widget.setGeometry(rect)
        self.graphWindowLeft.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))
        self.graphWindowLeft.keyDrawEvent.connect(self.keyboardHandler)

        pathPAR = self.optWindow.ui.importLineLeft.text().split(".")[0] + ".par"
        self.leftPictureManager = pictureManager(self.leftPic.size, pathPAR, "aa")
        self.leftPicSize = self.leftPic.size

    #Idem à mNewLeftPic
    #L'image a un effet miroir horizontal dès son ouverture
    def mNewRightPic(self):
        
        self.optWindow.ui.boxOrientationRight.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirRight.setCurrentIndex(1)

        self.intRightScreen = self.optWindow.ui.spinBoxRightScreen.value()
        self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)
        self.panCenterRight = (int(self.screenRight.width()/2), int(self.screenRight.height()/2))

        self.rightOrientation = 0
        self.rightMiroir = 1
        self.rightName = False
        self.optWindow.ui.affichageButton.setEnabled(False)

        try :
            del self.graphWindowRight
            self.graphWindowLeft.close()
        except :
            pass

        self.rightPic = Image.open(self.optWindow.ui.importLineRight.text())
        self.demoRightPic = Image.open(self.optWindow.ui.importLineRight.text())

        if hasattr(self.demoRightPic, "n_frames"): #and format == tif??
            for i in range(self.demoRightPic.n_frames):
                self.demoRightPic.seek(i)
                if self.demoRightPic.size < (200,200) :
                    self.demoRightPic.seek(i-1)
                    break

        elif self.rightPic.size[0] > self.rightPic.size[1] :
            self.demoRightPic = self.rightPic.resize((300,200))
        else :
            self.demoRightPic = self.rightPic.resize((200,300))

        draw = ImageDraw.Draw(self.demoRightPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        
        dRightPic = self.demoRightPic.transpose(Image.FLIP_LEFT_RIGHT)
        
        npPicture = np.array(dRightPic)
        img = qimage2ndarray.array2qimage(npPicture)

        sceneRight = QGraphicsScene()
        sceneRight.addPixmap(QPixmap.fromImage(img))
        self.optWindow.ui.graphicsViewRight.setScene(sceneRight)
        self.optWindow.ui.graphicsViewRight.show()
        self.optWindow.ui.graphicsViewRight.fitInView(self.optWindow.ui.graphicsViewRight.sceneRect(), Qt.KeepAspectRatio)
        self.optWindow.ui.importButtonRight.setEnabled(True)
        self.optWindow.ui.label_3.setEnabled(True)
        self.optWindow.ui.label_4.setEnabled(True)        
        self.optWindow.ui.boxMiroirRight.setEnabled(True)        
        self.optWindow.ui.boxOrientationRight.setEnabled(True)
        self.optWindow.ui.importDoneRight.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")

        self.graphWindowRight = graphicsWindow("Image Droite")
        self.graphWindowRight.setWindowState(Qt.WindowMaximized)
        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height())
        self.graphWindowRight.ui.graphicsView.setGeometry(rect)
        self.graphWindowRight.ui.widget.setGeometry(rect)
        self.graphWindowRight.move(QPoint(self.screenRight.x(), self.screenRight.y()))

        pathPAR = self.optWindow.ui.importLineRight.text().split(".")[0] + ".par"
        self.rightPictureManager = pictureManager(self.rightPic.size, pathPAR, "aa")
        self.rightPicSize = self.rightPic.size

    #Fonction qui récupère la couche vectorielle et change le SIG de QGIS 
    #Si possible appel la fonction pour afficher la couche vectorielle sur les images
    def mNewVectorLayer(self):

        self.enableDraw = True
        self.vectorLayer = self.optWindow.vLayer
        QgsProject.instance().setCrs(self.vectorLayer.crs())

        if self.enableShow :
            if self.optWindow.ui.radioPointLayer.isChecked() :
                self.addPointOnScreen()
            elif self.optWindow.ui.radioPolygonLayer.isChecked() :
                self.addPolygonOnScreen()

    
    #Fonction qui détermine la région approximative des photos
    #Retourne le rectangle de coordonnée
    def getShowRect(self) :
        
        if hasattr(self, "leftRect"): 
            endLeft = [self.leftRect.x() + self.leftRect.width(), self.leftRect.y() + self.leftRect.height()]
            topXL, topYL = self.leftPictureManager.pixelToCoord([self.leftRect.x(),self.leftRect.y()],self.initAltitude)
            botXL, botYL = self.leftPictureManager.pixelToCoord(endLeft,self.initAltitude)
            rectL = QgsRectangle(QgsPointXY(topXL, topYL), QgsPointXY(botXL, botYL))
            return rectL
        
        else :
            return QgsRectangle(QgsPointXY(0, 0), QgsPointXY(0, 0))
        
    #Fonction qui reçoit un pixel de chaque image
    #Utilise les deux pixels pour faire le calcul du Z et des coordonnées
    #Retourne la valeur des coordonnées moyennées
    def dualPixelToCoord(self, QPointLeft, QPointRight):
        pixL = (QPointLeft.x(), QPointLeft.y())
        mirrorX = self.rightPicSize[0] - QPointRight.x()
        pixR = (mirrorX, QPointRight.y())
        Z = self.dualManager.calculateZ(pixL, pixR)
        XL, YL = self.leftPictureManager.pixelToCoord(pixL, Z)
        XR, YR = self.rightPictureManager.pixelToCoord(pixR, Z)

        X = (XL + XR) / 2
        Y = (YL + YR) / 2
        
        return X, Y

    
    #Fonction qui ouvre les deux fenêtres sur les écrans choisis
    #Récupère les valeurs en pixels du centre de l'image
    #Création du dualManager qui permet de calculer l'altitude
    #Premier calcul de l'altitude du centre des images 
    #Utilise le pourcentage de recouvrement pour placer les images
    #Affichage de l'image complète
    #Affichage d'un curseur au centre des fenêtres
    #Si possible appel la fonction pour afficher la couche vectorielle sur les images   
    def loadWindows(self, value):

        self.intLeftScreen = self.optWindow.ui.spinBoxLeftScreen.value()
        self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)
        self.panCenterLeft = (int(self.screenLeft.width()/2), int(self.screenLeft.height()/2))
        self.leftScreenCenter = ( self.screenLeft.x() + int(self.screenLeft.width()/2), self.screenLeft.y() + int(self.screenLeft.height()/2))

        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height())
        self.graphWindowLeft.ui.graphicsView.setGeometry(rect)
        self.graphWindowLeft.ui.widget.setGeometry(rect)
        self.graphWindowLeft.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))

        self.intRightScreen = self.optWindow.ui.spinBoxRightScreen.value()
        self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)
        self.panCenterRight = (int(self.screenRight.width()/2), int(self.screenRight.height()/2))

        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height())
        self.graphWindowRight.ui.graphicsView.setGeometry(rect)
        self.graphWindowRight.ui.widget.setGeometry(rect)
        self.graphWindowRight.move(QPoint(self.screenRight.x(), self.screenRight.y()))

        self.dualManager = dualManager(self.leftPictureManager, self.rightPictureManager)
        xLeft = (self.leftPicSize[0]/2)*((100-self.optWindow.ui.spinBoxRecouvrementH.value())/100)
        xRight = (self.rightPicSize[0]/2)*((100-self.optWindow.ui.spinBoxRecouvrementH.value())/100)
        self.leftRect = QRectF(xLeft, 0, self.leftPicSize[0], self.leftPicSize[1])
        self.rightRect = QRectF(xRight, 0, self.rightPicSize[0], self.rightPicSize[1]) 
        
        self.graphWindowLeft.close()
        self.graphWindowRight.close()
        
        self.graphWindowLeft.cursorRectInit(self.screenLeft.width(), self.screenLeft.height())
        self.graphWindowRight.cursorRectInit(self.screenRight.width(), self.screenRight.height())

        self.graphWindowLeft.show()
        self.graphWindowRight.show()
        self.graphWindowLeft.ui.graphicsView.fitInView(self.leftRect, Qt.KeepAspectRatio)
        self.graphWindowRight.ui.graphicsView.fitInView(self.rightRect, Qt.KeepAspectRatio)
        self.graphWindowLeft.ui.graphicsView.update()
        self.graphWindowRight.ui.graphicsView.update()
        self.optWindow.activateWindow()
        self.optWindow.ui.panButton.setEnabled(True)
        self.enableShow = True
        
        centerPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(self.panCenterLeft[0], self.panCenterLeft[1]))
        centerPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))
        self.centerPixelLeft = (centerPointLeft.x(), centerPointLeft.y())
        mirrorX = self.rightPicSize[0] - centerPointRight.x()
        self.centerPixelRight = (mirrorX, centerPointRight.y())
        Z = self.dualManager.calculateZ(self.centerPixelLeft, self.centerPixelRight)
        self.optWindow.ui.lineEditCurrentZ.setText(str(round(Z,2)))

        self.initAltitude = Z
        
        if self.enableDraw :
            if self.optWindow.ui.radioPointLayer.isChecked() :
                self.addPointOnScreen()
            elif self.optWindow.ui.radioPolygonLayer.isChecked() :
                self.addPolygonOnScreen()

    def addPointOnScreen(self):
        rectCoord = self.getShowRect()
        listGeo = list(self.vectorLayer.getFeatures(rectCoord))

        if self.pointOnLeftScreen :
            for item in self.pointOnLeftScreen :
                self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
        self.pointOnLeftScreen = []

        if self.pointOnRightScreen :
            for item in self.pointOnRightScreen :
                self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
        self.pointOnRightScreen = []
            
        for item in listGeo : 
            featureGeo = item.geometry()
            
            if featureGeo.isNull() == False :

                QgsPoint = featureGeo.asPoint()
                xPixel, yPixel = self.leftPictureManager.coordToPixel((QgsPoint.x() , QgsPoint.y()), self.initAltitude) 
                xRPixel = -xPixel + self.rightPicSize[0] + self.rightRect.x() + self.leftRect.x()

                m_pen = QPen(QColor(0, 255, 255),14, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                m_brush = QBrush(QColor(0, 255, 255))
                leftObj = self.graphWindowLeft.ui.graphicsView.scene().addEllipse(xPixel, yPixel, 50, 50, m_pen, m_brush)
                rightObj = self.graphWindowRight.ui.graphicsView.scene().addEllipse(xRPixel, yPixel, 50, 50, m_pen, m_brush)
                self.pointOnLeftScreen.append(leftObj)
                self.pointOnRightScreen.append(rightObj)

    #Fonction qui ajoute les polygones sur chaque image
    #Elle concidère les coordonnées approximatives pour récupérer
    #les polygones de la région sur la couche vectorielle
    def addPolygonOnScreen(self) :
        rectCoord = self.getShowRect()
        listGeo = list(self.vectorLayer.getFeatures(rectCoord))

        if self.polygonOnLeftScreen :
            for item in self.polygonOnLeftScreen :
                self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
        self.polygonOnLeftScreen = []

        if self.polygonOnRightScreen :
            for item in self.polygonOnRightScreen :
                self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
        self.polygonOnRightScreen = []
            
        for item in listGeo : 
            featureGeo = item.geometry()
            
            if featureGeo.isNull() == False :

                listQgsPoint = featureGeo.asMultiPolygon()[0][0]
                polygonL = QPolygonF()
                polygonR = QPolygonF()
                for point in listQgsPoint :
                    xPixel, yPixel = self.leftPictureManager.coordToPixel((point.x() , point.y()), self.initAltitude)     
                    polygonL.append(QPointF(xPixel, yPixel))
                    xRPixel = -xPixel + self.rightPicSize[0] + self.rightRect.x() + self.leftRect.x()
                    polygonR.append(QPointF(xRPixel, yPixel))

                m_pen = QPen(QColor(0, 255, 255),10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                leftObj = self.graphWindowLeft.ui.graphicsView.scene().addPolygon(polygonL, m_pen)
                rightObj = self.graphWindowRight.ui.graphicsView.scene().addPolygon(polygonR, m_pen)
                self.polygonOnLeftScreen.append(leftObj)
                self.polygonOnRightScreen.append(rightObj)

    #Fonction pour permettre l'imporation de l'image sur le graphicsView
    #Similaire au fichier enhanceManager, une version de basse résolution de l'image est affichée immédiatement
    #Par la suite, un thread est lancé pour venir afficher les plus hautes résolutions
    #Le rehaussement, la rotation et l'effet miroir sont considérés
    #Les connections pour les fonctiones de navigations sont établies
    def mImportLeft(self):

        if hasattr(self, "tSeekLeft"): 
            try :
                self.tSeekLeft.newImage.disconnect(self.addLeftPixmap)
            except: 
                pass
            self.tSeekLeft.keepRunning = False

        self.optWindow.ui.importDoneLeft.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
        self.optWindow.ui.importButtonLeft.setEnabled(False)
 
        self.leftPic.seek(3)

        t = imageEnhancing(self.leftPic, self.listParam)
        t.start()
        r = t.join()
        enhancePic = Image.merge("RGB", (r[0],r[1],r[2]))
        #enhancePic = enhancePic.rotate(0.8634, expand=1)
        
        QtImg = pictureLayout(enhancePic, self.leftOrientation, self.leftMiroir, True)   
        
        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        
        objPixmap = scene.addPixmap(QPixmap.fromImage(QtImg))      
        objPixmap.setScale(8)
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        
        pointZero = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(0,0))
        GV = self.graphWindowLeft.ui.graphicsView
        pointMax = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))

        if self.showThreadLeftInProcess == False :
            #self.threadSeekLeft(pointZero, pointMax, 0.5, 1, 2)
            self.showThreadLeftInProcess = True
        else :
            self.newLeftRequest = True

        self.graphWindowLeft.ui.widget.mouseMoveEvent = self.mMoveEvent
        self.graphWindowLeft.ui.widget.mousePressEvent = self.mPressEvent
        self.graphWindowLeft.ui.widget.wheelEvent = self.wheelEvent
        self.graphWindowLeft.ui.graphicsView.show()
        self.optWindow.ui.importDoneLeft.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.optWindow.ui.importButtonLeft.setEnabled(True)
        self.leftName = True 
        if self.rightName :
            self.optWindow.ui.affichageButton.setEnabled(True)
            self.optWindow.ui.enhanceButton.setEnabled(True)

    #IDEM à mImportLeft
    def mImportRight(self):

        if hasattr(self, "tSeekRight"): 
            try :
                self.tSeekRight.newImage.disconnect(self.addRightPixmap)
            except: 
                pass
            self.tSeekRight.keepRunning = False

        self.optWindow.ui.importDoneRight.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
        self.optWindow.ui.importButtonRight.setEnabled(False)
      
        self.rightPic.seek(3)

        t = imageEnhancing(self.rightPic, self.listParam)
        t.start()
        r = t.join()      
        enhancePic = Image.merge("RGB", (r[0],r[1],r[2]))
        #enhancePic = enhancePic.rotate(0.8634, expand=1)
        
        QtImg = pictureLayout(enhancePic, self.rightOrientation, self.rightMiroir, True)   
        
        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        
        objPixmap = scene.addPixmap(QPixmap.fromImage(QtImg))
        objPixmap.setScale(8)
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        
        pointZero = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(0,0))
        GV = self.graphWindowRight.ui.graphicsView
        pointMax = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))

        if self.showThreadRightInProcess == False :
            #self.threadSeekRight(pointZero, pointMax, 0.5, 1, 2)
            self.showThreadRightInProcess = True
        else :
            self.newRightRequest = True

        self.graphWindowRight.ui.graphicsView.show()
        self.optWindow.ui.importDoneRight.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.optWindow.ui.importButtonRight.setEnabled(True)
        self.rightName = True 
        if self.leftName :
            self.optWindow.ui.affichageButton.setEnabled(True)
            self.optWindow.ui.enhanceButton.setEnabled(True)


    #Utiliser par threadShow pour afficher une portion de l'image à une certaine position
    def addLeftPixmap(self, pixmap, scaleFactor, topX, topY) :
        d = self.graphWindowLeft.ui.graphicsView.scene().addPixmap(pixmap)
        d.setScale(scaleFactor)
        d.setOffset(topX, topY)

    #IDEM à addLeftPixmap
    def addRightPixmap(self, pixmap, scaleFactor, topX, topY) :
        d = self.graphWindowRight.ui.graphicsView.scene().addPixmap(pixmap)
        d.setScale(scaleFactor)
        d.setOffset(topX, topY)

    #Fonction qui permet de lancer le thread d'affichage des images de plus grande qualité
    def threadSeekLeft(self, pointZero, pointMax, multiFactor, seekFactor, scaleFactor):
        self.tSeekLeft = threadShow(self.optWindow.ui.importLineLeft.text(), pointZero, pointMax, multiFactor, seekFactor, scaleFactor, self.listParam, self.leftOrientation, self.leftMiroir)
        self.tSeekLeft.newImage.connect(self.addLeftPixmap)
        self.tSeekLeft.finished.connect(self.seekLeftDone)
        self.showThreadLeftInProcess = True
        self.newLeftRequest = False
        self.tSeekLeft.start(QThread.IdlePriority)

    #IDEM à threadSeekLeft
    def threadSeekRight(self, pointZero, pointMax, multiFactor, seekFactor, scaleFactor):
        self.tSeekRight = threadShow(self.optWindow.ui.importLineRight.text(), pointZero, pointMax, multiFactor, seekFactor, scaleFactor, self.listParam, self.rightOrientation, self.rightMiroir)
        self.tSeekRight.newImage.connect(self.addRightPixmap)
        self.tSeekRight.finished.connect(self.seekRightDone)
        self.showThreadRightInProcess = True
        self.newRightRequest = False
        self.tSeekRight.start(QThread.IdlePriority)

    #Fonction exécutée lorsque le thread d'affichage se termine
    #Elle redessine les polygones sur les images
    #Elle relance le thread avec la même résolution si une requête a été faite sinon
    #elle relance le thread avec une plus grande résolution d'image 
    def seekLeftDone(self):

        if self.enableDraw and hasattr(self, "initAltitude"):
            if self.optWindow.ui.radioPointLayer.isChecked() :
                self.addPointOnScreen()
            elif self.optWindow.ui.radioPolygonLayer.isChecked() :
                self.addPolygonOnScreen()

        if self.newLeftRequest : 
            pointZero = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowLeft.ui.graphicsView
            pointMax = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekLeft(pointZero, pointMax, 0.5, 1, 2)

        elif self.tSeekLeft.seekFactor == 1 :
            pointZero = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowLeft.ui.graphicsView
            pointMax = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekLeft(pointZero, pointMax, 1, 0, 1)

        else :
            self.showThreadLeftInProcess = False

    #IDEM à seekLeftDone
    def seekRightDone(self):

        if self.enableDraw and hasattr(self, "initAltitude") :
            if self.optWindow.ui.radioPointLayer.isChecked() :
                self.addPointOnScreen()
            elif self.optWindow.ui.radioPolygonLayer.isChecked() :
                self.addPolygonOnScreen()

        if self.newRightRequest : 
            pointZero = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowRight.ui.graphicsView
            pointMax = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekRight(pointZero, pointMax, 0.5, 1, 2)

        elif self.tSeekRight.seekFactor == 1 :
            pointZero = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowRight.ui.graphicsView
            pointMax = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekRight(pointZero, pointMax, 1, 0, 1)

        else :
            self.showThreadRightInProcess = False
       
    
    #Place la souris en mode pan, active/désactive les boutons de dessin   
    def panClick(self):

        if self.optWindow.ui.panButton.isChecked():
            
            #22 est la taille en pixel de la barre du haute de la fenetre
            #Il y a toujours un petit pan lorsqu'on active le Pan sinon 
            self.lastX = self.panCenterLeft[0]
            self.lastY = self.panCenterLeft[1] - 22
            win32api.SetCursorPos(self.leftScreenCenter)
            self.graphWindowLeft.ui.widget.setMouseTracking(True)
            self.graphWindowLeft.setCursor(self.graphWindowLeft.invisibleCursor)
            if self.enableDraw : 
                self.optWindow.ui.drawButton.setEnabled(True)
                if self.optWindow.ui.radioPolygonLayer.isChecked() :
                    self.optWindow.ui.cutButton.setEnabled(True)
        
        else : 
            self.optWindow.ui.drawButton.setEnabled(False)
            self.optWindow.ui.cutButton.setEnabled(False)
            self.graphWindowLeft.ui.widget.setMouseTracking(False)
            win32api.SetCursorPos((self.optWindow.pos().x(), self.optWindow.pos().y()))
            self.graphWindowLeft.setCursor(self.graphWindowLeft.normalCursor)

    #Active le draw et peut désactiver le cut
    #Initialise les variables de dessins à un état de base
    def drawClick(self):
        self.optWindow.ui.cutButton.setChecked(False)
        self.optWindow.ui.drawButton.setChecked(True)

        self.listDrawCoord = []
        self.listLeftLineObj = []
        self.listRightLineObj = []
        self.firstDrawClick = True
        self.currentLeftLineObj = None
        self.currentRightLineObj = None

    #Active le cut et peut désactiver le draw
    #Initialise les variables de dessins à un état de base
    def cutClick(self):
        self.optWindow.ui.cutButton.setChecked(True)
        self.optWindow.ui.drawButton.setChecked(False)

        self.listDrawCoord = []
        self.listLeftLineObj = []
        self.listRightLineObj = []
        self.firstDrawClick = True
        self.currentLeftLineObj = None
        self.currentRightLineObj = None

    def radioLayerManager(self):

        self.vectorLayer = None 
        self.enableDraw = False
        self.optWindow.ui.cutButton.setEnabled(False)
        self.optWindow.ui.drawButton.setEnabled(False)

        self.optWindow.ui.importLineVectorLayer.textChanged.disconnect(self.mNewVectorLayer)
        self.optWindow.ui.importLineVectorLayer.setText("")
        self.optWindow.ui.importLineVectorLayer.textChanged.connect(self.mNewVectorLayer)

        if self.optWindow.ui.radioPointLayer.isChecked():
            self.optWindow.ui.drawButton.setText("Ajouter Point (1)")
        
        elif self.optWindow.ui.radioPolygonLayer.isChecked():
            self.optWindow.ui.drawButton.setText("Ajouter Polygon (1)")

    
    #Ouverture de la fenêtre de rehaussement
    def enhanceClick(self):
        nameLeft = self.optWindow.ui.importLineLeft.text()
        nameRight = self.optWindow.ui.importLineRight.text()
        self.enhanceManager = enhanceManager(nameLeft, nameRight, self.listParam)
        self.enhanceManager.listParamSignal.connect(self.applyEnhance)

    #Permet le lancement du traitement de modification des images
    def applyEnhance(self, listParam):
        self.enhanceManager.listParamSignal.disconnect(self.applyEnhance)
        self.listParam = listParam
        self.mImportLeft()
        self.mImportRight()

    #Fonction appelée lorsque les touches respectives du clavier sont appuyées
    #Les touches sont utiles lorsque le mode pan est en cours d'utilisation
    #Possibilité d'ajouter d'autres fonctions plus tard
    def keyboardHandler(self, number):
        
        if number == "1" :
            if self.optWindow.ui.drawButton.isChecked() :
                self.optWindow.ui.drawButton.setChecked(False)
            elif self.enableDraw :
                self.drawClick()
        
        elif number == "2" :
            if self.optWindow.ui.cutButton.isChecked() :
                self.optWindow.ui.cutButton.setChecked(False)
            elif self.enableDraw :
                self.cutClick()
        
        elif number == "3" :

            if self.optWindow.ui.radioButtonMerge.isChecked():
                self.optWindow.ui.radioButtonAuto.setChecked(True)
                self.optWindow.ui.radioButtonMerge.setChecked(False)

            elif self.optWindow.ui.radioButtonAuto.isChecked() :
                self.optWindow.ui.radioButtonAuto.setChecked(False)
                self.optWindow.ui.radioButtonMerge.setChecked(True)

        elif number == "ESC":
            self.optWindow.ui.panButton.setChecked(False)
            self.panClick()
            

    #Fonction qui réalise le pan et qui permet de prévisualiser la trace à venir
    #Lors du pan la souris est présente sur l'écran qui contient l'image de gauche
    #Cette fonction s'assure que la souris reste sur l'écran conserné pendant le Pan afin de garder le curseur invisible  
    def mMoveEvent(self, ev):

        if self.optWindow.ui.panButton.isChecked() :
            self.deltaX = int((ev.x()-self.lastX) / 2)
            self.lastX = ev.x()
            self.deltaY = int((ev.y()-self.lastY) / 2)
            self.lastY = ev.y()
            leftView = self.graphWindowLeft.ui.graphicsView
            rightView = self.graphWindowRight.ui.graphicsView
            pixRange = 400
            if ev.x() > (self.screenLeft.width() - pixRange) or ev.x() < pixRange or ev.y() < pixRange or ev.y() > (self.screenLeft.height() - pixRange) :
                self.graphWindowLeft.ui.widget.setMouseTracking(False)
                win32api.SetCursorPos(self.leftScreenCenter)
                self.lastX = self.panCenterLeft[0]
                self.lastY = self.panCenterLeft[1]
                self.graphWindowLeft.ui.widget.setMouseTracking(True)
                
            leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() - self.deltaX)
            leftView.verticalScrollBar().setValue(leftView.verticalScrollBar().value() + self.deltaY)
            rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() + self.deltaX)
            rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() + self.deltaY)
        
            if (self.optWindow.ui.drawButton.isChecked() or self.optWindow.ui.cutButton.isChecked()) and not self.firstDrawClick and self.optWindow.ui.radioPolygonLayer.isChecked() :

                
                pointL = QPoint(self.panCenterLeft[0], self.panCenterLeft[1])
                pointR = QPoint(self.panCenterRight[0], self.panCenterRight[1])
                self.endDrawPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(pointL)
                self.endDrawPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(pointR)
                lineL = QLineF(self.startDrawPointLeft, self.endDrawPointLeft)
                
                xStartPoint = -self.startDrawPointLeft.x() + self.rightPicSize[0] + self.rightRect.x() + self.leftRect.x()
                startRightPoint = QPointF(xStartPoint, self.startDrawPointLeft.y())
                
                xEndPoint = -self.endDrawPointLeft.x() + self.rightPicSize[0] + self.rightRect.x() + self.leftRect.x()
                endRightPoint = QPointF(xEndPoint, self.endDrawPointLeft.y())
                
                lineR = QLineF(startRightPoint, endRightPoint)

                m_pen = QPen(QColor(0, 255, 255),10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

                if self.currentLeftLineObj:
                    self.graphWindowLeft.ui.graphicsView.scene().removeItem(self.currentLeftLineObj)
                
                if self.currentRightLineObj:
                    self.graphWindowRight.ui.graphicsView.scene().removeItem(self.currentRightLineObj)
                    
                self.currentLeftLineObj = self.graphWindowLeft.ui.graphicsView.scene().addLine(lineL, m_pen)
                self.currentRightLineObj = self.graphWindowRight.ui.graphicsView.scene().addLine(lineR, m_pen)

    #Fonction réalisé lors du click sur l'image
    #La fonctionnalité sont possible seulement lorque le mode Pan est activé
    #En mode Draw/Cut Polygon, elle trace les lignes et les polygones sur l'image
    #Il y a une communication avec QGIS pour afficher les polygones dans le logiciel
    #Lorsque les polygones se croisent, les polygones peuvent merger ou se séparer automatiquement
    #Il est aussi possible de découper les polygones
    #Les polygones s'affichent sur les deux images
    #Le clic droit permet de terminer une trace ou de quitter le pan si aucune option est sélectionné
    #Un clic permet de rafraîchir les valeurs XYZ affichées sur le menu
    def mPressEvent(self, ev):

        if self.optWindow.ui.panButton.isChecked():

            pointLeft = QPoint(self.panCenterLeft[0], self.panCenterLeft[1])
            pointRight = QPoint(self.panCenterRight[0], self.panCenterRight[1])
            centerPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(pointLeft)
            centerPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(pointRight)
            pixL = (centerPointLeft.x(), centerPointLeft.y())
            mirrorX = self.rightPicSize[0] - centerPointRight.x()
            pixR = (mirrorX, centerPointRight.y())
            Z = self.dualManager.calculateZ(pixL, pixR)
            XL, YL = self.leftPictureManager.pixelToCoord(pixL, Z)
            XR, YR = self.rightPictureManager.pixelToCoord(pixR, Z)
            X = (XL + XR) / 2
            Y = (YL + YR) / 2
            self.optWindow.ui.lineEditXClic.setText(str(round(X,5)))
            self.optWindow.ui.lineEditYClic.setText(str(round(Y,5)))
            self.optWindow.ui.lineEditZClic.setText(str(round(Z,2)))
            
            if (self.optWindow.ui.drawButton.isChecked() or self.optWindow.ui.cutButton.isChecked()) and self.optWindow.ui.radioPolygonLayer.isChecked() :

                if ev.button() == Qt.LeftButton:
                    if self.firstDrawClick :
                        pointL = QPoint(self.panCenterLeft[0], self.panCenterLeft[1])
                        pointR = QPoint(self.panCenterRight[0], self.panCenterRight[1])
                        self.startDrawPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(pointL)
                        self.startDrawPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(pointR)
                        self.firstDrawClick = False
                    else : 
                        self.startDrawPointLeft = self.endDrawPointLeft
                        self.startDrawPointRight = self.endDrawPointRight
                        self.listLeftLineObj.append(self.currentLeftLineObj)
                        self.listRightLineObj.append(self.currentRightLineObj)
                        self.currentLeftLineObj = None
                        self.currentRightLineObj = None
                    
                    X, Y = self.dualPixelToCoord(self.startDrawPointLeft, self.startDrawPointRight)
                    self.listDrawCoord.append(QgsPointXY(X,Y))

                elif ev.button() == Qt.RightButton:

                    self.firstDrawClick = True
                    if self.currentLeftLineObj :
                        self.graphWindowLeft.ui.graphicsView.scene().removeItem(self.currentLeftLineObj)
                        self.currentLeftLineObj = None

                    if self.currentRightLineObj :
                        self.graphWindowRight.ui.graphicsView.scene().removeItem(self.currentRightLineObj)
                        self.currentRightLineObj = None
                    
                    for item in self.listLeftLineObj:
                        self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
                    self.listLeftLineObj = []

                    for item in self.listRightLineObj:
                        self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
                    self.listRightLineObj = []
                    
                    if self.optWindow.ui.drawButton.isChecked():
                        newGeo = QgsGeometry.fromMultiPolygonXY([[self.listDrawCoord]])
                        currentVectorLayer = self.vectorLayer
                        
                        rectCoord = self.getShowRect()
                        listGeo = list(currentVectorLayer.getFeatures(rectCoord))
                        #Gestion des plusieurs intersections à faire
                        for item in listGeo : 
                            featureGeo = item.geometry()
                            
                            if newGeo.intersects(featureGeo) :
                                if self.optWindow.ui.radioButtonMerge.isChecked() :
                                    mergePolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
                                else :
                                    automaticPolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
                                break
                                
                        else :
                            addPolygon(currentVectorLayer, newGeo)
                    else :
                        currentVectorLayer = self.vectorLayer    
                        cutPolygon(currentVectorLayer, self.listDrawCoord)
                    
                    self.listDrawCoord = []
                    
                    self.addPolygonOnScreen()
                    
            elif self.optWindow.ui.radioPointLayer.isChecked() and self.optWindow.ui.drawButton.isChecked() :
                
                if ev.button() == Qt.LeftButton:
                    pointL = QPoint(self.panCenterLeft[0], self.panCenterLeft[1])
                    pointR = QPoint(self.panCenterRight[0], self.panCenterRight[1])
                    self.startDrawPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(pointL)
                    self.startDrawPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(pointR)
                    
                    X, Y = self.dualPixelToCoord(self.startDrawPointLeft, self.startDrawPointRight)
                    
                    point = QgsPointXY(X,Y)
                    geometry =  QgsGeometry.fromPointXY(point)
                    self.vectorLayer.startEditing()
                    feat = QgsFeature()
                    feat.setGeometry(geometry)
                    self.vectorLayer.dataProvider().addFeature(feat)
                    self.vectorLayer.commitChanges()
                    self.addPointOnScreen()


            elif ev.button() == Qt.RightButton :
                self.optWindow.ui.panButton.setChecked(False)
                self.panClick()

    #Fonction activer par la roulette de la souris
    #Avec la touche CTRL, il est possible de zoom In/Out sur les photos 
    #Sinon il est possible de déplacer l'image de droite et d'actualiser la valeur Z du centre 
    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        leftView = self.graphWindowLeft.ui.graphicsView
        rightView = self.graphWindowRight.ui.graphicsView
        
        if self.optWindow.ctrlClick or self.graphWindowLeft.ctrlClick or self.graphWindowRight.ctrlClick :    
            if factor > 1 : 
                leftView.scale(1.25, 1.25)
                rightView.scale(1.25, 1.25)
            else :
                leftView.scale(0.8, 0.8)
                rightView.scale(0.8, 0.8)

        else : 

            bPoint = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))
            if factor > 1 : 
                #leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() - 1)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() - 1)
            else :
                #leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() + 1)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() + 1)

            aPoint = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))
            diffX = aPoint.x() - bPoint.x()

            self.centerPixelRight = (self.centerPixelRight[0]-diffX, self.centerPixelRight[1]) 
            Z = self.dualManager.calculateZ(self.centerPixelLeft, self.centerPixelRight)
            self.optWindow.ui.lineEditCurrentZ.setText(str(round(Z,2)))


if __name__ == "__main__":
    app = stereoPhoto(sys.argv)
    sys.exit(app.exec_())