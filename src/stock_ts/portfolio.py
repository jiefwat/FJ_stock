from __future__ import annotations

import csv
from pathlib import Path

from .models import Holding, Transaction


def load_holdings_csv(path: str | Path, *, allow_empty: bool = False) -> list[Holding]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Holdings file not found: {csv_path}")

    holdings: list[Holding] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            code = (row.get("code") or "").strip()
            if not code:
                continue
            holdings.append(
                Holding(
                    code=code,
                    name=(row.get("name") or code).strip(),
                    shares=float(row.get("shares") or 0),
                    cost_price=float(row.get("cost_price") or 0),
                    sector=(row.get("sector") or "").strip(),
                    note=(row.get("note") or "").strip(),
                )
            )
    if not holdings and not allow_empty:
        raise ValueError(f"No holdings found in {csv_path}")
    return holdings


def load_transactions_csv(path: str | Path) -> list[Transaction]:
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Transactions file not found: {csv_path}")

    transactions: list[Transaction] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            code = (row.get("code") or "").strip()
            if not code:
                continue
            transactions.append(
                Transaction(
                    date=(row.get("date") or "").strip(),
                    code=code,
                    name=(row.get("name") or code).strip(),
                    side=_normalize_side(row.get("side") or ""),
                    shares=float(row.get("shares") or 0),
                    price=float(row.get("price") or 0),
                    fee=float(row.get("fee") or 0),
                    tax=float(row.get("tax") or 0),
                    sector=(row.get("sector") or "").strip(),
                    note=(row.get("note") or "").strip(),
                )
            )
    if not transactions:
        raise ValueError(f"No transactions found in {csv_path}")
    return transactions


def build_holdings_from_transactions(transactions: list[Transaction]) -> list[Holding]:
    lots: dict[str, dict[str, float | str]] = {}
    for transaction in transactions:
        if transaction.shares <= 0:
            continue
        entry = lots.setdefault(
            transaction.code,
            {
                "name": transaction.name,
                "shares": 0.0,
                "cost": 0.0,
                "sector": transaction.sector,
                "note": transaction.note,
            },
        )
        current_shares = float(entry["shares"])
        current_cost = float(entry["cost"])
        if transaction.side == "buy":
            entry["shares"] = current_shares + transaction.shares
            entry["cost"] = current_cost + transaction.shares * transaction.price
        elif transaction.side == "sell":
            average_cost = current_cost / current_shares if current_shares else transaction.price
            sell_shares = min(transaction.shares, current_shares)
            entry["shares"] = current_shares - sell_shares
            entry["cost"] = current_cost - sell_shares * average_cost
        entry["name"] = transaction.name or str(entry["name"])
        entry["sector"] = transaction.sector or str(entry["sector"])
        entry["note"] = transaction.note or str(entry["note"])

    holdings = []
    for code, entry in lots.items():
        shares = float(entry["shares"])
        if shares <= 0:
            continue
        cost = float(entry["cost"])
        holdings.append(
            Holding(
                code=code,
                name=str(entry["name"]),
                shares=shares,
                cost_price=cost / shares if shares else 0.0,
                sector=str(entry["sector"]),
                note=str(entry["note"]),
            )
        )
    if not holdings:
        raise ValueError("No open holdings found in transactions")
    return holdings


def load_portfolio_source(
    *,
    holdings_path: str | Path | None = None,
    transactions_path: str | Path | None = None,
    allow_empty: bool = False,
) -> list[Holding]:
    if transactions_path is not None:
        return build_holdings_from_transactions(load_transactions_csv(transactions_path))
    if holdings_path is None:
        raise ValueError("Either holdings_path or transactions_path is required")
    return load_holdings_csv(holdings_path, allow_empty=allow_empty)


def upsert_holding_csv(path: str | Path, holding: Holding) -> str:
    csv_path = Path(path)
    existing = _load_holdings_for_write(csv_path)
    action = "added"
    replaced = False
    for index, item in enumerate(existing):
        if item.code == holding.code:
            existing[index] = holding
            action = "updated"
            replaced = True
            break
    if not replaced:
        existing.append(holding)
    _write_holdings_csv(csv_path, existing)
    return action


def delete_holding_csv(path: str | Path, code: str) -> None:
    csv_path = Path(path)
    existing = _load_holdings_for_write(csv_path)
    remaining = [item for item in existing if item.code != code]
    if len(remaining) == len(existing):
        raise ValueError(f"持仓文件中未找到股票代码 {code}")
    if not remaining:
        raise ValueError("至少保留一条持仓记录；如需重置，请直接替换持仓 CSV。")
    _write_holdings_csv(csv_path, remaining)


def _normalize_side(value: str) -> str:
    normalized = value.strip().lower()
    if normalized in {"buy", "b", "买入", "买"}:
        return "buy"
    if normalized in {"sell", "s", "卖出", "卖"}:
        return "sell"
    raise ValueError(f"Unsupported transaction side: {value}")


def _load_holdings_for_write(path: Path) -> list[Holding]:
    if not path.exists():
        return []
    try:
        return load_holdings_csv(path)
    except ValueError:
        return []


def _write_holdings_csv(path: Path, holdings: list[Holding]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["code", "name", "shares", "cost_price", "sector", "note"],
        )
        writer.writeheader()
        for holding in holdings:
            writer.writerow(
                {
                    "code": holding.code,
                    "name": holding.name,
                    "shares": _format_number(holding.shares),
                    "cost_price": _format_number(holding.cost_price),
                    "sector": holding.sector,
                    "note": holding.note,
                }
            )


def _format_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")
