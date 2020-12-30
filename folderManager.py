

#path = folder to image par année
#TODO
#possibiliter par chiffre de trouver les voisins left right
#pour up, down il est nécessaire de trier parmis les fichiers PAR
#déterminer quoi faire si à la limite dans une direction

#Trouver une paire initial ainsi que la position gauche droite (same Y close X) , taller X to left

#Temps pour une recherche 

#fonction pour trouver les voisins d'une image 
    #même ligne de vol pour gauche droite leur y va être similaire
    #pour up down, trouver un x similaire avec un y non similaire -> moyenne distance entre les X et les Y 

import os 

def getDict() :
    path = 'U:/Photos'

    listpath = os.listdir(path)
    parDict = {}
    for i in listpath : 
        if i.split('.')[-1] == 'par' : 
            fullpath = os.path.join(path,i)
            try :
                f = open(fullpath)
                s = f.read()
            except : 
                f = open(fullpath, encoding='ANSI')
                s = f.read() 

            v1 = s.find('XYZ00')
            v2 = s.find("\n", v1)
            w = s[v1:v2].split(' ')
            coord = []
            coord.append(float(w[-3]))
            coord.append(float(w[-2]))
            parDict[fullpath] = coord

    return parDict

a = getDict()
b= iter(a)
c = next(b)
d = next(b)
breakP = 0
#for key, value in a.items() :
#    print(value)

#make pair

#up = y up x same
#down = y down x same




