from PIL import Image, ImageDraw, ImageEnhance
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_Rehaussement import colorWindow, tableModel
import sys, os, time, gdal

Image.MAX_IMAGE_PIXELS = 1000000000 

acceptType = ["jpg", "jpeg", "tiff", "tif", "bmp", "png"]

class app(QApplication):

    def __init__(self, argv):
        QApplication.__init__(self,argv)
        self.colorWindow = colorWindow()
        self.colorWindow.ui.lineEdit.textChanged.connect(self.importFile)
        self.temp = "temp.jpg"
        self.colorWindow.ui.graphicsView.show()
        self.colorWindow.show()
        self.firstPicture = True
        self.switchActivate = False
        self.threadInProcess = False

        self.colorWindow.ui.saveAll.clicked.connect(self.saveAllPicture)
        

    def importFile(self):
        success = True
        self.colorWindow.ui.statusbar.clearMessage()
        self.path = self.colorWindow.ui.lineEdit.text()

        if not self.threadInProcess : 
            self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")


        if os.path.isfile(self.path) :
            self.colorWindow.ui.statusbar.showMessage("L'élément importé n'est pas un dossier", 20000)
            success = False
            
        else :
            f = []
            self.listPicture = []
            for (dirpath, dirnames, filenames) in os.walk(self.path):
                f.extend(filenames)
                break
            count = 0
            for i in f : 
                if i.split(".")[-1] in acceptType:
                    self.listPicture.append(i)
                    count += 1 

            if count == 0 : 
                self.colorWindow.ui.statusbar.showMessage("Le dossier ne possède aucune photo de format valide", 20000)
                success = False


        if success == False : 
            self.colorWindow.ui.lineEdit.textChanged.disconnect(self.importFile)
            self.colorWindow.ui.lineEdit.clear()
            self.colorWindow.ui.lineEdit.textChanged.connect(self.importFile)
            if self.switchActivate : 
                if self.firstPicture == False : 
                    self.setConnection(False)
                    self.firstPicture = True
                self.resetBox()
                self.colorWindow.ui.tableView.selectionModel().currentRowChanged.disconnect(self.switchPicture)
                model = tableModel([])
                self.colorWindow.ui.tableView.setModel(model)
                scene = QGraphicsScene()
                self.colorWindow.ui.graphicsView.setScene(scene)
                self.switchActivate = False
            self.saveButtonState(False)
            return
    
        self.listPicture.sort()
        model = tableModel(self.listPicture)
        self.colorWindow.ui.tableView.setModel(model)
        self.colorWindow.ui.tableView.setColumnWidth(0,310)
        self.colorWindow.ui.tableView.selectRow(0)
        self.colorWindow.ui.tableView.selectionModel().currentRowChanged.connect(self.switchPicture)
        self.switchActivate = True
        self.resetBox()

        if not self.threadInProcess : 
            self.saveButtonState(True)
            

        currentPath = self.path + "/" + self.listPicture[0]
        self.loadPicture(currentPath)

    def loadPicture(self, path) : 
        self.picture = Image.open(path)

        if hasattr(self.picture, "n_frames") and self.picture.n_frames > 4:
            self.picture.seek(4)

        elif self.picture.size[0] > self.picture.size[1] :
            self.picture = self.picture.resize((1000,700))
        else :
            self.picture = self.picture.resize((700,1000))

        h = self.picture.histogram()
        a = sum(h)
        cutValue = [round(a*0.05/3), round(a*0.95/3), round(a*1.05/3), round(a*1.95/3), round(a*2.05/3), round(a*2.95/3)]
        self.pixValue = []
        b = 0
        c = 0
        for i in range(len(h)):
            b += h[i] 
            if b > cutValue[c] : 
                self.pixValue.append(i)
                c += 1
                if c == 6 :
                    break
        self.picture.save(self.temp)
        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.colorWindow.ui.graphicsView.setScene(scene)
        os.remove(self.temp)

        self.colorWindow.ui.graphicsView.fitInView(self.colorWindow.ui.graphicsView.sceneRect(), Qt.KeepAspectRatio)

        if self.firstPicture : 
            self.setConnection(True)
            self.colorWindow.ui.buttonBoxReset.clicked.connect(self.reset)
            self.firstPicture = False
            self.reset()

    def switchPicture(self, value) :
        self.colorWindow.ui.tableView.selectionModel().currentRowChanged.disconnect(self.switchPicture)
        currentPath = self.path + "/" + self.listPicture[value.row()]
        self.loadPicture(currentPath)
        self.enhancePicture()
        self.colorWindow.ui.tableView.selectRow(value.row())
        self.colorWindow.ui.tableView.selectionModel().currentRowChanged.connect(self.switchPicture)
        

    def enhancePicture(self):
        p = self.picture

        if self.colorWindow.ui.spinBoxContrast.value() != 0 :
            p = ImageEnhance.Contrast(p).enhance(self.colorWindow.ui.spinBoxContrast.value() + 1)

        if self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
            p = ImageEnhance.Brightness(p).enhance(self.colorWindow.ui.spinBoxLuminosite.value() + 1)

        if self.colorWindow.ui.spinBoxSaturation.value() != 0 :    
            p = ImageEnhance.Color(p).enhance(self.colorWindow.ui.spinBoxSaturation.value() + 1)

        if self.colorWindow.ui.spinBoxNettete.value() != 0 :
            p = ImageEnhance.Sharpness(p).enhance(self.colorWindow.ui.spinBoxNettete.value() + 1)
        
        s = p.split()

        if self.colorWindow.ui.checkBoxMinMax.checkState() == Qt.Checked : 
            mr = s[0].point(self.redEqualization)
            mg = s[1].point(self.greenEqualization)
            mb = s[2].point(self.blueEqualization)

            if self.colorWindow.ui.spinBoxRed.value() != 0 :
                r = mr.point(self.redEnhance)
            else :
                r = mr

            if self.colorWindow.ui.spinBoxGreen.value() != 0 :
                g = mg.point(self.greenEnhance)
            else : 
                g = mg

            if self.colorWindow.ui.spinBoxBlue.value() != 0 :
                b = mb.point(self.blueEnhance)
            else :
                b = mb    
        
        else :
            if self.colorWindow.ui.spinBoxRed.value() != 0 :
                r = s[0].point(self.redEnhance)
            else :
                r = s[0]

            if self.colorWindow.ui.spinBoxGreen.value() != 0 :
                g = s[1].point(self.greenEnhance)
            else : 
                g = s[1]

            if self.colorWindow.ui.spinBoxBlue.value() != 0 :
                b = s[2].point(self.blueEnhance)
            else :
                b = s[2]

        p = Image.merge("RGB", (r,g,b))

        p.save(self.temp)
        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.colorWindow.ui.graphicsView.setScene(scene)
        os.remove(self.temp)

    def reset(self) : 
        self.setConnection(False)
        self.resetBox()
        self.enhancePicture()
        self.setConnection(True)

    def redEnhance(self, value):
        return value + self.colorWindow.ui.spinBoxRed.value()
    
    def greenEnhance(self, value):
        return value + self.colorWindow.ui.spinBoxGreen.value()

    def blueEnhance(self, value):
        return value + self.colorWindow.ui.spinBoxBlue.value()

    def redEqualization(self,value):
        oldMin = self.pixValue[0]
        oldMax = self.pixValue[1]
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    def greenEqualization(self,value):
        oldMin = self.pixValue[2] - 256
        oldMax = self.pixValue[3] - 256
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    def blueEqualization(self,value):
        oldMin = self.pixValue[4] - 512
        oldMax = self.pixValue[5] - 512
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    def setConnection(self, enable) : 
        if enable : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxSaturation.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxNettete.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxRed.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxGreen.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.spinBoxBlue.valueChanged.connect(self.enhancePicture)
            self.colorWindow.ui.checkBoxMinMax.stateChanged.connect(self.enhancePicture)

        else : 
            self.colorWindow.ui.spinBoxContrast.valueChanged.disconnect(self.enhancePicture)
            self.colorWindow.ui.spinBoxLuminosite.valueChanged.disconnect(self.enhancePicture)   
            self.colorWindow.ui.spinBoxSaturation.valueChanged.disconnect(self.enhancePicture)   
            self.colorWindow.ui.spinBoxNettete.valueChanged.disconnect(self.enhancePicture)  
            self.colorWindow.ui.spinBoxRed.valueChanged.disconnect(self.enhancePicture) 
            self.colorWindow.ui.spinBoxGreen.valueChanged.disconnect(self.enhancePicture) 
            self.colorWindow.ui.spinBoxBlue.valueChanged.disconnect(self.enhancePicture) 
            self.colorWindow.ui.checkBoxMinMax.stateChanged.disconnect(self.enhancePicture)

    def resetBox(self) : 
        self.colorWindow.ui.spinBoxContrast.setValue(0)
        self.colorWindow.ui.spinBoxLuminosite.setValue(0)   
        self.colorWindow.ui.spinBoxSaturation.setValue(0)   
        self.colorWindow.ui.spinBoxNettete.setValue(0)  
        self.colorWindow.ui.spinBoxRed.setValue(0) 
        self.colorWindow.ui.spinBoxGreen.setValue(0) 
        self.colorWindow.ui.spinBoxBlue.setValue(0) 
        self.colorWindow.ui.checkBoxMinMax.setCheckState(0)

    def saveButtonState(self, state): 
        self.colorWindow.ui.saveAll.setEnabled(state)
        self.colorWindow.ui.saveCurrent.setEnabled(state)
        self.colorWindow.ui.saveSelection.setEnabled(state)
    
    def saveAllPicture(self) : 

        con = self.colorWindow.ui.spinBoxContrast.value()
        lum = self.colorWindow.ui.spinBoxLuminosite.value()   
        sat = self.colorWindow.ui.spinBoxSaturation.value()   
        net = self.colorWindow.ui.spinBoxNettete.value()  
        red = self.colorWindow.ui.spinBoxRed.value() 
        gre = self.colorWindow.ui.spinBoxGreen.value() 
        blu = self.colorWindow.ui.spinBoxBlue.value() 
        bmm = self.colorWindow.ui.checkBoxMinMax.checkState()

        listParam = [con, lum, sat, net, red, gre, blu, bmm]
        self.t = threadSave(self.path, self.listPicture, listParam)
        self.nbPicture = len(self.listPicture)
        self.threadPath = self.path
        self.t.iterationDone.connect(self.iterationOnSaving)
        self.t.finished.connect(self.threadingDone)
        self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/loading.png);")
        self.saveButtonState(False)
        self.threadInProcess = True
        self.t.start()

        #Bouton Save Current ---> Idée sauvegarder sélection ouvrir une fenetre avec des checkboxs pour choisir les photos que l'on désire 
        
    def iterationOnSaving(self):
        print("A picture was saved")
        #Afficher nombre de photo traiter sur nombre total (rafraichir la string)

    @pyqtSlot()
    def go2Cross(self):
        self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/redCross.png);")

    def threadingDone(self):
        self.colorWindow.ui.saveImage.setStyleSheet("image: url(:/Rehaussement/Icons/greenCheck.png);")
        self.threadInProcess = False
        if self.colorWindow.ui.lineEdit.text() != "":
            self.saveButtonState(True)
            if self.threadPath != self.path :
                QTimer.singleShot(5000, self.go2Cross)
        else : 
            QTimer.singleShot(5000, self.go2Cross)



class threadSave(QThread):
    iterationDone = pyqtSignal()
    def __init__(self, path, listPicture, listParam):
        QThread.__init__(self)
        self.path = path
        self.listPicture = listPicture
        self.listParam = listParam

    def run(self):

        newDir = self.path + "/Photo_Rehausser"
        currentDir = newDir
        i = 2
        while(1): 
            try : 
                os.mkdir(newDir)
                newDir += "/"
                break
            except : 
                s = "_version" + str(i)
                newDir = currentDir + s
                i += 1 

        for pic in self.listPicture : 
            currentPath = self.path + "/" + pic
            myImage = Image.open(currentPath)
            self.pixValue = []
            if self.listParam[-1] == Qt.Checked : 
                h = myImage.histogram()
                a = sum(h)
                cutValue = [round(a*0.05/3), round(a*0.95/3), round(a*1.05/3), round(a*1.95/3), round(a*2.05/3), round(a*2.95/3)]
                b = 0
                c = 0
                for i in range(len(h)):
                    b += h[i] 
                    if b > cutValue[c] : 
                        self.pixValue.append(i)
                        c += 1
                        if c == 6 :
                            break
            
            if hasattr(myImage, "n_frames") :
                firstPicture = True
                for i in range(myImage.n_frames) : 
                    myImage.seek(i)
                    toSave = self.enhance(myImage)
                    
                    newPath = newDir + pic
                    
                    driver = gdal.GetDriverByName("GTiff")
                    if firstPicture :
                        fileout = driver.Create(newPath, myImage.size[0], myImage.size[1], 3 ,gdal.GDT_Byte, ["COMPRESS=JPEG", "PHOTOMETRIC=YCBCR"])
                        firstPicture = False
                    else : 
                        fileout = driver.Create(newPath, myImage.size[0], myImage.size[1], 3 ,gdal.GDT_Byte, ["APPEND_SUBDATASET=YES", "COMPRESS=JPEG", "PHOTOMETRIC=YCBCR"])
                    fileout.GetRasterBand(1).WriteArray(np.array(toSave[0], dtype=np.uint8))
                    fileout.GetRasterBand(2).WriteArray(np.array(toSave[1], dtype=np.uint8))
                    fileout.GetRasterBand(3).WriteArray(np.array(toSave[2], dtype=np.uint8))
                    fileout.FlushCache()
                    fileout = None
                self.iterationDone.emit()
 
            else : 
                toSave = self.enhance(myImage)
                newPath = newDir + pic
                img = Image.merge("RGB", (toSave[0],toSave[1],toSave[2]))
                img.save(newPath)
                self.iterationDone.emit()

            myImage.close()

    def enhance(self, img):
        p = img
        if self.listParam[0] != 0 :
            p = ImageEnhance.Contrast(p).enhance(self.listParam[0] + 1)

        if self.listParam[1] != 0 :
            p = ImageEnhance.Brightness(p).enhance(self.listParam[1] + 1)

        if self.listParam[2] != 0 :    
            p = ImageEnhance.Color(p).enhance(self.listParam[2] + 1)

        if self.listParam[3] != 0 :
            p = ImageEnhance.Sharpness(p).enhance(self.listParam[3] + 1)
        
        s = p.split()
        
        if len(self.pixValue) == 6 : 
            mr = s[0].point(self.redEqualization)
            mg = s[1].point(self.greenEqualization)
            mb = s[2].point(self.blueEqualization)

            if self.listParam[4] != 0 :
                r = mr.point(self.redEnhance)
            else :
                r = mr

            if self.listParam[5] != 0 :
                g = mg.point(self.greenEnhance)
            else : 
                g = mg

            if self.listParam[6] != 0 :
                b = mb.point(self.blueEnhance)
            else :
                b = mb    
        
        else :
            if self.listParam[4] != 0 :
                r = s[0].point(self.redEnhance)
            else :
                r = s[0]

            if self.listParam[5] != 0 :
                g = s[1].point(self.greenEnhance)
            else : 
                g = s[1]

            if self.listParam[6] != 0 :
                b = s[2].point(self.blueEnhance)
            else :
                b = s[2]

        ret = [r,g,b]
        return ret
    
    def redEnhance(self, value):
        return value + self.listParam[4]
    
    def greenEnhance(self, value):
        return value + self.listParam[5]

    def blueEnhance(self, value):
        return value + self.listParam[6]

    def redEqualization(self,value):
        oldMin = self.pixValue[0]
        oldMax = self.pixValue[1]
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    def greenEqualization(self,value):
        oldMin = self.pixValue[2] - 256
        oldMax = self.pixValue[3] - 256
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)

    def blueEqualization(self,value):
        oldMin = self.pixValue[4] - 512
        oldMax = self.pixValue[5] - 512
        newMin = 0 
        newMax = 255
        v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
        return round(v)


if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())
    

