import click

from moteroom.tools.check_cli import commands, main_gate, run


def test_every_command_says_what_it_is_for():
    findings, checked = run()
    assert findings == [], "\n".join(str(finding) for finding in findings)
    assert checked > 20


def test_the_gate_exits_clean():
    assert main_gate() == 0


def test_the_tree_reaches_the_leaves():
    paths = [path for path, _ in commands()]
    assert "ticket weigh" in paths
    assert "report exceptions" in paths
    assert "" in paths


def test_a_command_with_no_help_is_caught(monkeypatch):
    import moteroom.tools.check_cli as module

    @click.command("bare")
    def bare() -> None:
        pass

    monkeypatch.setattr(module, "commands", lambda: [("bare", bare)])
    findings, _ = module.run()
    assert "has no help" in str(findings[0])


def test_an_option_with_no_help_is_caught(monkeypatch):
    import moteroom.tools.check_cli as module

    @click.command("thin")
    @click.option("--quiet", is_flag=True)
    def thin(quiet: bool) -> None:
        """Do a thing worth doing."""

    monkeypatch.setattr(module, "commands", lambda: [("thin", thin)])
    findings, _ = module.run()
    assert "--quiet" in str(findings[0])


def test_an_argument_does_not_need_help(monkeypatch):
    import moteroom.tools.check_cli as module

    @click.command("taking")
    @click.argument("what")
    def taking(what: str) -> None:
        """Do a thing worth doing."""

    monkeypatch.setattr(module, "commands", lambda: [("taking", taking)])
    findings, _ = module.run()
    assert findings == []


def test_a_command_spelled_oddly_is_caught(monkeypatch):
    import moteroom.tools.check_cli as module

    @click.command("Weigh_In")
    def odd() -> None:
        """Do a thing worth doing."""

    monkeypatch.setattr(module, "commands", lambda: [("Weigh_In", odd)])
    findings, _ = module.run()
    assert "not spelled" in str(findings[0])


def test_an_empty_group_is_caught(monkeypatch):
    import moteroom.tools.check_cli as module

    @click.group("hollow")
    def hollow() -> None:
        """Do a thing worth doing."""

    monkeypatch.setattr(module, "commands", lambda: [("hollow", hollow)])
    findings, _ = module.run()
    assert "nothing under it" in str(findings[0])
