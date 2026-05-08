import ast

from moteroom.tools.check_sql import KEYWORDS, _imports_sqlite, _strings, main, run


def test_the_sql_all_lives_in_storage():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_keywords_cover_what_a_query_starts_with():
    assert "SELECT " in KEYWORDS
    assert "PRAGMA " in KEYWORDS


def test_a_sqlite_import_is_found_either_way():
    assert _imports_sqlite(ast.parse("import sqlite3\n"))
    assert _imports_sqlite(ast.parse("from sqlite3 import Row\n"))
    assert not _imports_sqlite(ast.parse("import json\n"))


def test_the_strings_of_a_module_include_the_f_string_parts():
    found = _strings(ast.parse('x = "plain"\ny = f"before {value} after"\n'))
    assert "plain" in found
    assert any("before" in one for one in found)


def test_a_query_outside_storage_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_sql as module

    bad = tmp_path / "bad.py"
    bad.write_text('rows = "SELECT 1 FROM tickets"\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "moteroom.service.bad")
    findings, _ = module.run()
    assert "writes SQL" in str(findings[0])


def test_sqlite_outside_storage_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_sql as module

    bad = tmp_path / "bad.py"
    bad.write_text("import sqlite3\n", encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "moteroom.service.bad")
    findings, _ = module.run()
    assert "outside storage" in str(findings[0])


def test_storage_itself_is_left_alone(monkeypatch, tmp_path):
    import moteroom.tools.check_sql as module

    fine = tmp_path / "fine.py"
    fine.write_text('import sqlite3\nrows = "SELECT 1"\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [fine])
    monkeypatch.setattr(module, "module_name", lambda path: "moteroom.storage.fine")
    findings, _ = module.run()
    assert findings == []
