# Prompt Figma : la D.A complète du côté démon

À coller dans l'IA de Figma. Si elle coupe la fin ou bâcle les écrans, l'envoyer en deux fois : d'abord jusqu'aux composants (fondations, composants), puis les écrans. Joindre des captures du HUD démon comme référence visuelle.

```
Tu es directeur artistique et UI designer de jeux vidéo. Crée dans Figma la direction artistique COMPLÈTE du camp DÉMON pour "Kimetsu RP", un jeu de rôle multijoueur PC (mode de jeu nanos world) qui se passe dans un Japon fantasmé, de nuit. Les pourfendeurs auront leur propre D.A plus tard (bleu glacier) : ici, on ne fait que le côté démon.

IDÉE DIRECTRICE
"Le prédateur de la nuit" : noir teinté de sang, lune rouge, laque sombre et ivoire, kanji gravés comme des sceaux, lueur rouge qui pulse lentement comme un battement de cœur. Ambiance : menaçante, élégante, jamais gore.

CONTRAINTE TECHNIQUE (importante)
Tout sera intégré en HTML/CSS dans le jeu : pas d'images bitmap lourdes. Utilise uniquement des dégradés, bordures, ombres lumineuses, formes vectorielles et icônes SVG. Format de référence : 1920x1080, 16:9.

PALETTE (crée-la en variables de couleur Figma)
- Nuit : #07040A, #12070B, #1B0A0F
- Sang (couleur d'accent) : #E0344B, sang profond #8A0F1C, sang vif #FF6A74
- Ivoire (texte) : #EFE3D0, ivoire atténué à 78 % d'opacité
- Chair : #F08A3A (orange) / #A24A14
- Âmes : #B06FE0 (violet) / #5A2A9A
- Or d'alerte : #F2C20F
- Lune : #E4CBA8 avec halo rouge
Pour les 6 raretés des pouvoirs : Commun gris pierre, Peu commun vert-de-gris, Rare bleu nuit, Épique violet, Légendaire or, Mythique rouge sang avec lueur.

TYPOGRAPHIE (crée les styles de texte)
- Titres et kanji : Shippori Mincho 700/800, espacement de lettres large.
- Interface et chiffres : Rajdhani 500/600/700.
- Échelle : 12 / 14 / 16 / 20 / 28 / 50 px.

FORMES ET MATIÈRE
Panneaux sombres à dégradé vertical, rayon 6 px, filet rouge de 1 px, ombre portée noire plus lueur rouge discrète. Portrait en losange, techniques en cercles, sceaux ronds portant un kanji. Fond : brume, voile de sang sur les bords de l'écran (vignette), montagnes et torii en silhouette, motif seigaiha en filigrane à 5 % d'opacité. Zones "gain à venir" en hachures diagonales.

ICONOGRAPHIE
Un jeu de 24 icônes en ligne de 2 px, 24x24 : goutte de sang, chair, âme (flamme), faim, soleil (danger), cadenas, griffe, lame, régénération, dévorer, palier, camp, boutique, sac, menu, fermer. Plus des sceaux-kanji : 鬼 (démon), 爪 (griffes), 刃 (lames), 癒 (régénération), 狂 (déchaînement), 血 (sang), 魂 (âme), 肉 (chair).

MOUVEMENT (notes pour les développeurs)
Durées 150 / 250 / 600 ms. Pulsation de lueur 2 s, survol : montée de 3 px, remplissage de jauge 400 ms, voile de sang qui monte en 600 ms pendant la dévoration.

COMPOSANTS (avec variantes d'état : normal, survol, appuyé, désactivé)
Bouton principal (sang), bouton secondaire (contour ivoire), jauge (sang / chair / âmes, avec zone fantôme hachurée), emplacement de technique (prête, en recharge, sang insuffisant, verrouillée avec "Palier 4", vide), badge de coût en sang, carte de camp (normale, survol, sélectionnée avec badge), panneau, infobulle, message (pastille ronde avec 鬼), barre de dévoration avec pastille de gain, anneau de rang, touche clavier, onglets, emplacement d'inventaire, champ texte, interrupteur.

ÉCRANS (frames 1920x1080)
1. Choix du camp (Pourfendeur / Démon, Démon sélectionné, bouton "Devenir Démon").
2. HUD en jeu : logo, quêtes + "Prochain palier", jauges du démon, bloc personnage (PV, grade, yens), 4 techniques, aide des touches.
3. Dévoration : barre "Dévorer : Villageois", temps restant, gain +40 chair / +4 âmes / +15 % PV / +15 XP, voile de sang renforcé.
4. Menu pause.
5. Inventaire (sac et équipement).
6. Créateur de personnage.
7. Changer de voie : cartes de pouvoirs sanguinaires avec les 6 raretés.
8. Tirage d'un pouvoir sanguinaire, avec taux affichés et compteur de pitié.
9. Montée de palier, plein écran, 5 paliers : Errant affamé, Chasseur de nuit, Prédateur, Seigneur de sang, Lune de sang.
10. Alerte soleil : bords de l'écran qui brûlent, compte à rebours.
11. K.O. : "Réapparition au Domaine…".
12. Écran de chargement.

TEXTES (en français, utilise-les tels quels)
"Choisis ton camp", "Ce choix est définitif pour ce personnage : tu pourras changer de voie, jamais de camp.", "Devenir Démon", "Affamé : dévore une proie pour te régénérer", "Repas interrompu : tu as été frappé", "Technique verrouillée", "Pas assez de sang", "Prochain palier", "Sang", "Chair", "Âmes".

ORGANISATION DU FICHIER
Pages : Cover, Foundations (couleurs, typo, icônes, effets), Components, HUD, Menus, Moodboard. Auto layout partout, composants avec variantes, calques nommés en anglais, grille 12 colonnes avec marge de 80 px et zone de sécurité de 48 px.

RÈGLES
Contraste AA minimum, pas d'emoji, pas de gore explicite. ORIGINALITÉ : aucun personnage, logo, illustration ou texte existant d'un manga, d'un anime ou d'un jeu. Si une silhouette est nécessaire, invente un démon original (cornes, griffes), sans reprendre un personnage connu.
```
