from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.core import Qgis, QgsPointXY, QgsWkbTypes

class keyboardInterceptor(QObject):
    def __init__(self, tool):
        super().__init__()
        self.tool = tool

    def eventFilter(self, obj, event):
        if event.type() in [QEvent.ShortcutOverride, QEvent.KeyPress]:
            event.accept()
            self.tool.keyPressEvent(event)
            return True
        return False

class navigationMapTool(QgsMapTool):
    mouseClicked = pyqtSignal()
    mouseMoved = pyqtSignal(tuple)
    wheelActivate = pyqtSignal(int, Qt.KeyboardModifier, tuple)
    keybordSignal = pyqtSignal(QKeyEvent)

    def __init__(self, canvas, iface): 
        super().__init__(canvas)
        self.canvas = canvas
        self.iface = iface
        self.lastMousePos = None
        self.currentMouseCoord = None
        self.lastEmittedCoord = None
        
        # This flag prevents the tool from freezing during recentering
        self.ignoringSyntheticMove = False

        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.GeometryType.LineGeometry)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(2)
        self.drawing = False
        self.activateDrawing = True
        
        self.borderRange = 150 # Larger border for 3D comfort
        self.safeRect = None
        self.centerGlobalPos = None

        # 125Hz Timer (8ms) for butter-smooth stereoscopic panning
        self.sendPosTimer = QTimer()
        self.sendPosTimer.setInterval(8)
        self.sendPosTimer.setTimerType(Qt.PreciseTimer)
        self.sendPosTimer.timeout.connect(self.sendMouseMovePos)

        self.interceptor = keyboardInterceptor(self)

    def eventFilter(self, obj, event):
        """
        This is the new "Trap" logic. 
        It replaces canvasMoveEvent for the centering check.
        """
        if event.type() == QEvent.MouseMove:
            # 1. Kill the loop: if we are currently warping, ignore this event
            if self.ignoringSyntheticMove:
                return True 

            new_pixel_pos = event.pos()
            
            # Update coordinates for the timer
            self.currentMouseCoord = self.toMapCoordinates(new_pixel_pos)
            self.lastMousePos = new_pixel_pos

            # 2. The Trap: If we cross the border, warp back
            if self.safeRect and not self.safeRect.contains(new_pixel_pos):
                self.recenterMouse()
                return True # Swallow the event so the mouse never 'leaves'
            
            # 3. Handle Rubberband drawing during the move
            if self.drawing:
                mapPoint = self.currentMouseCoord
                if self.rubberBand.numberOfVertices() > 1:
                    self.rubberBand.movePoint(mapPoint)
                else:
                    self.rubberBand.addPoint(mapPoint)

        return False # Let clicks/wheel pass through

    def canvasPressEvent(self, event):
        if event.button() == Qt.LeftButton: 
            self.mouseClicked.emit()

        if self.activateDrawing: 
            if event.button() == Qt.LeftButton:
                mapPoint = self.toMapCoordinates(event.pos())
                if not self.drawing:
                    self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
                    self.rubberBand.addPoint(mapPoint)
                    self.drawing = True
                else:
                    self.rubberBand.addPoint(mapPoint)
            elif event.button() == Qt.RightButton and self.drawing:
                self.drawing = False
                self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
        event.accept()

    def recenterMouse(self):
        if not self.centerGlobalPos or not self.currentMouseCoord:
            return

        # Snap map to current coord
        self.canvas.setCenter(self.currentMouseCoord)
        self.canvas.refresh()
            
        # Lock the filter and warp
        self.ignoringSyntheticMove = True        
        QCursor.setPos(self.centerGlobalPos)        
        
        # Wait 20ms for OS to finish the jump before unlocking the filter
        QTimer.singleShot(20, self.clearSyntheticGuard) 
    
    def clearSyntheticGuard(self):
        self.ignoringSyntheticMove = False

    def sendMouseMovePos(self): 
        if self.currentMouseCoord != self.lastEmittedCoord:
            # Emit floats for sub-pixel accuracy in GraphicsView
            coordFormat = (float(self.currentMouseCoord.x()), float(self.currentMouseCoord.y()))
            self.mouseMoved.emit(coordFormat)
            self.lastEmittedCoord = QgsPointXY(self.currentMouseCoord)

    def wheelEvent(self, event):
        factor = event.angleDelta().y()
        direction = -1 if factor < 0 else 1
        if event.modifiers() & Qt.ControlModifier:
            if direction == 1: self.canvas.zoomIn()
            else: self.canvas.zoomOut()
            self.canvas.refresh()

        coordFormat = (float(self.currentMouseCoord.x()), float(self.currentMouseCoord.y()))
        self.wheelActivate.emit(direction, event.modifiers(), coordFormat)
        event.accept()

    def activate(self):
        super().activate()
        self.updateSafeZone()
        
        # Install trap on the viewport
        self.canvas.viewport().installEventFilter(self)
        self.canvas.setMouseTracking(True)
        
        if self.centerGlobalPos: 
            self.ignoringSyntheticMove = True        
            QCursor.setPos(self.centerGlobalPos)        
            QTimer.singleShot(20, self.clearSyntheticGuard) 
            
        self.sendPosTimer.start()
        self.canvas.setFocus()
        self.iface.mainWindow().installEventFilter(self.interceptor)

    def deactivate(self):
        self.canvas.viewport().removeEventFilter(self)
        self.sendPosTimer.stop()
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
        self.iface.mainWindow().removeEventFilter(self.interceptor)
        super().deactivate()

    def updateSafeZone(self):
        # Always use viewport for coordinate trapping
        rect = self.canvas.viewport().rect()
        self.safeRect = rect.adjusted(
            self.borderRange, self.borderRange,
            -self.borderRange, -self.borderRange
        )
        self.centerGlobalPos = self.canvas.viewport().mapToGlobal(rect.center())

    def canvasResizeEvent(self, event):
        self.updateSafeZone()

    def keyPressEvent(self, event):
        self.keybordSignal.emit(event)
