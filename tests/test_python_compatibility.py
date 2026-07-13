from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_research_evidence_imports_on_supported_python() -> None:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from stock_ts.research.evidence import EvidenceStatus; "
            "print(str(EvidenceStatus.COMPLETE))",
        ],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "complete"
