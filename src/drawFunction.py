'''
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient des fonctions qui permettent de tracer des polygones dans QGIS 
Les fonctions utilisent des fonctions et des objets de QGIS pour faire le traitement

Il est possible de :
    - Créer un shapefile de type Vector Layer
    - Récupérer la couche active
    - Ajouter un polygon sur la couche
    - Fusionner 2 polygons
    - Découper un polygon
    - Reformer un polygon pour faire place à un nouveau

Des fonctionnalités supplémentaires seront ajouter dans le futur pour agrémenter l'outil de trace :
    - Trace automatique (sans click)
    - Accrochage des segments entre les formes via les segments ou les arêtes 
    - Ajout de points et de lignes
    et bien d'autre
'''

from qgis.gui import *
from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtWidgets import *
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *

import math, threading, traceback
from osgeo import gdal
import numpy as np
from .worldManager import pictureManager, dualManager


#Création d'un vector layer dans QGIS
#Ajout d'un ID pour être similaire à la création normale de QGIS
def createShape(shapeName, EPSG):
    #shapeName = "U:/StereoPhoto/ShapeFile/TestLayer.shp"
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    feature = QgsFeature()
    vectorWriter = QgsVectorFileWriter(shapeName, "System", fields, QgsWkbTypes.MultiPolygon, QgsCoordinateReferenceSystem(EPSG), "ESRI Shapefile")
    vectorWriter.addFeature(feature)
    del vectorWriter
    vectorLayer = iface.addVectorLayer(shapeName, "", "ogr")
    return vectorLayer

#Future fonction propose la liste des current layers et choisir parmis la liste ou tout simplement créer une nouvelle couche
#Pour le moment, elle retourne la couche active
def getVectorActiveLayer():
    return iface.activeLayer()

def getRectPolygon(rect, vectorLayer):
    return list(vectorLayer.getFeatures(rect))

#Ajout d'un polygon sur la couche
#Avec geometry comme intrant on considère déja un QgsGeometry
def addPolygon(vectorLayer, geometry):
    vectorLayer.startEditing()
    feat = QgsFeature()
    feat.setGeometry(geometry)
    vectorLayer.dataProvider().addFeature(feat)
    vectorLayer.commitChanges()

#Fusion 2 polygones ensemble
def mergePolygon(currentGeo, currentIndex, extraGeo, vectorLayer):
    vectorLayer.startEditing()
    newGeo = currentGeo.combine(extraGeo)
    vectorLayer.changeGeometry(currentIndex, newGeo)
    vectorLayer.commitChanges()
    return newGeo

def reshapeLayer(lineString,listFeatures,vectorLayer) :
    vectorLayer.startEditing()
    for feat in listFeatures :
        geo = feat.geometry()
        print(geo)
        retval = geo.reshapeGeometry(lineString)
        if retval == 0 : 
            print(geo)
            vectorLayer.changeGeometry(feat.id(),geo)
        else : print(retval)
    vectorLayer.commitChanges()
        

#Découpe la couche en fonction d'une ligne tracer par l'utilisateur
#Si les lignes tracées se croisent aucune coupe à lieu (IDEM à QGIS)
def cutPolygon(vectorLayer, line):
    vectorLayer.startEditing()
    vectorLayer.removeSelection()
    vectorLayer.splitFeatures(line)
    vectorLayer.commitChanges()

#Lorsqu'un nouveau polygon entre en contact avec un polygon existant
#Le nouveau est conservé dans son entièreté et l'ancien est reformé pour laisser la place au nouveau
def automaticPolygon(oldGeo, currentIndex, newGeo, vectorLayer):
    vectorLayer.startEditing()
    finalGeo =  oldGeo.difference(newGeo)

    firstShape = True
    for item in finalGeo.asGeometryCollection():
        if firstShape :
            vectorLayer.changeGeometry(currentIndex, item)
            firstShape = False
        else : 
            feat = QgsFeature()
            feat.setGeometry(item)
            vectorLayer.dataProvider().addFeature(feat)

    feat = QgsFeature()
    feat.setGeometry(newGeo)
    vectorLayer.dataProvider().addFeature(feat)
    vectorLayer.commitChanges()


def addPoint(vectorLayer,geometry) :
    vectorLayer.startEditing()
    
    feature = QgsFeature()
    #geom = QgsGeometry()
    feature.setGeometry(geometry)
    feature.setFields(vectorLayer.fields())

    
    
    vectorLayer.dataProvider().addFeature(feature)
    vectorLayer.commitChanges()
    vectorLayer.triggerRepaint()
    
    return feature
    


class calculatePolygon(QThread):
    def __init__(self, vectorToShow, rectCoord, leftPicMan, rightPicMan, initAltitude, mntPath):
        QThread.__init__(self)
        #self.features = featList
        self.vectorToShow = vectorToShow
        self.rectCoord = rectCoord
        self.leftManager = pictureManager(leftPicMan[0], leftPicMan[1])
        self.rightManager = pictureManager(rightPicMan[0], rightPicMan[1])
        self.dualManag = dualManager(self.leftManager,self.rightManager)
        self.initAltitude = initAltitude 
        self.mntPath = mntPath 
        self.useLayerZ = False
        self.oldMNTPath = ''
        self.dictPolyL = {}
        self.dictPolyR = {}
        self.running = True
        self.count = 0

    def run(self):
        while self.running : 
            if self.mntPath != '' :
                self.mntDS = gdal.Open(self.mntPath,gdal.GA_ReadOnly)
                self.mntBand = self.mntDS.GetRasterBand(1)
                self.mntGeo = self.mntDS.GetGeoTransform()
                self.mntSize = (self.mntDS.RasterXSize, self.mntDS.RasterYSize)
                self.mntNodata = self.mntBand.GetNoDataValue()

                pxStart = math.floor((self.rectCoord.xMinimum() - self.mntGeo[0]) / self.mntGeo[1])
                pyStart = math.floor((self.rectCoord.yMaximum() - self.mntGeo[3]) / self.mntGeo[5])

                pxEnd = math.floor((self.rectCoord.xMaximum() - self.mntGeo[0]) / self.mntGeo[1])
                pyEnd = math.floor((self.rectCoord.yMinimum() - self.mntGeo[3]) / self.mntGeo[5])

                # Requested output size
                sizeX = pxEnd - pxStart
                sizeY = pyEnd - pyStart            
                mntArr = np.full((sizeY, sizeX), self.mntNodata, dtype=np.float32)

                if (pxStart >= self.mntSize[0] or pxStart + sizeX <= 0 or
                    pyStart >= self.mntSize[1] or pyStart + sizeY <= 0):

                    self.mntArr = mntArr


                else : 
                    # Where the read starts *in the raster*
                    read_xoff = max(0, pxStart)
                    read_yoff = max(0, pyStart)

                    # Where the read starts *inside the output array*
                    arr_xoff = max(0, -pxStart)
                    arr_yoff = max(0, -pyStart)

                    # Compute read size inside raster bounds
                    read_xsize = min(pxStart + sizeX, self.mntSize[0]) - read_xoff
                    read_ysize = min(pyStart + sizeY, self.mntSize[1]) - read_yoff

                    if read_xsize > 0 and read_ysize > 0:
                        try:
                            sub = self.mntBand.ReadAsArray(read_xoff, read_yoff,
                                                        read_xsize, read_ysize)
                            # Place into output array
                            mntArr[arr_yoff:arr_yoff + read_ysize,
                                arr_xoff:arr_xoff + read_xsize] = sub

                        except Exception as e:
                            # Reading failed → keep nodata-filled array
                            print("ReadAsArray failed:", e)

                    # Store final result
                    self.mntArr = mntArr
                
            for layer in iface.mapCanvas().layers():
                try :
                    name = layer.name()
                    if name not in self.vectorToShow : continue
                    couleur = self.vectorToShow[name][0]
                    self.useLayerZ = self.vectorToShow[name][1]


                    if layer.type() == QgsMapLayerType.VectorLayer and name in self.vectorToShow.keys() : 
                        
                        self.dictPolyL[name] = [[],couleur,layer.geometryType()]
                        self.dictPolyR[name] = [[]]
                        features = layer.getFeatures(self.rectCoord)
            
                        for item in features : 
                            #try : 
                            featureGeo = item.geometry() 
                            constGeo = featureGeo.constGet()
                            self.count += 1
                            dataToUse = []
                            if featureGeo.isMultipart() :
                                for p in constGeo.parts() :
                                    dataToUse.append(p)
                            else : dataToUse.append(constGeo)

                            
                            if featureGeo.isNull() == False and featureGeo.type() == QgsWkbTypes.PolygonGeometry :
                                
                                for part in dataToUse : 
                                    polygonL = QPolygonF()
                                    polygonR = QPolygonF()
                                    #Avoir si il est nécessaire d'ajouter les anneaux internes
                                    #Normalement l'anneau interne existe comme anneaux externe d'un autre polygon
                                    #for i in range(constGeo.numInteriorRings()):
                                    #   inner = constGeo.interiorRing(i)
                                    
                                    exteriorRing = part.exteriorRing()
                                    for data in exteriorRing.points():

                                        pixL, pixR = self.pointToPix(data,featureGeo.wkbType())
                                        
                                        polygonL.append(QPointF(pixL[0], pixL[1]))
                                        polygonR.append(QPointF(pixR[0], pixR[1]))

                                    self.dictPolyL[name][0].append(polygonL)
                                    self.dictPolyR[name][0].append(polygonR)
                            elif featureGeo.isNull() == False and featureGeo.type() == QgsWkbTypes.LineGeometry : 
                                for part in dataToUse : 
                                    lineL = QPainterPath()
                                    lineR = QPainterPath()
                                    #constGeo = featureGeo.constGet() 
                                    first = True
                                    for data in part.points() : 

                                        pixL, pixR = self.pointToPix(data,featureGeo.wkbType())
                                        
                                        if first : 
                                            lineL.moveTo(QPointF(pixL[0], pixL[1]))
                                            lineR.moveTo(QPointF(pixR[0], pixR[1]))
                                            first = False
                                        else :
                                            lineL.lineTo(QPointF(pixL[0], pixL[1]))
                                            lineR.lineTo(QPointF(pixR[0], pixR[1]))

                                    self.dictPolyL[name][0].append(lineL)
                                    self.dictPolyR[name][0].append(lineR)
                            
                            elif featureGeo.isNull() == False and featureGeo.type() == QgsWkbTypes.PointGeometry :
                                for data in dataToUse :
                                
                                    pixL, pixR = self.pointToPix(data,featureGeo.wkbType())
                                    
                                    self.dictPolyL[name][0].append((pixL[0], pixL[1]))
                                    self.dictPolyR[name][0].append((pixR[0], pixR[1]))
                                
                except Exception as e:
                    print(f"Error in thread: {e}")
                    traceback.print_exc()
            self.running = False
                
    def pointToPix(self,point,geotype) : 

        if QgsWkbTypes.hasZ(geotype) :
            if self.useLayerZ : z = point.z()
            else : z = self.getAltitude(point.x(), point.y(),z=point.z()) 
        else : z = self.getAltitude(point.x(), point.y())
                
        xPixel, yPixel = self.leftManager.coordToPixel((point.x() , point.y()), z)
        #keyVal  = cropValueLeft,rightMiroir,rightPicSize[0],cropValueRight,initAltitude
        pixL = (xPixel, yPixel)            

        xPixel, yPixel = self.rightManager.coordToPixel((point.x() , point.y()), z)          
      
        pixR = (xPixel, yPixel)  
        
        return pixL, pixR

    def getAltitude(self,x,y,z=None) : 
        mntAlt = None
    
        if self.mntPath != '' : #and  self.mntArr is not self.mntNodata:

            pxPoint = math.floor((x - self.mntGeo[0]) / self.mntGeo[1]) 
            pyPoint = math.floor((y - self.mntGeo[3]) / self.mntGeo[5])

            try : 
                #Array numpy l'axe Y en premier
                mntAlt = self.mntArr[pyPoint-self.pyStart,pxPoint-self.pxStart]
                if mntAlt != self.mntNodata : 
                    return mntAlt
            #if pxPoint in range(0,self.mntSize[0]) and pyPoint in range(0,self.mntSize[1]) :
            #    try : 
            #        
            #        mntAlt = self.mntBand.ReadAsArray(pxPoint,pyPoint,1,1)
            #        if mntAlt != self.mntNodata : 
            #            return mntAlt

            except : pass
        
        if z is None  :
            pl = self.leftManager.coordToPixel((x,y), self.initAltitude)
            pr = self.rightManager.coordToPixel((x,y), self.initAltitude) 
            mntAlt = self.dualManag.calculateZ(pl,pr)
        else : mntAlt = z
        
        return mntAlt

    def stop(self) : 
        self.running = False
