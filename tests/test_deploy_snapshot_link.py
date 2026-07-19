from __future__ import annotations

import json
import subprocess
from pathlib import Path


def test_deployed_snapshot_follows_atomic_upstream_refresh(tmp_path: Path) -> None:
    source = tmp_path / "runtime" / "tdx_snapshots.json"
    target = tmp_path / "aster" / "market_snapshot.json"
    source.parent.mkdir()
    source.write_text(json.dumps({"trade_date": "2026-07-17"}), encoding="utf-8")

    subprocess.run(
        ["sh", "deploy/link-live-snapshot.sh", str(source), str(target)],
        check=True,
    )

    replacement = source.with_suffix(".staging")
    replacement.write_text(json.dumps({"trade_date": "2026-07-18"}), encoding="utf-8")
    replacement.replace(source)

    assert target.is_symlink()
    assert json.loads(target.read_text(encoding="utf-8"))["trade_date"] == "2026-07-18"
