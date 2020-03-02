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
    - Utiliser un shapefile déjà importé dans QGIS et afficher la région concernée 
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
def getVectorLayer():
    return iface.activeLayer()

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

#Découpe la couche en fonction d'une ligne tracer par l'utilisateur
def cutPolygon(vectorLayer, line):
    #p1 = p2 = QgsPointXY(float, float)
    #line = [p1, p2, ...]
    vectorLayer.startEditing()
    vectorLayer.removeSelection()
    vectorLayer.splitFeatures(line)
    vectorLayer.commitChanges()

#Lorsqu'un nouveau polygon entre en contact avec un polygon existant
#Le nouveau est conservé dans son entièreter et l'ancien est reformé pour laisser la place au nouveau
def automaticPolygon(oldGeo, currentIndex, newGeo, vectorLayer):
    vectorLayer.startEditing()
    finalGeo =  oldGeo.difference(newGeo)
    #Séparer les polygons en différente entité à changer
    vectorLayer.changeGeometry(currentIndex, finalGeo)
    feat = QgsFeature()
    feat.setGeometry(newGeo)
    vectorLayer.dataProvider().addFeature(feat)
    vectorLayer.commitChanges()
