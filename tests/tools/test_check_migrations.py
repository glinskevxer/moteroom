from moteroom.storage.migrations import MIGRATIONS
from moteroom.tools.check_migrations import EXPECTED_TABLES, main, run


def test_the_migrations_pass_their_own_gate():
    findings, checked = run()
    assert findings == []
    assert checked == len(MIGRATIONS)


def test_the_gate_exits_clean():
    assert main() == 0


def test_the_gate_knows_about_every_table_it_expects():
    assert "tickets" in EXPECTED_TABLES
    assert "season_rates" in EXPECTED_TABLES


def test_a_renumbered_migration_is_caught(monkeypatch):
    import moteroom.storage.migrations as module

    broken = (module.MIGRATIONS[1], module.MIGRATIONS[0], *module.MIGRATIONS[2:])
    monkeypatch.setattr(module, "MIGRATIONS", broken)
    findings, _ = run()
    assert findings
    assert "order" in str(findings[0])


def test_a_missing_table_is_caught(monkeypatch):
    import moteroom.tools.check_migrations as module

    monkeypatch.setattr(module, "EXPECTED_TABLES", EXPECTED_TABLES | {"ledger"})
    findings, _ = module.run()
    assert any("ledger" in str(finding) for finding in findings)


def test_a_table_the_gate_does_not_know_is_caught(monkeypatch):
    import moteroom.tools.check_migrations as module

    monkeypatch.setattr(module, "EXPECTED_TABLES", EXPECTED_TABLES - {"advances"})
    findings, _ = module.run()
    assert any("advances" in str(finding) for finding in findings)
