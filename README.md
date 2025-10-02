# yfinance-statements-to-json

Static JSON financial statements from yfinance, refreshed by GitHub Actions, consumable via plain REST GET.

## Quick start
1. Add your tickers to inputs/tickers.csv.
2. Push to main.
3. Run the "E2E smoke (real yfinance)" workflow with AAPL,MSFT to generate sample JSON as an artifact.
4. Enable the "Refresh yfinance statements (sharded)" schedule for nightly updates.

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
