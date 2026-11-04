"use strict";

// Visualiseur d'animations (page du panneau). Lua envoie les packs (anim:init) et l'ouverture (anim:open) ;
// la page renvoie anim:play, anim:stop, anim:mark et anim:close. Voir Client/AnimViewer.lua.

// Hors du jeu (aperçu dans un navigateur, tests), `Events` n'existe pas : on le remplace par un journal.
const bus = typeof Events !== "undefined" ? Events : { Subscribe() {}, Call: (...args) => console.log("Events.Call", ...args) };

const NO_PACK = { name: "", names: { A: [], AM: [] }, drop: "" };

const state = {
	packs: [], // { name, names: { A: séquences, AM: montages }, drop } de chaque pack
	pack: 0, // index du pack affiché
	key: "F7", // touche d'ouverture (Config.AnimViewer.key), qui ferme aussi le panneau
	kind: "A", // A = séquences, AM = montages
	chip: "", // catégorie = premier mot du nom ; "" = toutes
	query: "",
	selected: null, // nom sans pack
	playing: null, // id complet (pack::Nom) de l'animation lancée
	visible: [], // noms affichés après filtre
	marks: {}, // id complet -> "keep" | "bug"
};

const MARKS_KEY = "wakfu-anim-marks";

// --- logique pure (testée avec node) -----------------------------------------------------------------------------

// A_Combo_Attack_01 -> Combo_Attack_01 ; avec drop = "Scythe", A_Scythe_Combo_01 -> Combo_01
function shortName(name, drop) {
	const short = name.replace(/^AM?_/, "");
	return drop && short.startsWith(drop + "_") ? short.slice(drop.length + 1) : short;
}

// Combo_Attack_01 -> Combo
function categoryOf(name, drop) {
	return shortName(name, drop).split("_")[0];
}

// Mot que tous les noms d'un pack ont en tête (A_Scythe_Dodge_F_0 ... -> "Scythe"), pour qu'il ne forme pas à lui seul
// l'unique catégorie. "" s'il n'y en a pas ou qu'il y a moins de deux noms.
function commonWord(names) {
	if (names.length < 2) return "";
	const first = shortName(names[0]).split("_")[0];
	return names.every((name) => shortName(name).startsWith(first + "_")) ? first : "";
}

function filterNames(names, query, chip, drop) {
	const words = query.toLowerCase().split(/\s+/).filter(Boolean);
	return names.filter((name) => {
		const text = shortName(name, drop).toLowerCase();
		return (!chip || categoryOf(name, drop) === chip) && words.every((word) => text.includes(word));
	});
}

// [[catégorie, nombre]] des catégories les plus fournies d'abord.
function categories(names, drop) {
	const counts = {};
	for (const name of names) counts[categoryOf(name, drop)] = (counts[categoryOf(name, drop)] || 0) + 1;
	return Object.entries(counts).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
}

function pickedText(marks) {
	const ids = (mark) => Object.keys(marks).filter((id) => marks[id] === mark).sort();
	const keep = ids("keep");
	const bug = ids("bug");
	if (!keep.length && !bug.length) return "(rien pour l'instant : S retient, B signale un bug)";
	return ["RETENUES", ...keep, "", "BUGGÉES", ...bug].join("\n");
}

function isAssetId(text) {
	return /^[\w-]+::\w+$/.test(text);
}

// --- page ---------------------------------------------------------------------------------------------------------

const $ = (id) => document.getElementById(id);

function parse(payload) {
	return typeof payload === "string" ? JSON.parse(payload) : payload;
}

// Les tables Lua vides deviennent {} au lieu de [] : on accepte les deux.
function list(value) {
	if (!value) return [];
	return Array.isArray(value) ? value : Object.values(value);
}

function current() {
	return state.packs[state.pack] || NO_PACK;
}

function fullId(name) {
	return current().name + "::" + name;
}

function loadMarks() {
	try {
		state.marks = JSON.parse(localStorage.getItem(MARKS_KEY) || "{}");
	} catch (error) {
		state.marks = {};
	}
}

function saveMarks() {
	try {
		localStorage.setItem(MARKS_KEY, JSON.stringify(state.marks));
	} catch (error) {
		// pas de stockage dans cette page : les choix restent dans le journal du serveur
	}
}

function play(id) {
	state.playing = id;
	bus.Call("anim:play", id, $("slot").value, $("loop").checked, Number($("rate").value));
	$("now").textContent = "En cours : " + id;
}

function playName(name) {
	state.selected = name;
	play(fullId(name));
	renderList();
}

function toggleMark(name, mark) {
	const id = fullId(name);
	const next = state.marks[id] === mark ? "clear" : mark;
	if (next === "clear") delete state.marks[id];
	else state.marks[id] = mark;
	saveMarks();
	bus.Call("anim:mark", id, next);
	renderList();
	renderPicked();
}

function renderPicked() {
	$("picked").value = pickedText(state.marks);
}

// Un onglet par pack ; masqués quand il n'y en a qu'un.
function renderPacks() {
	const packs = $("packs");
	packs.textContent = "";
	packs.hidden = state.packs.length < 2;
	state.packs.forEach((pack, index) => {
		const button = document.createElement("button");
		button.textContent = pack.name + " " + (pack.names.A.length + pack.names.AM.length);
		button.dataset.pack = index;
		if (index === state.pack) button.classList.add("on");
		packs.appendChild(button);
	});
}

function renderChips() {
	const chips = $("chips");
	chips.textContent = "";
	const make = (label, value) => {
		const button = document.createElement("button");
		button.textContent = label;
		button.dataset.chip = value;
		if (state.chip === value) button.classList.add("on");
		chips.appendChild(button);
	};
	make("Toutes", "");
	for (const [category, count] of categories(current().names[state.kind], current().drop)) make(category + " " + count, category);
}

function renderList() {
	const names = current().names[state.kind];
	const drop = current().drop;
	state.visible = filterNames(names, state.query, state.chip, drop);
	const ul = $("list");
	ul.textContent = "";
	for (const name of state.visible) {
		const id = fullId(name);
		const li = document.createElement("li");
		li.dataset.name = name;
		if (name === state.selected) li.classList.add("selected");
		if (id === state.playing) li.classList.add("playing");

		const label = document.createElement("span");
		label.className = "name";
		label.textContent = shortName(name, drop);
		li.appendChild(label);

		for (const [mark, symbol, title] of [["keep", "★", "Retenir (S)"], ["bug", "⚠", "Signaler un bug (B)"]]) {
			const button = document.createElement("button");
			button.className = "mark " + mark + (state.marks[id] === mark ? " active" : "");
			button.dataset.mark = mark;
			button.textContent = symbol;
			button.title = title;
			li.appendChild(button);
		}
		ul.appendChild(li);
	}
	$("count").textContent = state.visible.length + " / " + names.length + " animations";
}

function scrollToSelected() {
	for (const li of $("list").children) {
		if (li.dataset.name === state.selected) li.scrollIntoView({ block: "nearest" });
	}
}

// Flèches : on choisit et on joue tout de suite, pour parcourir la liste d'un coup d'œil.
function moveSelection(step) {
	if (!state.visible.length) return;
	const index = state.visible.indexOf(state.selected);
	const next = Math.min(state.visible.length - 1, Math.max(0, index < 0 ? 0 : index + step));
	playName(state.visible[next]);
	scrollToSelected();
}

function selectPack(index) {
	state.pack = index;
	state.chip = "";
	state.selected = null;
	$("pack").textContent = current().name;
	renderPacks();
	renderChips();
	renderList();
}

function init(payload) {
	const data = parse(payload);
	state.key = data.key || state.key;
	state.packs = list(data.packs).map((pack) => {
		const names = { A: list(pack.sequences), AM: list(pack.montages) };
		return { name: pack.name, names, drop: commonWord([...names.A, ...names.AM]) };
	});
	loadMarks();
	selectPack(0);
	renderPicked();
}

function setOpen(open) {
	$("viewer").classList.toggle("hidden", !open);
}

document.addEventListener("DOMContentLoaded", () => {
	$("close").addEventListener("click", () => bus.Call("anim:close"));
	$("stop").addEventListener("click", () => {
		if (state.playing) bus.Call("anim:stop", state.playing);
		$("now").textContent = "Rien ne joue";
	});
	$("rate").addEventListener("input", () => {
		$("rate-out").textContent = Number($("rate").value).toFixed(2) + "×";
	});
	$("search").addEventListener("input", () => {
		state.query = $("search").value;
		renderList();
	});
	$("packs").addEventListener("click", (event) => {
		const button = event.target.closest("button");
		if (button) selectPack(Number(button.dataset.pack));
	});
	$("kinds").addEventListener("click", (event) => {
		const button = event.target.closest("button");
		if (!button) return;
		state.kind = button.dataset.kind;
		state.chip = "";
		for (const other of $("kinds").children) other.classList.toggle("on", other === button);
		renderChips();
		renderList();
	});
	$("chips").addEventListener("click", (event) => {
		const button = event.target.closest("button");
		if (!button) return;
		state.chip = button.dataset.chip;
		renderChips();
		renderList();
	});
	$("list").addEventListener("click", (event) => {
		const li = event.target.closest("li");
		if (!li) return;
		const mark = event.target.closest(".mark");
		if (mark) toggleMark(li.dataset.name, mark.dataset.mark);
		else playName(li.dataset.name);
	});
	$("free-play").addEventListener("click", () => {
		const id = $("free").value.trim();
		if (!isAssetId(id)) return ($("now").textContent = "Chemin invalide : attendu pack::NomAnimation");
		play(id);
		renderList();
	});

	document.addEventListener("keydown", (event) => {
		if (event.key === "Escape" || event.key === state.key) return bus.Call("anim:close");
		const typing = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement && document.activeElement.tagName);
		if (event.key === "ArrowDown" || event.key === "ArrowUp") {
			event.preventDefault();
			return moveSelection(event.key === "ArrowDown" ? 1 : -1);
		}
		if (event.key === "Enter" && state.selected && document.activeElement !== $("free")) return playName(state.selected);
		if (typing || !state.selected) return;
		if (event.key === "s" || event.key === "S") toggleMark(state.selected, "keep");
		else if (event.key === "b" || event.key === "B") toggleMark(state.selected, "bug");
	});
});

bus.Subscribe("anim:init", init);
bus.Subscribe("anim:open", (open) => setOpen(open === true || open === "true"));

// Pour les tests node et l'aperçu dans un navigateur.
if (typeof module !== "undefined") module.exports = { shortName, categoryOf, commonWord, filterNames, categories, pickedText, isAssetId };
if (typeof window !== "undefined") window.animViewer = { init, setOpen, state };
