import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import pandas as pd
import yfinance as yf


def df_to_period_dict(df: pd.DataFrame) -> dict[str, dict[str, float]]:
    if df is None or df.empty:
        return {}
    df = df.copy()
    df.columns = [c.strftime("%Y-%m-%d") if hasattr(c, "strftime") else str(c) for c in df.columns]
    df.index = [str(i) for i in df.index]
    return {period: df[period].dropna().to_dict() for period in df.columns}


def fetch_statements(ticker: str, retries: int = 3, backoff_s: float = 1.0) -> dict:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            t = yf.Ticker(ticker)
            inc_a = df_to_period_dict(t.financials)
            bs_a = df_to_period_dict(t.balance_sheet)
            cf_a = df_to_period_dict(t.cashflow)
            inc_q = df_to_period_dict(t.quarterly_financials)
            bs_q = df_to_period_dict(t.quarterly_balance_sheet)
            cf_q = df_to_period_dict(t.quarterly_cashflow)

            meta = {"symbol": ticker.upper()}
            try:
                fi = t.fast_info
                meta.update(
                    {
                        "currency": getattr(fi, "currency", None),
                        "exchange": getattr(fi, "exchange", None),
                        "shortName": getattr(fi, "shortName", None),
                    }
                )
            except Exception:
                pass

            return {
                "meta": meta,
                "source": "yfinance/Yahoo Finance",
                "generated_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "statements": {
                    "annual": {
                        "income_statement": inc_a,
                        "balance_sheet": bs_a,
                        "cash_flow": cf_a,
                    },
                    "quarterly": {
                        "income_statement": inc_q,
                        "balance_sheet": bs_q,
                        "cash_flow": cf_q,
                    },
                },
                "validations": {},
            }
        except Exception as e:  # noqa: PERF203 - the retry loop is intentional
            last_err = e
            time.sleep(backoff_s * attempt)
    raise RuntimeError(f"Failed to fetch {ticker}: {last_err}")


def load_tickers(csv_path: Path) -> list[str]:
    lines = [x.strip().upper() for x in csv_path.read_text().splitlines()]
    return [x for x in lines if x and not x.startswith("#")]


def shard(lst: list[str], idx: int, cnt: int) -> list[str]:
    if cnt <= 1:
        return lst
    n = math.ceil(len(lst) / cnt)
    return lst[idx * n : (idx + 1) * n]


def write_if_changed(path: Path, obj: dict) -> bool:
    new = json.dumps(obj, indent=2, ensure_ascii=False).encode()
    old = path.read_bytes() if path.exists() else b""
    if hashlib.sha256(new).hexdigest() != hashlib.sha256(old).hexdigest():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(new)
        return True
    return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers-csv", required=True)
    ap.add_argument("--out-dir", default="data")
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--shard-count", type=int, default=1)
    ap.add_argument("--sleep-ms", type=int, default=400)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tickers_all = load_tickers(Path(args.tickers_csv))
    tickers = shard(tickers_all, args.shard_index, args.shard_count)
    out_dir = Path(args.out_dir)

    updated, failures = [], []
    for tk in tickers:
        try:
            payload = fetch_statements(tk)
            if not args.dry_run:
                out = out_dir / f"{tk}.json"
                if write_if_changed(out, payload):
                    updated.append(tk)
            time.sleep(args.sleep_ms / 1000.0)
        except Exception as e:  # noqa: PERF203 - soft-fail logic requires catch-all
            failures.append({"ticker": tk, "error": str(e)})

    manifest = {
        "generated_at_utc": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tickers_processed": tickers,
        "tickers_updated": updated,
        "failures": failures,
    }
    if not args.dry_run:
        write_if_changed(out_dir / "index.json", manifest)

    print(json.dumps({"summary": manifest}, indent=2))

    if len(failures) > max(3, int(0.15 * max(1, len(tickers)))):
        sys.exit(1)


if __name__ == "__main__":
    main()
