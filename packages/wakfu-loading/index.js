// Écran de chargement : le moteur envoie UpdateScreen toutes les quelques ms.
const $ = (id) => document.getElementById(id);

// Étapes : 0 = rien, 1 = connexion, 2 = récupération, 3 = vérification, 4 = téléchargement,
// 5 = ressources, 6 = niveau, 7 = entités, 8 = shaders, 9 = fin.
const STAGES = {
	1: "CONNEXION À",
	2: "RÉCUPÉRATION DE",
	3: "VÉRIFICATION DE",
	4: "TÉLÉCHARGEMENT DE",
	5: "CHARGEMENT DE",
	6: "CHARGEMENT DE",
	7: "CHARGEMENT DE",
	8: "PRÉPARATION DE",
	9: "PRÊT À EXPLORER",
};

Events.Subscribe("UpdateScreen", function (message, messageSecondary, progressSmall, progressSmallTotal, progress, progressTotal, currentStage) {
	const ratio = progressTotal > 0 ? Math.max(0, Math.min(1, progress / progressTotal)) : 0;
	$("fill").style.width = Math.round(ratio * 100) + "%";
	$("percent").textContent = Math.round(ratio * 100) + "%";
	$("status").textContent = STAGES[currentStage] || "CONNEXION À";
	$("file").textContent = messageSecondary || "";
});
