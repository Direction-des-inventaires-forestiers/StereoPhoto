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
    mouseClicked = pyqtSignal(Qt.MouseButton,tuple)
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
        
        self.ignoringSyntheticMove = False

        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.GeometryType.LineGeometry)
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(2)
        self.drawing = False
        self.activateDrawing = False
        
        self.borderRange = 150
        self.safeRect = None
        self.centerGlobalPos = None

        # 125Hz Timer (8ms) 
        self.sendPosTimer = QTimer()
        self.sendPosTimer.setInterval(8)
        self.sendPosTimer.setTimerType(Qt.PreciseTimer)
        self.sendPosTimer.timeout.connect(self.sendMouseMovePos)

        self.interceptor = keyboardInterceptor(self)

    def eventFilter(self, obj, event):

        if event.type() == QEvent.MouseMove:

            if self.ignoringSyntheticMove:
                return True 

            new_pixel_pos = event.pos()
            
            self.currentMouseCoord = self.toMapCoordinates(new_pixel_pos)
            self.lastMousePos = new_pixel_pos

            if self.safeRect and not self.safeRect.contains(new_pixel_pos):
                self.recenterMouse()
                return True 
            
            if self.drawing:
                mapPoint = self.currentMouseCoord
                if self.rubberBand.numberOfVertices() > 1:
                    self.rubberBand.movePoint(mapPoint)
                else:
                    self.rubberBand.addPoint(mapPoint)

        return False 

    def canvasPressEvent(self, event):
            
        mapPoint = self.toMapCoordinates(event.pos())   
        coordFormat = (float(mapPoint.x()), float(mapPoint.y())) 
        self.mouseClicked.emit(event.button(),coordFormat)
        
        if self.activateDrawing: 
            if event.button() == Qt.LeftButton:
                
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
        
        if self.ignoringSyntheticMove:
            return

        # Lock the filter and warp
        self.ignoringSyntheticMove = True   
        # Snap map to current coord
        self.canvas.setCenter(self.currentMouseCoord)
        self.canvas.refresh()
        
        QCursor.setPos(self.centerGlobalPos)        
        
        # Wait 20ms for OS to finish the jump before unlocking the filter
        QTimer.singleShot(20, self.clearSyntheticGuard) 
    
    def clearSyntheticGuard(self):
        self.ignoringSyntheticMove = False

    def sendMouseMovePos(self): 
        if self.currentMouseCoord != self.lastEmittedCoord:

            coordFormat = (float(self.currentMouseCoord.x()), float(self.currentMouseCoord.y()))
            self.mouseMoved.emit(coordFormat)
            self.lastEmittedCoord = self.currentMouseCoord

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
        self.activateMapTool()

    def activateMapTool(self) : 
        self.updateSafeZone()
        
        # Install trap on the viewport
        self.canvas.viewport().installEventFilter(self)
        self.canvas.setMouseTracking(True)
        
        if self.centerGlobalPos: 
            self.ignoringSyntheticMove = True        
            QCursor.setPos(self.centerGlobalPos)        
            QTimer.singleShot(20, self.clearSyntheticGuard) 
            
        self.sendPosTimer.start()
        qApp.installEventFilter(self.interceptor)
        self.canvas.setFocus()

    def deactivate(self):
        self.deactivateMapTool()
        super().deactivate()

    def deactivateMapTool(self) : 
        self.canvas.viewport().removeEventFilter(self)
        self.sendPosTimer.stop()
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
        qApp.removeEventFilter(self.interceptor)
        self.drawing = False
        

    def updateSafeZone(self):
        
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


#Autre méthode pour le mouse trap Windows seulement

'''
    # Windows cursor clip
    def _clip_windows(self):
        rect = self.canvas.rect()
        top_left = self.canvas.mapToGlobal(rect.topLeft())
        bottom_right = self.canvas.mapToGlobal(rect.bottomRight())
        class RECT(ctypes.Structure):
            _fields_ = [("left", ctypes.c_long),
                        ("top", ctypes.c_long),
                        ("right", ctypes.c_long),
                        ("bottom", ctypes.c_long)]
        r = RECT(top_left.x(), top_left.y(), bottom_right.x(), bottom_right.y())
        ctypes.windll.user32.ClipCursor(ctypes.byref(r))

    def _release_windows(self):
        ctypes.windll.user32.ClipCursor(None)

    '''