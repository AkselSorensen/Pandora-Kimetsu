"""Retire ou ajoute des dossiers de la liste « Autres répertoires de ressources à préparer » que Forge cuit.

Unreal : champ Cmd, py "<chemin de ce fichier>" ; le résultat est dans le journal (filtre : cuisson).

Sert à sortir les animations de la cuisson (elle est beaucoup plus courte) : les packs déjà cuits restent dans le master. Pour les
cuire de nouveau, mets-les dans ADD et relance. DefaultGame.ini est aussi modifié sur le disque ; ce script met à jour la liste
déjà chargée par l'éditeur, que Forge lit, sans devoir le redémarrer.
"""
import unreal

REMOVE = ["/Game/Katana_Animations", "/Game/Scythe"]
ADD = []


def log(message):
    unreal.log("[cuisson] " + message)


try:
    settings = unreal.get_default_object(unreal.ProjectPackagingSettings)
    current = [str(d.path) for d in settings.get_editor_property("directories_to_always_cook")]
except Exception as error:  # noqa: BLE001
    log("liste illisible (%s) : Paramètres du projet > Empaquetage > « Autres répertoires de ressources à préparer »" % error)
else:
    log("avant : %s" % current)
    wanted = [p for p in current if p not in REMOVE] + [p for p in ADD if p not in current]
    if wanted == current:
        log("rien à changer")
    else:
        settings.set_editor_property("directories_to_always_cook", [unreal.DirectoryPath(path=p) for p in wanted])
        try:
            settings.save_config()
        except Exception as error:  # noqa: BLE001
            log("liste modifiée en mémoire, mais pas enregistrée par le script (%s) : DefaultGame.ini est déjà à jour" % error)
        log("après : %s" % [str(d.path) for d in settings.get_editor_property("directories_to_always_cook")])
