"""Teste unreal_tools/import_scythe_pack.py et lock_root_motion.py avec un module `unreal` factice."""
import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "unreal_tools"
ROOT = "/Game/Scythe"
SEQ = ROOT + "/Animation/Sequence"
NANOS_DIR = ROOT + "/Nanos"
SKEL = "/Game/NanosWorld/Characters/Common/SKEL_Mannequin"
NANOS_MESH = "/Game/NanosWorld/Characters/Mannequin/SK_Mannequin"
UE5_MESH = ROOT + "/Demo/Characters/Mannequins/Meshes/SKM_Manny"
UE4_MESH = ROOT + "/Demo/Characters/Mannequin_UE4/Meshes/SK_Mannequin"
RTG = ROOT + "/Demo/Characters/Mannequin_UE4/Rigs/RTG_UE5Manny_UE4Manny"

ANIMATIONS = [
    f"{SEQ}/02_Attack/01_Combo_Attack_01/AS_Combo_Attack_01_01_Seq",
    f"{SEQ}/02_Attack/01_Combo_Attack_01/AS_Combo_Attack_All_Seq",
    f"{SEQ}/02_Attack/02_Combo_Attack_02/AS_Combo_Attack_All_Seq",
    f"{SEQ}/06_Dodge/01_Dodge/02_IP/AS_Dodge_F_0_Seq",
    f"{SEQ}/08_Hit/01_Hit/AS_Hit_01_Seq",
]


class Asset:
    def __init__(self, skeleton=None):
        self.skeleton = skeleton
        self.props = {}

    def get_editor_property(self, name):
        return self.skeleton if name == "skeleton" else self.props.get(name)

    def set_editor_property(self, name, value):
        if name == "skeleton":
            raise Exception("propriété protégée")  # Unreal 5.7 : le squelette est en lecture seule
        self.props[name] = value


class Props:
    def __init__(self):
        self.props = {}

    def set_editor_property(self, name, value):
        self.props[name] = value


class Fake:
    def __init__(self, tmp_path, animations=ANIMATIONS, direct_fails=False, retarget_nothing=False, extra_assets=()):
        self.nanos_skel, self.ue4_skel = Asset("nanos"), Asset("ue4")
        self.assets = {SKEL: self.nanos_skel, NANOS_MESH: Asset(self.nanos_skel), UE4_MESH: Asset(self.ue4_skel),
                       UE5_MESH: Asset(Asset("ue5")), RTG: Asset()}
        for package in animations:
            self.assets[package] = Asset(Asset("ue5"))
        for name in ("Scythe", "M_Asset", "SKM_Manny_extra"):
            self.assets[f"{ROOT}/Demo/{name}"] = Asset()
        for package in extra_assets:
            self.assets[package] = Asset(self.nanos_skel)
        self.content = tmp_path / "Content"
        self.direct_fails, self.retarget_nothing = direct_fails, retarget_nothing
        self.deleted, self.logs = [], []
        fake = self

        def data(package):
            kind = "AnimSequence" if (package.startswith(SEQ) or "/Nanos/" in package or "/Katana_Animations/" in package) else "StaticMesh"
            return SimpleNamespace(asset_class_path=SimpleNamespace(asset_name=kind), package_name=package,
                                   asset_name=package.rsplit("/", 1)[1])

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
            def delete_asset(p):
                fake.assets.pop(p, None)
                return True

            @staticmethod
            def delete_directory(d):
                for p in [p for p in fake.assets if p.startswith(d + "/")]:
                    del fake.assets[p]
                fake.deleted.append(d)
                return True

        class Registry:
            scan_paths_synchronous = staticmethod(lambda paths, recursive: None)
            get_assets_by_path = staticmethod(
                lambda path, recursive=True: [data(p) for p in sorted(fake.assets) if p.startswith(path + "/")])

        class Batch:
            @staticmethod
            def duplicate_and_retarget(datas, source, target, retargeter, search, replace, prefix, suffix, incl, overwrite):
                if fake.retarget_nothing or (fake.direct_fails and target is fake.assets[NANOS_MESH]):
                    return []
                created = []
                for d in datas:
                    folder, name = str(d.package_name).rsplit("/", 1)
                    new = f"/Game/{prefix}{name}"  # comme Unreal : à la racine de /Game, pas à côté de l'original
                    while new in fake.assets:
                        new += "_1"
                    fake.assets[new] = Asset(target.skeleton)
                    created.append(data(new))
                return created

        class Exporter:
            @staticmethod
            def run_asset_export_task(task):
                Path(task.filename).write_bytes(b"fbx")

        class Tools:
            @staticmethod
            def import_asset_tasks(tasks):
                for t in tasks:
                    fake.assets[f"{t.destination_path}/{t.destination_name}"] = Asset(t.options.props["skeleton"])
                raise RuntimeError("Impossible de récupérer l'index des os pour la piste: Katana_weapon_01")

        m = types.ModuleType("unreal")
        m.FAKE_FOR_TESTS = True
        m.EditorAssetLibrary = Eal
        m.AssetRegistryHelpers = SimpleNamespace(get_asset_registry=lambda: Registry)
        m.AssetToolsHelpers = SimpleNamespace(get_asset_tools=lambda: Tools)
        m.IKRetargetBatchOperation = Batch
        m.Paths = SimpleNamespace(project_content_dir=lambda: str(self.content) + "/")
        m.log = self.logs.append
        m.AssetExportTask = lambda: SimpleNamespace()
        m.Exporter = Exporter
        m.FbxImportUI = lambda: Props()
        m.AssetImportTask = lambda: SimpleNamespace()
        m.FBXImportType = SimpleNamespace(FBXIT_ANIMATION="anim")
        self.module = m


def load(script, fake):
    sys.modules["unreal"] = fake.module
    spec = importlib.util.spec_from_file_location(script, TOOLS / f"{script}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scythe(tmp_path, **kwargs):
    fake = Fake(tmp_path, **kwargs)
    mod = load("import_scythe_pack", fake)
    source = tmp_path / "source"
    for rel in ("Animation/Sequence/02_Attack/a.uasset", "Animation/Sequence/03_Walk/w.uasset",
                "Animation/Sequence/06_Dodge/01_Dodge/01_RM/AS_Dodge_F_0_Seq.uasset",
                "Animation/Sequence/06_Dodge/01_Dodge/02_IP/AS_Dodge_F_0_Seq.uasset",
                "Demo/Maps/Demo_Map.umap", "Demo/Material/M_Floor.uasset", "Demo/Material/M_Asset.uasset",
                "Demo/Characters/Mannequins/Meshes/SKM_Manny.uasset", "Demo/Characters/Mannequins/Meshes/SKM_Quinn.uasset",
                "Demo/Characters/Mannequins/Textures/Quinn/T_Quinn.uasset", ".DS_Store"):
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


def finals(fake):
    return sorted(p.rsplit("/", 1)[1] for p in fake.assets if p.startswith(NANOS_DIR + "/"))


def test_names_and_filters(tmp_path):
    mod, _ = scythe(tmp_path)
    assert mod.pack_slug("Scythe") == "scythe"
    names = mod.unique_names([("02_Attack/01_Combo_Attack_01", "AS_Combo_Attack_All_Seq"),
                              ("02_Attack/02_Combo_Attack_02", "AS_Combo_Attack_All_Seq")])
    assert sorted(names.values()) == ["Combo_Attack_All", "Combo_Attack_All_Combo_Attack_02"]
    assert not mod.keep_source("Animation/Sequence/06_Dodge/01_Dodge/01_RM/AS_Dodge_F_0_Seq.uasset")
    assert mod.keep_source("Animation/Sequence/06_Dodge/01_Dodge/02_IP/AS_Dodge_F_0_Seq.uasset")
    assert not mod.keep_source("Animation/Sequence/03_Walk/01_Walk/AS_Walk_Seq.uasset")
    assert not mod.keep_source("Demo/Characters/Mannequins/Meshes/SKM_Quinn.uasset")


def test_copy_skips_root_motion_unused_groups_map_floor_quinn_and_dotfiles(tmp_path):
    mod, fake = scythe(tmp_path)
    mod.copy_pack()
    base = fake.content / "Scythe"
    copied = sorted(p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())
    assert copied == [
        "Animation/Sequence/02_Attack/a.uasset",
        "Animation/Sequence/06_Dodge/01_Dodge/02_IP/AS_Dodge_F_0_Seq.uasset",
        "Demo/Characters/Mannequins/Meshes/SKM_Manny.uasset",
        "Demo/Material/M_Asset.uasset",
    ]


def test_trial_run_retargets_three_with_locked_root_and_keeps_everything(tmp_path):
    mod, fake = scythe(tmp_path)
    mod.LIMIT = 3
    mod.main()
    assert finals(fake) == ["A_Scythe_Combo_Attack_01_01", "A_Scythe_Combo_Attack_All", "A_Scythe_Combo_Attack_All_Combo_Attack_02"]
    for p in fake.assets:
        if p.startswith(NANOS_DIR + "/"):
            assert fake.assets[p].get_editor_property("skeleton") is fake.nanos_skel
            assert fake.assets[p].props == {"enable_root_motion": False, "force_root_lock": True}
    assert fake.deleted == []
    assert all(p in fake.assets for p in ANIMATIONS)  # les originaux restent tant que l'essai n'est pas terminé
    assert not any(p.startswith("/Game/RT_") for p in fake.assets)  # les copies temporaires ont été rangées


def test_full_run_cleans_up_and_is_idempotent(tmp_path):
    mod, fake = scythe(tmp_path)
    mod.LIMIT = None
    mod.main()
    assert len(finals(fake)) == 5
    assert not any(p.startswith("/Game/RT_") for p in fake.assets)
    assert sorted(p for p in fake.assets if p.startswith(ROOT + "/Meshes/")) == [f"{ROOT}/Meshes/M_Asset", f"{ROOT}/Meshes/Scythe"]
    assert not any(p.startswith((ROOT + "/Demo/", ROOT + "/Animation/")) for p in fake.assets)
    before = dict(fake.assets)
    mod.main()
    assert fake.assets == before


def test_falls_back_to_ue4_mesh_then_fbx_roundtrip(tmp_path):
    mod, fake = scythe(tmp_path, direct_fails=True)
    mod.LIMIT = 3
    mod.main()
    assert len(finals(fake)) == 3
    assert all(fake.assets[f"{NANOS_DIR}/{n}"].get_editor_property("skeleton") is fake.nanos_skel for n in finals(fake))
    assert any("aucune animation produite" in m for m in fake.logs)
    assert any("avertissement d'import ignoré" in m for m in fake.logs)
    assert not any("ÉCHEC" in m for m in fake.logs)


def test_no_retarget_result_stops_before_cleanup(tmp_path):
    mod, fake = scythe(tmp_path, retarget_nothing=True)
    mod.LIMIT = None
    mod.main()
    assert fake.deleted == [] and finals(fake) == []
    assert all(p in fake.assets for p in ANIMATIONS)
    assert any("échec(s)" in m for m in fake.logs)


def test_root_motion_script_locks_most_and_keeps_movement_for_dodge_and_roll(tmp_path):
    base = "/Game/Katana_Animations/Nanos/"
    extra = [base + "A_Combo_Attack_01", base + "A_Dodge_F_0", base + "A_Roll_B", base + "A_Run_Attack_01", base + "A_Hit_Light"]
    fake = Fake(tmp_path, animations=[], extra_assets=extra)
    mod = load("lock_root_motion", fake)
    mod.main()  # /Game/Scythe/Nanos n'existe pas : ignoré
    in_place = {"enable_root_motion": False, "force_root_lock": True}
    moving = {"enable_root_motion": True, "force_root_lock": False}
    assert fake.assets[base + "A_Combo_Attack_01"].props == in_place
    assert fake.assets[base + "A_Hit_Light"].props == in_place
    for name in ("A_Dodge_F_0", "A_Roll_B", "A_Run_Attack_01"):
        assert fake.assets[base + name].props == moving
    assert any("absent, ignoré" in m for m in fake.logs)
    assert any("Terminé : 2 sur place, 3 avec déplacement" in m for m in fake.logs)


def test_root_motion_script_can_keep_everything_in_place(tmp_path):
    base = "/Game/Katana_Animations/Nanos/"
    fake = Fake(tmp_path, animations=[], extra_assets=[base + "A_Dodge_F_0"])
    mod = load("lock_root_motion", fake)
    mod.MOVING = ()
    mod.main()
    assert fake.assets[base + "A_Dodge_F_0"].props == {"enable_root_motion": False, "force_root_lock": True}
