# yfinance-statements-to-json

Static JSON financial statements from yfinance, refreshed by GitHub Actions, consumable via plain REST GET.

## Quick start
1. Add your tickers to inputs/tickers.csv (or swap in the curated list at `inputs/fortune_1000_plus_tech_firms.csv`).
2. Push to main.
3. Run the "E2E smoke (real yfinance)" workflow with AAPL,MSFT to generate sample JSON as an artifact.
4. Enable the "Refresh yfinance statements (sharded)" schedule for nightly updates.

### Pre-built ticker lists
- `inputs/fortune_1000_plus_tech_firms.csv` – Fortune 1000 constituents blended with the large-cap technology firms already tracked by this project. The file is newline-delimited (with an initial comment) so it can be passed directly to `--tickers-csv` without additional preprocessing.

## Local dev
```bash
python -m pip install -r requirements.txt
pytest -q
```

Dry run (no writes):
```bash
python scripts/build_statements.py --tickers-csv inputs/tickers.csv --dry-run
```

Generate locally:
```bash
python scripts/build_statements.py --tickers-csv inputs/tickers.csv --out-dir data
```

Schema validate:
```bash
python - <<'PY'
import json, glob
from jsonschema import validate
schema = json.load(open('schemas/statement.schema.json'))
for p in glob.glob('data/*.json'):
    if p.endswith('index.json'): continue
    validate(instance=json.load(open(p)), schema=schema)
    print("Validated:", p)
PY
```

## Consuming from a frontend
Raw GitHub:
https://raw.githubusercontent.com/ORG/REPO/main/data/AAPL.json

jsDelivr CDN:
https://cdn.jsdelivr.net/gh/ORG/REPO@main/data/AAPL.json
