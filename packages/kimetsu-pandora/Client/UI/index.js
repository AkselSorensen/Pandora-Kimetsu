// HUD Kimetsu RP. Les données arrivent de Client/Index.lua par Events, en JSON.

const DEFAULT_COLOR = "#e0602a";
const SPELL_KEYS = ["1", "2"];
const HP_WIDTH = 301; // largeur de hp-red.png, en px
const EN_WIDTH = 286; // largeur de hp-blue.png, en px
const TOAST_MS = 4000;
const DIALOG_MS = 12000;

const hud = {
	classes: {},
	quests: {},
	state: null,
	cooldownEnds: {}, // spellId -> fin du cooldown (ms, horloge du HUD)
	lastCast: null, // dernier sort lancé : { start, total } en ms
	dialogTimer: null,
};

const $ = (id) => document.getElementById(id);

// Couleur et ordre des classes : ils viennent de Classes.lua (champ color, Classes.RerollOrder).
function classColor(name) {
	const def = hud.classes[name];
	return (def && def.color) || DEFAULT_COLOR;
}

function classOrder() {
	const order = hud.rerollOrder && hud.rerollOrder.length ? hud.rerollOrder : Object.keys(hud.classes);
	// Le camp est un choix définitif : on ne propose que les voies du camp du joueur (toutes tant qu'il n'a pas choisi).
	const camp = hud.state && hud.state.camp;
	return order.filter((name) => hud.classes[name] && (!camp || hud.classes[name].camp === camp));
}

function parse(payload) {
	return typeof payload === "string" ? JSON.parse(payload) : payload;
}

// Les tables Lua vides deviennent {} au lieu de [] : on accepte les deux.
function list(value) {
	if (!value) return [];
	return Array.isArray(value) ? value : Object.values(value);
}

function escapeHtml(text) {
	const div = document.createElement("div");
	div.textContent = text;
	return div.innerHTML;
}

function renderClass() {
	const className = hud.state ? hud.state.class : "";
	const def = hud.classes[className];
	document.documentElement.style.setProperty("--accent", classColor(className));
	$("class-name").textContent = def ? def.name : className;
	renderRank();
	renderSpells();
}

// Grade : numéro dans l'anneau du portrait, nom à côté de la classe, XP vers le grade suivant dans l'infobulle.
const RING_LENGTH = 2 * Math.PI * 16.5;

function renderRank() {
	const rank = hud.state && hud.state.rank;
	const xp = (hud.state && hud.state.xp) || 0;
	$("rank-name").textContent = rank ? " · " + rank.name : "";
	$("level-value").textContent = rank ? rank.index : 1;
	const progress = rank && rank.nextXp ? Math.max(0, Math.min(1, (xp - rank.xp) / (rank.nextXp - rank.xp))) : 1;
	document.querySelector("#level .arc").setAttribute("stroke-dasharray", `${(RING_LENGTH * progress).toFixed(1)} ${RING_LENGTH.toFixed(1)}`);
	$("level").title = rank ? (rank.nextXp ? `${rank.name} : ${xp} / ${rank.nextXp} XP` : `${rank.name} : grade maximal`) : "";
}

const SPELL_ICONS = ["img/spell-swirl.png", "img/spell-burst.png"];
const SLOT_COUNT = 6;

function renderSpells() {
	const bar = $("spellbar");
	const className = hud.state ? hud.state.class : null;
	const classDef = hud.classes[className];
	const spells = classDef ? list(classDef.spells) : [];
	bar.innerHTML = "";

	for (let i = 0; i < SLOT_COUNT; i++) {
		const spell = spells[i];
		const slot = document.createElement("div");
		slot.className = "spell" + (spell ? "" : " empty");
		const key = `<span class="spell-key">${i + 1}</span>`;
		if (spell) {
			slot.id = "spell-" + spell.id;
			slot.dataset.name = spell.name;
			slot.dataset.cooldown = spell.cooldown;
			// Un démon voit le kanji de sa technique à la place de l'icône ; le badge (délai, ou coût en sang) et le verrou sont réglés par applySpellCosts.
			const icon =
				hud.state && hud.state.camp === "demon" && spell.glyph
					? `<span class="spell-glyph">${escapeHtml(spell.glyph)}</span>`
					: `<img class="spell-icon" src="${SPELL_ICONS[i % SPELL_ICONS.length]}" alt="">`;
			slot.innerHTML =
				key +
				icon +
				`<div class="spell-cooldown hidden"></div>` +
				`<div class="spell-padlock hidden">${LOCK}</div>` +
				`<div class="spell-badge">${spell.cooldown}</div>` +
				`<div class="spell-lock-label hidden"></div>` +
				`<div class="spell-tip">${escapeHtml(spell.name)}</div>`;
		} else {
			slot.innerHTML = key;
		}
		bar.appendChild(slot);
	}
	applySpellCosts();
}

function renderStats() {
	const stats = (hud.state && hud.state.stats) || {};
	const parts = [];
	const fmt = (value, suffix) => {
		const cls = value > 0 ? "up" : value < 0 ? "down" : "";
		const sign = value > 0 ? "+" : "";
		return `<span class="${cls}">${sign}${value}${suffix}</span>`;
	};
	if (stats.maxHp) parts.push("PV " + fmt(stats.maxHp, ""));
	if (stats.damagePct) parts.push("Dmg " + fmt(stats.damagePct, "%"));
	if (stats.speed) parts.push("Vit " + fmt(stats.speed, "%"));
	$("stats").innerHTML = parts.join(" · ");
}

function renderQuests() {
	const container = $("quest-list");
	const playerQuests = (hud.state && hud.state.quests) || {};
	const ids = Object.keys(playerQuests);
	if (ids.length === 0) {
		container.innerHTML = `<div class="empty">Parle au Kakushi (E)</div>`;
		return;
	}

	// Actives d'abord, terminées ensuite.
	ids.sort((a, b) => (playerQuests[a].status === "done") - (playerQuests[b].status === "done"));
	container.innerHTML = ids
		.map((id) => {
			const def = hud.quests[id] || { name: id, description: "", objective: { count: 1 } };
			const progress = playerQuests[id];
			const count = def.objective.count;
			const done = progress.status === "done";
			const value = done ? count : Math.min(progress.progress, count);
			return (
				`<div class="quest${done ? " done" : ""}">` +
				`<div class="quest-name">${escapeHtml(def.name)}</div>` +
				`<div class="quest-desc">${escapeHtml(def.description)} (${value}/${count})</div>` +
				`<div class="quest-progress"><div style="width:${(100 * value) / count}%"></div></div>` +
				`</div>`
			);
		})
		.join("");
}

function renderState() {
	hud.demon = (hud.state && hud.state.demon) || null;
	applyTheme(); // avant les techniques : leur icône dépend du camp
	renderClass();
	renderDemon();
	$("player-name").textContent = (hud.state && hud.state.name) || "";
	$("kamas-value").textContent = hud.state ? hud.state.kamas : 0;
	renderStats();
	renderQuests();
}

function toast(text) {
	const el = document.createElement("div");
	el.className = "toast";
	el.textContent = text;
	$("toasts").appendChild(el);
	setTimeout(() => el.classList.add("out"), TOAST_MS);
	setTimeout(() => el.remove(), TOAST_MS + 500);
}

function showDialog(dialog) {
	$("dialog-name").textContent = dialog.name;
	$("dialog-text").textContent = dialog.text;

	const actions = [];
	const offered = list(dialog.offered);
	if (offered.length > 0) {
		const quest = hud.quests[offered[0]];
		actions.push(`<span class="action">F5 · Accepter « ${escapeHtml(quest ? quest.name : offered[0])} »</span>`);
	}
	if (list(dialog.services).includes("reroll")) {
		actions.push(`<span class="action">F6 · Entraînement : nouveaux bonus (50 yens)</span>`);
	}
	$("dialog-actions").innerHTML = actions.join("");
	$("dialog").classList.remove("hidden");

	clearTimeout(hud.dialogTimer);
	hud.dialogTimer = setTimeout(() => $("dialog").classList.add("hidden"), DIALOG_MS);
}

// Animation des cooldowns : un voile qui descend, avec les secondes restantes.
function tickCooldowns() {
	const now = performance.now();

	// Barre bleue : disponibilité du dernier sort lancé, pleine quand il est prêt.
	let ready = 1;
	if (hud.lastCast) {
		ready = Math.max(0, Math.min(1, (now - hud.lastCast.start) / hud.lastCast.total));
		if (ready >= 1) hud.lastCast = null;
	}
	$("en-clip").style.width = Math.round(EN_WIDTH * ready) + "px";
	$("en-text").textContent = Math.round(ready * 100) + "%";

	for (const [spellId, end] of Object.entries(hud.cooldownEnds)) {
		const slot = $("spell-" + spellId);
		const overlay = slot && slot.querySelector(".spell-cooldown");
		if (!overlay) continue;

		const remaining = end.at - now;
		if (remaining <= 0) {
			overlay.classList.add("hidden");
			slot.classList.add("flash");
			setTimeout(() => slot.classList.remove("flash"), 300);
			delete hud.cooldownEnds[spellId];
			continue;
		}
		overlay.classList.remove("hidden");
		overlay.style.transform = `scaleY(${remaining / end.total})`;
		overlay.textContent = Math.ceil(remaining / 1000);
	}
	requestAnimationFrame(tickCooldowns);
}

Events.Subscribe("wakfu:init", (payload) => {
	const data = parse(payload);
	hud.classes = data.classes || {};
	hud.quests = data.quests || {};
	hud.items = data.items || {};
	hud.rerollOrder = list(data.rerollOrder);
	hud.blades = list(data.blades);
	hud.trails = list(data.trails);
	hud.trailSizes = list(data.trailSizes);
	if (data.trailKey) $("help-trail-key").textContent = data.trailKey;
	if (data.demonKey) $("help-demon-key").textContent = data.demonKey;
	hud.camps = data.camps || {};
	hud.campOrder = list(data.campOrder);
	hud.forgeCost = data.forgeCost || 0;
	SKINS = [""].concat(list(data.skins));
	hud.slotCount = data.slotCount;
	hud.maxWeight = data.maxWeight;
	renderState();
});

Events.Subscribe("wakfu:state", (payload) => {
	hud.state = parse(payload);
	renderState();
	onStateChanged();
});

Events.Subscribe("wakfu:health", (payload) => {
	const { hp, maxHp } = parse(payload);
	const pct = maxHp > 0 ? Math.max(0, Math.min(1, hp / maxHp)) : 0;
	$("hp-clip").style.width = Math.round(HP_WIDTH * pct) + "px";
	$("hp-text").textContent = `${hp}/${maxHp}`;
	$("ko").classList.toggle("hidden", hp > 0);
});

Events.Subscribe("wakfu:cast", (payload) => {
	const { id, cooldown } = parse(payload);
	document.querySelectorAll(".spell.selected").forEach((el) => el.classList.remove("selected"));
	const castSlot = $("spell-" + id);
	if (castSlot) {
		castSlot.classList.add("selected");
		clearTimeout(hud.selectTimer);
		hud.selectTimer = setTimeout(() => castSlot.classList.remove("selected"), 1500);
	}
	hud.cooldownEnds[id] = { at: performance.now() + cooldown * 1000, total: cooldown * 1000 };
	hud.lastCast = { start: performance.now(), total: cooldown * 1000 };
});

Events.Subscribe("wakfu:portrait", (src) => {
	$("portrait-img").src = src;
	$("portrait-live").classList.remove("empty");
});

Events.Subscribe("wakfu:dialog", (payload) => showDialog(parse(payload)));

Events.Subscribe("wakfu:dialogClose", () => $("dialog").classList.add("hidden"));

Events.Subscribe("wakfu:toast", (text) => toast(text));

document.addEventListener("DOMContentLoaded", () => {
	renderState();
	requestAnimationFrame(tickCooldowns);
});

// Menu pause : les clics repartent vers Lua, qui ferme le menu ou ouvre la suite.
document.addEventListener("click", (event) => {
	const target = event.target.closest("[data-action]");
	if (target) Events.Call("wakfu:menu", target.dataset.action);
});

document.addEventListener("keydown", (event) => {
	if (event.key === "Escape" && !$("menu").classList.contains("hidden")) Events.Call("wakfu:menu", "resume");
});

Events.Subscribe("wakfu:menuOpen", (open) => {
	$("menu").classList.toggle("hidden", !open);
});

// Créateur de personnage : chaque clic envoie le choix complet, le serveur l'applique au personnage.
const GENDERS = ["Homme", "Femme"];
const COLORS = ["#e0602a", "#18b8ee", "#4f9e3a", "#6b4a8e", "#fdb10d", "#c8323c"];

const creator = { class: "", gender: "Homme", color: 1, skin: "" };
let SKINS = [""];

function sendCreation() {
	Events.Call("wakfu:create", creator.class, creator.gender, creator.color, $("nick-input").value, creator.skin);
	renderCreator();
}

function renderCreator() {
	$("class-list").innerHTML = classOrder()
		.map(
			(name) =>
				`<button type="button" class="class-card${name === creator.class ? " selected" : ""}" data-class="${name}">` +
				`<span class="class-gem" style="background:${classColor(name)}"></span>` +
				`<span><b>${escapeHtml(classLabel(name))}</b><small>${escapeHtml(hud.classes[name].short || hud.classes[name].role || "")}</small></span></button>`
		)
		.join("");
	$("gender-list").innerHTML = GENDERS.map(
		(g) => `<button type="button" class="gender-btn${g === creator.gender ? " selected" : ""}" data-gender="${g}">${g}</button>`
	).join("");
	$("skin-label").classList.toggle("hidden", SKINS.length < 2);
	$("skin-list").classList.toggle("hidden", SKINS.length < 2);
	$("skin-list").innerHTML = SKINS.map(
		(s) => `<button type="button" class="gender-btn${s === creator.skin ? " selected" : ""}" data-skin="${s}">${s || "Classique"}</button>`
	).join("");
	$("color-list").innerHTML = COLORS.map(
		(color, i) =>
			`<button type="button" class="color-dot${i + 1 === creator.color ? " selected" : ""}" data-color="${i + 1}" style="background:${color}" aria-label="Couleur ${i + 1}"></button>`
	).join("");
}

document.addEventListener("click", (event) => {
	const cls = event.target.closest(".class-card[data-class]");
	const gender = event.target.closest("[data-gender]");
	const color = event.target.closest("[data-color]");
	const skin = event.target.closest("[data-skin]");
	if (cls) { creator.class = cls.dataset.class; sendCreation(); }
	else if (gender) { creator.gender = gender.dataset.gender; sendCreation(); }
	else if (skin) { creator.skin = skin.dataset.skin; sendCreation(); }
	else if (color) { creator.color = Number(color.dataset.color); sendCreation(); }
	else if (event.target.closest("#creator-ok")) { sendCreation(); Events.Call("wakfu:creatorClose"); }
	else if (event.target.closest("#creator-back")) Events.Call("wakfu:creatorClose");
});

document.addEventListener("DOMContentLoaded", () => $("nick-input").addEventListener("change", sendCreation));

document.addEventListener("keydown", (event) => {
	if (event.key === "Escape" && !$("creator").classList.contains("hidden")) Events.Call("wakfu:creatorClose");
});

Events.Subscribe("wakfu:creatorOpen", (open) => {
	if (open) {
		const state = hud.state || {};
		creator.class = state.class || creator.class;
		creator.gender = state.gender || creator.gender;
		creator.color = state.color || creator.color;
		creator.skin = state.skin || "";
		$("nick-input").value = state.name || "";
		renderCreator();
	}
	$("creator").classList.toggle("hidden", !open);
	document.body.classList.toggle("creating", open);

});



// Inventaire : le serveur est la source de vérité ; chaque action repart vers Lua puis le sac revient.
const EQUIP_LEFT = ["head", "chest", "legs", "feet"];
const EQUIP_RIGHT = ["hands", "shirt", "ring", "weapon"];
const STAT_LABELS = { endurance: "Endurance", vitesse: "Vitesse", force: "Force" };
const RARITY_LABELS = { common: "Commun", uncommon: "Peu commun", rare: "Rare", epic: "Épique" };
const FILTERS = [["", "Filtrer par:"], ["Équipement", "Équipement"], ["Consommable", "Consommable"]];
const ICONS = {
	mask: '<path d="M12 4c-5 0-8 3-8 8 0 5 3 8 8 8s8-3 8-8c0-5-3-8-8-8zm-3 7a1.500 1.500 0 1 0 0 3 1.500 1.500 0 0 0 0-3zm6 0a1.500 1.500 0 1 0 0 3 1.500 1.500 0 0 0 0-3z"/>',
	vest: '<path d="M8 3l4 3 4-3 5 4-3 4-2-1v11H8V10l-2 1-3-4z"/>',
	pants: '<path d="M6 3h12l1 18h-5l-2-10-2 10H5z"/>',
	boots: '<path d="M7 3h6v9l6 3v5H4v-4l3-2z"/>',
	gloves: '<path d="M7 11V5a1.500 1.500 0 0 1 3 0v4V4a1.500 1.500 0 0 1 3 0v5V5a1.500 1.500 0 0 1 3 0v6l2-2a1.500 1.500 0 0 1 2 2l-4 9H9l-3-6z"/>',
	shirt: '<path d="M8 3l4 2 4-2 6 4-3 4-2-1v11H7V10l-2 1-3-4z"/>',
	talisman: '<path d="M7 2h10v14l-5 6-5-6z"/><circle cx="12" cy="9" r="2.500" fill="#000" opacity=".45"/>',
	dagger: '<path d="M19 2l3 3-9 11-3-3zM9 14l3 3-3 5-2-1-1-2z"/>',
	onigiri: '<path d="M12 3l9 17H3z"/><path d="M8.500 20l1.200-3.500h4.600L15.500 20z" fill="#000" opacity=".5"/>',
};

const inv = { slots: {}, equip: {}, weight: 0, filter: 0, query: "", dragSlot: null };

function iconHtml(def, large) {
	if (def.icon === "orb") return '<span class="orb"><svg viewBox="0 0 64 64" width="64" height="64"><defs><radialGradient id="orbg" cx="35%" cy="30%"><stop offset="0" stop-color="#fff"/><stop offset=".35" stop-color="#6fd0ff"/><stop offset=".7" stop-color="#b04cf0"/><stop offset="1" stop-color="#2a5cff"/></radialGradient></defs><circle cx="32" cy="32" r="28" fill="url(#orbg)"/></svg></span>';
	const color = { common: "#c5cdd2", uncommon: "#7fe39a", rare: "#7fd6f5", epic: "#c9a6ff" }[def.rarity] || "#c5cdd2";
	return `<svg class="icon" viewBox="0 0 24 24" fill="${color}">${ICONS[def.icon] || ""}</svg>`;
}

function itemDef(id) {
	return (hud.items || {})[id];
}

function emptyIcon(slotName) {
	const sample = Object.values(hud.items || {}).find((def) => def.slot === slotName);
	return sample ? iconHtml(Object.assign({}, sample, { rarity: "common" })) : "";
}

function slotHtml(def, entry) {
	return iconHtml(def) + (entry.count > 1 ? `<span class="count">x${entry.count}</span>` : "");
}

function renderInventory() {
	const grid = $("inv-grid");
	grid.innerHTML = "";
	const query = inv.query.trim().toLowerCase();
	const type = FILTERS[inv.filter][0];
	for (let i = 1; i <= (hud.slotCount || 25); i++) {
		const entry = inv.slots[i];
		const def = entry && itemDef(entry.id);
		const cell = document.createElement("div");
		cell.dataset.slot = i;
		cell.className = "inv-slot" + (def ? " filled rarity-" + def.rarity : "");
		if (def) {
			cell.draggable = true;
			cell.innerHTML = slotHtml(def, entry);
			const hidden = (query && !def.name.toLowerCase().includes(query)) || (type && def.type !== type);
			if (hidden) cell.classList.add("dim");
		}
		grid.appendChild(cell);
	}

	for (const [id, names] of [["inv-equip-left", EQUIP_LEFT], ["inv-equip-right", EQUIP_RIGHT]]) {
		const column = $(id);
		column.innerHTML = "";
		for (const name of names) {
			const itemId = inv.equip[name];
			const def = itemId && itemDef(itemId);
			const cell = document.createElement("div");
			cell.dataset.equip = name;
			cell.className = "inv-slot" + (def ? " filled rarity-" + def.rarity : "");
			cell.innerHTML = def ? iconHtml(def) : emptyIcon(name);
			column.appendChild(cell);
		}
	}

	$("inv-weight-value").textContent = (Math.round(inv.weight * 100) / 100).toString();
	$("inv-weight-max").textContent = hud.maxWeight || 30;
	$("inv-weight").classList.toggle("full", inv.weight >= (hud.maxWeight || 30));
	$("inv-kamas-value").textContent = "¥" + String(hud.state ? hud.state.kamas : 0).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
	$("inv-filter-label").textContent = FILTERS[inv.filter][1];
}

Events.Subscribe("wakfu:inventory", (payload) => {
	const data = parse(payload);
	inv.slots = {};
	for (const entry of list(data.slots)) inv.slots[entry.slot] = entry;
	inv.equip = data.equip && !Array.isArray(data.equip) ? data.equip : {};
	inv.weight = data.weight || 0;
	hideInvPopups();
	renderInventory();
});

function hideInvPopups() {
	$("inv-menu").classList.add("hidden");
	$("inv-tip").classList.add("hidden");
}

// Placement d'une fenêtre près d'un slot, dans le repère 1920 x 1080 de la maquette.
function placeNear(element, cell, preferBelow) {
	const stageRect = $("inv-stage").getBoundingClientRect();
	const rect = cell.getBoundingClientRect();
	const scale = stageRect.width / 1920;
	let x = (rect.left - stageRect.left) / scale + 20;
	let y = (rect.top - stageRect.top) / scale + (preferBelow ? 60 : 90);
	element.classList.remove("hidden");
	const height = element.offsetHeight;
	x = Math.min(x, 1920 - element.offsetWidth - 20);
	y = Math.min(y, 1080 - height - 20);
	element.style.left = x + "px";
	element.style.top = y + "px";
}

function showTip(cell, def) {
	const stats = Object.entries(def.stats && !Array.isArray(def.stats) ? def.stats : {});
	$("inv-tip").innerHTML =
		`<div class="tip-head"><div><div class="tip-name">${escapeHtml(def.name)}</div><div class="tip-type">${escapeHtml(def.type)}</div></div>` +
		`<span class="tip-rarity ${def.rarity}">${RARITY_LABELS[def.rarity] || ""}</span></div>` +
		`<div class="tip-body">${escapeHtml(def.desc)}<br>Créé par <b>${escapeHtml(def.creator || "")}</b></div>` +
		(stats.length ? `<div class="tip-stats">${stats.map(([k, v]) => `<div class="tip-row ${k}"><span>${STAT_LABELS[k] || k}</span><span>+${v}%</span></div>`).join("")}</div>` : "") +
		`<div class="tip-weight"><span>Poids</span><span>${def.weight}kg</span></div>`;
	placeNear($("inv-tip"), cell, false);
}

function showMenu(cell, slot, def) {
	const actions = [[def.type === "Consommable" ? "Utiliser" : "Équiper", "use", "use"], ["Donner", "give", ""], ["Jeter", "drop", ""], ["Supprimer", "delete", "danger"]];
	const menu = $("inv-menu");
	menu.innerHTML = actions.map(([label, action, cls]) => `<button type="button" class="${cls}" data-act="${action}" data-slot="${slot}">${label}</button>`).join("");
	$("inv-tip").classList.add("hidden");
	placeNear(menu, cell, true);
}

function openInventory(open) {
	$("inventory").classList.toggle("hidden", !open);
	document.body.classList.toggle("inventory", open);
	hideInvPopups();
	if (open) {
		scaleInventory();
		renderInventory();
	}
}

function scaleInventory() {
	document.documentElement.style.setProperty("--inv-scale", Math.min(window.innerWidth / 1920, window.innerHeight / 1080));
}
window.addEventListener("resize", scaleInventory);

Events.Subscribe("wakfu:inventoryOpen", (open) => openInventory(open));

const invOpen = () => !$("inventory").classList.contains("hidden");

document.addEventListener("click", (event) => {
	if (!invOpen()) return;
	const act = event.target.closest("#inv-menu button");
	if (act) {
		const slot = Number(act.dataset.slot);
		Events.Call("wakfu:inv" + { use: "Use", give: "Give", drop: "Drop", delete: "Delete" }[act.dataset.act], slot);
		hideInvPopups();
		return;
	}
	if (event.target.closest("#inv-close")) return Events.Call("wakfu:inventoryClose");
	if (event.target.closest("#inv-auction")) return toast("L'hôtel de vente arrive bientôt");
	if (event.target.closest("#inv-filter")) {
		inv.filter = (inv.filter + 1) % FILTERS.length;
		return renderInventory();
	}
	const cell = event.target.closest(".inv-slot");
	if (cell && cell.dataset.slot && inv.slots[cell.dataset.slot]) {
		const slot = Number(cell.dataset.slot);
		return showMenu(cell, slot, itemDef(inv.slots[slot].id));
	}
	if (cell && cell.dataset.equip && inv.equip[cell.dataset.equip]) {
		return Events.Call("wakfu:invUnequip", cell.dataset.equip);
	}
	hideInvPopups();
});

document.addEventListener("mouseover", (event) => {
	if (!invOpen() || !$("inv-menu").classList.contains("hidden")) return;
	const cell = event.target.closest(".inv-slot");
	let def = null;
	if (cell && cell.dataset.slot && inv.slots[cell.dataset.slot]) def = itemDef(inv.slots[cell.dataset.slot].id);
	if (cell && cell.dataset.equip && inv.equip[cell.dataset.equip]) def = itemDef(inv.equip[cell.dataset.equip]);
	if (def) showTip(cell, def);
	else $("inv-tip").classList.add("hidden");
});

// Glisser-déposer : sur un autre slot = échange ou fusion, sur « jeter » = jeter.
document.addEventListener("dragstart", (event) => {
	const cell = event.target.closest && event.target.closest(".inv-slot[data-slot]");
	if (!cell) return;
	inv.dragSlot = Number(cell.dataset.slot);
	event.dataTransfer.setData("text/plain", String(inv.dragSlot));
	hideInvPopups();
});
document.addEventListener("dragover", (event) => {
	if (inv.dragSlot === null) return;
	const target = event.target.closest(".inv-slot[data-slot], #inv-drop");
	document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
	if (target) {
		event.preventDefault();
		target.classList.add("drag-over");
	}
});
document.addEventListener("drop", (event) => {
	if (inv.dragSlot === null) return;
	event.preventDefault();
	document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
	const cell = event.target.closest(".inv-slot[data-slot]");
	if (event.target.closest("#inv-drop")) Events.Call("wakfu:invDrop", inv.dragSlot);
	else if (cell) Events.Call("wakfu:invMove", inv.dragSlot, Number(cell.dataset.slot));
	inv.dragSlot = null;
});
document.addEventListener("dragend", () => {
	inv.dragSlot = null;
	document.querySelectorAll(".drag-over").forEach((el) => el.classList.remove("drag-over"));
});

document.addEventListener("input", (event) => {
	if (event.target.id === "inv-search-input") {
		inv.query = event.target.value;
		renderInventory();
	}
});

document.addEventListener("keydown", (event) => {
	if (!invOpen()) return;
	if (event.key === "Escape") Events.Call("wakfu:inventoryClose");
	else if ((event.key === "i" || event.key === "I") && event.target.id !== "inv-search-input") Events.Call("wakfu:inventoryClose");
});

// Changer de voie : on choisit une carte, on voit l'aperçu, puis on confirme ; le serveur applique.
const REROLL_STEPS = [["Choix de la voie", "Sélectionnez votre nouveau style"], ["Aperçu", "Découvrez vos techniques"], ["Confirmation", "Vérifiez les détails"], ["Finalisation", "Le changement est appliqué"]];
const BAR_LABELS = [["damage", "Dégâts", "#ff3b3b"], ["survival", "Survie", "#ff7a2a"], ["support", "Soutien", "#d4902f"], ["control", "Contrôle", "#a77c4a"]];
const rr = { selected: null, step: 1 };

function currentClass() {
	return hud.state ? hud.state.class : "";
}

function classLabel(name) {
	const def = hud.classes[name];
	return def ? def.name : name;
}

// Kanji de la classe : il remplace les portraits d'illustration.
function glyphOf(name) {
	const def = hud.classes[name];
	return (def && def.glyph) || classLabel(name).charAt(0);
}

// Rôle affiché dans les badges : court, pour tenir dans la colonne de droite.
function roleOf(name) {
	const def = hud.classes[name];
	return (def && def.role) || classLabel(name);
}

function emblem(name) {
	return `<span class="rr-emblem" style="--rr-color:${classColor(name)}">${escapeHtml(glyphOf(name))}</span>`;
}

function renderSteps() {
	$("rr-steps").innerHTML = REROLL_STEPS.map(([title, sub], i) => {
		const n = i + 1;
		const cls = n === rr.step ? " active" : n < rr.step ? " done" : "";
		return `<div class="rr-step${cls}"><i>${n < rr.step ? "✓" : n}</i><span><b>${title}</b><small>${sub}</small></span></div>` + (n < 4 ? '<span class="rr-sep">›</span>' : "");
	}).join("");
}

function renderReroll() {
	const order = classOrder();
	const current = currentClass();
	if (!rr.selected || !hud.classes[rr.selected]) rr.selected = hud.classes[current] ? current : order[0];
	const def = hud.classes[rr.selected];
	if (!def) return;
	const stage = $("rr-stage");
	stage.style.setProperty("--rr-color", classColor(rr.selected));

	$("rr-cards").innerHTML = order
		.map((name, i) => {
			const cls = (name === rr.selected ? " selected" : "") + (name === current ? " current" : "");
			return (
				`<button type="button" class="rr-card${cls}" data-class="${name}" style="left:${i * 148 + 3}px;--rr-color:${classColor(name)}">` +
				`<span class="rr-face"><span class="rr-glyph">${escapeHtml(glyphOf(name))}</span><span class="rr-cardname">${escapeHtml(classLabel(name))}</span></span></button>`
			);
		})
		.join("");

	$("rr-art").innerHTML = `<span class="rr-bigglyph">${escapeHtml(glyphOf(rr.selected))}</span>`;
	$("rr-emblem").outerHTML = `<span id="rr-emblem">${emblem(rr.selected)}</span>`;
	$("rr-name").textContent = classLabel(rr.selected);
	$("rr-title2").textContent = def.title || def.role || "";
	$("rr-blurb").textContent = def.blurb || "";
	$("rr-tags").innerHTML = list(def.tags).map((t) => `<span>${escapeHtml(t)}</span>`).join("");

	const spells = list(def.spells);
	let skills = "";
	for (let i = 0; i < 4; i++) {
		const spell = spells[i];
		if (spell) {
			skills += `<div class="rr-skill letter" title="${escapeHtml(spell.name)}">${escapeHtml(spell.name.charAt(0))}</div>`;
		} else {
			skills += `<div class="rr-skill locked">?</div>`;
		}
	}
	$("rr-skills").innerHTML = skills;

	const play = def.gameplay || {};
	$("rr-bars").innerHTML = BAR_LABELS.map(([key, label, barColor]) => `<div class="rr-bar"><span>${label}</span><i><b style="width:${play[key] || 0}%;background:${barColor}"></b></i></div>`).join("");

	const rank = hud.state && hud.state.rank;
	$("rr-cur-portrait").style.setProperty("--rr-color", classColor(current));
	$("rr-cur-portrait").textContent = glyphOf(current);
	$("rr-cur-name").textContent = hud.state ? hud.state.name : "";
	$("rr-cur-level").textContent = rank ? rank.name : "";
	$("rr-cur-class").innerHTML = emblem(current) + escapeHtml(roleOf(current));
	$("rr-new-portrait").style.setProperty("--rr-color", classColor(rr.selected));
	$("rr-new-portrait").textContent = glyphOf(rr.selected);
	$("rr-new-name").textContent = classLabel(rr.selected);
	$("rr-new-level").textContent = "XP conservée";
	$("rr-new-class").innerHTML = emblem(rr.selected) + escapeHtml(roleOf(rr.selected));
	$("rr-confirm").disabled = rr.selected === current;
	renderSteps();
}

function scaleReroll() {
	document.documentElement.style.setProperty("--rr-scale", Math.min(window.innerWidth / 1536, window.innerHeight / 1024));
}
window.addEventListener("resize", scaleReroll);

Events.Subscribe("wakfu:rerollOpen", (open) => {
	$("reroll").classList.toggle("hidden", !open);
	document.body.classList.toggle("reroll", open);
	if (open) {
		rr.selected = null;
		rr.step = 1;
		scaleReroll();
		renderReroll();
	}
});

const rerollOpenNow = () => !$("reroll").classList.contains("hidden");

document.addEventListener("click", (event) => {
	if (!rerollOpenNow()) return;
	if (event.target.closest("#rr-close")) return Events.Call("wakfu:rerollClose");
	const card = event.target.closest(".rr-card");
	if (card) {
		rr.selected = card.dataset.class;
		rr.step = rr.selected === currentClass() ? 1 : 2;
		return renderReroll();
	}
	if (event.target.closest("#rr-confirm") && rr.selected && rr.selected !== currentClass()) {
		Events.Call("wakfu:classReroll", rr.selected);
		rr.step = 4;
		renderSteps();
		setTimeout(() => Events.Call("wakfu:rerollClose"), 900);
	}
});

document.addEventListener("mouseover", (event) => {
	if (rerollOpenNow() && event.target.closest("#rr-confirm") && !$("rr-confirm").disabled && rr.step === 2) {
		rr.step = 3;
		renderSteps();
	}
});

document.addEventListener("keydown", (event) => {
	if (rerollOpenNow() && event.key === "Escape") Events.Call("wakfu:rerollClose");
});

// Le HUD garde la classe à jour : on réaffiche si l'écran est ouvert quand l'état change.
function onStateChanged() {
	if (rerollOpenNow()) renderReroll();
	if (forgeOpenNow()) renderForge();
	if (trailOpenNow()) renderTrail();
	if (typeof invOpen === "function" && invOpen()) renderInventory();
}

// Forge des lames Nichirin : le serveur vérifie la distance, le prix et la place dans le sac, puis renvoie le sac et un message.
const forge = { group: "", query: "" };
const forgeOpenNow = () => !$("forge").classList.contains("hidden");
const BLADE_RARITY = { rare: "rare", epic: "epic" };

function renderForge() {
	const blades = list(hud.blades);
	const groups = [""].concat([...new Set(blades.map((blade) => blade.group))]);
	const yens = hud.state ? hud.state.kamas : 0;
	$("forge-yens").textContent = `${yens} yens`;
	$("forge-sub").textContent = `Chaque lame coûte ${hud.forgeCost || 0} yens et rejoint ton sac : équipe-la ensuite avec I.`;
	$("forge-tabs").innerHTML = groups
		.map((group) => `<button type="button" class="forge-tab${group === forge.group ? " selected" : ""}" data-group="${escapeHtml(group)}">${group ? escapeHtml(group) : "Toutes"}</button>`)
		.join("");
	const query = forge.query.trim().toLowerCase();
	const shown = blades.filter((blade) => (!forge.group || blade.group === forge.group) && (!query || blade.name.toLowerCase().includes(query)));
	$("forge-list").innerHTML = shown.length
		? shown
				.map((blade) => {
					const def = itemDef(blade.id) || {};
					const force = def.stats && def.stats.force ? `+${def.stats.force}% force · ` : "";
					return (
						`<button type="button" class="forge-blade rarity-${BLADE_RARITY[def.rarity] || "rare"}" data-blade="${escapeHtml(blade.id)}">` +
						`<b>${escapeHtml(blade.name)}</b><small>${escapeHtml(blade.group)} · ${force}${def.weight || 0} kg</small></button>`
					);
				})
				.join("")
		: `<div class="empty">Aucune lame ne porte ce nom.</div>`;
}

Events.Subscribe("wakfu:forgeOpen", (open) => {
	$("forge").classList.toggle("hidden", !open);
	document.body.classList.toggle("forge", open);
	if (open) {
		forge.group = "";
		forge.query = "";
		$("forge-search").value = "";
		renderForge();
	}
});

document.addEventListener("click", (event) => {
	if (!forgeOpenNow()) return;
	if (event.target.closest("#forge-close")) return Events.Call("wakfu:forgeClose");
	const tab = event.target.closest(".forge-tab");
	if (tab) {
		forge.group = tab.dataset.group;
		return renderForge();
	}
	const blade = event.target.closest(".forge-blade");
	if (blade) Events.Call("wakfu:forgeBuy", blade.dataset.blade);
});

document.addEventListener("input", (event) => {
	if (event.target.id === "forge-search") {
		forge.query = event.target.value;
		renderForge();
	}
});

document.addEventListener("keydown", (event) => {
	if (forgeOpenNow() && event.key === "Escape") Events.Call("wakfu:forgeClose");
});

// Traînée de l'arme : le serveur valide le choix, l'applique à l'arme tenue et renvoie l'état (hud.state.trail : "auto", "none" ou un identifiant).
const trail = { group: "" };
const trailOpenNow = () => !$("trail").classList.contains("hidden");

function trailChoiceLabel(choice) {
	if (!choice || choice === "auto") return "Automatique (celle de ta voie)";
	if (choice === "none") return "Aucune";
	const found = list(hud.trails).find((t) => t.id === choice);
	return found ? `${found.group} · ${found.name}` : choice;
}

function renderTrail() {
	const choice = (hud.state && hud.state.trail) || "auto";
	const trails = list(hud.trails);
	const groups = [""].concat([...new Set(trails.map((t) => t.group))]);
	$("trail-current").textContent = "Actuelle : " + trailChoiceLabel(choice);
	const sizeId = (hud.state && hud.state.trailSize) || "";
	$("trail-sizes").innerHTML =
		"<span>Taille :</span>" +
		list(hud.trailSizes)
			.map((size) => `<button type="button" class="forge-tab${size.id === sizeId ? " selected" : ""}" data-tsize="${escapeHtml(size.id)}">${escapeHtml(size.label)}</button>`)
			.join("");
	$("trail-tabs").innerHTML = groups
		.map((group) => `<button type="button" class="forge-tab${group === trail.group ? " selected" : ""}" data-tgroup="${escapeHtml(group)}">${group ? escapeHtml(group) : "Toutes"}</button>`)
		.join("");
	const option = (id, name, sub) =>
		`<button type="button" class="trail-opt${choice === id ? " selected" : ""}" data-trail="${escapeHtml(id)}"><b>${escapeHtml(name)}</b><small>${escapeHtml(sub)}</small></button>`;
	let html = option("auto", "Automatique", "La traînée de ta voie") + option("none", "Aucune", "Pas de traînée");
	html += trails.filter((t) => !trail.group || t.group === trail.group).map((t) => option(t.id, t.name, t.group)).join("");
	if (!trails.length) html += `<div class="empty">Aucune traînée cuite pour l'instant.</div>`;
	$("trail-list").innerHTML = html;
}

Events.Subscribe("wakfu:trailOpen", (open) => {
	$("trail").classList.toggle("hidden", !open);
	document.body.classList.toggle("trail", open);
	if (open) {
		trail.group = "";
		renderTrail();
	}
});

document.addEventListener("click", (event) => {
	if (event.target.closest("#inv-trail")) return Events.Call("wakfu:trailRequest");
	if (!trailOpenNow()) return;
	if (event.target.closest("#trail-close")) return Events.Call("wakfu:trailClose");
	const tab = event.target.closest("[data-tgroup]");
	if (tab) {
		trail.group = tab.dataset.tgroup;
		return renderTrail();
	}
	const size = event.target.closest("[data-tsize]");
	if (size) return Events.Call("wakfu:trailSize", size.dataset.tsize);
	const choice = event.target.closest(".trail-opt");
	if (choice) Events.Call("wakfu:trailChoose", choice.dataset.trail);
});

document.addEventListener("keydown", (event) => {
	if (trailOpenNow() && event.key === "Escape") Events.Call("wakfu:trailClose");
});

// ===== Démon : thème, choix du camp, jauges, techniques, prochain palier, geste de dévoration =====

const DROP = '<svg aria-hidden="true" viewBox="0 0 24 24" width="11" height="11"><path d="M12 2c4 5 7 8.5 7 12a7 7 0 0 1-14 0c0-3.5 3-7 7-12z" fill="#ff8a96"/></svg>';
const LOCK = '<svg aria-hidden="true" viewBox="0 0 24 24" width="30" height="30"><rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="#efe3d0" stroke-width="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3" fill="none" stroke="#efe3d0" stroke-width="2"/></svg>';
const CHECK = '<svg aria-hidden="true" viewBox="0 0 24 24" width="14" height="14"><path d="M5 12.5l4.5 4.5L19 7" fill="none" stroke="#fff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>';

const isDemon = () => !!(hud.state && hud.state.camp === "demon");

// Thème du démon : une classe sur <html> restyle tout le HUD (logo, panneaux, personnage, techniques, messages) et montre le voile de sang.
function applyTheme() {
	document.documentElement.classList.toggle("demon", isDemon());
	$("demon-fx").classList.toggle("hidden", !isDemon());
}

// Choix de la faction : chaque carte ouvre une confirmation avant l’envoi définitif au serveur.
const camp = { pending: "", closeTimer: 0, confirmTimer: 0, fallbackTimer: 0 };

function renderCamp() {
	const order = hud.campOrder && hud.campOrder.length ? hud.campOrder : Object.keys(hud.camps || {});
	$("camp-cards").innerHTML = order
		.filter((id) => hud.camps[id])
		.map((id, index) => {
			const def = hud.camps[id];
			const pending = camp.pending === id;
			return (
				`<div class="camp-card${pending ? " pending" : ""} ${index === 0 ? "left" : "right"}" data-camp="${id}" style="--camp:${def.color}">` +
				`<button type="button" class="camp-pick" data-camp="${id}" aria-label="Sélectionner ${escapeHtml(def.name)}">Sélectionner</button>` +
				`</div>`
			);
		})
		.join("");
}

function openCampConfirmation(id) {
	const def = hud.camps[id];
	if (!def) return;
	clearTimeout(camp.closeTimer);
	clearTimeout(camp.confirmTimer);
	clearTimeout(camp.fallbackTimer);
	camp.pending = id;
	const dialog = $("camp-confirmation");
	dialog.dataset.camp = id;
	$("camp-confirm-title").textContent = "Confirmer votre choix ?";
	$("camp-confirm-message").textContent = `Vous avez choisi la faction ${def.name}. Ce choix est définitif pour ce personnage.`;
	$("camp-confirm-accept").disabled = false;
	$("camp-confirm-accept").textContent = "Confirmer";
	$("camp-confirm-cancel").disabled = false;
	dialog.classList.remove("hidden", "is-closing", "is-confirming");
	renderCamp();
}

function closeCampConfirmation() {
	const dialog = $("camp-confirmation");
	if (dialog.classList.contains("hidden") || dialog.classList.contains("is-confirming")) return;
	clearTimeout(camp.closeTimer);
	dialog.classList.add("is-closing");
	camp.closeTimer = setTimeout(() => {
		dialog.classList.add("hidden");
		dialog.classList.remove("is-closing");
		camp.pending = "";
		renderCamp();
	}, 220);
}

function confirmCampChoice() {
	const id = camp.pending;
	if (!id) return;
	clearTimeout(camp.closeTimer);
	const dialog = $("camp-confirmation");
	$("camp-confirm-accept").disabled = true;
	$("camp-confirm-cancel").disabled = true;
	$("camp-confirm-accept").textContent = "Confirmation…";
	dialog.classList.remove("is-closing");
	dialog.classList.add("is-confirming");
	camp.confirmTimer = setTimeout(() => Events.Call("wakfu:chooseCamp", id), 360);
	camp.fallbackTimer = setTimeout(() => {
		if ($("camp").classList.contains("hidden") || camp.pending !== id) return;
		dialog.classList.remove("is-confirming");
		dialog.dataset.camp = id;
		$("camp-confirm-title").textContent = "Le choix n’a pas été confirmé";
		$("camp-confirm-message").textContent = "Le serveur n’a pas confirmé ce choix. Vous pouvez réessayer.";
		$("camp-confirm-accept").textContent = "Réessayer";
		$("camp-confirm-accept").disabled = false;
		$("camp-confirm-cancel").disabled = false;
	}, 2000);
}

Events.Subscribe("wakfu:campOpen", (open) => {
	$("camp").classList.toggle("hidden", !open);
	if (open) {
		camp.pending = "";
		clearTimeout(camp.closeTimer);
		clearTimeout(camp.confirmTimer);
		clearTimeout(camp.fallbackTimer);
		$("camp-confirmation").classList.add("hidden");
		$("camp-confirmation").classList.remove("is-closing", "is-confirming");
		$("camp-confirm-accept").textContent = "Confirmer";
		renderCamp();
	} else {
		clearTimeout(camp.fallbackTimer);
		$("camp-confirmation").classList.add("hidden");
	}
});

document.addEventListener("click", (event) => {
	if ($("camp").classList.contains("hidden")) return;
	if (event.target.closest("#camp-confirm-cancel") || event.target.classList.contains("camp-confirm-scrim")) {
		closeCampConfirmation();
		return;
	}
	if (event.target.closest("#camp-confirm-accept")) {
		if ($("camp-confirm-accept").textContent === "Réessayer") {
			openCampConfirmation(camp.pending);
		} else {
			confirmCampChoice();
		}
		return;
	}
	if (!$("camp-confirmation").classList.contains("hidden")) return;
	const pick = event.target.closest(".camp-pick");
	const card = event.target.closest(".camp-card");
	const id = pick ? pick.dataset.camp : card ? card.dataset.camp : "";
	if (id) openCampConfirmation(id);
});

document.addEventListener("keydown", (event) => {
	if (event.key === "Escape" && !$("camp-confirmation").classList.contains("hidden")) closeCampConfirmation();
});
// Jauges du démon. Le panneau n'existe que pour un démon.
function setGauge(id, ratio, text) {
	const gauge = $(id);
	gauge.querySelector("i").style.width = Math.round(100 * Math.max(0, Math.min(1, ratio))) + "%";
	gauge.querySelector(".dval").textContent = text;
}

// Techniques : coût en sang à la place du délai (démon), verrou avec le palier requis, d'après les valeurs du serveur (view.costs, view.unlock).
function applySpellCosts() {
	const view = isDemon() ? hud.demon : null;
	document.querySelectorAll("#spellbar .spell").forEach((slot, index) => {
		const tip = slot.querySelector(".spell-tip");
		if (!tip || !slot.dataset.name) return;
		// Les tables Lua arrivent en tableau (0 = technique 1) ou en objet indexé par numéro de technique selon leur forme : on accepte les deux.
		const byNumber = (table) => (!table ? 0 : Array.isArray(table) ? table[index] : table[index + 1] || table[String(index + 1)]) || 0;
		const cost = view ? byNumber(view.costs) : 0;
		const required = view ? byNumber(view.unlock) : 0;
		const locked = !!(view && required && view.tier < required);
		slot.classList.toggle("locked", locked);
		tip.textContent = slot.dataset.name + (cost ? ` · ${cost} sang` : "") + (locked ? ` · palier ${required} requis` : "");
		const badge = slot.querySelector(".spell-badge");
		if (badge) {
			badge.classList.toggle("blood", !!view);
			badge.classList.toggle("hidden", !!view && (!cost || locked)); // une technique verrouillée montre son palier, pas son coût
			badge.innerHTML = view ? (cost ? DROP + cost : "") : escapeHtml(slot.dataset.cooldown || "");
		}
		const padlock = slot.querySelector(".spell-padlock");
		const label = slot.querySelector(".spell-lock-label");
		if (padlock) padlock.classList.toggle("hidden", !locked);
		if (label) {
			label.classList.toggle("hidden", !locked);
			label.textContent = locked ? `Palier ${required}` : "";
		}
	});
}

// Prochain palier, sous les quêtes : nom, âmes, progression.
function renderNextTier(view) {
	const block = $("next-tier");
	block.classList.toggle("hidden", !view);
	if (!view) return;
	const span = view.soulsNext ? view.soulsNext - view.soulsFloor : 1;
	$("next-tier-name").textContent = view.nextName || view.tierName;
	$("next-tier-count").textContent = view.soulsNext ? `${view.souls} / ${view.soulsNext} âmes` : "Palier maximal";
	$("next-tier-bar").firstElementChild.style.width = Math.round(100 * (view.soulsNext ? Math.max(0, Math.min(1, (view.souls - view.soulsFloor) / span)) : 1)) + "%";
}

// Gain attendu d'un repas : zones hachurées au bout des jauges de chair et d'âmes tant que le geste dure.
const devour = { gain: null, timer: 0 };

function renderGhosts() {
	const view = isDemon() ? hud.demon : null;
	const gain = devour.gain;
	const flesh = $("dg-flesh").querySelector(".dghost");
	const souls = $("dg-souls").querySelector(".dghost");
	flesh.style.display = souls.style.display = "none";
	if (!view || !gain) return;
	const fleshGain = Math.min(gain.flesh || 0, view.fleshMax - view.flesh);
	if (fleshGain > 0) {
		flesh.style.left = (100 * view.flesh) / view.fleshMax + "%";
		flesh.style.width = (100 * fleshGain) / view.fleshMax + "%";
		flesh.style.display = "block";
	}
	if (view.soulsNext && gain.souls) {
		const span = view.soulsNext - view.soulsFloor;
		const from = Math.max(0, Math.min(1, (view.souls - view.soulsFloor) / span));
		const width = Math.min(gain.souls / span, 1 - from);
		if (width > 0) {
			souls.style.left = 100 * from + "%";
			souls.style.width = 100 * width + "%";
			souls.style.display = "block";
		}
	}
}

function renderDemon() {
	applyTheme();
	const view = isDemon() ? hud.demon : null;
	$("demon").classList.toggle("hidden", !view);
	$("help-demon").classList.toggle("hidden", !view);
	renderNextTier(view);
	if (view) {
		$("demon-tier-name").textContent = view.tierName;
		$("demon-tier-count").textContent = `Palier ${view.tier}/${view.tierCount}`;
		setGauge("dg-blood", view.blood / view.bloodMax, `${view.blood}/${view.bloodMax}`);
		setGauge("dg-flesh", view.flesh / view.fleshMax, `${view.flesh}/${view.fleshMax}`);
		const span = view.soulsNext ? view.soulsNext - view.soulsFloor : 1;
		setGauge("dg-souls", view.soulsNext ? (view.souls - view.soulsFloor) / span : 1, view.soulsNext ? `${view.souls}/${view.soulsNext}` : `${view.souls} · max`);
		$("demon-hint").textContent = view.hungry ? "Affamé : dévore une proie pour te régénérer" : "";
		// Repas du jour : la limite monte avec le grade ; elle devient or quand elle est atteinte.
		$("demon-meals-count").textContent = `${view.meals}/${view.mealsCap}`;
		$("demon-meals").classList.toggle("full", view.meals >= view.mealsCap);
	}
	renderGhosts();
	applySpellCosts();
}

Events.Subscribe("wakfu:demon", (payload) => {
	hud.demon = parse(payload);
	renderDemon();
});

// Geste de dévoration : la barre se remplit en `seconds` secondes avec le temps restant ; le serveur l'arrête s'il aboutit ou s'il est interrompu.
function stopDevour() {
	clearInterval(devour.timer);
	devour.gain = null;
	$("devour").classList.add("hidden");
	document.body.classList.remove("devouring");
	renderGhosts();
}

Events.Subscribe("wakfu:devourStart", (payload) => {
	const { name, seconds, gain } = parse(payload);
	devour.gain = gain || null;
	const fill = $("devour-bar").firstElementChild;
	$("devour-name").textContent = "Dévorer : " + name;
	$("devour-gain").innerHTML = gain
		? `<span><i class="gdot flesh"></i>+${gain.flesh} chair</span><span><i class="gdot souls"></i>+${gain.souls} âmes</span><span><i class="gdot hp"></i>+${gain.heal} % PV</span><span class="gxp">+${gain.xp} XP</span>`
		: "";
	$("devour-gain").classList.toggle("hidden", !gain);
	fill.style.transition = "none";
	fill.style.width = "0";
	$("devour").classList.remove("hidden");
	document.body.classList.add("devouring");
	renderGhosts();
	const end = performance.now() + seconds * 1000;
	clearInterval(devour.timer);
	const tick = () => {
		$("devour-time").textContent = (Math.max(0, end - performance.now()) / 1000).toFixed(1).replace(".", ",") + " s";
	};
	tick();
	devour.timer = setInterval(tick, 100);
	requestAnimationFrame(() =>
		requestAnimationFrame(() => {
			fill.style.transition = `width ${seconds}s linear`;
			fill.style.width = "100%";
		})
	);
});

Events.Subscribe("wakfu:devourStop", stopDevour);

// Écran de bienvenue (planche « Tengen — Bienvenue ») : le nom, le grade, l'argent viennent de l'état du serveur. Le temps de jeu compte la session en cours
// (il ne sera cumulé qu'avec la sauvegarde des joueurs, tâche B1).
const welcomeSince = Date.now();

function welcomeFill() {
	const state = hud.state || {};
	$("wl-name").textContent = state.name || "Joueur";
	$("wl-rank").textContent = state.rank && state.rank.name ? state.rank.name : "-";
	$("wl-money").textContent = String(state.kamas || 0).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " ¥";
	const minutes = Math.floor((Date.now() - welcomeSince) / 60000);
	$("wl-time").textContent = minutes >= 60 ? Math.floor(minutes / 60) + "h " + (minutes % 60) + "m" : minutes + "m";
}

Events.Subscribe("wakfu:welcomeOpen", (open) => {
	$("welcome").classList.toggle("hidden", !open);
	if (open) welcomeFill();
});

Events.Subscribe("wakfu:state", () => {
	if (!$("welcome").classList.contains("hidden")) welcomeFill();
});

document.addEventListener("click", (event) => {
	if ($("welcome").classList.contains("hidden")) return;
	if (event.target.closest("#wl-start")) Events.Call("wakfu:welcomeStart");
	else if (event.target.closest("#wl-character")) Events.Call("wakfu:welcomeCharacter");
});
