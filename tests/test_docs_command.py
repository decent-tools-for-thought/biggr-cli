from __future__ import annotations

from _pytest.capture import CaptureFixture

from biggr_cli.cli import main


def test_docs_command_includes_all_major_commands(capsys: CaptureFixture[str]) -> None:
    code = main(["docs"])
    out = capsys.readouterr().out

    assert code == 0
    assert "### docs" in out
    assert "### endpoint" in out
    assert "### model" in out
    assert "- model summary" in out
    assert "- model export" in out
    assert "### compare" in out
    assert "- compare models" in out
    assert "### api" in out
    assert "- api table-endpoints" in out
    assert "### doctor" in out
