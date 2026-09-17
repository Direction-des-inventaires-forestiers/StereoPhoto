'''
Lecture des fichiers PAR

Un fichier PAR accompagne chaque photo et décrit la caméra qui l'a prise :
transformation affine, focale, position, orientation, taille du pixel. Ce
module contient l'unique lecture de ce format; les modules appelants
interprètent ensuite les champs dont ils ont besoin.
'''

# Champs PAR lus par le plugin. La valeur décrit le champ, seules les clés sont
# utilisées à la lecture. Tous les modules lisent le même ensemble, chacun
# n'interprétant ensuite que les champs qui le concernent : $PPA ne sert qu'à
# worldManager.pictureManager (point principal d'autocollimation).
PAR_KEYWORDS = {
    "$PARAFFINE00": "affine",
    "$PARINVAFF00": "inverse_affine",
    "$FOC00": "focal",
    "$XYZ00": "camera position",
    "$OPK00": "orientation",
    "$PIXELSIZE": "pixel_size",
    "$FSCALE00": "fscale",
    "$PPA": "principal point of autocollimation",
}

# Champs sans lesquels un fichier PAR est inexploitable
PAR_REQUIRED_KEYWORDS = ("$PARAFFINE00", "$PARINVAFF00", "$FOC00", "$XYZ00", "$OPK00")


def parse_par_file(path, keywords=None):
    '''Lit un fichier PAR et retourne ses champs sous la forme
    {clé: jetons de la ligne}, le premier jeton étant la clé elle-même.

    Les champs absents du fichier sont absents du dictionnaire : c'est à
    l'appelant de vérifier leur présence (voir PAR_REQUIRED_KEYWORDS).
    Seule la première occurrence d'un champ est retenue.
    '''

    if keywords is None:
        keywords = PAR_KEYWORDS

    try:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
    except:
        with open(path, encoding='ansi') as f:
            lines = f.read().splitlines()

    values = {}
    for line in lines:
        for key in keywords:
            if line.startswith(key):
                values[key] = line.split()
                break

    return values
