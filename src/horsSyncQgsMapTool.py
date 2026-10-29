# -*- coding: utf-8 -*-
"""Outil de carte de l'état hors-synchronisation.

Avant ce module, la touche ESC retirait l'outil de navigation du canevas
(`unsetMapTool`) : l'état atteint n'était pas un mode mais une absence d'outil,
plus aucun code de l'extension ne s'exécutait, et les trois fonctions attendues
dans cet état (zoom à la roulette, navigation « main », changement automatique
de modèle à la limite) étaient irréalisables.

Cet outil occupe cette place. Il garde de `navigationMapTool` le seul couplage
aux vues photo qui existe, les signaux Qt, et laisse tomber ce qui gêne hors
navigation :

- pas de filtre d'événements posé sur `qApp` : les raccourcis natifs de QGIS
  répondent de nouveau ;
- pas de piège à souris : le curseur sort librement du canevas ;
- pas de tracé : l'édition reste à la navigation synchronisée.

Choisir un outil de QGIS dans sa barre d'outils remplace celui-ci, comme pour
n'importe quel outil de carte. `ESC` ramène à la navigation synchronisée.
"""

from qgis.core import QgsPointXY
from qgis.gui import QgsMapTool
from qgis.PyQt.QtCore import Qt, pyqtSignal


class horsSyncMapTool(QgsMapTool):
    """Zoom, pan « main » et retour, dans l'état atteint après ESC."""

    # Le canevas a déjà bougé quand ces signaux partent : stereoPhoto n'a qu'à
    # réaligner les deux vues photo sur lui.
    panDemande = pyqtSignal()
    zoomDemande = pyqtSignal()
    retourSynchronise = pyqtSignal()

    def __init__(self, canvas):
        super().__init__(canvas)
        self.canvas = canvas
        # Point de la carte saisi sous le curseur au début du geste de pan.
        # Il reste sous le curseur pendant tout le déplacement.
        self.ancrePan = None

    def canvasPressEvent(self, event):
        # Bouton du milieu : convention de QGIS et d'ArcGIS, hypothèse à
        # confirmer à la DIF aux tests manuels.
        if event.button() == Qt.MiddleButton:
            self.ancrePan = self.toMapCoordinates(event.pos())
            self.canvas.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def canvasMoveEvent(self, event):
        if self.ancrePan is None:
            return

        positionCourante = self.toMapCoordinates(event.pos())
        dx = self.ancrePan.x() - positionCourante.x()
        dy = self.ancrePan.y() - positionCourante.y()
        if dx == 0 and dy == 0:
            return

        # Déplacer le centre de l'écart ramène le point d'ancrage sous le
        # curseur : c'est ce qui donne la sensation de tirer la carte.
        centre = self.canvas.center()
        self.canvas.setCenter(QgsPointXY(centre.x() + dx, centre.y() + dy))
        self.canvas.refresh()

        self.panDemande.emit()
        event.accept()

    def canvasReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self.ancrePan is not None:
            self.ancrePan = None
            self.canvas.setCursor(Qt.ArrowCursor)
            event.accept()

    def wheelEvent(self, event):
        # La roulette seule zoome ici, alors qu'elle règle la
        # parallaxe en navigation synchronisée. Le photo-interprète ne règle
        # pas la parallaxe dans un état où les photos ne suivent plus.
        if event.angleDelta().y() < 0:
            self.canvas.zoomOut()
        else:
            self.canvas.zoomIn()
        self.canvas.refresh()

        self.zoomDemande.emit()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.retourSynchronise.emit()
            event.accept()

    def deactivate(self):
        self.ancrePan = None
        super().deactivate()
