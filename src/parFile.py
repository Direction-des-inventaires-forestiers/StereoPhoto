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
    except UnicodeDecodeError:
        # Les fichiers PAR de la DIF sont produits sous Windows en français et
        # encodés en Windows-1252. Le repli est déclaré explicitement plutôt
        # qu'en 'ansi' : 'ansi' suit la page de codes du poste, qui vaut UTF-8
        # (65001) là où l'option « Utiliser UTF-8 pour la prise en charge
        # linguistique mondiale » est activée, auquel cas le repli échoue comme
        # la première tentative. Les octets non ASCII n'apparaissent que dans
        # les champs descriptifs ($FCAM00, $DESCR), jamais lus par le plugin :
        # errors='replace' garantit la lecture des paramètres de caméra même
        # si un octet n'est pas défini dans Windows-1252.
        with open(path, encoding='cp1252', errors='replace') as f:
            lines = f.read().splitlines()

    values = {}
    for line in lines:
        for key in keywords:
            if line.startswith(key):
                values[key] = line.split()
                break

    return values
