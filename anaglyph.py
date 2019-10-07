from PIL import Image, ImageDraw
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_optionWindow import optionWindow
from ui_graphicsWindow import graphicsWindow 
from threadLoading import threadPicture
from worldManager import pictureManager, dualManager
import sys, os, time, math

#Permet l'ouverture avec PIL de fichier énorme!
Image.MAX_IMAGE_PIXELS = 1000000000 

#Cyan = Left = Gauche
#Rouge = Right = Droite
#Éventuellement enlever tout code de couleur pour garder gauche et droite

class app(QApplication):

    #Initialisation de l'application, des variables
    #Connection entre les boutons du menu d'options (mOpt) et leur fonction attitrée
    #On fait apparaître le menu des options seul
    #Les écrans où l'on veut que les fênetres s'ouvrent sont choisi ici 
    def __init__(self, argv):
        QApplication.__init__(self,argv)

        self.intRightScreen = 3
        self.intLeftScreen = 1

        self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)
        self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)

        self.temp = "temp.jpg"
        self.demoLeftExist = False
        self.demoRightExist = False
        self.redOrientation = 0
        self.cyanOrientation = 0
        self.redMiroir = 0
        self.cyanMiroir = 0


        self.redName = False 
        self.cyanName = False 
        self.anaglyphActivate = False #??
        

        self.Z = 300

        self.optWindow = optionWindow()

        self.optWindow.ui.boxMiroirRed.currentIndexChanged.connect(self.mMiroirRed)
        self.optWindow.ui.boxMiroirCyan.currentIndexChanged.connect(self.mMiroirCyan)
        self.optWindow.ui.boxOrientationRed.currentIndexChanged.connect(self.mOrientationRed)
        self.optWindow.ui.boxOrientationCyan.currentIndexChanged.connect(self.mOrientationCyan)
        self.optWindow.ui.importLineRed.textChanged.connect(self.mNewRedPic)
        self.optWindow.ui.importLineCyan.textChanged.connect(self.mNewCyanPic)
        self.optWindow.ui.importButtonRed.clicked.connect(self.mImportRed)
        self.optWindow.ui.importButtonCyan.clicked.connect(self.mImportCyan)
        
        
        self.optWindow.ui.panButton.clicked.connect(self.panClick)
        self.optWindow.ui.offsetButton.clicked.connect(self.offsetClick)

        self.optWindow.ui.radioNoirBlanc.toggled.connect(self.setSuper)
        self.optWindow.ui.saveSuper.clicked.connect(self.saveSuper)

        self.optWindow.ui.affichageButton.clicked.connect(self.mAffichage)
        self.optWindow.closeWindow.connect(self.optWindowClose)

        self.optWindow.show()


    #Fonction qui permet l'affichage des fenêtres. 
    def mAffichage(self) : 
        #Anaglyphe
        if self.optWindow.ui.radioAnaglyph.isChecked() : 
            self.loadWindows(2)
        #Fenêtre séparée
        else :            
            self.loadWindows(0)

    #Fonction appelée lors de la fermeture du mOpt
    #Si l'on ferme le mOpt toute l'application ferme au complet, soit les deux fenêtres avec les images
    def optWindowClose(self):
        if self.demoLeftExist :
            os.remove("demoLeft.jpg")
        if self.demoRightExist :
            os.remove("demoRight.jpg")
        if hasattr(self, "graphWindowLeft"):
            self.graphWindowLeft.close()
        if hasattr(self, "graphWindowRight"):
            self.graphWindowRight.close()
    
    #Fonction qui permet un traitement en couleur ou en noir et blanc sur les photos superposées 
    def setSuper(self):

        #Vérification que les photos sont de la même taille afin de les superposer
        if self.rightPic.size != self.leftPic.size :
            QMessageBox.information(self.optWindow, "Taille Différente", "Les images importées ne sont pas de la même taille. \nChoisir deux images de taille similaire ")
            return 1

        if self.optWindow.ui.radioCouleur.isChecked() :
            img_right_splited = self.rightPic.split()
            img_left_splited = self.leftPic.split()
            img_anaglyph_color = Image.merge('RGB', (img_left_splited[0], img_right_splited[1], img_right_splited[2]))
            img_anaglyph_color.save(self.temp)
            self.currentSuperPic = img_anaglyph_color 
        
        else : 
            img_right_grey = self.rightPic.convert('L')
            img_left_grey = self.leftPic.convert('L')
            img_anaglyph_grey = Image.merge('RGB', (img_left_grey, img_right_grey, img_right_grey))
            img_anaglyph_grey.save(self.temp)
            self.currentSuperPic = img_anaglyph_grey

        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        os.remove(self.temp)
        return 0

    #Fonction qui réalise le traitement des photos miniatures et affiche 
    # la nouvelle version de l'image sur le mOpt
    # PIL est utilisé pour le traitement.
    def processSmallPicture(self, picture, rotation, miroir):
        
        if rotation == 0 and miroir == 0 :
            picture.save(self.temp)

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
            pic.save(self.temp)

        scene = QGraphicsScene()
        a = QImage(self.temp)


        ##### Change this
        if picture == self.demoLeftPic :
            scene.addPixmap(QPixmap.fromImage(a))
            self.optWindow.ui.graphicsViewRed.setScene(scene)
            self.optWindow.ui.graphicsViewRed.fitInView(self.optWindow.ui.graphicsViewRed.sceneRect(), Qt.KeepAspectRatio)
        
        else :
            self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
            self.optWindow.ui.graphicsViewCyan.setScene(scene)
            self.optWindow.ui.graphicsViewCyan.fitInView(self.optWindow.ui.graphicsViewCyan.sceneRect(), Qt.KeepAspectRatio)

        os.remove(self.temp)
    
    #Fonction de traitement d'image pour modifier l'orientation
    #Les angles de rotation possible sont 0, 90, 180 et 270
    def mOrientationRed(self, value):
        self.redOrientation = value
        self.processSmallPicture(self.demoLeftPic, self.redOrientation, self.redMiroir)

    
    #Idem à mOrientationRed
    def mOrientationCyan(self, value):
        self.cyanOrientation = value
        self.processSmallPicture(self.demoRightPic, self.cyanOrientation, self.cyanMiroir)
        
    #Fonction de traitement d'image pour ajouter un effet mirroir à l'image
    #Deux modes sont possible, soit un effet mirroir à l'horizontal et un à la verticale
    def mMiroirRed(self, value):
        self.redMiroir = value
        self.processSmallPicture(self.demoLeftPic, self.redOrientation, self.redMiroir)
        
    #Idem à mMiroirRed
    def mMiroirCyan(self,value):
        self.cyanMiroir = value
        self.processSmallPicture(self.demoRightPic, self.cyanOrientation, self.cyanMiroir)


    #Fonction réaliser lorsqu'une photo est importée 
    #Elle permet de rendre le panneau de fonctionnalité accessible à l'utilisateur 
    #pour le traitement d'image ainsi que le bouton d'importation
    #L'image est affiché en petit format pour permettre une visualisation du 
    #résultat qui sera produit suite à l'importation  
    #Si une nouvelle photo est importée, l'ancienne est fermée 
    #Si la photo est un fichier tif avec plusieurs versions de l'image, 
    #on récupère une version plus petite plutot que la produire, le résultat est donc 
    #instantané
    def mNewRedPic(self) : 

        self.optWindow.ui.boxOrientationRed.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirRed.setCurrentIndex(0)
          
        self.redName = False
        self.enableOptionImage(False)
        self.optWindow.ui.affichageButton.setEnabled(False)
        self.optWindow.ui.groupBoxSuper.setEnabled(False)       

        try :
            del self.graphWindowLeft
            self.graphWindowRight.close()
        except :
            pass

        self.leftPic = Image.open(self.optWindow.ui.importLineRed.text())

        if hasattr(self.leftPic, "n_frames"): #and format == tif??
            for i in range(self.leftPic.n_frames):
                self.leftPic.seek(i)
                if self.leftPic.size < (200,200) :
                    self.leftPic.seek(i-1)
                    self.leftPic.save("demoLeft.jpg")
                    self.demoLeftPic = Image.open("demoLeft.jpg")
                    self.demoLeftExist = True
                    self.leftPic.seek(0)
                    break

        elif self.leftPic.size[0] > self.leftPic.size[1] :
            self.demoLeftPic = self.leftPic.resize((300,200))
        else :
            self.demoLeftPic = self.leftPic.resize((200,300))

        draw = ImageDraw.Draw(self.demoLeftPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        self.demoLeftPic.save(self.temp)

        sceneRed = QGraphicsScene()
        img = QImage(self.temp)
        sceneRed.addPixmap(QPixmap.fromImage(img))
        self.optWindow.ui.graphicsViewRed.setScene(sceneRed)
        self.optWindow.ui.graphicsViewRed.show()
        self.optWindow.ui.graphicsViewRed.fitInView(self.optWindow.ui.graphicsViewRed.sceneRect(), Qt.KeepAspectRatio)
        self.optWindow.ui.label.setEnabled(True)
        self.optWindow.ui.label_2.setEnabled(True)
        self.optWindow.ui.boxMiroirRed.setEnabled(True)        
        self.optWindow.ui.boxOrientationRed.setEnabled(True)
        self.optWindow.ui.importButtonRed.setEnabled(True)
        self.optWindow.ui.importDoneRed.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")
        os.remove(self.temp)
        
        self.graphWindowLeft = graphicsWindow("Image Gauche")
        self.graphWindowLeft.setWindowState(Qt.WindowMaximized)
        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height())
        self.graphWindowLeft.ui.graphicsView.setGeometry(rect)
        self.graphWindowLeft.ui.widget.setGeometry(rect)
        self.graphWindowLeft.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))

        fname = self.optWindow.ui.importLineRed.text()
        filename = "/" +  fname.split("/")[-1].split(".")[0]
        self.path = fname.partition(filename)[0]

        pathPAR = self.optWindow.ui.importLineRed.text().split(".")[0] + ".par"
        self.leftPictureManager = pictureManager(self.leftPic.size, pathPAR, "aa")

    #Idem à mNewRedPic
    def mNewCyanPic(self):
        
        self.optWindow.ui.boxOrientationCyan.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirCyan.setCurrentIndex(0)

        self.cyanOrientation = 0
        self.cyanMiroir = 0
        self.cyanName = False
        self.enableOptionImage(False)
        self.optWindow.ui.affichageButton.setEnabled(False)
        self.optWindow.ui.groupBoxSuper.setEnabled(False)

        try :
            del self.graphWindowRight
            self.graphWindowLeft.close()
        except :
            pass
        

        self.rightPic = Image.open(self.optWindow.ui.importLineCyan.text())

        if hasattr(self.rightPic, "n_frames"): #and format == tif??
            for i in range(self.rightPic.n_frames):
                self.rightPic.seek(i)
                if self.rightPic.size < (200,200) :
                    self.rightPic.seek(i-1)
                    self.rightPic.save("demoRight.jpg")
                    self.demoRightPic = Image.open("demoRight.jpg")
                    self.demoRightExist = True 
                    self.rightPic.seek(0)
                    break

        elif self.rightPic.size[0] > self.rightPic.size[1] :
            self.demoRightPic = self.rightPic.resize((300,200))
        else :
            self.demoRightPic = self.rightPic.resize((200,300))

        draw = ImageDraw.Draw(self.demoRightPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        self.demoRightPic.save(self.temp)

        sceneCyan = QGraphicsScene()
        img = QImage(self.temp)
        sceneCyan.addPixmap(QPixmap.fromImage(img))
        self.optWindow.ui.graphicsViewCyan.setScene(sceneCyan)
        self.optWindow.ui.graphicsViewCyan.show()
        self.optWindow.ui.graphicsViewCyan.fitInView(self.optWindow.ui.graphicsViewCyan.sceneRect(), Qt.KeepAspectRatio)
        self.optWindow.ui.importButtonCyan.setEnabled(True)
        self.optWindow.ui.label_3.setEnabled(True)
        self.optWindow.ui.label_4.setEnabled(True)        
        self.optWindow.ui.boxMiroirCyan.setEnabled(True)        
        self.optWindow.ui.boxOrientationCyan.setEnabled(True)
        self.optWindow.ui.importDoneCyan.setStyleSheet("image: url(:/Anaglyph/Icons/redCross.png);")
        os.remove(self.temp)
        

        self.graphWindowRight = graphicsWindow("Image Droite")
        self.graphWindowRight.setWindowState(Qt.WindowMaximized)
        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height())
        self.graphWindowRight.ui.graphicsView.setGeometry(rect)
        self.graphWindowRight.ui.widget.setGeometry(rect)
        self.graphWindowRight.move(QPoint(self.screenRight.x(), self.screenRight.y()))

        pathPAR = self.optWindow.ui.importLineCyan.text().split(".")[0] + ".par"
        self.rightPictureManager = pictureManager(self.rightPic.size, pathPAR, "aa")


    #Fonction qui affiche les bonnes fenêtres selon la requête de l'utilisateur, soit 
    #les images superposer ou deux fenêtres séparées 
    #En fonction du module actif, certaines options sont rendu disponible pour 
    #l'utilisateur alors que d'autres deviennent bloquer.
    #Les paramètres de déplacement et de traitement d'image sont sauvegarder entre les deux modes
    #Donc si on retourne sur l'autre option, on retrouve nos paramètres sélectionnés auparavant   
    def loadWindows(self, value):

        self.graphWindowLeft.close()
        self.graphWindowRight.close()

        #Create DualManager, call getRect
        self.dualManager = dualManager(self.leftPictureManager, self.rightPictureManager, self.Z)
        self.leftRect, self.rightRect = self.dualManager.getRect()
        r = self.dualManager.calculateZ([9357,8860], [4861,8876])
        self.graphWindowLeft.cursorRectInit(self.screenLeft.width(), self.screenLeft.height())
        self.graphWindowRight.cursorRectInit(self.screenRight.width() + 11, self.screenRight.height() +5)
        a = self.leftPictureManager.pixelToCoord([9357,8860],self.Z)
        print(a)
        b = self.rightPictureManager.coordToPixel(a,self.Z)
        print(b)

        if value == 2 :
            ret = self.setSuper()

            if ret == 0 :
                self.enableOptionImage(False)
                self.optWindow.ui.groupBoxSuper.setEnabled(True)

                self.graphWindowLeft.setWindowTitle("Anaglyphe")
                self.graphWindowLeft.show()
                self.graphWindowLeft.ui.graphicsView.fitInView(self.rightRect,Qt.KeepAspectRatio)
                self.optWindow.activateWindow()
                self.anaglyphActivate = True
            
            #Les images ne sont pas de même taille, la superposition est impossible
            else : 
                self.enableOptionImage(False)
                self.optWindow.ui.groupBoxSuper.setEnabled(False)

        else : 
            
            if self.anaglyphActivate == True : 
                self.graphWindowLeft.ui.graphicsView.setScene(self.redViewScene)
                self.graphWindowLeft.setWindowTitle("Image Gauche")
                self.anaglyphActivate = False

            self.graphWindowLeft.show()
            self.graphWindowRight.show()
            self.graphWindowLeft.ui.graphicsView.fitInView(self.leftRect, Qt.KeepAspectRatio)
            self.graphWindowRight.ui.graphicsView.fitInView(self.rightRect, Qt.KeepAspectRatio)
            self.optWindow.activateWindow()
            self.enableOptionImage(True)
            self.optWindow.ui.groupBoxSuper.setEnabled(False)

            
            

    #Fonction permettant l'enregistrement de la photo superposer. La photo enregistrée prend en considération
    #le offset qui a pu être réalisé, le chemin proposé est celui de la photo de gauche
    def saveSuper(self) :
        path = self.path + "/Anaglyph"
        fname = QFileDialog.getSaveFileName(self.graphWindowRight, "Save your anaglyph picture", path, "Image (*.jpg)")[0]
        if fname: 
            self.currentSuperPic.save(fname)
        self.optWindow.activateWindow()



    #Fonction pour permettre l'utilisation des boutons d'option pour les fenêtres séparées 
    #Action peut être True ou False selon la permission que l'on veut donner
    def enableOptionImage(self, action):
        self.optWindow.ui.panButton.setEnabled(action)
        self.optWindow.ui.offsetButton.setEnabled(action)

    #Fonction pour zoom In sur les deux photos simultannément
    def mZoomIn(self) :
        self.graphWindowLeft.ui.graphicsView.scale(1.25, 1.25)
        self.graphWindowRight.ui.graphicsView.scale(1.25, 1.25)
        #self.redSizeX = int(self.redSizeX/1.25) 
        #self.redSizeY = int(self.redSizeY/1.25)
        #rect = QRectF(0,0, self.redSizeX, self.redSizeY)
        #self.graphWindowRight.ui.graphicsView.fitInView(rect,Qt.KeepAspectRatio)
        #self.graphWindowLeft.ui.graphicsView.fitInView(rect,Qt.KeepAspectRatio)

    #Fonction pour zoom Out sur les deux photos simultannément
    def mZoomOut(self):
        self.graphWindowLeft.ui.graphicsView.scale(0.8, 0.8)
        self.graphWindowRight.ui.graphicsView.scale(0.8, 0.8)
        #self.redSizeX = int(self.redSizeX/0.8) 
        #self.redSizeY = int(self.redSizeY/0.8)
        #rect = QRectF(0,0, self.redSizeX, self.redSizeY)
        #self.graphWindowRight.ui.graphicsView.fitInView(rect,Qt.KeepAspectRatio)
        #self.graphWindowLeft.ui.graphicsView.fitInView(rect,Qt.KeepAspectRatio)

    #Fonction pour permettre l'imporation de l'image sur le graphicsView
    #L'importation est généré par un thread pour permettre à l'application de rouler
    #correctement et ainsi continuer à répondre
    #Le thread est nécessaire puisqu'il réalise le traitement qui est lourd lorsque les 
    #fichiers importés sont gros
    def mImportRed(self):
        self.optWindow.ui.importDoneRed.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
        self.optWindow.ui.importButtonRed.setEnabled(False)
    
        self.tRed = threadPicture(self.leftPic, self.redOrientation, self.redMiroir, "tempLeft.jpg")
        self.tRed.finished.connect(self.threadRed)
        self.tRed.start()
       
    #Idem à mImportRed
    def mImportCyan(self):
        self.optWindow.ui.importDoneCyan.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
        self.optWindow.ui.importButtonCyan.setEnabled(False)
    
        self.tCyan = threadPicture(self.rightPic, self.cyanOrientation, self.cyanMiroir, "tempRight.jpg")
        self.tCyan.finished.connect(self.threadCyan)
        self.tCyan.start()

    #Fonction d'affichage d'une photo et connection vers les fonctions de souris liées
    #aux images. La scene est crée avec une grande taille pour permettre un pan "sans fin"
    #ce qui évite de perdre le décalage existant entre les photos 
    def threadRed(self):
        scene = QGraphicsScene() 

        scene.setSceneRect(-100000,-100000,200000,200000)
        self.redScene = scene.addPixmap(self.tRed.pix)
        
        del self.tRed


        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        self.redViewScene = self.graphWindowLeft.ui.graphicsView.scene()
        os.remove("tempLeft.jpg")
        self.graphWindowLeft.ui.widget.mouseMoveEvent = self.mMoveEvent
        self.graphWindowLeft.ui.widget.mousePressEvent = self.mPressEvent
        self.graphWindowLeft.ui.widget.wheelEvent = self.wheelEvent
        self.graphWindowLeft.ui.graphicsView.show()
        self.optWindow.ui.importDoneRed.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.optWindow.ui.importButtonRed.setEnabled(True)
        self.redName = True 
        if self.cyanName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)

    #idem a threadRed
    def threadCyan(self):
        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        self.cyanScene = scene.addPixmap(self.tCyan.pix)
        del self.tCyan
        
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        self.cyanViewScene = self.graphWindowRight.ui.graphicsView.scene()
        os.remove("tempRight.jpg")
        self.graphWindowRight.ui.widget.mouseMoveEvent = self.mMoveEvent
        self.graphWindowRight.ui.widget.mousePressEvent = self.mPressEvent
        self.graphWindowRight.ui.widget.wheelEvent = self.wheelEvent
        self.graphWindowRight.ui.graphicsView.show()
        self.optWindow.ui.importDoneCyan.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.optWindow.ui.importButtonCyan.setEnabled(True)
        self.cyanName = True 
        if self.redName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)
    
    #Désactive le offset pour activer le pan     
    def panClick(self):
        self.optWindow.ui.offsetButton.setChecked(False)

    #Désactive le pan pour activer le offset
    def offsetClick(self):
        self.optWindow.ui.panButton.setChecked(False)

    #Fonction qui réalise le pan et le offset selon le bouton sélectionné 
    def mMoveEvent(self, ev):
        if self.optWindow.ui.panButton.isChecked() :
            redView = self.graphWindowLeft.ui.graphicsView
            cyanView = self.graphWindowRight.ui.graphicsView
            delta = ev.pos() - self.panPosition
            redView.horizontalScrollBar().setValue(redView.horizontalScrollBar().value() - delta.x())
            redView.verticalScrollBar().setValue(redView.verticalScrollBar().value() - delta.y())
            cyanView.horizontalScrollBar().setValue(cyanView.horizontalScrollBar().value() + delta.x())
            cyanView.verticalScrollBar().setValue(cyanView.verticalScrollBar().value() - delta.y())
            self.panPosition = ev.pos()
        
        elif self.optWindow.ui.offsetButton.isChecked():
            redView = self.graphWindowLeft.ui.graphicsView
            cyanView = self.graphWindowRight.ui.graphicsView
            delta = ev.pos() - self.panPosition
            redView.horizontalScrollBar().setValue(redView.horizontalScrollBar().value() - delta.x())
            redView.verticalScrollBar().setValue(redView.verticalScrollBar().value() - delta.y())
            cyanView.horizontalScrollBar().setValue(cyanView.horizontalScrollBar().value() - delta.x())
            cyanView.verticalScrollBar().setValue(cyanView.verticalScrollBar().value() + delta.y())
            self.panPosition = ev.pos()

    #Fonction réalisé lors du click sur l'image, elle prend la première position de la souris
    def mPressEvent(self, ev):
        if self.optWindow.ui.panButton.isChecked() or self.optWindow.ui.offsetButton.isChecked() :
            self.panPosition = ev.pos()

    #Fonction pour zoom In/Out sur les photos avec la souris, elle zoom dans la 
    #direction de la souris 
    def wheelEvent(self, event):
        factor = 1.41 ** (event.angleDelta().y() / 240.0)
        redView = self.graphWindowLeft.ui.graphicsView
        cyanView = self.graphWindowRight.ui.graphicsView
        
        if self.optWindow.ctrlClick or self.graphWindowLeft.ctrlClick or self.graphWindowRight.ctrlClick :
            oldPos = self.graphWindowLeft.ui.graphicsView.mapToScene(event.pos())
            #print(oldPos)
            #print(event.pos())
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
                redView.horizontalScrollBar().setValue(redView.horizontalScrollBar().value() - 3)
                cyanView.horizontalScrollBar().setValue(cyanView.horizontalScrollBar().value() - 3)
            else :
                redView.horizontalScrollBar().setValue(redView.horizontalScrollBar().value() + 3)
                cyanView.horizontalScrollBar().setValue(cyanView.horizontalScrollBar().value() + 3)


if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())