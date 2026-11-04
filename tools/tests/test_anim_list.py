import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "unreal_tools" / "gen_anim_list.py"
spec = importlib.util.spec_from_file_location("gen_anim_list", SCRIPT)
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def make_pack(assets: Path, name: str, toml_body: str):
    pack = assets / name
    pack.mkdir(parents=True)
    (pack / "Assets.toml").write_text(f"[assets.animations]\n{toml_body}", encoding="utf-8")


def test_split_names_sorts_and_ignores_other_prefixes():
    seq, mon = gen.split_names(["AM_Dodge", "A_Roll", "A_Combo_02", "A_Combo_01", "SK_x", "AM_Combo_01"])
    assert seq == ["A_Combo_01", "A_Combo_02", "A_Roll"]
    assert mon == ["AM_Combo_01", "AM_Dodge"]


def test_build_lua_shape():
    text = gen.build_lua([("pk", ["A_One", "AM_One"])])
    assert text.startswith("-- Généré par")
    assert text == (
        text.splitlines()[0] + "\n"
        "return {\n"
        "\tpacks = {\n"
        "\t\t{\n"
        '\t\t\tname = "pk",\n'
        "\t\t\tsequences = {\n"
        '\t\t\t\t"A_One",\n'
        "\t\t\t},\n"
        "\t\t\tmontages = {\n"
        '\t\t\t\t"AM_One",\n'
        "\t\t\t},\n"
        "\t\t},\n"
        "\t},\n"
        "}\n"
    )


def test_build_lua_keeps_pack_order():
    text = gen.build_lua([("b", ["A_X"]), ("a", ["A_Y"])])
    assert text.index('name = "b"') < text.index('name = "a"')


def test_main_writes_every_output(tmp_path: Path):
    make_pack(tmp_path / "assets", "pk", 'A_One = "X/One"\nAM_One = "X/MOne"\n')
    a, b = tmp_path / "a" / "Animations.lua", tmp_path / "b" / "Animations.lua"
    gen.main(["--pack", "pk", "--assets", str(tmp_path / "assets"), "--out", str(a), "--out", str(b)])
    assert a.read_bytes() == b.read_bytes()
    assert b"\r\n" not in a.read_bytes() and b'"A_One"' in a.read_bytes()


def test_main_skips_pack_that_is_not_cooked_yet(tmp_path: Path, capsys):
    make_pack(tmp_path / "assets", "one", 'A_One = "X/One"\n')
    out = tmp_path / "Animations.lua"
    gen.main(["--pack", "one", "--pack", "two", "--assets", str(tmp_path / "assets"), "--out", str(out)])
    text = out.read_text(encoding="utf-8")
    assert 'name = "one"' in text and 'name = "two"' not in text
    assert "ignoré : two" in capsys.readouterr().out


def test_main_fails_when_no_pack_exists(tmp_path: Path):
    out = tmp_path / "Animations.lua"
    with pytest.raises(SystemExit):
        gen.main(["--pack", "none", "--assets", str(tmp_path), "--out", str(out)])
    assert not out.exists()
