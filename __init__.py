#Fichier utiliser par QGIS pour lancer l'application
def classFactory(iface):
    from .stereoPhotoCleaner import stereoPhoto
    return stereoPhoto(iface)
