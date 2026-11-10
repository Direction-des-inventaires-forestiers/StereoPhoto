# Explication du dossier Navigation Sans Géoréférencement

Pour permettre la visualisation en stéréoscopie d'images sans orientation intérieur et extérieur, une application est disponible dans ce dossier. Elle permet de choisir une paire d'images et de les afficher sur les écrans du stéréorestétuteur. Avec la souris et le clavier, il devient possible de déplacer et tourner les images afin de les alligner en superposition sur les écrans. 

**Application en déveleppement**

## Utilisation

```
python main_application.py --image-bas <chemin_image_bas> --image-haut <chemin_image_haut> [--ecran-bas <num>] [--ecran-haut <num>] [--mirroir]
```

- `--image-bas` / `--image-haut` : chemins des images à afficher sur chaque écran (obligatoires).
- `--ecran-bas` / `--ecran-haut` : numéros des écrans du stéréorestituteur (défaut : 1 et 2).
- `--mirroir` : active l'effet miroir sur l'écran du haut. 