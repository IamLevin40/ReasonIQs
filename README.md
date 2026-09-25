# ReasonIQs

A focused reasoning-practice prototype built with Flask and vanilla JavaScript. Questions are intentionally labelled placeholders. No AI service, database, or Node.js installation is needed.

## Run locally

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. On macOS/Linux, activate with `source venv/bin/activate` and use `python3 -m venv venv` if needed. If PowerShell blocks activation, run `venv\Scripts\python.exe app.py` directly.

## Structure

```text
app.py                    Flask routes and API validation
data/reasoning_types.json Editable domain and subtype catalog
generators/               Normalized question contract and placeholder adapter
templates/index.html      Accessible application shell
static/css/app.css        Structural and responsive styles
static/css/theme.css      Lively challenge-board visual identity
static/js/                API, state, timer, rendering and interactions
static/assets/icons/      Local SVG symbols
tests/                    API and catalog tests
venv/                     Project-local Python environment (ignored by Git)
```

Edit `data/reasoning_types.json` to add or change domains and subtypes. Each subtype has a `generator_key` reserved for a future procedural module. `generators/placeholder.py` currently returns normalized question objects from the practice API; replace its implementation with a dispatcher when procedural generators are ready.

The interface uses hash routes, so refreshing a menu or setup URL retains its context. An in-progress practice session stays in memory; refreshing it returns to setup. Setup values are saved locally in the browser. Leaving an active session asks for confirmation.

## Checks

`python -m unittest discover -s tests -p test_app.py` checks catalog consistency and API validation. The optional browser workflow check requires `pip install playwright`, an installed Playwright Chromium browser, and a running local server; then run `python tests/browser_check.py`.
