'''
Cette version de l'application de rehaussement est concu pour fonctionner indépendamment 
L'application permet de rehaussser des photos de plusieurs formats (jpeg et TIF principalement) 
Il est possible de modifier le constraste, la saturation, la luminosité et le netteté
Il est aussi possible de d'ajouter du rouge, du vert ou du bleu dans l'image. 
Le bouton Min/Max permet de couper les valeurs RGB en dessous de 5% et au dessus de 95% de l'histogramme
Il est possible d'effectuer l'opération Min/Max en considérant seulement la région observée seulement 
Il est possible d'enregistrer les photos dans leur format original
Zoom et Pan disponible avec la souris pour faciliter la navigation 
La photo en cours est affiché en 3 temps. Chaque itération augmente la résolution de l'image 
se qui permet d'observer la photo rehaussée dans son entièreté
IL est possible de drag n drop une ou plusieurs photos si on ne veut pas importer un dossier complet 

Optimisation futur 
    Gestion des photos à 4 couches (RGBA) et à une seule couche (Grayscale)
'''
from PIL import Image, ImageEnhance #Utiliser seulement pour l'enregistrement
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_Rehaussement import colorWindow, tableModel
import sys, os, time, threading, traceback, gc
from osgeo import gdal
from math import ceil
Image.MAX_IMAGE_PIXELS = 1000000000 
from scipy.ndimage import uniform_filter


#from win32com.shell import shell, shellcon
#file to save current project shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, None, 0) + "\\appRehaussement"

#A retirer pour tout simple regarder si GDAL peut ouvrir le format
acceptType = ["jpg", "jpeg", "tiff", "tif", "bmp", "png", "JPG"]

class app(QApplication):
    def __init__(self, argv):
        QApplication.__init__(self,argv)
        self.colorWindow = colorWindow()
        self.colorWindow.ui.groupBox.dropHappen.connect(self.importFile)
        self.colorWindow.ui.radioButtonCurrent.toggled.connect(self.currentViewActivate)
        self.colorWindow.ui.currentStatusButton.pressed.connect(self.keepCurrentView)

        self.spinBoxesTimer = QTimer(self)
        self.spinBoxesTimer.setSingleShot(True)
        self.spinBoxesTimer.timeout.connect(self.enhancePicture)

        self.scene = QGraphicsScene(self.colorWindow.ui.graphicsView)
        self.colorWindow.ui.graphicsView.setScene(self.scene)
        self.colorWindow.show()

        self.switchActivate = False
        self.savingThreadInProcess = False
        self.showThreadInProcess = False
        self.statusKeepCurrentView = False
        self.listParam = []

        self.colorWindow.ui.saveButton.clicked.connect(self.saveSelectPicture)
        self.colorWindow.ui.toolButton.clicked.connect(self.showDialog)
        self.colorWindow.ui.zoomInButton.clicked.connect(self.zoomIn)
        self.colorWindow.ui.zoomOutButton.clicked.connect(self.zoomOut)
        self.colorWindow.ui.tableView.verticalScrollBar().rangeChanged.connect(self.newScrollBar)
        
        self.colorWindow.setWindowState(Qt.WindowMaximized)
    
    
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

    #Fonction lancer lorsque le thread d'affichage se termine
    def seekDone(self):

        self.showThreadInProcess = False
        gc.collect()
        QApplication.processEvents()

        
    #Fonction appelée par le thread pour ajouter une portion de l'image sur l'affichage
    def addPixmap(self, pixmap, scaleFactor, topX, topY) :
        
        d = self.colorWindow.ui.graphicsView.scene().addPixmap(pixmap)
        d.setScale(scaleFactor)
        d.setOffset(topX, topY)

    #Fonction qui permet de réaliser le Pan 
    def mMoveEvent(self, ev):
        
        if self.colorWindow.ui.zoomPanButton.isChecked() :
            gView = self.colorWindow.ui.graphicsView
            delta = ev.pos() - self.panPosition
            gView.horizontalScrollBar().setValue(gView.horizontalScrollBar().value() - delta.x())
            gView.verticalScrollBar().setValue(gView.verticalScrollBar().value() - delta.y())
            self.panPosition = ev.pos()

    #Fonction qui détecte que la souris a été cliquée pour faire le Pan
    def mPressEvent(self, ev):
        self.panPosition = ev.pos()
        self.pressPosition = ev.pos()
        print(ev.pos())

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
    
    #Fonction qui permet de sélectionner le dossier à importer 
    ###Ajouter un autre bouton pour l'importation de fichier vs dossier 
    def showDialog(self) : 
        path = os.path.dirname(os.path.abspath(__file__))
        fname = QFileDialog.getExistingDirectory(self.colorWindow, 'Ouvrir le dossier',path)
        if fname:
            self.colorWindow.ui.lineEdit.setText(fname)

    #Fonction pour trier si le fichier à afficher est compatible avec l'application
    def importFile(self):
        success = True
        self.colorWindow.ui.statusbar.clearMessage()
        
        if not self.savingThreadInProcess : 
            self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")
        
        
        importList = self.colorWindow.ui.groupBox.importList
        self.listPicture = []
        
        if len(importList) > 1 :

            try :
                self.path = importList[0].toString().split('file:///')[1].rpartition("/")[0]
            except :
                self.path = importList[0].toString().split('file:')[1].rpartition("/")[0]
            
            for item in importList :
                try :
                    fileName = item.toString().split('file:///')[1]
                except :
                    fileName = item.toString().split('file:')[1]

                if fileName.split(".")[-1] in acceptType:
                    strSplit = self.path + "/"
                    self.listPicture.append(fileName.split(strSplit)[-1])
                
                
            if not self.listPicture : 
                self.colorWindow.ui.statusbar.showMessage("Les éléments importés ne possèdent aucune photo de format valide", 20000)
                success = False
            else :
                self.colorWindow.ui.groupBox.dropHappen.disconnect(self.importFile)
                self.colorWindow.ui.lineEdit.setText(self.path)
                self.colorWindow.ui.groupBox.dropHappen.connect(self.importFile)
                    
        else :
            self.path = self.colorWindow.ui.lineEdit.text()
            
            if os.path.isfile(self.path) :

                try :
                    fileName = importList[0].toString().split('file:///')[1]
                except :
                    fileName = importList[0].toString().split('file:')[1]

                self.path = fileName.rpartition("/")[0]

                if fileName.split(".")[-1] in acceptType:
                    strSplit = self.path + "/"
                    self.listPicture.append(fileName.split(strSplit)[-1])
                    self.colorWindow.ui.groupBox.dropHappen.disconnect(self.importFile)
                    self.colorWindow.ui.lineEdit.setText(self.path)
                    self.colorWindow.ui.groupBox.dropHappen.connect(self.importFile)
                
                else :
                    self.colorWindow.ui.statusbar.showMessage("L'élément importé n'est pas un photo de format valide", 20000)
                    success = False
            
            else :
                f = []
                for (dirpath, dirnames, filenames) in os.walk(self.path):
                    f.extend(filenames)
                    break
                
                for i in f : 
                    if i.split(".")[-1] in acceptType:
                        self.listPicture.append(i)

                if not self.listPicture : 
                    self.colorWindow.ui.statusbar.showMessage("Le dossier ne possède aucune photo de format valide", 20000)
                    success = False


        if success == False : 
            self.colorWindow.ui.groupBox.dropHappen.disconnect(self.importFile)
            self.colorWindow.ui.lineEdit.clear()
            self.colorWindow.ui.groupBox.dropHappen.connect(self.importFile)
            if self.switchActivate : 
                self.setConnection(False)
                self.resetBox()
                self.colorWindow.ui.tableView.selectionModel().currentChanged.disconnect(self.switchPicture)
                model = tableModel([])
                self.colorWindow.ui.checkBoxSave.setVisible(False)
                self.colorWindow.ui.tableView.setModel(model)
                scene = QGraphicsScene()
                self.colorWindow.ui.graphicsView.setScene(scene)
                self.switchActivate = False
            self.colorWindow.ui.saveButton.setEnabled(False)
            return
    
        self.listPicture.sort()

        data = []
        for i in self.listPicture:
            data.append([i, QCheckBox("")])
        

        self.colorWindow.ui.checkBoxSave.setVisible(True)
        self.colorWindow.ui.checkBoxSave.setCheckState(False)
        self.colorWindow.ui.checkBoxSave.stateChanged.connect(self.selectAll)
        model = tableModel(data)
        self.colorWindow.ui.tableView.setModel(model)
        self.colorWindow.ui.tableView.setColumnWidth(0,290)
        self.colorWindow.ui.tableView.setColumnWidth(1,20)
        self.colorWindow.ui.tableView.selectionModel().currentChanged.connect(self.switchPicture)
        self.colorWindow.ui.tableView.selectionModel().select(self.colorWindow.ui.tableView.model().index(0,0), QItemSelectionModel.Select)
        self.switchActivate = True
        self.resetBox()

        if not self.savingThreadInProcess : 
            self.colorWindow.ui.saveButton.setEnabled(True)
    
        self.zoomState = 0

        self.setConnection(True)
        self.colorWindow.ui.buttonBoxReset.clicked.connect(self.reset)
        self.reset()

        
    #Permet de changer la photo couramment affiché
    def switchPicture(self, value) :

        if value.column() == 0 :
            self.colorWindow.ui.tableView.selectionModel().currentChanged.disconnect(self.switchPicture)
            lastSelect = self.colorWindow.ui.tableView.model().currentSelect
            self.colorWindow.ui.tableView.model().currentSelect = (value.row(), value.column())
            ind = self.colorWindow.ui.tableView.model().index(lastSelect[0],lastSelect[1])
            self.colorWindow.ui.tableView.model().dataChanged.emit(ind, ind)
            self.zoomState = 0

            self.enhancePicture("reset")
            self.colorWindow.ui.tableView.selectionModel().currentChanged.connect(self.switchPicture)
    
    #Gestion de la taille du table view lorsque la barre de défilement est nécessaire
    def newScrollBar(self, min, max):
        if max > 0 :
            geo = self.colorWindow.ui.tableView.geometry()
            self.initTableViewGeo = geo
            self.colorWindow.ui.tableView.setGeometry(QRect(geo.x()-10, geo.y(), geo.width()+20, geo.height()))
        else :
            self.colorWindow.ui.tableView.setGeometry(self.initTableViewGeo)
    
    #Fonction appellée quand le checkbox min/max est utilisé
    def minmaxActivate(self, value):
        
        self.colorWindow.ui.radioButtonCurrent.setEnabled(False)
        self.colorWindow.ui.radioButtonComplete.setEnabled(value)
        self.enhancePicture(value)

    #Fonction pour activer le bouton de conservation de l'histogramme 
    def currentViewActivate(self, value):
        self.colorWindow.ui.currentStatusButton.setEnabled(value)
        self.enhancePicture(value)


    #Détermine si l'on conserve les valeurs min/max nouvellement calculées 
    def keepCurrentView(self):
        self.statusKeepCurrentView = not self.statusKeepCurrentView
        if self.statusKeepCurrentView :
            self.colorWindow.ui.currentStatusButton.setText("Modifier")
        else :
            self.colorWindow.ui.currentStatusButton.setText("Conserver")
            self.enhancePicture(True)
    
    #Fonction de rehaussement d'image, utilise PIL et permet de la modification sur les couches RGB
    def enhancePicture(self, ajustView=False):
        if hasattr(self, "tSeek"):
            if self.showThreadInProcess : 
                try:
                    self.tSeek.newImage.disconnect(self.addPixmap)
                except:
                    pass
                
                self.tSeek.keepRunning = False
                self.tSeek.wait()
                self.showThreadInProcess = False
            del self.tSeek
            

        self.getBoxValues(ajustView)

        for item in list(self.scene.items()):
            if isinstance(item, QGraphicsPixmapItem):
                self.scene.removeItem(item)
        
        gc.collect()
        QApplication.processEvents()
        
        pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
        GV = self.colorWindow.ui.graphicsView
        pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))

        
        currentPath = self.path + "/" + self.listPicture[self.colorWindow.ui.tableView.model().currentSelect[0]]

        self.tSeek = threadShow(currentPath, pointZero, pointMax, self.listParam)
        self.tSeek.newImage.connect(self.addPixmap)
        self.tSeek.finished.connect(self.seekDone)
        
        self.showThreadInProcess = True
        self.tSeek.start(QThread.IdlePriority)
        

        if ajustView == "reset":
            self.colorWindow.ui.graphicsView.fitInView(self.tSeek.rect, Qt.KeepAspectRatio)
            self.zoomState = 0

        

    #Remet la photo à son affichage d'origine
    def reset(self) : 
        self.setConnection(False)
        self.resetBox()
        self.enhancePicture("reset")
        self.setConnection(True)

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
        elif cv and self.statusKeepCurrentView and type(changePixVal) is int:
            pointZero = self.colorWindow.ui.graphicsView.mapToScene(QPoint(0,0))
            GV = self.colorWindow.ui.graphicsView
            pointMax = self.colorWindow.ui.graphicsView.mapToScene(QPoint(GV.width(),GV.height()))
            pix = self.calculHistogram(pointZero, pointMax)
            self.currentPixVal = pix
       
        elif cv :
            pix = self.currentPixVal

        self.listParam = [con, lum, sat, net, red, gre, blu, bmm, cv, pix]


    #Permet de reproduire l'état du checkbox unique sur toutes les photos de la liste
    def selectAll(self,value) : 
        for i in range(len(self.listPicture)) : 
            ind = self.colorWindow.ui.tableView.model().index(i,1)
            self.colorWindow.ui.tableView.model().setData(ind, value, Qt.CheckStateRole)


    #Démarre l'enregistrement des photos sélectionnées 
    def startSavingThread(self, listPic) : 

        fname = QFileDialog.getExistingDirectory(self.colorWindow, 'Choisir le dossier d\'enregistrement' ,self.path)
        
        f = []

        if fname :
            for (dirpath, dirnames, filenames) in os.walk(fname):
                f.extend(filenames)
                break
            listSaveName = []
            for i in listPic : 
                name = i
                val = 2
                while name in f :
                    name  = i.split(".")[0] + "_(" + str(val) + ")." + i.split(".")[-1]
                    val += 1
                listSaveName.append(name)
            

            self.getBoxValues()
            self.nbPicture = len(listPic)

            if hasattr(self.colorWindow.ui, "progressBar"):
                self.colorWindow.ui.progressBar.close()
                del self.colorWindow.ui.progressBar
            
            STRbar = " Photos traitées 0/" + str(self.nbPicture) + " "
            self.colorWindow.ui.progressBar = QProgressBar(self.colorWindow.ui.centralwidget)
            self.colorWindow.ui.progressBar.setGeometry(QRect(550+self.colorWindow.pixelX, 660+self.colorWindow.pixelY, 461, 23))
            self.colorWindow.ui.progressBar.setObjectName("progressBar")
            self.colorWindow.ui.progressBar.setFormat(STRbar)
            self.colorWindow.ui.progressBar.setMaximum(self.nbPicture)
            self.colorWindow.ui.progressBar.setValue(0)
            self.colorWindow.ui.progressBar.show()

            self.t = threadSave(self.path, listPic, self.listParam, fname, listSaveName)
            self.threadPath = self.path
            self.t.iterationDone.connect(self.iterationOnSaving)
            self.t.finished.connect(self.threadingDone)
            self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/loading.png);")
            self.colorWindow.ui.saveButton.setEnabled(False)
            self.savingThreadInProcess = True
            self.t.start()

        
    #Place dans une liste les images sélectionnées et lance leur enregistrement
    def saveSelectPicture(self):
        data = self.colorWindow.ui.tableView.model().data
        newList = []
        for d in data :
            if d[1].checkState() == Qt.Checked :
                newList.append(d[0])
        if newList :
            self.startSavingThread(newList)


    #Permet de mettre à jour la barre de progrès lorsqu'une photo termine d'être enregistré
    def iterationOnSaving(self):
        v = self.colorWindow.ui.progressBar.value()
        v += 1 
        STRbar = " Photos traitées " + str(v)  + "/" + str(self.nbPicture) + " "
        self.colorWindow.ui.progressBar.setValue(v)
        self.colorWindow.ui.progressBar.setFormat(STRbar)

    #Transforme l'état de l'enregistrement vers la croix rouge
    #Slot signigie qu'il est appeler par un object QT
    @pyqtSlot()
    def go2Cross(self):
        self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")
        
    #Fonction appelée à la fin du thread lorsque l'enregistrement se termine
    def threadingDone(self):
        self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/greenCheck.png);")
        self.savingThreadInProcess = False
        if self.colorWindow.ui.lineEdit.text() != "":
            self.colorWindow.ui.saveButton.setEnabled(True)
            if self.threadPath != self.path :
                QTimer.singleShot(5000, self.go2Cross)
        else : 
            QTimer.singleShot(5000, self.go2Cross)


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
    


#Permet l'enregistrement des photos
#L'idée du thread est de pouvoir continuer à utiliser l'application lorsque l'enregistrement s'execute
#La majorité des fonctions sont identiques à celle dans la classe de l'application seul les noms des variables sont différents

#Fonction a refaire avec la nouvelle version de threadShow
#L'ordre des opérations de rehaussement n'étant pas la même il a des risques que le résultat soit différent
#Le min/max étant la dernière opération, l'activer aura un effet non désirer sur l'enregistrement
#Étant un plugin qui à pour rôle principale de faire des tests de développement, la priorité pour régler ce problème est faible
class threadSave(QThread):
    iterationDone = pyqtSignal()
    def __init__(self, path, listPicture, listParam, savePathDir, listSaveName):
        QThread.__init__(self)
        self.path = path
        self.listPicture = listPicture
        self.listParam = listParam
        self.savePathDir = savePathDir
        self.listSaveName = listSaveName

    def run(self):

        for pic in range(len(self.listPicture)) : 
            currentPath = self.path + "/" + self.listPicture[pic]
            myImage = Image.open(currentPath)
            self.pixValue = []
            if hasattr(myImage, "n_frames") :

                t = imageEnhancing(myImage, self.listParam)
                t.start()
                toSave = t.join() 
                tab = []
                for i in range(1, myImage.n_frames):
                    tab.append(2**i)

                newPath = self.savePathDir + "/" + self.listSaveName[pic]
                
                driver = gdal.GetDriverByName("GTiff")
                

                #Cette méthode d'enregistrement cause une perte de réponse de l'application 
                #l'application ne répond plus, il est donc impossible de faire du traitement d'image pendant l'enregistrement 
                #Peut être une cause déjà trouver en ligne --> à rechercher 
                #Regarder les lignes de codes qui cause le problème --> seul test tout était en commentaire
                fileout = driver.Create(newPath, myImage.size[0], myImage.size[1], 3 ,gdal.GDT_Byte, ["COMPRESS=JPEG", "PHOTOMETRIC=YCBCR", "TILED=YES" , "JPEG_QUALITY=90"])
                fileout.GetRasterBand(1).WriteArray(np.array(toSave[0], dtype=np.uint8))
                fileout.GetRasterBand(2).WriteArray(np.array(toSave[1], dtype=np.uint8))
                fileout.GetRasterBand(3).WriteArray(np.array(toSave[2], dtype=np.uint8))
                fileout.BuildOverviews("AVERAGE", tab)
                fileout.FlushCache()
                fileout = None

                self.iterationDone.emit()
 
            else : 
                t = imageEnhancing(myImage, self.listParam)
                t.start()
                toSave = t.join() 

                newPath = self.savePathDir + "/" + self.listSaveName[pic]
                img = Image.merge("RGB", (toSave[0],toSave[1],toSave[2]))
                img.save(newPath)
                self.iterationDone.emit()

            myImage.close()



#Thread qui permet l'affichage des images de plus grandes résolutions
#Il ajoute des petites portions de l'image à chaque itération
#Il concidère toujours la vue courante dans la priorité d'affichage
class threadShow(QThread):
    newImage = pyqtSignal(QPixmap, float, int, int)
    
    def __init__(self, picturePath, pointZero, pointMax,listParam):
        super().__init__()
        self.picturePath = picturePath
        self.pointZero = pointZero
        self.pointMax = pointMax
        self.listParam = listParam
        self.perform_Enhancing = True if self.listParam[:8] != [0,0,0,0,0,0,0,False] else False
        self.keepRunning = True
        
        # Open GDAL dataset ONCE here
        gdal.SetCacheMax(256 * 1024 * 1024)
        self.ds = gdal.Open(self.picturePath, gdal.GA_ReadOnly)
        self.rect = QRectF(0,0,self.ds.RasterXSize,self.ds.RasterYSize)
        if self.ds is None:
            raise ValueError("Cannot open image")
        
        
        
    
    def run(self):
        # Get dimensions from GDAL dataset (no loading yet!)
        height = self.ds.RasterYSize
        width = self.ds.RasterXSize
        self.stats, overViewArray = self.get_global_stats_from_overview()

        if overViewArray is not None: 
            overViewArray = self.applyEnhancements(overViewArray,self.listParam)
            he, wi, _ = overViewArray.shape
            q_image = QImage(overViewArray.data, wi, he, wi*3, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)
            scale = min(width/wi, height/he)
            self.newImage.emit(pixmap, scale, 0, 0)

        maxX, maxY = 2048,2048
        
        # Calculate tile boundaries
        topX = max(0, int(self.pointZero.x()-1024))
        topY = max(0, int(self.pointZero.y()-1024))
        lowX = min(width, int(self.pointMax.x()+1024))
        lowY = min(height, int(self.pointMax.y()+1024))
        
        sizePixelX = abs(lowX - topX)
        sizePixelY = abs(lowY - topY)
        
        
        rects = [
            [topX, topY, lowX, lowY],
            [0, 0, topX, height],
            [lowX, 0, width, height],
            [topX, 0, topX + sizePixelX, topY],
            [topX, topY + sizePixelY, lowX, height]
        ]
        #rects = [[0, 0, width, height]]

        # Load and emit tiles ONE AT A TIME (on-demand)
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

        # --- Min–Max Stretch (only if enabled) ---
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
            arr -= lows               # in-place subtract
            arr /= (highs - lows)     # cannot avoid temporary highs−lows but OK
            arr *= 255.0    
        

        # --- Mean-based Contrast (per band, Pillow-like) ---
        contrast = params[0]
        if contrast != 0:
            #factor = 1.0 + (contrast / 100.0)
            if contrast > 0:
                if contrast < 50:
                    factor = 1 + (0.02 * contrast)  # 1.0 to 2.0
                elif contrast < 80:
                    factor = 2 + (0.1 * (contrast - 50))  # 2.0 to 5.0
                else:
                    factor = 5 + (contrast - 80)  # 5.0 to 25.0
            else:
                factor = 1 + (contrast / 100)
            #arr = (arr - means) * factor + means
            grayscale = (arr[:, :, 0] * 0.299 + 
                        arr[:, :, 1] * 0.587 + 
                        arr[:, :, 2] * 0.114)
            
            # Get mean of grayscale
            mean = float(grayscale.mean())
            for c in range(3):
                channel = arr[:, :, c]
                channel[:] = mean + (channel - mean) * factor

        # --- Saturation (unchanged) ---
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
            
            # Blend: output = grayscale + (original - grayscale) * factor
            for c in range(3):
                channel = arr[:, :, c]
                channel[:] = grayscale + (channel - grayscale) * factor


        # --- Per-channel R/G/B adjustments ---
        for i, ch_param in enumerate(params[4:7]):
            if ch_param != 0:
                factor = 1.0 + (ch_param / 100.0)
                arr[:,:,i] *= factor


        # --- Sharpness (Unsharp Mask) ---
        sharpness = params[3]
        if sharpness != 0:
            sharp_factor = sharpness / 10.0 + 1  
            #blurred = cv2.GaussianBlur(arr, (0,0), sigmaX=1.0)
            blurred = uniform_filter(arr,size=(3, 3, 1))
            arr[:] = blurred + (arr - blurred) * sharp_factor


                  
        # --- Brightness ---
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

            # Use smallest overview (but not pyramid zero)
            ovr_count = band.GetOverviewCount()
            #print(ovr_count)
            if ovr_count > 0:
                ovr_band = band.GetOverview(3)
                arr = ovr_band.ReadAsArray().astype(np.float32)
            else:
                return None, None

            arr_flat = arr[np.isfinite(arr)]

            # percentile min/max stretch values
            low, high = np.percentile(arr_flat, [lower, upper])

            # mean for contrast reference
            #mean = arr.mean()

            stats.append((low, high))
        #print(stats)
            band_arrays.append(arr)
        
        img = np.stack(band_arrays, axis=2)
        return stats, img
        #else : return stats, None
    
    def applyMinMaxStretch(self, arr, stretch_values):
        out = np.zeros_like(arr, dtype=np.float32)
        for b in range(arr.shape[2]):
            low, high = stretch_values[b]
            stretched = (arr[:,:,b] - low) / (high - low) * 255.0
            out[:,:,b] = np.clip(stretched, 0, 255)
        return out

#Thread qui reçoit une image PIL ainsi que la liste des paramètres de rehaussement
#Le thread permet de réaliser le rehaussement
#Il retourne une list qui contient les trois couches de l'image  
class imageEnhancing(threading.Thread):

    def __init__(self, image, listParam):
        threading.Thread.__init__(self)
        self.image = image
        self.listParam = listParam

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
    

if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())
    



