from math import cos, sin, radians
from PyQt5.QtCore import QRectF


class pictureManager(): 

    def __init__(self, sizePicture, pathPAR, pathDEM):

        self.sizePicture = sizePicture
        self.pathPAR = pathPAR
        self.pathDEM = pathDEM
        self.paramPAR = ["$PARAFFINE00", "$PARINVAFF00", "$FOC00", "$XYZ00", "$OPK00"]
        self.initPAR()
        self.initDEM()
        self.angleCalculation()
        
    def initPAR(self):

        f = open(self.pathPAR) # if case si le read foncitonne pas changer le encoding pour open(...,encoding = 'ANSI') probleme seulement dans QGIS
        s = f.read() 
        a = []
        for i in range(len(self.paramPAR)) : 
            v1 = s.find(self.paramPAR[i])
            v2 = s.find("\n", v1)
            w = s[v1:v2]
            a.append(w.split(" ")) 


        self.AffineA = float(a[0][1])
        self.AffineB = float(a[0][2])
        self.AffineC = float(a[0][3])
        self.AffineD = float(a[0][4])
        self.AffineE = float(a[0][5]) 
        self.AffineF = float(a[0][6])
        
        self.InvA = float(a[1][1])
        self.InvB = float(a[1][2])
        self.InvC = float(a[1][3])
        self.InvD = float(a[1][4])
        self.InvE = float(a[1][5])
        self.InvF = float(a[1][6])
        
        self.Focal = float(a[2][1])
        
        self.X0 = float(a[3][1])
        self.Y0 = float(a[3][2])
        self.Z0 = float(a[3][3])

        self.omega = radians(float(a[4][1])) 
        self.phi = radians(float(a[4][2]))
        self.kappa = radians(float(a[4][3])) 
        

        
        self.PPCx = self.AffineA * (self.sizePicture[0]/2) + self.AffineB * (self.sizePicture[1]/2) + self.AffineC 
        self.PPCy = self.AffineD * (self.sizePicture[0]/2) + self.AffineE * (self.sizePicture[1]/2) + self.AffineF 


    def initDEM(self):
        altitudeTerrain = 298

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

    def getZ(self, coord):
        pass

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

    
# get Initial Z 

class dualManager() :

    def __init__(self, leftManager, rightManager, Z):
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
        print(rectL)
        print(rectR)
        return rectL, rectR












