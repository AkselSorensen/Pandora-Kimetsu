// Écran de chargement : le moteur envoie UpdateScreen toutes les quelques ms.
const $ = (id) => document.getElementById(id);

// À régler : les pastilles de la planche. Laisser vide pour les masquer (le client ne connaît pas le nombre de joueurs en ligne).
const DISCORD = ""; // par exemple "discord.gg/ton-lien"
const PLAYERS = ""; // par exemple "128/128 joueurs connectés"

if (DISCORD) { $("discord-text").textContent = DISCORD; $("discord").hidden = false; }
if (PLAYERS) { $("players-text").textContent = PLAYERS; $("players").hidden = false; }

// Étapes : 0 = rien, 1 = connexion, 2 = récupération, 3 = vérification, 4 = téléchargement,
// 5 = ressources, 6 = niveau, 7 = entités, 8 = shaders, 9 = fin.
const STAGES = {
	1: "Connexion au serveur...",
	2: "Récupération des informations...",
	3: "Vérification des fichiers...",
	4: "Téléchargement en cours...",
	5: "Chargement des ressources...",
	6: "Chargement du monde...",
	7: "Chargement des personnages...",
	8: "Préparation des effets...",
	9: "Prêt à explorer",
};

function update(ratio, stage, file) {
	const pct = Math.round(Math.max(0, Math.min(1, ratio)) * 100);
	$("fill").style.width = pct + "%";
	$("percent").textContent = pct + "%";
	$("status").textContent = STAGES[stage] || "Chargement en cours...";
	$("file").textContent = file || "";
}

if (typeof Events !== "undefined") {
	Events.Subscribe("UpdateScreen", function (message, messageSecondary, progressSmall, progressSmallTotal, progress, progressTotal, currentStage) {
		update(progressTotal > 0 ? progress / progressTotal : 0, currentStage, messageSecondary);
	});
} else {
	// Aperçu dans un navigateur : ?p=78 pour fixer le pourcentage
	const p = Number(new URLSearchParams(location.search).get("p") || 78);
	update(p / 100, 0, "");
}
