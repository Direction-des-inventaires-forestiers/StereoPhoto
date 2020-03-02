'''
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient une classe de type QApplication qui permet l'affichage d'images de grandes tailles sur des 
écrans de type Planar

La classe stereoPhoto gère l'application complète via un interface utilisateur
L'application permet de :
    - Importer des fichiers TIF de grandes tailles via un drag n drop
    - Réaliser une rotation de 90°, 180° et 270°
    - Réaliser un effet miroir sur l'horizontal et la verticale
    - Afficher les deux images importées sur les écrans Planar
    - Superposer automatiquement les images en fonction de leur fichier PAR associé
    - Offrir une option de Pan (via PushButton + Click souris) et de Zoom (via touche CTRL + Roulette) qui s'exécute simultanément sur les 2 photos
    - Offrir un déplacement opposé des deux images pour ajuster la stéréoscopie (pushButton offset + click souris et Roulette)
    - Rehausser les couleurs des images via une nouvelle fenêtre intéractive 
    - Traçage de forme géolocalisée
    - Communication avec QGIS

Le main permet tout simplement de lancer l'application

Plusieurs autres outils seront intégrés à cette application dans le futur :
    - Tracer les formes sur l'image de droite
    - Fonctionnalité de trace supplémentaire
    - Amélioration des fonctions de photogrammétrie 
    - Menu de choix de paramètres (numéro des écrans, curseur, keybinding, couleur des traces)
    - Affichage des zones supersposées seulement
    - Déplacement pour simple avec la souris (pas de drag avec la souris)
    - Gestion de projet 
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
import sys, os, time, math, qimage2ndarray

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
        
        self.action.setCheckable(True)
        self.action.toggled.connect(self.run)
         
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu("&StereoPhoto", self.action)

    #Retire le bout de l'application dans QGIS
    def unload(self):
        self.iface.removePluginMenu("&StereoPhoto", self.action)
        self.iface.removeToolBarIcon(self.action)
        
    #Initialisation de l'application, des variables
    #Connection entre les boutons du menu d'options (mOpt) et leur fonction attitrée
    #On fait apparaître le menu des options seul
    #Les écrans où l'on veut que les fênetres s'ouvrent sont choisi ici 
    def run(self):
    
        if self.action.isChecked() :
            self.intRightScreen = 0
            self.intLeftScreen = 1

            self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)
            self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)

            self.leftOrientation = 0
            self.rightOrientation = 0
            self.leftMiroir = 0
            self.rightMiroir = 0


            self.leftName = False 
            self.rightName = False 
            self.anaglyphActivate = False 

            self.showThreadLeftInProcess = False
            self.newLeftRequest = False
            self.showThreadRightInProcess = False
            self.newRightRequest = False
            self.enableDraw = False

            #MTM 1 à 17 prendre de 32181 à 32197 
            #MTM 10 32190
            #MTM 9  32189   
            self.crs = 32190
            self.Z = 300

            self.polygonOnScreen = []

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
            self.optWindow.ui.offsetButton.clicked.connect(self.offsetClick)
            self.optWindow.ui.drawButton.clicked.connect(self.drawClick)
            self.optWindow.ui.enhanceButton.clicked.connect(self.enhanceClick)
            self.optWindow.ui.cutButton.clicked.connect(self.cutClick)

            self.optWindow.ui.affichageButton.clicked.connect(self.loadWindows)
            self.optWindow.closeWindow.connect(self.optWindowClose)

            self.optWindow.show()
        
        else:
            self.optWindowClose()


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
        
    #Fonction de traitement d'image pour ajouter un effet mirroir à l'image
    #Deux modes sont possible, soit un effet mirroir à l'horizontal et un à la verticale
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
    #Si la photo est un fichier tif avec plusieurs versions de l'image, 
    #on récupère une version plus petite plutot que la produire, le résultat est donc instantané
    #Création d'un pictureManager pour associer les pixels à des coordonnées en fonction du .par de la photo
    def mNewLeftPic(self) : 

        self.optWindow.ui.boxOrientationLeft.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirLeft.setCurrentIndex(0)
          
        self.leftName = False
        self.enableOptionImage(False)
        self.optWindow.ui.affichageButton.setEnabled(False)

        try :
            del self.graphWindowLeft
            self.graphWindowRight.close()
        except :
            pass

        self.leftPic = Image.open(self.optWindow.ui.importLineLeft.text())
        self.demoLeftPic = Image.open(self.optWindow.ui.importLineLeft.text())

        if hasattr(self.demoLeftPic, "n_frames"): #and format == tif??
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

        fname = self.optWindow.ui.importLineLeft.text()
        filename = "/" +  fname.split("/")[-1].split(".")[0]
        self.path = fname.partition(filename)[0]

        pathPAR = self.optWindow.ui.importLineLeft.text().split(".")[0] + ".par"
        self.leftPictureManager = pictureManager(self.leftPic.size, pathPAR, "aa")

    #Idem à mNewLeftPic
    def mNewRightPic(self):
        
        self.optWindow.ui.boxOrientationRight.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirRight.setCurrentIndex(0)

        self.rightOrientation = 0
        self.rightMiroir = 0
        self.rightName = False
        self.enableOptionImage(False)
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

        npPicture = np.array(self.demoRightPic)
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

    #Fonction qui créer une nouvelle couche de type VectorLayer dans QGIS 
    #La couche permet d'afficher les polygones tracés sur l'image dans QGIS
    def mNewVectorLayer(self):
        shapeName = self.optWindow.ui.importLineVectorLayer.text()
        
        if self.optWindow.ui.affichageButton.isEnabled() :
            self.optWindow.ui.drawButton.setEnabled(True)
            self.optWindow.ui.cutButton.setEnabled(True)
    
        self.enableDraw = True

        self.vectorLayer = createShape(shapeName, self.crs)
        QgsProject.instance().setCrs(self.vectorLayer.crs())

    #Fonction qui lance l'affichage des deux fenêtres sur les écrans Planar (choix dans l'init)
    #Création du dualManager qui utilise les pictures managers pour positionner les photos selon les régions superposées
    #Affichage de l'image complète
    #Affichage d'un curseur au centre des fenêtres  
    def loadWindows(self, value):

        self.graphWindowLeft.close()
        self.graphWindowRight.close()

        self.dualManager = dualManager(self.leftPictureManager, self.rightPictureManager, self.Z)
        self.leftRect, self.rightRect = self.dualManager.getRect()
        self.graphWindowLeft.cursorRectInit(self.screenLeft.width(), self.screenLeft.height())
        self.graphWindowRight.cursorRectInit(self.screenRight.width(), self.screenRight.height())
        
        r = self.dualManager.calculateZ([9357,8860], [4861,8876])
        a = self.leftPictureManager.pixelToCoord([9357,8860],self.Z)
        b = self.rightPictureManager.coordToPixel(a,self.Z)

        self.graphWindowLeft.show()
        self.graphWindowRight.show()
        self.graphWindowLeft.ui.graphicsView.fitInView(self.leftRect, Qt.KeepAspectRatio)
        self.graphWindowRight.ui.graphicsView.fitInView(self.rightRect, Qt.KeepAspectRatio)
        self.optWindow.activateWindow()
        self.enableOptionImage(True)

    
    #Fonction pour permettre l'utilisation des boutons d'option pour les fenêtres séparées 
    #Action peut être True ou False selon la permission que l'on veut donner
    def enableOptionImage(self, action):
        self.optWindow.ui.panButton.setEnabled(action)
        self.optWindow.ui.offsetButton.setEnabled(action)
        if self.enableDraw : 
            self.optWindow.ui.drawButton.setEnabled(action)
            self.optWindow.ui.cutButton.setEnabled(action)

    #Fonction pour zoom In sur les deux photos simultannément
    def mZoomIn(self) :
        self.graphWindowLeft.ui.graphicsView.scale(1.25, 1.25)
        self.graphWindowRight.ui.graphicsView.scale(1.25, 1.25)

    #Fonction pour zoom Out sur les deux photos simultannément
    def mZoomOut(self):
        self.graphWindowLeft.ui.graphicsView.scale(0.8, 0.8)
        self.graphWindowRight.ui.graphicsView.scale(0.8, 0.8)

    #Fonction pour permettre l'imporation de l'image sur le graphicsView
    #Similaire au fichier enhanceManager, une version de basse résolution de l'image est affichée immédiatement
    #Par la suite, un un thread est lancer pour venir afficher les plus hautes résolutions
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
            self.threadSeekLeft(pointZero, pointMax, 0.5, 1, 2)
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
            self.threadSeekRight(pointZero, pointMax, 0.5, 1, 2)
            self.showThreadRightInProcess = True
        else :
            self.newRightRequest = True

        self.graphWindowRight.ui.widget.mouseMoveEvent = self.mMoveEvent
        self.graphWindowRight.ui.widget.mousePressEvent = self.mPressEvent
        self.graphWindowRight.ui.widget.wheelEvent = self.wheelEvent
        self.graphWindowRight.ui.graphicsView.show()
        self.optWindow.ui.importDoneRight.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.optWindow.ui.importButtonRight.setEnabled(True)
        self.rightName = True 
        if self.leftName :
            self.optWindow.ui.affichageButton.setEnabled(True)
            self.optWindow.ui.enhanceButton.setEnabled(True)


    #Utiliser par threadShow pour afficher une portion de l'image
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
    #Elle relance le thread avec la même résolution si une requête a été faite sinon
    #elle relance le thread avec une plus grande résolution d'image 
    def seekLeftDone(self):

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
       
    
    #Désactive le offset, le cut et le draw pour activer le pan     
    def panClick(self):
        self.optWindow.ui.offsetButton.setChecked(False)
        self.optWindow.ui.drawButton.setChecked(False)
        self.optWindow.ui.cutButton.setChecked(False)
        self.graphWindowLeft.ui.widget.setMouseTracking(False)

    #Désactive le pan, le cut et le draw pour activer le offset
    def offsetClick(self):
        self.optWindow.ui.panButton.setChecked(False)
        self.optWindow.ui.drawButton.setChecked(False)
        self.optWindow.ui.cutButton.setChecked(False)
        self.graphWindowLeft.ui.widget.setMouseTracking(False)

    #Désactive le offset, le cut et le pan pour activer le draw
    def drawClick(self):
        self.optWindow.ui.panButton.setChecked(False)
        self.optWindow.ui.offsetButton.setChecked(False)
        self.optWindow.ui.cutButton.setChecked(False)
        self.graphWindowLeft.ui.widget.setMouseTracking(True)

        self.listDrawCoord = []
        self.listLineObj = []
        self.firstDrawClick = True
        self.currentLineObj = None

    #Désactive le offset, le pan et le draw pour activer le cut
    def cutClick(self):
        self.optWindow.ui.panButton.setChecked(False)
        self.optWindow.ui.offsetButton.setChecked(False)
        self.optWindow.ui.drawButton.setChecked(False)
        self.graphWindowLeft.ui.widget.setMouseTracking(True)

        self.listDrawCoord = []
        self.listLineObj = []
        self.firstDrawClick = True
        self.currentLineObj = None
    
    #Ouverture de la fenêtre de rehaussement
    def enhanceClick(self):
        nameLeft = self.optWindow.ui.importLineLeft.text()
        nameRight = self.optWindow.ui.importLineRight.text()
        self.enhanceManager = enhanceManager(nameLeft,nameRight,self.listParam)
        self.enhanceManager.listParamSignal.connect(self.applyEnhance)

    #Permet le lancement du traitement de modification des images
    def applyEnhance(self, listParam):
        self.enhanceManager.listParamSignal.disconnect(self.applyEnhance)
        self.listParam = listParam
        self.mImportLeft()
        self.mImportRight()

    #Fonction qui réalise le pan et le offset selon le bouton sélectionné
    #Elle permet aussi de tracer une ligne pour prévisualiser la trace à venir 
    def mMoveEvent(self, ev):
        if self.optWindow.ui.panButton.isChecked() :
            leftView = self.graphWindowLeft.ui.graphicsView
            rightView = self.graphWindowRight.ui.graphicsView
            delta = ev.pos() - self.panPosition
            leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() - delta.x())
            leftView.verticalScrollBar().setValue(leftView.verticalScrollBar().value() - delta.y())
            rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() + delta.x())
            rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() - delta.y())
            self.panPosition = ev.pos()
        
        elif self.optWindow.ui.offsetButton.isChecked():
            leftView = self.graphWindowLeft.ui.graphicsView
            rightView = self.graphWindowRight.ui.graphicsView
            delta = ev.pos() - self.panPosition
            leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() - delta.x())
            leftView.verticalScrollBar().setValue(leftView.verticalScrollBar().value() - delta.y())
            rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() - delta.x())
            rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() + delta.y())
            self.panPosition = ev.pos()

        elif (self.optWindow.ui.drawButton.isChecked() or self.optWindow.ui.cutButton.isChecked()) and not self.firstDrawClick :

            self.endDrawPoint = self.graphWindowLeft.ui.graphicsView.mapToScene(ev.pos())
            m_line = QLineF(self.startDrawPoint, self.endDrawPoint)
            m_pen = QPen(QColor(0, 255, 255),10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)

            if self.currentLineObj:
                self.graphWindowLeft.ui.graphicsView.scene().removeItem(self.currentLineObj)
                
            self.currentLineObj = self.graphWindowLeft.ui.graphicsView.scene().addLine(m_line, m_pen)

    #Fonction réalisé lors du click sur l'image
    #En mode Pan et Offset, elle prend la première position de la souris
    #En mode Draw/Cut Polygon, elle trace les lignes et les polygones sur l'image
    #Il y a une communication avec QGIS pour afficher les polygones dans le logiciel
    #Lorsque les polygones se croisent, les polygones peuvent merger ou se séparer automatiquement
    #Il est aussi possible de découper les polygones
    def mPressEvent(self, ev):
        if self.optWindow.ui.panButton.isChecked() or self.optWindow.ui.offsetButton.isChecked() :
            self.panPosition = ev.pos()

        elif self.optWindow.ui.drawButton.isChecked() or self.optWindow.ui.cutButton.isChecked():

            if ev.button() == Qt.LeftButton:
                if self.firstDrawClick :
                    self.startDrawPoint = self.graphWindowLeft.ui.graphicsView.mapToScene(ev.pos())
                    self.firstDrawClick = False
                else : 
                    self.startDrawPoint = self.endDrawPoint
                    self.listLineObj.append(self.currentLineObj)
                    self.currentLineObj = None
                
                X, Y = self.leftPictureManager.pixelToCoord((self.startDrawPoint.x() , self.startDrawPoint.y()), self.Z)
                self.listDrawCoord.append(QgsPointXY(X,Y))

            elif ev.button() == Qt.RightButton:

                self.firstDrawClick = True
                if self.currentLineObj :
                    self.graphWindowLeft.ui.graphicsView.scene().removeItem(self.currentLineObj)
                    self.currentLineObj = None
                
                for item in self.listLineObj:
                    self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
                self.listLineObj = []
                
                if self.optWindow.ui.drawButton.isChecked():
                    newGeo = QgsGeometry.fromMultiPolygonXY([[self.listDrawCoord]])
                    currentVectorLayer = self.vectorLayer
                    #Gestion des plusieurs intersections à faire
                    for i in range(currentVectorLayer.featureCount()):
                        featureGeo = currentVectorLayer.getGeometry(i)
                        if newGeo.intersects(featureGeo) :
                            if self.optWindow.ui.radioButtonMerge.isChecked() :
                                mergePolygon(featureGeo, i, newGeo, currentVectorLayer)
                            else :
                                automaticPolygon(featureGeo, i, newGeo, currentVectorLayer)
                            break
                            
                    else :
                        addPolygon(currentVectorLayer, newGeo)
                else :
                    currentVectorLayer = self.vectorLayer    
                    cutPolygon(currentVectorLayer, self.listDrawCoord)
                
                self.listDrawCoord = []
                
                for item in self.polygonOnScreen :
                    self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
                
                for i in range(currentVectorLayer.featureCount()):
                    
                    featureGeo = currentVectorLayer.getGeometry(i)
                    
                    if featureGeo.isNull() == False :

                        listQgsPoint = featureGeo.asMultiPolygon()[0][0]
                        polygon = QPolygonF()
                        for item in listQgsPoint :
                            xPixel, yPixel = self.leftPictureManager.coordToPixel((item.x() , item.y()), self.Z)     
                            polygon.append(QPointF(xPixel, yPixel))

                        m_pen = QPen(QColor(0, 255, 255),10, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                        obj = self.graphWindowLeft.ui.graphicsView.scene().addPolygon(polygon, m_pen)
                        self.polygonOnScreen.append(obj)


    #Fonction pour zoom In/Out sur les photos avec la souris, elle zoom dans la 
    #direction de la souris 
    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        leftView = self.graphWindowLeft.ui.graphicsView
        rightView = self.graphWindowRight.ui.graphicsView
        
        if self.optWindow.ctrlClick or self.graphWindowLeft.ctrlClick or self.graphWindowRight.ctrlClick :
            oldPos = self.graphWindowLeft.ui.graphicsView.mapToScene(event.pos())
            if factor > 1 : 
                self.mZoomIn()
            else :
                self.mZoomOut()

            newPos = self.graphWindowLeft.ui.graphicsView.mapToScene(event.pos())
            delta = newPos- oldPos

            self.graphWindowRight.ui.graphicsView.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.graphWindowLeft.ui.graphicsView.setTransformationAnchor(QGraphicsView.NoAnchor)
            self.graphWindowRight.ui.graphicsView.translate(-delta.x(), delta.y())
            self.graphWindowLeft.ui.graphicsView.translate(delta.x(), delta.y())
            self.graphWindowRight.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            self.graphWindowLeft.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorViewCenter)
            
        else : 
            if factor > 1 : 
                leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() - 3)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() - 3)
            else :
                leftView.horizontalScrollBar().setValue(leftView.horizontalScrollBar().value() + 3)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() + 3)


if __name__ == "__main__":
    app = stereoPhoto(sys.argv)
    sys.exit(app.exec_())