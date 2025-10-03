"""Utilities to bundle statement data for a list of tickers into CSV slices.

This script mirrors the ticker loading behaviour from ``build_statements.py`` but
shapes the yfinance payloads into a tidy ``pandas`` DataFrame.  It is designed to
run in GitHub Actions where the resulting CSV slices can be uploaded as
artifacts.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class StatementSlice:
    ticker: str
    statement: str
    frequency: str
    metric: str
    period: pd.Timestamp
    value: float


def _load_tickers(csv_path: Path, limit: int | None = None) -> list[str]:
    lines = [x.strip().upper() for x in csv_path.read_text().splitlines()]
    tickers = [x for x in lines if x and not x.startswith("#")]
    if limit is not None:
        return tickers[:limit]
    return tickers


def _normalize_statement(
    ticker: str,
    statement: str,
    frequency: str,
    df: pd.DataFrame | None,
    start: pd.Timestamp | None,
    end: pd.Timestamp | None,
) -> Iterable[StatementSlice]:
    if df is None or df.empty:
        return []

    normalized = []
    # Some yfinance frames use DatetimeIndex columns, others strings; coerce to Timestamp.
    for raw_period, series in df.items():
        period = pd.to_datetime(raw_period)
        if start is not None and period < start:
            continue
        if end is not None and period > end:
            continue
        for metric, value in series.dropna().items():
            normalized.append(
                StatementSlice(
                    ticker=ticker,
                    statement=statement,
                    frequency=frequency,
                    metric=str(metric),
                    period=period,
                    value=float(value),
                )
            )
    return normalized


def collect_statements(
    tickers: Iterable[str],
    start: str | None = None,
    end: str | None = None,
) -> pd.DataFrame:
    """Return a tidy DataFrame of statement slices for the provided tickers."""

    start_ts = pd.to_datetime(start) if start else None
    end_ts = pd.to_datetime(end) if end else None

    records: list[StatementSlice] = []
    for ticker in tickers:
        t = yf.Ticker(ticker)
        records.extend(
            _normalize_statement(
                ticker,
                "income_statement",
                "annual",
                t.financials,
                start_ts,
                end_ts,
            )
        )
        records.extend(
            _normalize_statement(
                ticker,
                "balance_sheet",
                "annual",
                t.balance_sheet,
                start_ts,
                end_ts,
            )
        )
        records.extend(
            _normalize_statement(
                ticker,
                "cash_flow",
                "annual",
                t.cashflow,
                start_ts,
                end_ts,
            )
        )

        records.extend(
            _normalize_statement(
                ticker,
                "income_statement",
                "quarterly",
                t.quarterly_financials,
                start_ts,
                end_ts,
            )
        )
        records.extend(
            _normalize_statement(
                ticker,
                "balance_sheet",
                "quarterly",
                t.quarterly_balance_sheet,
                start_ts,
                end_ts,
            )
        )
        records.extend(
            _normalize_statement(
                ticker,
                "cash_flow",
                "quarterly",
                t.quarterly_cashflow,
                start_ts,
                end_ts,
            )
        )

    if not records:
        return pd.DataFrame(
            columns=["ticker", "statement", "frequency", "metric", "period", "value"]
        )

    df = pd.DataFrame([r.__dict__ for r in records])
    df["period"] = pd.to_datetime(df["period"], utc=True)
    return df


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect ticker statements and emit per-slice CSV files"
    )
    parser.add_argument("--tickers-csv", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=None, help="Number of tickers to load")
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Inclusive period start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="Inclusive period end (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        required=True,
        help="Directory where CSV slices will be written",
    )

    args = parser.parse_args()
    tickers = _load_tickers(args.tickers_csv, args.limit)
    df = collect_statements(tickers, start=args.start, end=args.end)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    # Materialize each (statement, frequency) slice into its own CSV to make
    # downstream artifact uploads easier to target.
    ordered_columns = ["ticker", "statement", "frequency", "metric", "period", "value"]
    statement_frequencies = (
        ("income_statement", "annual"),
        ("balance_sheet", "annual"),
        ("cash_flow", "annual"),
        ("income_statement", "quarterly"),
        ("balance_sheet", "quarterly"),
        ("cash_flow", "quarterly"),
    )

    for statement, frequency in statement_frequencies:
        slice_df = df.loc[
            (df["statement"] == statement) & (df["frequency"] == frequency),
            ordered_columns,
        ].copy()
        if not slice_df.empty:
            slice_df = slice_df.sort_values(["ticker", "period", "metric"])  # stable order
        out_path = args.out_dir / f"{statement}_{frequency}.csv"
        slice_df.to_csv(out_path, index=False)


if __name__ == "__main__":
    main()
