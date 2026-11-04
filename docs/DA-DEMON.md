# Direction artistique : le côté démon

**L'idée directrice** : le prédateur de la nuit. Noir teinté de sang, lune rouge, laque sombre et ivoire, kanji gravés comme des sceaux, une lueur rouge qui pulse lentement comme un battement de cœur. Menaçant et élégant, jamais gore.

Le côté pourfendeur aura sa propre direction (bleu glacier) plus tard : ce document ne traite que du démon. Le thème est déjà appliqué dans le HUD (`packages/wakfu-rp/Client/UI/style.css`, classe `html.demon`).

## Couleurs

| Rôle | Valeur |
|---|---|
| Nuit | `#07040A`, `#12070B`, `#1B0A0F` |
| Sang (accent) | `#E0344B`, profond `#8A0F1C`, vif `#FF6A74` |
| Texte | ivoire `#EFE3D0`, atténué à 78 % |
| Chair | `#F08A3A` et `#A24A14` |
| Âmes | `#B06FE0` et `#5A2A9A` |
| Alerte | or `#F2C20F` |
| Lune | `#E4CBA8`, halo rouge |

Le côté pourfendeur reste en bleu : `#2F8FD0`. Les six raretés des pouvoirs (décision 8) : commun gris pierre, peu commun vert-de-gris, rare bleu nuit, épique violet, légendaire or, mythique rouge sang avec lueur.

## Typographie

Titres et kanji : **Shippori Mincho** 700 à 800, grand espacement. Interface et chiffres : **Rajdhani** 500 à 700. Échelle : 12, 14, 16, 20, 28, 50 px. Les polices ne sont pas livrées avec le jeu : repli sur Yu Mincho, MS Mincho puis Georgia.

## Formes et matière

Panneaux sombres à dégradé vertical, rayon de 6 px, filet rouge de 1 px, ombre noire et lueur rouge discrète. Portrait en losange, techniques en cercles, sceaux ronds portant un kanji. Fond de brume et de montagnes en silhouette, voile de sang sur les bords de l'écran (plus fort pendant la dévoration). Le gain à venir s'affiche en hachures diagonales sur les jauges.

Les kanji servent d'icônes : 鬼 (démon), 爪 (griffes), 刃 (lames), 癒 (régénération), 狂 (déchaînement).

## Composants du HUD démon

Jauges de sang, de chair et d'âmes avec aperçu du gain ; nom et numéro du palier ; « Repas du jour » ; bloc « Prochain palier » sous les quêtes ; techniques en cercles avec coût en sang, voile de recharge, cadenas et mention « Palier N » ; barre de dévoration avec temps restant et pastille de gain ; messages avec sceau 鬼.

L'écran de choix du camp, la dévoration et le HUD complet ont été maquettés puis portés dans le jeu. Tout doit rester réalisable en HTML et CSS (dégradés, bordures, ombres, SVG), sans image lourde.

## Pour produire la suite dans Figma

Le prompt complet, à coller dans l'IA de Figma, est dans [design/FIGMA-PROMPT.md](design/FIGMA-PROMPT.md). Il demande la palette en variables, les styles de texte, 24 icônes, les composants avec états et 12 écrans en 1920 x 1080 (choix du camp, HUD, dévoration, menu pause, inventaire, créateur, changement de voie, tirage avec pitié, montée de palier, alerte soleil, K.O., chargement).

**Originalité** : aucun personnage, logo ou illustration existant ne doit être repris. Les silhouettes de démons sont à inventer.
