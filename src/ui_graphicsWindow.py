from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt
import os


class ImageRoot(QtWidgets.QGraphicsObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def boundingRect(self):
        return QtCore.QRectF(-100000, -100000, 200000, 200000)

    def paint(self, painter, option, widget=None):
        pass

class CursorItem(QtWidgets.QGraphicsItem):
    def __init__(self, radius=20):
        super().__init__()
        self.r = radius
        self.setZValue(1000)  # ALWAYS on top

        self.setFlags(QtWidgets.QGraphicsItem.ItemIgnoresTransformations)
        self.setCacheMode(QtWidgets.QGraphicsItem.NoCache)

    def boundingRect(self):
        pad = 3
        r = self.r + pad
        return QtCore.QRectF(-r, -r, 2*r, 2*r)

    def paint(self, painter, option, widget=None):
        pen = QtGui.QPen(QtGui.QColor(0, 255, 255), 3)
        painter.setPen(pen)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.drawLine(-self.r, 0, self.r, 0)
        painter.drawLine(0, -self.r, 0, self.r)

class Ui_graphicsWindow(object):
    def setupUi(self, graphicsWindow):
        graphicsWindow.setObjectName("graphicsWindow")

        self.centralwidget = QtWidgets.QWidget(graphicsWindow)
        layout = QtWidgets.QVBoxLayout(self.centralwidget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.graphicsView = QtWidgets.QGraphicsView(self.centralwidget)

        fmt = QtGui.QSurfaceFormat()
        fmt.setSamples(4)  # Anti-aliasing for the tiles
        
        self.gl_viewport = QtWidgets.QOpenGLWidget()
        self.gl_viewport.setFormat(fmt)
        self.graphicsView.setViewport(self.gl_viewport)

        
        self.graphicsView.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.graphicsView.setRenderHint(QtGui.QPainter.SmoothPixmapTransform)
        self.graphicsView.setRenderHint(QtGui.QPainter.Antialiasing)
        self.graphicsView.setBackgroundBrush(QtGui.QColor(182, 182, 182))

        self.graphicsView.setViewportUpdateMode(QtWidgets.QGraphicsView.FullViewportUpdate)
        self.graphicsView.setTransformationAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.graphicsView.setResizeAnchor(QtWidgets.QGraphicsView.NoAnchor)
        self.graphicsView.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        layout.addWidget(self.graphicsView)
        graphicsWindow.setCentralWidget(self.centralwidget)


class graphicsWindow(QtWidgets.QMainWindow):
    keyPressed = QtCore.pyqtSignal(QtGui.QKeyEvent)

    def __init__(self):
        super().__init__()

        self.ui = Ui_graphicsWindow()
        self.ui.setupUi(self)

        self.scene = QtWidgets.QGraphicsScene(self)
        self.scene.setSceneRect(-100000, -100000, 200000, 200000)
        self.scene.setItemIndexMethod(QtWidgets.QGraphicsScene.NoIndex)
        self.ui.graphicsView.setScene(self.scene)

        self.imageRoot = ImageRoot()
        self.scene.addItem(self.imageRoot)

        self.resetTileGroup(remove=False)

        self.geometryItemGroup = QtWidgets.QGraphicsItemGroup()
        self.geometryItemGroup.setZValue(100)
        self.scene.addItem(self.geometryItemGroup)

        self.offboundRectGroup = QtWidgets.QGraphicsItemGroup()
        self.offboundRectGroup.setZValue(200)
        self.scene.addItem(self.offboundRectGroup)

        self.drawingLineGroup = QtWidgets.QGraphicsItemGroup()
        self.drawingLineGroup.setZValue(300)
        self.scene.addItem(self.drawingLineGroup)

        self.cursor = CursorItem(radius=20)
        self.scene.addItem(self.cursor)

        self.tileGroupAction = 'safety'

    def keyPressEvent(self, event):
        self.keyPressed.emit(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.centerCrosshair()

    def showEvent(self, event):
        super().showEvent(event)
        self.centerCrosshair()

    def centerCrosshair(self):
        view = self.ui.graphicsView
        scene_center = view.mapToScene(view.viewport().rect().center())
        self.cursor.prepareGeometryChange()
        self.cursor.setPos(scene_center)

    def findScaleAction(self, scale):
        if scale < 0.1:   return 'safety'
        elif scale < 0.5: return 'overview'
        else:             return 'full'

    
    def custom_centerOn(self, target_scene_pos, scale, forceGroupCall=False):
        view = self.ui.graphicsView

        #Le centrage passe par centerOn() et non par une translation intégrée à
        #la transformation de la vue. Cette translation n'amène la cible au centre
        #que si le décalage de défilement est nul, ce qui n'est jamais garanti :
        #la scène fait 200 000 px, les barres de défilement sont masquées mais
        #conservent leur valeur, et NoAnchor fait que setTransform() ne réancre
        #rien. Le décalage résiduel persistait d'un chargement de paire au
        #suivant et faisait dériver la vue de plusieurs dizaines de milliers de
        #pixels hors de l'image (affichage gris, aucune tuile chargée).
        transform = QtGui.QTransform()
        transform.scale(scale, scale)
        view.setTransform(transform)
        view.centerOn(target_scene_pos)

        self.centerCrosshair()

        newAction = self.findScaleAction(scale)
        if self.tileGroupAction != newAction or forceGroupCall:
            self.manageTileGroupViewing(newAction)
            self.tileGroupAction = newAction

    def addPixmap(self, q_img, scaleX, scaleY, topX, topY, groupId):
        if groupId == 0 : tileGroup = self.fullviewTileGroup 
        elif groupId == 1 : tileGroup = self.overviewTileGroup
        else : tileGroup = self.safetyTileGroup

        #q_img = QtGui.QImage(tile.data, tile.shape[1], tile.shape[0],tile.shape[1]*3, QtGui.QImage.Format_RGB888).copy()
        pixmap = QtGui.QPixmap.fromImage(q_img)

        item = QtWidgets.QGraphicsPixmapItem(pixmap, self.imageRoot)
        item.setTransformationMode(Qt.FastTransformation)
        item.setPos(topX, topY)
        #setScale() est isotrope : on passe par une transformation pour appliquer
        #une échelle distincte sur chaque axe.
        item.setTransform(QtGui.QTransform().scale(scaleX, scaleY))
        tileGroup.addToGroup(item)
        

    def resetTileGroup(self,remove=True) :

        if remove : 
            self.scene.removeItem(self.fullviewTileGroup)
            self.scene.removeItem(self.overviewTileGroup)
            self.scene.removeItem(self.safetyTileGroup)


        self.fullviewTileGroup = QtWidgets.QGraphicsItemGroup()
        self.fullviewTileGroup.setZValue(0)
        self.scene.addItem(self.fullviewTileGroup)

        self.overviewTileGroup = QtWidgets.QGraphicsItemGroup()
        self.overviewTileGroup.setZValue(0)
        self.scene.addItem(self.overviewTileGroup)

        self.safetyTileGroup = QtWidgets.QGraphicsItemGroup()
        self.safetyTileGroup.setZValue(-100)
        self.scene.addItem(self.safetyTileGroup)

        self.imageRoot.setTransform(QtGui.QTransform())

    def manageTileGroupViewing(self, action='full'):
        if action == 'full':
            self.fullviewTileGroup.show()
            self.overviewTileGroup.hide()
            self.safetyTileGroup.show() 

        elif action == 'overview':
            self.fullviewTileGroup.hide()
            self.overviewTileGroup.show()
            self.safetyTileGroup.show()

        elif action == 'safety':
            self.fullviewTileGroup.hide()
            self.overviewTileGroup.hide()
            self.safetyTileGroup.show()


