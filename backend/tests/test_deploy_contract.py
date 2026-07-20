from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_production_service_runs_marketdesk_on_public_proxy_port() -> None:
    service = (ROOT / "deploy" / "stock-ts.service").read_text(encoding="utf-8")

    assert "WorkingDirectory=/opt/aster-market/current" in service
    assert "Environment=PYTHONPATH=/opt/aster-market/current/backend/src" in service
    assert "ExecStart=/opt/aster-market/current/.venv/bin/python -m uvicorn marketdesk.api:app --host 127.0.0.1 --port 8501" in service


def test_deploy_script_uses_local_frontend_build_and_atomic_current_switch() -> None:
    script = (ROOT / "deploy" / "deploy_public.sh").read_text(encoding="utf-8")

    assert "pnpm --dir \"$ROOT/frontend\" build" in script
    assert "rsync" in script
    assert "ln -sfn" in script
    assert "/opt/aster-market/current" in script
    assert "systemctl restart stock-ts.service" in script


def test_production_service_enables_two_hour_market_refresh() -> None:
    service = (ROOT / "deploy" / "stock-ts.service").read_text(encoding="utf-8")

    assert "Environment=MARKETDESK_AUTO_REFRESH_ENABLED=true" in service
    assert "Environment=MARKETDESK_AUTO_REFRESH_INTERVAL_SECONDS=7200" in service
