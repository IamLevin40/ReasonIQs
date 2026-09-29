# ReasonIQs

A focused reasoning-practice app built with Flask and vanilla JavaScript. Spatial practice topics use procedural generators. Mechanical and verbal reasoning are shown as coming soon until practice topics are available. No AI service, database, or Node.js installation is needed.

## Run locally

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

Open <http://127.0.0.1:5000>. On macOS/Linux, activate with `source venv/bin/activate` and use `python3 -m venv venv` if needed. If PowerShell blocks activation, run `venv\Scripts\python.exe app.py` directly.

## Deploy to Vercel from Git

1. Push this repository to GitHub, GitLab, or Bitbucket.
2. In Vercel, choose **Add New → Project**, import the repository, and set the root directory to this repository's root (the folder containing `app.py` and `requirements.txt`).
3. Keep the detected Flask framework and default build/output settings, then deploy. No environment variables are required.

Vercel detects the top-level Flask `app` in `app.py`. It runs the API as a Python function and serves `public/static/` at `/static/` from its CDN. The same asset URLs also work with `python app.py` locally. The browser requests larger practice sessions in batches to stay within Vercel's function response size limit. Practice sessions live in the browser; reloading an active session returns to setup.

## Structure

```text
app.py                    Flask routes and API validation
data/reasoning_types.json Editable domain and subtype catalog
generators/               Dispatcher, reasoning-type packages, and shared placeholder adapter
  spatial/                One package per spatial subtype
    dice_folding/         Folding question generator
    dice_unfolding/       Unfolding question generator
    pattern_finding/      Rule engine, inference validator, distractors, and SVG renderer
    pattern_fitting/      Continuous vector composition, exact clipping, distractors, and SVG renderer
    which_does_not_belong/ Rule-first classification, ambiguity audit, and SVG renderer
    rule_determining/     String transformation engine, directed graph, evidence audit, and SVG renderer
    misc/                 Cube model and SVG figures shared by spatial subtypes
  mechanical/             One package per mechanical subtype, plus misc/
  verbal/                 One package per verbal subtype, plus misc/
  misc/                   Placeholder adapter shared across reasoning types
templates/index.html      Accessible application shell
public/static/css/app.css   Structural and responsive styles
public/static/css/theme.css Lively challenge-board visual identity
public/static/js/           API, state, timer, rendering and interactions
public/static/assets/icons/ Local SVG symbols
tests/                    API and catalog tests
venv/                     Project-local Python environment (ignored by Git)
```

Edit `data/reasoning_types.json` to add or change reasoning areas and practice topics. Spatial generator keys dispatch to dedicated modules; mechanical and verbal currently have empty subtype lists. The dice setup offers Mixed, Shapes/Polygons, Dice Dots, Characters, and Abstract Structures face markings. Both dice generators share `generators/spatial/misc/cube_model.py`, which enumerates the eleven cube-net topologies, folds nets with 3D orientation bases, and checks choices against all 24 rigid cube rotations. Each question's metadata records the cube faces, markings, opposite and adjacent pairs, option validity, proof rotation, and any violated constraint.

Pattern Finding selects declarative attribute rules, builds every structured cell, hides one cell, and derives rule-aware distractors. Its Puzzle type setting offers Linear, Matrix, and Mixed; Mixed alternates Linear and Matrix questions so their counts differ by at most one. Matrix is one continuous sequence in reading order: after cell 3, cell 4 begins the next row, and after cell 6, cell 7 begins the final row. Each boxed figure has invisible 3×3 position anchors, and all figures use monochrome SVG. Question metadata records the complete generated states, active rules, missing cell, derivation, and each distractor's error. The shared figure viewer provides zoom, focus, and PNG download for these SVGs.

Pattern Fitting builds a complete layered vector composition across a 3×3 canvas, then clips an exact cell or four-cell junction region as the answer. The missing-region setting offers either mode or Mixed, which alternates them. Line, motif, and texture layers supply continuation, closure, repetition, reflection, and symmetry constraints. Distractors mutate the clipped piece, and a vector-signature validator reinserts every option against the master. Metadata includes the complete geometry, rule layers, edge connections, clipped answer, and mutation reasons. Its SVG figures use the shared inspect, zoom, focus, and PNG export controls.

Pattern Fitting motifs use evenly spaced placements and opaque foreground fills, so background contours stop visually at each shape. Its cool-blue strokes add visual hierarchy; shape and texture fills use one dark shade and white. The validator also checks exposed vector geometry in grayscale, rejecting choices whose only difference is hidden behind a foreground shape or depends on hue.

Which Does Not Belong? selects a geometric classification rule before building choices. Its library includes properties, quantities, component relationships, closure, polygon sides, clockwise order, rotations and reflections, and compound constraints. Every component belongs to a cell in an invisible 1×1, 2×2, or 3×3 layout and sits at its exact center. Nested components share a cell as one structure; empty cells are allowed. Distance, center-offset, and symmetry-axis rules are excluded. Sessions rotate through available grid sizes, and figures draw from circles, polygons, stars, arrows, kites, shields, crescents, and varied asymmetric transformation silhouettes. The generator checks visible geometry signatures for duplicates and selects strongly separated choices. After shuffling, it verifies the intended predicate and checks for competing simpler classifications and presentation cues. Choices use monochrome SVG with an internal rounded frame and the shared zoom and PNG controls.

Shapes/Polygons uses six regular polygons with three through eight sides and no extra marks. Characters displays only the chosen letters, numbers, or symbols. Marking symmetries are included in answer validation.

Rule Determining selects pure string operations, solves the complete query, then adds demonstrations that eliminate competing registered meanings. Metadata records the directed logical grid, operator dictionary, demonstrations, intermediate query states, and distractor misconceptions. Its neutral SVG projection uses the shared focus, zoom, and PNG controls.

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

Images must come from the app origin or a `data:image/png`, `image/jpeg`, or `image/webp` base64 URL. SVG markup is sanitized before display. Every figure needs a descriptive `alt`; an optional `caption` appears below it. For a canvas payload, register a synchronous drawing function with `registerCanvasRenderer(key, draw)` from `public/static/js/figures.js`, then send `{ "kind": "canvas", "renderer": key, "width": 640, "height": 480, "data": { ... }, "alt": "..." }`. A DOM figure can use `registerDomRenderer(key, render, exportCanvas)` and `{ "kind": "dom", "renderer": key, "data": { ... }, "alt": "..." }`. `exportCanvas` is optional; without it the export utility captures the local styled DOM through SVG `foreignObject`. Registered functions live in the browser, while the API sends only their keys and data.

Hover over a figure, then use its Inspect button to open the viewer. On touch screens, the button stays visible. The viewer supports mouse wheel, touch pinch, drag, keyboard `+`/`-`, arrow keys, `0`/Home, and Escape. The PNG control downloads one figure, or all figures in its question or choice block as one image in display order.

Clicking or tapping a choice figure selects that choice. Submit answer checks the current item, shows Correct or Incorrect with its explanation, and locks that answer. Submitted results remain visible when revisiting an item. Only submitted answers count toward the final score.

The interface uses hash routes, so refreshing a menu or setup URL retains its context. An in-progress practice session stays in memory; refreshing it returns to setup. Setup values are saved locally in the browser. Leaving an active session asks for confirmation.

## Checks

`python -m unittest discover -s tests -p "test_*.py"` checks the catalog, API, cube geometry, and generated answer uniqueness. The optional browser workflow checks require `pip install playwright`, an installed Playwright Chromium browser, and a running local server; then run `python tests/browser_check.py`, `python tests/figure_check.py`, and `python tests/spatial_browser_check.py`.
