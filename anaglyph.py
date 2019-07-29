from PIL import Image, ImageQt
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_optionWindow import optionWindow
from ui_graphicsWindow import graphicsWindow 
import sys, os, time
import cv2

#Permet l'ouverture avec PIL de fichier énorme!
Image.MAX_IMAGE_PIXELS = 1000000000 

class app(QApplication):

    #Initialisation de l'application, des variables
    #Connection entre les boutons du menu d'options (mOpt) et leur fonction attitrée
    #On fait apparaître le menu des options seul
    def __init__(self, argv):
        QApplication.__init__(self,argv)
        
        self.temp = "temp.jpg"
        self.rougeOrientation = 0
        self.cyanOrientation = 0
        self.rougeMiroir = 0
        self.cyanMiroir = 0
        self.redOffsetX = 0
        self.redOffsetY = 0
        self.cyanOffsetX = 0
        self.cyanOffsetY = 0
        self.superOffsetX = 0
        self.superOffsetY = 0
        self.offsetVal = 5
        self.redName = False
        self.cyanName = False

        self.optWindow = optionWindow()

        self.optWindow.ui.boxMiroirRouge.currentIndexChanged.connect(self.mMiroirRouge)
        self.optWindow.ui.boxMiroirCyan.currentIndexChanged.connect(self.mMiroirCyan)
        self.optWindow.ui.boxOrientationRouge.currentIndexChanged.connect(self.mOrientationRouge)
        self.optWindow.ui.boxOrientationCyan.currentIndexChanged.connect(self.mOrientationCyan)
        self.optWindow.ui.importLineRed.textChanged.connect(self.mNewRedPic)
        self.optWindow.ui.importLineCyan.textChanged.connect(self.mNewCyanPic)
        
        self.optWindow.ui.upRed.clicked.connect(self.mUpRouge)
        self.optWindow.ui.upCyan.clicked.connect(self.mUpCyan)
        self.optWindow.ui.downRed.clicked.connect(self.mDownRouge)
        self.optWindow.ui.downCyan.clicked.connect(self.mDownCyan)
        self.optWindow.ui.leftRed.clicked.connect(self.mLeftRouge)
        self.optWindow.ui.leftCyan.clicked.connect(self.mLeftCyan)
        self.optWindow.ui.rightRed.clicked.connect(self.mRightRouge)
        self.optWindow.ui.rightCyan.clicked.connect(self.mRightCyan)
        self.optWindow.ui.origineRed.clicked.connect(self.mOrigineRed)
        self.optWindow.ui.origineCyan.clicked.connect(self.mOrigineCyan)
        self.optWindow.ui.zoomInRed.clicked.connect(self.mZoomInRed)
        self.optWindow.ui.zoomOutRed.clicked.connect(self.mZoomOutRed)

        self.optWindow.ui.radioNoirBlanc.toggled.connect(self.setSuper)
        self.optWindow.ui.saveSuper.clicked.connect(self.saveSuper)
        self.optWindow.ui.upSuper.clicked.connect(self.mUpSuper)
        self.optWindow.ui.downSuper.clicked.connect(self.mDownSuper)
        self.optWindow.ui.leftSuper.clicked.connect(self.mLeftSuper)
        self.optWindow.ui.rightSuper.clicked.connect(self.mRightSuper)
        self.optWindow.ui.origineSuper.clicked.connect(self.mOrigineSuper)

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
            del self.graphWindowLeft
        except :
            pass
        try :
            del self.graphWindowRight
        except :
            pass

    #Fonction d'affichage d'une photo et ajustement pour que la photo soit affichée complètement
    #Apparition d'une nouvelle fenêtre qui ne peut être fermé que part la fermeture du mOpt
    def initGraphicsWindow(self, gWindow, photo):
        gWindow.setWindowState(Qt.WindowMaximized)
        
        rect = QApplication.desktop().availableGeometry(-1)
        gWindow.ui.graphicsView.setGeometry(rect)
        
        scene = QGraphicsScene()
        
        #Cyan
        if photo == "Droite" :
            self.rightPic.save(self.temp)
            a = QImage(self.temp)
            self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
            self.cyanRect = QRectF(0,0,self.rightPic.size[0], self.rightPic.size[1]) 

        #Rouge
        elif photo == "Gauche" :
            self.leftPic.save(self.temp) 
            a = QImage(self.temp)
            self.redScene = scene.addPixmap(QPixmap.fromImage(a))
            self.redRect = QRectF(0,0,self.leftPic.size[0], self.leftPic.size[1])

        else :
            return
    
        gWindow.ui.graphicsView.setScene(scene)
        os.remove(self.temp)
        gWindow.ui.graphicsView.show()
        

    
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
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        os.remove(self.temp)
        return 0


    #Fonction de traitement d'image pour modifier l'orientation
    #Quatre modes sont possible, soit paysage, portrait, paysage inversé et portrait inversé
    #La fonction nécessite un certain temps de calcul donc l'image ne doit pas être trop grosse
    def mOrientationRouge(self, value):
        if value == 0 :
            self.mRougePicMiroir.save(self.temp)
            self.mRougePicOrientation = self.leftPic

        elif value == 1 :
            a = np.array(self.leftPic)
            a = np.rot90(a)
            self.mRougePicOrientation = Image.fromarray(a)
            a = np.array(self.mRougePicMiroir)
            a = np.rot90(a)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 2 :
            a = np.array(self.leftPic)
            a = np.rot90(a,2)
            self.mRougePicOrientation = Image.fromarray(a)
            a = np.array(self.mRougePicMiroir)
            a = np.rot90(a,2)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 3 :
            a = np.array(self.leftPic)
            a = np.rot90(a,3)
            self.mRougePicOrientation = Image.fromarray(a)
            a = np.array(self.mRougePicMiroir)
            a = np.rot90(a,3)
            im = Image.fromarray(a)
            im.save(self.temp)

        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.redScene = scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)
        os.remove(self.temp)
        self.rougeOrientation = value

    
    #Idem à mOrientationRouge
    def mOrientationCyan(self, value):
        if value == 0 :
            self.mCyanPicMiroir.save(self.temp)
            self.mCyanPicOrientation = self.rightPic

        elif value == 1 :
            a = np.array(self.rightPic)
            a = np.rot90(a)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 2 :
            a = np.array(self.rightPic)
            a = np.rot90(a,2)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a,2)
            im = Image.fromarray(a)
            im.save(self.temp)

        elif value == 3 :
            a = np.array(self.rightPic)
            a = np.rot90(a,3)
            self.mCyanPicOrientation = Image.fromarray(a)
            a = np.array(self.mCyanPicMiroir)
            a = np.rot90(a,3)
            im = Image.fromarray(a)
            im.save(self.temp)

        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        self.cyanScene.setOffset(self.cyanOffsetX ,self.cyanOffsetY)
        os.remove(self.temp)
        self.cyanOrientation = value
        

    #Fonction de traitement d'image pour ajouter un effet mirroir à l'image
    #Deux modes sont possible, soit un effet mirroir à l'horizontal et un à la verticale
    #La fonction nécessite un certain temps de calcul donc l'image ne doit pas être trop grosse
    def mMiroirRouge(self, value):
        if value == 0:
            self.mRougePicOrientation.save(self.temp)
            self.mRougePicMiroir = self.leftPic
        
        elif value == 1 :
            a = np.array(self.leftPic)
            a = np.fliplr(a)
            self.mRougePicMiroir = Image.fromarray(a)
            a = np.array(self.mRougePicOrientation)
            a = np.fliplr(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        elif value == 2 :
            a = np.array(self.leftPic)
            a = np.flipud(a)
            self.mRougePicMiroir = Image.fromarray(a)
            a = np.array(self.mRougePicOrientation)
            a = np.flipud(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.redScene = scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowLeft.ui.graphicsView.setScene(scene)
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)
        os.remove(self.temp)
        self.rougeMiroir = value
        
    #Idem à mMiroirRouge
    def mMiroirCyan(self,value):
        if value == 0:
            self.mCyanPicOrientation.save(self.temp)
            self.mCyanPicMiroir = self.rightPic
        
        elif value == 1 :
            a = np.array(self.rightPic)
            a = np.fliplr(a)
            self.mCyanPicMiroir = Image.fromarray(a)
            a = np.array(self.mCyanPicOrientation)
            a = np.fliplr(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        elif value == 2 :
            a = np.array(self.rightPic)
            a = np.flipud(a)
            self.mCyanPicMiroir = Image.fromarray(a)
            a = np.array(self.mCyanPicOrientation)
            a = np.flipud(a)
            im = Image.fromarray(a)
            im.save(self.temp)
        
        scene = QGraphicsScene()
        a = QImage(self.temp)
        self.cyanScene = scene.addPixmap(QPixmap.fromImage(a))
        self.graphWindowRight.ui.graphicsView.setScene(scene)
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)
        os.remove(self.temp)
        self.cyanMiroir = value

    #Les 8 fonctions suivantes sont des fonctions de déplacement des images
    #Il est possible de déplacer la photo d'une valeur de offsetVal vers
    #le haut, le bas, la gauche ou la droite
    def mUpRouge(self):
        self.redOffsetY += self.offsetVal
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)
    
    def mUpCyan(self):
        self.cyanOffsetY += self.offsetVal
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mLeftRouge(self):
        self.redOffsetX += self.offsetVal
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mLeftCyan(self):
        self.cyanOffsetX += self.offsetVal
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mRightRouge(self):
        self.redOffsetX -= self.offsetVal
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mRightCyan(self):
        self.cyanOffsetX -= self.offsetVal
        self.cyanScene.setOffset(self.cyanOffsetX, self.cyanOffsetY)

    def mDownRouge(self):
        self.redOffsetY -= self.offsetVal
        self.redScene.setOffset(self.redOffsetX, self.redOffsetY)

    def mDownCyan(self):
        self.cyanOffsetY -= self.offsetVal
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


    #Fonction réaliser lorsqu'une photo est importée 
    #Elle permet de rendre le panneau de fonctionnalité accessible à l'utilisateur 
    #pour le traitement d'image ainsi que le repositionnement 
    #L'image est affiché sur une nouvelle fenêtre qui ne peut être que part 
    #la fermeture du mOpt 
    #Si une nouvelle photo est importée, l'ancienne est fermée 
    def mNewRedPic(self) : 
        
        self.optWindow.ui.boxOrientationRouge.currentIndexChanged.disconnect(self.mOrientationRouge)
        self.optWindow.ui.boxOrientationRouge.setCurrentIndex(0)
        self.optWindow.ui.boxOrientationRouge.currentIndexChanged.connect(self.mOrientationRouge)
        self.optWindow.ui.boxMiroirRouge.currentIndexChanged.disconnect(self.mMiroirRouge)
        self.optWindow.ui.boxMiroirRouge.setCurrentIndex(0)
        self.optWindow.ui.boxMiroirRouge.currentIndexChanged.connect(self.mMiroirRouge)
        
        self.rougeOrientation = 0
        self.rougeMiroir = 0
        self.redOffsetX = 0
        self.redOffsetY = 0
        self.superOffsetX = 0
        self.superOffsetY = 0         

        try :
            del self.graphWindowLeft
            self.graphWindowRight.close()
        except :
            pass

        #Here
        img = cv2.imread(self.optWindow.ui.importLineRed.text())
        layer = img.copy()
        gaussian_pyramid = [layer]
        for i in range(3):
            layer = cv2.pyrDown(layer)
            gaussian_pyramid.append(layer)

        rgbLayer = cv2.cvtColor(layer, cv2.COLOR_BGR2RGB)
        self.leftPic = Image.fromarray(rgbLayer)
        
        #self.leftPic = Image.open(self.optWindow.ui.importLineRed.text())
        self.graphWindowLeft = graphicsWindow("Image Gauche")
        self.initGraphicsWindow(self.graphWindowLeft,"Gauche")
        self.mRougePicOrientation = self.leftPic
        self.mRougePicMiroir = self.leftPic
        self.offLeftPic = self.leftPic

        fname = self.optWindow.ui.importLineRed.text()
        filename = "/" +  fname.split("/")[-1].split(".")[0]
        self.path = fname.partition(filename)[0]
        
        self.redName = True 
        if self.cyanName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)
        
        self.optWindow.activateWindow()


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

        try :
            del self.graphWindowRight
            self.graphWindowLeft.close()
        except :
            pass
        
        self.rightPic = Image.open(self.optWindow.ui.importLineCyan.text())
        self.graphWindowRight = graphicsWindow("Image Droite") 
        self.initGraphicsWindow(self.graphWindowRight, "Droite")
        self.mCyanPicOrientation = self.rightPic 
        self.mCyanPicMiroir = self.rightPic

        self.cyanName = True 
        if self.redName == True :
            self.optWindow.ui.affichageButton.setEnabled(True)

        self.optWindow.activateWindow()
    

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

                self.graphWindowRight.setWindowTitle("Anaglyphe")
                self.graphWindowRight.show()
                self.graphWindowRight.ui.graphicsView.fitInView(self.cyanRect,Qt.KeepAspectRatio)
                self.optWindow.activateWindow()
            
            #Les images ne sont pas de même taille, la superposition est impossible
            else : 
                self.enableOptionImage(False)
                self.optWindow.ui.groupBoxSuper.setEnabled(False)


        else : 
            self.rightPic.save(self.temp) 
            scene = QGraphicsScene()
            a = QImage(self.temp)
            scene.addPixmap(QPixmap.fromImage(a))
            self.graphWindowRight.ui.graphicsView.setScene(scene)
            os.remove(self.temp)

            self.enableOptionImage(True)
            self.optWindow.ui.groupBoxSuper.setEnabled(False)
            
            self.mOrientationCyan(self.cyanOrientation)
            self.mOrientationRouge(self.rougeOrientation)
            self.mMiroirCyan(self.cyanMiroir)
            self.mMiroirRouge(self.rougeMiroir)
            self.graphWindowRight.setWindowTitle("Image Droite")
            self.graphWindowLeft.show()
            self.graphWindowRight.show()
            self.graphWindowRight.ui.graphicsView.fitInView(self.cyanRect,Qt.KeepAspectRatio)
            self.graphWindowLeft.ui.graphicsView.fitInView(self.redRect,Qt.KeepAspectRatio)
            self.optWindow.activateWindow()

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
        self.superOffsetY += self.offsetVal
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mDownSuper(self):
        self.superOffsetY -= self.offsetVal
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mLeftSuper(self):
        self.superOffsetX += self.offsetVal
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mRightSuper(self):
        self.superOffsetX -= self.offsetVal
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    def mOrigineSuper(self):
        self.superOffsetY = 0
        self.superOffsetX = 0
        self.offLeftPic = self.leftPic.transform(self.leftPic.size, Image.AFFINE, (1,0,self.superOffsetX,0,1,self.superOffsetY))
        self.setSuper()

    #Fonction pour permettre l'utilisation des boutons d'option pour les fenêtres séparées 
    #Action peut être True ou False selon la permission que l'on veut donner
    def enableOptionImage(self, action):
        self.optWindow.ui.rightCyan.setEnabled(action)
        self.optWindow.ui.leftCyan.setEnabled(action)
        self.optWindow.ui.downCyan.setEnabled(action)
        self.optWindow.ui.upCyan.setEnabled(action)
        self.optWindow.ui.origineCyan.setEnabled(action)        
        self.optWindow.ui.label_3.setEnabled(action)
        self.optWindow.ui.label_4.setEnabled(action)
        self.optWindow.ui.boxMiroirCyan.setEnabled(action)        
        self.optWindow.ui.boxOrientationCyan.setEnabled(action)
        self.optWindow.ui.zoomInCyan.setEnabled(action)
        self.optWindow.ui.zoomOutCyan.setEnabled(action)

        self.optWindow.ui.boxOrientationRouge.setEnabled(action)
        self.optWindow.ui.label.setEnabled(action)
        self.optWindow.ui.label_2.setEnabled(action)
        self.optWindow.ui.boxMiroirRouge.setEnabled(action)
        self.optWindow.ui.rightRed.setEnabled(action)
        self.optWindow.ui.leftRed.setEnabled(action)
        self.optWindow.ui.downRed.setEnabled(action)
        self.optWindow.ui.upRed.setEnabled(action)
        self.optWindow.ui.origineRed.setEnabled(action)
        self.optWindow.ui.zoomInRed.setEnabled(action)
        self.optWindow.ui.zoomOutRed.setEnabled(action)


    def mZoomInRed(self) : 
        rect = QRectF(0,0, int(self.leftPic.size[0]/1.25), int(self.leftPic.size[1]/1.25))
        self.graphWindowLeft.ui.graphicsView.fitInView(rect,Qt.KeepAspectRatio)
        #factor = 1.25
        #self.graphWindowLeft.ui.graphicsView.scale(factor,factor)

    def mZoomOutRed(self):
        factor = 0.8
        self.graphWindowLeft.ui.graphicsView.scale(factor,factor)


if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())