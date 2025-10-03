from datetime import datetime

import pandas as pd

from scripts.collect_financial_frames import _normalize_statement, collect_statements


def test_normalize_statement_filters_by_period():
    idx = ["Revenue", "Cost"]
    df = pd.DataFrame(
        {
            datetime(2024, 12, 31): [100, 50],
            datetime(2025, 3, 31): [110, 55],
            datetime(2025, 6, 30): [120, None],
        },
        index=idx,
    )

    slices = list(
        _normalize_statement(
            ticker="TEST",
            statement="income_statement",
            frequency="quarterly",
            df=df,
            start=pd.Timestamp("2025-01-01"),
            end=pd.Timestamp("2025-12-31"),
        )
    )

    assert {s.period.date() for s in slices} == {
        datetime(2025, 3, 31).date(),
        datetime(2025, 6, 30).date(),
    }
    assert all(s.ticker == "TEST" for s in slices)
    assert {s.metric for s in slices} == {"Revenue", "Cost"}


def test_collect_statements_handles_empty(monkeypatch):
    class DummyTicker:
        financials = pd.DataFrame()
        balance_sheet = pd.DataFrame()
        cashflow = pd.DataFrame()
        quarterly_financials = pd.DataFrame()
        quarterly_balance_sheet = pd.DataFrame()
        quarterly_cashflow = pd.DataFrame()

    def fake_ticker(symbol):  # noqa: ARG001 - signature mimics yfinance.Ticker
        return DummyTicker()

    monkeypatch.setattr("scripts.collect_financial_frames.yf.Ticker", fake_ticker)

    df = collect_statements(["FOO"], start="2025-01-01", end="2025-12-31")
    assert df.empty
    assert list(df.columns) == ["ticker", "statement", "frequency", "metric", "period", "value"]
