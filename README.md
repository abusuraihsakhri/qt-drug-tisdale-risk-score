# Tisdale QTc Prolongation Risk Score

A deterministic implementation of the published **Tisdale 0–21-point risk score** for QTc prolongation in hospitalized patients. Includes a standalone browser calculator, a dependency-free Python CLI, CSV batch processing, and an optional FastAPI service.

## What is scored?

| Factor | Points |
| --- | ---: |
| Age ≥68 years | 1 |
| Female sex | 1 |
| Loop diuretic | 1 |
| Potassium ≤3.5 mEq/L | 2 |
| Admission QTc ≥450 ms | 2 |
| Acute myocardial infarction | 2 |
| Heart failure | 3 |
| Sepsis | 3 |
| One QTc-prolonging drug | 3 |
| Two or more QTc-prolonging drugs | **6 total** |

**Risk strata:** 0–6 low; 7–10 moderate; 11–21 high. The two-or-more-drug category includes the three points for one drug **plus three additional points**. Hypoalbuminemia is *not* part of the published score and is not counted.

All nine fields must be supplied to report a risk stratum. Partial input is returned as a subtotal with an **Incomplete** label; unspecified risk factors are never treated as absent.

Reference: Tisdale JE, Jaynes HA, Kingery JR, et al. Development and validation of a risk score to predict QT interval prolongation in hospitalized patients. *Circ Cardiovasc Qual Outcomes.* 2013;6(4):479–487. DOI: [10.1161/CIRCOUTCOMES.113.000152](https://doi.org/10.1161/CIRCOUTCOMES.113.000152), PMID: [23716032](https://pubmed.ncbi.nlm.nih.gov/23716032/).

## Browser application

The static website is in [`web/index.html`](web/index.html). Open it locally in a browser through a static HTTP server, or access the GitHub Pages deployment once enabled and verified. No Python runtime, Pyodide, server, build system, account, or network call is needed for the scoring workflow.

Features: accessible inputs for all nine factors, validation, itemized point contributions, risk classification, reset, synthetic example, local CSV export, and print view. The implementation uses plain JavaScript modules (`web/calculator.mjs` and `web/app.mjs`).

For local development:

```bash
python -m http.server 8080 --directory web
# Open http://localhost:8080/
```

## Python CLI (standard library only)

```bash
python tisdale_qt.py single \
  --age 72 --sex female --loop-diuretic --potassium 3.4 \
  --qtc 465 --no-acute-mi --heart-failure --num-qtdrugs 2 --no-sepsis
```

This **complete synthetic example scores 16 points (high risk)**. Boolean flags accept both `--flag` and `--no-flag` to record explicit yes/no answers. Omitting a field produces an incomplete assessment.

Batch mode:

```bash
python tisdale_qt.py batch -i sample.csv -o results.csv
```

The CSV columns are `age,sex,loop_diuretic,potassium,qtc,acute_mi,heart_failure,num_qtdrugs,sepsis`. Boolean cells accept `true/false`, `yes/no`, or `1/0`. Blank fields produce an incomplete result. Invalid rows are recorded as `ERROR` while valid rows continue. The output preserves input columns and includes the score, classification, recommendation, and missing fields. Exported spreadsheet-formula-like text fields are escaped.

## Optional API and legacy audit demonstration

```bash
python -m pip install -r requirements-api.txt
python cli.py serve  # http://127.0.0.1:8000, docs at /docs
```

`POST /api/score` accepts the nine required fields as JSON and returns the validated clinical score. `GET /health` and `GET /metrics` expose process status. The original `/api/audit`, `/api/audit/logs`, `/api/chat`, and `cli.py audit/chat/verify-audit` routines are preserved for compatibility; these are **generic demonstration utilities, not clinical scoring or validated real-time monitoring**. The chat engine is a deterministic mock even if other providers are selected. Do not treat its output as medical advice.

To run Docker locally:

```bash
docker compose up --build
```

The container exposes the API on **localhost:8000**. For the in-memory HMAC audit demonstration, supply a persistent `AUDIT_SECRET_KEY` environment variable if audit signatures need to remain verifiable across instances; in-memory logs themselves are not persisted.

## Testing

```bash
python -m pip install -r requirements-api.txt pytest
pytest -q
node --test tests/test_browser.mjs  # Node.js 22+
docker build -t tisdale-risk-score .
```

GitHub Actions runs the Python tests on 3.10, 3.11 and 3.12, browser module tests, a CLI smoke test, and a Docker build. The separate Pages workflow publishes `web/` from `master` when Pages is configured to deploy using GitHub Actions.

## Privacy, applicability and limitations

- **Static calculator:** input values stay in the browser; no analytics, cookies, backend requests, or persistent browser storage. CSV export and printing are explicit user actions.
- **Python CLI:** local data are processed on the invoking machine; CSV identifiers can still be sensitive. Use synthetic/de-identified data in examples and shared outputs.
- **Optional API:** not authenticated and **not suitable for direct public exposure or identifiable patient data** without additional controls. The audit demonstration uses heuristic identifier patterns; it is not comprehensive de-identification or a HIPAA compliance guarantee.
- The score was derived and internally validated in hospitalized cardiac-care patients. It estimates QTc prolongation risk, **not an individual's probability of torsades de pointes**. It does not independently prescribe medication changes, telemetry, or treatment. Clinical assessment and local protocols remain necessary.
- No real-time medication database, FHIR ingestion, longitudinal tracking or verified external model inference is implemented.

## License

[MIT](LICENSE).
