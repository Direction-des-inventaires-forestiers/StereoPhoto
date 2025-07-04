'''
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient des classes qui permettent de faire le lien entre les pixels et des coordonnées géospatiales

La classe pictureManager reçoit la taille d'une photo ainsi que le fichier PAR associé à cette photo
Le fichier PAR contient des informations sur la caméra qui ont pris la photo. Ces informations sont 
essentielles pour tranférer un pixel en coordonnée. 
Prochainement, le modèle numérique de terrain pourrait être utilisé pour déterminer l'altitude moyenne du sol sur la photo

La classe dualManager reçoit les informations des deux photos pour produire la zone de recouvrement des photos
C'est avec ce résultat que les photos sont positionnées automatiquement
Il est aussi possible de calculer le Z pour un point donné en utilisant l'information des deux photos

'''

from math import cos, sin, radians
#from qgis.PyQt.QtCore import QRectF
from PyQt5.QtCore import QRectF
import numpy as np

class pictureManager(): 

    def __init__(self, sizePicture, pathPAR):

        self.sizePicture = sizePicture
        self.pathPAR = pathPAR
        self.initPAR()
        #Try + Message QGIS si les point par marche pas
        
        
    def initPAR(self):

        keywords = {
            "$PARAFFINE00": "affine",
            "$PARINVAFF00": "inverse_affine",
            "$FOC00": "focal",
            "$XYZ00": "camera position",
            "$OPK00": "orientation",
            "$PIXELSIZE": "pixel_size",
            "$FSCALE00": "fscale",
            "$PPA": "principal point of autocollimation"
        }

        try:
            with open(self.pathPAR, encoding='utf-8') as f:
                lines = f.read().splitlines()
        except:
            with open(self.pathPAR, encoding='ansi') as f:
                lines = f.read().splitlines()

        values = {}
        for line in lines:
            for key in keywords:
                if line.startswith(key):
                    values[key] = line.split()
                    break

        affine = [float(val) for val in values["$PARAFFINE00"][-6:]]
        self.AffineA, self.AffineB, self.AffineC, self.AffineD, self.AffineE, self.AffineF = affine

        inverse_affine = [float(val) for val in values["$PARINVAFF00"][-6:]]
        self.InvA, self.InvB, self.InvC, self.InvD, self.InvE, self.InvF = inverse_affine

        self.Focal = float(values["$FOC00"][-1])

        self.X0, self.Y0, self.Z0 = [float(val) for val in values["$XYZ00"][-3:]]

        omega, phi, kappa = [float(val) for val in values["$OPK00"][-3:]]
        self.omega, self.phi, self.kappa = radians(omega), radians(phi), radians(kappa)

        if "$PIXELSIZE" in values:
            self.pixelSize = float(values["$PIXELSIZE"][-1]) * 1e-3
        else :
            self.pixelSize = self.AffineA 

        if "$FSCALE00" in values:   
            self.fscale = float(values["$FSCALE00"][-1]) * 1e-3
        else : 
            self.fscale = self.Z0/self.Focal

        if "$PPA" in values:
            self.PPAx = float(values["$PPA"][-2])
            self.PPAy = float(values["$PPA"][-1])
            self.PPCx = self.AffineA * self.PPAx + self.AffineB * self.PPAy + self.AffineC 
            self.PPCy = self.AffineD * self.PPAx + self.AffineE * self.PPAy + self.AffineF 
        else:
            self.PPCx = 0
            self.PPCy = 0
            self.PPAx = self.sizePicture[0] / 2
            self.PPAy = self.sizePicture[1] / 2

        self.groundPixelSize = self.fscale * self.pixelSize
        
        self.angleCalculation()


    def affineEquation(self, pixel) :
        xMM = self.AffineA * pixel[0] + self.AffineB * pixel[1] + self.AffineC 
        yMM = self.AffineD * pixel[0] + self.AffineE * pixel[1] + self.AffineF 
        return xMM, yMM

    def invAffineEquation(self, valueMM) :
        xPixel = self.InvA * valueMM[0] + self.InvB * valueMM[1] + self.InvC 
        yPixel = self.InvD * valueMM[0] + self.InvE * valueMM[1] + self.InvF
        return xPixel, yPixel

    def pixelToCoord(self, pixel, Z):

        xMM, yMM = self.affineEquation(pixel)
        kx = (self.r11*(xMM-self.PPCx) + self.r12*(yMM-self.PPCy) - self.r13*self.Focal) / (self.r31*(xMM-self.PPCx) + self.r32*(yMM-self.PPCy) - self.r33*self.Focal)
        ky = (self.r21*(xMM-self.PPCx) + self.r22*(yMM-self.PPCy) - self.r23*self.Focal) / (self.r31*(xMM-self.PPCx) + self.r32*(yMM-self.PPCy) - self.r33*self.Focal)
        X = self.X0 + (Z - self.Z0) * kx
        Y = self.Y0 + (Z - self.Z0) * ky
        return X, Y

    def coordToPixel(self, coord, Z):
        
        xMM = self.PPCx - self.Focal*(self.r11*(coord[0]-self.X0)+self.r21*(coord[1]-self.Y0)+self.r31*(Z-self.Z0)) / (self.r13*(coord[0]-self.X0)+self.r23*(coord[1]-self.Y0)+self.r33*(Z-self.Z0))
        yMM = self.PPCy - self.Focal*(self.r12*(coord[0]-self.X0)+self.r22*(coord[1]-self.Y0)+self.r32*(Z-self.Z0)) / (self.r13*(coord[0]-self.X0)+self.r23*(coord[1]-self.Y0)+self.r33*(Z-self.Z0))
        xPixel, yPixel = self.invAffineEquation([xMM,yMM])
        return xPixel, yPixel


    def angleCalculation(self):
        self.r11 = cos(self.phi)*cos(self.kappa)
        self.r12 = -cos(self.phi)*sin(self.kappa)
        self.r13 = sin(self.phi)
        self.r21 = cos(self.omega)*sin(self.kappa)+sin(self.omega)*sin(self.phi)*cos(self.kappa)
        self.r22 = cos(self.omega)*cos(self.kappa)-sin(self.omega)*sin(self.phi)*sin(self.kappa)
        self.r23 = -sin(self.omega)*cos(self.phi)
        self.r31 = sin(self.omega)*sin(self.kappa)-cos(self.omega)*sin(self.phi)*cos(self.kappa)
        self.r32 = sin(self.omega)*cos(self.kappa)+cos(self.omega)*sin(self.phi)*sin(self.kappa)
        self.r33 = cos(self.omega)*cos(self.phi)

    def getKX(self, valueMM):
        return (self.r11*(valueMM[0]-self.PPCx) + self.r12*(valueMM[1]-self.PPCy) - self.r13*self.Focal) / (self.r31*(valueMM[0]-self.PPCx) + self.r32*(valueMM[1]-self.PPCy) - self.r33*self.Focal)

    def getKY(self, valueMM):
        return (self.r21*(valueMM[0]-self.PPCx) + self.r22*(valueMM[1]-self.PPCy) - self.r23*self.Focal) / (self.r31*(valueMM[0]-self.PPCx) + self.r32*(valueMM[1]-self.PPCy) - self.r33*self.Focal)

    
class dualManager() :

    def __init__(self, leftManager, rightManager, Z=0):
        self.leftManager = leftManager
        self.rightManager = rightManager
        self.Z = Z

    def calculateZ(self, pixelLeft, pixelRight) :
        leftXMM, leftYMM = self.leftManager.affineEquation(pixelLeft)
        rightXMM, rightYMM = self.rightManager.affineEquation(pixelRight)
        kxLeft = self.leftManager.getKX([leftXMM, leftYMM])
        kyLeft = self.leftManager.getKY([leftXMM, leftYMM])
        kxRight = self.rightManager.getKX([rightXMM, rightYMM])
        kyRight = self.rightManager.getKY([rightXMM, rightYMM])

        if abs(kxLeft-kxRight) >= abs(kyLeft-kyRight) : 
            result = (self.rightManager.X0 - self.rightManager.Z0 * kxRight + self.leftManager.Z0 * kxLeft - self.leftManager.X0) / (kxLeft - kxRight)
        else:
            result = (self.rightManager.Y0 - self.rightManager.Z0 * kyRight + self.leftManager.Z0 * kyLeft - self.leftManager.Y0) / (kyLeft - kyRight)

        return result

    def getRect(self) :

        X = (self.leftManager.X0 + self.rightManager.X0) / 2
        Y = (self.leftManager.Y0 + self.rightManager.Y0) / 2
        pixL = self.leftManager.coordToPixel([X,Y], self.Z) 
        pixR = self.rightManager.coordToPixel([X,Y], self.Z)
        midL = [self.leftManager.sizePicture[0]/2 , self.leftManager.sizePicture[1]/2] 
        midR = [self.rightManager.sizePicture[0]/2 , self.rightManager.sizePicture[1]/2]
        rectL = QRectF(pixL[0] - midL[0], pixL[1] - midL[1], self.leftManager.sizePicture[0], self.leftManager.sizePicture[1])
        rectR = QRectF(-(pixR[0] - midR[0]), pixR[1] - midR[1], self.rightManager.sizePicture[0], self.rightManager.sizePicture[1]) 
        return rectL, rectR

def createWKTString(coordList,strName) :
    if strName == 'PolygonZ' :
        retSTR = strName + '(('
        for coord in coordList:
            retSTR += str(coord[0])
            retSTR += ' '
            retSTR += str(coord[1])
            retSTR += ' '
            retSTR += str(coord[2])
            retSTR += ','
        retSTR += '))'

        return retSTR
