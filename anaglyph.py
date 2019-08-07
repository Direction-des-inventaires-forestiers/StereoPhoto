from PIL import Image, ImageDraw, ImageOps
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_optionWindow import optionWindow
from ui_graphicsWindow import graphicsWindow 
from loadingPicture import threadPicture
import sys, os, time, math

#Permet l'ouverture avec PIL de fichier énorme!
Image.MAX_IMAGE_PIXELS = 1000000000 

class app(QApplication):

    #Initialisation de l'application, des variables
    #Connection entre les boutons du menu d'options (mOpt) et leur fonction attitrée
    #On fait apparaître le menu des options seul
    def __init__(self, argv):
        QApplication.__init__(self,argv)

        self.intRightScreen = 1
        self.intLeftScreen = 2

        self.screenRight = QApplication.desktop().screenGeometry(self.intRightScreen)
        self.screenLeft = QApplication.desktop().screenGeometry(self.intLeftScreen)
        
        self.temp = "temp.jpg"
        self.demoLeft = "demoLeft.jpg"
        self.demoRight = "demoRigh.jpg"
        self.redOrientation = 0
        self.cyanOrientation = 0
        self.redMiroir = 0
        self.cyanMiroir = 0
        self.redOffsetX = 0
        self.redOffsetY = 0
        self.cyanOffsetX = 0
        self.cyanOffsetY = 0
        self.superOffsetX = 0
        self.superOffsetY = 0
        self.offsetValCyan = 50
        self.offsetValRed = 50
        self.offsetValSuper = 50
        self.redName = False
        self.cyanName = False
        self.nbZoom = 0
        self.anaglyphActivate = False
        self.pan = False
        self.n = 0
        self.optWindow = optionWindow()

        self.optWindow.ui.boxMiroirRed.currentIndexChanged.connect(self.mMiroirRed)
        self.optWindow.ui.boxMiroirCyan.currentIndexChanged.connect(self.mMiroirCyan)
        self.optWindow.ui.boxOrientationRed.currentIndexChanged.connect(self.mOrientationRed)
        self.optWindow.ui.boxOrientationCyan.currentIndexChanged.connect(self.mOrientationCyan)
        self.optWindow.ui.importLineRed.textChanged.connect(self.mNewRedPic)
        self.optWindow.ui.importLineCyan.textChanged.connect(self.mNewCyanPic)
        self.optWindow.ui.importButtonRed.clicked.connect(self.mImportRed)
        self.optWindow.ui.importButtonCyan.clicked.connect(self.mImportCyan)
        
        self.optWindow.ui.upRed.clicked.connect(self.mUpRed)
        self.optWindow.ui.upCyan.clicked.connect(self.mUpCyan)
        self.optWindow.ui.downRed.clicked.connect(self.mDownRed)
        self.optWindow.ui.downCyan.clicked.connect(self.mDownCyan)
        self.optWindow.ui.leftRed.clicked.connect(self.mLeftRed)
        self.optWindow.ui.leftCyan.clicked.connect(self.mLeftCyan)
        self.optWindow.ui.rightRed.clicked.connect(self.mRightRed)
        self.optWindow.ui.rightCyan.clicked.connect(self.mRightCyan)
        self.optWindow.ui.origineRed.clicked.connect(self.mOrigineRed)
        self.optWindow.ui.origineCyan.clicked.connect(self.mOrigineCyan)
        self.optWindow.ui.offsetValRed.valueChanged.connect(self.mOffsetChangeRed)
        self.optWindow.ui.offsetValCyan.valueChanged.connect(self.mOffsetChangeCyan)

        self.optWindow.ui.zoomInButton.clicked.connect(self.mZoomIn)
        self.optWindow.ui.zoomOutButton.clicked.connect(self.mZoomOut)
        self.optWindow.ui.panButton.clicked.connect(self.panClick)
        self.optWindow.ui.offsetButton.clicked.connect(self.offsetClick)

        self.optWindow.ui.radioNoirBlanc.toggled.connect(self.setSuper)
        self.optWindow.ui.saveSuper.clicked.connect(self.saveSuper)
        self.optWindow.ui.upSuper.clicked.connect(self.mUpSuper)
        self.optWindow.ui.downSuper.clicked.connect(self.mDownSuper)
        self.optWindow.ui.leftSuper.clicked.connect(self.mLeftSuper)
        self.optWindow.ui.rightSuper.clicked.connect(self.mRightSuper)
        self.optWindow.ui.origineSuper.clicked.connect(self.mOrigineSuper)
        self.optWindow.ui.offsetValSuper.valueChanged.connect(self.mOffsetChangeSuper)

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
        try :
            os.remove(self.demoLeft)
        except :
            pass
        try :
            os.remove(self.demoRight)
        except :
            pass
        try :
            del self.graphWindowLeft
        except :
            pass
        try :
            del self.graphWindowRight
        except :
            pass
    
    #Fonction qui permet un traitement en couleur ou en noir et blanc sur les photos superposées 
    def setSuper(self):

        #Vérification que les photos sont de la même taille afin de les superposer
        if self.rightPic.size != self.leftPic.size :
            QMessageBox.information(self.optWindow, "Taille Différente", "Les images importées ne sont pas de la même taille. \nChoisir deux images de taille similaire ")
            return 1

        
        if self.optWindow.ui.radioCouleur.isChecked() :
            img_right_splited = self.rightPic.split()
            img_left_splited = self.offLeftPic.split()
            img_anaglyph_color = Image.merge('RGB', (img_left_splited[0], img_right_splited[1], img_right_splited[2]))
            img_anaglyph_color.save(self.temp)
            self.currentSuperPic = img_anaglyph_color 

        
        else : 
            img_right_grey = self.rightPic.convert('L')
            img_left_grey = self.offLeftPic.convert('L')
            img_anaglyph_grey = Image.merge('RGB', (img_left_grey, img_right_grey, img_right_grey))
            img_anaglyph_grey.save(self.temp)
            self.currentSuperPic = img_anaglyph_grey

        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        os.remove(self.temp)
        return 0


    #Fonction de traitement d'image pour modifier l'orientation
    #Quatre modes sont possible, soit paysage, portrait, paysage inversé et portrait inversé
    #La fonction nécessite un certain temps de calcul donc l'image ne doit pas être trop grosse
    def mOrientationRed(self, value):
        if value == 0 :
            self.mRedPicMiroir.save(self.temp)
            self.mRedPicOrientation = self.demoLeftPic

        elif value == 3 :
            a = np.array(self.demoLeftPic)
            a = np.rot90(a)
            self.mRedPicOrientation = Image.fromarray(a)
            a = np.array(self.mRedPicMiroir)
            a = np.rot90(a)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 2 :
            a = np.array(self.demoLeftPic)
            a = np.rot90(a,2)
            self.mRedPicOrientation = Image.fromarray(a)
            a = np.array(self.mRedPicMiroir)
            a = np.rot90(a,2)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 1 :
            a = np.array(self.demoLeftPic)
            a = np.rot90(a,3)
            self.mRedPicOrientation = Image.fromarray(a)
            a = np.array(self.mRedPicMiroir)
            a = np.rot90(a,3)
            im = Image.fromarray(a)
            im.save(self.temp)

        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.optWindow.ui.graphicsViewRed.setScene(scene)
        self.optWindow.ui.graphicsViewRed.fitInView(self.optWindow.ui.graphicsViewRed.sceneRect(), Qt.KeepAspectRatio)
        os.remove(self.temp)
        self.redOrientation = value

    
    #Idem à mOrientationRed
    def mOrientationCyan(self, value):
        if value == 0 :
            self.mCyanPicMiroir.save(self.temp)
            self.mCyanPicOrientation = self.demoRightPic

        elif value == 3 :
            a = np.array(self.demoRightPic)
            a = np.rot90(a)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 2 :
            a = np.array(self.demoRightPic)
            a = np.rot90(a,2)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a,2)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 1 :
            a = np.array(self.demoRightPic)
            a = np.rot90(a,3)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a,3)
            im = Image.fromarray(a)
            im.save(self.temp)

        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
        self.optWindow.ui.graphicsViewCyan.setScene(scene)
        self.optWindow.ui.graphicsViewCyan.fitInView(self.optWindow.ui.graphicsViewCyan.sceneRect(), Qt.KeepAspectRatio)
        os.remove(self.temp)
        self.cyanOrientation = value
        

    #Fonction de traitement d'image pour ajouter un effet mirroir à l'image
    #Deux modes sont possible, soit un effet mirroir à l'horizontal et un à la verticale
    #La fonction nécessite un certain temps de calcul donc l'image ne doit pas être trop grosse
    def mMiroirRed(self, value):
        if value == 0:
            self.mRedPicOrientation.save(self.temp)
            self.mRedPicMiroir = self.demoLeftPic
        
        elif value == 1 :
            a = np.array(self.demoLeftPic)
            a = np.fliplr(a)
            self.mRedPicMiroir = Image.fromarray(a)
            a = np.array(self.mRedPicOrientation)
            a = np.fliplr(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        elif value == 2 :
            a = np.array(self.demoLeftPic)
            a = np.flipud(a)
            self.mRedPicMiroir = Image.fromarray(a)
            a = np.array(self.mRedPicOrientation)
            a = np.flipud(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.optWindow.ui.graphicsViewRed.setScene(scene)
        self.optWindow.ui.graphicsViewRed.fitInView(self.optWindow.ui.graphicsViewRed.sceneRect(), Qt.KeepAspectRatio)
        os.remove(self.temp)
        self.redMiroir = value
        
    #Idem à mMiroirRed
    def mMiroirCyan(self,value):
        if value == 0:
            self.mCyanPicOrientation.save(self.temp)
            self.mCyanPicMiroir = self.demoRightPic
        
        elif value == 1 :
            a = np.array(self.demoRightPic)
            a = np.fliplr(a)
            self.mCyanPicMiroir = Image.fromarray(a)
            a = np.array(self.mCyanPicOrientation)
            a = np.fliplr(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        elif value == 2 :
            a = np.array(self.demoRightPic)
            a = np.flipud(a)
            self.mCyanPicMiroir = Image.fromarray(a)
            a = np.array(self.mCyanPicOrientation)
            a = np.flipud(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
        self.optWindow.ui.graphicsViewCyan.setScene(scene)
        self.optWindow.ui.graphicsViewCyan.fitInView(self.optWindow.ui.graphicsViewCyan.sceneRect(), Qt.KeepAspectRatio)
        os.remove(self.temp)
        self.cyanMiroir = value

    #Les 8 fonctions suivantes sont des fonctions de déplacement des images
    #Il est possible de déplacer la photo d'une valeur de offsetVal vers
    #le haut, le bas, la gauche ou la droite
    def mUpRed(self):
        self.redOffsetY += self.offsetValRed
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)
    
    def mUpCyan(self):
        self.cyanOffsetY += self.offsetValCyan
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mLeftRed(self):
        self.redOffsetX += self.offsetValRed
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mLeftCyan(self):
        self.cyanOffsetX += self.offsetValCyan
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mRightRed(self):
        self.redOffsetX -= self.offsetValRed
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mRightCyan(self):
        self.cyanOffsetX -= self.offsetValCyan
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mDownRed(self):
        self.redOffsetY -= self.offsetValRed
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mDownCyan(self):
        self.cyanOffsetY -= self.offsetValCyan
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    #Deux autres fonctions de déplacement
    #La photo est repositionné à son origine
    def mOrigineRed(self):
        self.redOffsetX = 0
        self.redOffsetY = 0
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mOrigineCyan(self):
        self.cyanOffsetX = 0
        self.cyanOffsetY = 0
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mOffsetChangeRed(self, value):
        self.offsetValRed = value
    
    def mOffsetChangeCyan(self, value):
        self.offsetValCyan = value


    #Fonction réaliser lorsqu'une photo est importée 
    #Elle permet de rendre le panneau de fonctionnalité accessible à l'utilisateur 
    #pour le traitement d'image ainsi que le repositionnement 
    #L'image est affiché sur une nouvelle fenêtre qui ne peut être que part 
    #la fermeture du mOpt 
    #Si une nouvelle photo est importée, l'ancienne est fermée 
    #L'image est aussi enregistré en différent format plus petit que l'orginal 
    def mNewRedPic(self) : 

        self.optWindow.ui.boxOrientationRed.currentIndexChanged.disconnect(self.mOrientationRed)
        self.optWindow.ui.boxOrientationRed.setCurrentIndex(0)
        self.optWindow.ui.boxOrientationRed.currentIndexChanged.connect(self.mOrientationRed)
        self.optWindow.ui.boxMiroirRed.currentIndexChanged.disconnect(self.mMiroirRed)
        self.optWindow.ui.boxMiroirRed.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirRed.currentIndexChanged.connect(self.mMiroirRed)
        
        self.redOrientation = 0
        self.redMiroir = 0
        self.redOffsetX = 0
        self.redOffsetY = 0
        self.superOffsetX = 0
        self.superOffsetY = 0  
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
                if self.leftPic.size < (100,100) :
                    self.leftPic.seek(i-1)
                    self.leftPic.save(self.demoLeft)
                    self.demoLeftPic = Image.open(self.demoLeft)
                    self.leftPic.seek(0)
                    break

        elif self.leftPic.size[0] > self.leftPic.size[1] :
            self.demoLeftPic = self.leftPic.resize((300,200))
        else :
            self.demoLeftPic = self.leftPic.resize((200,300))   

        draw = ImageDraw.Draw(self.demoLeftPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        self.demoLeftPic.save(self.temp)
        self.mRedPicOrientation = self.demoLeftPic
        self.mRedPicMiroir = self.demoLeftPic

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
        rect = QRect(0,0,self.screenLeft.width(),self.screenLeft.height()-40)
        self.graphWindowLeft.ui.graphicsView.setGeometry(rect)
        self.offLeftPic = self.leftPic

        fname = self.optWindow.ui.importLineRed.text()
        filename = "/" +  fname.split("/")[-1].split(".")[0]
        self.path = fname.partition(filename)[0]


    #Idem à mNewRedPic
    def mNewCyanPic(self):
        
        self.optWindow.ui.boxOrientationCyan.currentIndexChanged.disconnect(self.mOrientationCyan)
        self.optWindow.ui.boxOrientationCyan.setCurrentIndex(0)
        self.optWindow.ui.boxOrientationCyan.currentIndexChanged.connect(self.mOrientationCyan)
        self.optWindow.ui.boxMiroirCyan.currentIndexChanged.disconnect(self.mMiroirCyan)
        self.optWindow.ui.boxMiroirCyan.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirCyan.currentIndexChanged.connect(self.mMiroirCyan)

        self.cyanOrientation = 0
        self.cyanMiroir = 0
        self.cyanOffsetX = 0
        self.cyanOffsetY = 0
        self.superOffsetX = 0
        self.superOffsetY = 0
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
                if self.rightPic.size < (100,100) :
                    self.rightPic.seek(i-1)
                    self.rightPic.save(self.demoRight)
                    self.demoRightPic = Image.open(self.demoRight)
                    self.rightPic.seek(0)
                    break

        elif self.rightPic.size[0] > self.rightPic.size[1] :
            self.demoRightPic = self.rightPic.resize((300,200))
        else :
            self.demoRightPic = self.rightPic.resize((200,300))
       
        draw = ImageDraw.Draw(self.demoRightPic)
        draw.ellipse((20,20,60,60), fill="red", outline="white")
        self.demoRightPic.save(self.temp)
        self.mCyanPicOrientation = self.demoRightPic
        self.mCyanPicMiroir = self.demoRightPic

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
        rect = QRect(0,0,self.screenRight.width(),self.screenRight.height()-40)
        self.graphWindowRight.ui.graphicsView.setGeometry(rect)


    #Fonction qui affiche les bonnes fenêtres selon la requête de l'utilisateur, soit 
    #les images superposer ou deux fenêtres séparées 
    #En fonction du module actif, certaines options sont rendu disponible pour 
    #l'utilisateur alors que d'autres deviennent bloquer.
    #Les paramètres de déplacement et de traitement d'image sont sauvegarder entre les deux modes
    #Donc si on retourne sur l'autre option, on retrouve nos paramètres sélectionnés auparavant   
    def loadWindows(self, value):

        self.graphWindowLeft.close()
        self.graphWindowRight.close()

        if value == 2 :
            ret = self.setSuper()

            if ret == 0 :
                self.enableOptionImage(False)
                self.optWindow.ui.groupBoxSuper.setEnabled(True)

                self.graphWindowLeft.setWindowTitle("Anaglyphe")
                self.graphWindowLeft.show()
                self.graphWindowLeft.ui.graphicsView.fitInView(self.cyanRect,Qt.KeepAspectRatio)
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
            self.graphWindowLeft.ui.graphicsView.fitInView(self.redRect, Qt.KeepAspectRatio)
            self.graphWindowRight.ui.graphicsView.fitInView(self.cyanRect, Qt.KeepAspectRatio)
            self.optWindow.activateWindow()
            self.enableOptionImage(True)
            self.optWindow.ui.groupBoxSuper.setEnabled(False)
            
            

    #Fonction permettant l'enregistrement de la photo superposer. La photo enregistrée prend en considération
    #le offset qui a pu être réalisé 
    def saveSuper(self) :
        path = self.path + "/Anaglyph"
        fname = QFileDialog.getSaveFileName(self.graphWindowRight, "Save your anaglyph picture", path, "Image (*.jpg)")[0]
        if fname: 
            self.currentSuperPic.save(fname)
        self.optWindow.activateWindow()

    #Fonction de déplacement de la photo superposer. Déplacement possible vers le haut, le bas,
    #la gauche, la droite et un retour à l'origine
    def mUpSuper(self) :
        self.superOffsetY += self.offsetValSuper
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mDownSuper(self):
        self.superOffsetY -= self.offsetValSuper
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mLeftSuper(self):
        self.superOffsetX += self.offsetValSuper
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mRightSuper(self):
        self.superOffsetX -= self.offsetValSuper
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mOrigineSuper(self):
        self.superOffsetY = 0
        self.superOffsetX = 0
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mOffsetChangeSuper(self, value):
        self.offsetValSuper = value

    #Fonction pour permettre l'utilisation des boutons d'option pour les fenêtres séparées 
    #Action peut être True ou False selon la permission que l'on veut donner
    def enableOptionImage(self, action):

        self.optWindow.ui.rightCyan.setEnabled(action)
        self.optWindow.ui.leftCyan.setEnabled(action)
        self.optWindow.ui.downCyan.setEnabled(action)
        self.optWindow.ui.upCyan.setEnabled(action)
        self.optWindow.ui.origineCyan.setEnabled(action)
        self.optWindow.ui.label_8.setEnabled(action)
        self.optWindow.ui.offsetValCyan.setEnabled(action)
        
        self.optWindow.ui.rightRed.setEnabled(action)
        self.optWindow.ui.leftRed.setEnabled(action)
        self.optWindow.ui.downRed.setEnabled(action)
        self.optWindow.ui.upRed.setEnabled(action)
        self.optWindow.ui.origineRed.setEnabled(action)
        self.optWindow.ui.label_7.setEnabled(action)
        self.optWindow.ui.offsetValRed.setEnabled(action)

        self.optWindow.ui.zoomInButton.setEnabled(action)
        self.optWindow.ui.zoomOutButton.setEnabled(action)
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


    def mImportRed(self):
        self.optWindow.ui.importDoneRed.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
    
        self.tRed = threadPicture(self.leftPic, self.redOrientation, self.redMiroir, "tempLeft.jpg")
        self.tRed.finished.connect(self.threadRed)
        self.tRed.start()
       

    def mImportCyan(self):
        self.optWindow.ui.importDoneCyan.setStyleSheet("image: url(:/Anaglyph/Icons/loading.png);")
    
        self.tCyan = threadPicture(self.rightPic, self.cyanOrientation, self.cyanMiroir, "tempRight.jpg")
        self.tCyan.finished.connect(self.threadCyan)
        self.tCyan.start()

    #Fonction d'affichage d'une photo et ajustement pour que la photo soit affichée complètement
    #Apparition d'une nouvelle fenêtre qui ne peut être fermé que part la fermeture du mOpt
    def threadRed(self):
        scene = QGraphicsScene() 
        scene.setSceneRect(-100000,-100000,200000,200000)
        self.redScene = scene.addPixmap(self.tRed.pix)
        if self.redOrientation == 0 or self.redOrientation == 2 :
            self.redRect = QRectF(0,0,self.leftPic.size[0], self.leftPic.size[1])
        else :
            self. redRect =  QRectF(0,0,self.leftPic.size[1], self.leftPic.size[0])
        self.graphWindowLeft.ui.graphicsView.fitInView(self.redRect, Qt.KeepAspectRatio)
        self.redSizeX = self.leftPic.size[0]
        self.redSizeY = self.leftPic.size[1]
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        self.redViewScene = self.graphWindowLeft.ui.graphicsView.scene()
        self.graphWindowLeft.move(QPoint(self.screenLeft.x(), self.screenLeft.y()))
        os.remove("tempLeft.jpg")
        self.graphWindowLeft.ui.graphicsView.mouseMoveEvent = self.mMoveEvent
        self.graphWindowLeft.ui.graphicsView.mousePressEvent = self.mPressEvent
        self.graphWindowLeft.ui.graphicsView.show()
        self.optWindow.ui.importDoneRed.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.redName = True 
        if self.cyanName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)

    def threadCyan(self):
        scene = QGraphicsScene()
        scene.setSceneRect(-100000,-100000,200000,200000)
        self.cyanScene = scene.addPixmap(self.tCyan.pix)
        if self.cyanOrientation == 0 or self.cyanOrientation == 2 :
            self.cyanRect = QRectF(0,0,self.rightPic.size[0], self.rightPic.size[1])
        else : 
            self.cyanRect = QRectF(0,0,self.rightPic.size[1], self.rightPic.size[0])
        self.graphWindowRight.ui.graphicsView.fitInView(self.cyanRect, Qt.KeepAspectRatio)
        self.cyanSizeX = self.rightPic.size[0]
        self.cyanSizeY = self.rightPic.size[1]
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        self.cyanViewScene = self.graphWindowRight.ui.graphicsView.scene()
        self.graphWindowRight.move(QPoint(self.screenRight.x(), self.screenRight.y()))
        os.remove("tempRight.jpg")
        self.graphWindowRight.ui.graphicsView.mouseMoveEvent = self.mMoveEvent
        self.graphWindowRight.ui.graphicsView.mousePressEvent = self.mPressEvent
        self.graphWindowRight.ui.graphicsView.show()
        self.optWindow.ui.importDoneCyan.setStyleSheet("image: url(:/Anaglyph/Icons/greenCheck.png);")
        self.cyanName = True 
        if self.redName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)
        
    def panClick(self):
        self.optWindow.ui.offsetButton.setChecked(False)

    def offsetClick(self):
        self.optWindow.ui.panButton.setChecked(False)

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

    def mPressEvent(self, ev):
        if self.optWindow.ui.panButton.isChecked() or self.optWindow.ui.offsetButton.isChecked() :
            self.panPosition = ev.pos()

if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())