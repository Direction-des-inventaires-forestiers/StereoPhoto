import cv2, os
import numpy as np
import math, time
from pynput import mouse
from PIL import Image, ImageOps, ImageEnhance
import gdal
import libtiff
#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *

#print(pen.)


Image.MAX_IMAGE_PIXELS = 1000000000 

a = ["1","2","3"]
b = ["e","f","1"]

for i in range(len(b)) :
    u = 2
    while(b[i] in a):
        b[i] = str(u)
        u += 1
        print("t")
print(b)
#a = Image.open("c.tif")
#b = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Serie_3/008_0913_0370_NIR.tif")

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

# Collect events until released
#with mouse.Listener(
#        on_move=on_move,
#        on_click=on_click,
#        on_scroll=on_scroll) as listener:
#    listener.join()

# ...or, in a non-blocking fashion:
#listener = mouse.Listener(
#    on_move=on_move,
#    on_click=on_click,
#    on_scroll=on_scroll)
#listener.start() 

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