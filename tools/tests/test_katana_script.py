"""Teste unreal_tools/import_katana_pack.py avec un module `unreal` factice (l'éditeur n'est pas disponible ici)."""
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "unreal_tools" / "import_katana_pack.py"
ROOT = "/Game/Katana_Animations"
SEQ = ROOT + "/Animations/Sequence"
SKEL = "/Game/NanosWorld/Characters/Common/SKEL_Mannequin"


class Asset:
    def __init__(self, skeleton=None):
        self.skeleton = skeleton

    def get_editor_property(self, name):
        assert name == "skeleton"
        return self.skeleton

    def set_editor_property(self, name, value):
        raise Exception("propriété protégée")  # Unreal 5.7 refuse l'assignation directe du squelette


class Props:
    def __init__(self, **kw):
        self.props = dict(kw)

    def set_editor_property(self, name, value):
        self.props[name] = value


class Fake:
    """Module `unreal` factice : un dictionnaire de chemins -> assets suffit pour suivre le script."""

    def __init__(self, tmp_path, animations, export_works=True):
        self.assets = {SKEL: Asset("nanos")}
        self.skeleton = self.assets[SKEL]
        for package in animations:
            self.assets[package] = Asset("ue4")
        for name in ("M_Katana", "Katana_sword", "Katana_sheath", "SK_Mannequin"):
            self.assets[f"{ROOT}/Demo/{name}"] = Asset()
        self.content = tmp_path / "Content"
        self.export_works = export_works
        self.montage_error = None
        self.import_warning = False
        self.deleted = []
        self.logs = []
        fake = self

        class Eal:
            load_asset = staticmethod(lambda p: fake.assets.get(p))
            does_asset_exist = staticmethod(lambda p: p in fake.assets)
            does_directory_exist = staticmethod(lambda d: any(p.startswith(d + "/") for p in fake.assets))
            save_asset = staticmethod(lambda p, *a: True)
            make_directory = staticmethod(lambda d: True)

            @staticmethod
            def rename_asset(src, dst):
                fake.assets[dst] = fake.assets.pop(src)
                return True

            @staticmethod
            def delete_directory(d):
                for p in [p for p in fake.assets if p.startswith(d + "/")]:
                    del fake.assets[p]
                fake.deleted.append(d)
                return True

        class Registry:
            scan_paths_synchronous = staticmethod(lambda paths, recursive: None)

            @staticmethod
            def get_assets_by_path(path, recursive=True):
                out = []
                for package, asset in fake.assets.items():
                    if package.startswith(path + "/"):
                        kind = "AnimSequence" if package.startswith(SEQ) else "StaticMesh"
                        out.append(SimpleNamespace(asset_class_path=SimpleNamespace(asset_name=kind),
                                                   package_name=package, asset_name=package.rsplit("/", 1)[1]))
                return out

        class Exporter:
            @staticmethod
            def run_asset_export_task(task):
                if fake.export_works:
                    Path(task.filename).write_bytes(b"fbx")

        class Tools:
            @staticmethod
            def import_asset_tasks(tasks):
                for t in tasks:
                    fake.assets[f"{t.destination_path}/{t.destination_name}"] = Asset(t.options.props["skeleton"])
                if fake.import_warning:  # Unreal lève une exception alors que l'asset est bien créé
                    raise RuntimeError("Impossible de récupérer l'index des os pour la piste: Katana_weapon_01")

            @staticmethod
            def create_asset(name, folder, cls, factory):
                if fake.montage_error:
                    raise fake.montage_error
                fake.assets[f"{folder}/{name}"] = Asset(factory.props["target_skeleton"])
                return fake.assets[f"{folder}/{name}"]

        self.module = types.ModuleType("unreal")
        m = self.module
        m.FAKE_FOR_TESTS = True
        m.EditorAssetLibrary = Eal
        m.AssetRegistryHelpers = SimpleNamespace(get_asset_registry=lambda: Registry)
        m.AssetToolsHelpers = SimpleNamespace(get_asset_tools=lambda: Tools)
        m.Paths = SimpleNamespace(project_content_dir=lambda: str(self.content) + "/")
        m.log = self.logs.append
        m.AssetExportTask = lambda: SimpleNamespace()
        m.Exporter = Exporter
        m.FbxImportUI = lambda: Props()
        m.AssetImportTask = lambda: SimpleNamespace()
        m.FBXImportType = SimpleNamespace(FBXIT_ANIMATION="anim")
        m.AnimMontageFactory = lambda: Props()
        m.AnimMontage = object


ANIMATIONS = [
    f"{SEQ}/02_Attack/01_Combo_Attack_01/AS_Combo_Attack_01_Seq",
    f"{SEQ}/02_Attack/01_Combo_Attack_01/AS_Combo_Attack_All_Seq",
    f"{SEQ}/02_Attack/02_Combo_Attack_02/AS_Combo_Attack_All_Seq",
    f"{SEQ}/06_Dodge/AS_Dodge_F_Seq",
    f"{SEQ}/08_Hit/AS_Hit_Light_Seq",
]


def load(tmp_path, animations=ANIMATIONS, export_works=True):
    fake = Fake(tmp_path, animations, export_works)
    sys.modules["unreal"] = fake.module
    spec = importlib.util.spec_from_file_location("import_katana_pack", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    source = tmp_path / "source"
    for rel in ("Animations/Sequence/02_Attack/a.uasset", "Animations/Sequence/03_Walk/w.uasset",
                "Demo/Maps/Demo_map.umap", "Demo/Material/M_Floor.uasset", "Demo/Material/M_Katana.uasset", ".DS_Store"):
        (source / rel).parent.mkdir(parents=True, exist_ok=True)
        (source / rel).write_bytes(b"x")
    mod.SOURCE = str(source)
    return mod, fake


@pytest.fixture(autouse=True)
def _restore_unreal():
    saved = sys.modules.get("unreal")
    yield
    if saved is None:
        sys.modules.pop("unreal", None)
    else:
        sys.modules["unreal"] = saved


def test_names(tmp_path):
    mod, _ = load(tmp_path)
    assert mod.seq_base("AS_Combo_Attack_01_Seq") == "Combo_Attack_01"
    assert mod.folder_tag("02_Attack/02_Combo_Attack_02") == "Combo_Attack_02"
    assert mod.pack_slug("Katana_Animations") == "katana-animations"
    assert mod.pack_slug("YufuPmVaasContent") == "yufu-pm-vaas-content"
    names = mod.unique_names([("02_Attack/01_Combo_Attack_01", "AS_Combo_Attack_All_Seq"),
                              ("02_Attack/02_Combo_Attack_02", "AS_Combo_Attack_All_Seq")])
    assert sorted(names.values()) == ["Combo_Attack_All", "Combo_Attack_All_Combo_Attack_02"]


def test_copy_filters_groups_map_floor_and_dotfiles(tmp_path):
    mod, fake = load(tmp_path)
    mod.copy_pack()
    copied = sorted(p.relative_to(fake.content / "Katana_Animations").as_posix()
                    for p in (fake.content / "Katana_Animations").rglob("*") if p.is_file())
    assert copied == ["Animations/Sequence/02_Attack/a.uasset", "Demo/Material/M_Katana.uasset"]


def test_trial_run_converts_three_and_keeps_everything(tmp_path):
    mod, fake = load(tmp_path)
    mod.LIMIT = 3
    mod.main()
    nanos = [p for p in fake.assets if p.startswith(ROOT + "/Nanos/")]
    montages = [p for p in fake.assets if p.startswith(ROOT + "/Montages/")]
    assert len(nanos) == 3 and len(montages) == 3
    assert all(fake.assets[p].skeleton is fake.skeleton for p in nanos + montages)
    assert fake.deleted == []  # essai : aucun nettoyage
    assert all(p in fake.assets for p in ANIMATIONS)


def test_full_run_cleans_up_and_is_idempotent(tmp_path):
    mod, fake = load(tmp_path)
    mod.LIMIT = None
    mod.main()
    nanos = sorted(p.rsplit("/", 1)[1] for p in fake.assets if p.startswith(ROOT + "/Nanos/"))
    assert nanos == ["A_Combo_Attack_01", "A_Combo_Attack_All", "A_Combo_Attack_All_Combo_Attack_02", "A_Dodge_F", "A_Hit_Light"]
    assert len([p for p in fake.assets if p.startswith(ROOT + "/Montages/")]) == 5
    assert sorted(p for p in fake.assets if p.startswith(ROOT + "/Meshes/")) == [
        f"{ROOT}/Meshes/Katana_sheath", f"{ROOT}/Meshes/Katana_sword", f"{ROOT}/Meshes/M_Katana"]
    assert not any(p.startswith((ROOT + "/Demo/", ROOT + "/Animations/")) for p in fake.assets)
    before = dict(fake.assets)
    mod.main()  # deuxième passage : rien à refaire
    assert fake.assets == before


def test_montage_error_is_logged_and_other_animations_continue(tmp_path):
    mod, fake = load(tmp_path)
    fake.montage_error = AttributeError("pas de fabrique de montage")
    mod.LIMIT = 3
    mod.main()
    assert len([p for p in fake.assets if p.startswith(ROOT + "/Nanos/")]) == 3  # le squelette est changé pour les 3
    errors = [m for m in fake.logs if "ÉCHEC" in m]
    assert len(errors) == 3 and "AttributeError: pas de fabrique de montage" in errors[0]
    assert fake.deleted == []
    # relance après correction : les animations déjà converties ne sont pas refaites, les montages sont créés
    fake.montage_error = None
    mod.main()
    assert len([p for p in fake.assets if p.startswith(ROOT + "/Montages/")]) == 3


def test_import_warning_exception_is_not_a_failure(tmp_path):
    mod, fake = load(tmp_path)
    fake.import_warning = True
    mod.LIMIT = 3
    mod.main()
    assert len([p for p in fake.assets if p.startswith(ROOT + "/Nanos/")]) == 3
    assert len([p for p in fake.assets if p.startswith(ROOT + "/Montages/")]) == 3
    assert not any("ÉCHEC" in m for m in fake.logs)
    assert any("avertissement d'import ignoré" in m for m in fake.logs)


def test_failed_export_stops_before_cleanup(tmp_path):
    mod, fake = load(tmp_path, export_works=False)
    mod.LIMIT = None
    mod.main()
    assert fake.deleted == []
    assert all(p in fake.assets for p in ANIMATIONS)
