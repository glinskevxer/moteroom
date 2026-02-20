import ast

from moteroom.tools.check_errors import MESSAGE_AT, _message, main, run


def call_of(text: str) -> ast.Call:
    node = ast.parse(text).body[0]
    assert isinstance(node, ast.Raise)
    assert isinstance(node.exc, ast.Call)
    return node.exc


def test_every_error_in_the_package_reads_the_same_way():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 50


def test_the_gate_exits_clean():
    assert main() == 0


def test_not_found_carries_no_message_to_check():
    assert "NotFoundError" not in MESSAGE_AT


def test_a_plain_message_reads_back():
    assert (
        _message(call_of('raise ValidationError("tare", "is too heavy")'), 1) == "is too heavy"
    )


def test_an_f_string_keeps_its_literal_parts():
    made = _message(call_of('raise ValidationError("tare", f"{value} is too heavy")'), 1)
    assert made == "{} is too heavy"


def test_a_message_nobody_wrote_reads_as_nothing():
    assert _message(call_of("raise ValidationError('tare', detail)"), 1) is None
    assert _message(call_of('raise ValidationError("tare")'), 1) is None


def test_a_capitalised_message_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_errors as module

    bad = tmp_path / "bad.py"
    bad.write_text('raise ValidationError("tare", "Is too heavy")\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert "does not start lower case" in str(findings[0])


def test_a_message_ending_in_a_full_stop_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_errors as module

    bad = tmp_path / "bad.py"
    bad.write_text('raise ValidationError("tare", "is too heavy.")\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert "full stop" in str(findings[0])


def test_an_empty_message_is_caught(monkeypatch, tmp_path):
    import moteroom.tools.check_errors as module

    bad = tmp_path / "bad.py"
    bad.write_text('raise MoteroomError("  ")\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [bad])
    monkeypatch.setattr(module, "module_name", lambda path: "bad")
    findings, _ = module.run()
    assert "empty message" in str(findings[0])


def test_a_message_that_opens_with_a_placeholder_is_allowed(monkeypatch, tmp_path):
    import moteroom.tools.check_errors as module

    good = tmp_path / "good.py"
    good.write_text(
        'raise ValidationError("tare", f"{value} is too heavy")\n', encoding="utf-8"
    )
    monkeypatch.setattr(module, "source_files", lambda: [good])
    monkeypatch.setattr(module, "module_name", lambda path: "good")
    findings, _ = module.run()
    assert findings == []


def test_an_error_this_package_does_not_raise_is_left_alone(monkeypatch, tmp_path):
    import moteroom.tools.check_errors as module

    other = tmp_path / "other.py"
    other.write_text('raise ValueError("Something.")\n', encoding="utf-8")
    monkeypatch.setattr(module, "source_files", lambda: [other])
    monkeypatch.setattr(module, "module_name", lambda path: "other")
    findings, _ = module.run()
    assert findings == []
