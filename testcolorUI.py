from PIL import Image, ImageDraw, ImageEnhance
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ui_colorWindow import colorWindow
import sys, os, time

Image.MAX_IMAGE_PIXELS = 1000000000 

class app(QApplication):

    def __init__(self, argv):
        QApplication.__init__(self,argv)
        self.colorWindow = colorWindow()
        
        
        self.temp = "temp.jpg"
        path = "//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Paire_2/Q16069_420_NIR.tif"

        self.picture = Image.open(path)
        self.picture.seek(4)

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

        self.colorWindow.ui.spinBoxContrast.valueChanged.connect(self.enhancePicture)
        self.colorWindow.ui.spinBoxLuminosite.valueChanged.connect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxSaturation.valueChanged.connect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxNettete.valueChanged.connect(self.enhancePicture)  
        self.colorWindow.ui.spinBoxRed.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxGreen.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxBlue.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.checkBoxMinMax.stateChanged.connect(self.enhancePicture)
        
        self.colorWindow.ui.buttonBoxReset.clicked.connect(self.reset)

        self.colorWindow.ui.graphicsView.show()
        self.colorWindow.show()

        self.colorWindow.ui.graphicsView.fitInView(self.colorWindow.ui.graphicsView.sceneRect(), Qt.KeepAspectRatio)
        
    def enhancePicture(self):
        p = ImageEnhance.Contrast(self.picture).enhance(self.colorWindow.ui.spinBoxContrast.value() + 1)
        p = ImageEnhance.Brightness(p).enhance(self.colorWindow.ui.spinBoxLuminosite.value() + 1)
        p = ImageEnhance.Color(p).enhance(self.colorWindow.ui.spinBoxSaturation.value() + 1)
        p = ImageEnhance.Sharpness(p).enhance(self.colorWindow.ui.spinBoxNettete.value() + 1)
        s = p.split()
        if self.colorWindow.ui.checkBoxMinMax.checkState() == Qt.Checked : 
            mr = s[0].point(self.redEqualization)
            mg = s[1].point(self.greenEqualization)
            mb = s[2].point(self.blueEqualization)
            r = mr.point(self.redEnhance)
            g = mg.point(self.greenEnhance)
            b = mb.point(self.blueEnhance)
        else :
            r = s[0].point(self.redEnhance)
            g = s[1].point(self.greenEnhance)
            b = s[2].point(self.blueEnhance)
        p = Image.merge("RGB", (r,g,b))

        p.save(self.temp)
        scene = QGraphicsScene()
        a = QImage(self.temp)
        scene.addPixmap(QPixmap.fromImage(a))
        self.colorWindow.ui.graphicsView.setScene(scene)
        os.remove(self.temp)


    def reset(self) : 

        self.colorWindow.ui.spinBoxContrast.valueChanged.disconnect(self.enhancePicture)
        self.colorWindow.ui.spinBoxLuminosite.valueChanged.disconnect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxSaturation.valueChanged.disconnect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxNettete.valueChanged.disconnect(self.enhancePicture)  
        self.colorWindow.ui.spinBoxRed.valueChanged.disconnect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxGreen.valueChanged.disconnect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxBlue.valueChanged.disconnect(self.enhancePicture) 
        self.colorWindow.ui.checkBoxMinMax.stateChanged.disconnect(self.enhancePicture)

        self.colorWindow.ui.spinBoxContrast.setValue(0)
        self.colorWindow.ui.spinBoxLuminosite.setValue(0)   
        self.colorWindow.ui.spinBoxSaturation.setValue(0)   
        self.colorWindow.ui.spinBoxNettete.setValue(0)  
        self.colorWindow.ui.spinBoxRed.setValue(0) 
        self.colorWindow.ui.spinBoxGreen.setValue(0) 
        self.colorWindow.ui.spinBoxBlue.setValue(0) 
        self.colorWindow.ui.checkBoxMinMax.setCheckState(0)

        self.enhancePicture()
        
        self.colorWindow.ui.spinBoxContrast.valueChanged.connect(self.enhancePicture)
        self.colorWindow.ui.spinBoxLuminosite.valueChanged.connect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxSaturation.valueChanged.connect(self.enhancePicture)   
        self.colorWindow.ui.spinBoxNettete.valueChanged.connect(self.enhancePicture)  
        self.colorWindow.ui.spinBoxRed.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxGreen.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.spinBoxBlue.valueChanged.connect(self.enhancePicture) 
        self.colorWindow.ui.checkBoxMinMax.stateChanged.connect(self.enhancePicture)

        

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
        




if __name__ == "__main__":
    app = app(sys.argv)
    sys.exit(app.exec_())