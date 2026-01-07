import os, math
from osgeo import gdal, ogr, osr
import numpy as np

def getParDict(dossierImages) :
    
    keywords = {
        "$PARAFFINE00": "affine",
        "$PARINVAFF00": "inverse_affine",
        "$FOC00": "focal",
        "$XYZ00": "camera position",
        "$OPK00": "orientation",
        "$PIXELSIZE": "pixel_size",
        "$FSCALE00": "fscale"
        }

    listpath = os.listdir(dossierImages)
    parDict = {}
    
    for i in listpath : 
        #On traite seulement les fichiers PAR du dossier
        if not i.endswith('.par') : continue
        
        pathPAR = os.path.join(dossierImages,i)

        pathImg = os.path.join(dossierImages,i[:-4]+'.tif')
        #L'image associée n'existe pas, on rejète le PAR
        if not os.path.exists(pathImg) : continue
        else : 
            imgDS = gdal.Open(pathImg,gdal.GA_ReadOnly)
            sizeImg = (imgDS.RasterXSize, imgDS.RasterYSize)
            imgDS = None
        
        try:
            with open(pathPAR, encoding='utf-8') as f:
                lines = f.read().splitlines()
        except:
            with open(pathPAR, encoding='ansi') as f:
                lines = f.read().splitlines()

        values = {}
        for line in lines:
            for key in keywords:
                if line.startswith(key):
                    values[key] = line.split()
                    break
        
        #Vérification des paramètres obligatoires, le fichier PAR sera ignoré si un paramètre est absent
        if not all(key in values for key in ['$PARAFFINE00','$PARINVAFF00','$FOC00','$XYZ00','$OPK00']) : continue
        
        affine = [float(val) for val in values["$PARAFFINE00"][-6:]]
        AffineA, AffineB, AffineC, AffineD, AffineE, AffineF = affine

        Focal = float(values["$FOC00"][-1])

        X0, Y0, Z0 = [float(val) for val in values["$XYZ00"][-3:]]
        omega, phi, kappa = [float(val) for val in values["$OPK00"][-3:]]

        if "$PIXELSIZE" in values:
            pixelSize = float(values["$PIXELSIZE"][-1]) * 1e-3
        else :
            pixelSize = AffineA 

        if "$FSCALE00" in values:   
            fscale = float(values["$FSCALE00"][-1]) * 1e-3
        else : 
            fscale = Z0/Focal
        
        threshold_deg=10
        if (abs(kappa - 90) < threshold_deg) or (abs(kappa + 90) < threshold_deg):
            longSensor = abs(sizeImg[1] * pixelSize)
            hautSensor = abs(sizeImg[0] * pixelSize)
        else : 
            longSensor = abs(sizeImg[0] * pixelSize)
            hautSensor = abs(sizeImg[1] * pixelSize)
        
        longGroundFscale = (longSensor * fscale)
        hautGroundFscale = (hautSensor * fscale)
        
        bbox = (X0,Y0,X0-longGroundFscale/2,Y0-hautGroundFscale/2,X0+longGroundFscale/2,Y0+hautGroundFscale/2)# xmin, ymin, xmax, ymax 
        #save_bbox_to_gpkg(bbox,dossierImages+'/'+i[:-4]+'.gpkg')
        parDict[i[:-4]] = bbox
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



def compute_overlap(bbox1, bbox2):
    xmin1, ymin1, xmax1, ymax1 = bbox1[2], bbox1[3], bbox1[4], bbox1[5]
    xmin2, ymin2, xmax2, ymax2 = bbox2[2], bbox2[3], bbox2[4], bbox2[5]

    overlap_xmin = max(xmin1, xmin2)
    overlap_ymin = max(ymin1, ymin2)
    overlap_xmax = min(xmax1, xmax2)
    overlap_ymax = min(ymax1, ymax2)

    x_overlap = max(0, overlap_xmax - overlap_xmin)
    y_overlap = max(0, overlap_ymax - overlap_ymin)
    overlap_area = x_overlap * y_overlap

    if overlap_area == 0:
        return 0.0, None

    area1 = (xmax1 - xmin1) * (ymax1 - ymin1)
    area2 = (xmax2 - xmin2) * (ymax2 - ymin2)

    overlap_ratio = overlap_area / min(area1, area2)
    overlap_bbox = (overlap_xmin, overlap_ymin, overlap_xmax, overlap_ymax)

    return overlap_ratio, overlap_bbox


def get_neighbors_and_pairs(parID, parDict, direction_buffer=500):
    
    bbox_ref = parDict[parID]
    x0 = bbox_ref[0] 
    y0 = bbox_ref[1]

    best_horizontal_pair = {"leftPic": (None,0), "rightPic": (None,0)}

    best_left = (None, 0, float('inf'))
    best_right = (None, 0, float('inf'))

    up_candidates = []
    down_candidates = []

    for key, bbox in parDict.items():
        if key == parID: continue
        
        x1 = bbox[0] 
        y1 = bbox[1] 

        dx = x1 - x0
        dy = y1 - y0

        dist = math.sqrt(dx**2 + dy**2)

        overlap_ratio, overlap_bbox = compute_overlap(bbox_ref, bbox)

        if abs(dy) < direction_buffer :
            if dx < 0 :
                if overlap_ratio > best_left[1]:
                    best_left = (key, overlap_ratio, dist)
                elif overlap_ratio == 0 and dist < best_left[2] :  
                 best_left = (key, overlap_ratio, dist)
            elif dx > 0 :
                if overlap_ratio > best_right[1]:
                    best_right = (key, overlap_ratio, dist)
                elif overlap_ratio == 0 and dist < best_right[2] :  
                    best_right = (key, overlap_ratio, dist)

        if overlap_ratio > 0.05:
            if dy > direction_buffer:  # up
                up_candidates.append((key, overlap_ratio, dy))
            elif dy < -direction_buffer:  # down
                down_candidates.append((key, overlap_ratio, dy))
        
        if overlap_ratio == 0: continue

        if dx < 0 and overlap_ratio > best_horizontal_pair["leftPic"][1] and abs(dy) < direction_buffer:
            best_horizontal_pair["leftPic"] = (key, overlap_ratio)

        elif dx > 0 and overlap_ratio > best_horizontal_pair["rightPic"][1] and abs(dy) < direction_buffer:
            best_horizontal_pair["rightPic"] = (key, overlap_ratio)

    # Sort up/down candidates by descending overlap, then closest in dy
    up_sorted = sorted(up_candidates, key=lambda x: (-x[1], abs(x[2])))[:2]
    down_sorted = sorted(down_candidates, key=lambda x: (-x[1], abs(x[2])))[:2]

    return {
        "leftPic": best_horizontal_pair["leftPic"],
        "rightPic": best_horizontal_pair["rightPic"],
        "left": best_left,
        "right": best_right,
        "up": up_sorted,
        "down": down_sorted
    }



def save_bbox_to_gpkg(bbox, gpkg_path, layer_name="bbox", crs_epsg=2948):

    if os.path.exists(gpkg_path):
        os.remove(gpkg_path)
    
    driver = ogr.GetDriverByName("GPKG")
    datasource = driver.CreateDataSource(gpkg_path)

    srs = osr.SpatialReference()
    srs.ImportFromEPSG(crs_epsg)

    layer = datasource.CreateLayer(layer_name, srs, ogr.wkbPolygon)

    field = ogr.FieldDefn("id", ogr.OFTInteger)
    layer.CreateField(field)

    _,_,xmin, ymin, xmax, ymax = bbox
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(xmin, ymin)
    ring.AddPoint(xmax, ymin)
    ring.AddPoint(xmax, ymax)
    ring.AddPoint(xmin, ymax)
    ring.AddPoint(xmin, ymin)

    poly = ogr.Geometry(ogr.wkbPolygon)
    poly.AddGeometry(ring)

    feature_defn = layer.GetLayerDefn()
    feature = ogr.Feature(feature_defn)
    feature.SetGeometry(poly)
    feature.SetField("id", 1)
    layer.CreateFeature(feature)

    feature = None
    datasource = None
    print(f"BBox saved to {gpkg_path} as layer '{layer_name}'")

#from qgis.gui import *
#from qgis.core import *
#from qgis.utils import iface
#from qgis.PyQt.QtWidgets import *
#from qgis.PyQt.QtCore import *
#from qgis.PyQt.QtGui import *

def createShapePoint(shapeName, epsg):
    
    #
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    fields.append(QgsField("name", QVariant.String))
    shapeName = 'E:\\point/pointFromPicture.shp'
    epsg = 'EPSG:2950'
    
    vectorWriter = QgsVectorFileWriter(shapeName, "System", fields, QgsWkbTypes.MultiPoint, QgsCoordinateReferenceSystem(epsg), "ESRI Shapefile")
    points = getParDict('E:\\mtm8')
    for key, value in points.items() :
        
        feature = QgsFeature(fields)
        feature.setAttribute(1,str(key))
        geo = QgsGeometry.fromPointXY(QgsPointXY(value[0],value[1]))
        feature.setGeometry(geo)
        vectorWriter.addFeature(feature)
    #return vectorWriter
    
#createShapePoint('a','A')    
'''
a = getParDict('E:/Probleme_photos_paysage/fonctionne_pas_MTM6')
result = get_neighbors_and_pairs("Q24226_002_NIR", a)
print(result)
leftBbox = a["q18067_172_rgb"]
rightBbox = a[result["rightPic"][0]]
overlap, bboxOverlap = compute_overlap(leftBbox, rightBbox)

gpz = 0.199998

x1Start = (bboxOverlap[0] - leftBbox[2])/gpz
x1End = (bboxOverlap[2] - leftBbox[4])/gpz
y1Start = (bboxOverlap[1] - leftBbox[3])/gpz
y1End = (bboxOverlap[3] - leftBbox[5])/gpz
x2Start = (bboxOverlap[0] - rightBbox[2])/gpz
x2End = (bboxOverlap[2] - rightBbox[4])/gpz
y2Start = (bboxOverlap[1] - rightBbox[3])/gpz
y2End = (bboxOverlap[3] - rightBbox[5])/gpz

x1Startw = (bboxOverlap[0] - leftBbox[2])/gpz
x1Endw = (bboxOverlap[2] - leftBbox[2])/gpz
y1Startw = (bboxOverlap[1] - leftBbox[3])/gpz
y1Endw = (bboxOverlap[3] - leftBbox[3])/gpz

x2Startw = (bboxOverlap[0] - rightBbox[2])/gpz
x2Endw = (bboxOverlap[2] - rightBbox[2])/gpz
y2Startw = (bboxOverlap[1] - rightBbox[3])/gpz
y2Endw = (bboxOverlap[3] - rightBbox[3])/gpz


xStartL = int((bboxOverlap[0] - leftBbox[2]) / gpz)
yStartL = int((leftBbox[5] - bboxOverlap[3]) / gpz)

xEndL   = int((bboxOverlap[2] - leftBbox[2]) / gpz)
yEndL   = int((leftBbox[5] - bboxOverlap[1]) / gpz)

xStartR = int((bboxOverlap[0] - rightBbox[2]) / gpz)
yStartR = int((rightBbox[5] - bboxOverlap[3]) / gpz)

xEndR   = int((bboxOverlap[2] - rightBbox[2]) / gpz)
yEndR   = int((rightBbox[5] - bboxOverlap[1]) / gpz)

exit()
'''