import pandas as pd

import scripts.build_statements as mod


class FakeTicker:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.fast_info = type(
            "FastInfo",
            (),
            {"currency": "USD", "exchange": "NMS", "shortName": "Fake Inc"},
        )()
        df = pd.DataFrame(
            {"2023-12-31": [100, 50], "2022-12-31": [90, 45]},
            index=["Total Revenue", "Net Income"],
        )
        self.financials = df
        self.balance_sheet = pd.DataFrame(
            {"2023-12-31": [300, 200, 100]},
            index=["Total Assets", "Total Liab", "Total Stockholder Equity"],
        )
        self.cashflow = pd.DataFrame({"2023-12-31": [50]}, index=["Net Income"])
        self.quarterly_financials = df
        self.quarterly_balance_sheet = self.balance_sheet
        self.quarterly_cashflow = self.cashflow


def test_df_to_period_dict_basic():
    df = pd.DataFrame({"2023-12-31": [1, 2]}, index=["A", "B"])
    got = mod.df_to_period_dict(df)
    assert "2023-12-31" in got
    assert got["2023-12-31"]["A"] == 1


def test_fetch_statements_monkeypatch(monkeypatch):
    monkeypatch.setattr(mod.yf, "Ticker", lambda s: FakeTicker(s))
    payload = mod.fetch_statements("AAPL", retries=1)
    assert payload["meta"]["symbol"] == "AAPL"
    assert "annual" in payload["statements"]


def test_write_and_manifest(monkeypatch, tmp_path):
    monkeypatch.setattr(mod.yf, "Ticker", lambda s: FakeTicker(s))
    out = tmp_path / "data"
    csv = tmp_path / "tickers.csv"
    csv.write_text("AAPL\nMSFT\n")

    tickets = mod.load_tickers(csv)
    assert tickets == ["AAPL", "MSFT"]

    payload = mod.fetch_statements("AAPL", retries=1)
    changed = mod.write_if_changed(out / "AAPL.json", payload)
    assert changed

    changed2 = mod.write_if_changed(out / "AAPL.json", payload)
    assert not changed2


def test_load_tickers_skips_comments(tmp_path):
    csv = tmp_path / "fortune_1000_plus_tech_firms.csv"
    csv.write_text("# comment\nAAPL\nMSFT\n")
    assert mod.load_tickers(csv) == ["AAPL", "MSFT"]
