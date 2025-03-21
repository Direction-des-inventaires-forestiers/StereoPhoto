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
#from PyQt5.QtWidgets import *
#from PyQt5.QtCore import *
#from PyQt5.QtGui import *

import math, threading, traceback
from osgeo import gdal
from .worldManager import pictureManager, dualManager

#rect signifie la zone d'inspection désirer (QgsRectangle de coordonnée)
#un feature partiellement dans le rectangle se considérer dans la liste -> ce qu'on désire
#list(QgsVectorLayer.getFeatures(rect))[0] -> retourne le premier feature de la liste .geometry()
#QgsProject.instance().fileName()

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
    #p1 = p2 = QgsPointXY(float, float)
    #line = [p1, p2, ...]
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
    
    #feature = QgsFeature(vectorLayer.fields())  
    #feature.setGeometry(geometry)
    feature = QgsFeature()
    #geom = QgsGeometry()
    feature.setGeometry(geometry)
    feature.setFields(vectorLayer.fields())

    
    
    vectorLayer.dataProvider().addFeature(feature)
    vectorLayer.commitChanges()
    vectorLayer.triggerRepaint()
    
    return feature
    


class calculatePolygon(QThread):
    def __init__(self, vectorToShow, rectCoord, leftPicMan, rightPicMan, value, mntPath, useLayerZ=False):
        QThread.__init__(self)
        #self.features = featList
        self.vectorToShow = vectorToShow
        self.rectCoord = rectCoord
        self.leftManager = pictureManager(leftPicMan[0], leftPicMan[1], 'aa')
        self.rightManager = pictureManager(rightPicMan[0], rightPicMan[1], 'aa')
        self.dualManag = dualManager(self.leftManager,self.rightManager)
        self.keyVal = value #cropValueLeft[0],rightMiroir,rightPicSize[0],cropValueRight[0],initAltitude
        self.mntPath = mntPath 
        self.useLayerZ = useLayerZ
        self.oldMNTPath = ''
        self.dictPolyL = {}
        self.dictPolyR = {}
        self.running = True
        self.count = 0

    def run(self):
        while self.running : 
            if self.mntPath != '' :
                self.mntDS = gdal.Open(self.mntPath)
                self.mntBand = self.mntDS.GetRasterBand(1)
                self.mntGeo = self.mntDS.GetGeoTransform()
                self.mntSize = (self.mntDS.RasterXSize, self.mntDS.RasterYSize)
                self.mntNodata = self.mntBand.GetNoDataValue()
                self.pxStart = math.floor((self.rectCoord.xMinimum() - self.mntGeo[0]) / self.mntGeo[1]) 
                self.pyStart = math.floor((self.rectCoord.yMaximum() - self.mntGeo[3]) / self.mntGeo[5])
                #print('range mnt start : ' + str(self.pxStart)+ ' , ' +str(self.pyStart))
                #try : 
                pxEnd = math.floor((self.rectCoord.xMaximum() - self.mntGeo[0]) / self.mntGeo[1]) 
                pyEnd = math.floor((self.rectCoord.yMinimum() - self.mntGeo[3]) / self.mntGeo[5])
                #print('range mnt end : ' + str(pxEnd)+ ' , ' +str(pyEnd))
                sizeX = int(pxEnd-self.pxStart) if pxEnd < self.mntSize[0] else int(self.mntSize[0]-self.pxStart)
                sizeY = int(pyEnd-self.pyStart) if pyEnd < self.mntSize[1] else int(self.mntSize[1]-self.pyStart)
                try : self.mntArr = self.mntBand.ReadAsArray(self.pxStart,self.pyStart,sizeX,sizeY)
                except : self.mntArr = self.mntNodata
                #print(self.mntArr.shape)
                
            for layer in iface.mapCanvas().layers():
                try :
                    name = layer.name()
                    #print(name)
                    if layer.type() == QgsMapLayerType.VectorLayer and name in self.vectorToShow.keys() : 
                        
                        self.dictPolyL[name] = [[],self.vectorToShow[name],layer.geometryType()]
                        self.dictPolyR[name] = [[]]
                        #print(self.rectCoord)
                        features = layer.getFeatures(self.rectCoord)
            
                        for item in features : 
                            #try : 
                            featureGeo = item.geometry() 
                            self.count += 1
                            
                            if featureGeo.isNull() == False and featureGeo.type() == QgsWkbTypes.PolygonGeometry :

                                polygonL = QPolygonF()
                                polygonR = QPolygonF()
                                listPoint = []
                                for vertex in featureGeo.vertices():
                                    data = vertex
                                    if data.is3D() and self.useLayerZ : z = data.z()
                                    elif data.is3D() : z = self.getAltitude(data.x(), data.y(),z=data.z()) 
                                    else :  z = self.getAltitude(data.x(), data.y())
                                            
                                    xPixel, yPixel = self.leftManager.coordToPixel((data.x() , data.y()), z)
                                    
                                    pixL = (xPixel-self.keyVal[0], yPixel)            

                                    xPixel, yPixel = self.rightManager.coordToPixel((data.x() , data.y()), z)          
                                    if self.keyVal[1] == 1 :
                                        mirrorX = self.keyVal[2] - xPixel
                                        pixR = (mirrorX, yPixel)
                                    else : pixR = (xPixel-self.keyVal[3], yPixel)  
                                    
                                    polygonL.append(QPointF(pixL[0], pixL[1]))
                                    polygonR.append(QPointF(pixR[0], pixR[1]))

                                    if (data.x(),data.y()) in listPoint :
                                        self.dictPolyL[name][0].append(polygonL)
                                        self.dictPolyR[name][0].append(polygonR)
                                        polygonL = QPolygonF()
                                        polygonR = QPolygonF()
                                        listPoint = []

                                    else : listPoint.append((data.x(),data.y()))

                                self.dictPolyL[name][0].append(polygonL)
                                self.dictPolyR[name][0].append(polygonR)
                            elif featureGeo.isNull() == False and featureGeo.type() == QgsWkbTypes.PointGeometry :
                                data = featureGeo.constGet()
                                
                                if QgsWkbTypes.hasZ(featureGeo.wkbType()) and self.useLayerZ : z = data.z()
                                elif QgsWkbTypes.hasZ(featureGeo.wkbType()) : z = self.getAltitude(data.x(), data.y(),z=data.z()) 
                                else : z = self.getAltitude(data.x(), data.y())
                                #print(z)
                                        
                                xPixel, yPixel = self.leftManager.coordToPixel((data.x() , data.y()), z)
                                
                                pixL = (xPixel-self.keyVal[0], yPixel)            

                                xPixel, yPixel = self.rightManager.coordToPixel((data.x() , data.y()), z)          
                                if self.keyVal[1] == 1 :
                                    mirrorX = self.keyVal[2] - xPixel
                                    pixR = (mirrorX, yPixel)
                                else : pixR = (xPixel-self.keyVal[3], yPixel)  
                                
                                #polygonL.append(QPointF(pixL[0], pixL[1]))
                                #polygonR.append(QPointF(pixR[0], pixR[1]))

                                self.dictPolyL[name][0].append((pixL[0], pixL[1]))
                                self.dictPolyR[name][0].append((pixR[0], pixR[1]))
                        
                        #except : pass
                        #self.completed() #calculationDone.emit(self.dictPolyL,self.dictPolyR)
                    #self.running = False
                except Exception as e:
                    print(f"Error in thread: {e}")
                    traceback.print_exc()
            self.running = False
                
    #def join(self) : 
        #threading.Thread.join(self)
        #return (self.dictPolyL, self.dictPolyR)

    def getAltitude(self,x,y,z=None) : 
        mntAlt = None
    
        if self.mntPath != '' and  self.mntArr is not self.mntNodata:
            #if self.oldMNTPath != self.mntPath :
            #        self.mntDS = gdal.Open(self.mntPath)
            #        self.mntBand = self.mntDS.GetRasterBand(1)
            #        self.mntGeo = self.mntDS.GetGeoTransform()
            #        self.mntSize = (self.mntDS.RasterXSize, self.mntDS.RasterYSize)
            #        self.oldMNTPath = self.mntPath
            #else: pass

            pxPoint = math.floor((x - self.mntGeo[0]) / self.mntGeo[1]) 
            pyPoint = math.floor((y - self.mntGeo[3]) / self.mntGeo[5])
            #print('Point X : ' + str(pxPoint) + ', Point Y : ' + str(pyPoint))
            try : 
                #mntAlt = self.mntBand.ReadAsArray(pxPoint-self.pxStart,pyPoint-self.pyStart ,1,1)[0][0]
                
                #Array numpy l'axe Y en premier
                mntAlt = self.mntArr[pyPoint-self.pyStart,pxPoint-self.pxStart]
                #print(mntAlt)
                if mntAlt != self.mntNodata : 
                    return mntAlt

            except : pass
        
        if z is None  :
            pl = self.leftManager.coordToPixel((x,y), self.keyVal[4])
            pr = self.rightManager.coordToPixel((x,y), self.keyVal[4]) 
            mntAlt = self.dualManag.calculateZ(pl,pr)
        else : mntAlt = z
        
        return mntAlt

    def stop(self) : 
        self.running = False
