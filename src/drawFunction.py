"""Projection des couches vectorielles dans les deux vues photo.

Le code d'origine a été réalisé par Frédérick Pineault
(frederick.pineault@mffp.gouv.qc.ca).

Ce module ne porte plus qu'une seule chose : le fil `calculatePolygon`, qui lit
les couches vectorielles affichées et projette leurs géométries en coordonnées
pixel des deux photos, pour que `stereoPhoto` les dessine dans les scènes.

Les primitives d'écriture qui s'y trouvaient (ajout, fusion, découpage,
remodelage) sont parties dans `editionVecteur.py` : elles écrivaient par le
fournisseur de données, hors du tampon d'édition, donc hors d'atteinte de
l'annulation. Le remodelage et la trace automatique, dont aucun appel n'était
actif, sont retirés en attendant d'être repris.

Chaque forme projetée est accompagnée de l'identifiant de l'entité dont elle
vient, et chaque couche de son identifiant de couche : c'est la condition pour
que la surbrillance de la sélection puisse désigner, dans les vues photo, la
même entité que la sélection de QGIS. Une entité multipartie donne plusieurs
formes portant le même identifiant.
"""

from qgis.core import (
    QgsMapLayerType,
    QgsWkbTypes,
)
from qgis.utils import iface
from qgis.PyQt.QtCore import QPointF, QThread
from qgis.PyQt.QtGui import QPainterPath, QPolygonF

import math
from .lectureRaster import fenetre_mnt, ouvrir_raster
from .journal import obtenir_journal
from .worldManager import pictureManager, dualManager

# Journal du module; le préfixe « _ » le réserve à l'usage interne
_journal = obtenir_journal(__name__)


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
                # cette taille est une indexation valide : il désigne une
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
