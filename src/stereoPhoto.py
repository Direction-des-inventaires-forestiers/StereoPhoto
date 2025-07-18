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
    - Utiliser un shapefile 3D

Le main permet tout simplement de lancer l'application

Plusieurs autres outils seront intégrés à cette application dans le futur :
    - Fonctionnalité de trace supplémentaire
    - Amélioration des fonctions de photogrammétrie 
    - Menu de choix de paramètres (curseur, keybinding, couleur des traces)
    - Affichage des zones supersposées seulement
    - Gestion de projet
    
    et bien d'autre
Dans EFOTO, il semble avoir un décalage de 16 pixels en x et en y pour la photo de droite right/leftcursoroffset -> pourrait s'appliquer pour le curseur


'''
from qgis.gui import *
from qgis.core import *
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

from PIL import Image
import numpy as np
from . import resources

#from .ui_optWindowCleaner import optionWindow
from .ui_optionWindow import optionWindow
from .ui_graphicsWindow import graphicsWindow 
from .ui_getVectorLayer import getImageListDialog
from .ui_paramWindow import paramWindow
from .worldManager import pictureManager, dualManager, createWKTString
from .enhanceManager import enhanceManager, threadShow, imageEnhancing, pictureLayout
from .drawFunction import *
#from .folderManager import getParDict, findPossiblePair, findNeighbour, findPairWithCoord
from .gestionDossier import getParDict, get_neighbors_and_pairs, findPairWithCoord, compute_overlap
import sys, os, time, math
from osgeo import gdal

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

    #Retire le bouton de l'application dans QGIS
    def unload(self):
        self.iface.removePluginMenu("&StereoPhoto", self.action)
        self.iface.removeToolBarIcon(self.action)

    #Initialisation de l'application et des variables
    #Connection entre les boutons du menu d'options (mOpt) et leurs fonctions attitrées
    #Ouverture du menu d'options
    def run(self):

        if self.action.isChecked() :

            self.initGlobalParam()           

            self.paramMenu = paramWindow()
            self.optWindow = optionWindow(self.iface)
            
            self.setConnection() 

            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.optWindow)
            self.optWindow.raise_()

            if self.paramMenu.currentDictParam['LastPath'] : self.optWindow.ui.importLineProject.setText(self.paramMenu.currentDictParam['LastPath'])
            
            if self.paramMenu.currentDictParam['MNTPath'] : 
                self.optWindow.currentMNTPath = self.paramMenu.currentDictParam['MNTPath']
                self.optWindow.ui.importLineMNT.setText(os.path.basename(self.optWindow.currentMNTPath))
                self.optWindow.ui.radioButtonCut.setEnabled(True)
                self.optWindow.ui.radioButtonDraw.setEnabled(True)
                self.optWindow.ui.pushButtonRemoveMNT.setEnabled(True)
            else : self.optWindow.currentMNTPath = ''

        else :
            self.iface.removeDockWidget(self.optWindow)
            self.optWindowClose()
            del self.optWindow
            try : del self.currentParDict
            except: pass

    def initGlobalParam(self):
        self.showThreadLeftInProcess = False
        self.newLeftRequest = False
        self.showThreadRightInProcess = False
        self.newRightRequest = False
        self.enableDraw = False
        self.enableShow = False
        self.ignoreMouseAction = False

        self.zoomClick = False
        self.longClick = False

        self.firstDrawClick = True
        self.listDrawCoord = []
        self.listCutCoord = []

        self.list2DPoint = []
        self.list3DPoint = []

        self.listLeftLineObj = []
        self.listRightLineObj = []
        self.currentLeftLineObj = None
        self.currentRightLineObj = None

        self.polygonOnLeftScreen = []
        self.polygonOnRightScreen = []
        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        
        self.greyRectOnLeftScreen = []
        self.greyRectOnRightScreen = []

        self.listParam = [0, 0, 0, 0, 0, 0, 0, False, False, []]
        self.lastEnhanceParam = [0, 0, 0, 0, 0, 0, 0, False, False, []]

        self.buttonPosition = None

        #À retirer, mais je dois tester avant
        self.leftOrientation = self.rightOrientation = self.leftMiroir = self.rightMiroir = 0
    
    def setConnection(self) : 

        self.optWindow.ui.importLineProject.textChanged.connect(self.newPictureFile)
        self.optWindow.ui.importLineVectorLayer.textChanged.connect(self.mNewVectorLayer)
        self.optWindow.ui.pushButtonShowPicture.clicked.connect(self.createGraphicsWindows)
        self.optWindow.ui.pushButtonShowIDList.clicked.connect(self.showIDList)
        self.optWindow.ui.enhanceButton.clicked.connect(self.enhanceClick)
        self.optWindow.ui.pushButtonFindBestPair.clicked.connect(self.findPairWithPosition)
        self.optWindow.ui.pushButtonOpenParam.clicked.connect(self.showParamMenu)
        self.optWindow.closeWindow.connect(self.optWindowClose)
        self.optWindow.ui.pushButtonCloseWindow.clicked.connect(self.closeAllSideWindows)

    #Fonction appelée lors de la fermeture du mOpt
    #Si l'on ferme le mOpt toutes les autres fenêtres Qt se ferment
    def closeAllSideWindows(self) :
        self.enableShow = False
        scene = QGraphicsScene()
        if hasattr(self, "tSeekLeft"): 
            try : self.tSeekLeft.newImage.disconnect(self.addLeftPixmap)
            except: pass
            self.tSeekLeft.keepRunning = False
        if hasattr(self, "tSeekRight"): 
            try : self.tSeekRight.newImage.disconnect(self.addRightPixmap)
            except: pass
            self.tSeekRight.keepRunning = False
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
        self.manageQGISCursor([0,0],True)
        self.optWindow.ui.pushButtonCloseWindow.setEnabled(False)
        self.paramMenu.currentDictParam['MNTPath'] = self.optWindow.currentMNTPath
        self.paramMenu.saveToJSON()
    
    def optWindowClose(self):
        self.closeAllSideWindows()
        self.optWindow.close()
        self.paramMenu.close()
        self.optWindow.vectorWindow.close()
        if self.action.isChecked() : self.action.setChecked(False)
    
    def showParamMenu(self): 

        nbScreen = QApplication.desktop().screenCount()-1
        self.paramMenu.ui.spinBoxScreenLeft.setMaximum(nbScreen)
        self.paramMenu.ui.spinBoxScreenRight.setMaximum(nbScreen)

        self.paramMenu.show()
        if self.paramMenu.isMinimized() : self.paramMenu.showNormal()
        
        self.paramMenu.raise_()
        
    def newPictureFile(self):
        
        self.currentMainPath = self.optWindow.ui.importLineProject.text()
        self.optWindow.projectPath = os.path.dirname(self.currentMainPath)
        self.currentParDict = getParDict(self.currentMainPath)
        
        
        if len(self.currentParDict) < 2 :
            self.optWindow.ui.pushButtonShowIDList.setEnabled(False)
            self.optWindow.ui.enhanceButton.setEnabled(False)
            self.optWindow.ui.pushButtonShowPicture.setEnabled(False)
            self.optWindow.ui.pushButtonFindBestPair.setEnabled(False)
            return

        else : 
            self.optWindow.ui.pushButtonShowIDList.setEnabled(True)
            self.optWindow.ui.enhanceButton.setEnabled(True)
            self.optWindow.ui.pushButtonShowPicture.setEnabled(True)
            self.optWindow.ui.pushButtonFindBestPair.setEnabled(True)

        if self.paramMenu.currentDictParam['LastName'] in self.currentParDict.keys() : 
            parToUse = self.paramMenu.currentDictParam['LastName']
            if float(self.paramMenu.currentDictParam['LastX']) != 0.0 :
                x = float(self.paramMenu.currentDictParam['LastX'])
                y = float(self.paramMenu.currentDictParam['LastY'])
                z = float(self.paramMenu.currentDictParam['LastZ'])
                scaleX = float(self.paramMenu.currentDictParam['ScaleX'])
                scaleY = float(self.paramMenu.currentDictParam['ScaleY'])
                self.lastCurrentView = (x,y,z,scaleX,scaleY)
            else : self.lastCurrentView = ()
        
        else : 
            self.lastCurrentView = ()
            #self.optWindow.removeImportMNT()
            self.removePolygonOnScreen()
            parToUse = next(iter(self.currentParDict))
            
        self.paramMenu.currentDictParam['LastPath'] = self.currentMainPath

        if self.enableShow : self.closeAllSideWindows()
        self.setPairWithPARId(parToUse)

    def showIDList(self) : 
        self.pictureSelectWindow = getImageListDialog(sorted(self.currentParDict),self.leftParID)
        self.pictureSelectWindow.ui.buttonBox.accepted.connect(self.pictureSelectionAccept)
        self.pictureSelectWindow.ui.buttonBox.rejected.connect(lambda : self.pictureSelectWindow.close())
        self.pictureSelectWindow.show()
    
    def pictureSelectionAccept(self):
        pictureID = self.pictureSelectWindow.ui.listWidget.selectedItems()[0].text()
        #if self.setPairID(pictureID) :  self.addNewPair()
        self.setPairWithPARId(pictureID)
        
        if self.enableShow and self.leftParID != '': self.loadNewPair()
        self.lastCurrentView = ()
        self.pictureSelectWindow.close()

    def setPairWithPARId(self, parID, secondID=None) : 

        #Retourne les paires left et right ainsi que les 4 voisins NOSE
        #Voisin Est/Ouest peut être une image qui n'est pas une paire
        #Voisin Nord/Sud peut être une paire pour assurer la continuitée de la vue courante
        self.infoNeighbors = get_neighbors_and_pairs(parID, self.currentParDict)

        if secondID : 
            self.leftParID = parID
            self.rightParID = secondID
        
        elif self.infoNeighbors['leftPic'][0] is None and self.infoNeighbors['rightPic'][0] is None : 
            self.leftParID == ''
            return
        
        elif self.infoNeighbors['rightPic'][0] is None : 
            self.leftParID = self.infoNeighbors['leftPic'][0]
            self.rightParID = parID
                        
        else : 
            self.leftParID = parID
            self.rightParID = self.infoNeighbors['rightPic'][0]

        self.optWindow.ui.labelLeftName.setText(self.leftParID)
        self.optWindow.ui.labelRightName.setText(self.rightParID)
        self.paramMenu.currentDictParam['LastName'] = self.leftParID

        self.currentLeftTIF = self.currentMainPath + '/' + self.leftParID + '.tif'
        self.currentLeftPAR = self.currentMainPath  + '/' + self.leftParID + '.par'
        self.currentRightTIF = self.currentMainPath  + '/' + self.rightParID + '.tif'
        self.currentRightPAR = self.currentMainPath  + '/' + self.rightParID + '.par'

        infoNeighborR = get_neighbors_and_pairs(self.rightParID, self.currentParDict)
        self.infoNeighbors = get_neighbors_and_pairs(self.leftParID, self.currentParDict)

        self.currentLeftID = True if self.infoNeighbors['left'][0] else False
        
        if infoNeighborR['rightPic'][0] is None and infoNeighborR['right'][0] : 
            self.currentRightID = True
            self.infoNeighbors['right'] = infoNeighborR['right']

        elif infoNeighborR['rightPic'][0] : self.currentRightID = True
        else : self.currentRightID = False
        
        self.currentUpID = True if len(self.infoNeighbors['up']) != 0 else False
        self.currentDownID = True if len(self.infoNeighbors['down']) != 0 else False
        #print(self.infoNeighbors)

        
    def setLastView(self) :
        rectViewPort = self.graphWindowLeft.ui.graphicsView.viewport().rect()
        leftCV = self.graphWindowLeft.ui.graphicsView.mapToScene(rectViewPort).boundingRect() 
        windowSize = (leftCV.width(),leftCV.height()) 

        coord = self.pointTranslator()
        self.lastCurrentView = coord + windowSize

        self.paramMenu.currentDictParam['LastX'] = str(self.lastCurrentView[0])
        self.paramMenu.currentDictParam['LastY'] = str(self.lastCurrentView[1])
        self.paramMenu.currentDictParam['LastZ'] = str(self.lastCurrentView[2])
        self.paramMenu.currentDictParam['ScaleX'] = str(self.lastCurrentView[3])
        self.paramMenu.currentDictParam['ScaleY'] = str(self.lastCurrentView[4])

    
    def findNextPair(self, ori):
        self.setLastView()
        secondID = None
        if ori == 'L': newID = self.infoNeighbors['left'][0]
        elif ori == 'R': newID = self.infoNeighbors['right'][0]
        
        elif ori == 'D': #down/Bas
            if len(self.infoNeighbors['down']) == 2 :
                name_1 = self.infoNeighbors['down'][0][0]
                name_2 = self.infoNeighbors['down'][1][0]
                x0_1 = self.currentParDict[name_1][0]
                x0_2 = self.currentParDict[name_2][0]
                if x0_1 < x0_2 : 
                    newID = name_1
                    secondID = name_2
                else : 
                    newID = name_2
                    secondID = name_1

            else : newID = self.infoNeighbors['down'][0][0]
        
        elif ori == 'U': #up/Haut
            if len(self.infoNeighbors['up']) == 2 :
                name_1 = self.infoNeighbors['up'][0][0]
                name_2 = self.infoNeighbors['up'][1][0]
                x0_1 = self.currentParDict[name_1][0]
                x0_2 = self.currentParDict[name_2][0]
                if x0_1 < x0_2 : 
                    newID = name_1
                    secondID = name_2
                else : 
                    newID = name_2
                    secondID = name_1

            else : newID = self.infoNeighbors['up'][0][0]
        
        #if self.setPairID(newID) :  self.addNewPair()
        self.setPairWithPARId(newID,secondID)

        self.loadNewPair()

    def findPairWithPosition(self) :

        qgisExtent = self.canvas.extent()
        centerCoord = (qgisExtent.xMinimum()+qgisExtent.width()/2,qgisExtent.yMinimum()+qgisExtent.height()/2)
        bestFit = findPairWithCoord(self.currentParDict,centerCoord)

        width = qgisExtent.width()
        height = qgisExtent.height()
        imageID = bestFit[0] 
        distance = bestFit[1]

        #Zone de 3 km pour être proche de la photo le plus possible
        if max(width,height,distance) < 3000 : 
            self.buttonPosition = centerCoord
            #if self.setPairID(imageID) :  self.addNewPair()
            self.setPairWithPARId(imageID)
            if self.enableShow and self.leftParID != '' : self.loadNewPair()
        else : self.buttonPosition = None

    
    def createGraphicsWindows(self) : 

        if self.enableShow : 
            self.windowHandler('picture')
            return

        self.intLeftScreen = self.paramMenu.ui.spinBoxScreenLeft.value()
        self.intRightScreen = self.paramMenu.ui.spinBoxScreenRight.value()
        self.rightMiroir = 0 if self.paramMenu.ui.checkBoxFlip.isChecked() else 3


        self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)
        self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)

        self.panCenterLeft = (int(self.screenLeft.width()/2), int(self.screenLeft.height()/2))
        self.panCenterRight = (int(self.screenRight.width()/2), int(self.screenRight.height()/2))

        self.leftScreenCenter = (self.screenLeft.x() + int(self.screenLeft.width()/2), self.screenLeft.y() + int(self.screenLeft.height()/2))

        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height())
        self.graphWindowLeft = graphicsWindow("Image Gauche")
        self.graphWindowLeft.setWindowState(Qt.WindowMaximized)
        self.graphWindowLeft.ui.graphicsView.setGeometry(rect)
        self.graphWindowLeft.ui.widget.setGeometry(rect)
        self.graphWindowLeft.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))
        self.graphWindowLeft.keyPressed.connect(self.keyboardHandler)
        self.graphWindowLeft.setFocusPolicy(Qt.StrongFocus) 
        #self.graphWindowLeft.leaveEvent = self.windowHandlerEvent 
        #self.graphWindowLeft.enterEvent = self.windowHandlerEvent

        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height())
        self.graphWindowRight = graphicsWindow("Image Droite")
        self.graphWindowRight.setWindowState(Qt.WindowMaximized)
        self.graphWindowRight.ui.graphicsView.setGeometry(rect)
        self.graphWindowRight.ui.widget.setGeometry(rect)
        self.graphWindowRight.move(QPoint(self.screenRight.x(), self.screenRight.y()))
        self.graphWindowRight.keyPressed.connect(self.keyboardHandler)
        self.graphWindowRight.setFocusPolicy(Qt.StrongFocus) 
        
        self.graphWindowLeft.cursorRectInit(self.screenLeft.width(), self.screenLeft.height())
        self.graphWindowRight.cursorRectInit(self.screenRight.width(), self.screenRight.height())

        width = self.paramMenu.ui.spinBoxPenWidth.value()
        color = QColor(self.paramMenu.ui.comboBoxColor.currentText())

        self.my_pen = QPen(color, width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
        self.my_pen.setCosmetic(True)

        self.enableShow = True
        self.optWindow.ui.pushButtonCloseWindow.setEnabled(True)
        self.loadNewPair()

        
    def loadNewPair(self,mouseAction=True):

        if hasattr(self, "tSeekLeft"): 
            try : self.tSeekLeft.newImage.disconnect(self.addLeftPixmap)
            except: pass
            self.tSeekLeft.keepRunning = False


        if hasattr(self, "tSeekRight"): 
            try : self.tSeekRight.newImage.disconnect(self.addRightPixmap)
            except: pass
            self.tSeekRight.keepRunning = False
            
        self.graphWindowLeft.ui.graphicsView.setTransform(QTransform())
        self.graphWindowRight.ui.graphicsView.setTransform(QTransform())  
        
        #Récupération de la taille complète des images
        leftPic = gdal.Open(self.currentLeftTIF)
        rightPic = gdal.Open(self.currentRightTIF)  
        self.fullLeftPicSize = (leftPic.RasterXSize, leftPic.RasterYSize)
        self.fullRightPicSize = (rightPic.RasterXSize, rightPic.RasterYSize)
        leftPic = None
        rightPic = None
        
        self.leftPictureManager = pictureManager(self.fullLeftPicSize, self.currentLeftPAR)
        self.rightPictureManager = pictureManager(self.fullRightPicSize, self.currentRightPAR)

        leftBbox = self.currentParDict[self.leftParID]
        rightBbox = self.currentParDict[self.rightParID]

        _, bboxOverlap = compute_overlap(leftBbox, rightBbox)

        gpzL = self.leftPictureManager.groundPixelSize
        gpzR = self.rightPictureManager.groundPixelSize

        r11L = self.leftPictureManager.r11
        r12L = self.leftPictureManager.r12

        r11R = self.rightPictureManager.r11
        r12R = self.rightPictureManager.r12

        self.cropValueLeft = self.calculDecoupageAvecRotation(self.fullLeftPicSize,bboxOverlap,leftBbox,gpzL,r11L,r12L)
        self.cropValueRight = self.calculDecoupageAvecRotation(self.fullRightPicSize,bboxOverlap,rightBbox,gpzR,r11R,r12R)
        
        self.leftPicSize = (self.cropValueLeft[2]-self.cropValueLeft[0],self.cropValueLeft[3]-self.cropValueLeft[1])
        self.rightPicSize = (self.cropValueRight[2]-self.cropValueRight[0],self.cropValueRight[3]-self.cropValueRight[1])
        
        self.leftRect = QRectF(0, 0, self.leftPicSize[0], self.leftPicSize[1])
        self.rightRect = QRectF(0, 0, self.rightPicSize[0], self.rightPicSize[1]) 
        self.graphWindowLeft.currentRect = self.leftRect
        self.graphWindowRight.currentRect = self.rightRect

        self.dualManager = dualManager(self.leftPictureManager, self.rightPictureManager)
        
        self.getSceneFromPath(self.currentLeftTIF, self.leftMiroir, self.graphWindowLeft, self.cropValueLeft)
        self.getSceneFromPath(self.currentRightTIF, self.rightMiroir, self.graphWindowRight, self.cropValueRight)
        
        self.graphWindowLeft.ui.graphicsView.show()
        self.graphWindowRight.ui.graphicsView.show()
        self.graphWindowRight.show()
        self.graphWindowLeft.show()
        
        if mouseAction : self.windowHandler('picture')

        pixel = self.pointTranslator(onlyPixel=True)
        
        Z = self.dualManager.calculateZ(pixel[0], pixel[1])
        self.initAltitude = Z
        self.afficherPositionDepart()

        self.optWindow.ui.labelAltitude.setText(str(round(Z,5)))

        self.polygonOnLeftScreen = []
        self.polygonOnRightScreen = []
        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        self.greyRectOnLeftScreen = []
        self.greyRectOnRightScreen = []

        LGV = self.graphWindowLeft.ui.graphicsView
        leftTop = LGV.mapToScene(QPoint(0,0))
        leftButtom = LGV.mapToScene(QPoint(LGV.width(),LGV.height()))

        if self.showThreadLeftInProcess == False :
            self.threadSeekLeft(leftTop, leftButtom, 1, 0, 1)
            self.showThreadLeftInProcess = True
        else :
            self.newLeftRequest = True
        

        RGV = self.graphWindowRight.ui.graphicsView
        rightTop = RGV.mapToScene(QPoint(0,0))
        rightButtom = RGV.mapToScene(QPoint(RGV.width(),RGV.height()))


        if self.showThreadRightInProcess == False :
            self.threadSeekRight(rightTop, rightButtom, 1, 0, 1)
            self.showThreadRightInProcess = True
        else :
            self.newRightRequest = True           
        
        leftTransform = self.getQtransform(self.leftPictureManager)
        rightTransform = self.getQtransform(self.rightPictureManager)

        if not self.paramMenu.ui.checkBoxFlip.isChecked() : 

            mirror_transform = QTransform()
            mirror_transform.scale(-1, 1)
            mirror_transform.translate(-self.fullRightPicSize[0], 0)
            rightTransform =  rightTransform * mirror_transform

        self.graphWindowLeft.ui.graphicsView.setTransform(leftTransform)
        self.graphWindowRight.ui.graphicsView.setTransform(rightTransform)    
    
        
        self.afficherPositionDepart()
        self.buttonPosition = None
        
        if self.enableDraw : 
            self.startPolygonThread()

    def getQtransform(self, pictureManager : pictureManager):
        r11 = pictureManager.r11
        r12 = pictureManager.r12
        r21 = pictureManager.r21
        r22 = pictureManager.r22
        ppa_x = pictureManager.PPAx
        ppa_y =  pictureManager.PPAy
        
        
        t = QTransform()
        t.translate(ppa_x, ppa_y)
        t *= QTransform(r11, r12, r21, r22, 0, 0)
        t.translate(-ppa_x, -ppa_y)
        return t
    
    def afficherPositionDepart(self) : 
        
        if self.buttonPosition : 
            if self.optWindow.currentMNTPath : 
                mntDS = gdal.Open(self.optWindow.currentMNTPath)
                mntBand = mntDS.GetRasterBand(1)
                mntGeo = mntDS.GetGeoTransform()
                px = math.floor((self.buttonPosition[0] - mntGeo[0]) / mntGeo[1]) 
                py = math.floor((self.buttonPosition[1] - mntGeo[3]) / mntGeo[5])
                Z = mntBand.ReadAsArray(px,py,1,1)[0][0]
                mntDS = None
            else : Z = self.initAltitude
            
            pxL, pyL = self.leftPictureManager.coordToPixel(self.buttonPosition,Z)
            pxR, pyR = self.rightPictureManager.coordToPixel(self.buttonPosition,Z)

            if pxL < 0 or pxL > self.fullLeftPicSize[0] or pyL < 0 or pyL > self.fullLeftPicSize[1] : self.zoomToScale(2,center=True)
            elif pxR < 0 or pxR > self.fullRightPicSize[0] or pyR < 0 or pyR > self.fullRightPicSize[1] : self.zoomToScale(2,center=True)
            else : 
                #pixL = (pxL-self.cropValueLeft[0], pyL)            
                #if self.rightMiroir == 1 :
                #    mirrorX = self.rightPicSize[0] - pxR - 2000
                #    pixR = (mirrorX, pyR)
                #else : pixR = (pxR-self.cropValueRight[0], pyR) 
                zoomX = self.leftPicSize[0] / 8
                zoomY = self.leftPicSize[1] / 8 
                 
                #pixL = (pxL-self.cropValueLeft[0]-1000, pyL-self.cropValueLeft[1]-1000)            
                #if self.rightMiroir == 1 :
                #    mirrorX = self.rightPicSize[0] - pxR - 1000
                #    pixR = (mirrorX, pyR-1000)
                #else : pixR = (pxR-self.cropValueRight[0]-1000, pyR-self.cropValueRight[1]-1000)  
                
                pixL = (pxL-self.cropValueLeft[0]-(zoomX/2), pyL-self.cropValueLeft[1]-(zoomY/2))            
                pixR = (pxR-self.cropValueRight[0]-(zoomX/2), pyR-self.cropValueRight[1]-(zoomY/2))  

                customView = pixL + pixR + (zoomX,zoomY)
                #customView = (pxL,pyL,pxR,pyR) + self.lastCurrentView[-2:]
                self.zoomToScale(-1, customView=customView)

        

        elif self.lastCurrentView : 
            pxL, pyL = self.leftPictureManager.coordToPixel(self.lastCurrentView[:2],self.lastCurrentView[2])
            pxR, pyR = self.rightPictureManager.coordToPixel(self.lastCurrentView[:2],self.lastCurrentView[2])

            if pxL < 0 or pxL > self.fullLeftPicSize[0] or pyL < 0 or pxL > self.fullLeftPicSize[1] : self.zoomToScale(2,center=True)
            elif pxR < 0 or pxR > self.fullRightPicSize[0] or pyR < 0 or pxR > self.fullRightPicSize[1] : self.zoomToScale(2,center=True)
            else : 
                corrX = self.lastCurrentView[-2] /2     
                corrY = self.lastCurrentView[-1] /2     

                pixL = (pxL-self.cropValueLeft[0], pyL-self.cropValueLeft[1])            
                if self.rightMiroir == 1 :
                    mirrorX = self.rightPicSize[0] - pxR 
                    pixR = (mirrorX, pyR)
                else : pixR = (pxR-self.cropValueRight[0], pyR-self.cropValueRight[1])  
                pixLCustom = (pixL[0]-corrX,pixL[1]-corrY)
                pixRCustom = (pixR[0]-corrX,pixR[1]-corrY)
                
                customView = pixLCustom + pixRCustom + self.lastCurrentView[-2:]
                #print(customView)
                #customView = (pxL,pyL,pxR,pyR) + self.lastCurrentView[-2:]
                self.zoomToScale(-1, customView=customView)
        

        else : 
            self.zoomToScale(2,center=True)


    def getSceneFromPath(self, tifPath, miroir, graphWindow, cropValue):

        img = Image.open(tifPath)
        #Seek(3) est le facteur le plus petit qui permet un affichage immédiat d'une image
        img.seek(3)
        divCropValue = tuple(map(lambda val : val/8, cropValue))

        thread = imageEnhancing(img, self.listParam)
        thread.start()
        retVal = thread.join()

        enhancePic = Image.merge("RGB", (retVal[0],retVal[1],retVal[2]))
        QtImg = pictureLayout(enhancePic, 0, miroir, True, divCropValue)

        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)

        obj = scene.addPixmap(QPixmap.fromImage(QtImg))      
        obj.setScale(8)      
        graphWindow.ui.graphicsView.setScene(scene)
        img.close()
        return scene

    def calculDecoupageAvecRotation(self, sizeImg, bboxOverlap, bbox, gpz, R11, R12) :
        threshold = 0.5  
        width, height = sizeImg

        if R11 < -threshold:
            # +180° Rotation : World X → Pixel X (flip), World Y → Pixel Y 
            xStart = int((bbox[4] - bboxOverlap[2]) / gpz)
            yStart = int((bboxOverlap[1] - bbox[3]) / gpz)

            xEnd   = int((bbox[4] - bboxOverlap[0]) / gpz)
            yEnd   = int((bboxOverlap[3] - bbox[3]) / gpz)

        elif abs(R11) < threshold and R12 > threshold:
            # +90° Rotation : World X → Pixel Y,  World Y → Pixel X  (flip)           
            xStart = int((bboxOverlap[1] - bbox[3]) / gpz)
            yStart = int((bbox[4] - bboxOverlap[2]) / gpz)

            xEnd   = int((bboxOverlap[3] - bbox[3]) / gpz)
            yEnd   = int((bbox[4] - bboxOverlap[0]) / gpz)

        elif abs(R11) < threshold and R12 < -threshold:
            # -90° Rotation : World X → Pixel Y (flip), World Y → Pixel X (flip)
           
            xStart = int((bbox[5] - bboxOverlap[3]) / gpz)
            yStart = int((bboxOverlap[0] - bbox[2]) / gpz)

            xEnd   = int((bbox[5] - bboxOverlap[1]) / gpz)
            yEnd   = int((bboxOverlap[2] - bbox[2]) / gpz)

        else : 
            # 0° Rotation : World X → Pixel X,  World Y → Pixel Y (flip)
            xStart = int((bboxOverlap[0] - bbox[2]) / gpz)  
            yStart = int((bbox[5] - bboxOverlap[3]) / gpz)  

            xEnd = int((bboxOverlap[2] - bbox[2]) / gpz) 
            yEnd = int((bbox[5] - bboxOverlap[1]) / gpz) 
        
        xStart = max(0, min(xStart, width))
        xEnd   = max(0, min(xEnd, width))
        yStart = max(0, min(yStart, height))
        yEnd   = max(0, min(yEnd, height))
        
        return (xStart, yStart, xEnd, yEnd)
                
    #Fonction qui récupère la couche vectorielle et change le SIG de QGIS 
    #Si possible appel la fonction pour afficher la couche vectorielle sur les images
    def mNewVectorLayer(self):

        self.enableDraw = True
        self.vectorLayer = self.optWindow.vLayer
        self.vectorLayerName = self.optWindow.vLayerName
        QgsProject.instance().setCrs(self.vectorLayer.crs())

    #Fonction qui détermine la région approximative des photos
    #Retourne le rectangle de coordonnée
    def getShowRect(self) :

        try :
            leftBbox = self.currentParDict[self.leftParID]
            rightBbox = self.currentParDict[self.rightParID]

            _, bboxOverlap = compute_overlap(leftBbox, rightBbox) 

            rectL = QgsRectangle(QgsPointXY(bboxOverlap[0]-700, bboxOverlap[1]-700), QgsPointXY(bboxOverlap[2]+700, bboxOverlap[3]+700))
            

            return rectL
        
        except :
            return QgsRectangle(QgsPointXY(0, 0), QgsPointXY(0, 0))
        
    def removePolygonOnScreen(self) :
        if self.polygonOnLeftScreen and hasattr(self, 'graphWindowLeft'):
            for item in self.polygonOnLeftScreen :
                self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
        self.polygonOnLeftScreen = []

        if self.polygonOnRightScreen and hasattr(self, 'graphWindowRight'):
            for item in self.polygonOnRightScreen :
                self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
        self.polygonOnRightScreen = []

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        

        self.vectorLayer = None 
        self.vectorLayerName = None
        self.enableDraw = False

        self.optWindow.ui.importLineVectorLayer.blockSignals(True)
        self.optWindow.ui.importLineVectorLayer.setText("")
        self.optWindow.ui.importLineVectorLayer.blockSignals(False)



    #Ralentie l'app et fait des crash très fréquent, peut être pas donner l'object au complet...
    def startPolygonThread(self) : 
        if hasattr(self,'tPolygon'): 
            if self.tPolygon.isRunning():
                self.tPolygon.stop()
                self.tPolygon.wait()
        rectCoord = self.getShowRect()
        value = [self.cropValueLeft,self.rightMiroir,self.rightPicSize[0],self.cropValueRight,self.initAltitude]
        lmanag = [self.fullLeftPicSize, self.currentLeftPAR]
        rmanag = [self.fullRightPicSize, self.currentRightPAR]
        mntPath = self.optWindow.currentMNTPath
        vectorToShow = self.optWindow.vectorToShow
        self.tPolygon = calculatePolygon(vectorToShow,rectCoord,lmanag,rmanag,value, mntPath)
        self.tPolygon.finished.connect(self.storePolygon)
        self.tPolygon.start(QThread.LowestPriority)
        
    def storePolygon(self):
        self.polygonL2Draw = self.tPolygon.dictPolyL
        self.polygonR2Draw = self.tPolygon.dictPolyR
        self.drawPolygon()
        
        
    def drawPolygon(self) :   

        if self.polygonOnLeftScreen :
            for item in self.polygonOnLeftScreen :
                try : self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
                except : pass
        self.polygonOnLeftScreen = []

        if self.polygonOnRightScreen :
            for item in self.polygonOnRightScreen :
                try : self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
                except : pass
        self.polygonOnRightScreen = []

        if self.polygonL2Draw : 
            for name, arr in self.polygonL2Draw.items() : 
                geoType = arr[2]
                color = arr[1]
                polyLeft = arr[0]
                polyRight = self.polygonR2Draw[name][0]
                width = self.paramMenu.ui.spinBoxPenWidth.value()

                layerPen = QPen(color, width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
                layerPen.setCosmetic(True)

                for i in range(len(polyLeft)) : 

                    if geoType == QgsWkbTypes.PolygonGeometry : 
                        leftObj = self.graphWindowLeft.ui.graphicsView.scene().addPolygon(polyLeft[i], layerPen)
                        rightObj = self.graphWindowRight.ui.graphicsView.scene().addPolygon(polyRight[i], layerPen)
                    elif geoType == QgsWkbTypes.LineGeometry : 
                        leftObj = self.graphWindowLeft.ui.graphicsView.scene().addPath(polyLeft[i], layerPen)
                        rightObj = self.graphWindowRight.ui.graphicsView.scene().addPath(polyRight[i], layerPen)
                    elif geoType == QgsWkbTypes.PointGeometry : 
                        radius = 9  #rayon pour la taille des points 
                        pointLeft = QGraphicsEllipseItem(polyLeft[i][0] - radius, polyLeft[i][1] - radius, 2*radius, 2*radius)
                        pointLeft.setPen(layerPen)
                        pointLeft.setBrush(color)
                        pointRight = QGraphicsEllipseItem(polyRight[i][0] - radius, polyRight[i][1] - radius, 2*radius, 2*radius)
                        pointRight.setPen(layerPen)
                        pointRight.setBrush(color)
                        leftObj = self.graphWindowLeft.ui.graphicsView.scene().addItem(pointLeft)
                        rightObj = self.graphWindowRight.ui.graphicsView.scene().addItem(pointRight)

                    
                    self.polygonOnLeftScreen.append(leftObj)
                    self.polygonOnRightScreen.append(rightObj)

        if self.greyRectOnLeftScreen : 
            for item in self.greyRectOnLeftScreen :
                try : self.graphWindowLeft.ui.graphicsView.scene().removeItem(item)
                except : pass
        self.greyRectOnLeftScreen = []

        if self.greyRectOnRightScreen :
            for item in self.greyRectOnRightScreen :
                try : self.graphWindowRight.ui.graphicsView.scene().removeItem(item)
                except : pass
        self.greyRectOnRightScreen = []

        dval =15000
        gr1 = QtCore.QRectF(-dval,-dval,dval,(2*dval)+self.leftPicSize[1])
        self.greyRectOnRightScreen.append(self.graphWindowRight.ui.graphicsView.scene().addRect(gr1, QColor(182,182,182),QColor(182,182,182)))
        self.greyRectOnLeftScreen.append(self.graphWindowLeft.ui.graphicsView.scene().addRect(gr1,QColor(182,182,182),QColor(182,182,182)))
        
        gr2 = QtCore.QRectF(self.leftPicSize[0],-dval,dval,(2*dval)+self.leftPicSize[1])
        self.greyRectOnRightScreen.append(self.graphWindowRight.ui.graphicsView.scene().addRect(gr2,QColor(182,182,182),QColor(182,182,182)))
        self.greyRectOnLeftScreen.append(self.graphWindowLeft.ui.graphicsView.scene().addRect(gr2,QColor(182,182,182),QColor(182,182,182)))
        
        gr3= QtCore.QRectF(0,-dval,self.leftPicSize[0],dval)
        self.greyRectOnRightScreen.append(self.graphWindowRight.ui.graphicsView.scene().addRect(gr3,QColor(182,182,182),QColor(182,182,182)))
        self.greyRectOnLeftScreen.append(self.graphWindowLeft.ui.graphicsView.scene().addRect(gr3,QColor(182,182,182),QColor(182,182,182)))
        
        gr4 = QtCore.QRectF(0,self.leftPicSize[1],self.leftPicSize[0],dval)
        self.greyRectOnRightScreen.append(self.graphWindowRight.ui.graphicsView.scene().addRect(gr4,QColor(182,182,182),QColor(182,182,182)))
        self.greyRectOnLeftScreen.append(self.graphWindowLeft.ui.graphicsView.scene().addRect(gr4,QColor(182,182,182),QColor(182,182,182)))
        

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
        self.tSeekLeft = threadShow(self.currentLeftTIF, pointZero, pointMax, multiFactor, seekFactor, scaleFactor, self.listParam, self.leftOrientation, self.leftMiroir, self.cropValueLeft)
        self.tSeekLeft.newImage.connect(self.addLeftPixmap)
        self.tSeekLeft.finished.connect(self.seekLeftDone)
        self.showThreadLeftInProcess = True
        self.newLeftRequest = False
        self.tSeekLeft.start(QThread.IdlePriority)

    #IDEM à threadSeekLeft
    def threadSeekRight(self, pointZero, pointMax, multiFactor, seekFactor, scaleFactor):
        self.tSeekRight = threadShow(self.currentRightTIF, pointZero, pointMax, multiFactor, seekFactor, scaleFactor, self.listParam, self.rightOrientation, self.rightMiroir, self.cropValueRight)
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

        if self.enableDraw and hasattr(self, "initAltitude") and hasattr(self, "graphWindowLeft") and self.polygonL2Draw :
            self.drawPolygon()

        if self.newLeftRequest : 
            pointZero = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowLeft.ui.graphicsView
            pointMax = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekLeft(pointZero, pointMax, 1, 0, 1)

        else :
            self.showThreadLeftInProcess = False

    #IDEM à seekLeftDone
    def seekRightDone(self):

        if self.enableDraw and hasattr(self, "initAltitude") and hasattr(self, "graphWindowRight") and self.polygonR2Draw :
            self.drawPolygon()

        if self.newRightRequest : 
            pointZero = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.graphWindowRight.ui.graphicsView
            pointMax = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            self.threadSeekRight(pointZero, pointMax, 1, 0, 1)

        else :
            self.showThreadRightInProcess = False
       
    
    #Ouverture de la fenêtre de rehaussement
    def enhanceClick(self):
        self.enhanceManager = enhanceManager(self.currentLeftTIF, self.currentRightTIF, self.listParam, self.leftParID, self.rightParID)
        self.enhanceManager.listParamSignal.connect(self.applyEnhance)

    #Permet le lancement du traitement de modification des images
    def applyEnhance(self, listParam):
        self.enhanceManager.listParamSignal.disconnect(self.applyEnhance)
        self.listParam = listParam

    #Fonction non utilisée à reprendre pour la souris qui sort  
    def windowHandlerEvent(self,event) : 
        if event.type() == QtCore.QEvent.Enter : self.windowHandler('picture')
        if event.type() == QtCore.QEvent.Leave : self.windowHandler('qgis')
    
    def windowHandler(self,window) : 
        if window == 'qgis' : 
            self.setLastView()
            #try : self.graphWindowLeft.keyPressed.disconnect(self.keyboardHandler)
            #except : pass
            self.graphWindowLeft.ui.widget.mouseMoveEvent = None
            self.graphWindowLeft.ui.widget.mousePressEvent = None
            self.graphWindowLeft.ui.widget.wheelEvent = None
            self.graphWindowLeft.ui.widget.setMouseTracking(False)
            self.graphWindowLeft.setCursor(self.graphWindowLeft.normalCursor)
            #win32api.SetCursorPos((self.iface.mainWindow().pos().x()+int(iface.mainWindow().width()/2), self.iface.mainWindow().pos().y()+int(iface.mainWindow().height()/2)))
            QCursor.setPos(self.iface.mainWindow().mapToGlobal(self.iface.mainWindow().rect().center()))
            self.iface.mainWindow().activateWindow()
            self.iface.mainWindow().raise_()
            
            #self.graphWindowLeft.leaveEvent = QMainWindow.leaveEvent
            #self.graphWindowLeft.enterEvent = self.windowHandlerEvent #lambda : self.windowHandler('picture')

        if window == 'picture' : 
            #self.graphWindowLeft.keyPressed.connect(self.keyboardHandler)
            
            self.lastX = self.panCenterLeft[0]
            self.lastY = self.panCenterLeft[1] - 22
            #win32api.SetCursorPos(self.leftScreenCenter)
            QCursor.setPos(self.graphWindowLeft.ui.graphicsView.mapToGlobal(self.graphWindowLeft.ui.graphicsView.rect().center()))
            self.graphWindowLeft.ui.widget.setMouseTracking(True)
            if self.graphWindowRight.isMinimized() : self.graphWindowRight.showNormal()
            self.graphWindowRight.raise_()
            self.graphWindowLeft.activateWindow()
            if self.graphWindowLeft.isMinimized() : self.graphWindowLeft.showNormal()
            self.graphWindowLeft.raise_()
            self.graphWindowLeft.ui.widget.mouseMoveEvent = self.mMoveEvent
            self.tick=0
            self.graphWindowLeft.ui.widget.mousePressEvent = self.mPressEvent
            self.graphWindowLeft.ui.widget.wheelEvent = self.wheelEvent
            self.graphWindowLeft.setCursor(self.graphWindowLeft.invisibleCursor)

            #22 est la taille en pixel de la barre du haute de la fenetre
            #Il y a toujours un petit pan lorsqu'on active le Pan sinon 
            

            if self.lastEnhanceParam != self.listParam : 
                self.lastEnhanceParam = self.listParam
                self.loadNewPair(False)
            
            #self.graphWindowLeft.leaveEvent = self.windowHandlerEvent #lambda : self.windowHandler('qgis')
            #self.graphWindowLeft.enterEvent = QMainWindow.enterEvent


    #Fonction appelée lorsque les touches respectives du clavier sont appuyées
    #Les touches sont utiles lorsque le mode pan est en cours d'utilisation
    #Possibilité d'ajouter d'autres fonctions plus tard
    def keyboardHandler(self, event):
        if event.type() == QtCore.QEvent.KeyPress :
            if event.key() == QtCore.Qt.Key_Escape :
                #print('escape')
                self.windowHandler('qgis')
                #self.graphWindowLeft.ui.widget.setMouseTracking(False)
                #win32api.SetCursorPos((self.optWindow.pos().x(), self.optWindow.pos().y()))
                #self.graphWindowLeft.setCursor(self.graphWindowLeft.normalCursor)
                #self.closeAllSideWindows()
                #self.iface.mainWindow().activateWindow() #Combiner avec raise() pour mettre la fenetre on top

            elif event.key() == int(self.paramMenu.currentDictParam['BindZoom']) : self.zoomClick = True
            elif event.key() == int(self.paramMenu.currentDictParam['BindLong']) : self.longClick = True
            elif event.key() == int(self.paramMenu.currentDictParam['BindDraw']) : 
                if self.optWindow.ui.radioButtonDraw.isChecked() : self.optWindow.ui.radioButtonCut.setChecked(True)
                else : self.optWindow.ui.radioButtonDraw.setChecked(True)
            elif event.key() in range(QtCore.Qt.Key_F5, QtCore.Qt.Key_F13) :
                val = event.key() - QtCore.Qt.Key_F5
                self.zoomToScale(val)

        else : 
            self.zoomClick = False
            self.longClick = False
            
    #Fonction qui réalise le pan 
    #Lors du pan la souris est présente sur l'écran qui contient l'image de gauche
    #Cette fonction s'assure que la souris reste sur l'écran conserné pendant le Pan afin de garder le curseur invisible  
    def mMoveEvent(self, ev):

        if self.ignoreMouseAction : 
            self.ignoreMouseAction = False
            return

        self.deltaX = int((ev.x()-self.lastX)/2)
        self.lastX = ev.x()
        self.deltaY = int((ev.y()-self.lastY)/2)
        self.lastY = ev.y()
        leftView = self.graphWindowLeft.ui.graphicsView
        rightView = self.graphWindowRight.ui.graphicsView

        lhv = leftView.horizontalScrollBar().value() + self.deltaX
        lvv = leftView.verticalScrollBar().value() + self.deltaY

        rhv = rightView.horizontalScrollBar().value() + self.deltaX if self.rightMiroir == 0 else rightView.horizontalScrollBar().value() - self.deltaX
        rvv = rightView.verticalScrollBar().value() + self.deltaY


        leftView.horizontalScrollBar().setValue(lhv)
        leftView.verticalScrollBar().setValue(lvv)
        rightView.horizontalScrollBar().setValue(rhv)
        rightView.verticalScrollBar().setValue(rvv)


        pixRange = 200
        cursor_pos = leftView.mapFromGlobal(QCursor.pos())
        centerView = leftView.rect().center()
        if cursor_pos.x() <= pixRange or cursor_pos.x() >= leftView.width()-pixRange or cursor_pos.y() <= pixRange or cursor_pos.y() >= leftView.height()-pixRange:
            #self.graphWindowLeft.ui.widget.setMouseTracking(False)
            self.ignoreMouseAction = True
            #win32api.SetCursorPos(self.leftScreenCenter)
            QCursor.setPos(leftView.mapToGlobal(centerView))
            #last_mouse_pos = leftView.mapToGlobal(leftView.rect().center())
            self.lastX = centerView.x()
            self.lastY = centerView.y()
            #self.graphWindowLeft.ui.widget.setMouseTracking(True)

        pourcent = 2/100
        startX = int(self.leftPicSize[0]*pourcent)
        startY = int(self.leftPicSize[1]*pourcent)
        rangeX = range(startX, int(self.leftPicSize[0]-startX+1))
        rangeY = range(startY, int(self.leftPicSize[1]-startY+1))

        self.endDrawPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(self.panCenterLeft[0], self.panCenterLeft[1]))
        self.endDrawPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))

        coord = self.pointTranslator()

        if self.firstDrawClick and (int(self.endDrawPointLeft.x()) not in rangeX or int(self.endDrawPointLeft.y()) not in rangeY) :
            threshold_deg=10
            kappa = math.degrees(self.leftPictureManager.kappa)
            #Nord à gauche (-90 + 90)
            if (abs(kappa + 90) < threshold_deg):
                if self.endDrawPointLeft.x() < startX and self.currentUpID :
                    self.findNextPair('U')
                elif self.endDrawPointLeft.x() > self.leftPicSize[0]-startX+1 and self.currentDownID :
                    self.findNextPair('D')
                elif self.endDrawPointLeft.y() < startY and self.currentRightID :
                    self.findNextPair('R')
                elif self.endDrawPointLeft.y() > self.leftPicSize[1]-startY+1 and self.currentLeftID :
                    self.findNextPair('L')
            #Nord à droite (90 - 90)
            elif (abs(kappa - 90) < threshold_deg) :
                if self.endDrawPointLeft.x() < startX and self.currentDownID :
                    self.findNextPair('D')
                elif self.endDrawPointLeft.x() > self.leftPicSize[0]-startX+1 and self.currentUpID :
                    self.findNextPair('U')
                elif self.endDrawPointLeft.y() < startY and self.currentLeftID :
                    self.findNextPair('L')
                elif self.endDrawPointLeft.y() > self.leftPicSize[1]-startY+1 and self.currentRightID :
                    self.findNextPair('R')
            #Nord en bas (+/- 180 +/- 180)
            elif abs(kappa - 180) < threshold_deg or abs(kappa + 180) < threshold_deg: 
                if self.endDrawPointLeft.x() < startX and self.currentRightID :
                    self.findNextPair('R')
                elif self.endDrawPointLeft.x() > self.leftPicSize[0]-startX+1 and self.currentLeftID :
                    self.findNextPair('L')
                elif self.endDrawPointLeft.y() < startY and self.currentDownID :
                    self.findNextPair('D')
                elif self.endDrawPointLeft.y() > self.leftPicSize[1]-startY+1 and self.currentUpID :
                    self.findNextPair('U')
            #Nord en haut
            else : 
                if self.endDrawPointLeft.x() < startX and self.currentLeftID :
                    self.findNextPair('L')
                elif self.endDrawPointLeft.x() > self.leftPicSize[0]-startX+1 and self.currentRightID :
                    self.findNextPair('R')
                elif self.endDrawPointLeft.y() < startY and self.currentUpID :
                    self.findNextPair('U')
                elif self.endDrawPointLeft.y() > self.leftPicSize[1]-startY+1 and self.currentDownID :
                    self.findNextPair('D')

        else :
            if  not self.firstDrawClick and self.enableDraw and self.optWindow.currentMNTPath :
                
                lineL = QLineF(self.startDrawPointLeft, self.endDrawPointLeft) 
                lineR = QLineF(self.startDrawPointRight, self.endDrawPointRight)  
                            

                if self.currentLeftLineObj:
                    self.graphWindowLeft.ui.graphicsView.scene().removeItem(self.currentLeftLineObj)
                
                if self.currentRightLineObj:
                    self.graphWindowRight.ui.graphicsView.scene().removeItem(self.currentRightLineObj)
                    
                self.currentLeftLineObj = self.graphWindowLeft.ui.graphicsView.scene().addLine(lineL, self.my_pen)
                self.currentRightLineObj = self.graphWindowRight.ui.graphicsView.scene().addLine(lineR, self.my_pen)
    
            self.tick += 1 
            if self.tick == 5 : 
                self.manageQGISCursor(coord[:2])
                self.tick=0

    def mPressEvent(self, ev):
        if self.optWindow.currentMNTPath and self.enableDraw and self.vectorLayer.geometryType() == QgsWkbTypes.PolygonGeometry :

            #if shape have 2d only2D = True
            coordTuple = self.pointTranslator()
            
            if ev.button() == Qt.LeftButton:
                if self.firstDrawClick :
                    self.startDrawPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(self.panCenterLeft[0], self.panCenterLeft[1]))
                    self.startDrawPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))
                    self.firstDrawClick = False
                else : 
                    self.startDrawPointLeft = self.endDrawPointLeft
                    self.startDrawPointRight = self.endDrawPointRight
                    self.listLeftLineObj.append(self.currentLeftLineObj)
                    self.listRightLineObj.append(self.currentRightLineObj)
                    self.currentLeftLineObj = None
                    self.currentRightLineObj = None
                
                self.listDrawCoord.append(coordTuple)
                self.list2DPoint.append(QgsPoint(coordTuple[0],coordTuple[1]))
                self.list3DPoint.append(QgsPoint(coordTuple[0],coordTuple[1],coordTuple[2]))
                self.listCutCoord.append(QgsPointXY(coordTuple[0],coordTuple[1]))

            elif ev.button() == Qt.RightButton and len(self.listDrawCoord) > 0:

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
                
                if self.optWindow.ui.radioButtonDraw.isChecked(): 
                    firstPoint = self.listDrawCoord[0]
                    self.listDrawCoord.append(firstPoint)
                    
                    lineString2D = QgsLineString(self.list2DPoint)
                    lineString3D = QgsLineString(self.list3DPoint)

                    polyZstr = createWKTString(self.listDrawCoord,'PolygonZ')
                    newGeo = QgsGeometry.fromWkt(polyZstr)
                    currentVectorLayer = self.vectorLayer
                    
                    rectCoord = self.getShowRect()
                    listGeo = list(currentVectorLayer.getFeatures(rectCoord))
                    #reshapeLayer(lineString2D,listGeo,currentVectorLayer)
                    
                    #Détection du feature selon le 
                    #Gestion des plusieurs intersections à faire
                    for item in listGeo : 
                        featureGeo = item.geometry()
                        
                        if newGeo.intersects(featureGeo) :
                            if self.paramMenu.ui.radioButtonMerge.isChecked() :
                                mergePolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
                            else :
                                automaticPolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
                            break
                            
                    else :
                        addPolygon(currentVectorLayer, newGeo)
                else :
                    currentVectorLayer = self.vectorLayer    
                    cutPolygon(currentVectorLayer, self.listCutCoord)
                
                self.listDrawCoord = []
                self.listCutCoord = []
                
                self.list2DPoint = []
                self.list3DPoint = []
                self.startPolygonThread()    
                
                
                    
        elif self.enableDraw and self.vectorLayer.geometryType() == QgsWkbTypes.PointGeometry and ev.button() == Qt.LeftButton :
            coordTuple = self.pointTranslator() 
            if QgsWkbTypes.hasZ(self.vectorLayer.wkbType()) : geo = QgsGeometry(QgsPoint(coordTuple[0],coordTuple[1],coordTuple[2]))
            else : geo = QgsGeometry.fromPointXY(QgsPointXY(coordTuple[0],coordTuple[1]))
            
            self.windowHandler('qgis')
            feature = addPoint(self.vectorLayer, geo)
            
            #self.vectorLayer.select(feature.id())
            self.vectorLayer.startEditing()
            resultForm = self.iface.openFeatureForm(self.vectorLayer, feature)
            if resultForm == False : 
                provider =  self.vectorLayer.dataProvider()
                provider.deleteFeatures([feature.id()]) 
            self.vectorLayer.commitChanges()
            self.vectorLayer.triggerRepaint()
            self.windowHandler('picture')
            
            self.startPolygonThread()    

    
    #Fonction activer par la roulette de la souris
    #Avec la touche CTRL, il est possible de zoom In/Out sur les photos 
    #Sinon il est possible de déplacer l'image de droite et d'actualiser la valeur Z du centre 
    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        leftView = self.graphWindowLeft.ui.graphicsView
        rightView = self.graphWindowRight.ui.graphicsView
        
        if self.zoomClick  :    
            if factor > 1 : 
                leftView.scale(1.25, 1.25)
                rightView.scale(1.25, 1.25)
            else :
                leftView.scale(0.8, 0.8)
                rightView.scale(0.8, 0.8)
            self.setQGISView()

        elif self.longClick :
            if factor > 1 : 
                rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() - 3)
            else :
                rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() + 3)

        else : 

            if factor < 1 : 
                leftView.verticalScrollBar().setValue(leftView.verticalScrollBar().value() - 1)
                rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() - 1)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() - 1)
                
            else :
                leftView.verticalScrollBar().setValue(leftView.verticalScrollBar().value() + 1)
                rightView.verticalScrollBar().setValue(rightView.verticalScrollBar().value() + 1)
                rightView.horizontalScrollBar().setValue(rightView.horizontalScrollBar().value() + 1)

            self.pointTranslator(ignoreMNT=True)

    def pointTranslator(self, customPoint=(-1,-1,-1,-1), onlyPixel=False, only2D=False,ignoreMNT=False) :
        
        if customPoint != (-1,-1,-1,-1) :
            #pointRight doit être l'inverse en X si mirroir puisque le pixel de l'écran est inverse
            pointLeft = QPoint(customPoint[0], customPoint[1])
            pointRight = QPoint(customPoint[2], customPoint[3])
        else : 
            pointLeft = QPoint(self.panCenterLeft[0], self.panCenterLeft[1])
            pointRight = QPoint(self.panCenterRight[0], self.panCenterRight[1])
        
        centerPointLeft = self.graphWindowLeft.ui.graphicsView.mapToScene(pointLeft)
        centerPointRight = self.graphWindowRight.ui.graphicsView.mapToScene(pointRight)

        pixL = (centerPointLeft.x()+self.cropValueLeft[0], centerPointLeft.y()+self.cropValueLeft[1])            
        
        if self.rightMiroir == 1 :
            mirrorX = self.rightPicSize[0] - centerPointRight.x()
            pixR = (mirrorX, centerPointRight.y())
        else : pixR = (centerPointRight.x()+self.cropValueRight[0], centerPointRight.y()+self.cropValueRight[1])  

        if onlyPixel : return (pixL,pixR)
        Z = self.dualManager.calculateZ(pixL, pixR)
        self.optWindow.ui.labelAltitude.setText(str(round(Z,5)))

        X, Y = self.leftPictureManager.pixelToCoord(pixL, Z)
        if not self.optWindow.currentMNTPath or ignoreMNT: 
            if only2D == True : return (X, Y)
            else : return (X,Y,Z)

        mntDS = gdal.Open(self.optWindow.currentMNTPath)
        mntBand = mntDS.GetRasterBand(1)
        mntNoData = mntBand.GetNoDataValue()
        mntGeo = mntDS.GetGeoTransform()
        px = math.floor((X - mntGeo[0]) / mntGeo[1]) 
        py = math.floor((Y - mntGeo[3]) / mntGeo[5])

        #comparer mnt vs alt via photogram -> intéressant d'avoir la précision
        try : mntAlt = mntBand.ReadAsArray(px,py,1,1)[0][0]
        except : 
            if only2D : return (X, Y)
            else : return (X, Y, Z)
        
        if mntAlt == mntNoData : 
            if only2D : return (X, Y)
            else : return (X, Y, Z)
            

        '''XL, YL = self.leftPictureManager.pixelToCoord(pixL, mntAlt)
        XR, YR = self.rightPictureManager.pixelToCoord(pixR, mntAlt)

        mntLong = (XL + XR) / 2
        mntLat = (YL + YR) / 2'''

        mntLong, mntLat = self.leftPictureManager.pixelToCoord(pixL, mntAlt)
        
        addedAlt = self.paramMenu.ui.spinBoxAltitude.value()
        if addedAlt > 0 :
            mntAlt += addedAlt

        if only2D : return (mntLong,mntLat)
        else : return (mntLong,mntLat,mntAlt)


    def zoomToScale(self,value,center=False,customView=None) :
        
        if value == -1 and customView : 
            rect= QtCore.QRectF(customView[0],customView[1],customView[-2],customView[-1])
            self.graphWindowLeft.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            rect= QtCore.QRectF(customView[2],customView[3],customView[-2],customView[-1])
            self.graphWindowRight.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            #self.setQGISView()
            #return

            #sizeRef = [500,1000,2000,3000,4000,5000,7000,9000]
            #ratio = sizeRef[value]
        
        elif center : 
            midX = (self.leftPictureManager.X0 + self.rightPictureManager.X0) / 2
            midY = (self.leftPictureManager.Y0 + self.rightPictureManager.Y0) / 2
            if self.optWindow.currentMNTPath : 
                mntDS = gdal.Open(self.optWindow.currentMNTPath)
                mntBand = mntDS.GetRasterBand(1)
                mntGeo = mntDS.GetGeoTransform()
                px = math.floor((midX - mntGeo[0]) / mntGeo[1]) 
                py = math.floor((midY - mntGeo[3]) / mntGeo[5])
                Z = mntBand.ReadAsArray(px,py,1,1)[0][0]
                mntDS = None
            else : 
                #Autre méthode pour estimer l'altitude? Avec le dual manager? 
                #Rajouter une option dans le menu des paramètres? -> Altitude moyenne du vol 
                Z = 300
            
            pxL, pyL = self.leftPictureManager.coordToPixel((midX,midY),Z)
            pxR, pyR = self.rightPictureManager.coordToPixel((midX,midY),Z)

            zoomX = self.leftPicSize[0] / 8
            zoomY = self.leftPicSize[1] / 8 
                 
    
            pixL = (pxL-self.cropValueLeft[0]-(zoomX/2), pyL-self.cropValueLeft[1]-(zoomY/2))            
            pixR = (pxR-self.cropValueRight[0]-(zoomX/2), pyR-self.cropValueRight[1]-(zoomY/2))  

            #customView = pixL + pixR + (zoomX,zoomY)
            rect= QtCore.QRectF(pixL[0],pixL[1],zoomX,zoomY)
            self.graphWindowLeft.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            rect= QtCore.QRectF(pixR[0],pixR[1],zoomX,zoomY)
            self.graphWindowRight.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)


            #xSizeL = self.leftPicSize[0]/2
            #ySizeL = self.leftPicSize[1]/2 
            #xSizeR = self.rightPicSize[0]/2
            #ySizeR = self.rightPicSize[1]/2
        
        else : 
            zoomLevels = [128, 64, 32, 16, 8, 4, 2, 1]  # 8 zoom levels
            scaleFactor = zoomLevels[value]

            point = self.graphWindowLeft.ui.graphicsView.mapToScene(QPoint(self.panCenterLeft[0], self.panCenterLeft[1]))
            xSizeL = point.x()
            ySizeL = point.y()
            point = self.graphWindowRight.ui.graphicsView.mapToScene(QPoint(self.panCenterRight[0], self.panCenterRight[1]))
            xSizeR = point.x()
            ySizeR = point.y()

            rectWidthL  = self.leftPicSize[0] / scaleFactor
            rectHeightL = self.leftPicSize[1] / scaleFactor

            rectWidthR  = self.rightPicSize[0] / scaleFactor
            rectHeightR = self.rightPicSize[1] / scaleFactor
            
            rect= QtCore.QRectF(xSizeL-(rectWidthL/2),ySizeL-(rectHeightL/2),rectWidthL,rectHeightL)
            self.graphWindowLeft.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)
            rect= QtCore.QRectF(xSizeR-(rectWidthR/2),ySizeR-(rectHeightR/2),rectWidthR,rectHeightR)
            self.graphWindowRight.ui.graphicsView.fitInView(rect, QtCore.Qt.KeepAspectRatio)

        self.setQGISView()
    
    def setQGISView(self): 

        coord = self.pointTranslator(ignoreMNT=True,only2D=True)
        self.canvas.setCenter(QgsPointXY(coord[0],coord[1]))
        
        gv = self.graphWindowLeft.ui.graphicsView
        startPoint = gv.mapToScene(QPoint(0, 0))
        endPoint = gv.mapToScene(QPoint(gv.width(),gv.height()))
        if endPoint.y()-startPoint.y() > self.leftPicSize[1] : 
            val = self.leftPicSize[1]
        else : val = endPoint.y()-startPoint.y() 
        self.canvas.zoomScale(val)
        
        self.canvas.refresh()
        self.currentQGISRect = self.canvas.extent()
    
    def manageQGISCursor(self,newCoord,onlyDelete=False):
        point = QgsPointXY(newCoord[0],newCoord[1])
        if hasattr(self, 'mapCursor') : 
            try :self.canvas.scene().removeItem(self.mapCursor)
            except : pass
        if onlyDelete : return

        if not self.currentQGISRect.contains(point) : self.setQGISView()

        self.mapCursor = QgsVertexMarker(self.canvas)
        self.mapCursor.setCenter(point)
        self.mapCursor.setColor(QColor(255, 0, 0))
        self.mapCursor.setIconSize(14)
        self.mapCursor.setIconType(QgsVertexMarker.ICON_CROSS)
        self.mapCursor.setPenWidth(8)


