import time

from qgis.core import QgsWkbTypes
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import (
    QCoreApplication,
    QEvent,
    QEventLoop,
    QObject,
    Qt,
    QTimer,
    pyqtSignal,
)
from qgis.PyQt.QtGui import QCursor, QKeyEvent
from qgis.PyQt.QtWidgets import qApp

from .config import (
    NAVIGATION_TRACE_RECENTRAGE_INTERVALLE_S,
    NAVIGATION_TRACE_RECENTRAGE_SEUIL_PAR_S,
    NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS,
    NAVIGATION_ZONE_SURE_COTE_MIN_PX,
    NAVIGATION_ZONE_SURE_MARGE_MAX_PX,
    NAVIGATION_ZONE_SURE_MARGE_MIN_PX,
    NAVIGATION_ZONE_SURE_MARGE_RATIO,
)
from .journal import avertir_utilisateur, obtenir_journal

journal = obtenir_journal(__name__)


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
    # Les modificateurs voyagent avec le clic : la sélection additive (Ctrl ou
    # Maj) en a besoin, et ils étaient perdus ici, event.modifiers() n'étant lu
    # que par la roulette.
    mouseClicked = pyqtSignal(Qt.MouseButton, tuple, Qt.KeyboardModifiers)
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

        # Comportement de navigation. False : les photos
        # défilent sous un curseur ramené au centre par recenterMouse().
        # True : le piège à souris est levé, le curseur parcourt les photos.
        # L'état est posé par stereoPhoto, qui porte le bouton de bascule.
        self.curseurLibre = False

        self.rubberBand = QgsRubberBand(
            self.canvas, QgsWkbTypes.GeometryType.LineGeometry
        )
        self.rubberBand.setColor(Qt.red)
        self.rubberBand.setWidth(2)
        self.drawing = False
        self.activateDrawing = False

        # Zone sûre du piège à souris. None : zone inutilisable, piège levé.
        self.safeRect = None
        self.centerGlobalPos = None

        # Vrai quand la zone est jugée inutilisable : porté à part de
        # safeRect, qui vaut aussi None avant le premier calcul.
        self.zoneSureLevee = False

        # Alerte de canevas trop petit : différée par cette minuterie, et
        # relancée à chaque recalcul tant que la condition tient (voir
        # updateSafeZone()). Le drapeau évite de répéter le message tant que le
        # canevas n'a pas retrouvé une zone utilisable.
        self.minuterieAlerteZoneSure = QTimer()
        self.minuterieAlerteZoneSure.setSingleShot(True)
        self.minuterieAlerteZoneSure.timeout.connect(self.avertirZoneSureLevee)
        self.alerteZoneSureAffichee = False

        # Diagnostic du piège (voir tracerRecentrages()).
        self.recentragesDepuisTrace = 0
        self.derniereTraceRecentrage = time.monotonic()

        # 125Hz Timer (8ms)
        # self.sendPosTimer = QTimer()
        # self.sendPosTimer.setInterval(16) #Diminuer à 60 hz
        # self.sendPosTimer.setTimerType(Qt.PreciseTimer)
        # self.sendPosTimer.timeout.connect(self.sendMouseMovePos)

        self.interceptor = keyboardInterceptor(self)

    def eventFilter(self, obj, event):

        if event.type() == QEvent.MouseMove:
            if self.ignoringSyntheticMove:
                return True

            new_pixel_pos = event.pos()

            self.currentMouseCoord = self.toMapCoordinates(new_pixel_pos)
            self.lastMousePos = new_pixel_pos

            if self.currentMouseCoord != self.lastEmittedCoord:
                coordFormat = (
                    float(self.currentMouseCoord.x()),
                    float(self.currentMouseCoord.y()),
                )
                self.mouseMoved.emit(coordFormat)
                self.lastEmittedCoord = self.currentMouseCoord

            if self.drawing:
                mapPoint = self.currentMouseCoord
                if self.rubberBand.numberOfVertices() > 1:
                    self.rubberBand.movePoint(mapPoint)
                else:
                    self.rubberBand.addPoint(mapPoint)

            # Piège à souris, propre au mode synchronisé : sorti de la zone
            # sûre, le curseur est ramené au centre et la carte suit.
            # `is not None` et non une évaluation booléenne : None est
            # désormais un état porté (zone jugée inutilisable, piège levé)
            # qu'il faut distinguer explicitement. Une zone vide était déjà
            # écartée par l'ancienne garde booléenne (PyQt5 rend un QRect vide
            # faux), mais silencieusement : le piège cessait d'agir sans que
            # rien ne le signale, et la course du curseur se trouvait limitée
            # à la taille du canevas.
            if (
                not self.curseurLibre
                and self.safeRect is not None
                and not self.safeRect.contains(new_pixel_pos)
            ):
                self.recenterMouse()
                return True

        return False

    def canvasPressEvent(self, event):

        mapPoint = self.toMapCoordinates(event.pos())
        coordFormat = (float(mapPoint.x()), float(mapPoint.y()))
        self.mouseClicked.emit(event.button(), coordFormat, event.modifiers())

        if self.activateDrawing:
            if event.button() == Qt.LeftButton:
                if not self.drawing:
                    self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
                    self.rubberBand.addPoint(mapPoint)
                    self.drawing = True
                else:
                    self.rubberBand.addPoint(mapPoint)

            elif event.button() == Qt.RightButton and self.drawing:
                self.reinitialiserTrace()

        event.accept()

    def reinitialiserTrace(self):
        """Efface la bande élastique du tracé en cours sur le canevas.

        Appelée au clic droit, mais aussi par `annulerTraceEnCours()` de
        stereoPhoto : le tracé s'abandonne au changement d'outil et
        au changement de modèle photo, et la bande élastique doit partir avec
        lui. Elle restait auparavant à l'écran, figurant un geste qui n'existait
        plus.
        """
        self.drawing = False
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)

    def recenterMouse(self):
        if self.curseurLibre:
            # Le curseur parcourt les photos : rien à recentrer.
            return

        if not self.centerGlobalPos or not self.currentMouseCoord:
            return

        if self.ignoringSyntheticMove:
            return

        self.tracerRecentrages()

        target_map_coord = self.currentMouseCoord

        # Lock the filter and warp
        self.ignoringSyntheticMove = True
        # Snap map to current coord
        self.canvas.setCenter(self.currentMouseCoord)
        self.canvas.refresh()

        QCursor.setPos(self.centerGlobalPos)

        self.currentMouseCoord = target_map_coord
        self.lastEmittedCoord = target_map_coord

        # Wait 20ms for OS to finish the jump before unlocking the filter
        # QTimer.singleShot(20, self.clearSyntheticGuard)
        QCoreApplication.processEvents(QEventLoop.ExcludeUserInputEvents)
        QTimer.singleShot(0, self.clearSyntheticGuard)

    def clearSyntheticGuard(self):
        self.ignoringSyntheticMove = False

    def sendMouseMovePos(self):
        if self.currentMouseCoord != self.lastEmittedCoord:
            coordFormat = (
                float(self.currentMouseCoord.x()),
                float(self.currentMouseCoord.y()),
            )
            self.mouseMoved.emit(coordFormat)
            self.lastEmittedCoord = self.currentMouseCoord

    def wheelEvent(self, event):
        factor = event.angleDelta().y()
        direction = -1 if factor < 0 else 1
        if event.modifiers() & Qt.ControlModifier:
            # Changer pour des fonctions plus flexible pour diminuer le zoom a plus petite échelle
            if direction == 1:
                self.canvas.zoomIn()
            else:
                self.canvas.zoomOut()
            self.canvas.refresh()

        coordFormat = (
            float(self.currentMouseCoord.x()),
            float(self.currentMouseCoord.y()),
        )
        self.wheelActivate.emit(direction, event.modifiers(), coordFormat)
        event.accept()

    def activate(self):
        super().activate()
        self.activateMapTool()

    def activateMapTool(self):
        self.updateSafeZone()

        # Install trap on the viewport
        self.canvas.viewport().installEventFilter(self)
        self.canvas.setMouseTracking(True)

        # Curseur amené au centre à l'activation, en mode synchronisé seulement :
        # en mode curseur libre, il doit rester là où le photo-interprète l'a mis.
        if self.centerGlobalPos and not self.curseurLibre:
            self.ignoringSyntheticMove = True
            QCursor.setPos(self.centerGlobalPos)
            QTimer.singleShot(20, self.clearSyntheticGuard)

        # self.sendPosTimer.start()
        qApp.installEventFilter(self.interceptor)
        self.canvas.setFocus()

    def deactivate(self):
        self.deactivateMapTool()
        super().deactivate()

    def deactivateMapTool(self):
        # L'alerte en attente tombe avec l'outil : la taille du canevas ne
        # demande plus rien à l'utilisateur dès que la navigation s'arrête.
        self.minuterieAlerteZoneSure.stop()
        self.canvas.viewport().removeEventFilter(self)
        # self.sendPosTimer.stop()
        self.rubberBand.reset(QgsWkbTypes.GeometryType.LineGeometry)
        qApp.removeEventFilter(self.interceptor)
        self.drawing = False

    def updateSafeZone(self):
        """Recalcule la zone sûre du piège à souris et le centre du canevas.

        La marge n'est pas une constante : une marge fixe de 150 px exige un
        canevas de plus de 300 px de côté, condition remplie au poste de
        stéréoscopie mais pas sur un canevas réduit par les panneaux latéraux.
        Elle suit donc une part de la dimension du canevas, bornée en pixels.

        Sous un côté minimal, la zone est jugée inutilisable et mise à None :
        le piège est levé pour ce canevas plutôt que de recentrer le curseur à
        chaque mouvement.

        La condition est portée au bandeau de QGIS par `avertirZoneSureLevee()`
        seulement, après un délai que la minuterie relance ici à chaque recalcul.
        Le canevas passe en effet par des tailles minuscules que personne ne
        voit : au montage de la fenêtre de QGIS, à l'ouverture du panneau de
        l'extension, et tout au long d'un déplacement de panneau latéral.
        Avertir sur l'état de passage remplissait le bandeau d'un message
        d'action impossible, le canevas étant déjà redevenu grand.
        """
        rect = self.canvas.viewport().rect()

        margeX = self.margeZoneSure(rect.width())
        margeY = self.margeZoneSure(rect.height())
        zone = rect.adjusted(margeX, margeY, -margeX, -margeY)

        if (
            zone.width() < NAVIGATION_ZONE_SURE_COTE_MIN_PX
            or zone.height() < NAVIGATION_ZONE_SURE_COTE_MIN_PX
        ):
            journal.debug(
                "Canevas de %dx%d px : zone sûre inutilisable, piège levé ; "
                "alerte différée de %d ms",
                rect.width(),
                rect.height(),
                NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS,
            )
            self.safeRect = None
            self.zoneSureLevee = True
            self.minuterieAlerteZoneSure.start(NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS)
        else:
            self.minuterieAlerteZoneSure.stop()
            if self.zoneSureLevee:
                # Le rétablissement reste au journal : l'utilisateur vient
                # d'agrandir le canevas, il n'a pas besoin qu'on le lui dise.
                journal.info(
                    "Canevas de %dx%d px : zone sûre de %dx%d px, "
                    "piège à souris rétabli.",
                    rect.width(),
                    rect.height(),
                    zone.width(),
                    zone.height(),
                )
            self.zoneSureLevee = False
            self.alerteZoneSureAffichee = False
            journal.debug(
                "Zone sûre : %dx%d px (marges %d/%d) pour un canevas de %dx%d px",
                zone.width(),
                zone.height(),
                margeX,
                margeY,
                rect.width(),
                rect.height(),
            )
            self.safeRect = zone

        self.centerGlobalPos = self.canvas.viewport().mapToGlobal(rect.center())

    def avertirZoneSureLevee(self):
        """Porte au bandeau de QGIS un canevas resté trop petit.

        Appelée par la minuterie de `updateSafeZone()`, donc seulement sur une
        condition qui tient depuis NAVIGATION_ZONE_SURE_ALERTE_DELAI_MS : la
        disposition de la fenêtre est stabilisée, et la taille annoncée est
        celle que l'utilisateur a réellement sous les yeux : elle est relue ici
        plutôt que reprise du calcul qui a armé la minuterie.

        Le message va au bandeau, et pas seulement au journal : la condition
        demande une action de l'utilisateur, et le journal n'est pas consulté en
        cours de photo-interprétation. Durée nulle : le message reste affiché
        jusqu'à ce qu'il le ferme.
        """
        if not self.zoneSureLevee or self.alerteZoneSureAffichee:
            # Canevas agrandi entre-temps, ou condition déjà signalée.
            return

        rect = self.canvas.viewport().rect()
        avertir_utilisateur(
            f"Canevas de {rect.width()}x{rect.height()} px trop petit "
            "pour la navigation : le curseur ne peut plus être ramené "
            "au centre et sa course est limitée à la largeur du "
            "canevas. Agrandir le canevas de QGIS en réduisant, repliant "
            "ou détachant les panneaux latéraux.",
            duree_secondes=0,
        )
        self.alerteZoneSureAffichee = True

    @staticmethod
    def margeZoneSure(dimension):
        """Marge (pixels) à retirer de chaque côté pour une dimension donnée."""
        marge = int(dimension * NAVIGATION_ZONE_SURE_MARGE_RATIO)
        marge = max(marge, NAVIGATION_ZONE_SURE_MARGE_MIN_PX)
        return min(marge, NAVIGATION_ZONE_SURE_MARGE_MAX_PX)

    def tracerRecentrages(self):
        """Compte les recentrages et en trace le taux, par intervalles.

        Un recentrage par mouvement de souris est le symptôme d'une zone sûre
        trop étroite : le curseur reste collé au centre et la carte n'avance
        plus que par pas d'un pixel. La trace est agrégée pour ne pas inonder
        le journal, et passe en information au-delà du taux attendu.
        """
        self.recentragesDepuisTrace += 1

        ecoule = time.monotonic() - self.derniereTraceRecentrage
        if ecoule < NAVIGATION_TRACE_RECENTRAGE_INTERVALLE_S:
            return

        taux = self.recentragesDepuisTrace / ecoule
        zone = (
            f"{self.safeRect.width()}x{self.safeRect.height()}"
            if self.safeRect is not None
            else "levée"
        )
        tracer = (
            journal.info
            if taux > NAVIGATION_TRACE_RECENTRAGE_SEUIL_PAR_S
            else journal.debug
        )
        tracer(
            "Piège à souris : %d recentrages en %.1f s (%.1f/s), zone sûre %s",
            self.recentragesDepuisTrace,
            ecoule,
            taux,
            zone,
        )

        self.recentragesDepuisTrace = 0
        self.derniereTraceRecentrage = time.monotonic()

    def canvasResizeEvent(self, event):
        self.updateSafeZone()

    def keyPressEvent(self, event):
        self.keybordSignal.emit(event)


# Autre méthode pour le mouse trap Windows seulement

"""
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

    """
