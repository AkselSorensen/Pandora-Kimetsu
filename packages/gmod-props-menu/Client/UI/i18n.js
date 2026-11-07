// Translations for the props menu. To add a language, copy the "en" block, translate the values
// and add it to LANGUAGES. Missing keys fall back to English. {0}, {1} are replaced by values.
const LANGUAGES = { en: "English", fr: "Français" };

const I18N = {
  en: {
    "brand.a": "PROPS",
    "brand.b": "MENU",
    "tab.Prop": "Props",
    "tab.Modèle": "Models",
    "tab.Arme": "Weapons",
    "tab.Entité": "Entities",
    "size": "Size",
    "search": "Search an item…",
    "packs": "PACKS",
    "packs.all": "All packs",
    "packs.favorites": "Favorites",
    "cat.all": "All",
    "group.creator": "EQUIPPABLE · IN THE CHARACTER CREATOR",
    "group.others": "OTHER MODELS",
    "tools": "TOOLS",
    "undo": "↶ Undo last",
    "clear": "🗑 Delete all",
    "close": "✕ Close",
    "history": "🕘 History",
    "history.back": "← Back to items",
    "history.title": "Your history",
    "history.empty": "Nothing spawned yet.",
    "history.clear": "Clear history",
    "history.equipped": "Equipped",
    "history.spawned": "Spawned",
    "tip": "Click an item to spawn it in front of you, or a model to equip it. Star ★ to add it to your favorites.",
    "tip.remove": "Aim at one of your props and press {0} to remove it.",
    "tip.keys": "{0} open / close",
    "tip.esc": "{0} close",
    "items.one": "{0} item",
    "items.many": "{0} items",
    "empty": "No item found",
    "loading": "Loading the catalog…",
    "error": "Could not read the catalog: {0}",
    "toast.spawned": "“{0}” spawned",
    "toast.equipped": "“{0}” equipped",
    "toast.undo": "Last item removed",
    "toast.clear": "All your items removed",
    "toast.history": "History cleared",
    "language": "Language"
  },
  fr: {
    "brand.a": "MENU",
    "brand.b": "DES PROPS",
    "tab.Prop": "Objets",
    "tab.Modèle": "Modèles",
    "tab.Arme": "Armes",
    "tab.Entité": "Entités",
    "size": "Taille",
    "search": "Rechercher un objet…",
    "packs": "PACKS",
    "packs.all": "Tous les packs",
    "packs.favorites": "Favoris",
    "cat.all": "Tout",
    "group.creator": "ÉQUIPABLES · DANS LE CRÉATEUR",
    "group.others": "AUTRES MODÈLES",
    "tools": "OUTILS",
    "undo": "↶ Annuler le dernier",
    "clear": "🗑 Tout supprimer",
    "close": "✕ Fermer",
    "history": "🕘 Historique",
    "history.back": "← Retour aux objets",
    "history.title": "Ton historique",
    "history.empty": "Rien n'est encore apparu.",
    "history.clear": "Vider l'historique",
    "history.equipped": "Équipé",
    "history.spawned": "Créé",
    "tip": "Clique sur un objet pour le faire apparaître devant toi, ou sur un modèle pour l'équiper. Étoile ★ : l'ajouter à tes favoris.",
    "tip.remove": "Vise un de tes props et appuie sur {0} pour le supprimer.",
    "tip.keys": "{0} ouvrir / fermer",
    "tip.esc": "{0} fermer",
    "items.one": "{0} objet",
    "items.many": "{0} objets",
    "empty": "Aucun objet trouvé",
    "loading": "Chargement du catalogue…",
    "error": "Erreur de lecture du catalogue : {0}",
    "toast.spawned": "« {0} » créé",
    "toast.equipped": "« {0} » équipé",
    "toast.undo": "Dernier objet supprimé",
    "toast.clear": "Tous tes objets supprimés",
    "toast.history": "Historique vidé",
    "language": "Langue"
  }
};

let currentLanguage = "en";

function setLanguage(code) {
  if (I18N[code]) currentLanguage = code;
  return currentLanguage;
}

function t(key, ...values) {
  let text = (I18N[currentLanguage] && I18N[currentLanguage][key]) || I18N.en[key] || key;
  values.forEach((v, i) => { text = text.split("{" + i + "}").join(v); });
  return text;
}
