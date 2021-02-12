"""import cv2, os
import numpy as np



import gdal
import libtiff"""
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
#from pynput import mouse
import math, time, threading, win32api
from PIL import Image, ImageOps, ImageEnhance, ImageStat
#print(pen.)

#cropV = (2000,0,11310,17310)
#i = Image.open('C:\\Users\\pinfr1\\Downloads\\Photos\\AP13052_0930_RGB.tif')
#i.seek(3)

#Image.MAX_IMAGE_PIXELS = 1000000000 

#image = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/q19596_019_rgb.tif")
#t = image._TiffImageFile__frame
#image.seek(3)
#z = image._TiffImageFile__frame

#QgsProject.instance().fileName()
#a = QgsVectorLayer()
#a.startEditing()
#p1 = p2 = QgsPointXY(float, float)
#line = [p1, p2, ...]
#les points ne peuvent pas se croiser
#a.splitFeatures(line)

#line = [QgsPointXY(-0.29724165594392782 0.23624634305703263), QgsPointXY(0.03001826676176712 0.41875668456597787), QgsPointXY(-0.00209026952537686 -0.22570278064427082), QgsPointXY(-0.29724165594392782 0.23624634305703263)]
#repeter le dernier point non nécessaire
#newG = QgsGeometry.fromMultiPolygonXY([[line]])
#a.getGeometry(i),asMultiPolygon()[0][0][#QgsPointXY][x/y], isNull()
#a.changeGeometry(i, newQgsGeometry)
#iface.mapCanvas().refresh()

#Ajouter un polygon à une couche deja existante
#feat = QgsFeature()
#feat.setGeometry(newG)
#QgsVectorLayer.dataProvider().addFeatures([feat])

#Ajouter un polygon sur une nouvelle vectorLayer
#from osgeo import ogr, osr
#shapeName = "U:/StereoPhoto/polyLayer.shp"
#outDriver = ogr.GetDriverByName("ESRI Shapefile")
#outDataSource = outDriver.CreateDataSource(shapeName)
#shapeCRS = osr.SpatialReference()
#shapeCRS.ImportFromEPSG(epsg) epsg --> MTM 10 par exemple mais le code en chiffre
#outLayer = outDataSource.CreateLayer("polyLayer",shapeCRS , geom_type = ogr.wkbPolygon)
#iface.addVectorLayer(shapeName, polyLayer, "ogr")
#feat = QgsFeature()
#feat.setGeometry(newG)
#QgsVectorLayer.dataProvider().addFeatures([feat])

#Merge 2 polygon
#currentG1 = QgsVectorLayer.getGeometry(i) -> QgsGeometry
#currentG2 = QgsVectorLayer.getGeometry(j) -> QgsGeometry
#newG = currentG1.combine(currentG2)
#QgsVectorLayer.deleteFeature(i)
#QgsVectorLayer.changeGeometry(j, newG)

#Trouver si le point est dans la forme
#QgsGeometry.contains(QgsPointXY(x,y))

#Trouver les points d'intersection 
#QgsGeometry.intersection(QgsGeometry) -> le dernier point est comme le premier
#QgsGeometry.intersects(QgsGeometry)

#Pour le cas ou l'on ne veut pas merge les polygons mais plutôt les séparer
#Le résultat peut être plusieur polygone, voir si on les sépares en 2 entités
# geo =  newDrawPolygon.difference(alreadyDrawPoly) -> QgsGeometry pour les 2 cas


#symDifference et makeDifference sont des inverses (pas pertinant je crois mais garder en tête)

#fields = QgsFields()
#feet = QgsFeature()
#r =QgsVectorFileWriter(shapeName, "System", fields, QgsWkbTypes.MultiPolygon, QgsCoordinateReferenceSystem(4326), "ESRI Shapefile")
#r.addFeature(feet)

#a = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Saturation/2019-11-22_000484.png")
#sa = a.load()
#psa1 = sa[950,200]
#psa2 = sa[800,200]
#psa3 = sa[600,500]
#psa4 = sa[1429,662]
#psa5 = sa[1429,664]

#c = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Saturation/2019-11-22_000486.png")
#sc = c.load()
#psc1 = sc[950,200]
#psc2 = sc[800,200]

"""
psc1 = sc[1429,679]
psc2 = sc[1429,680]
psc3 = sc[1429,664]
psc4 = sc[1429,662]
psc5 = sc[1429,665]
psc6 = sc[1429,666]"""

#b = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/AutoLocalizedHistogram/Original.png")
#sb = b.load()
#psb1 = sb[950,200]
#psb2 = sb[800,200]
"""
psb1 = sb[1429,679]
psb2 = sb[1429,680]
psb3 = sb[1429,664]
psb4 = sb[1429,662]
psb5 = sb[1429,665]
psb6 = sb[1429,666]"""




"""
d = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Contrast/2019-11-22_000479.png")
sd = d.load()
psd1 = sd[1429,679]
psd2 = sd[1429,680]
psd3 = sd[1429,664]
psd4 = sd[1429,662]
psd5 = sd[1429,665]
psd6 = sd[1429,666]

e = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Contrast/2019-11-22_000477.png")
se = e.load()
pse1 = se[1429,679]
pse2 = se[1429,680]
pse3 = se[1429,664]
pse4 = se[1429,662]
pse5 = se[1429,665]
pse6 = se[1429,666]

f = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Contrast/2019-11-22_000476.png")
sf = f.load()
psf1 = sf[1429,679]
psf2 = sf[1429,680]
psf3 = sf[1429,664]
psf4 = sf[1429,662]
psf5 = sf[1429,665]
psf6 = sf[1429,666]

g = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Rehaussements_SUMMIT/Contrast/2019-11-22_000475.png")
sg = g.load()
psg1 = sg[1429,679]
psg2 = sg[1429,680]
psg3 = sg[1429,664]
psg4 = sg[1429,662]
psg5 = sg[1429,665]
psg6 = sg[1429,666]"""


#a = ["1","2","3"]
#b = ["e","f","1"]

#for i in range(len(b)) :
    #u = 2
    #while(b[i] in a):
        #b[i] = str(u)
        #u += 1
        #print("t")

#a = Image.open("c.tif")
b = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Serie_3/008_0913_0370_NIR.tif")
print(b.size)
#z = b.split()


#c = np.zeros((17110,11310), dtype=np.uint8)


#driver = gdal.GetDriverByName("GTiff")
#fileout = driver.Create("w.tif",11310,17110,1,gdal.GDT_Byte, ["COMPRESS=JPEG", "TILED=YES", "PHOTOMETRIC=YCBCR" , "JPEG_QUALITY=90"])
#fileout = driver.Create("y.tif",b.size[0],b.size[1],3,gdal.GDT_Byte, ["COMPRESS=JPEG", "TILED=YES" , "JPEG_QUALITY=90"])
#fileout.GetRasterBand(1).WriteArray(np.array(z[0], dtype=np.uint8))
#fileout.GetRasterBand(2).WriteArray(np.array(z[1], dtype=np.uint8))
#fileout.GetRasterBand(3).WriteArray(np.array(z[2], dtype=np.uint8))
#fileout.BuildOverviews("AVERAGE", [2,4,8])


#fileout.FlushCache()
#fileout = None

#loop this
#fileout = driver.Create("e.tif",d.shape[1],d.shape[0],1,gdal.GDT_Byte, options=["APPEND_SUBDATASET=YES", "COMPRESS=JPEG"])
#fileout.GetRasterBand(1).WriteArray(d)
#fileout.FlushCache()
#fileout = None

def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
       return False

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y

line1 = ((1,1),(-1,-1))
line2 = ((1,-1),(-1,-1))
line_intersection(line1, line2)



def colorEqualization(value):
    oldMin = 50
    oldMax = 100
    newMin = 0 
    newMax = 255
    v = ((value-oldMin)*(newMax-newMin))/(oldMax - oldMin) + newMin
    return round(v)


def on_move(x, y):
    print('Pointer moved to {0}'.format(
        (x, y)))

def on_click(x, y, button, pressed):
    print('{0} at {1}'.format(
        'Pressed' if pressed else 'Released',
        (x, y)))
    if not pressed:
        # Stop listener
        return False

def on_scroll(x, y, dx, dy):
    print('Scrolled {0} at {1}'.format(
        'down' if dy < 0 else 'up',
        (x, y)))
"""
# Collect events until released
with mouse.Listener(
        on_move=on_move,
        #on_click=on_click,
        on_scroll=on_scroll) as listener:
    listener.join()"""

#win32api.SetCursorPos((960,540))
"""listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click,
    on_scroll=on_scroll)
listener.start()"""

#time.sleep(1)
#listener.stop()



#m = mouse.Controller() #Plutot que prendre le controlleur seulement bouger avec ctypes et relancer le listerner ?
#m.move(200,200)

# ...or, in a non-blocking fashion:
 

#s = time.time()
#path = "//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Paire_1/Q18066_484_RGB.tif"
#img = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Anaglyph/Photo/Camion_L.jpg")
#img = Image.open(path)
#img.seek(2)
#b = img.split()
#r = b[0].point(colorEqualization)
#g = b[1].point(colorEqualization)
#b = b[2].point(colorEqualization)
#c = Image.merge("RGB", (r,g,b))
#c.show()

#a = ImageEnhance.Brightness(img)
#b = ImageEnhance.Contrast(img)
#c = ImageEnhance.Color(img)
#c.enhance(0.5).show()
#a.enhance(1.5)
#c.enhance(0.5).show()




#a = img.histogram()
#a = img.size[0]
#print(a)
#a = img.histogram()
#img = img.rotate(270, expand=1)
#img = img.transpose(Image.FLIP_LEFT_RIGHT)
#j = ImageOps.mirror(i)
#img.save("a.jpg")
#picArray = np.array(img)
#picArray = np.rot90(picArray,2)
#im = Image.fromarray(picArray)
#print(time.time()-s)

#a = img.transpose(Image.ROTATE_90)
#a.show()
#f = Image.open("a.jpg")
#os.remove("a.jpg")
#f.show()

#path = "//smullin/lidar/PUBLIC/11M/11M01NE/MNT_11M01NE.tif"
#img = Image.open(path)
#a = np.array(img)


#path = "//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Paire_1/Q18066_406_RGB.par"
#f = open(path, encoding = 'ANSI')
#s = f.read() 
#v1 = s.find("$XYZ00")
#v2 = s.find("\n", v1)
#xyz = s[v1:v2]

#v1 = s.find("$PARAFFINE00")
#v2 = s.find("\n", v1)
#affine = s[v1:v2]





specifiedWidth = 1500
specifiedHeight = 2000

def createPyramid(self, path):
    img = cv2.imread(path)
    height, width, channel = img.shape
    numberOfHorizontalTile = math.ceil(width/specifiedWidth)
    numberOfVerticalTile = math.ceil(height/specifiedHeight)
    numberOfIterationA = math.floor(math.log2(numberOfHorizontalTile))
    numberOfIterationB = math.floor(math.log2(numberOfVerticalTile))
    nbPyramid = min(numberOfIterationA, numberOfIterationB)

    layer = img.copy()
    gaussian_pyramid = [cv2.cvtColor(layer,cv2.COLOR_BGR2RGB)]
    for i in range(nbPyramid):
        
        layer = cv2.pyrDown(layer)
        gaussian_pyramid.append(cv2.cvtColor(layer,cv2.COLOR_BGR2RGB))

    listPic = []
    for j in range(nbPyramid):
        a = gaussian_pyramid[j]
        height, width, channel = a.shape
        numberOfHorizontalTile = math.ceil(width/specifiedWidth)
        numberOfVerticalTile = math.ceil(height/specifiedHeight)

        b = [[0 for u in range(numberOfHorizontalTile)] for v in range(numberOfVerticalTile)]
        for x in range(numberOfVerticalTile):
            for y in range(numberOfHorizontalTile):
                b[x][y] = np.fliplr(a[x*specifiedHeight : ((x+1)*specifiedHeight)- 1, y*specifiedWidth : ((y+1)*specifiedWidth) - 1, :])
                #b[x][y] = (a[x*specifiedHeight : ((x+1)*specifiedHeight)- 1, y*specifiedWidth : ((y+1)*specifiedWidth) - 1, :])
        listPic.append(b)

    return nbPyramid, gaussian_pyramid, listPic
 
 
def seekNewQuality(self, multiFactor, seekFactor, scaleFactor):

        self.picture.seek(seekFactor)
        topX = round(self.pointZero.x()*multiFactor) if round(self.pointZero.x()*multiFactor) >= 0 else 0
        topY = round(self.pointZero.y()*multiFactor) if round(self.pointZero.y()*multiFactor) >= 0 else 0
        lowX = round(self.pointMax.x()*multiFactor)  if round(self.pointMax.x()*multiFactor) <= self.picture.size[0] else self.picture.size[0]
        lowY = round(self.pointMax.y()*multiFactor)  if round(self.pointMax.y()*multiFactor) <= self.picture.size[1] else self.picture.size[1]
        sizePixelX = abs(lowX - topX)
        sizePixelY = abs(lowY - topY)
        
        #Ne doit pas être de petites valeurs
     
        maxX = 750 #via self.picture.size
        maxY = 500

        middleRect = [topX, topY, lowX, lowY]
        firstRect = [0,0,topX, self.picture.size[1]]
        secondRect = [lowX, 0, self.picture.size[0], self.picture.size[1]]
        thridRect = [topX, 0, topX+sizePixelX , topY]
        fourthRect = [topX, topY+sizePixelY, lowX, self.picture.size[1]]

        rect = [middleRect, firstRect, secondRect, thridRect, fourthRect]
        t = time.time()
        for item in rect :

            nbDivX = ceil(abs(item[2] - item[0])/maxX)
            nbDivY = ceil(abs(item[3] - item[1])/maxY)

            currentTopX = item[0]
            currentTopY = item[1]
            
            for x in range(nbDivX) :
                
                currentLowX = currentTopX + maxX if (currentTopX + maxX) < item[2] else item[2]
                
                for y in range(nbDivY) : 

                    currentLowY = currentTopY + maxY if (currentTopY + maxY) < item[3] else item[3]
                    
                    cropPicture = self.picture.crop((currentTopX,currentTopY,currentLowX,currentLowY))
                    
                    #cropPicture.save(self.temp)
                    #a = QImage(self.temp)
                    
                    cropPictur = np.array(cropPicture)
                    a = qimage2ndarray.array2qimage(cropPictur)
                    
                    b = QPixmap.fromImage(a)
                    d = self.colorWindow.ui.graphicsView.scene().addPixmap(b)
                    d.setScale(scaleFactor)
                    d.setOffset(currentTopX, currentTopY)

                    currentTopY += maxY
                
                currentTopX += maxX
                currentTopY = item[1]

            
                

        #Découpage de 4 rectangles qui seront ensuite découpé en plus petit rectangle 
        #Version 1 placer les 5 rectangles sans rien optimisé
        #Version 2 placer les sous-rectangles
        #Version 3 placer les sous-rectangles via un thread
        #Version 4 offrir le seek(0)
        #Version 5 Offrir le placement selon la proximité 
        #os.remove(self.temp)
        self.picture.seek(3) 


"""import numpy as np

from skimage import data, io
from skimage.transform import pyramid_gaussian

from PIL import Image
Image.MAX_IMAGE_PIXELS = 1000000000 

image = io.imread("Photo/Q18066_406_RGB.tif", plugin="pil")
original, pyramid = tuple(pyramid_gaussian(image, max_layer=1, downscale=16, multichannel=True))
f = (pyramid*255 / np.max(pyramid)).astype('uint8')
im = Image.fromarray(f)
im.show()"""

"""
void QGraphicsView::mouseMoveEvent(QMouseEvent *event)
{
    Q_D(QGraphicsView);
    if (d->dragMode == QGraphicsView::ScrollHandDrag) {
        if (d->handScrolling) {
            QScrollBar *hBar = horizontalScrollBar();
            QScrollBar *vBar = verticalScrollBar();
            QPoint delta = event->pos() - d->lastMouseEvent.pos();
            hBar->setValue(hBar->value() + (isRightToLeft() ? delta.x() : -delta.x()));
            vBar->setValue(vBar->value() - delta.y());
            // Detect how much we've scrolled to disambiguate scrolling from
            // clicking.
            ++d->handScrollMotions;
        }
    }
    d->mouseMoveEventHandler(event);
}"""

"""
if hasattr(self.leftPic, "n_frames"): #and format == tif??
    for i in range(self.leftPic.n_frames):
        self.leftPic.seek(i)
        if self.leftPic.size < (100,100) :
            self.leftPic.seek(i-1)
            break

    self.demoLeftPic = self.leftPic
    self.leftPic.seek(0)

print(img.n_frames)
for i in range(img.n_frames) :
img.seek(3)
a = img 
a = np.asarray(img)
a.show()
print(img.size)
print(a.shape)"""



"""
        p = self.picture

        if self.colorWindow.ui.spinBoxContrast.value() != 0 :
            value = self.colorWindow.ui.spinBoxContrast.value()
            if value > 0:
                if value < 50 :
                    p = ImageEnhance.Contrast(p).enhance(1 + (0.02*value))
                elif value < 80:
                    p = ImageEnhance.Contrast(p).enhance(2 + (0.1*(value-50)))
                else :
                    p = ImageEnhance.Contrast(p).enhance(5 + (value-80))

            else : 
                p = ImageEnhance.Contrast(p).enhance(1 +(value/100))

        if self.colorWindow.ui.spinBoxSaturation.value() != 0 :
            value = self.colorWindow.ui.spinBoxSaturation.value()
            if value > 0 :
                p = ImageEnhance.Color(p).enhance(1 + (0.05 * value))
            else :
                p = ImageEnhance.Color(p).enhance(1 + int(value/100))

        if self.colorWindow.ui.spinBoxNettete.value() != 0 :
            p = ImageEnhance.Sharpness(p).enhance(self.colorWindow.ui.spinBoxNettete.value()/10 + 1)
        
        s = p.split()

        if self.colorWindow.ui.checkBoxMinMax.checkState() == Qt.Checked : 

            if self.colorWindow.ui.spinBoxRed.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                mr = s[0].point(self.redEnhance)
            else :
                mr = s[0]

            if self.colorWindow.ui.spinBoxGreen.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                mg = s[1].point(self.greenEnhance)
            else : 
                mg = s[1]

            if self.colorWindow.ui.spinBoxBlue.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                mb = s[2].point(self.blueEnhance)
            else :

                mb = s[2]

            self.calculHistogram(mr,mg,mb)

            r = mr.point(self.redEqualization)
            g = mg.point(self.greenEqualization)
            b = mb.point(self.blueEqualization)

        
        else :
            if self.colorWindow.ui.spinBoxRed.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                r = s[0].point(self.redEnhance)
            else :
                r = s[0]

            if self.colorWindow.ui.spinBoxGreen.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                g = s[1].point(self.greenEnhance)
            else : 
                g = s[1]

            if self.colorWindow.ui.spinBoxBlue.value() != 0 or self.colorWindow.ui.spinBoxLuminosite.value() != 0 :
                b = s[2].point(self.blueEnhance)
            else :
                b = s[2]
        """