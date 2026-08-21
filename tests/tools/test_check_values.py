import ast

from moteroom.tools.check_values import (
    DOMAIN,
    _dataclass_call,
    _is_frozen,
    _mutable_defaults,
    _package,
    main,
    run,
)


def only(text: str) -> ast.ClassDef:
    node = ast.parse(text).body[0]
    assert isinstance(node, ast.ClassDef)
    return node


def test_the_domain_is_all_values():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 40


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_domain_is_the_packages_below_storage():
    assert "core" in DOMAIN
    assert "storage" not in DOMAIN
    assert "cli" not in DOMAIN


def test_a_package_is_read_off_a_dotted_name():
    assert _package("moteroom.core.weight") == "core"
    assert _package("moteroom") == ""


def test_a_frozen_dataclass_reads_as_frozen():
    node = only("@dataclass(frozen=True)\nclass Thing:\n    a: int\n")
    call = _dataclass_call(node)
    assert call is not None
    assert _is_frozen(call)


def test_a_bare_dataclass_is_not_frozen():
    node = only("@dataclass\nclass Thing:\n    a: int\n")
    call = _dataclass_call(node)
    assert call is not None
    assert not _is_frozen(call)


def test_a_dataclass_frozen_by_a_variable_is_not_taken_on_trust():
    node = only("@dataclass(frozen=SOMETHING)\nclass Thing:\n    a: int\n")
    call = _dataclass_call(node)
    assert call is not None
    assert not _is_frozen(call)


def test_a_class_that_is_not_a_dataclass_is_left_alone():
    assert _dataclass_call(only("class Thing:\n    pass\n")) is None


def test_a_mutable_default_is_found_either_way():
    node = only("@dataclass\nclass Thing:\n    a: list = []\n    b: dict = dict()\n")
    assert _mutable_defaults(node) == ["a", "b"]


def test_an_immutable_default_is_left_alone():
    node = only('@dataclass\nclass Thing:\n    a: int = 0\n    b: str = ""\n')
    assert _mutable_defaults(node) == []


def test_an_unfrozen_dataclass_in_the_domain_would_be_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_values as module

    bad = tmp_path / "bad.py"
    bad.write_text("@dataclass\nclass Thing:\n    a: int\n", encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "moteroom.core.bad")
    findings, checked = module.run()
    assert checked == 1
    assert "not frozen" in str(findings[0])


def test_a_mutable_default_in_the_domain_would_be_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_values as module

    bad = tmp_path / "bad.py"
    bad.write_text(
        "@dataclass(frozen=True)\nclass Thing:\n    a: list = []\n", encoding="utf-8"
    )
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "moteroom.core.bad")
    findings, _ = module.run()
    assert "mutable default" in str(findings[0])
