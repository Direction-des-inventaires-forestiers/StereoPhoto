# -*- coding: utf-8 -*-
"""Lanceur du banc de tests du dépôt (registre A7, tâche 3A.6).

Le banc est fait de scripts autonomes : chaque fichier `tests/test_*.py`
extrait par analyse syntaxique la fonction visée de son module, l'exécute avec
des bouchons, imprime une ligne par contrôle et sort avec un code non nul dès
qu'un contrôle échoue. Rien n'enchaînait ces scripts : ils s'exécutaient un à
un, à la main, ce qui laissait le banc hors de portée d'une vérification
automatique. Ce lanceur les enchaîne, agrège les codes de sortie et compte les
contrôles, de sorte que le banc puisse être vérifié à chaque demande de tirage
(`.github/workflows/tests.yml`).

Le lanceur n'a aucune dépendance. Le banc lui-même n'exige ni QGIS ni Qt ; seul
`tests/test_altitude_mnt.py` demande numpy, la lecture d'altitude étant
éprouvée sur un vrai tableau.

Le nombre de contrôles est mesuré et non tenu à la main : il se lit sur les
lignes « OK » et « ECHEC » que chaque script imprime. Un décompte recopié dans
une issue ou dans un rapport se périme dès le test suivant ; celui-ci suit le
banc.

Usage :
    python tests/executer_tous.py                  tout le banc
    python tests/executer_tous.py zone_sure mnt    un ou plusieurs fichiers
    python tests/executer_tous.py --detail         avec la sortie de chaque test

Sortie 0 si tous les contrôles passent, 1 sinon. La sortie d'un fichier en
échec est toujours reprise, que `--detail` soit donné ou non.
"""

import os
import re
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "tests")

# Ligne de contrôle imprimée par les scripts du banc : « OK » ou « ECHEC »,
# puis le libellé. La forme est commune aux douze fichiers.
LIGNE_CONTROLE = re.compile(r"^(OK|ECHEC)\s")

FANIONS = ("--detail",)


def fichiers_du_banc(filtres):
    """Retourne les scripts de test à exécuter, en ordre alphabétique."""
    noms = sorted(
        nom
        for nom in os.listdir(DOSSIER)
        if nom.startswith("test_") and nom.endswith(".py")
    )
    if not filtres:
        return noms
    inconnus = [f for f in filtres if not any(f in nom for nom in noms)]
    if inconnus:
        raise SystemExit("aucun test ne correspond à : %s" % ", ".join(inconnus))
    return [nom for nom in noms if any(f in nom for f in filtres)]


def executer_un(nom):
    """Exécute un script du banc et rend son code, sa sortie et ses comptes."""
    # Les libellés sont accentués. Sans PYTHONIOENCODING, le processus enfant
    # suit la page de codes de la console sous Windows : la sortie revient
    # illisible, ou l'enfant lève à l'écriture. Même dépendance à la page de
    # codes que le défaut P1-H, et même traitement.
    environnement = dict(os.environ, PYTHONIOENCODING="utf-8")
    depart = time.monotonic()
    resultat = subprocess.run(
        [sys.executable, os.path.join(DOSSIER, nom)],
        cwd=RACINE,
        env=environnement,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
    )
    delai = (time.monotonic() - depart) * 1000.0
    lignes = resultat.stdout.splitlines()
    controles = [ligne for ligne in lignes if LIGNE_CONTROLE.match(ligne)]
    echoues = [ligne for ligne in controles if ligne.startswith("ECHEC")]
    return resultat.returncode, resultat.stdout, len(controles), len(echoues), delai


def reprendre(sortie):
    """Décale la sortie d'un script pour la distinguer du résumé du lanceur."""
    lignes = [ligne for ligne in sortie.splitlines() if ligne.strip()]
    return "\n".join("     | %s" % ligne for ligne in lignes)


def executer(filtres, detail):
    """Enchaîne les scripts retenus et rend le code de sortie du lanceur."""
    noms = fichiers_du_banc(filtres)
    print(
        "Banc de tests : %d fichier(s), interpréteur %s\n"
        % (len(noms), sys.version.split()[0])
    )

    total_controles = 0
    total_echoues = 0
    en_echec = []
    for nom in noms:
        code, sortie, controles, echoues, delai = executer_un(nom)
        total_controles += controles
        total_echoues += echoues
        if code != 0:
            en_echec.append(nom)
        print(
            "%-6s %-34s %3d contrôle(s) %6.0f ms"
            % ("OK" if code == 0 else "ECHEC", nom, controles, delai)
        )
        if detail or code != 0:
            reprise = reprendre(sortie)
            if reprise:
                print(reprise)

    print()
    if en_echec:
        print(
            "%d fichier(s) en échec sur %d : %s"
            % (len(en_echec), len(noms), ", ".join(en_echec))
        )
        print("%d contrôle(s) en échec sur %d." % (total_echoues, total_controles))
        return 1
    print("%d fichier(s), %d contrôle(s), aucun échec." % (len(noms), total_controles))
    return 0


if __name__ == "__main__":
    arguments = sys.argv[1:]
    egares = [a for a in arguments if a.startswith("-") and a not in FANIONS]
    if egares:
        raise SystemExit(
            "option inconnue : %s (attendu : %s)"
            % (", ".join(egares), ", ".join(FANIONS))
        )
    sys.exit(
        executer(
            [a for a in arguments if not a.startswith("-")],
            "--detail" in arguments,
        )
    )
