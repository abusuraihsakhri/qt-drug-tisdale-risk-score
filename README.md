# Qt Drug Tisdale Risk Score

> **Domain:** Clinical Decision Support & Biomedical Computing  
> **Reference:** Tisdale JE, et al. Development and validation of a risk score for drug-induced QT prolongation. J Am Coll Cardiol. 2013;61(14):1450-1457.

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## What It Does

Calculates the validated **Tisdale Risk Score (0-16)** to quantify risk of QTc prolongation in hospitalized patients receiving torsadogenic drugs. The score helps clinicians identify patients at risk for drug-induced long QT syndrome and torsades de pointes.

Zero-dependency Python implementation with single and batch evaluation.

Author: Dr. Abu Suraih Sakhri  
License: MIT

---

## Clinical Background

The Tisdale Risk Score assigns points based on established risk factors for QT prolongation:

| Risk Factor | Points |
|:------------|:------:|
| Age >= 65 years | 1 |
| Female sex | 1 |
| Loop diuretic use | 1 |
| Serum potassium <= 3.5 mEq/L | 1 |
| Admission QTc >= 450 ms | 2 |
| Acute myocardial infarction | 2 |
| Heart failure | 2 |
| One QTc-prolonging drug | 1 |
| Two or more QTc-prolonging drugs | 2 |
| Sepsis | 2 |
| Hypoalbuminemia | 2 |

**Total possible score: 0-16**

### Risk Classification

| Score | Classification | Recommendation |
|:------|:---------------|:---------------|
| 0-6 | Low Risk | Standard monitoring |
| 7-10 | Moderate Risk | Enhanced monitoring recommended |
| 11-16 | High Risk | Continuous telemetry and electrolyte management |

---

## Installation

```bash
# Clone the repository
git clone https://github.com/abusuraihsakhri/qt-drug-tisdale-risk-score.git
cd qt-drug-tisdale-risk-score

# No external dependencies required for core functionality
# For API server and tests:
pip install fastapi uvicorn pydantic pytest
```

---

## Usage

### 1. Single Case Evaluation

```bash
# Evaluate a single patient
python tisdale_qt.py single --age 72 --sex female --potassium 3.2 --qtc 470 --num-qtdrugs 2

# Output:
# {
#   "tool": "qt-drug-tisdale-risk-score",
#   "score": 9,
#   "max_score": 16,
#   "risk_classification": "Moderate Risk",
#   "clinical_recommendation": "Enhanced monitoring recommended",
#   "component_breakdown": [...],
#   "factors_evaluated": 5
# }
```

### 2. Batch CSV Processing

```bash
# Process a CSV file with patient records
python tisdale_qt.py batch -i patients.csv -o results.csv
```

**Input CSV format:**
```csv
Patient_ID,age,sex,potassium,qtc,num_qtdrugs
PT-001,72,female,3.2,470,2
PT-002,45,male,4.0,420,0
PT-003,80,female,3.0,480,3
```

### 3. API Server (FastAPI)

```bash
# Start the REST API server
python cli.py serve --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health

# Audit logs
curl http://localhost:8000/api/audit/logs
```

### 4. Docker Deployment

```bash
# Build and run with Docker Compose
cp .env.example .env
# Edit .env to set AUDIT_SECRET_KEY
docker-compose up -d

# Or build manually
docker build -t qt-drug-tisdale-risk-score .
docker run -p 8000:8000 qt-drug-tisdale-risk-score
```

---

## Testing

```bash
# Run all tests
pytest -v

# Run specific test modules
pytest test_tisdale_qt.py -v
pytest tests/ -v
```

---

## Security Features

* **Zero-PHI Outbound Interceptor:** Active regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers from outbound data.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation.
* **Input Validation:** Comprehensive validation of all clinical parameters with bounds checking.
* **Path Traversal Protection:** Safe file path handling for batch processing.
* **Secure Defaults:** Cryptographically random HMAC key generation when not explicitly configured.

### Environment Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Generate a secure key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env
AUDIT_SECRET_KEY=your-generated-key-here
```

---

## Project Structure

```
qt-drug-tisdale-risk-score/
├── tisdale_qt.py          # Core algorithm & CLI
├── cli.py                 # Advanced CLI with audit features
├── agents/                # Enterprise agent framework
│   ├── base.py           # Security, PHI guard, audit trail
│   ├── models.py         # Pydantic data models
│   ├── supervisor.py     # Multi-agent orchestration
│   ├── workers.py        # Domain-specific workers
│   ├── api.py            # FastAPI endpoints
│   └── ...
├── tests/                # Test suite
├── web/index.html        # Operations dashboard
├── Dockerfile            # Container definition
├── docker-compose.yml    # Service orchestration
└── README.md             # This file
```

---

## License

MIT License - see [LICENSE](LICENSE) for details.
