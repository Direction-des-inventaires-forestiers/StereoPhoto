

#def openFile(pathPAR, pathDEM):
    #Ouvre le fichier PAR
    #Détecter le type de MTM (#) et établir sa taille
    #récolte les coordonnées du centre de la photo et autres si nécessaire
    #identifié quelques pixels (4 coins, centre, autres points de l'image) pour la positionné
    #positionné la photo à la bonne place sur le plan

#Retourne la différence de pixel entre les images
def distance(picture):
    if picture == "tif" :
        return 4489
    else :
        return 0  

#Retourner la coordonnée du coin supérieur gauche 
def coord(picture) :
    if picture == "439": 
        return (4489,0)
    elif picture == "440":
        return (0,0)
    else :
        return (0,0)