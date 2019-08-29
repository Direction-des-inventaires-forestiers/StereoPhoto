import cv2, os
import numpy as np
import math, time
from PIL import Image, ImageOps
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

#print(pen.)

#Image.MAX_IMAGE_PIXELS = 1000000000 

#s = time.time()
#img = Image.open("//ulysse/LIDAR/Developpement/Programmation/FP/Stereoscopie/Photos_stereo/Paire_1/Q18066_406_RGB.tif")
#a = img.histogram()
#img = img.rotate(270, expand=1)
#img = img.transpose(Image.FLIP_LEFT_RIGHT)
#j = ImageOps.mirror(i)
#img.save("a.jpg")
#picArray = np.array(img)
#picArray = np.rot90(picArray,2)
#im = Image.fromarray(picArray)
#print(time.time()-s )

#a = img.transpose(Image.ROTATE_90)
#a.show()
#f = Image.open("a.jpg")
#os.remove("a.jpg")
#f.show()



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