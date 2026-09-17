'''
Journalisation de l'extension StereoPhoto

Un fichier par jour est écrit sous le dossier de profil QGIS de l'utilisateur.
Au changement de journée, le fichier de la veille est déplacé dans le
sous-dossier d'archive, et les archives plus vieilles que la rétention sont
supprimées.

Les messages sont aussi envoyés à l'onglet « StereoPhoto » du panneau Journal de
QGIS lorsque l'extension tourne dans QGIS. Le coeur du module ne dépend ni de
QGIS ni de Qt : il reste utilisable et testable hors de QGIS, où seul le fichier
est écrit.

Utilisation dans un module de l'extension :

    from .journal import obtenir_journal
    journal = obtenir_journal(__name__)
    journal.warning("Fichier PAR écarté : %s", chemin)
    journal.exception("Échec du chargement de l'image")   # avec la trace

L'initialisation et la fermeture sont faites une seule fois, par la classe
principale du plugin (voir stereoPhoto.py).
'''

import configparser
import logging
import os
import time
from datetime import datetime, timedelta

from .config import (
    JOURNAL_NIVEAU_DEFAUT,
    JOURNAL_PREFIXE_FICHIER,
    JOURNAL_RETENTION_JOURS,
    JOURNAL_SOUS_DOSSIER,
    JOURNAL_SOUS_DOSSIER_ARCHIVE,
)

try:
    from qgis.core import Qgis, QgsApplication, QgsMessageLog
except ImportError:
    Qgis = None
    QgsApplication = None
    QgsMessageLog = None

#Nom du journal racine; chaque module obtient un journal « StereoPhoto.<module> »
NOM_JOURNAL_RACINE = "StereoPhoto"

#Onglet du panneau Journal de QGIS
ETIQUETTE_QGIS = "StereoPhoto"

FORMAT_FICHIER = ("%(asctime)s | %(levelname)-8s | %(name)s"
                  " | %(threadName)s | %(message)s")
FORMAT_QGIS = "%(levelname)s | %(name)s | %(threadName)s | %(message)s"

FORMAT_JOUR = "%Y-%m-%d"


def jour_courant():
    '''Date du jour au format utilisé dans le nom des fichiers.'''

    return time.strftime(FORMAT_JOUR)


def nom_fichier_du_jour(jour, prefixe=JOURNAL_PREFIXE_FICHIER):
    '''Nom du fichier de journal correspondant à une date.'''

    return "{}-{}.log".format(prefixe, jour)


def archiver_journees_precedentes(dossier, jour, prefixe=JOURNAL_PREFIXE_FICHIER,
                                  nom_archive=JOURNAL_SOUS_DOSSIER_ARCHIVE):
    '''Déplace dans le sous-dossier d'archive les fichiers de journal dont la
    date n'est pas celle passée en paramètre, et retourne leurs nouveaux chemins.

    Un fichier encore ouvert par une autre instance de QGIS ne peut pas être
    déplacé sous Windows : il est laissé en place et sera repris au prochain
    démarrage.
    '''

    if not os.path.isdir(dossier):
        return []

    fichier_du_jour = nom_fichier_du_jour(jour, prefixe)
    dossier_archive = os.path.join(dossier, nom_archive)
    deplaces = []

    for nom in sorted(os.listdir(dossier)):
        if not nom.startswith(prefixe + "-") or not nom.endswith(".log"):
            continue
        if nom == fichier_du_jour:
            continue

        source = os.path.join(dossier, nom)
        if not os.path.isfile(source):
            continue

        cible = os.path.join(dossier_archive, nom)
        try:
            os.makedirs(dossier_archive, exist_ok=True)
            if os.path.exists(cible):
                #Même journée déjà archivée : on ajoute à la suite plutôt que
                #d'écraser, les deux fichiers couvrant la même date.
                with open(source, encoding='utf-8', errors='replace') as entree:
                    contenu = entree.read()
                with open(cible, 'a', encoding='utf-8') as sortie:
                    sortie.write(contenu)
                os.remove(source)
            else:
                os.replace(source, cible)
            deplaces.append(cible)
        except OSError:
            continue

    return deplaces


def purger_archives(dossier, retention_jours=JOURNAL_RETENTION_JOURS,
                    prefixe=JOURNAL_PREFIXE_FICHIER,
                    nom_archive=JOURNAL_SOUS_DOSSIER_ARCHIVE):
    '''Supprime les archives dont la date inscrite au nom dépasse la rétention,
    et retourne les chemins supprimés.

    La date vient du nom du fichier et non de sa date de modification : une copie
    ou une synchronisation modifie la seconde, jamais la première.
    '''

    dossier_archive = os.path.join(dossier, nom_archive)
    if not os.path.isdir(dossier_archive):
        return []

    limite = datetime.now() - timedelta(days=retention_jours)
    supprimes = []

    for nom in sorted(os.listdir(dossier_archive)):
        if not nom.startswith(prefixe + "-") or not nom.endswith(".log"):
            continue
        try:
            date_fichier = datetime.strptime(nom[len(prefixe) + 1:-4], FORMAT_JOUR)
        except ValueError:
            #Nom qui ne porte pas de date exploitable : on n'y touche pas.
            continue

        if date_fichier >= limite:
            continue

        chemin = os.path.join(dossier_archive, nom)
        try:
            os.remove(chemin)
            supprimes.append(chemin)
        except OSError:
            continue

    return supprimes


class JournalQuotidienHandler(logging.FileHandler):
    '''Écrit dans un fichier nommé par la date du jour.

    Le nom du fichier porte la date dès l'écriture : aucun fichier ouvert n'est
    jamais renommé, contrairement à TimedRotatingFileHandler. Au premier message
    d'une nouvelle journée, le flux est rouvert sur le fichier du nouveau jour et
    les fichiers des jours précédents sont archivés.
    '''

    def __init__(self, dossier, prefixe=JOURNAL_PREFIXE_FICHIER,
                 nom_archive=JOURNAL_SOUS_DOSSIER_ARCHIVE, encoding='utf-8'):
        self.dossier = dossier
        self.prefixe = prefixe
        self.nom_archive = nom_archive
        self.jour = jour_courant()
        chemin = os.path.join(dossier, nom_fichier_du_jour(self.jour, prefixe))
        logging.FileHandler.__init__(self, chemin, mode='a', encoding=encoding)

    def emit(self, record):
        #emit() est appelé sous le verrou du handler : la bascule de journée est
        #donc sûre entre les threads du plugin.
        jour = jour_courant()
        if jour != self.jour:
            self._changer_de_jour(jour)
        logging.FileHandler.emit(self, record)

    def _changer_de_jour(self, jour):
        #Le flux est fermé sans passer par close(), qui retirerait le handler de
        #la liste interne de logging alors qu'il reste en service.
        if self.stream is not None:
            try:
                self.flush()
            finally:
                flux = self.stream
                self.stream = None
                try:
                    flux.close()
                except OSError:
                    pass

        self.jour = jour
        nom = nom_fichier_du_jour(jour, self.prefixe)
        self.baseFilename = os.path.abspath(os.path.join(self.dossier, nom))
        self.stream = self._open()

        archiver_journees_precedentes(self.dossier, jour, self.prefixe,
                                      self.nom_archive)


class HandlerMessageLogQgis(logging.Handler):
    '''Recopie les messages dans l'onglet « StereoPhoto » du panneau Journal de
    QGIS. Sans QGIS, le handler ne fait rien.
    '''

    def emit(self, record):
        if QgsMessageLog is None or Qgis is None:
            return

        if record.levelno >= logging.ERROR:
            niveau = Qgis.Critical
        elif record.levelno >= logging.WARNING:
            niveau = Qgis.Warning
        else:
            niveau = Qgis.Info

        try:
            QgsMessageLog.logMessage(self.format(record), ETIQUETTE_QGIS, niveau)
        except Exception:
            #Une erreur de journalisation ne doit jamais interrompre le plugin.
            self.handleError(record)


def version_extension():
    '''Version déclarée dans metadata.txt, ou None si elle est illisible.'''

    chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metadata.txt')
    lecteur = configparser.ConfigParser()
    try:
        lecteur.read(chemin, encoding='utf-8')
        return lecteur.get('general', 'version')
    except (configparser.Error, OSError):
        return None


def dossier_journal_par_defaut():
    '''Dossier des journaux : sous le profil QGIS de l'utilisateur, ou à côté du
    module lorsque QGIS n'est pas disponible (tests, exécution hors QGIS).
    '''

    base = ''
    if QgsApplication is not None:
        try:
            base = QgsApplication.qgisSettingsDirPath()
        except Exception:
            base = ''

    if not base:
        base = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base, *JOURNAL_SOUS_DOSSIER.split('/'))


def obtenir_journal(nom):
    '''Journal d'un module : obtenir_journal(__name__).

    Le nom du paquet est retiré, pour que les lignes affichent « gestionDossier »
    plutôt que « src.gestionDossier ».
    '''

    return logging.getLogger(NOM_JOURNAL_RACINE + '.' + nom.rsplit('.', 1)[-1])


def fermer_journal():
    '''Ferme et retire les handlers du journal.

    À appeler au déchargement de l'extension : sous Windows, un handler laissé
    ouvert garde un verrou sur le fichier, et un rechargement de l'extension
    écrirait chaque message deux fois.
    '''

    logger = logging.getLogger(NOM_JOURNAL_RACINE)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        try:
            handler.close()
        except OSError:
            continue


def initialiser_journal(dossier=None, niveau=None):
    '''Prépare la journalisation et retourne le chemin du fichier du jour, ou
    None si aucun fichier n'a pu être ouvert.

    La fonction est idempotente : les handlers déjà en place sont retirés avant
    d'en poser de nouveaux, donc un rechargement d'extension ne produit pas de
    doublons.
    '''

    if dossier is None:
        dossier = dossier_journal_par_defaut()
    if niveau is None:
        niveau = JOURNAL_NIVEAU_DEFAUT

    logger = logging.getLogger(NOM_JOURNAL_RACINE)
    fermer_journal()
    logger.setLevel(niveau)
    #Les messages ne remontent pas au journal racine de Python : la console
    #Python de QGIS est partagée par toutes les extensions.
    logger.propagate = False

    chemin = None
    try:
        os.makedirs(dossier, exist_ok=True)
        #Archivage avant l'ouverture : le fichier de la veille est encore fermé.
        archiver_journees_precedentes(dossier, jour_courant())
        purger_archives(dossier)

        handler_fichier = JournalQuotidienHandler(dossier)
        handler_fichier.setFormatter(logging.Formatter(FORMAT_FICHIER))
        logger.addHandler(handler_fichier)
        chemin = handler_fichier.baseFilename
    except OSError as erreur:
        #Dossier non inscriptible : on continue sans fichier plutôt que
        #d'empêcher le plugin de démarrer.
        if QgsMessageLog is not None and Qgis is not None:
            QgsMessageLog.logMessage(
                "Journalisation dans un fichier impossible ({}) : {}".format(
                    dossier, erreur),
                ETIQUETTE_QGIS, Qgis.Warning)

    if QgsMessageLog is not None:
        handler_qgis = HandlerMessageLogQgis()
        handler_qgis.setFormatter(logging.Formatter(FORMAT_QGIS))
        logger.addHandler(handler_qgis)

    version = version_extension()
    logger.info("Journalisation démarrée — StereoPhoto %s, niveau %s, fichier %s",
                version or "version inconnue", niveau, chemin or "aucun")

    return chemin


def avertir_utilisateur(message, niveau=logging.WARNING, duree_secondes=8):
    '''Journalise le message et l'affiche dans le bandeau de QGIS.

    À n'appeler que depuis le thread d'interface : le bandeau manipule des
    widgets. Un QThread qui veut avertir l'utilisateur émet un signal Qt vers son
    propriétaire, qui appelle cette fonction.
    '''

    logging.getLogger(NOM_JOURNAL_RACINE).log(niveau, message)

    try:
        from qgis.utils import iface
    except ImportError:
        return

    if iface is None or Qgis is None:
        return

    if niveau >= logging.ERROR:
        niveau_qgis = Qgis.Critical
    elif niveau >= logging.WARNING:
        niveau_qgis = Qgis.Warning
    else:
        niveau_qgis = Qgis.Info

    try:
        iface.messageBar().pushMessage(ETIQUETTE_QGIS, message, level=niveau_qgis,
                                       duration=duree_secondes)
    except Exception:
        #L'échec de l'affichage ne doit pas masquer le message : il est déjà
        #dans le fichier et dans le panneau Journal.
        pass
