from PIL import Image
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys, os, time, math


class threadPicture(QThread):

    def __init__(self, picture, rotation, miroir, path):
        QThread.__init__(self)
        self.picture = picture
        self.rotation = rotation
        self.miroir = miroir
        self.temp = path
        self.pix = QPixmap()

    def run(self) :
        if self.rotation == 0 and self.miroir == 0 :
            self.picture.save(self.temp)

        else :
            if self.rotation == 3 :
                self.picture = self.picture.rotate(90, expand=1)

            elif self.rotation == 2 :
                self.picture = self.picture.rotate(180, expand=0)

            elif self.rotation == 1 :
                self.picture = self.picture.rotate(270, expand=1)

            if self.miroir == 1 :
                self.picture = self.picture.transpose(Image.FLIP_LEFT_RIGHT)

            elif self.miroir == 2 :
                self.picture = self.picture.transpose(Image.FLIP_TOP_BOTTOM)

            self.picture.save(self.temp)

        self.pix = QPixmap.fromImage(QImage(self.temp))
    

    
