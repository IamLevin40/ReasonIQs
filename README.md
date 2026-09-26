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

## Question and figure data

Each question has an `id`, optional `text` (legacy `prompt` is accepted), optional ordered `figures`, `choices`, and `correct_answer_id`. Each choice has an `id`, optional `text`, and optional ordered `figures`. Text may be empty when figures carry the whole question or answer. The renderer chooses a two-column answer layout only when every choice has figures and little text; otherwise choices stack. The temporary generator includes text-only, figure-only, and mixed examples.

```json
{
  "text": "Which diagram continues the pattern?",
  "figures": [
    { "kind": "svg", "svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 240 140\">...</svg>", "alt": "First pattern tile" },
    { "kind": "image", "src": "/static/generated/tile-2.png", "alt": "Second pattern tile" }
  ],
  "choices": [
    { "id": "a", "figures": [{ "kind": "image", "base64": "...", "mime": "image/png", "alt": "Option A pattern" }] },
    { "id": "b", "text": "A written answer" }
  ]
}
```

Images must come from the app origin or a `data:image/png`, `image/jpeg`, or `image/webp` base64 URL. SVG markup is sanitized before display. Every figure needs a descriptive `alt`; an optional `caption` appears below it. For a canvas payload, register a synchronous drawing function with `registerCanvasRenderer(key, draw)` from `static/js/figures.js`, then send `{ "kind": "canvas", "renderer": key, "width": 640, "height": 480, "data": { ... }, "alt": "..." }`. A DOM figure can use `registerDomRenderer(key, render, exportCanvas)` and `{ "kind": "dom", "renderer": key, "data": { ... }, "alt": "..." }`. `exportCanvas` is optional; without it the export utility captures the local styled DOM through SVG `foreignObject`. Registered functions live in the browser, while the API sends only their keys and data.

Hover over a figure, then use its Inspect button to open the viewer. On touch screens, the button stays visible. The viewer supports mouse wheel, touch pinch, drag, keyboard `+`/`-`, arrow keys, `0`/Home, and Escape. The PNG control downloads one figure, or all figures in its question or choice block as one image in display order.

The interface uses hash routes, so refreshing a menu or setup URL retains its context. An in-progress practice session stays in memory; refreshing it returns to setup. Setup values are saved locally in the browser. Leaving an active session asks for confirmation.

## Checks

`python -m unittest discover -s tests -p test_app.py` checks catalog consistency and API validation. The optional browser workflow checks require `pip install playwright`, an installed Playwright Chromium browser, and a running local server; then run `python tests/browser_check.py` and `python tests/figure_check.py`.
