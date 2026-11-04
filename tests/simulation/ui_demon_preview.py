"""Rend le HUD du démon dans Edge sans interface : captures d'écran (camp, jauges, dévoration) et vérifications du DOM (clics, états)."""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

from lupa import LuaRuntime, lua_type

SCRATCH = Path(__file__).resolve().parent / "out"
SCRATCH.mkdir(exist_ok=True)
SRC = Path(__file__).resolve().parents[2] / "packages" / "kimetsu-pandora"
OUT = SCRATCH / "ui_demon"
EDGE = next(p for p in (Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"), Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")) if p.exists())

lua = LuaRuntime()
prelude = r'''
local Any = {}
setmetatable(Any, { __index = function() return Any end, __call = function() return Any end })
local ROOT = ...
local env = {}
setmetatable(env, { __index = function(_, k) local v = _G[k]; if v == nil then return Any end; return v end })
local cache = {}
env.Package = setmetatable({ Require = function(name)
	if cache[name] == nil then local f, err
		for _, dir in ipairs({ "Shared", "Server", "Client" }) do f, err = loadfile(ROOT .. "/" .. dir .. "/" .. name, "t", env); if f then break end end
		assert(f, tostring(err)); cache[name] = f() end
	return cache[name] end }, { __index = function() return Any end })
return env.Package.Require("Classes.lua"), env.Package.Require("Items.lua"), env.Package.Require("Quests.lua"), env.Package.Require("Config.lua"), env.Package.Require("VfxPlan.lua"), env.Package.Require("Demon.lua")
'''
Classes, Items, Quests, Config, VfxPlan, Demon = lua.eval("function(...) " + prelude + " end")(str(SRC).replace("\\", "/"))


def to_py(value):
    if lua_type(value) == "table":
        keys = list(value.keys())
        if keys and all(isinstance(k, int) for k in keys) and sorted(keys) == list(range(1, len(keys) + 1)):
            return [to_py(value[k]) for k in sorted(keys)]
        return {str(k): to_py(value[k]) for k in keys}
    return value


def demon_view(souls, blood, flesh):
    state = lua.table_from({"blood": blood, "flesh": flesh, "souls": souls, "sinceFed": 0, "sinceCombat": 99, "meals": 3, "dayElapsed": 0})
    return to_py(Demon.View(Config.Demon, state, 1))


init = {
    "classes": to_py(Classes.List), "quests": to_py(Quests.List), "items": to_py(Items.List), "rerollOrder": to_py(Classes.RerollOrder),
    "equipSlots": to_py(Items.EquipSlots), "slotCount": Items.SlotCount, "maxWeight": Items.MaxWeight, "skins": [], "blades": to_py(Items.BladeList),
    "forgeCost": Config.Forge.cost, "trails": to_py(VfxPlan.TrailList()), "trailSizes": to_py(Config.Vfx.trail.sizes), "trailKey": "J",
    "camps": to_py(Classes.Camps), "campOrder": to_py(Classes.CampOrder), "demonKey": Config.Demon.devourKey,
}
rank = {"index": 2, "count": 8, "name": "Lune Inférieure Six", "kanji": "下六", "hp": 30, "xp": 150, "nextXp": 500}
demon_state = {
    "name": "Muzan", "gender": "Homme", "color": 6, "class": "Demon", "camp": "demon", "trail": "auto", "trailSize": "fine", "kamas": 200, "xp": 220, "rank": rank,
    "stats": {}, "quests": {}, "demon": demon_view(22, 62, 55),
}
slayer_state = {**demon_state, "class": "Eau", "camp": "slayer", "demon": None, "name": "Tanjiro", "rank": {**rank, "name": "Mizunoe", "kanji": "壬", "count": 11}}
nocamp_state = {**slayer_state, "camp": None}
hungry_view = demon_view(40, 8, 0)

if OUT.exists():
    shutil.rmtree(OUT)
shutil.copytree(SRC / "Client" / "UI", OUT)
html = (OUT / "index.html").read_text(encoding="utf-8")
html = html.replace('<script src="index.js"></script>', '<script src="stub.js"></script>\n\t<script src="index.js"></script>\n\t<script src="scene.js"></script>')
(OUT / "index.html").write_text(html, encoding="utf-8")
(OUT / "stub.js").write_text("""
window.handlers = {}; window.calls = [];
window.Events = { Subscribe(name, fn) { (window.handlers[name] = window.handlers[name] || []).push(fn); }, Call(name, ...args) { window.calls.push([name, ...args]); } };
window.fire = (name, payload) => (window.handlers[name] || []).forEach((fn) => fn(payload));
""", encoding="utf-8")
(OUT / "scene.js").write_text("""
const INIT = __INIT__, DEMON = __DEMON__, SLAYER = __SLAYER__, NOCAMP = __NOCAMP__, HUNGRY = __HUNGRY__;
const scene = new URLSearchParams(location.search).get("scene");
const results = [];
const ok = (cond, text) => results.push((cond ? "OK   " : "ECHEC ") + text);
const $$ = (sel) => document.querySelector(sel);
const click = (selector) => $$(selector).dispatchEvent(new MouseEvent("click", { bubbles: true }));
const visible = (id) => !document.getElementById(id).classList.contains("hidden");
window.addEventListener("load", () => {
	fire("wakfu:init", JSON.stringify(INIT));
	fire("wakfu:health", JSON.stringify({ hp: 1220, maxHp: 1330 }));
	if (scene === "camp") { fire("wakfu:state", JSON.stringify(NOCAMP)); fire("wakfu:campOpen", true); click('.camp-card[data-camp="demon"]'); }
	else if (scene === "welcome") { fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:welcomeOpen", true); }
	else if (scene === "hud-demon") { fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:toast", "Villageois dévoré : chair +40, âmes +4 · palier « Chasseur de nuit »"); }
	else if (scene === "hud-hungry") { fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:demon", JSON.stringify(HUNGRY)); }
	else if (scene === "devour") { fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:devourStart", JSON.stringify({ name: "Villageois", seconds: 30, gain: { flesh: 40, souls: 4, heal: 15, xp: 15 } })); }
	else if (scene === "hud-slayer") { fire("wakfu:state", JSON.stringify(SLAYER)); }
	else if (scene === "reroll-demon") { fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:rerollOpen", true); }
	else if (scene === "test") {
		// Ecran de camp : deux cartes, bouton inactif, selection, confirmation
		fire("wakfu:state", JSON.stringify(NOCAMP)); fire("wakfu:campOpen", true);
		ok(visible("camp") && document.querySelectorAll(".camp-card").length === 2, "l'ecran affiche 2 cartes");
		ok($$("#camp-confirm").disabled, "le bouton est inactif sans selection");
		ok($$('.camp-card[data-camp="slayer"] h3').textContent === "Pourfendeur" && $$('.camp-card[data-camp="demon"] h3').textContent === "Démon", "noms des camps");
		ok(document.querySelectorAll('.camp-card[data-camp="demon"] li').length === 5, "5 points pour le demon");
		click('.camp-card[data-camp="demon"]');
		ok($$('.camp-card[data-camp="demon"]').classList.contains("selected") && !$$('.camp-card[data-camp="slayer"]').classList.contains("selected"), "la carte choisie est marquee");
		ok(!$$("#camp-confirm").disabled && $$("#camp-confirm").textContent === "Devenir Démon", "le bouton s'active : " + $$("#camp-confirm").textContent);
		ok(!!$$('.camp-card[data-camp="demon"] .camp-badge') && !$$('.camp-card[data-camp="slayer"] .camp-badge'), "le badge Sélectionné est sur la seule carte choisie");
		ok($$("#camp-confirm").dataset.camp === "demon" && !!$$("#camp-note") && $$('.camp-card[data-camp="demon"] .kanji').textContent === "鬼", "bouton teinté du camp, note boutique, kanji du démon");
		click('.camp-card[data-camp="slayer"]'); ok($$("#camp-confirm").textContent === "Devenir Pourfendeur", "on peut changer d'avis avant de confirmer");
		click("#camp-confirm"); ok(window.calls.some((c) => c[0] === "wakfu:chooseCamp" && c[1] === "slayer"), "la confirmation envoie le camp");
		fire("wakfu:campOpen", false); ok(!visible("camp"), "l'ecran se ferme");
		// Pourfendeur : aucun panneau de demon, aide sans H
		fire("wakfu:state", JSON.stringify(SLAYER));
		ok(!visible("demon") && !visible("help-demon"), "pourfendeur : ni jauges ni aide de dévoration");
		ok(document.querySelectorAll("#spellbar .spell.locked").length === 0, "pourfendeur : aucune technique verrouillee");
		ok(!document.documentElement.classList.contains("demon") && !visible("demon-fx") && !visible("next-tier"), "pourfendeur : ni theme demon, ni voile de sang, ni prochain palier");
		ok(document.querySelectorAll("#spellbar .spell-icon").length === 4 && document.querySelectorAll("#spellbar .spell-glyph").length === 0, "pourfendeur : 4 icones, aucun kanji");
		ok([...document.querySelectorAll("#spellbar .spell-badge")].slice(0, 4).map((b) => b.textContent).join(",") === "2,4,6,10" && !document.querySelector("#spellbar .spell-badge.blood"), "pourfendeur : le badge montre le delai de recharge");
		// Demon : jauges
		fire("wakfu:state", JSON.stringify(DEMON));
		ok(visible("demon") && visible("help-demon"), "demon : jauges et aide visibles");
		ok($$("#demon-tier-name").textContent === "Chasseur de nuit" && $$("#demon-tier-count").textContent === "Palier 2/5", "palier affiche : " + $$("#demon-tier-name").textContent);
		ok($$("#dg-blood .dval").textContent === "62/100" && $$("#dg-flesh .dval").textContent === "55/100" && $$("#dg-souls .dval").textContent === "22/30", "valeurs des jauges : " + $$("#dg-blood .dval").textContent + " " + $$("#dg-flesh .dval").textContent + " " + $$("#dg-souls .dval").textContent);
		ok($$("#dg-blood .dbar i").style.width === "62%" && $$("#dg-souls .dbar i").style.width === "60%", "largeurs : sang " + $$("#dg-blood .dbar i").style.width + ", ames " + $$("#dg-souls .dbar i").style.width);
		ok(document.documentElement.classList.contains("demon") && visible("demon-fx"), "demon : theme sombre et voile de sang");
		ok(document.querySelectorAll("#spellbar .spell-glyph").length === 4 && document.querySelectorAll("#spellbar .spell-icon").length === 0, "demon : 4 kanji a la place des icones");
		ok([...document.querySelectorAll("#spellbar .spell-glyph")].map((g) => g.textContent).join("") === "爪刃癒狂", "demon : kanji des techniques " + [...document.querySelectorAll("#spellbar .spell-glyph")].map((g) => g.textContent).join(""));
		ok(visible("next-tier") && $$("#next-tier-name").textContent === "Prédateur" && $$("#next-tier-count").textContent === "22 / 30 âmes" && $$("#next-tier-bar i").style.width === "60%", "prochain palier : " + $$("#next-tier-name").textContent + ", " + $$("#next-tier-count").textContent + ", " + $$("#next-tier-bar i").style.width);
		const badges = [...document.querySelectorAll("#spellbar .spell:not(.empty)")].map((s) => { const b = s.querySelector(".spell-badge"); return b.classList.contains("hidden") ? "-" : b.textContent; });
		ok(badges.join(",") === "8,12,25,-", "le badge montre le cout en sang (masque sur la technique verrouillee) : " + badges.join(","));
		const lockedSlot = document.querySelectorAll("#spellbar .spell")[3];
		ok($$("#demon-meals-count").textContent === "3/5" && !$$("#demon-meals").classList.contains("full"), "repas du jour : " + $$("#demon-meals-count").textContent);
		fire("wakfu:demon", JSON.stringify({ ...DEMON.demon, meals: 5, mealsCap: 5 }));
		ok($$("#demon-meals-count").textContent === "5/5" && $$("#demon-meals").classList.contains("full"), "limite atteinte : 5/5 passe en or");
		fire("wakfu:demon", JSON.stringify({ ...DEMON.demon, meals: 5, mealsCap: 10 }));
		ok($$("#demon-meals-count").textContent === "5/10" && !$$("#demon-meals").classList.contains("full"), "grade superieur : 5/10, plus en or");
		fire("wakfu:demon", JSON.stringify(DEMON.demon));
		ok(!lockedSlot.querySelector(".spell-padlock").classList.contains("hidden") && lockedSlot.querySelector(".spell-lock-label").textContent === "Palier 4" && !lockedSlot.querySelector(".spell-lock-label").classList.contains("hidden"), "technique 4 : cadenas et mention Palier 4");
		// Techniques : couts et verrou
		const spells = document.querySelectorAll("#spellbar .spell:not(.empty)");
		ok(spells.length === 4 && spells[3].classList.contains("locked") && !spells[0].classList.contains("locked"), "la technique 4 est verrouillee au palier 2");
		ok(spells[0].querySelector(".spell-tip").textContent.includes("8 sang") && spells[3].querySelector(".spell-tip").textContent.includes("40 sang") && spells[3].querySelector(".spell-tip").textContent.includes("palier 4"), "infobulles : " + spells[0].querySelector(".spell-tip").textContent + " / " + spells[3].querySelector(".spell-tip").textContent);
		fire("wakfu:demon", JSON.stringify({ ...DEMON.demon, tier: 4, tierName: "Seigneur de sang", souls: 62, soulsFloor: 60, soulsNext: 100 }));
		ok(!document.querySelectorAll("#spellbar .spell")[3].classList.contains("locked") && document.querySelectorAll("#spellbar .spell")[3].querySelector(".spell-padlock").classList.contains("hidden") && document.querySelectorAll("#spellbar .spell")[3].querySelector(".spell-badge").textContent === "40", "au palier 4 la technique 4 est debloquee : cadenas retire, cout 40 affiche");
		fire("wakfu:demon", JSON.stringify({ ...DEMON.demon, tier: 5, tierName: "Lune de sang", souls: 110, soulsFloor: 100, soulsNext: null }));
		ok($$("#dg-souls .dval").textContent === "110 · max" && $$("#dg-souls .dbar i").style.width === "100%", "dernier palier : jauge pleine et mention max");
		ok($$("#next-tier-count").textContent === "Palier maximal", "dernier palier : le bloc dit Palier maximal");
		fire("wakfu:demon", JSON.stringify(HUNGRY));
		ok($$("#demon-hint").textContent.includes("Affamé") && $$("#dg-flesh .dbar i").style.width === "0%", "affame : message et chair vide");
		// Devoration
		fire("wakfu:state", JSON.stringify(DEMON));
		fire("wakfu:devourStart", JSON.stringify({ name: "Villageois", seconds: 3.5, gain: { flesh: 40, souls: 4, heal: 15, xp: 15 } }));
		ok(visible("devour") && $$("#devour-name").textContent === "Dévorer : Villageois", "la barre de dévoration apparait");
		ok(document.body.classList.contains("devouring"), "le voile de sang monte pendant le repas");
		const pill = $$("#devour-gain").textContent;
		ok(pill.includes("+40 chair") && pill.includes("+4 âmes") && pill.includes("+15 % PV") && pill.includes("+15 XP"), "pastille du gain attendu : " + pill);
		ok($$("#devour-time").textContent === "3,5 s" || $$("#devour-time").textContent === "3,4 s", "temps restant : " + $$("#devour-time").textContent);
		const flesh = $$("#dg-flesh .dghost"), souls = $$("#dg-souls .dghost");
		ok(flesh.style.display === "block" && flesh.style.left === "55%" && flesh.style.width === "40%", "chair : zone hachuree de 55 % a 95 % : " + flesh.style.left + " " + flesh.style.width);
		ok(souls.style.display === "block" && souls.style.left === "60%" && parseFloat(souls.style.width).toFixed(1) === "20.0", "ames : zone hachuree apres 60 % : " + souls.style.left + " " + souls.style.width);
		fire("wakfu:demon", JSON.stringify({ ...DEMON.demon, flesh: 80, souls: 22 }));
		ok($$("#dg-flesh .dghost").style.width === "20%", "le gain de chair est borne par le plafond : " + $$("#dg-flesh .dghost").style.width);
		fire("wakfu:devourStop", "");
		ok(!visible("devour") && !document.body.classList.contains("devouring") && $$("#dg-flesh .dghost").style.display === "none" && $$("#dg-souls .dghost").style.display === "none", "a la fin : barre, voile et zones hachurees disparaissent");
		fire("wakfu:devourStart", JSON.stringify({ name: "Villageois", seconds: 3.5 }));
		ok(!visible("devour-gain") && $$("#dg-flesh .dghost").style.display === "none", "sans gain annonce : ni pastille ni zones hachurees");
		fire("wakfu:devourStop", "");
		// Reroll : seulement les voies du camp
		fire("wakfu:state", JSON.stringify(DEMON)); fire("wakfu:rerollOpen", true);
		const cards = [...document.querySelectorAll(".rr-card")].map((c) => c.dataset.class);
		ok(cards.length === 1 && cards[0] === "Demon", "un demon ne voit que sa voie au reroll : " + cards.join(","));
		fire("wakfu:rerollOpen", false);
		fire("wakfu:state", JSON.stringify(SLAYER)); fire("wakfu:rerollOpen", true);
		const slayerCards = [...document.querySelectorAll(".rr-card")].map((c) => c.dataset.class);
		ok(slayerCards.length === 7 && !slayerCards.includes("Demon"), "un pourfendeur voit ses 7 voies, pas celle des demons : " + slayerCards.length);
		fire("wakfu:rerollOpen", false);
		// Etat avec camp absent : toutes les voies
		fire("wakfu:state", JSON.stringify(NOCAMP)); fire("wakfu:rerollOpen", true);
		ok(document.querySelectorAll(".rr-card").length === 8, "sans camp, les 8 voies sont listees (l'ecran de choix passe avant)");
	}
	const pre = document.createElement("pre"); pre.id = "result"; pre.textContent = results.join("\\n"); pre.style.display = "none"; document.body.appendChild(pre);
	document.title = "ready";
});
"""
    .replace("__INIT__", json.dumps(init, ensure_ascii=False)).replace("__DEMON__", json.dumps(demon_state, ensure_ascii=False))
    .replace("__SLAYER__", json.dumps(slayer_state, ensure_ascii=False)).replace("__NOCAMP__", json.dumps(nocamp_state, ensure_ascii=False))
    .replace("__HUNGRY__", json.dumps(hungry_view, ensure_ascii=False)), encoding="utf-8")

args = sys.argv[1:]
shots = [a for a in args if a != "test"] or ["camp", "hud-demon", "hud-hungry", "devour", "hud-slayer"]


def run(extra, scene):
    url = (OUT / "index.html").as_uri() + "?scene=" + scene
    return subprocess.run([str(EDGE), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=1920,1080", "--virtual-time-budget=4000",
                           "--default-background-color=1B2430FF", *extra, url], check=False, capture_output=True, timeout=120)


failed = False
if "test" in args or not args:
    dom = run(["--dump-dom"], "test").stdout.decode("utf-8", "replace")
    m = re.search(r'<pre id="result"[^>]*>(.*?)</pre>', dom, re.S)
    lines = m.group(1).replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&").strip().splitlines() if m else ["ECHEC : pas de resultat (erreur JavaScript ?)"]
    for line in lines:
        print("  " + line.encode("ascii", "replace").decode())
        failed = failed or line.startswith("ECHEC")
    print("  %d verifications du DOM" % len(lines))
for scene in ([] if args == ["test"] else shots):
    target = SCRATCH / f"ui_{scene}.png"
    if target.exists():
        target.unlink()
    run([f"--screenshot={target}"], scene)
    print(scene, "->", target if target.exists() else "ECHEC")
sys.exit(1 if failed else 0)
