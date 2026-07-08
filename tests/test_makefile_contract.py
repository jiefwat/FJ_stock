from pathlib import Path


def test_makefile_exposes_project_run_target() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    phony_line = makefile.splitlines()[0]

    assert phony_line.startswith(".PHONY:")
    assert "run" in phony_line.split()
    assert "\nrun: web\n" in makefile
    assert "python3 -m stock_ts.web" in makefile
