#Fichier utiliser par QGIS pour lancer l'application
def classFactory(iface):
    from .stereoPhoto import stereoPhoto
    return stereoPhoto(iface)
