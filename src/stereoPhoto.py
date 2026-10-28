"""
L'entièreté du code a été réalisé par Frédérick Pineault (frederick.pineault@mffp.gouv.qc.ca)

Ce dossier contient une classe de type QApplication qui permet l'affichage d'images de grandes tailles sur des
écrans de type Planar

La classe stereoPhoto gère l'application complète via un interface utilisateur
L'application permet de :
    - Importer des fichiers TIF de grandes tailles via un drag n drop
    - Réaliser une rotation de 90°, 180° et 270°
    - Réaliser un effet miroir sur l'horizontal et la verticale
    - Afficher les deux images importées
    - Superposer automatiquement les images en fonction d'un pourcentage choisi par l'utilisateur
    - Offrir une interface de navigation qui permet le déplacement, le zoom (CTRL+Roulette) et le traçage (Click & 1,2,3,ESC)
    - Offrir un déplacement de l'image de droite pour ajuster l'altitude (Roulette)
    - Rehausser les couleurs des images via une nouvelle fenêtre intéractive
    - Traçage de forme géolocalisée
    - Communication avec QGIS
    - Utiliser un shapefile 2D déjà importé dans QGIS et afficher la région concernée
    - Afficher le Z du centre de l'image
    - Afficher les coordonnées XYZ lors d'un clic
    - Permettre le choix des écrans
    - Utiliser un shapefile 3D

Le main permet tout simplement de lancer l'application

Plusieurs autres outils seront intégrés à cette application dans le futur :
    - Fonctionnalité de trace supplémentaire
    - Amélioration des fonctions de photogrammétrie
    - Menu de choix de paramètres (curseur, keybinding, couleur des traces)
    - Affichage des zones supersposées seulement
    - Gestion de projet

    et bien d'autre
Dans EFOTO, il semble avoir un décalage de 16 pixels en x et en y pour la photo de droite right/leftcursoroffset -> pourrait s'appliquer pour le curseur


"""

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsGeometry,
    QgsLineString,
    QgsPoint,
    QgsPointXY,
    QgsPolygon,
    QgsProject,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.PyQt.QtCore import (
    QEvent,
    QLineF,
    QPointF,
    QRectF,
    Qt,
    QThread,
)
from qgis.PyQt.QtGui import (
    QBrush,
    QColor,
    QGuiApplication,
    QIcon,
    QPen,
    QTransform,
)
from qgis.PyQt.QtWidgets import (
    QAction,
    QActionGroup,
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsRectItem,
    QMessageBox,
)

from . import resources  # noqa: F401  (enregistre les icônes auprès de Qt)

from .ui_graphicsWindow import graphicsWindow
from .ui_getVectorLayer import getImageListDialog
from .worldManager import pictureManager, dualManager
from .enhanceManager import enhanceManager, threadShow
from .drawFunction import calculatePolygon
from . import editionOutils
from . import editionVecteur
from .navigationQgsMapTool import navigationMapTool
from .horsSyncQgsMapTool import horsSyncMapTool
from .ui_widgetStereoPhoto import optionWindow

from .gestionDossier import (
    getParDict,
    get_neighbors_and_pairs,
    findPairWithCoord,
    compute_overlap,
)
from .orientationModele import directionProchainModele
from .config import (
    DONNEES_SCR_EPSG,
    EDITION_OUTIL_PAR_DEFAUT,
    EDITION_SELECTION_COULEUR,
    EDITION_SELECTION_PEN_WIDTH_PX,
    EDITION_SELECTION_TOLERANCE_PX,
    NAVIGATION_ARRET_THREAD_DELAI_MAX_MS,
    NAVIGATION_CURSEUR_LIBRE_PAR_DEFAUT,
    PAR_CAMERA_ORIENTATION_TOLERANCE_DEG,
    DRAW_LINE_PEN_WIDTH_PX,
    GEOMETRY_PEN_WIDTH_PX,
    GEOMETRY_POINT_RADIUS_PX,
)
from .journal import (
    initialiser_journal,
    fermer_journal,
    obtenir_journal,
    avertir_utilisateur,
)
import logging
import os
import math


class stereoPhoto(object):
    # Traduction des boutons de Qt et des types de géométrie de QGIS vers les
    # clés de editionOutils, qui ne connaît ni l'un ni l'autre. La frontière
    # est ici, et nulle part ailleurs.
    BOUTONS_QT = {
        Qt.LeftButton: editionOutils.BOUTON_GAUCHE,
        Qt.RightButton: editionOutils.BOUTON_DROIT,
        Qt.MiddleButton: editionOutils.BOUTON_MILIEU,
    }

    TYPES_GEOMETRIE_QGIS = {
        QgsWkbTypes.PointGeometry: editionOutils.TYPE_POINT,
        QgsWkbTypes.LineGeometry: editionOutils.TYPE_LIGNE,
        QgsWkbTypes.PolygonGeometry: editionOutils.TYPE_POLYGONE,
    }

    # Fonction d'initilisation
    def __init__(self, iface):
        self.iface = iface
        self.canvas = self.iface.mapCanvas()

        # Journalisation : appelée à chaque construction du plugin, donc aussi à
        # chaque rechargement. initialiser_journal() retire les handlers déjà
        # posés, ce qui évite les lignes en double et les fichiers verrouillés.
        initialiser_journal()
        self.journal = obtenir_journal(__name__)

    # Place le bouton de l'application dans QGIS
    def initGui(self):

        self.toolbarST = self.iface.addToolBar("StereoPhoto Toolbar")
        self.toolbarST.setObjectName("StereoPhotoToolbar")

        iconOuvrirMenu = ":/Anaglyph/Icons/OuvrirMenu.png"
        self.actionMainMenu = QAction(
            QIcon(iconOuvrirMenu), "Ouvrir le menu principal", self.iface.mainWindow()
        )

        self.actionMainMenu.setCheckable(True)
        self.actionMainMenu.toggled.connect(self.run)

        iconSuivreMNT = ":/Anaglyph/Icons/SuivreMNT.png"
        self.actionSuivreMNT = QAction(
            QIcon(iconSuivreMNT),
            "Suivre le MNT (touche M)",
            self.iface.mainWindow(),
        )

        self.actionSuivreMNT.setCheckable(True)

        iconUnlockCursor = ":/Anaglyph/Icons/UnlockCursor.png"
        self.actionUnlockCursor = QAction(
            QIcon(iconUnlockCursor),
            "Débarrer le curseur (touche C)",
            self.iface.mainWindow(),
        )

        self.actionUnlockCursor.setCheckable(True)
        self.actionUnlockCursor.setChecked(NAVIGATION_CURSEUR_LIBRE_PAR_DEFAUT)
        # Connexion posée ici, et non dans setConnection() : l'action survit à
        # la fermeture de la session, alors que setConnection() est rejouée à
        # chaque ouverture et empilerait les connexions.
        self.actionUnlockCursor.toggled.connect(self.basculerCurseurLibre)

        # Outils d'édition. Un groupe exclusif : un seul outil
        # actif à la fois, comme la barre d'édition de QGIS. Les icônes sont
        # prises au thème de QGIS, le dossier Icons/ n'en portant aucune
        # d'approchant et toute addition imposant de régénérer resources.py.
        # Les connexions sont posées ici, et non dans setConnection(), pour la
        # même raison que celle d'actionUnlockCursor ci-dessus.
        self.groupeOutils = QActionGroup(self.iface.mainWindow())
        self.groupeOutils.setExclusive(True)
        self.actionsOutil = {}
        for cle, libelle, icone in (
            (
                editionOutils.OUTIL_SELECTIONNER,
                "Sélectionner une entité ; clic droit : vider la sélection",
                "/mActionSelectRectangle.svg",
            ),
            (
                editionOutils.OUTIL_AJOUTER,
                "Ajouter une entité ; clic droit : clore le tracé",
                "/mActionCapturePolygon.svg",
            ),
            (
                editionOutils.OUTIL_COMBINER,
                "Combiner : clic gauche pour désigner, clic droit pour fusionner",
                "/mActionMergeFeatures.svg",
            ),
            (
                editionOutils.OUTIL_DECOUPER,
                "Découper ; touche 1 : alterne avec Ajouter",
                "/mActionSplitFeatures.svg",
            ),
        ):
            action = QAction(
                QgsApplication.getThemeIcon(icone), libelle, self.iface.mainWindow()
            )
            action.setCheckable(True)
            action.setData(cle)
            # Nommée pour qu'une table de raccourcis configurables la désigne.
            action.setObjectName("stereophoto_outil_" + cle)
            self.groupeOutils.addAction(action)
            self.actionsOutil[cle] = action

        self.groupeOutils.triggered.connect(self.changerOutilActif)

        self.outilActif = EDITION_OUTIL_PAR_DEFAUT
        if self.outilActif not in self.actionsOutil:
            self.journal.warning(
                "EDITION_OUTIL_PAR_DEFAUT vaut %r, qui n'est pas un outil connu ;"
                " repli sur %r",
                self.outilActif,
                editionOutils.OUTIL_AJOUTER,
            )
            self.outilActif = editionOutils.OUTIL_AJOUTER
        self.actionsOutil[self.outilActif].setChecked(True)

        # Enregistrement et annulation : la session d'édition reste ouverte
        # pendant le travail, et c'est l'utilisateur qui décide quand écrire.
        # L'intercepteur clavier de la navigation avalant les raccourcis natifs
        # de QGIS, ces deux gestes n'ont pas d'autre accès.
        self.actionEnregistrerEdition = QAction(
            QgsApplication.getThemeIcon("/mActionSaveEdits.svg"),
            "Enregistrer les modifications de la couche (Ctrl+S)",
            self.iface.mainWindow(),
        )
        self.actionEnregistrerEdition.setObjectName("stereophoto_enregistrer_edition")
        self.actionEnregistrerEdition.setEnabled(False)
        self.actionEnregistrerEdition.triggered.connect(self.enregistrerEdition)

        self.actionAnnulerEdition = QAction(
            QgsApplication.getThemeIcon("/mActionUndo.svg"),
            "Annuler le dernier geste d'édition (Ctrl+Z)",
            self.iface.mainWindow(),
        )
        self.actionAnnulerEdition.setObjectName("stereophoto_annuler_edition")
        self.actionAnnulerEdition.setEnabled(False)
        self.actionAnnulerEdition.triggered.connect(self.annulerEdition)

        self.toolbarST.addAction(self.actionMainMenu)
        self.toolbarST.addAction(self.actionSuivreMNT)
        self.toolbarST.addAction(self.actionUnlockCursor)
        self.toolbarST.addSeparator()
        for cle in editionOutils.OUTILS:
            self.toolbarST.addAction(self.actionsOutil[cle])
        self.toolbarST.addSeparator()
        self.toolbarST.addAction(self.actionEnregistrerEdition)
        self.toolbarST.addAction(self.actionAnnulerEdition)

        self.iface.addPluginToMenu("&StereoPhoto", self.actionMainMenu)

        # Raccordement au projet posé ici, et non dans setConnection() : le
        # projet est un singleton qui survit aux sessions, et setConnection()
        # étant rejouée à chaque ouverture, les connexions s'y empileraient.
        QgsProject.instance().cleared.connect(self.projetChange)

    # Retire le bouton de l'application dans QGIS
    def unload(self):
        try:
            QgsProject.instance().cleared.disconnect(self.projetChange)
        except TypeError:
            # Connexion déjà rompue : cas normal si initGui() n'a pas tourné.
            self.journal.debug("Aucun raccordement au projet à rompre")

        self.iface.removePluginMenu("&StereoPhoto", self.actionMainMenu)
        # self.iface.removeToolBarIcon(self.actionMainMenu)

        if hasattr(self, "toolbarST"):
            self.iface.mainWindow().removeToolBar(self.toolbarST)
            self.toolbarST.deleteLater()

        # L'extension se décharge, la couche reste : son tampon d'édition
        # survit dans QGIS. Rien n'est enregistré ici, mais la trace évite de
        # chercher des modifications perdues qui ne le sont pas.
        enAttente, nombre = editionVecteur.modificationsEnAttente(
            getattr(self, "vectorLayer", None)
        )
        if enAttente:
            self.journal.info(
                "%d modification(s) laissée(s) en attente dans QGIS au "
                "déchargement de l'extension",
                nombre,
            )

        self.journal.info("Extension déchargée")
        fermer_journal()

    # Initialisation de l'application et des variables
    # Connection entre les boutons du menu d'options (mOpt) et leurs fonctions attitrées
    # Ouverture du menu d'options
    def run(self):

        if self.actionMainMenu.isChecked():
            self.initGlobalParam()

            self.optWindow = optionWindow(self.iface)
            self.navigMapTool = navigationMapTool(self.canvas, self.iface)
            # Outil de l'état hors-synchronisation : posé sur le canevas par
            # windowHandler("qgis") là où l'outil était retiré.
            self.horsSyncMapTool = horsSyncMapTool(self.canvas)
            # L'outil est neuf à chaque ouverture : il reprend le comportement
            # de navigation que porte le bouton de la barre d'outils.
            self.navigMapTool.curseurLibre = self.actionUnlockCursor.isChecked()

            self.setConnection()
            # Le SCR est vérifié à l'affichage des photos, par
            # createGraphicsWindows(), et non ici. L'ouverture du menu principal
            # ne transforme aucune coordonnée : vérifier le SCR à cet instant
            # avertissait, et remplaçait le SCR du projet, sur un projet que
            # l'utilisateur n'a pas fini de monter, souvent un projet neuf
            # encore en WGS 84 dont les couches arrivent après.
            self.optWindow.loadParamFile()
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.optWindow)
            self.optWindow.raise_()
            self.journal.info("Session ouverte")

        else:
            self.iface.removeDockWidget(self.optWindow)
            self.optWindowClose()
            del self.optWindow
            try:
                del self.currentParDict
            except AttributeError:
                # Aucun dossier de photos n'avait été ouvert : cas normal.
                self.journal.debug("Aucun dictionnaire PAR à libérer à la fermeture")
            self.journal.info("Session fermée")

    def initGlobalParam(self):

        self.enableDraw = False
        self.enableShow = False
        self.ignoreMouseAction = False
        self.fermetureEnCours = False
        self.fermetureSessionEnCours = False

        self.zoomClick = False
        self.longClick = False

        # Vrai dès qu'un sommet est posé et jusqu'à la clôture du tracé.
        # Remplace firstDrawClick, qui décrivait un clic alors que le reste du
        # code l'interrogeait comme un état de geste.
        self.traceEnCours = False
        self.list3DPoint = []

        self.vectorLayer = None
        self.vectorLayerName = None

        # Table des traitements : un dictionnaire de méthodes liées, et non un
        # getattr dynamique, pour que le contrôle de style et le test de forme
        # voient les noms.
        self.tableTraitements = {
            editionOutils.TRAITEMENT_SELECTIONNER: self.selectionner,
            editionOutils.TRAITEMENT_VIDER_SELECTION: self.viderSelection,
            editionOutils.TRAITEMENT_AJOUTER_POINT: self.ajouterPoint,
            editionOutils.TRAITEMENT_POSER_SOMMET: self.poserSommet,
            editionOutils.TRAITEMENT_CLORE_LIGNE: self.cloreLigne,
            editionOutils.TRAITEMENT_CLORE_POLYGONE: self.clorePolygone,
            editionOutils.TRAITEMENT_CLORE_DECOUPE: self.cloreDecoupe,
            editionOutils.TRAITEMENT_FUSIONNER: self.fusionnerSelection,
        }

        # Un seul avertissement d'altitude indéterminée par série de clics :
        # sans ce drapeau, dix clics donnaient dix bandeaux. Remis à faux dès
        # que l'altitude redevient déterminée.
        self.altitudeRefusSignalee = False

        # Couche dont les signaux d'édition sont raccordés, pour les rompre
        # avant d'en raccorder une autre et ne pas empiler les connexions.
        self.coucheRaccordee = None

        self.listLeftLineObj = []
        self.listRightLineObj = []
        self.currentLeftLineObj = None
        self.currentRightLineObj = None

        self.tSeekLeft = None
        self.tSeekRight = None

        # Threads d'affichage dont l'arrêt a dépassé le délai d'attente :
        # conservés ici le temps qu'ils se terminent, pour que Qt ne détruise
        # pas un QThread en cours d'exécution (voir arreterThreadAffichage).
        self.threadsEnArret = []

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}

        self.buttonPosition = None
        self.buttonMapUnit = None

        self.cursorAltitude = None
        self.isLoadingPair = False

        # Vrai entre ESC et le retour aux photos : les vues ne suivent plus le
        # curseur, elles suivent le canevas de QGIS.
        self.horsSynchronisation = False

    def setConnection(self):

        self.optWindow.ui.importLineProject.textChanged.connect(self.newPictureFile)
        self.optWindow.ui.importLineVectorLayer.textChanged.connect(
            self.mNewVectorLayer
        )
        self.optWindow.ui.pushButtonShowPicture.clicked.connect(
            self.createGraphicsWindows
        )
        self.optWindow.ui.pushButtonShowIDList.clicked.connect(self.showIDList)
        self.optWindow.ui.enhanceButton.clicked.connect(self.enhanceClick)
        self.optWindow.ui.pushButtonFindBestPair.clicked.connect(
            self.findPairWithPosition
        )
        self.optWindow.closeWindow.connect(self.optWindowClose)
        self.optWindow.ui.pushButtonCloseWindow.clicked.connect(
            self.closeAllSideWindows
        )

        # Les radios Dessiner et Découper remontent vers l'outil actif ; la
        # synchronisation descendante passe par synchroniserRadiosTrace(), qui
        # bloque leurs signaux le temps de les accorder.
        self.optWindow.ui.radioButtonDraw.toggled.connect(self.radioTraceBasculee)
        self.optWindow.ui.radioButtonCut.toggled.connect(self.radioTraceBasculee)

        self.navigMapTool.mouseClicked.connect(self.mousePressEvent)
        self.navigMapTool.wheelActivate.connect(self.wheelActionEvent)
        self.navigMapTool.mouseMoved.connect(self.mouseMoveEvent)
        self.navigMapTool.keybordSignal.connect(self.keyboardHandler)

        self.horsSyncMapTool.panDemande.connect(self.suivreCanevasHorsSync)
        self.horsSyncMapTool.zoomDemande.connect(self.zoomerHorsSync)
        self.horsSyncMapTool.retourSynchronise.connect(self.retourNavigationPhoto)

    # Fonction appelée lors de la fermeture du mOpt
    # Si l'on ferme le mOpt toutes les autres fenêtres Qt se ferment
    def closeAllSideWindows(self):
        # Garde de réentrance : fermer une fenêtre fille fait circuler les
        # événements Qt, et la fermeture peut revenir ici par un autre chemin
        # (bouton de fermeture, closeEvent du mOpt, changement de projet).
        # Au second passage, les attributs étaient déjà retirés, d'où
        # l'AttributeError sur enhanceManager.
        if self.fermetureEnCours:
            return
        self.fermetureEnCours = True
        try:
            self.enableShow = False
            self.canvas.unsetMapTool(self.navigMapTool)
            self.canvas.unsetMapTool(self.horsSyncMapTool)
            self.horsSynchronisation = False
            # Le tracé est abandonné tant que les scènes existent encore :
            # après la démolition, ses traits ne seraient plus retirables.
            self.annulerTraceEnCours()
            self.removeCurrentScene()
            self.deleteOldPolygon()
            # L'attribut est retiré avant l'appel de fermeture : ainsi l'état
            # reste cohérent même si cet appel redonne la main à Qt.
            graphWindowLeft = self.__dict__.pop("graphWindowLeft", None)
            if graphWindowLeft is not None:
                graphWindowLeft.close()
            graphWindowRight = self.__dict__.pop("graphWindowRight", None)
            if graphWindowRight is not None:
                graphWindowRight.close()
            gestionRehaussement = self.__dict__.pop("enhanceManager", None)
            if gestionRehaussement is not None:
                gestionRehaussement.cancelEnhance()
            self.optWindow.ui.pushButtonCloseWindow.setEnabled(False)
            self.optWindow.saveParamFile()
        finally:
            self.fermetureEnCours = False

    def projetChange(self):
        """Ferme la session de navigation quand le projet est vidé ou remplacé.

        QGIS émet `cleared` avant de lire un nouveau projet, comme à la demande
        d'un projet neuf. Sans ce raccordement, rien ne s'exécutait : les deux
        vues photo restaient ouvertes en plein écran sur un projet qui n'a plus
        le SCR des photos ni leurs couches, l'outil de navigation restait posé
        sur ce canevas, ramenant le symptôme de la navigation figée puisque
        verifierScrProjet() n'est rejouée qu'à l'affichage des photos, et
        les paramètres de la session étaient perdus.
        """
        if not self.actionMainMenu.isChecked():
            # Aucune session ouverte : le projet peut changer librement.
            return

        self.journal.info("Projet vidé ou remplacé : fermeture de la session")
        # La vue courante est mémorisée avant la démolition, pour que la
        # position se retrouve à la prochaine ouverture du dossier. L'échec de
        # cette mémorisation ne doit jamais empêcher la fermeture : cette
        # méthode répond à un signal, et une exception qui s'en échappe part
        # vers la fenêtre d'erreur Python de QGIS, dont le dialogue modal
        # bloque la session, soit l'inverse de ce que le raccordement cherche.
        if self.enableShow:
            try:
                self.setLastView()
            except Exception:
                self.journal.exception(
                    "Vue courante non mémorisée ; la fermeture se poursuit"
                )
        # Les modifications en attente sont nommées, sans dialogue : cette
        # méthode répond à `cleared`, donc s'exécute pendant la démolition du
        # projet, et un dialogue modal y ramènerait le défaut que le
        # commentaire ci-dessus décrit. La couche peut d'ailleurs déjà être
        # invalide. QGIS pose sa propre question sur les couches en édition
        # avant de vider un projet ; ce message dit ce qui est en jeu.
        enAttente, nombre = editionVecteur.modificationsEnAttente(self.vectorLayer)
        nomCouche = ""
        if enAttente:
            try:
                nomCouche = self.vectorLayer.name()
            except RuntimeError:
                nomCouche = self.vectorLayerName or "(inconnue)"
            self.journal.warning(
                "Changement de projet avec %d modification(s) en attente sur "
                "la couche %s",
                nombre,
                nomCouche,
            )

        avertir_utilisateur(
            "Le projet a changé : la session StereoPhoto est fermée et ses "
            "paramètres enregistrés. Rouvrir le menu principal pour reprendre "
            "la navigation."
            + (
                " La couche « %s » portait %d modification(s) non "
                "enregistrée(s)." % (nomCouche, nombre)
                if enAttente
                else ""
            )
        )
        # Déclenche run(), qui retire le panneau puis appelle optWindowClose(),
        # lequel écrit le fichier de paramètres par closeAllSideWindows().
        self.actionMainMenu.setChecked(False)

    def optWindowClose(self):
        # Garde de réentrance, comme celle de closeAllSideWindows() un niveau
        # plus bas. optWindow.close() déclenche son closeEvent, qui réémet
        # closeWindow et rappelle cette méthode. L'appel imbriqué atteignait
        # alors setChecked(False), donc le `del self.optWindow` de run(), et
        # l'appel extérieur trouvait l'attribut disparu à la ligne suivante.
        if self.fermetureSessionEnCours:
            return
        self.fermetureSessionEnCours = True
        try:
            # L'enregistrement étant un geste explicite, la question est posée
            # avant la démolition, pour que le photo-interprète ne s'en aille
            # pas en croyant son travail écrit.
            self.demanderSortEditions()
            # Les signaux de la couche sont rompus ici, et non dans
            # closeAllSideWindows() qui sert aussi à ne fermer que les vues :
            # la couche survit à la session, et la session suivante
            # raccorderait par-dessus, empilant les connexions.
            self.rompreRaccordementCouche()
            self.closeAllSideWindows()
            # Référence locale plutôt que l'attribut : la fermeture fait
            # circuler les événements Qt, et l'attribut peut disparaître entre
            # deux lignes.
            optWindow = getattr(self, "optWindow", None)
            if optWindow is not None:
                optWindow.close()
                optWindow.vectorWindow.close()
            if self.actionMainMenu.isChecked():
                self.actionMainMenu.setChecked(False)
        finally:
            self.fermetureSessionEnCours = False

    def newPictureFile(self):

        # Aucune garde de SCR ici : la lecture du dossier ne fait que dresser la
        # liste des paires et préparer la paire courante, sans transformer une
        # coordonnée. Cette méthode répond de plus à `textChanged`, donc au
        # dossier restauré par loadParamFile() à l'ouverture de la session,
        # avertir ici revenait à avertir au démarrage, avant que l'utilisateur
        # ait monté son projet. La garde est posée là où les mètres servent :
        # createGraphicsWindows() et findPairWithPosition().
        self.currentMainPath = self.optWindow.ui.importLineProject.text()
        self.optWindow.projectPath = os.path.dirname(self.currentMainPath)
        self.currentParDict = getParDict(self.currentMainPath)

        if len(self.currentParDict) < 2:
            self.optWindow.ui.pushButtonShowIDList.setEnabled(False)
            self.optWindow.ui.enhanceButton.setEnabled(False)
            self.optWindow.ui.pushButtonShowPicture.setEnabled(False)
            self.optWindow.ui.pushButtonFindBestPair.setEnabled(False)
            return

        else:
            self.optWindow.ui.pushButtonShowIDList.setEnabled(True)
            self.optWindow.ui.enhanceButton.setEnabled(True)
            self.optWindow.ui.pushButtonShowPicture.setEnabled(True)
            self.optWindow.ui.pushButtonFindBestPair.setEnabled(True)

        userImage = self.optWindow.ParamDict["info_raster"]["user_image"]
        lastPosition = self.optWindow.ParamDict["position"]
        if userImage in self.currentParDict.keys():
            parToUse = userImage
            if float(lastPosition["longitude"]) != 0.0:
                x = float(lastPosition["longitude"])
                y = float(lastPosition["latitude"])
                z = float(lastPosition["altitude"])
                scale = float(lastPosition["scale"])
                self.lastCurrentView = (x, y, z, scale)
            else:
                self.lastCurrentView = ()

        else:
            self.lastCurrentView = ()
            # self.optWindow.removeImportMNT()
            self.removePolygonOnScreen()
            parToUse = next(iter(self.currentParDict))

        if self.enableShow:
            self.closeAllSideWindows()
        self.setPairWithPARId(parToUse)

    def showIDList(self):
        self.pictureSelectWindow = getImageListDialog(
            sorted(self.currentParDict), self.leftParID
        )
        self.pictureSelectWindow.ui.buttonBox.accepted.connect(
            self.pictureSelectionAccept
        )
        self.pictureSelectWindow.ui.buttonBox.rejected.connect(
            lambda: self.pictureSelectWindow.close()
        )
        self.pictureSelectWindow.show()

    def pictureSelectionAccept(self):
        pictureID = self.pictureSelectWindow.ui.listWidget.selectedItems()[0].text()
        self.setPairWithPARId(pictureID)

        if self.enableShow and self.leftParID != "":
            self.loadNewPair()
        self.lastCurrentView = ()
        self.pictureSelectWindow.close()

    def setPairWithPARId(self, parID, secondID=None):

        # Retourne les paires left et right ainsi que les 4 voisins NOSE
        # Voisin Est/Ouest peut être une image qui n'est pas une paire
        # Voisin Nord/Sud peut être une paire pour assurer la continuitée de la vue courante
        self.infoNeighbors = get_neighbors_and_pairs(parID, self.currentParDict)

        if secondID:
            self.leftParID = parID
            self.rightParID = secondID

        elif (
            self.infoNeighbors["leftPic"][0] is None
            and self.infoNeighbors["rightPic"][0] is None
        ):
            self.leftParID = ""
            return

        elif self.infoNeighbors["rightPic"][0] is None:
            self.leftParID = self.infoNeighbors["leftPic"][0]
            self.rightParID = parID

        else:
            self.leftParID = parID
            self.rightParID = self.infoNeighbors["rightPic"][0]

        self.optWindow.ui.labelLeftName.setText(self.leftParID)
        self.optWindow.ui.labelRightName.setText(self.rightParID)

        self.currentLeftTIF = self.currentMainPath + "/" + self.leftParID + ".tif"
        self.currentLeftPAR = self.currentMainPath + "/" + self.leftParID + ".par"
        self.currentRightTIF = self.currentMainPath + "/" + self.rightParID + ".tif"
        self.currentRightPAR = self.currentMainPath + "/" + self.rightParID + ".par"

        infoNeighborR = get_neighbors_and_pairs(self.rightParID, self.currentParDict)
        self.infoNeighbors = get_neighbors_and_pairs(
            self.leftParID, self.currentParDict
        )

        self.currentLeftID = True if self.infoNeighbors["left"][0] else False

        if infoNeighborR["rightPic"][0] is None and infoNeighborR["right"][0]:
            self.currentRightID = True
            self.infoNeighbors["right"] = infoNeighborR["right"]

        elif infoNeighborR["rightPic"][0]:
            self.currentRightID = True
        else:
            self.currentRightID = False

        self.currentUpID = True if len(self.infoNeighbors["up"]) != 0 else False
        self.currentDownID = True if len(self.infoNeighbors["down"]) != 0 else False

    def setLastView(self):
        if not hasattr(self, "graphWindowLeft"):
            return

        if self.cursorAltitude is None:
            # Sans altitude, pixelToCoord() ne peut pas rendre de coordonnée :
            # il soustrait l'altitude du curseur à celle de la prise de vue, et
            # lève un TypeError sur None. L'altitude est indéterminée tant
            # qu'une paire n'a pas été mesurée, ou quand la mesure a échoué.
            # Mémoriser la vue n'a alors pas de sens, et la levée partirait
            # vers la fenêtre d'erreur Python de QGIS, par le signal du
            # projet, elle bloquait la session derrière un dialogue modal.
            self.journal.debug("Altitude indéterminée : vue courante non mémorisée")
            return

        LGV = self.graphWindowLeft.ui.graphicsView
        sceneRect = LGV.mapToScene(LGV.viewport().rect()).boundingRect()
        sceneCenter = sceneRect.center()
        centerPixel = self.graphWindowLeft.imageRoot.mapFromScene(sceneCenter)

        currentTransform = LGV.transform()

        scaleStore = currentTransform.m11()  # self.currentScale

        cx, cy = self.leftPictureManager.pixelToCoord(
            (centerPixel.x(), centerPixel.y()), self.cursorAltitude
        )
        self.lastCurrentView = (cx, cy, self.cursorAltitude, scaleStore)

        # Types natifs pour ce qui part au fichier de paramètres : une valeur
        # numpy y ferait lever json.dump(), et l'échec détruirait le fichier.
        # La conversion est faite ici plutôt que laissée à saveParamFile(),
        # pour que ParamDict ne contienne jamais que du sérialisable.
        self.optWindow.ParamDict["position"]["longitude"] = float(cx)
        self.optWindow.ParamDict["position"]["latitude"] = float(cy)
        self.optWindow.ParamDict["position"]["altitude"] = float(self.cursorAltitude)
        self.optWindow.ParamDict["position"]["scale"] = float(scaleStore)

    def findNextPair(self, ori):
        if not self.horsSynchronisation:
            self.navigMapTool.deactivateMapTool()
        self.setLastView()

        secondID = None
        newID = None
        if ori == "L":
            newID = self.infoNeighbors["left"][0]
        elif ori == "R":
            newID = self.infoNeighbors["right"][0]

        elif ori == "D":  # down/Bas
            if len(self.infoNeighbors["down"]) == 2:
                name_1 = self.infoNeighbors["down"][0][0]
                name_2 = self.infoNeighbors["down"][1][0]
                x0_1 = self.currentParDict[name_1][0]
                x0_2 = self.currentParDict[name_2][0]
                if x0_1 < x0_2:
                    newID = name_1
                    secondID = name_2
                else:
                    newID = name_2
                    secondID = name_1

            else:
                newID = self.infoNeighbors["down"][0][0]

        elif ori == "U":  # up/Haut
            if len(self.infoNeighbors["up"]) == 2:
                name_1 = self.infoNeighbors["up"][0][0]
                name_2 = self.infoNeighbors["up"][1][0]
                x0_1 = self.currentParDict[name_1][0]
                x0_2 = self.currentParDict[name_2][0]
                if x0_1 < x0_2:
                    newID = name_1
                    secondID = name_2
                else:
                    newID = name_2
                    secondID = name_1

            else:
                newID = self.infoNeighbors["up"][0][0]

        # Orientation inconnue ou voisin absent : aucune paire à charger
        if newID is None:
            return

        self.setPairWithPARId(newID, secondID)

        self.loadNewPair(ignoreMapTool=True)

    def findPairWithPosition(self):

        # La vue du canevas est lue en mètres pour la comparer aux coordonnées
        # des photos : même garde qu'à l'affichage, et même moment choisi par
        # l'utilisateur.
        if not self.verifierScrProjet():
            return

        qgisExtent = self.canvas.extent()
        centerCoord = (
            qgisExtent.xMinimum() + qgisExtent.width() / 2,
            qgisExtent.yMinimum() + qgisExtent.height() / 2,
        )
        bestFit = findPairWithCoord(self.currentParDict, centerCoord)

        width = qgisExtent.width()
        height = qgisExtent.height()
        imageID = bestFit[0]
        distance = bestFit[1]

        # Zone de 7.5 km pour être proche de la photo le plus possible
        if max(width, height, distance) < 7500:
            self.buttonPosition = centerCoord
            self.buttonMapUnit = self.canvas.mapUnitsPerPixel()
            self.setPairWithPARId(imageID)
            if self.enableShow and self.leftParID != "":
                self.loadNewPair()
        else:
            self.buttonPosition = None
            # Sans message, le bouton restait sans effet visible : l'utilisateur
            # ne pouvait pas distinguer une vue mal placée d'une panne.
            avertir_utilisateur(
                "Aucune paire trouvée à cet endroit. Rapprochez la vue de la "
                "zone des photos et zoomez sous 7,5 km avant de réessayer."
            )

    def createGraphicsWindows(self):

        # Première opération qui transforme des coordonnées de
        # photos en position de canevas. Le projet est monté, l'utilisateur
        # vient de demander l'affichage : c'est ici que l'avertissement de SCR
        # a un sens, et qu'il précède encore toute navigation.
        if not self.verifierScrProjet():
            return

        if self.enableShow:
            self.setExtent2Canvas()
            self.windowHandler("picture")
            if self.enableDraw:
                self.startPolygonThread()
                self.majActivationTrace()
            return

        intDownScreen = self.optWindow.ui.spinBoxDownScreen.value()
        intUpSreen = self.optWindow.ui.spinBoxUpScreen.value()

        screenLeft = QGuiApplication.screens()[intDownScreen]
        screenRight = QGuiApplication.screens()[intUpSreen]

        screenLeft_geom = screenLeft.geometry()
        screenRight_geom = screenRight.geometry()

        self.graphWindowLeft = graphicsWindow()
        self.graphWindowLeft.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.graphWindowLeft.move(screenLeft_geom.topLeft())
        self.graphWindowLeft.keyPressed.connect(self.keyboardHandler)

        self.graphWindowRight = graphicsWindow()
        self.graphWindowRight.setWindowFlags(Qt.Window | Qt.FramelessWindowHint)
        self.graphWindowRight.move(screenRight_geom.topLeft())
        self.graphWindowRight.keyPressed.connect(self.keyboardHandler)

        width = DRAW_LINE_PEN_WIDTH_PX
        color = QColor("Cyan")

        self.my_pen = QPen(color, width, Qt.SolidLine, Qt.SquareCap, Qt.RoundJoin)
        self.my_pen.setCosmetic(True)

        # Pinceau de la surbrillance des entités sélectionnées. Construit une
        # fois, comme celui du tracé : drawPolygon() est rappelée à chaque
        # chargement de tuiles.
        self.selectionPen = QPen(
            QColor(EDITION_SELECTION_COULEUR),
            EDITION_SELECTION_PEN_WIDTH_PX,
            Qt.SolidLine,
            Qt.SquareCap,
            Qt.RoundJoin,
        )
        self.selectionPen.setCosmetic(True)

        self.enableShow = True
        self.optWindow.ui.pushButtonCloseWindow.setEnabled(True)

        self.graphWindowRight.showFullScreen()
        self.graphWindowLeft.showFullScreen()
        self.iface.mainWindow().raise_()
        self.iface.mainWindow().activateWindow()
        self.canvas.setFocus()
        self.loadNewPair()

    def arreterThreadAffichage(self, thread):
        """Arrête un thread d'affichage et ne rend la main qu'une fois sûr.

        La condition d'attente porte sur `isRunning()`, et non sur
        `showThreadInProcess` : ce drapeau est posé et retiré *dans* `run()`,
        donc sur le thread de travail. Il est faux entre `start()` et l'entrée
        dans `run()` (de 24 à 98 ms, mesuré sur quatorze changements de
        modèle), puis de nouveau entre son retrait dans le `finally` de
        `run()` et la
        fin réelle du thread. Dans ces deux fenêtres, la garde précédente
        laissait relâcher la dernière référence Python d'un QThread en cours
        d'exécution, et Qt interrompait le processus sans rien journaliser.

        L'attente est bornée : l'interface ne doit pas rester figée sur un
        thread qui ne se terminerait pas. Mais un thread encore vivant au bout
        du délai n'est pas relâché pour autant : il est gardé de côté le temps
        qu'il finisse, car c'est le relâchement qui tue le processus, pas
        l'attente.
        """
        if thread is None:
            return

        # Signaux coupés avant l'arrêt : le chargement en cours est abandonné,
        # ses tuiles ne doivent plus rejoindre la scène de la paire suivante.
        thread.blockSignals(True)
        thread.keepRunning = False

        if not thread.isRunning():
            return

        if thread.wait(NAVIGATION_ARRET_THREAD_DELAI_MAX_MS):
            return

        self.journal.warning(
            "Thread d'affichage encore en cours après %d ms : conservé le "
            "temps qu'il se termine, pour ne pas détruire un QThread en "
            "exécution.",
            NAVIGATION_ARRET_THREAD_DELAI_MAX_MS,
        )
        self.threadsEnArret.append(thread)

    def purgerThreadsEnArret(self):
        """Relâche les threads gardés de côté qui se sont terminés depuis."""

        if not self.threadsEnArret:
            return

        restants = [t for t in self.threadsEnArret if t.isRunning()]
        relaches = len(self.threadsEnArret) - len(restants)
        if relaches:
            self.journal.debug(
                "%d thread(s) d'affichage relâché(s), %d encore en cours",
                relaches,
                len(restants),
            )
        self.threadsEnArret = restants

    def removeCurrentScene(self):

        self.purgerThreadsEnArret()

        self.arreterThreadAffichage(self.tSeekLeft)
        self.tSeekLeft = None

        if hasattr(self, "graphWindowLeft"):
            self.graphWindowLeft.resetTileGroup()

        self.arreterThreadAffichage(self.tSeekRight)
        self.tSeekRight = None

        if hasattr(self, "graphWindowRight"):
            self.graphWindowRight.resetTileGroup()

        QApplication.processEvents()

    def loadNewPair(self, ignoreMapTool=False):
        # Le drapeau n'était jusqu'ici jamais levé, seulement abaissé : la garde
        # de mouseMoveEvent() et de wheelActionEvent() ne protégeait rien. Un
        # mouvement reçu pendant le chargement lisait des tuiles et un cadrage
        # en cours de remplacement.
        self.isLoadingPair = True

        self.removeCurrentScene()

        self.graphWindowLeft.ui.graphicsView.resetTransform()
        self.graphWindowRight.ui.graphicsView.resetTransform()

        self.tSeekLeft = threadShow(
            self.currentLeftTIF, self.optWindow.rehaussementParam
        )
        self.tSeekLeft.newImage.connect(self.graphWindowLeft.addPixmap)
        self.tSeekLeft.finished.connect(self.seekLeftDone)

        self.tSeekRight = threadShow(
            self.currentRightTIF, self.optWindow.rehaussementParam
        )
        self.tSeekRight.newImage.connect(self.graphWindowRight.addPixmap)
        self.tSeekRight.finished.connect(self.seekRightDone)

        self.fullLeftPicSize = (self.tSeekLeft.width, self.tSeekLeft.height)
        self.fullRightPicSize = (self.tSeekRight.width, self.tSeekRight.height)

        self.leftPictureManager = pictureManager(
            self.fullLeftPicSize, self.currentLeftPAR
        )
        self.rightPictureManager = pictureManager(
            self.fullRightPicSize, self.currentRightPAR
        )

        leftBbox = self.currentParDict[self.leftParID]
        rightBbox = self.currentParDict[self.rightParID]

        _, bboxOverlap = compute_overlap(leftBbox, rightBbox)

        gpzL = self.leftPictureManager.groundPixelSize
        gpzR = self.rightPictureManager.groundPixelSize

        r11L = self.leftPictureManager.r11
        r12L = self.leftPictureManager.r12

        r11R = self.rightPictureManager.r11
        r12R = self.rightPictureManager.r12

        cropValueLeft = self.calculDecoupageAvecRotation(
            self.fullLeftPicSize, bboxOverlap, leftBbox, gpzL, r11L, r12L
        )
        cropValueRight = self.calculDecoupageAvecRotation(
            self.fullRightPicSize, bboxOverlap, rightBbox, gpzR, r11R, r12R
        )

        self.leftPicSize = (
            cropValueLeft[2] - cropValueLeft[0],
            cropValueLeft[3] - cropValueLeft[1],
        )
        self.rightPicSize = (
            cropValueRight[2] - cropValueRight[0],
            cropValueRight[3] - cropValueRight[1],
        )

        self.dualManager = dualManager(
            self.leftPictureManager, self.rightPictureManager
        )

        self.tSeekLeft.cropValue = cropValueLeft
        self.tSeekRight.cropValue = cropValueRight

        self.realCropValueLeft = cropValueLeft
        self.realCropValueRight = cropValueRight

        # self.openMNT()
        coordRect = self.getShowRect()
        self.optWindow.getMNTWithCoord(coordRect)

        self.setInitialCursorAltitude()
        self.setBaseTransform()
        self.setStartingView()
        self.setExtent2Canvas()

        if ignoreMapTool:
            # Le chargement vient de la navigation elle-même : on remet l'outil
            # de l'état courant, sans ramener les fenêtres photo au premier plan.
            if self.horsSynchronisation:
                self.canvas.setMapTool(self.horsSyncMapTool)
            else:
                self.navigMapTool.activateMapTool()
        else:
            self.windowHandler("picture")

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}
        # Le tracé appartient au modèle quitté : ses sommets et ses traits sont
        # abandonnés. Remettre le seul drapeau à vrai, comme avant, laissait
        # les sommets dans les accumulateurs et les traits cyan dans les
        # scènes ; la géométrie suivante enjambait deux modèles.
        self.annulerTraceEnCours()

        LGV = self.graphWindowLeft.ui.graphicsView
        vpl = LGV.viewport()
        sceneRectL = LGV.mapToScene(vpl.rect()).boundingRect()
        realLeftRect = self.graphWindowLeft.imageRoot.mapFromScene(
            sceneRectL
        ).boundingRect()
        self.tSeekLeft.set_SceneRect(realLeftRect)
        self.tSeekLeft.start(QThread.LowestPriority)

        RGV = self.graphWindowRight.ui.graphicsView
        vpr = RGV.viewport()
        sceneRectR = RGV.mapToScene(vpr.rect()).boundingRect()
        realRigthRect = self.graphWindowRight.imageRoot.mapFromScene(
            sceneRectR
        ).boundingRect()

        self.tSeekRight.set_SceneRect(realRigthRect)
        self.tSeekRight.start(QThread.LowestPriority)

        if self.enableDraw:
            self.startPolygonThread()
            self.majActivationTrace()

        self.isLoadingPair = False

    def getQtransform(self, pictureManager: pictureManager):
        r11 = pictureManager.r11
        r12 = pictureManager.r12
        r21 = pictureManager.r21
        r22 = pictureManager.r22
        ppa_x = pictureManager.PPAx
        ppa_y = pictureManager.PPAy

        t = QTransform()
        t.translate(ppa_x, ppa_y)
        t *= QTransform(r11, r12, r21, r22, 0, 0)
        t.translate(-ppa_x, -ppa_y)
        return t

    def calculDecoupageAvecRotation(self, sizeImg, bboxOverlap, bbox, gpz, R11, R12):
        threshold = 0.5
        width, height = sizeImg
        if gpz <= 0:
            # Use a fallback or log an error
            return (0, 0, width, height)

        if R11 < -threshold:
            # +180° Rotation : World X → Pixel X (flip), World Y → Pixel Y
            xStart = int((bbox[4] - bboxOverlap[2]) / gpz)
            yStart = int((bboxOverlap[1] - bbox[3]) / gpz)

            xEnd = int((bbox[4] - bboxOverlap[0]) / gpz)
            yEnd = int((bboxOverlap[3] - bbox[3]) / gpz)

        elif abs(R11) < threshold and R12 > threshold:
            # +90° Rotation : World X → Pixel Y,  World Y → Pixel X  (flip)
            xStart = int((bboxOverlap[1] - bbox[3]) / gpz)
            yStart = int((bbox[4] - bboxOverlap[2]) / gpz)

            xEnd = int((bboxOverlap[3] - bbox[3]) / gpz)
            yEnd = int((bbox[4] - bboxOverlap[0]) / gpz)

        elif abs(R11) < threshold and R12 < -threshold:
            # -90° Rotation : World X → Pixel Y (flip), World Y → Pixel X (flip)

            xStart = int((bbox[5] - bboxOverlap[3]) / gpz)
            yStart = int((bboxOverlap[0] - bbox[2]) / gpz)

            xEnd = int((bbox[5] - bboxOverlap[1]) / gpz)
            yEnd = int((bboxOverlap[2] - bbox[2]) / gpz)

        else:
            # 0° Rotation : World X → Pixel X,  World Y → Pixel Y (flip)
            xStart = int((bboxOverlap[0] - bbox[2]) / gpz)
            yStart = int((bbox[5] - bboxOverlap[3]) / gpz)

            xEnd = int((bboxOverlap[2] - bbox[2]) / gpz)
            yEnd = int((bbox[5] - bboxOverlap[1]) / gpz)

        xStart = max(0, min(xStart, width))
        xEnd = max(0, min(xEnd, width))
        yStart = max(0, min(yStart, height))
        yEnd = max(0, min(yEnd, height))

        return (xStart, yStart, xEnd, yEnd)

    def verifierScrProjet(self):
        """S'assure que le projet est dans un SCR projeté en mètres.

        Tout le calcul de navigation suppose des mètres. Les
        fichiers PAR portent des coordonnées projetées, `setExtent2Canvas()`
        accorde l'échelle du canevas sur celle des vues photo en mètres par
        pixel, et `coordToPixel()` reçoit la coordonnée du canevas telle quelle.

        Un projet dans un SCR géographique fait donc traiter des degrés comme
        des mètres : le déplacement image devient d'environ 10⁻⁵ pixel par
        pixel de souris, et la navigation paraît figée sans qu'aucune erreur ne
        soit levée. C'est l'état par défaut d'un projet neuf (WGS 84), et celui
        qu'on obtient dès que les rasters ne déclarent aucun SCR.

        Le SCR est alors posé depuis la configuration plutôt que refusé : la
        navigation reste possible, et l'utilisateur est averti du changement.
        Retourne True si la navigation peut se poursuivre.

        La garde est posée aux deux opérations qui consomment des mètres,
        l'affichage des photos et la recherche de paire par la vue, et non à
        l'ouverture de la session : un projet neuf y est encore en WGS 84 et
        ses couches arrivent après, de sorte que l'avertissement tombait au
        démarrage, sur un projet que l'utilisateur n'avait pas fini de monter.
        """
        projet = QgsProject.instance()
        scr = projet.crs()

        if scr.isValid() and not scr.isGeographic():
            self.journal.debug("SCR du projet : %s", scr.authid())
            return True

        scrDonnees = QgsCoordinateReferenceSystem.fromEpsgId(DONNEES_SCR_EPSG)
        if not scrDonnees.isValid():
            avertir_utilisateur(
                f"Le SCR EPSG:{DONNEES_SCR_EPSG} des données est introuvable "
                "dans cette installation de QGIS : la navigation est "
                "impossible. Vérifier l'installation de PROJ.",
                logging.ERROR,
            )
            return False

        ancien = scr.authid() if scr.isValid() else "aucun"
        projet.setCrs(scrDonnees)
        avertir_utilisateur(
            f"Le SCR du projet ({ancien}) ne convient pas aux coordonnées des "
            f"photos, exprimées en mètres. Il est remplacé par "
            f"{scrDonnees.authid()}. Si les données du secteur sont dans un "
            "autre SCR projeté, le poser avant d'ouvrir les photos."
        )
        return True

    # Fonction qui récupère la couche vectorielle et change le SIG de QGIS
    # Si possible appel la fonction pour afficher la couche vectorielle sur les images
    def mNewVectorLayer(self):
        couche = self.optWindow.vLayer
        if couche is None:
            return

        # Tout le calcul de navigation suppose des mètres. Cette méthode pose le
        # SCR de la couche au projet : une couche en coordonnées géographiques
        # figeait donc la navigation, et sans un mot, la garde
        # verifierScrProjet() n'étant rejouée qu'à l'affichage.
        if couche.crs().isGeographic():
            avertir_utilisateur(
                "La couche « %s » est en coordonnées géographiques (%s). Elle "
                "ne peut pas servir à l'édition : la navigation et l'altitude "
                "supposent des mètres. Reprojeter la couche en EPSG:%s, ou en "
                "un autre SCR projeté."
                % (couche.name(), couche.crs().authid(), DONNEES_SCR_EPSG)
            )
            self.journal.warning(
                "Couche %s écartée : SCR géographique %s",
                couche.name(),
                couche.crs().authid(),
            )
            return

        self.enableDraw = True
        self.vectorLayer = couche
        self.vectorLayerName = self.optWindow.vLayerName
        QgsProject.instance().setCrs(self.vectorLayer.crs())

        # La couche porte l'état d'édition : ses signaux commandent les boutons
        # Enregistrer et Annuler, et sa sélection commande la surbrillance.
        self.raccorderCoucheEditable(self.vectorLayer)
        self.annulerTraceEnCours()
        self.majActivationTrace()
        self.synchroniserRadiosTrace()

    # Fonction qui détermine la région approximative des photos
    # Retourne le rectangle de coordonnée
    def getShowRect(self):
        try:
            leftBbox = self.currentParDict[self.leftParID]
            rightBbox = self.currentParDict[self.rightParID]

            _, bboxOverlap = compute_overlap(leftBbox, rightBbox)

            rectL = QgsRectangle(
                QgsPointXY(bboxOverlap[0] - 700, bboxOverlap[1] - 700),
                QgsPointXY(bboxOverlap[2] + 700, bboxOverlap[3] + 700),
            )

            return rectL
        except Exception:
            # Rectangle dégénéré retourné à l'appelant : sans trace, la région
            # d'affichage vide est impossible à expliquer en support.
            self.journal.warning(
                "Région d'affichage indéterminable pour la paire %s / %s",
                getattr(self, "leftParID", None),
                getattr(self, "rightParID", None),
                exc_info=True,
            )
            return QgsRectangle(QgsPointXY(0, 0), QgsPointXY(0, 0))

    def removePolygonOnScreen(self):
        self.deleteOldPolygon()
        self.annulerTraceEnCours()
        self.rompreRaccordementCouche()

        self.polygonL2Draw = {}
        self.polygonR2Draw = {}

        self.vectorLayer = None
        self.vectorLayerName = None
        self.enableDraw = False

        self.majEtatActionsEdition()
        self.majActivationTrace()
        self.synchroniserRadiosTrace()

        self.optWindow.ui.importLineVectorLayer.blockSignals(True)
        self.optWindow.ui.importLineVectorLayer.setText("")
        self.optWindow.ui.importLineVectorLayer.blockSignals(False)

    def startPolygonThread(self):
        if hasattr(self, "tPolygon"):
            if self.tPolygon.isRunning():
                self.tPolygon.stop()
                self.tPolygon.wait()
            del self.tPolygon
        rectCoord = self.getShowRect()
        lmanag = [self.fullLeftPicSize, self.currentLeftPAR]
        rmanag = [self.fullRightPicSize, self.currentRightPAR]
        mntPath = self.optWindow.currentMNTPath
        vectorToShow = self.optWindow.vectorToShow
        self.tPolygon = calculatePolygon(
            vectorToShow, rectCoord, lmanag, rmanag, self.cursorAltitude, mntPath
        )
        self.tPolygon.finished.connect(self.storePolygon)
        self.tPolygon.start(QThread.LowestPriority)

    def storePolygon(self):
        self.polygonL2Draw = self.tPolygon.dictPolyL
        self.polygonR2Draw = self.tPolygon.dictPolyR
        self.drawPolygon()

    def deleteOldPolygon(self):
        for fenetre in (
            getattr(self, "graphWindowLeft", None),
            getattr(self, "graphWindowRight", None),
        ):
            if fenetre is None:
                continue
            for groupe in (fenetre.geometryItemGroup, fenetre.selectionItemGroup):
                for item in groupe.childItems():
                    fenetre.scene.removeItem(item)

    def creerItemGeometrie(self, geoType, forme, imageRoot, rayonSupplementaire=0):
        """Objet de scène pour une forme déjà projetée, ou None si inconnue.

        Extrait de `drawPolygon()` pour que la surbrillance reprenne exactement
        la forme de la géométrie qu'elle désigne, et non une seconde
        projection : la géométrie des vues est projetée sommet par sommet avec
        l'altitude du MNT, et toute autre projection s'en écarterait à l'œil.
        """
        if geoType == QgsWkbTypes.PolygonGeometry:
            return QGraphicsPolygonItem(forme, imageRoot)

        if geoType == QgsWkbTypes.LineGeometry:
            return QGraphicsPathItem(forme, imageRoot)

        if geoType == QgsWkbTypes.PointGeometry:
            rayon = GEOMETRY_POINT_RADIUS_PX + rayonSupplementaire
            return QGraphicsEllipseItem(
                forme[0] - rayon,
                forme[1] - rayon,
                2 * rayon,
                2 * rayon,
                imageRoot,
            )

        return None

    def drawPolygon(self):
        """Dessine les géométries projetées, et la surbrillance de la sélection.

        Les formes viennent du fil `calculatePolygon`, qui joint désormais à
        chacune l'identifiant de l'entité dont elle vient, et à chaque couche
        son identifiant de couche. C'est ce qui permet de désigner, dans les
        deux vues photo, la même entité que la sélection de QGIS : les
        géométries y sont des objets de scène et non des entités, la
        surbrillance native de QGIS ne les atteint donc pas.
        """
        self.deleteOldPolygon()

        if not self.polygonL2Draw:
            self.hideOffBoundDrawing()
            return

        idCoucheEditable = None
        selectionnes = set()
        if self.vectorLayer is not None:
            try:
                idCoucheEditable = self.vectorLayer.id()
                selectionnes = set(self.vectorLayer.selectedFeatureIds())
            except RuntimeError:
                # Couche détruite par QGIS entre deux rafraîchissements.
                self.journal.debug("Couche éditable disparue avant le dessin")

        for name, arr in self.polygonL2Draw.items():
            geoType = arr[2]
            color = arr[1]
            polyLeft = arr[0]
            polyRight = self.polygonR2Draw[name][0]
            identifiants = arr[3] if len(arr) > 3 else []

            # La surbrillance ne concerne que la couche éditable. Les
            # dictionnaires d'affichage sont indexés par nom de couche, et deux
            # couches homonymes du projet partageraient la même entrée :
            # l'identifiant de couche lève l'ambiguïté.
            coucheSelectionnable = bool(
                selectionnes and len(arr) > 4 and arr[4] == idCoucheEditable
            )

            layerPen = QPen(
                color,
                GEOMETRY_PEN_WIDTH_PX,
                Qt.SolidLine,
                Qt.SquareCap,
                Qt.RoundJoin,
            )
            layerPen.setCosmetic(True)

            for i in range(len(polyLeft)):
                leftObj = self.creerItemGeometrie(
                    geoType, polyLeft[i], self.graphWindowLeft.imageRoot
                )
                rightObj = self.creerItemGeometrie(
                    geoType, polyRight[i], self.graphWindowRight.imageRoot
                )

                # Type de géométrie non pris en charge : rien à dessiner
                if leftObj is None:
                    continue

                if geoType == QgsWkbTypes.PointGeometry:
                    leftObj.setBrush(color)
                    rightObj.setBrush(color)

                leftObj.setPen(layerPen)
                rightObj.setPen(layerPen)
                self.graphWindowLeft.geometryItemGroup.addToGroup(leftObj)
                self.graphWindowRight.geometryItemGroup.addToGroup(rightObj)

                if not coucheSelectionnable or i >= len(identifiants):
                    continue
                if identifiants[i] not in selectionnes:
                    continue

                for fenetre, forme in (
                    (self.graphWindowLeft, polyLeft[i]),
                    (self.graphWindowRight, polyRight[i]),
                ):
                    surbrillance = self.creerItemGeometrie(
                        geoType, forme, fenetre.imageRoot, rayonSupplementaire=4
                    )
                    surbrillance.setPen(self.selectionPen)
                    fenetre.selectionItemGroup.addToGroup(surbrillance)

        self.hideOffBoundDrawing()

    def hideOffBoundDrawing(self):

        color = QColor(182, 182, 182)

        if hasattr(self.graphWindowLeft, "offboundRectGroup"):
            for item in self.graphWindowLeft.offboundRectGroup.childItems():
                self.graphWindowLeft.scene.removeItem(item)

        if hasattr(self.graphWindowRight, "offboundRectGroup"):
            for item in self.graphWindowRight.offboundRectGroup.childItems():
                self.graphWindowRight.scene.removeItem(item)

        # Offsets in the scene
        offLX, offLY = self.realCropValueLeft[0], self.realCropValueLeft[1]
        offRX, offRY = self.realCropValueRight[0], self.realCropValueRight[1]

        dval = 15000

        # For LEFT screen
        x0 = offLX
        y0 = offLY
        x1 = offLX + self.leftPicSize[0]
        y1 = offLY + self.leftPicSize[1]

        # Left side
        gr1L = QRectF(x0 - dval, y0 - dval, dval, (y1 - y0) + 2 * dval)
        rectObj = QGraphicsRectItem(gr1L, self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # Right side
        gr2L = QRectF(x1, y0 - dval, dval, (y1 - y0) + 2 * dval)
        rectObj = QGraphicsRectItem(gr2L, self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # Top
        gr3L = QRectF(x0, y0 - dval, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr3L, self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # Bottom
        gr4L = QRectF(x0, y1, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr4L, self.graphWindowLeft.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowLeft.offboundRectGroup.addToGroup(rectObj)

        # For RIGHT screen
        x0 = offRX
        y0 = offRY
        x1 = offRX + self.rightPicSize[0]
        y1 = offRY + self.rightPicSize[1]

        # Left side
        gr1R = QRectF(x0 - dval, y0 - dval, dval, (y1 - y0) + 2 * dval)
        rectObj = QGraphicsRectItem(gr1R, self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

        # Right side
        gr2R = QRectF(x1, y0 - dval, dval, (y1 - y0) + 2 * dval)
        rectObj = QGraphicsRectItem(gr2R, self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

        # Top
        gr3R = QRectF(x0, y0 - dval, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr3R, self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

        # Bottom
        gr4R = QRectF(x0, y1, (x1 - x0), dval)
        rectObj = QGraphicsRectItem(gr4R, self.graphWindowRight.imageRoot)
        rectObj.setBrush(QBrush(color))
        rectObj.setPen(QPen(color))
        self.graphWindowRight.offboundRectGroup.addToGroup(rectObj)

    def seekLeftDone(self):
        if self.enableDraw and self.enableShow:
            self.drawPolygon()
        if hasattr(self, "tSeekLeft"):
            self.tSeekLeft.showThreadInProcess = False

    def seekRightDone(self):
        if self.enableDraw and self.enableShow:
            self.drawPolygon()
        if hasattr(self, "tSeekRight"):
            self.tSeekRight.showThreadInProcess = False

    # Ouverture de la fenêtre de rehaussement
    def enhanceClick(self):
        self.enhanceManager = enhanceManager(
            self.currentLeftTIF,
            self.currentRightTIF,
            self.optWindow.rehaussementParam,
            self.leftParID,
            self.rightParID,
        )
        self.enhanceManager.listParamSignal.connect(self.applyEnhance)

    # Permet le lancement du traitement de modification des images
    def applyEnhance(self, listParam):
        self.enhanceManager.listParamSignal.disconnect(self.applyEnhance)
        self.optWindow.rehaussementParam = listParam

    def windowHandler(self, window):
        if window == "qgis":
            self.iface.mainWindow().raise_()
            self.iface.mainWindow().activateWindow()

            # La vue est mémorisée avant la bascule : c'est elle qu'on
            # retrouvera au retour par ESC.
            self.setLastView()

            # Le hors-synchronisation est un état porté par un
            # outil, et non le retrait de l'outil de navigation. Sans outil, le
            # zoom, le pan et le changement de modèle n'auraient aucun code pour
            # s'exécuter. setMapTool() remplace l'outil courant de lui-même.
            self.horsSynchronisation = True
            self.canvas.setMapTool(self.horsSyncMapTool)
            self.canvas.setFocus()

        if window == "picture":
            self.graphWindowRight.raise_()
            self.graphWindowRight.activateWindow()
            self.graphWindowLeft.raise_()
            self.graphWindowLeft.activateWindow()
            self.iface.mainWindow().raise_()
            self.iface.mainWindow().activateWindow()
            self.horsSynchronisation = False
            self.canvas.setMapTool(self.navigMapTool)
            self.canvas.setFocus()

    # Bascule entre les deux comportements de navigation :
    #   décoché : les photos se déplacent sous un curseur immobile au centre
    #   coché   : le curseur se déplace sur les photos, qui restent fixes
    # Le changement prend effet au mouvement de souris suivant : mouseMoveEvent()
    # et wheelActionEvent() lisent l'état de l'outil à chaque appel.
    def basculerCurseurLibre(self, actif):
        if not hasattr(self, "navigMapTool"):
            # Aucune session ouverte. L'état est relu par run() à l'ouverture.
            return

        self.navigMapTool.curseurLibre = actif
        self.journal.info(
            "Comportement de navigation : %s",
            "le curseur se déplace sur les photos"
            if actif
            else "les photos se déplacent sous le curseur",
        )

    # --- État hors-synchronisation -----------------------------------------
    #
    # Les trois récepteurs ci-dessous sont appelés après que l'outil a déjà
    # déplacé ou zoomé le canevas de QGIS : les vues photo n'ont qu'à s'y
    # réaligner. C'est l'inverse de setExtent2Canvas(), qui pousse la vue photo
    # vers le canevas.

    def suivreCanevasHorsSync(self):
        """Pan « main » : les deux vues suivent le canevas, à échelle égale."""
        self.recadrerVuesSurCanevas()

    def zoomerHorsSync(self):
        """Roulette : les deux vues suivent le canevas, échelle comprise."""
        self.recadrerVuesSurCanevas(ajusterEchelle=True)

    def retourNavigationPhoto(self):
        """Retour en navigation synchronisée, sur la vue quittée."""
        if self.enableShow:
            self.windowHandler("picture")

    def recadrerVuesSurCanevas(self, ajusterEchelle=False):
        if self.isLoadingPair or not self.enableShow:
            return
        if self.cursorAltitude is None or not hasattr(self, "graphWindowLeft"):
            return

        if ajusterEchelle:
            # Même calcul que la branche CTRL de wheelActionEvent() : l'échelle
            # d'affichage des photos se déduit de celle du canevas.
            self.currentScale = (
                self.leftPictureManager.groundPixelSize / self.canvas.mapUnitsPerPixel()
            )

        centre = self.canvas.center()
        coordCentre = (centre.x(), centre.y())

        pxL, pyL = self.leftPictureManager.coordToPixel(
            coordCentre, self.cursorAltitude
        )
        pxR, pyR = self.rightPictureManager.coordToPixel(
            coordCentre, self.cursorAltitude
        )

        pointImageGauche = QPointF(pxL, pyL)
        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(pointImageGauche)
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

        # La croix marque un point de l'image, pas le centre de la vue : un
        # déplacement de vue ne doit pas l'emmener avec lui.
        self.graphWindowLeft.custom_centerOn(
            scenePointL, self.currentScale, recentrerCroix=False
        )
        self.graphWindowRight.custom_centerOn(
            scenePointR, self.currentScale, recentrerCroix=False
        )

        self.changerModeleSiBordFranchi(pointImageGauche)

    # Fonction appelée lorsque les touches respectives du clavier sont appuyées
    # Les touches sont utiles lorsque le mode pan est en cours d'utilisation
    # Possibilité d'ajouter d'autres fonctions plus tard
    def keyboardHandler(self, event):
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.horsSynchronisation:
                    self.retourNavigationPhoto()
                else:
                    self.windowHandler("qgis")

            elif event.key() in range(Qt.Key_F5, Qt.Key_F13):
                val = event.key() - Qt.Key_F5
                self.keyboardZoom(val)

            elif event.key() == Qt.Key_1:
                self.basculerOutilTrace()

            elif event.key() == Qt.Key_Z and event.modifiers() & Qt.ControlModifier:
                # L'intercepteur clavier de la navigation avale tout KeyPress
                # et tout ShortcutOverride : le Ctrl+Z de QGIS ne répond pas
                # pendant la navigation. L'annulation passe donc par ici, et
                # deviendra une entrée de la table de raccourcis configurables.
                self.annulerEdition()

            elif event.key() == Qt.Key_S and event.modifiers() & Qt.ControlModifier:
                self.enregistrerEdition()

            elif event.key() == Qt.Key_M:
                if self.optWindow.mntArr is not None:
                    self.actionSuivreMNT.toggle()

            elif event.key() == Qt.Key_C:
                # Raccourci annoncé par l'infobulle du bouton de la barre d'outils.
                self.actionUnlockCursor.toggle()

        event.accept()

    def setInitialCursorAltitude(self):

        midLPix = (
            (self.realCropValueLeft[0] + self.realCropValueLeft[2]) / 2,
            (self.realCropValueLeft[1] + self.realCropValueLeft[3]) / 2,
        )
        midRPix = (
            (self.realCropValueRight[0] + self.realCropValueRight[2]) / 2,
            (self.realCropValueRight[1] + self.realCropValueRight[3]) / 2,
        )

        Z = self.dualManager.calculateZ(midLPix, midRPix)
        self.cursorAltitude = Z

        if self.buttonPosition:
            altitude = self.optWindow.readMNTWithCoord(self.buttonPosition)
            if altitude is not None:
                self.cursorAltitude = altitude

        elif self.lastCurrentView:
            self.cursorAltitude = self.lastCurrentView[2]

        elif self.optWindow.mntArr is not None:
            middleCoordLeft = self.leftPictureManager.pixelToCoord(
                midLPix, self.cursorAltitude
            )
            altitude = self.optWindow.readMNTWithCoord(middleCoordLeft)
            if altitude is not None:
                self.cursorAltitude = altitude

        self.afficherAltitude()

    def openMNT(self):
        pass
        # if not self.optWindow.currentMNTPath :
        #    self.mntDS = None
        #    return#

        # self.mntDS = gdal.Open(self.optWindow.currentMNTPath,gdal.GA_ReadOnly)
        # self.mntBand = self.mntDS.GetRasterBand(1)
        # self.mntGeo = self.mntDS.GetGeoTransform()
        # self.mntNoData = self.mntBand.GetNoDataValue()
        # self.mntXSize = self.mntDS.RasterXSize
        # self.mntYSize = self.mntDS.RasterYSize

    def readMNTWithCoordinate(self, coordinates):
        pass
        # if self.mntDS is None : return None

        # px = math.floor((coordinates[0] - self.mntGeo[0]) / self.mntGeo[1])
        # py = math.floor((coordinates[1] - self.mntGeo[3]) / self.mntGeo[5])
        # if px < 0 or py < 0 or px >= self.mntXSize or py >= self.mntYSize: return None

        # try : Z = self.mntBand.ReadAsArray(px,py,1,1)[0][0]
        # except : return None
        # if Z == self.mntNoData : return None
        # return Z

    def setStartingView(self):

        if self.buttonPosition:
            pxL, pyL = self.leftPictureManager.coordToPixel(
                self.buttonPosition, self.cursorAltitude
            )
            pxR, pyR = self.rightPictureManager.coordToPixel(
                self.buttonPosition, self.cursorAltitude
            )

            scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
            scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

            if (
                pxL < 0
                or pxL > self.fullLeftPicSize[0]
                or pyL < 0
                or pyL > self.fullLeftPicSize[1]
            ):
                self.setCenterView()
            elif (
                pxR < 0
                or pxR > self.fullRightPicSize[0]
                or pyR < 0
                or pyR > self.fullRightPicSize[1]
            ):
                self.setCenterView()

            else:
                scale = self.leftPictureManager.groundPixelSize / self.buttonMapUnit
                self.currentScale = scale

                self.graphWindowLeft.custom_centerOn(
                    scenePointL, scale, forceGroupCall=True
                )
                self.graphWindowRight.custom_centerOn(
                    scenePointR, scale, forceGroupCall=True
                )

        elif self.lastCurrentView:
            pxL, pyL = self.leftPictureManager.coordToPixel(
                self.lastCurrentView[:2], self.cursorAltitude
            )
            pxR, pyR = self.rightPictureManager.coordToPixel(
                self.lastCurrentView[:2], self.cursorAltitude
            )

            scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
            scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

            if (
                pxL < 0
                or pxL > self.fullLeftPicSize[0]
                or pyL < 0
                or pyL > self.fullLeftPicSize[1]
            ):
                self.setCenterView()
            elif (
                pxR < 0
                or pxR > self.fullRightPicSize[0]
                or pyR < 0
                or pyR > self.fullRightPicSize[1]
            ):
                self.setCenterView()
            else:
                scale = self.lastCurrentView[-1]
                self.currentScale = scale

                self.graphWindowLeft.custom_centerOn(
                    scenePointL, scale, forceGroupCall=True
                )
                self.graphWindowRight.custom_centerOn(
                    scenePointR, scale, forceGroupCall=True
                )

        else:
            self.setCenterView()

        # L'altitude du chargement est celle que setInitialCursorAltitude() a
        # établie : mesurée au centre des découpes, ou lue du MNT, ou reprise de
        # la vue précédente. La remesurer ici l'écraserait par la position des
        # vues qu'elle vient elle-même de dicter.
        self.afficherAltitude()
        self.buttonPosition = None

    def afficherAltitude(self):
        """Porte l'altitude courante au panneau, sans la recalculer.

        La navigation ne mesure pas l'altitude, elle la porte.
        Les deux vues étant toujours cadrées à partir de cursorAltitude, une
        mesure prise sur leur position ne pouvait que rendre la valeur déjà
        écrite, aux arrondis près (pixels entiers du défilement des vues,
        miroir de la vue droite), et ces arrondis s'accumulaient dans le même
        sens à chaque mouvement de souris.

        L'altitude ne change donc que par le MNT suivi, par la roulette, ou au
        chargement d'une paire, où setInitialCursorAltitude() l'établit. C'est
        la seule mesure de parallaxe qui subsiste, et elle n'est prise qu'une
        fois par paire, sur les centres des découpes.
        """
        # Altitude indéterminée : affichage de repli
        self.optWindow.ui.labelAltitude.setText(
            f"{self.cursorAltitude:.3f}" if self.cursorAltitude is not None else "N/D"
        )

    def setCenterView(self):
        gwL = self.graphWindowLeft.ui.graphicsView

        pxL = (self.realCropValueLeft[0] + self.realCropValueLeft[2]) / 2
        pyL = (self.realCropValueLeft[1] + self.realCropValueLeft[3]) / 2
        pxR = (self.realCropValueRight[0] + self.realCropValueRight[2]) / 2
        pyR = (self.realCropValueRight[1] + self.realCropValueRight[3]) / 2

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

        scaleX = gwL.viewport().width() / (self.leftPicSize[0] / 8)
        scaleY = gwL.viewport().height() / (self.leftPicSize[1] / 8)

        scale = min(scaleX, scaleY)
        self.currentScale = scale

        self.graphWindowLeft.custom_centerOn(scenePointL, scale, forceGroupCall=True)
        self.graphWindowRight.custom_centerOn(scenePointR, scale, forceGroupCall=True)

    def setBaseTransform(self):
        leftTransform = self.getQtransform(self.leftPictureManager)
        rightTransform = self.getQtransform(self.rightPictureManager)

        if not self.optWindow.ui.checkBoxFlip.isChecked():
            mirror_transform = QTransform()
            mirror_transform.scale(-1, 1)
            mirror_transform.translate(-self.rightPicSize[0], 0)
            rightTransform = rightTransform * mirror_transform

        self.graphWindowLeft.imageRoot.setTransform(leftTransform)
        self.graphWindowRight.imageRoot.setTransform(rightTransform)

    def setExtent2Canvas(self):

        LGV = self.graphWindowLeft.ui.graphicsView
        sceneRect = LGV.mapToScene(LGV.viewport().rect()).boundingRect()
        sceneCenter = sceneRect.center()
        centerPixel = self.graphWindowLeft.imageRoot.mapFromScene(sceneCenter)

        cx, cy = self.leftPictureManager.pixelToCoord(
            (centerPixel.x(), centerPixel.y()), self.cursorAltitude
        )
        meters_per_pixel = self.leftPictureManager.groundPixelSize / self.currentScale
        dpi = self.canvas.mapSettings().outputDpi()

        scale_canvas = meters_per_pixel * dpi / 0.0254  # Valeur pour mètre vers pouce
        self.canvas.zoomScale(scale_canvas)
        self.canvas.setCenter(QgsPointXY(cx, cy))
        self.canvas.refresh()

    def mouseMoveEvent(self, coordinate):
        if self.isLoadingPair:
            return

        if self.actionSuivreMNT.isChecked():
            mntAlt = self.optWindow.readMNTWithCoord(coordinate)
            if mntAlt is not None and mntAlt != self.optWindow.mntNodata:
                self.cursorAltitude = mntAlt

        pxL, pyL = self.leftPictureManager.coordToPixel(coordinate, self.cursorAltitude)
        pxR, pyR = self.rightPictureManager.coordToPixel(
            coordinate, self.cursorAltitude
        )

        self.endDrawPointLeft = QPointF(pxL, pyL)
        self.endDrawPointRight = QPointF(pxR, pyR)

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(self.endDrawPointLeft)
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(self.endDrawPointRight)

        curseurLibre = self.navigMapTool.curseurLibre

        self.graphWindowLeft.ui.graphicsView.setUpdatesEnabled(False)
        self.graphWindowRight.ui.graphicsView.setUpdatesEnabled(False)

        if curseurLibre:
            # Les photos restent fixes, seule la croix parcourt l'image.
            self.graphWindowLeft.placerCroix(scenePointL)
            self.graphWindowRight.placerCroix(scenePointR)
        else:
            # Les photos défilent sous la croix, immobile au centre des vues.
            scale = self.currentScale
            self.graphWindowLeft.custom_centerOn(scenePointL, scale)
            self.graphWindowRight.custom_centerOn(scenePointR, scale)

        self.graphWindowLeft.ui.graphicsView.setUpdatesEnabled(True)
        self.graphWindowRight.ui.graphicsView.setUpdatesEnabled(True)

        # Single coordinated repaint
        self.graphWindowLeft.ui.graphicsView.viewport().update()
        self.graphWindowRight.ui.graphicsView.viewport().update()

        # Le mouvement de souris n'est pas une mesure. Dans les
        # deux modes, les positions image viennent d'être calculées à partir de
        # cursorAltitude : en remesurer l'altitude reviendrait à lire la valeur
        # qu'on vient d'écrire, aux arrondis près, et ces arrondis
        # s'accumulaient. L'altitude ne change ici que par le MNG suivi, plus
        # haut dans la fonction.
        self.afficherAltitude()

        rangeX, rangeY, horsCadre = self.bordFranchi(self.endDrawPointLeft)

        # Un tracé en cours interdit le changement de modèle : la géométrie
        # serait coupée en deux par le chargement.
        if not self.traceEnCours and horsCadre:
            self.calculNextPairWithPos(rangeX, rangeY, self.endDrawPointLeft)

            return

        if self.traceEnCours and self.enableDraw and self.outilDeTraceActif():
            self.editCurrentWorkingLine()

    def wheelActionEvent(self, direction, modifier, mousePos):
        if self.isLoadingPair:
            return
        # if mod ctrl zoom
        if modifier & Qt.ControlModifier:
            scale = (
                self.leftPictureManager.groundPixelSize / self.canvas.mapUnitsPerPixel()
            )
            self.currentScale = scale
            newAltitude = self.cursorAltitude

        else:
            # Désactiver le suivi du MNT pour permettre l'action de la roulette
            self.actionSuivreMNT.setChecked(False)

            zoom_level = math.log2(self.currentScale)

            if zoom_level > 2:
                meter_changer = 0.1
            elif zoom_level > 1:
                meter_changer = 0.5
            elif zoom_level > 0:
                meter_changer = 1
            elif zoom_level > -1:
                meter_changer = 2
            else:
                meter_changer = 4

            if direction == 1:
                meter_changer *= 1
            else:
                meter_changer *= -1

            newAltitude = self.cursorAltitude + meter_changer

        pxL, pyL = self.leftPictureManager.coordToPixel(mousePos, newAltitude)
        pxR, pyR = self.rightPictureManager.coordToPixel(mousePos, newAltitude)

        self.endDrawPointLeft = QPointF(pxL, pyL)
        self.endDrawPointRight = QPointF(pxR, pyR)

        scenePointL = self.graphWindowLeft.imageRoot.mapToScene(QPointF(pxL, pyL))
        scenePointR = self.graphWindowRight.imageRoot.mapToScene(QPointF(pxR, pyR))

        # En mode curseur libre, la roulette seule règle la parallaxe sans
        # bouger les photos : la croix se décale sur chaque image. Le zoom
        # (CTRL + roulette) recadre les vues dans les deux modes, puisqu'il
        # change l'échelle d'affichage et non la position du curseur.
        if self.navigMapTool.curseurLibre and not modifier & Qt.ControlModifier:
            self.graphWindowLeft.placerCroix(scenePointL)
            self.graphWindowRight.placerCroix(scenePointR)
        else:
            self.graphWindowLeft.custom_centerOn(scenePointL, self.currentScale)
            self.graphWindowRight.custom_centerOn(scenePointR, self.currentScale)

        # La roulette commande l'altitude, elle ne la mesure
        # pas. newAltitude est la valeur voulue : celle du pas de parallaxe, ou
        # l'altitude inchangée sous CTRL, où la roulette ne fait que zoomer.
        self.cursorAltitude = newAltitude
        self.afficherAltitude()

        if self.traceEnCours and self.enableDraw and self.outilDeTraceActif():
            self.editCurrentWorkingLine()

    def editCurrentWorkingLine(self):
        if not self.currentLeftLineObj:
            self.currentLeftLineObj = QGraphicsLineItem(
                parent=self.graphWindowLeft.imageRoot
            )
            self.currentLeftLineObj.setPen(self.my_pen)
            self.graphWindowLeft.drawingLineGroup.addToGroup(self.currentLeftLineObj)

        if not self.currentRightLineObj:
            self.currentRightLineObj = QGraphicsLineItem(
                parent=self.graphWindowRight.imageRoot
            )
            self.currentRightLineObj.setPen(self.my_pen)
            self.graphWindowRight.drawingLineGroup.addToGroup(self.currentRightLineObj)

        lineL = QLineF(self.startDrawPointLeft, self.endDrawPointLeft)
        lineR = QLineF(self.startDrawPointRight, self.endDrawPointRight)

        self.currentLeftLineObj.setLine(lineL)
        self.currentRightLineObj.setLine(lineR)

    def bordFranchi(self, pointImageGauche):
        """Bornes du cadrage et franchissement, dans le repère de la photo gauche.

        La marge de 2 % du cadrage courant évite de déclencher un changement de
        modèle sur un tremblement du curseur au ras du bord.
        """
        pourcent = 2 / 100
        deltaX = self.leftPicSize[0] * pourcent
        deltaY = self.leftPicSize[1] * pourcent

        rangeX = (
            self.realCropValueLeft[0] + deltaX,
            self.realCropValueLeft[2] - deltaX,
        )
        rangeY = (
            self.realCropValueLeft[1] + deltaY,
            self.realCropValueLeft[3] - deltaY,
        )

        horsCadre = (
            pointImageGauche.x() <= rangeX[0]
            or pointImageGauche.x() >= rangeX[1]
            or pointImageGauche.y() <= rangeY[0]
            or pointImageGauche.y() >= rangeY[1]
        )

        return rangeX, rangeY, horsCadre

    def changerModeleSiBordFranchi(self, pointImageGauche):
        """Charge le modèle voisin si la position donnée sort du cadrage.

        En hors-synchronisation, la position à tester est le centre de la vue
        et non la croix : c'est la vue qui se déplace.
        """
        rangeX, rangeY, horsCadre = self.bordFranchi(pointImageGauche)
        if horsCadre:
            self.calculNextPairWithPos(rangeX, rangeY, pointImageGauche)

    def calculNextPairWithPos(self, rangeX, rangeY, qpoint):
        voisinDisponible = {
            "U": bool(self.currentUpID),
            "D": bool(self.currentDownID),
            "L": bool(self.currentLeftID),
            "R": bool(self.currentRightID),
        }

        # La table de correspondance bord franchi -> modèle voisin, qui dépend
        # de l'orientation de la caméra, vit dans orientationModele.py : c'est
        # la seule pièce de cette décision qui se vérifie sans QGIS.
        direction = directionProchainModele(
            math.degrees(self.leftPictureManager.kappa),
            PAR_CAMERA_ORIENTATION_TOLERANCE_DEG,
            qpoint.x(),
            qpoint.y(),
            rangeX,
            rangeY,
            voisinDisponible,
        )

        if direction is not None:
            self.findNextPair(direction)

    # --- Gestes d'édition ---------------------------------------------------
    #
    # La cascade de `if`/`elif` de 133 lignes qui occupait cette place ne
    # traitait que les polygones et les points : un clic sur une couche de
    # lignes n'avait aucun effet et ne laissait aucune trace. La décision est
    # maintenant une table, dans `editionOutils`, et chaque case de la table a
    # sa méthode ci-dessous, nommée de la même façon.

    def mousePressEvent(self, mouseButton, mousePos, modificateurs=Qt.NoModifier):
        if not self.enableDraw or self.vectorLayer is None:
            return

        cle, motif = editionOutils.resoudreTraitement(
            self.outilActif,
            self.typeGeometrieCouche(),
            self.BOUTONS_QT.get(mouseButton),
            self.traceEnCours,
        )

        if cle is None:
            if motif:
                avertir_utilisateur(motif)
            return

        self.tableTraitements[cle](mousePos, modificateurs)

    def typeGeometrieCouche(self):
        """Type de géométrie de la couche éditable, en clé de `editionOutils`."""
        if self.vectorLayer is None:
            return None
        return self.TYPES_GEOMETRIE_QGIS.get(self.vectorLayer.geometryType())

    def coucheAUnZ(self):
        return self.vectorLayer is not None and QgsWkbTypes.hasZ(
            self.vectorLayer.wkbType()
        )

    def outilDeTraceActif(self):
        return self.outilActif in editionOutils.OUTILS_DE_TRACE

    def altitudeEcriture(self):
        """Altitude à écrire, ou un refus motivé une seule fois.

        L'altitude vient de `cursorAltitude`, celle que la session porte et que
        la croix affiche. Le code d'origine relisait le MNT à chaque clic : la
        cote écrite pouvait donc différer du trait que le photo-interprète
        voyait à l'écran, de plusieurs mètres sous couvert.
        """
        autorise, altitude, motif = editionOutils.altitudeEcriture(
            self.coucheAUnZ(), self.cursorAltitude
        )
        if autorise:
            self.altitudeRefusSignalee = False
            return True, altitude

        if not self.altitudeRefusSignalee:
            avertir_utilisateur(motif)
            self.journal.warning("Écriture refusée : %s", motif)
            self.altitudeRefusSignalee = True
        return False, None

    def toleranceSelection(self):
        """Rayon de désignation d'une entité, en unités terrain.

        Huit pixels de canevas, convertis à l'échelle courante : comme
        `setExtent2Canvas()` accorde l'échelle du canevas à celle des vues
        photo, la tolérance vaut autant de pixels à l'écran stéréo qu'au
        canevas. Elle suit donc le zoom, ce qu'une tolérance en mètres ne
        ferait pas.
        """
        unitesParPixel = self.canvas.mapUnitsPerPixel()
        if not math.isfinite(unitesParPixel) or unitesParPixel <= 0:
            self.journal.warning(
                "Échelle du canevas indéterminable (%r) ; tolérance de "
                "sélection repliée sur un mètre par pixel",
                unitesParPixel,
            )
            unitesParPixel = 1.0
        return unitesParPixel * EDITION_SELECTION_TOLERANCE_PX

    def selectionner(self, mousePos, modificateurs):
        """Désigne l'entité sous le clic, dans les trois types de géométrie.

        Aucune sélection n'existait dans l'extension : le seul appel du dépôt
        était le `removeSelection()` du découpage. La sélection de QGIS est ici
        la source unique de vérité, et la surbrillance des vues photo la suit
        par `drawPolygon()`.
        """
        tolerance = self.toleranceSelection()
        rectangle = QgsRectangle(
            mousePos[0] - tolerance,
            mousePos[1] - tolerance,
            mousePos[0] + tolerance,
            mousePos[1] + tolerance,
        )
        pointClic = QgsGeometry.fromPointXY(QgsPointXY(mousePos[0], mousePos[1]))
        typeGeo = self.typeGeometrieCouche()

        candidats = []
        for entite in editionVecteur.entitesDansRectangle(self.vectorLayer, rectangle):
            geometrie = entite.geometry()
            if geometrie is None or geometrie.isNull():
                continue
            if typeGeo == editionOutils.TYPE_POLYGONE:
                mesure = geometrie.area()
            elif typeGeo == editionOutils.TYPE_LIGNE:
                mesure = geometrie.length()
            else:
                mesure = 0.0
            candidats.append(
                {
                    "fid": entite.id(),
                    "type": typeGeo,
                    "distance": geometrie.distance(pointClic),
                    "contient": geometrie.intersects(pointClic),
                    "mesure": mesure,
                }
            )

        choisie = editionOutils.choisirEntite(candidats)
        additive = bool(modificateurs & (Qt.ControlModifier | Qt.ShiftModifier))

        if choisie is None:
            if not additive:
                self.vectorLayer.removeSelection()
            return

        if additive:
            self.vectorLayer.select(choisie["fid"])
        else:
            self.vectorLayer.selectByIds([choisie["fid"]])

        # Le compte est porté au bandeau : sans retour chiffré, l'utilisateur
        # ne sait pas combien d'entités la combinaison va consommer.
        avertir_utilisateur(
            "%d entité(s) sélectionnée(s) sur « %s »."
            % (self.vectorLayer.selectedFeatureCount(), self.vectorLayerName),
            niveau=logging.INFO,
            duree_secondes=3,
        )

    def viderSelection(self, _mousePos, _modificateurs):
        """Clic droit sous l'outil Sélectionner : la sélection est vidée."""
        self.vectorLayer.removeSelection()

    def fusionnerSelection(self, _mousePos, _modificateurs):
        """Clic droit sous l'outil Combiner : les entités choisies fusionnent."""
        if editionVecteur.fusionnerSelection(self.vectorLayer):
            self.rafraichirGeometries()

    def ajouterPoint(self, mousePos, _modificateurs):
        """Ajoute un point d'un seul clic, puis ouvre son formulaire."""
        autorise, altitude = self.altitudeEcriture()
        if not autorise:
            return

        if altitude is None:
            geometrie = QgsGeometry.fromPointXY(QgsPointXY(mousePos[0], mousePos[1]))
        else:
            geometrie = QgsGeometry(QgsPoint(mousePos[0], mousePos[1], altitude))

        # Les deux vues photo sont en plein écran : la fenêtre de QGIS passe
        # devant le temps de la saisie des attributs, puis les photos
        # reviennent. Le `finally` garantit ce retour même si le formulaire
        # lève, ce que le code d'origine ne faisait pas.
        self.windowHandler("qgis")
        try:
            entite = editionVecteur.ajouterEntite(
                self.vectorLayer, geometrie, ouvrirFormulaire=True
            )
        finally:
            self.windowHandler("picture")

        if entite is not None:
            self.rafraichirGeometries()

    def poserSommet(self, mousePos, _modificateurs):
        """Ajoute un sommet au tracé en cours, pour une ligne ou un polygone.

        Le même geste sert à l'ajout et au découpage, et désormais aux lignes
        comme aux polygones : c'est le tracé point par point d'origine, dont
        seule la clôture diffère selon l'outil et le type.
        """
        autorise, altitude = self.altitudeEcriture()
        if not autorise:
            return

        # Le trait affiché dans les deux vues est projeté à l'altitude portée,
        # quel que soit le type de la couche : une couche sans Z n'a pas besoin
        # d'altitude pour son géométrie, mais le tracé en a besoin pour se
        # dessiner. Sans cette garde, coordToPixel() recevait None.
        if self.cursorAltitude is None:
            avertir_utilisateur(editionOutils.MOTIF_ALTITUDE_INDETERMINEE)
            self.journal.warning("Tracé refusé : aucune altitude portée")
            return

        if not self.traceEnCours:
            pxL, pyL = self.leftPictureManager.coordToPixel(
                mousePos, self.cursorAltitude
            )
            pxR, pyR = self.rightPictureManager.coordToPixel(
                mousePos, self.cursorAltitude
            )
            self.startDrawPointLeft = QPointF(pxL, pyL)
            self.startDrawPointRight = QPointF(pxR, pyR)
            self.traceEnCours = True
        else:
            self.startDrawPointLeft = self.endDrawPointLeft
            self.startDrawPointRight = self.endDrawPointRight
            self.listLeftLineObj.append(self.currentLeftLineObj)
            self.listRightLineObj.append(self.currentRightLineObj)
            self.currentLeftLineObj = None
            self.currentRightLineObj = None

        if altitude is None:
            self.list3DPoint.append(QgsPoint(mousePos[0], mousePos[1]))
        else:
            self.list3DPoint.append(QgsPoint(mousePos[0], mousePos[1], altitude))

    def cloreLigne(self, _mousePos, _modificateurs):
        """Clic droit : la ligne tracée est ajoutée telle quelle, sans anneau."""
        sommets = list(self.list3DPoint)
        self.annulerTraceEnCours()

        if len(sommets) < 2:
            avertir_utilisateur(
                "Une ligne demande au moins deux sommets : le tracé est abandonné."
            )
            return

        geometrie = QgsGeometry(QgsLineString(sommets))
        if editionVecteur.ajouterEntite(self.vectorLayer, geometrie) is not None:
            self.rafraichirGeometries()

    def clorePolygone(self, _mousePos, _modificateurs):
        """Clic droit : l'anneau est refermé et le polygone ajouté.

        Un tracé sous l'outil Ajouter produit toujours une entité neuve, même
        s'il touche ou recoupe ses voisins. Le code d'origine fusionnait avec
        le premier polygone intersecté, ce qu'un simple contact de limite
        suffisait à déclencher : des peuplements adjacents, qui partagent
        toujours une limite, s'avalaient l'un l'autre. La combinaison est
        maintenant un geste explicite, par l'outil Combiner.
        """
        sommets = list(self.list3DPoint)
        self.annulerTraceEnCours()

        distincts = {(sommet.x(), sommet.y()) for sommet in sommets}
        if len(distincts) < 3:
            avertir_utilisateur(
                "Un polygone demande au moins trois sommets distincts : le "
                "tracé est abandonné."
            )
            return

        anneau = QgsLineString(sommets + [sommets[0]])
        geometrie = QgsGeometry(QgsPolygon(anneau))
        if editionVecteur.ajouterEntite(self.vectorLayer, geometrie) is not None:
            self.rafraichirGeometries()

    def cloreDecoupe(self, _mousePos, _modificateurs):
        """Clic droit sous l'outil Découper : la ligne de coupe est appliquée."""
        sommets = list(self.list3DPoint)
        self.annulerTraceEnCours()

        if editionVecteur.decouper(self.vectorLayer, sommets):
            self.rafraichirGeometries()

    def annulerTraceEnCours(self):
        """Abandonne le tracé en cours : sommets accumulés et traits cyan.

        Le ménage n'était fait qu'au clic droit. Partout ailleurs, seul le
        drapeau revenait à son état initial : au changement de modèle, les
        sommets du geste précédent restaient dans les listes et les traits
        cyan dans les scènes, et la géométrie suivante enjambait deux modèles.
        """
        self.traceEnCours = False
        self.list3DPoint = []

        for fenetre, nomCourant, nomListe in (
            (
                getattr(self, "graphWindowLeft", None),
                "currentLeftLineObj",
                "listLeftLineObj",
            ),
            (
                getattr(self, "graphWindowRight", None),
                "currentRightLineObj",
                "listRightLineObj",
            ),
        ):
            traits = list(getattr(self, nomListe, []))
            traits.append(getattr(self, nomCourant, None))
            if fenetre is not None:
                for trait in traits:
                    if trait is None:
                        continue
                    fenetre.drawingLineGroup.removeFromGroup(trait)
                    fenetre.scene.removeItem(trait)
            setattr(self, nomListe, [])
            setattr(self, nomCourant, None)

        # La bande élastique du canevas de QGIS porte le même tracé : la
        # laisser en place afficherait un geste qui n'existe plus.
        if hasattr(self, "navigMapTool"):
            self.navigMapTool.reinitialiserTrace()

    def rafraichirGeometries(self):
        """Relance le calcul des géométries affichées, si les vues sont là.

        Une édition faite avant l'affichage des photos ne doit pas lancer le
        fil : il lit les emprises de la paire courante, qui n'existe pas
        encore.
        """
        if self.enableShow and hasattr(self, "graphWindowLeft"):
            self.startPolygonThread()

    # --- État des outils d'édition ----------------------------------------

    def changerOutilActif(self, action):
        """Prend acte du changement d'outil d'édition."""
        self.outilActif = action.data()

        if not hasattr(self, "optWindow"):
            # Aucune session ouverte : l'outil est mémorisé et vaudra à
            # l'ouverture, comme le fait le bouton du curseur libre.
            return

        # Un tracé commencé avec l'outil précédent n'a plus de sens.
        self.annulerTraceEnCours()
        self.majActivationTrace()
        self.synchroniserRadiosTrace()
        self.journal.info("Outil d'édition : %s", self.outilActif)

    def basculerOutilTrace(self):
        """Touche 1 : alterne entre Ajouter et Découper, comme avant.

        La touche basculait les deux radios du panneau. Elle commande
        maintenant l'outil, et la synchronisation redescend vers les radios.
        Depuis un outil qui ne trace pas, elle ramène au tracé.
        """
        if self.outilActif == editionOutils.OUTIL_AJOUTER:
            voulu = editionOutils.OUTIL_DECOUPER
        elif self.outilActif == editionOutils.OUTIL_DECOUPER:
            voulu = editionOutils.OUTIL_AJOUTER
        else:
            self.journal.info(
                "Touche 1 depuis l'outil %s : retour au tracé", self.outilActif
            )
            voulu = editionOutils.OUTIL_AJOUTER

        self.actionsOutil[voulu].setChecked(True)
        self.changerOutilActif(self.actionsOutil[voulu])

    def radioTraceBasculee(self):
        """Suit le choix fait sur les radios Dessiner et Découper du panneau."""
        if not hasattr(self, "optWindow"):
            return

        voulu = (
            editionOutils.OUTIL_DECOUPER
            if self.optWindow.ui.radioButtonCut.isChecked()
            else editionOutils.OUTIL_AJOUTER
        )
        if voulu == self.outilActif:
            return

        self.actionsOutil[voulu].setChecked(True)
        self.changerOutilActif(self.actionsOutil[voulu])

    def majActivationTrace(self):
        """Accorde la bande élastique du canevas à l'outil et à la couche.

        Elle était conditionnée à la présence d'un MNT et à une couche
        polygonale. Le MNT n'est plus exigé pour éditer et les lignes se
        tracent aussi : la condition est désormais un outil de tracé et un
        type de géométrie qui se trace.
        """
        if not hasattr(self, "navigMapTool"):
            return

        self.navigMapTool.activateDrawing = bool(
            self.enableDraw
            and self.outilDeTraceActif()
            and self.typeGeometrieCouche()
            in (editionOutils.TYPE_LIGNE, editionOutils.TYPE_POLYGONE)
        )

    def synchroniserRadiosTrace(self):
        """Accorde les radios Dessiner et Découper à l'outil actif.

        Les deux radios gardent le sens qu'elles avaient : quel tracé
        s'appliquerait. Elles sont grisées quand l'outil actif n'est pas un
        outil de tracé, où leur état coché est sans portée. Un couple de radios
        exclusives ne saurait pas représenter quatre outils, et le panneau ne
        doit pas recevoir de nouveau contrôle.
        """
        if not hasattr(self, "optWindow"):
            return

        radios = (self.optWindow.ui.radioButtonDraw, self.optWindow.ui.radioButtonCut)
        actif = bool(self.enableDraw and self.outilDeTraceActif())
        for radio in radios:
            radio.setEnabled(actif)

        if not actif:
            return

        for radio in radios:
            radio.blockSignals(True)
        try:
            if self.outilActif == editionOutils.OUTIL_DECOUPER:
                radios[1].setChecked(True)
            else:
                radios[0].setChecked(True)
        finally:
            for radio in radios:
                radio.blockSignals(False)

    # --- Session d'édition --------------------------------------------------

    def raccorderCoucheEditable(self, couche):
        """Suit l'état d'édition et la sélection de la couche choisie.

        Le raccordement est rompu avant d'en poser un autre : la couche change
        au fil de la session, et les connexions s'y empileraient sans cela.
        """
        self.rompreRaccordementCouche()
        if couche is None:
            return

        couche.editingStarted.connect(self.majEtatActionsEdition)
        couche.editingStopped.connect(self.majEtatActionsEdition)
        couche.layerModified.connect(self.majEtatActionsEdition)
        couche.selectionChanged.connect(self.selectionCoucheChangee)
        couche.undoStack().canUndoChanged.connect(self.majEtatActionsEdition)

        self.coucheRaccordee = couche
        self.majEtatActionsEdition()

    def rompreRaccordementCouche(self):
        couche = self.coucheRaccordee
        self.coucheRaccordee = None
        if couche is None:
            return

        for nomSignal, recepteur in (
            ("editingStarted", self.majEtatActionsEdition),
            ("editingStopped", self.majEtatActionsEdition),
            ("layerModified", self.majEtatActionsEdition),
            ("selectionChanged", self.selectionCoucheChangee),
        ):
            try:
                getattr(couche, nomSignal).disconnect(recepteur)
            except (TypeError, RuntimeError):
                # Connexion déjà rompue, ou couche détruite par QGIS.
                self.journal.debug("Signal %s de couche déjà rompu", nomSignal)

        try:
            couche.undoStack().canUndoChanged.disconnect(self.majEtatActionsEdition)
        except (TypeError, RuntimeError):
            self.journal.debug("Pile d'annulation de couche déjà rompue")

    def majEtatActionsEdition(self, *_args):
        """Active ou grise les boutons Enregistrer et Annuler."""
        couche = self.vectorLayer
        enAttente, _nombre = editionVecteur.modificationsEnAttente(couche)
        self.actionEnregistrerEdition.setEnabled(bool(enAttente))

        peutAnnuler = False
        if couche is not None and couche.isEditable():
            try:
                peutAnnuler = couche.undoStack().canUndo()
            except RuntimeError:
                peutAnnuler = False
        self.actionAnnulerEdition.setEnabled(bool(peutAnnuler))

    def selectionCoucheChangee(self, *_args):
        """La sélection a changé, ici ou dans QGIS : la surbrillance suit.

        Aucun calcul n'est relancé : les formes sont déjà projetées, seule leur
        mise en évidence change. Relancer le fil à chaque clic de sélection
        serait un gel perceptible, puisqu'il attend son prédécesseur sur le
        thread d'interface.
        """
        self.majEtatActionsEdition()
        if self.enableShow and self.polygonL2Draw:
            self.drawPolygon()

    def enregistrerEdition(self):
        """Écrit les modifications en attente de la couche éditable."""
        if self.vectorLayer is None:
            avertir_utilisateur("Aucune couche vectorielle choisie.")
            return

        editionVecteur.enregistrer(self.vectorLayer)
        self.majEtatActionsEdition()

    def annulerEdition(self):
        """Défait le dernier geste d'édition sur la couche éditable."""
        if self.vectorLayer is None:
            return

        if editionVecteur.annulerDernier(self.vectorLayer):
            self.rafraichirGeometries()
        self.majEtatActionsEdition()

    def demanderSortEditions(self):
        """Propose d'enregistrer les modifications en attente, à la fermeture.

        Rien n'est perdu si l'utilisateur décline : le tampon d'édition
        appartient à la couche, qui survit à la session StereoPhoto, et QGIS le
        conserve. La question évite que le photo-interprète s'en aille en
        croyant son travail écrit, et lui épargne de rouvrir la session pour
        cela. Elle n'offre donc pas d'annuler la fermeture : il n'y a rien à
        sauver de la fermeture elle-même.
        """
        couche = self.vectorLayer
        enAttente, nombre = editionVecteur.modificationsEnAttente(couche)
        if not enAttente:
            return

        boite = QMessageBox(self.iface.mainWindow())
        boite.setWindowTitle("StereoPhoto : modifications en attente")
        boite.setIcon(QMessageBox.Question)
        boite.setText(
            "La couche « %s » porte %d modification(s) non enregistrée(s)."
            % (couche.name(), nombre)
        )
        boite.setInformativeText(
            "Les enregistrer maintenant ? Sinon elles restent en attente dans "
            "QGIS, qui les conservera jusqu'à l'enregistrement de la couche."
        )
        boutonEnregistrer = boite.addButton("Enregistrer", QMessageBox.AcceptRole)
        boite.addButton("Laisser en attente", QMessageBox.RejectRole)
        boite.setDefaultButton(boutonEnregistrer)
        boite.exec_()

        if boite.clickedButton() is boutonEnregistrer:
            editionVecteur.enregistrer(couche)
        else:
            self.journal.info(
                "%d modification(s) laissée(s) en attente sur la couche %s",
                nombre,
                couche.name(),
            )

    def keyboardZoom(self, value):
        zoomLevels = [128, 64, 32, 16, 8, 4, 2, 1]
        scaleFactor = zoomLevels[value]

        scaleX = self.leftPicSize[0] / scaleFactor
        scaleY = self.leftPicSize[1] / scaleFactor

        gwL = self.graphWindowLeft.ui.graphicsView
        gwR = self.graphWindowRight.ui.graphicsView

        scaleW = gwL.viewport().width() / scaleX
        scaleH = gwL.viewport().height() / scaleY

        scale = min(scaleW, scaleH)
        self.currentScale = scale

        center_scene_L = gwL.mapToScene(gwL.viewport().rect().center())
        center_scene_R = gwR.mapToScene(gwR.viewport().rect().center())

        # Le zoom clavier recadre sur le centre des vues. En mode curseur libre,
        # la croix marque un point de l'image : la ramener au centre la ferait
        # sauter le temps d'un zoom, puis se replacer au mouvement suivant.
        recentrerCroix = not self.navigMapTool.curseurLibre

        self.graphWindowLeft.custom_centerOn(
            center_scene_L, self.currentScale, recentrerCroix=recentrerCroix
        )
        self.graphWindowRight.custom_centerOn(
            center_scene_R, self.currentScale, recentrerCroix=recentrerCroix
        )

        self.setExtent2Canvas()
