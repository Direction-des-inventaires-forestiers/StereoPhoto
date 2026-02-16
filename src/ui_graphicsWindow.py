from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import Qt
import os


class ImageRoot(QtWidgets.QGraphicsObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    def boundingRect(self):
        # Doesn't draw anything, but must exist
        return QtCore.QRectF()

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

        self.resetTileGroup(remove=False)

        self.imageRoot = ImageRoot()
        self.currentScale = 1

        self.cursor = CursorItem(radius=20)
        self.scene.addItem(self.cursor)



    def keyPressEvent(self, event):
        self.keyPressed.emit(event)
        #event.accept()
        #super().keyPressEvent(event)

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

    def custom_centerOn(self,target_scene_pos,scale) :
        view = self.ui.graphicsView
        view_center = view.viewport().rect().center()
        
        tx = view_center.x() - (target_scene_pos.x() * scale)
        ty = view_center.y() - (target_scene_pos.y() * scale)
        
        transform = QtGui.QTransform()
        transform.translate(tx, ty)
        transform.scale(scale, scale)
        
        view.setTransform(transform)
        
        self.centerCrosshair()
        
    def addPixmap(self,pixmap, scaleFactor, topX, topY,groupId) :
        if groupId == 0 : tileGroup = self.fullviewTileGroup 
        elif groupId == 1 : tileGroup = self.overviewTileGroup
        else : tileGroup = self.safetyTileGroup

        item = QtWidgets.QGraphicsPixmapItem(pixmap,self.imageRoot)
        item.setPos(topX, topY)
        item.setScale(scaleFactor)
        item.setTransformationMode(Qt.FastTransformation) 
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