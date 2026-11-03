# Spatial reasoning benchmark with an executable answer key

**Status: benchmark and figures executed; LLM evaluation NOT RUN.** No LLM accuracy or model-comparison claims are made. `ground_truth_results.csv` is the final **PostGIS answer table**, not model predictions. `model_results.csv` is intentionally header-only until a model is actually evaluated.

240 questions, eight tasks, 30 questions per task. Real airport coordinate questions cover nearest candidate, radius, ordered nearest-three, and a precisely defined northwest coordinate quadrant. Synthetic fixtures cover strict containment, intersection, touching adjacency, and filter-plus-distance ranking. Boundary-inclusive `ST_Covers` is also demonstrated in the predicate figure.

## Data and scope

- Public source: [OurAirports downloads and public-domain terms](https://ourairports.com/data/), [upstream repository](https://github.com/davidmegginson/ourairports-data), [source CSV](https://davidmegginson.github.io/ourairports-data/airports.csv).
- `airports_subset.csv` freezes 40 eligible large, scheduled-service airports in the contiguous-US bounding box, sorted by identifier. This is a deliberately limited candidate set, **not all US airports**. Source URL, selection, retrieval timestamp, full-source checksum and frozen-subset checksum are in `source_manifest.json`. The huge upstream file is linked rather than uploaded.
- `generate.py` creates original synthetic geometries. They are test fixtures, **not actual counties, roads, or wildfire perimeters**. Synthetic data is dedicated to the public domain under CC0-1.0.
- These 240 questions are 60 base scenes with related tasks, not 240 independent geographies. Synthetic scenes use translations of a few deliberately simple patterns. They do not measure the full difficulty of geography or global topology.

## Reproduce (Node 24 and Python 3.11)

```sh
npm ci
python -m pip install -r requirements.txt
python generate.py
node ground_truth.mjs
python -m unittest test_evaluation.py
python analyze.py
```

The default rebuild uses committed inputs and does not download fresh airport data. `python generate.py --refresh-source` intentionally replaces the snapshot and source manifest; doing so creates a new dataset version and may change every result.

PostGIS runs locally through [PGlite's PostGIS WASM extension](https://pglite.dev/extensions/), using real PostgreSQL and PostGIS functions, with no Docker or database account. Exact JS package versions and integrity hashes are in `package-lock.json`; engine/library versions and input/output hashes are in `run_manifest.json`. This run used PostgreSQL 18.6 and PostGIS 3.6.2. `ground_truth.sql` contains all 240 generated queries; `ground_truth.mjs` initializes the airport table and executes them. The synthetic cases include 120 analytic assertions. This is reference computation under declared semantics, not a guarantee that real-world source coordinates are perfect.

Open `analysis.ipynb` for the same analysis and figure generation in notebook form. A Jupyter installation is optional and is not needed for the command-line rebuild.

## Files

| File | Purpose |
| --- | --- |
| `generate.py`, `questions.jsonl` | End-to-end question generation, complete geometry contexts and scene IDs |
| `ground_truth.sql`, `ground_truth.mjs` | Queries and executable PostGIS reference runner |
| `answer_key.jsonl`, `ground_truth_results.csv` | 240 actually computed reference answers |
| `evaluate.py`, `test_evaluation.py` | Configurable model API runner, strict scoring, scoring tests |
| `model_results.csv`, `evaluation_status.json` | Explicitly pending model-evaluation artifacts; no invented rows |
| `analysis.ipynb`, `analyze.py` | Notebook and CLI analysis |
| `airport_example.json`, `predicate_diagnostics.json` | Actual PostGIS outputs behind the figures |
| `figure_1_airport_distances.png` | Real airport-distance comparison, generated with Matplotlib |
| `figure_2_boundary_predicates.png` | Exact PostGIS predicate truth matrix, generated with Matplotlib |
| `source_manifest.json`, `run_manifest.json` | Provenance, checksums, engine versions |

## Run a model when credentials are available

Use an HTTPS chat-completions-compatible endpoint and a specific model ID. The API key is read only from `MODEL_API_KEY`; do not put it in a notebook, command-line argument, or public file. The API runner is implemented and its scoring logic tested, but **the API integration has not been exercised**. Some providers may require an adapter for generation parameters or response shape.

```sh
# Set MODEL_API_KEY securely in your environment first.
python evaluate.py run --endpoint https://YOUR_PROVIDER/v1/chat/completions --model YOUR_EXACT_MODEL_ID --output model_runs/run_1.jsonl
python evaluate.py score --input model_runs/run_1.jsonl --output model_results.csv
```

API usage may incur provider charges. Start with `--limit 2` for a smoke test and choose a new output for each model/repetition. Default full run is 240 calls. Failed calls are saved without silent retry. Raw JSONL includes complete prompts, timestamps, returned model metadata, usage if supplied, latency and raw responses. Model prompts exclude SQL, analytic fixture expectations and the answer key. Successful API text must parse as exactly `{"answer": ...}`.

The runner resumes a file only when configuration and prompt hashes match. The scorer requires booleans for boolean tasks, rejects duplicate IDs in arrays, ignores set ordering, and preserves ranking order. In a full comparison publish all 240 unique attempted questions, including failures and abstentions, not just successful calls. The scorer reports coverage; an incomplete run is not comparable to a full run. For uncertainty estimates, resample by `scene_id`, not by individual question. Repeat full runs to assess sampling variability.

`model_runs/` is ignored to prevent accidental publication of unreviewed provider payloads. After a real run, review raw responses for secrets/provider metadata and deliberately publish the raw run files needed to reproduce the model scores. Do not claim model results until those artifacts exist.

## What the figures establish

The distance figure compares one nearest result against a complete 100 km radius set, within the declared 40-airport candidate set. It depicts an arbitrary reference point near Los Angeles, not a fire or an operational recommendation. The matrix shows how `ST_Contains`, `ST_Covers`, `ST_Intersects`, and `ST_DWithin(..., 1)` differ for exact synthetic points. Neither figure measures model accuracy. Both are conventional plots created from executed queries; no AI image generation is used.

## License

Original code: MIT (`LICENSE`). Original benchmark data, synthetic fixtures and figures: CC0-1.0. Upstream airport data: public domain per OurAirports; retain its source attribution and manifest. Third-party runtime dependencies retain their own licenses.
