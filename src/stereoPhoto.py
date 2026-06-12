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

import numpy as np
from . import resources

from .ui_graphicsWindow import graphicsWindow
from .ui_getVectorLayer import getImageListDialog
from .worldManager import pictureManager, dualManager, createWKTString
from .enhanceManager import enhanceManager, threadShow
from .drawFunction import *
from .navigationQgsMapTool import navigationMapTool
from .ui_widgetStereoPhoto import optionWindow

from .gestionDossier import getParDict, get_neighbors_and_pairs, findPairWithCoord, compute_overlap
import sys, os, time, math, gc
from osgeo import gdal


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

            self.optWindow = optionWindow(self.iface)
            self.navigMapTool= navigationMapTool(self.canvas,self.iface)
            
            self.setConnection() 
            self.optWindow.loadParamFile()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.optWindow)
            self.optWindow.raise_()

        else :
            self.iface.removeDockWidget(self.optWindow)
            self.optWindowClose()
            del self.optWindow
            try : del self.currentParDict
            except: pass

    def initGlobalParam(self):
        
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

        self.tSeekLeft = None
        self.tSeekRight = None

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        
        self.buttonPosition = None
        self.buttonMapUnit  = None

        self.cursorAltitude = None
        self.isLoadingPair = False
    
    def setConnection(self) : 

        self.optWindow.ui.importLineProject.textChanged.connect(self.newPictureFile)
        self.optWindow.ui.importLineVectorLayer.textChanged.connect(self.mNewVectorLayer)
        self.optWindow.ui.pushButtonShowPicture.clicked.connect(self.createGraphicsWindows)
        self.optWindow.ui.pushButtonShowIDList.clicked.connect(self.showIDList)
        self.optWindow.ui.enhanceButton.clicked.connect(self.enhanceClick)
        self.optWindow.ui.pushButtonFindBestPair.clicked.connect(self.findPairWithPosition)
        self.optWindow.closeWindow.connect(self.optWindowClose)
        self.optWindow.ui.pushButtonCloseWindow.clicked.connect(self.closeAllSideWindows)

        self.navigMapTool.mouseClicked.connect(self.mousePressEvent)
        self.navigMapTool.wheelActivate.connect(self.wheelActionEvent)
        self.navigMapTool.mouseMoved.connect(self.mouseMoveEvent)
        self.navigMapTool.keybordSignal.connect(self.keyboardHandler)

    #Fonction appelée lors de la fermeture du mOpt
    #Si l'on ferme le mOpt toutes les autres fenêtres Qt se ferment
    def closeAllSideWindows(self) :
        self.enableShow = False
        self.canvas.unsetMapTool(self.navigMapTool)
        self.removeCurrentScene()
        self.deleteOldPolygon()
        if hasattr(self, "graphWindowLeft"):
            self.graphWindowLeft.close()
            del self.graphWindowLeft
        if hasattr(self, "graphWindowRight"):
            self.graphWindowRight.close()
            del self.graphWindowRight
        if hasattr(self, "enhanceManager"):
            self.enhanceManager.cancelEnhance()
            del self.enhanceManager 
        self.optWindow.ui.pushButtonCloseWindow.setEnabled(False)
        self.optWindow.saveParamFile()
    
    def optWindowClose(self):
        self.closeAllSideWindows()
        self.optWindow.close()
        self.optWindow.vectorWindow.close()
        if self.action.isChecked() : self.action.setChecked(False)

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
        
        userImage = self.optWindow.ParamDict['info_raster']['user_image']
        lastPosition = self.optWindow.ParamDict['position']
        if userImage in self.currentParDict.keys() : 
            parToUse = userImage
            if float(lastPosition['longitude']) != 0.0 :
                x = float(lastPosition['longitude'])
                y = float(lastPosition['latitude'])
                z = float(lastPosition['altitude'])
                scale = float(lastPosition['scale'])
                self.lastCurrentView = (x,y,z,scale)
            else : self.lastCurrentView = ()
        
        else : 
            self.lastCurrentView = ()
            #self.optWindow.removeImportMNT()
            self.removePolygonOnScreen()
            parToUse = next(iter(self.currentParDict))
            

        if self.enableShow : self.closeAllSideWindows()
        self.setPairWithPARId(parToUse)

    def showIDList(self) : 
        self.pictureSelectWindow = getImageListDialog(sorted(self.currentParDict),self.leftParID)
        self.pictureSelectWindow.ui.buttonBox.accepted.connect(self.pictureSelectionAccept)
        self.pictureSelectWindow.ui.buttonBox.rejected.connect(lambda : self.pictureSelectWindow.close())
        self.pictureSelectWindow.show()
    
    def pictureSelectionAccept(self):
        pictureID = self.pictureSelectWindow.ui.listWidget.selectedItems()[0].text()
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
            self.leftParID = ''
            return
        
        elif self.infoNeighbors['rightPic'][0] is None : 
            self.leftParID = self.infoNeighbors['leftPic'][0]
            self.rightParID = parID
                        
        else : 
            self.leftParID = parID
            self.rightParID = self.infoNeighbors['rightPic'][0]

        self.optWindow.ui.labelLeftName.setText(self.leftParID)
        self.optWindow.ui.labelRightName.setText(self.rightParID)

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

        
    def setLastView(self) :
        if not hasattr(self, "graphWindowLeft"): return

        LGV = self.graphWindowLeft.ui.graphicsView
        sceneRect = LGV.mapToScene(LGV.viewport().rect()).boundingRect()  
        sceneCenter = sceneRect.center()
        centerPixel = self.graphWindowLeft.imageRoot.mapFromScene(sceneCenter)

        currentTransform = LGV.transform()  

        scaleStore = currentTransform.m11() #self.currentScale

        cx, cy = self.leftPictureManager.pixelToCoord((centerPixel.x(), centerPixel.y()), self.cursorAltitude)
        self.lastCurrentView = (cx,cy,self.cursorAltitude,scaleStore)

        self.optWindow.ParamDict['position']['longitude'] = cx
        self.optWindow.ParamDict['position']['latitude'] = cy
        self.optWindow.ParamDict['position']['altitude'] = self.cursorAltitude
        self.optWindow.ParamDict['position']['scale'] = scaleStore

    
    def findNextPair(self, ori):
        self.navigMapTool.deactivateMapTool() 
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
        
        self.setPairWithPARId(newID,secondID)
        
        self.loadNewPair(ignoreMapTool=True)

    def findPairWithPosition(self) :

        qgisExtent = self.canvas.extent()
        centerCoord = (qgisExtent.xMinimum()+qgisExtent.width()/2,qgisExtent.yMinimum()+qgisExtent.height()/2)
        bestFit = findPairWithCoord(self.currentParDict,centerCoord)

        width = qgisExtent.width()
        height = qgisExtent.height()
        imageID = bestFit[0] 
        distance = bestFit[1]

        #Zone de 7.5 km pour être proche de la photo le plus possible
        if max(width,height,distance) < 7500 : 
            self.buttonPosition = centerCoord
            self.buttonMapUnit = self.canvas.mapUnitsPerPixel()
            self.setPairWithPARId(imageID)
            if self.enableShow and self.leftParID != '' : self.loadNewPair()
        else : self.buttonPosition = None

    
    def createGraphicsWindows(self) : 

        if self.enableShow : 
            self.setExtent2Canvas()
            self.windowHandler('picture')
            if self.enableDraw : 
                self.startPolygonThread()
                if self.optWindow.currentMNTPath and self.vectorLayer.geometryType() == QgsWkbTypes.PolygonGeometry :self.navigMapTool.activateDrawing = True
                else : self.navigMapTool.activateDrawing = False
            return

        intDownScreen = self.optWindow.ui.spinBoxDownScreen.value()
        intUpSreen = self.optWindow.ui.spinBoxUpScreen.value()
        
        screenLeft = QGuiApplication.screens()[intDownScreen]
        screenRight = QGuiApplication.screens()[intUpSreen]

        screenLeft_geom = screenLeft.geometry()
        screenRight_geom = screenRight.geometry()

        self.graphWindowLeft = graphicsWindow()
        self.graphWindowLeft.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.graphWindowLeft.move(screenLeft_geom.topLeft())
        self.graphWindowLeft.keyPressed.connect(self.keyboardHandler)

        self.graphWindowRight = graphicsWindow()
        self.graphWindowRight.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.graphWindowRight.move(screenRight_geom.topLeft())
        self.graphWindowRight.keyPressed.connect(self.keyboardHandler)
        
        width = 4
        color = QColor('Cyan')

        self.my_pen = QPen(color, width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
        self.my_pen.setCosmetic(True)

        self.enableShow = True
        self.optWindow.ui.pushButtonCloseWindow.setEnabled(True)

        self.graphWindowRight.showFullScreen()
        self.graphWindowLeft.showFullScreen()
        self.iface.mainWindow().raise_()       
        self.iface.mainWindow().activateWindow()
        self.canvas.setFocus()
        self.loadNewPair()

    def removeCurrentScene(self) : 

        if self.tSeekLeft is not None : 
            if self.tSeekLeft.showThreadInProcess : 
                self.tSeekLeft.blockSignals(True)
                self.tSeekLeft.keepRunning = False
                self.tSeekLeft.wait()
            self.tSeekLeft = None

        if hasattr(self, "graphWindowLeft"):
            self.graphWindowLeft.resetTileGroup()
        
        if self.tSeekRight is not None : 
            if self.tSeekRight.showThreadInProcess : 
                self.tSeekRight.blockSignals(True)
                self.tSeekRight.keepRunning = False
                self.tSeekRight.wait()
            self.tSeekRight = None

        if hasattr(self, "graphWindowRight"):
            self.graphWindowRight.resetTileGroup()
        
        QApplication.processEvents()
        
    def loadNewPair(self,ignoreMapTool=False):
        self.removeCurrentScene()

        self.graphWindowLeft.ui.graphicsView.resetTransform()
        self.graphWindowRight.ui.graphicsView.resetTransform()
       
        self.tSeekLeft = threadShow(self.currentLeftTIF, self.optWindow.rehaussementParam)
        self.tSeekLeft.newImage.connect(self.graphWindowLeft.addPixmap)
        self.tSeekLeft.finished.connect(self.seekLeftDone)
        
        self.tSeekRight = threadShow(self.currentRightTIF, self.optWindow.rehaussementParam)
        self.tSeekRight.newImage.connect(self.graphWindowRight.addPixmap)
        self.tSeekRight.finished.connect(self.seekRightDone)
        
        self.fullLeftPicSize = (self.tSeekLeft.width, self.tSeekLeft.height)
        self.fullRightPicSize = (self.tSeekRight.width, self.tSeekRight.height)
       
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

        cropValueLeft = self.calculDecoupageAvecRotation(self.fullLeftPicSize,bboxOverlap,leftBbox,gpzL,r11L,r12L)
        cropValueRight = self.calculDecoupageAvecRotation(self.fullRightPicSize,bboxOverlap,rightBbox,gpzR,r11R,r12R)
        
        self.leftPicSize = (cropValueLeft[2]-cropValueLeft[0],cropValueLeft[3]-cropValueLeft[1])
        self.rightPicSize = (cropValueRight[2]-cropValueRight[0],cropValueRight[3]-cropValueRight[1])


        self.dualManager = dualManager(self.leftPictureManager, self.rightPictureManager)

        self.tSeekLeft.cropValue = cropValueLeft
        self.tSeekRight.cropValue = cropValueRight
        
        self.realCropValueLeft = cropValueLeft
        self.realCropValueRight = cropValueRight
        
        #self.openMNT()
        coordRect = self.getShowRect()
        self.optWindow.getMNTWithCoord(coordRect)

        self.setInitialCursorAltitude()
        self.setBaseTransform()
        self.setStartingView()
        self.setExtent2Canvas()
        
        if ignoreMapTool : self.navigMapTool.activateMapTool() 
        else : self.windowHandler('picture')
        
        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        self.firstDrawClick = True

        LGV = self.graphWindowLeft.ui.graphicsView
        vpl = LGV.viewport()
        sceneRectL = LGV.mapToScene(vpl.rect()).boundingRect()
        realLeftRect = self.graphWindowLeft.imageRoot.mapFromScene(sceneRectL).boundingRect()
        self.tSeekLeft.set_SceneRect(realLeftRect)
        self.tSeekLeft.start(QThread.LowestPriority)
        
        RGV = self.graphWindowRight.ui.graphicsView
        vpr = RGV.viewport()
        sceneRectR = RGV.mapToScene(vpr.rect()).boundingRect()
        realRigthRect = self.graphWindowRight.imageRoot.mapFromScene(sceneRectR).boundingRect()

        self.tSeekRight.set_SceneRect(realRigthRect)
        self.tSeekRight.start(QThread.LowestPriority)
        
        if self.enableDraw : 
            self.startPolygonThread()
            if self.optWindow.currentMNTPath and self.vectorLayer.geometryType() == QgsWkbTypes.PolygonGeometry :self.navigMapTool.activateDrawing = True
            else : self.navigMapTool.activateDrawing = False
        
        self.isLoadingPair = False

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
    
  
    def calculDecoupageAvecRotation(self, sizeImg, bboxOverlap, bbox, gpz, R11, R12) :
        threshold = 0.5  
        width, height = sizeImg
        if gpz <= 0:
            # Use a fallback or log an error
            return (0, 0, width, height) 

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
        self.deleteOldPolygon()

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        

        self.vectorLayer = None 
        self.vectorLayerName = None
        self.enableDraw = False

        self.optWindow.ui.importLineVectorLayer.blockSignals(True)
        self.optWindow.ui.importLineVectorLayer.setText("")
        self.optWindow.ui.importLineVectorLayer.blockSignals(False)

    def startPolygonThread(self) : 
        if hasattr(self,'tPolygon'): 
            if self.tPolygon.isRunning():
                self.tPolygon.stop()
                self.tPolygon.wait()
            del self.tPolygon
        rectCoord = self.getShowRect()
        lmanag = [self.fullLeftPicSize, self.currentLeftPAR]
        rmanag = [self.fullRightPicSize, self.currentRightPAR]
        mntPath = self.optWindow.currentMNTPath
        vectorToShow = self.optWindow.vectorToShow
        self.tPolygon = calculatePolygon(vectorToShow,rectCoord,lmanag,rmanag, self.cursorAltitude, mntPath)
        self.tPolygon.finished.connect(self.storePolygon)
        self.tPolygon.start(QThread.LowestPriority)
        
    def storePolygon(self):
        self.polygonL2Draw = self.tPolygon.dictPolyL
        self.polygonR2Draw = self.tPolygon.dictPolyR
        self.drawPolygon()
        
        
    def deleteOldPolygon(self) :   

        if hasattr(self,'graphWindowLeft'):
            for item in self.graphWindowLeft.geometryItemGroup.childItems():
                self.graphWindowLeft.scene.removeItem(item)
                
        if hasattr(self,'graphWindowRight'):
            for item in self.graphWindowRight.geometryItemGroup.childItems():
                self.graphWindowRight.scene.removeItem(item)
        
    def drawPolygon(self) :   
        self.deleteOldPolygon()
        if self.polygonL2Draw : 
            
            for name, arr in self.polygonL2Draw.items() : 
                geoType = arr[2]
                color = arr[1]
                polyLeft = arr[0]
                polyRight = self.polygonR2Draw[name][0]
                width = 4

                layerPen = QPen(color, width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
                layerPen.setCosmetic(True)

                for i in range(len(polyLeft)) : 

                    if geoType == QgsWkbTypes.PolygonGeometry : 
                        leftObj = QGraphicsPolygonItem(polyLeft[i],self.graphWindowLeft.imageRoot)
                        rightObj = QGraphicsPolygonItem(polyRight[i],self.graphWindowRight.imageRoot)

                    elif geoType == QgsWkbTypes.LineGeometry : 
                        leftObj = QGraphicsPathItem(polyLeft[i],self.graphWindowLeft.imageRoot)
                        rightObj = QGraphicsPathItem(polyRight[i],self.graphWindowRight.imageRoot)

                    elif geoType == QgsWkbTypes.PointGeometry : 
                        radius = 9  #rayon pour la taille des points 
                        
                        leftObj = QGraphicsEllipseItem(polyLeft[i][0] - radius, polyLeft[i][1] - radius, 2*radius, 2*radius,self.graphWindowLeft.imageRoot)
                        leftObj.setBrush(color)
                        
                        rightObj = QGraphicsEllipseItem(polyRight[i][0] - radius, polyRight[i][1] - radius, 2*radius, 2*radius,self.graphWindowRight.imageRoot)
                        rightObj.setBrush(color)
                    
                    leftObj.setPen(layerPen)
                    rightObj.setPen(layerPen)
                    self.graphWindowLeft.geometryItemGroup.addToGroup(leftObj)
                    self.graphWindowRight.geometryItemGroup.addToGroup(rightObj)
        
        self.hideOffBoundDrawing()

    def hideOffBoundDrawing(self) : 

        color = QColor(182, 182, 182)

        if hasattr(self.graphWindowLeft, 'offboundRectGroup'):
            for item in self.graphWindowLeft.offboundRectGroup.childItems():
                self.graphWindowLeft.scene.removeItem(item)
                
        if hasattr(self.graphWindowRight, 'offboundRectGroup'):
            for item in self.graphWindowRight.offboundRectGroup.childItems():
                self.graphWindowRight.scene.removeItem(item)

        # Offsets in the scene
        offLX, offLY = self.realCropValueLeft[0],  self.realCropValueLeft[1]     
        offRX, offRY = self.realCropValueRight[0], self.realCropValueRight[1]   

        dval = 15000

        # For LEFT screen 
        x0 = offLX
        y0 = offLY
        x1 = offLX + self.leftPicSize[0]
        y1 = offLY + self.leftPicSize[1]

        # Left side
        gr1L = QtCore.QRectF(x0 - dval, y0 - dval, dval, (y1 - y0) + 2*dval)
        rectObj = QGraphicsRectItem(gr1L,self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # Right side
        gr2L = QtCore.QRectF(x1, y0 - dval, dval, (y1 - y0) + 2*dval)
        rectObj = QGraphicsRectItem(gr2L,self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)
        

        # Top
        gr3L = QtCore.QRectF(x0, y0 - dval, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr3L,self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)
        

        # Bottom
        gr4L = QtCore.QRectF(x0, y1, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr4L,self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # For RIGHT screen 
        x0 = offRX
        y0 = offRY
        x1 = offRX + self.rightPicSize[0]
        y1 = offRY + self.rightPicSize[1]

        # Left side
        gr1R = QtCore.QRectF(x0 - dval, y0 - dval, dval, (y1 - y0) + 2*dval)
        rectObj = QGraphicsRectItem(gr1R,self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

        # Right side
        gr2R = QtCore.QRectF(x1, y0 - dval, dval, (y1 - y0) + 2*dval)
        rectObj = QGraphicsRectItem(gr2R,self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

        # Top
        gr3R = QtCore.QRectF(x0, y0 - dval, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr3R,self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)


        # Bottom
        gr4R = QtCore.QRectF(x0, y1, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr4R,self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)


    def seekLeftDone(self) : 
        if self.enableDraw and self.enableShow :
            self.drawPolygon()
        if hasattr(self, "tSeekLeft"):  self.tSeekLeft.showThreadInProcess = False 
    
    def seekRightDone(self) : 
        if self.enableDraw and self.enableShow :
            self.drawPolygon()
        if hasattr(self, "tSeekRight"):  self.tSeekRight.showThreadInProcess = False
    
    #Ouverture de la fenêtre de rehaussement
    def enhanceClick(self):
        self.enhanceManager = enhanceManager(self.currentLeftTIF, self.currentRightTIF, self.optWindow.rehaussementParam, self.leftParID, self.rightParID)
        self.enhanceManager.listParamSignal.connect(self.applyEnhance)

    #Permet le lancement du traitement de modification des images
    def applyEnhance(self, listParam):
        self.enhanceManager.listParamSignal.disconnect(self.applyEnhance)
        self.optWindow.rehaussementParam = listParam

    
    def windowHandler(self,window) : 
        if window == 'qgis' : 
            self.iface.mainWindow().raise_()       
            self.iface.mainWindow().activateWindow()
            self.canvas.unsetMapTool(self.navigMapTool)

            self.setLastView()

        if window == 'picture' : 
            self.graphWindowRight.raise_()
            self.graphWindowRight.activateWindow()
            self.graphWindowLeft.raise_()
            self.graphWindowLeft.activateWindow()
            self.iface.mainWindow().raise_()       
            self.iface.mainWindow().activateWindow()
            self.canvas.setMapTool(self.navigMapTool)
            self.canvas.setFocus()
   
            
    #Fonction appelée lorsque les touches respectives du clavier sont appuyées
    #Les touches sont utiles lorsque le mode pan est en cours d'utilisation
    #Possibilité d'ajouter d'autres fonctions plus tard
    def keyboardHandler(self, event):
        if event.type() == QtCore.QEvent.KeyPress :
            if event.key() == QtCore.Qt.Key_Escape :
                
                self.windowHandler('qgis')
            
            elif event.key() in range(QtCore.Qt.Key_F5, QtCore.Qt.Key_F13) :
                val = event.key() - QtCore.Qt.Key_F5
                self.keyboardZoom(val)

            elif event.key() == QtCore.Qt.Key_1 : 
                if self.optWindow.ui.radioButtonDraw.isChecked() : self.optWindow.ui.radioButtonCut.setChecked(True)
                else : self.optWindow.ui.radioButtonDraw.setChecked(True)
            

        event.accept()
            
    def setInitialCursorAltitude(self) :


        midLPix = ((self.realCropValueLeft[0] + self.realCropValueLeft[2]) / 2,(self.realCropValueLeft[1] + self.realCropValueLeft[3]) / 2)
        midRPix = ((self.realCropValueRight[0] + self.realCropValueRight[2]) / 2,(self.realCropValueRight[1] + self.realCropValueRight[3]) / 2)

        Z = self.dualManager.calculateZ(midLPix, midRPix)
        self.cursorAltitude = Z

        if self.buttonPosition : 
            altitude = self.optWindow.readMNTWithCoord(self.buttonPosition)
            if altitude is not None : self.cursorAltitude = altitude

        elif self.lastCurrentView : 
            self.cursorAltitude = self.lastCurrentView[2]

        elif self.optWindow.mntArr is not None :
            middleCoordLeft = self.leftPictureManager.pixelToCoord(midLPix,self.cursorAltitude)
            altitude = self.optWindow.readMNTWithCoord(middleCoordLeft)
            if altitude is not None : self.cursorAltitude = altitude

        self.optWindow.ui.labelAltitude.setText(f"{self.cursorAltitude:.3f}")

    
    def openMNT(self) : pass
        #if not self.optWindow.currentMNTPath : 
        #    self.mntDS = None
        #    return#

        #self.mntDS = gdal.Open(self.optWindow.currentMNTPath,gdal.GA_ReadOnly)
        #self.mntBand = self.mntDS.GetRasterBand(1)
        #self.mntGeo = self.mntDS.GetGeoTransform()
        #self.mntNoData = self.mntBand.GetNoDataValue()
        #self.mntXSize = self.mntDS.RasterXSize
        #self.mntYSize = self.mntDS.RasterYSize


    def readMNTWithCoordinate(self,coordinates) : pass
        #if self.mntDS is None : return None
        
        #px = math.floor((coordinates[0] - self.mntGeo[0]) / self.mntGeo[1]) 
        #py = math.floor((coordinates[1] - self.mntGeo[3]) / self.mntGeo[5])
        #if px < 0 or py < 0 or px >= self.mntXSize or py >= self.mntYSize: return None

        #try : Z = self.mntBand.ReadAsArray(px,py,1,1)[0][0]
        #except : return None 
        #if Z == self.mntNoData : return None
        #return Z

    def setStartingView(self) : 

        if self.buttonPosition : 
            
            pxL, pyL = self.leftPictureManager.coordToPixel(self.buttonPosition,self.cursorAltitude)
            pxR, pyR = self.rightPictureManager.coordToPixel(self.buttonPosition,self.cursorAltitude)

            scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
            scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

            
            if pxL < 0 or pxL > self.fullLeftPicSize[0] or pyL < 0 or pyL > self.fullLeftPicSize[1] : self.setCenterView()
            elif pxR < 0 or pxR > self.fullRightPicSize[0] or pyR < 0 or pyR > self.fullRightPicSize[1] : self.setCenterView()
            
            else :

                scale = self.leftPictureManager.groundPixelSize / self.buttonMapUnit 
                self.currentScale = scale

                self.graphWindowLeft.custom_centerOn(scenePointL,scale,forceGroupCall=True)
                self.graphWindowRight.custom_centerOn(scenePointR,scale,forceGroupCall=True)
                


        elif self.lastCurrentView : 

            pxL, pyL = self.leftPictureManager.coordToPixel(self.lastCurrentView[:2],self.cursorAltitude)
            pxR, pyR = self.rightPictureManager.coordToPixel(self.lastCurrentView[:2],self.cursorAltitude)
            
            scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
            scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

            if pxL < 0 or pxL > self.fullLeftPicSize[0] or pyL < 0 or pyL > self.fullLeftPicSize[1] : self.setCenterView()
            elif pxR < 0 or pxR > self.fullRightPicSize[0] or pyR < 0 or pyR > self.fullRightPicSize[1] : self.setCenterView()
            else : 
                scale = self.lastCurrentView[-1]  
                self.currentScale = scale

                self.graphWindowLeft.custom_centerOn(scenePointL,scale,forceGroupCall=True)
                self.graphWindowRight.custom_centerOn(scenePointR,scale,forceGroupCall=True)

        else : self.setCenterView()
        
        self.updateUserAltitude()
        self.buttonPosition = None

    def updateUserAltitude(self) : 
        gwL = self.graphWindowLeft.ui.graphicsView
        gwR = self.graphWindowRight.ui.graphicsView

        sceneCenterL = gwL.mapToScene(gwL.viewport().rect().center())  
        cPixelL = self.graphWindowLeft.imageRoot.mapFromScene(sceneCenterL)

        sceneCenterR = gwR.mapToScene(gwR.viewport().rect().center())  
        cPixelR = self.graphWindowRight.imageRoot.mapFromScene(sceneCenterR)

        self.cursorAltitude = self.dualManager.calculateZ((cPixelL.x(), cPixelL.y()), (cPixelR.x(), cPixelR.y())) 
        self.optWindow.ui.labelAltitude.setText(f"{self.cursorAltitude:.3f}")
        


    def setCenterView(self) : 
        gwL = self.graphWindowLeft.ui.graphicsView
        gwR = self.graphWindowRight.ui.graphicsView
        
        pxL = (self.realCropValueLeft[0] + self.realCropValueLeft[2]) / 2
        pyL = (self.realCropValueLeft[1] + self.realCropValueLeft[3]) / 2
        pxR = (self.realCropValueRight[0] + self.realCropValueRight[2]) /2
        pyR = (self.realCropValueRight[1] + self.realCropValueRight[3]) / 2

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

        scaleX  = gwL.viewport().width()  / (self.leftPicSize[0] / 8)
        scaleY  = gwL.viewport().height() / (self.leftPicSize[1] / 8) 

        scale  = min(scaleX, scaleY)
        self.currentScale = scale
        
        self.graphWindowLeft.custom_centerOn(scenePointL,scale,forceGroupCall=True)
        self.graphWindowRight.custom_centerOn(scenePointR,scale,forceGroupCall=True)

    def setBaseTransform(self) : 
        leftTransform = self.getQtransform(self.leftPictureManager)
        rightTransform = self.getQtransform(self.rightPictureManager)

        if not self.optWindow.ui.checkBoxFlip.isChecked() : 

            mirror_transform = QTransform()
            mirror_transform.scale(-1, 1)
            mirror_transform.translate(-self.rightPicSize[0], 0)
            rightTransform =  rightTransform * mirror_transform

        self.graphWindowLeft.imageRoot.setTransform(leftTransform)
        self.graphWindowRight.imageRoot.setTransform(rightTransform)
    
    def setExtent2Canvas(self) : 
        
        LGV = self.graphWindowLeft.ui.graphicsView
        sceneRect = LGV.mapToScene(LGV.viewport().rect()).boundingRect()  
        sceneCenter = sceneRect.center()
        centerPixel = self.graphWindowLeft.imageRoot.mapFromScene(sceneCenter)
        
        cx, cy = self.leftPictureManager.pixelToCoord((centerPixel.x(), centerPixel.y()), self.cursorAltitude)
        meters_per_pixel = self.leftPictureManager.groundPixelSize / self.currentScale
        dpi = self.canvas.mapSettings().outputDpi()
        
        scale_canvas = meters_per_pixel * dpi / 0.0254 #Valeur pour mètre vers pouce
        self.canvas.zoomScale(scale_canvas)
        self.canvas.setCenter(QgsPointXY(cx, cy))
        self.canvas.refresh()

    def mouseMoveEvent(self,coordinate) :
        if self.isLoadingPair : return

        if True : 
            mntAlt = self.optWindow.readMNTWithCoord(coordinate)
            if mntAlt is not None and mntAlt != self.optWindow.mntNodata : self.cursorAltitude = mntAlt

        pxL, pyL = self.leftPictureManager.coordToPixel(coordinate,self.cursorAltitude)
        pxR, pyR = self.rightPictureManager.coordToPixel(coordinate,self.cursorAltitude)

        self.endDrawPointLeft = QPointF(pxL, pyL)
        self.endDrawPointRight = QPointF(pxR, pyR)

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(self.endDrawPointLeft)
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(self.endDrawPointRight)

        scale = self.currentScale
        self.graphWindowLeft.custom_centerOn(scenePointL,scale)
        self.graphWindowRight.custom_centerOn(scenePointR,scale)

        self.updateUserAltitude()

        pourcent = 2/100
        deltaX = self.leftPicSize[0]*pourcent
        deltaY = self.leftPicSize[1]*pourcent

        rangeX = (self.realCropValueLeft[0]+deltaX, self.realCropValueLeft[2]-deltaX)
        rangeY = (self.realCropValueLeft[1]+deltaY, self.realCropValueLeft[3]-deltaY)

    
        out_x = self.endDrawPointLeft.x() <= rangeX[0]  or self.endDrawPointLeft.x() >= rangeX[1]
        out_y = self.endDrawPointLeft.y() <= rangeY[0] or self.endDrawPointLeft.y() >= rangeY[1]
        
        if self.firstDrawClick and (out_x or out_y) :
            self.calculNextPairWithPos(rangeX,rangeY,self.endDrawPointLeft)

            return

        if not self.firstDrawClick and self.enableDraw and self.optWindow.currentMNTPath :
            
            self.editCurrentWorkingLine()
        
    def wheelActionEvent(self,direction,modifier,mousePos):
        if self.isLoadingPair : return
        #if mod ctrl zoom
        if modifier & Qt.ControlModifier:
            
            scale = self.leftPictureManager.groundPixelSize / self.canvas.mapUnitsPerPixel()
            self.currentScale = scale
            newAltitude = self.cursorAltitude

        else : 
            zoom_level = math.log2(self.currentScale)

            if zoom_level > 2 : meter_changer = 0.1
            elif zoom_level > 1 : meter_changer = 0.5
            elif zoom_level > 0 : meter_changer = 1
            elif zoom_level > -1 : meter_changer = 2
            else : meter_changer = 4

            if direction == 1 : meter_changer *= 1
            else : meter_changer *= -1

            newAltitude = self.cursorAltitude + meter_changer


        pxL, pyL = self.leftPictureManager.coordToPixel(mousePos,newAltitude)
        pxR, pyR = self.rightPictureManager.coordToPixel(mousePos,newAltitude)

        self.endDrawPointLeft = QPointF(pxL, pyL)
        self.endDrawPointRight = QPointF(pxR, pyR)

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

        self.graphWindowLeft.custom_centerOn(scenePointL,self.currentScale)
        self.graphWindowRight.custom_centerOn(scenePointR,self.currentScale)

        self.updateUserAltitude()

        if not self.firstDrawClick and self.enableDraw and self.optWindow.currentMNTPath :
            self.editCurrentWorkingLine()
            
    def editCurrentWorkingLine(self) : 
        if not self.currentLeftLineObj:
            self.currentLeftLineObj = QGraphicsLineItem(parent=self.graphWindowLeft.imageRoot) 
            self.currentLeftLineObj.setPen(self.my_pen)
            self.graphWindowLeft.drawingLineGroup.addToGroup(self.currentLeftLineObj)
        
        if not self.currentRightLineObj:
            self.currentRightLineObj = QGraphicsLineItem(parent=self.graphWindowRight.imageRoot)
            self.currentRightLineObj.setPen(self.my_pen)
            self.graphWindowRight.drawingLineGroup.addToGroup(self.currentRightLineObj)

        lineL = QLineF(self.startDrawPointLeft, self.endDrawPointLeft)
        lineR = QLineF(self.startDrawPointRight, self.endDrawPointRight)
        
        self.currentLeftLineObj.setLine(lineL)
        self.currentRightLineObj.setLine(lineR)


    def calculNextPairWithPos(self,rangeX,rangeY,qpoint)   :
        threshold_deg=10
        kappa = math.degrees(self.leftPictureManager.kappa)

        #Faire une liste des combinaison plutot que de répter 4 fois
        #Nord à gauche (-90 + 90)
        if (abs(kappa + 90) < threshold_deg):
            if qpoint.x() < rangeX[0] and self.currentUpID :
                self.findNextPair('U')
            elif qpoint.x() > rangeX[1] and self.currentDownID :
                self.findNextPair('D')
            elif qpoint.y() < rangeY[0] and self.currentRightID :
                self.findNextPair('R')
            elif qpoint.y() > rangeY[1] and self.currentLeftID :
                self.findNextPair('L')
        #Nord à droite (90 - 90)
        elif (abs(kappa - 90) < threshold_deg) :
            if qpoint.x() < rangeX[0] and self.currentDownID :
                self.findNextPair('D')
            elif qpoint.x() > rangeX[1] and self.currentUpID :
                self.findNextPair('U')
            elif qpoint.y() <  rangeY[0] and self.currentLeftID :
                self.findNextPair('L')
            elif qpoint.y() >  rangeY[1] and self.currentRightID :
                self.findNextPair('R')
        #Nord en bas (+/- 180 +/- 180)
        elif abs(kappa - 180) < threshold_deg or abs(kappa + 180) < threshold_deg: 
            if qpoint.x() < rangeX[0] and self.currentRightID :
                self.findNextPair('R')
            elif qpoint.x() > rangeX[1] and self.currentLeftID :
                self.findNextPair('L')
            elif qpoint.y() < rangeY[0] and self.currentDownID :
                self.findNextPair('D')
            elif qpoint.y() > rangeY[1] and self.currentUpID :
                self.findNextPair('U')
        #Nord en haut
        else : 
            if qpoint.x() < rangeX[0] and self.currentLeftID :
                self.findNextPair('L')
            elif qpoint.x() >rangeX[1] and self.currentRightID :
                self.findNextPair('R')
            elif qpoint.y() < rangeY[0] and self.currentUpID :
                self.findNextPair('U')
            elif qpoint.y() > rangeY[1] and self.currentDownID :
                self.findNextPair('D')

    def mousePressEvent(self,mouseButton,mousePos) : 

        altitude = self.optWindow.readMNTWithCoord(mousePos)

        coordTuple = (mousePos[0],mousePos[1],altitude)
        if self.optWindow.currentMNTPath and self.enableDraw and self.vectorLayer.geometryType() == QgsWkbTypes.PolygonGeometry :

            if mouseButton == Qt.LeftButton:
                if self.firstDrawClick :
                    pxL, pyL = self.leftPictureManager.coordToPixel(mousePos,self.cursorAltitude)
                    pxR, pyR = self.rightPictureManager.coordToPixel(mousePos,self.cursorAltitude)

                    self.startDrawPointLeft = QPointF(pxL, pyL)
                    self.startDrawPointRight = QPointF(pxR, pyR)

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

            elif mouseButton == Qt.RightButton and len(self.listDrawCoord) > 0:

                self.firstDrawClick = True
                if self.currentLeftLineObj :
                    self.graphWindowLeft.drawingLineGroup.removeFromGroup(self.currentLeftLineObj)
                    self.graphWindowLeft.scene.removeItem(self.currentLeftLineObj)
                self.currentLeftLineObj = None

                if self.currentRightLineObj :
                    self.graphWindowRight.drawingLineGroup.removeFromGroup(self.currentRightLineObj)
                    self.graphWindowRight.scene.removeItem(self.currentRightLineObj)
                self.currentRightLineObj = None
                
                for item in self.listLeftLineObj:
                    if item:
                        self.graphWindowLeft.drawingLineGroup.removeFromGroup(item)
                        self.graphWindowLeft.scene.removeItem(item)
                self.listLeftLineObj = []

                for item in self.listRightLineObj:
                    if item:
                        self.graphWindowRight.drawingLineGroup.removeFromGroup(item)
                        self.graphWindowRight.scene.removeItem(item)
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
                            #if self.paramMenu.ui.radioButtonMerge.isChecked() :
                            mergePolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
                            #else :
                            #automaticPolygon(featureGeo, item.id(), newGeo, currentVectorLayer)
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
                
        elif self.enableDraw and self.vectorLayer.geometryType() == QgsWkbTypes.PointGeometry and mouseButton == Qt.LeftButton :
            
            if QgsWkbTypes.hasZ(self.vectorLayer.wkbType()) : geo = QgsGeometry(QgsPoint(coordTuple[0],coordTuple[1],coordTuple[2]))
            else : geo = QgsGeometry.fromPointXY(QgsPointXY(coordTuple[0],coordTuple[1]))
            
            self.windowHandler('qgis')
            feature = addPoint(self.vectorLayer, geo)
            
            self.vectorLayer.startEditing()
            resultForm = self.iface.openFeatureForm(self.vectorLayer, feature)
            if resultForm == False : 
                provider =  self.vectorLayer.dataProvider()
                provider.deleteFeatures([feature.id()]) 
            self.vectorLayer.commitChanges()
            self.vectorLayer.triggerRepaint()
            self.windowHandler('picture')
            
            self.startPolygonThread()    

    
    def keyboardZoom(self,value):
        zoomLevels = [128, 64, 32, 16, 8, 4, 2, 1]  
        scaleFactor = zoomLevels[value]
        
        scaleX  = self.leftPicSize[0] / scaleFactor
        scaleY = self.leftPicSize[1] / scaleFactor

        gwL = self.graphWindowLeft.ui.graphicsView
        gwR = self.graphWindowRight.ui.graphicsView
    
        scaleW  = gwL.viewport().width()  / scaleX
        scaleH  = gwL.viewport().height() / scaleY

        scale  = min(scaleW, scaleH)
        self.currentScale = scale

        center_scene_L = gwL.mapToScene(gwL.viewport().rect().center())
        center_scene_R = gwR.mapToScene(gwR.viewport().rect().center())

        self.graphWindowLeft.custom_centerOn(center_scene_L,self.currentScale)
        self.graphWindowRight.custom_centerOn(center_scene_R,self.currentScale)

        self.setExtent2Canvas()

        






