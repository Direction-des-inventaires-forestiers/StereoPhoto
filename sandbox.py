import cv2
import numpy as np


img = cv2.imread("Photo/Q18066_406_RGB.tif")
height, width, channels = img.shape

# Gaussian Pyramid
layer = img.copy()
gaussian_pyramid = [layer]
#for i in range(3):
layer = cv2.pyrUp(layer)
    #gaussian_pyramid.append(layer)
    #cv2.imshow(str(i), layer)

cv2.imwrite("a.jpg", layer)
#cv2.imshow("Original image", img)
#cv2.waitKey(0)
#cv2.destroyAllWindows()


"""
        img = cv2.imread(self.optWindow.ui.importLineRed.text())
        layer = img.copy()
        gaussian_pyramid = [layer]
        for i in range(3):
            layer = cv2.pyrDown(layer)
            gaussian_pyramid.append(layer)
        
        #cv2.imwrite("a.jpg", layer)
        #self.leftPic = Image.open("a.jpg")
        #print(type(gaussian_pyramid[2][0,0,0]))"""




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