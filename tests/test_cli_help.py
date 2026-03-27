from __future__ import annotations

from _pytest.capture import CaptureFixture

from biggr_cli.cli import main


def test_bare_invocation_prints_help_and_exits_zero(capsys: CaptureFixture[str]) -> None:
    exit_code = main([])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "usage:" in captured.out
    assert "tables" in captured.out


def test_top_level_help_works(capsys: CaptureFixture[str]) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "CLI wrapper for BiGGr v3 data APIs" in captured.out
