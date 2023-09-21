

#Tester pour voir si le left right se combine avec le mirroir horizontale à l'image de gauche

import os 

def getParDict(path) :

    listpath = os.listdir(path)
    parDict = {}
    for i in listpath : 
        if i.split('.')[-1] == 'par' : 
            fullpath = os.path.join(path,i)
            try :
                with open(fullpath) as f : 
                    s = f.read()
            except : 
                with open(fullpath, encoding='ANSI') as f :
                    s = f.read() 
            
            v1 = s.find('XYZ00')
            v2 = s.find("\n", v1)
            w = s[v1:v2].split(' ')
            coord = []
            coord.append(float(w[-3]))
            coord.append(float(w[-2]))
            parID = i.split('.')[0]
            parDict[parID] = coord
            f.close()

    return parDict


def findPairWithCoord(parDict,centerCoord) : 
    distDict = {}
    minDist = 9999999
    minID = ''
    for key, val in parDict.items() :
        dist = math.sqrt((centerCoord[0]-val[0])**2 + (centerCoord[1]-val[1])**2)
        distDict[key] = dist
        if dist < minDist : 
            minID = key
            minDist = dist

    buffer = 500
    nbPic = int(minID.split('_')[1])
    leftDist = 9999999
    leftName = ''
    rightDist = 9999998
    
    for key in distDict.keys() : 
        if key != minID and abs(parDict[minID][1] - parDict[key][1]) < buffer :  
            idNb = int(key.split('_')[1])
            if idNb + 1 == nbPic or idNb - 1 == nbPic :  
                if parDict[key][0] < parDict[minID][0] :
                    leftDist = distDict[key]
                    leftName = key
                elif parDict[key][0] > parDict[minID][0] :    
                    rightDist = distDict[key]

    if leftDist < rightDist : minID = leftName
    return (minID,minDist)
    #if minDist < 3000 : 

#a = getDict()
#b= iter(a)
#c = next(b)
#d = next(b)
#breakP = 0
#for key, value in a.items() :
#    print(value)

#make pair

#up = y up x same
#down = y down x same
from qgis.gui import *
from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
import math

def createShapePoint(shapeName, epsg, photoPath):
    #
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    fields.append(QgsField("name", QVariant.String))
    shapeName = 'C:\\Users\\pinfr1\\Downloads\\Photos/pointFromPicture.shp'
    epsg = 'EPSG:32187'
    
    vectorWriter = QgsVectorFileWriter(shapeName, "System", fields, QgsWkbTypes.MultiPoint, QgsCoordinateReferenceSystem(epsg), "ESRI Shapefile")
    points = getParDict('C:\\Users\\pinfr1\\Downloads\\Photos')
    for key, value in points.items() :
        
        feature = QgsFeature(fields)
        feature.setAttribute(1,str(key))
        geo = QgsGeometry.fromPointXY(QgsPointXY(value[0],value[1]))
        feature.setGeometry(geo)
        vectorWriter.addFeature(feature)
    #return vectorWriter
    
    

def findNeighbour(parID, currentDict):
    #path = 'U:/Photos\\q18067_226_rgb.par'
    #print(path.split('_')[1])
    
    up = ''
    upDiff = 9999999
    down = ''
    downDiff = 9999999
    left = ''
    leftDiff = 9999999
    right = ''
    rightDiff = 9999999
    points = currentDict
    currentValue = points[parID]
    #listpath = os.listdir(path)
    for key, value in points.items() :
        if key != parID :
            dist = math.sqrt((currentValue[0]-value[0])**2 + (currentValue[1]-value[1])**2)
            buffer = 500
            #up 
            if currentValue[1]+buffer < value[1] and dist < upDiff :
                upDiff = dist
                up = key
            #down
            if currentValue[1]-buffer > value[1] and dist < downDiff :
                downDiff = dist
                down = key
            #left    
            if  currentValue[0]-buffer > value[0] and dist < leftDiff :
                leftDiff = dist
                left = key
            #right
            if currentValue[0]+buffer < value[0] and dist < rightDiff :    
                rightDiff = dist
                right = key
    
    return (up,down,left,right)
    #Retourner une liste avec toutes les paires possibles (donc les chiffres collés seulement)
    #print(up)
    #print(down)
    #print(left)
    #print(right)


#findNeighbour()


def findPossiblePair(parID, currentDict) :
    #path = 'U:/Photos\\q18070_626_rgb.par'
    nbPic = int(parID.split('_')[1])
    
    leftPic = ''
    rightPic = ''
    
    points = currentDict
    currentValue = points[parID]
    
    buffer = 500
    
    for key, value in points.items() :
        if key != parID :
            if abs(currentValue[1] - value[1]) < buffer :  
                idNb = int(key.split('_')[1])
                if idNb + 1 == nbPic or idNb - 1 == nbPic :  
                    if value[0] < currentValue[0] :
                        leftPic = key
                    elif value[0] > currentValue[0] :    
                        rightPic = key
    return (leftPic, rightPic)
    #print(leftPic)
    #print(rightPic)
#findPossiblePair() 


