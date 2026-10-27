"""
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
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsMapLayerType,
    QgsVectorFileWriter,
    QgsVectorLayerEditUtils,
    QgsWkbTypes,
)
from qgis.utils import iface
from qgis.PyQt.QtCore import QPointF, QThread, QVariant
from qgis.PyQt.QtGui import QPainterPath, QPolygonF

import math
from .lectureRaster import fenetre_mnt, ouvrir_raster
from .journal import obtenir_journal
from .worldManager import pictureManager, dualManager

# Journal du module; le préfixe « _ » le réserve à l'usage interne
_journal = obtenir_journal(__name__)


# Création d'un vector layer dans QGIS
# Ajout d'un ID pour être similaire à la création normale de QGIS
def createShape(shapeName, EPSG):
    # shapeName = "U:/StereoPhoto/ShapeFile/TestLayer.shp"
    fields = QgsFields()
    fields.append(QgsField("id", QVariant.Int))
    feature = QgsFeature()
    vectorWriter = QgsVectorFileWriter(
        shapeName,
        "System",
        fields,
        QgsWkbTypes.MultiPolygon,
        QgsCoordinateReferenceSystem(EPSG),
        "ESRI Shapefile",
    )
    vectorWriter.addFeature(feature)
    del vectorWriter
    vectorLayer = iface.addVectorLayer(shapeName, "", "ogr")
    return vectorLayer


# Future fonction propose la liste des current layers et choisir parmis la liste ou tout simplement créer une nouvelle couche
# Pour le moment, elle retourne la couche active
def getVectorActiveLayer():
    return iface.activeLayer()


def getRectPolygon(rect, vectorLayer):
    return list(vectorLayer.getFeatures(rect))


# Ajout d'un polygon sur la couche
# Avec geometry comme intrant on considère déja un QgsGeometry
def addPolygon(vectorLayer, geometry):
    vectorLayer.startEditing()
    feat = QgsFeature()
    feat.setGeometry(geometry)
    vectorLayer.dataProvider().addFeature(feat)
    vectorLayer.commitChanges()


# Fusion 2 polygones ensemble
def mergePolygon(currentGeo, currentIndex, extraGeo, vectorLayer):
    vectorLayer.startEditing()
    newGeo = currentGeo.combine(extraGeo)
    vectorLayer.changeGeometry(currentIndex, newGeo)
    vectorLayer.commitChanges()
    return newGeo


def reshapeLayer(lineString, listFeatures, vectorLayer):
    vectorLayer.startEditing()
    for feat in listFeatures:
        geo = feat.geometry()
        _journal.debug("reshapeLayer : géométrie initiale %s", geo)
        retval = geo.reshapeGeometry(lineString)
        if retval == 0:
            _journal.debug("reshapeLayer : géométrie remodelée %s", geo)
            vectorLayer.changeGeometry(feat.id(), geo)
        else:
            _journal.warning("reshapeLayer : reshapeGeometry a retourné %s", retval)
    vectorLayer.commitChanges()


# Découpe la couche en fonction d'une ligne tracer par l'utilisateur
# Si les lignes tracées se croisent aucune coupe à lieu (IDEM à QGIS)
def cutPolygon(vectorLayer, line):
    if len(line) < 2:
        return

    # splitLineGeometry = QgsGeometry.fromPolylineXY(line)
    vectorLayer.startEditing()
    vectorLayer.removeSelection()
    # vectorLayer.splitFeatures(line)
    editUtils = QgsVectorLayerEditUtils(vectorLayer)
    result_code = editUtils.splitFeatures(line)

    if result_code == 0:
        vectorLayer.commitChanges()


# Lorsqu'un nouveau polygon entre en contact avec un polygon existant
# Le nouveau est conservé dans son entièreté et l'ancien est reformé pour laisser la place au nouveau
def automaticPolygon(oldGeo, currentIndex, newGeo, vectorLayer):
    vectorLayer.startEditing()
    finalGeo = oldGeo.difference(newGeo)

    firstShape = True
    for item in finalGeo.asGeometryCollection():
        if firstShape:
            vectorLayer.changeGeometry(currentIndex, item)
            firstShape = False
        else:
            feat = QgsFeature()
            feat.setGeometry(item)
            vectorLayer.dataProvider().addFeature(feat)

    feat = QgsFeature()
    feat.setGeometry(newGeo)
    vectorLayer.dataProvider().addFeature(feat)
    vectorLayer.commitChanges()


def addPoint(vectorLayer, geometry):
    vectorLayer.startEditing()

    feature = QgsFeature()
    # geom = QgsGeometry()
    feature.setGeometry(geometry)
    feature.setFields(vectorLayer.fields())

    vectorLayer.dataProvider().addFeature(feature)
    vectorLayer.commitChanges()
    vectorLayer.triggerRepaint()

    return feature


class calculatePolygon(QThread):
    def __init__(
        self, vectorToShow, rectCoord, leftPicMan, rightPicMan, initAltitude, mntPath
    ):
        QThread.__init__(self)
        # self.features = featList
        self.vectorToShow = vectorToShow
        self.rectCoord = rectCoord
        self.leftManager = pictureManager(leftPicMan[0], leftPicMan[1])
        self.rightManager = pictureManager(rightPicMan[0], rightPicMan[1])
        self.dualManag = dualManager(self.leftManager, self.rightManager)
        self.initAltitude = initAltitude
        self.mntPath = mntPath
        self.useLayerZ = False
        self.oldMNTPath = ""
        self.dictPolyL = {}
        self.dictPolyR = {}
        self.running = True
        self.count = 0
        # Nombre de sommets dont l'altitude n'a pu être lue dans la fenêtre de MNT
        # chargée; résumé une seule fois à la fin du traitement (voir run()).
        self.nbSommetsHorsMNT = 0

    def run(self):
        while self.running:
            if self.mntPath != "":
                self.mntDS = ouvrir_raster(self.mntPath)
                if self.mntDS is None:
                    # Sans MNT lisible, les altitudes reviennent au calcul
                    # stéréoscopique. Le chemin est vidé plutôt que de laisser
                    # getAltitude() chercher une fenêtre qui n'existe pas : il
                    # compterait alors chaque sommet comme hors MNT, et le
                    # résumé de fin de traitement désignerait une mauvaise
                    # cause. L'avertissement nommant le fichier est déjà au
                    # journal, posé par ouvrir_raster().
                    self.mntPath = ""

            if self.mntPath != "":
                self.mntBand = self.mntDS.GetRasterBand(1)
                self.mntGeo = self.mntDS.GetGeoTransform()
                self.mntSize = (self.mntDS.RasterXSize, self.mntDS.RasterYSize)
                self.mntNodata = self.mntBand.GetNoDataValue()

                # Même fenêtre, même garde que du côté du panneau d'options :
                # le bornage au raster précède l'allocation. Le calcul remplacé
                # allouait d'abord, et un MNT dont le pas n'est pas dans
                # l'unité de l'emprise faisait demander des pétaoctets.
                # pxStart et pyStart sont l'origine de la fenêtre retenue,
                # celle à laquelle getAltitude() rapporte ses indices.
                self.mntArr, self.pxStart, self.pyStart = fenetre_mnt(
                    self.mntBand,
                    self.mntGeo,
                    self.mntSize,
                    (
                        self.rectCoord.xMinimum(),
                        self.rectCoord.yMinimum(),
                        self.rectCoord.xMaximum(),
                        self.rectCoord.yMaximum(),
                    ),
                    self.mntNodata,
                    self.mntPath,
                )

            for layer in iface.mapCanvas().layers():
                try:
                    name = layer.name()
                    if name not in self.vectorToShow:
                        continue
                    couleur = self.vectorToShow[name][0]
                    self.useLayerZ = self.vectorToShow[name][1]

                    if (
                        layer.type() == QgsMapLayerType.VectorLayer
                        and name in self.vectorToShow.keys()
                    ):
                        # [formes, couleur, type de géométrie, identifiants
                        # des entités, identifiant de la couche]. Les
                        # identifiants sont parallèles aux formes : une entité
                        # multipartie en porte plusieurs, toutes sous le même
                        # identifiant.
                        self.dictPolyL[name] = [
                            [],
                            couleur,
                            layer.geometryType(),
                            [],
                            layer.id(),
                        ]
                        self.dictPolyR[name] = [[]]
                        features = layer.getFeatures(self.rectCoord)

                        for item in features:
                            # try :
                            featureGeo = item.geometry()
                            constGeo = featureGeo.constGet()
                            self.count += 1
                            dataToUse = []
                            if featureGeo.isMultipart():
                                for p in constGeo.parts():
                                    dataToUse.append(p)
                            else:
                                dataToUse.append(constGeo)

                            if (
                                not featureGeo.isNull()
                                and featureGeo.type() == QgsWkbTypes.PolygonGeometry
                            ):
                                for part in dataToUse:
                                    polygonL = QPolygonF()
                                    polygonR = QPolygonF()
                                    # Avoir si il est nécessaire d'ajouter les anneaux internes
                                    # Normalement l'anneau interne existe comme anneaux externe d'un autre polygon
                                    # for i in range(constGeo.numInteriorRings()):
                                    #   inner = constGeo.interiorRing(i)

                                    exteriorRing = part.exteriorRing()
                                    for data in exteriorRing.points():
                                        pixL, pixR = self.pointToPix(
                                            data, featureGeo.wkbType()
                                        )

                                        polygonL.append(QPointF(pixL[0], pixL[1]))
                                        polygonR.append(QPointF(pixR[0], pixR[1]))

                                    self.dictPolyL[name][0].append(polygonL)
                                    self.dictPolyR[name][0].append(polygonR)
                                    self.dictPolyL[name][3].append(item.id())
                            elif (
                                not featureGeo.isNull()
                                and featureGeo.type() == QgsWkbTypes.LineGeometry
                            ):
                                for part in dataToUse:
                                    lineL = QPainterPath()
                                    lineR = QPainterPath()
                                    # constGeo = featureGeo.constGet()
                                    first = True
                                    for data in part.points():
                                        pixL, pixR = self.pointToPix(
                                            data, featureGeo.wkbType()
                                        )

                                        if first:
                                            lineL.moveTo(QPointF(pixL[0], pixL[1]))
                                            lineR.moveTo(QPointF(pixR[0], pixR[1]))
                                            first = False
                                        else:
                                            lineL.lineTo(QPointF(pixL[0], pixL[1]))
                                            lineR.lineTo(QPointF(pixR[0], pixR[1]))

                                    self.dictPolyL[name][0].append(lineL)
                                    self.dictPolyR[name][0].append(lineR)
                                    self.dictPolyL[name][3].append(item.id())

                            elif (
                                not featureGeo.isNull()
                                and featureGeo.type() == QgsWkbTypes.PointGeometry
                            ):
                                for data in dataToUse:
                                    pixL, pixR = self.pointToPix(
                                        data, featureGeo.wkbType()
                                    )

                                    self.dictPolyL[name][0].append((pixL[0], pixL[1]))
                                    self.dictPolyR[name][0].append((pixR[0], pixR[1]))
                                    self.dictPolyL[name][3].append(item.id())

                except Exception:
                    _journal.exception("Erreur dans le thread de calcul des polygones")
            if self.nbSommetsHorsMNT:
                _journal.warning(
                    "%s sommets sans altitude dans la fenêtre de MNT"
                    " chargée; altitude calculée par stéréoscopie",
                    self.nbSommetsHorsMNT,
                )
                self.nbSommetsHorsMNT = 0
            self.running = False

    def pointToPix(self, point, geotype):

        if QgsWkbTypes.hasZ(geotype):
            if self.useLayerZ:
                z = point.z()
            else:
                z = self.getAltitude(point.x(), point.y(), z=point.z())
        else:
            z = self.getAltitude(point.x(), point.y())

        xPixel, yPixel = self.leftManager.coordToPixel((point.x(), point.y()), z)
        # keyVal  = cropValueLeft,rightMiroir,rightPicSize[0],cropValueRight,initAltitude
        pixL = (xPixel, yPixel)

        xPixel, yPixel = self.rightManager.coordToPixel((point.x(), point.y()), z)

        pixR = (xPixel, yPixel)

        return pixL, pixR

    def getAltitude(self, x, y, z=None):
        mntAlt = None

        if self.mntPath != "":
            fenetre = getattr(self, "mntArr", None)

            try:
                pxPoint = math.floor((x - self.mntGeo[0]) / self.mntGeo[1])
                pyPoint = math.floor((y - self.mntGeo[3]) / self.mntGeo[5])

                # Array numpy : l'axe Y en premier
                iy = pyPoint - self.pyStart
                ix = pxPoint - self.pxStart

                # Bornes explicites sur les deux indices, et non un `except` sur
                # l'indexation : numpy ne lève que pour un indice supérieur ou
                # égal à la taille de l'axe. Un indice négatif compris dans
                # cette taille est une indexation valide — il désigne une
                # cellule à partir de la fin de l'axe. Un sommet sorti au nord
                # ou à l'ouest de la fenêtre chargée recevait ainsi l'altitude
                # du bord opposé du MNT : sans lever, sans être compté, et sans
                # retomber sur le calcul stéréoscopique. C'est la forme que
                # readMNTWithCoord() emploie déjà de son côté.
                if (
                    fenetre is not None
                    and 0 <= iy < fenetre.shape[0]
                    and 0 <= ix < fenetre.shape[1]
                ):
                    mntAlt = fenetre[iy, ix]
                    if mntAlt != self.mntNodata:
                        return mntAlt
                else:
                    # Sommet hors de la fenêtre de MNT chargée. Appelé une fois
                    # par sommet : jamais de trace par sommet au-delà du niveau
                    # débogage, un seul résumé à la fin du traitement.
                    self.nbSommetsHorsMNT += 1
                    _journal.debug("Sommet hors de la fenêtre de MNT en (%s, %s)", x, y)

            except Exception:
                # Le calcul d'indice ou la lecture a échoué : le sommet est
                # traité comme hors MNT plutôt que d'interrompre le thread de
                # calcul des géométries pour un seul point.
                self.nbSommetsHorsMNT += 1
                _journal.debug(
                    "Lecture du MNT impossible en (%s, %s)", x, y, exc_info=True
                )

        if z is None:
            pl = self.leftManager.coordToPixel((x, y), self.initAltitude)
            pr = self.rightManager.coordToPixel((x, y), self.initAltitude)
            mntAlt = self.dualManag.calculateZ(pl, pr)
        else:
            mntAlt = z

        return mntAlt

    def stop(self):
        self.running = False
