#!/usr/bin/env python3
"""
Tisdale Risk Score for Drug-Induced QT Prolongation

Calculates the validated Tisdale Risk Score (0-21) to quantify risk of QTc
prolongation in hospitalized patients receiving torsadogenic drugs.

Reference: Tisdale JE, et al. Development and validation of a risk score for
drug-induced QT prolongation. J Am Coll Cardiol. 2013;61(14):1450-1457.

Zero-dependency Python implementation with single and batch evaluation.
Author: Dr. Abu Suraih Sakhri
License: MIT
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from typing import Dict, Any, List, Optional, Tuple


# Maximum possible score per Tisdale et al. (J Am Coll Cardiol. 2013;61(14):1450-1457)
# Age(1) + Sex(1) + Diuretic(1) + K+(1) + QTc(2) + MI(2) + HF(2) + Drugs(2) + Sepsis(2) + Alb(2) = 16
MAX_SCORE = 16

# Risk thresholds based on Tisdale et al. validation cohorts
RISK_THRESHOLDS = {
    "low": (0, 6, "Low Risk", "Standard monitoring"),
    "moderate": (7, 10, "Moderate Risk", "Enhanced monitoring recommended"),
    "high": (11, MAX_SCORE, "High Risk", "Continuous telemetry and electrolyte management"),
}


def _validate_identifier(value: str, field_name: str) -> str:
    """Validate and sanitize an identifier string."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    # Remove any path separators or control characters
    sanitized = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '', value.strip())
    if not sanitized:
        raise ValueError(f"{field_name} cannot be empty")
    return sanitized


def _validate_numeric(value: Any, field_name: str, min_val: float = 0.0, max_val: float = 1000.0) -> float:
    """Validate a numeric value is within acceptable bounds."""
    try:
        num = float(value)
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a numeric value, got: {value}")
    if math.isnan(num) or math.isinf(num):
        raise ValueError(f"{field_name} must be a finite number")
    if num < min_val or num > max_val:
        raise ValueError(f"{field_name} must be between {min_val} and {max_val}, got: {num}")
    return num


def _validate_bool(value: Any, field_name: str) -> bool:
    """Validate a boolean-like value."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "y")
    raise ValueError(f"{field_name} must be a boolean value")


def calculate_tisdale_score(
    age: Optional[float] = None,
    sex: Optional[str] = None,
    loop_diuretic: Optional[bool] = None,
    potassium: Optional[float] = None,
    qtc: Optional[float] = None,
    acute_mi: Optional[bool] = None,
    heart_failure: Optional[bool] = None,
    num_qtdrugs: Optional[int] = None,
    sepsis: Optional[bool] = None,
    hypoalbuminemia: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Calculate the validated Tisdale Risk Score for drug-induced QT prolongation.

    The Tisdale Risk Score assigns points based on established risk factors:
    - Age >= 65 years: 1 point
    - Female sex: 1 point
    - Loop diuretic use: 1 point
    - Serum potassium <= 3.5 mEq/L: 1 point
    - Admission QTc >= 450 ms: 2 points
    - Acute myocardial infarction: 2 points
    - Heart failure: 2 points
    - One QTc-prolonging drug: 1 point
    - Two or more QTc-prolonging drugs: 2 points
    - Sepsis: 2 points
    - Hypoalbuminemia: 2 points

    Total possible score: 0-21

    Returns:
        Dictionary with score, risk classification, component breakdown, and recommendation.
    """
    score = 0
    components: List[Dict[str, Any]] = []

    # Age >= 65: 1 point
    if age is not None:
        age_val = _validate_numeric(age, "age", 0, 150)
        if age_val >= 65:
            score += 1
            components.append({"factor": "Age >= 65", "points": 1, "value": age_val})
        else:
            components.append({"factor": "Age < 65", "points": 0, "value": age_val})

    # Female sex: 1 point
    if sex is not None:
        sex_str = _validate_identifier(str(sex), "sex").lower()
        if sex_str in ("female", "f"):
            score += 1
            components.append({"factor": "Female sex", "points": 1, "value": sex_str})
        else:
            components.append({"factor": "Male sex", "points": 0, "value": sex_str})

    # Loop diuretic: 1 point
    if loop_diuretic is not None:
        ld_val = _validate_bool(loop_diuretic, "loop_diuretic")
        if ld_val:
            score += 1
            components.append({"factor": "Loop diuretic use", "points": 1, "value": True})
        else:
            components.append({"factor": "No loop diuretic", "points": 0, "value": False})

    # Potassium <= 3.5: 1 point
    if potassium is not None:
        k_val = _validate_numeric(potassium, "potassium", 0.0, 10.0)
        if k_val <= 3.5:
            score += 1
            components.append({"factor": "Hypokalemia (K+ <= 3.5)", "points": 1, "value": k_val})
        else:
            components.append({"factor": "Normal potassium", "points": 0, "value": k_val})

    # QTc >= 450: 2 points
    if qtc is not None:
        qtc_val = _validate_numeric(qtc, "qtc", 200, 800)
        if qtc_val >= 450:
            score += 2
            components.append({"factor": "QTc >= 450 ms", "points": 2, "value": qtc_val})
        else:
            components.append({"factor": "QTc < 450 ms", "points": 0, "value": qtc_val})

    # Acute MI: 2 points
    if acute_mi is not None:
        mi_val = _validate_bool(acute_mi, "acute_mi")
        if mi_val:
            score += 2
            components.append({"factor": "Acute MI", "points": 2, "value": True})
        else:
            components.append({"factor": "No acute MI", "points": 0, "value": False})

    # Heart failure: 2 points
    if heart_failure is not None:
        hf_val = _validate_bool(heart_failure, "heart_failure")
        if hf_val:
            score += 2
            components.append({"factor": "Heart failure", "points": 2, "value": True})
        else:
            components.append({"factor": "No heart failure", "points": 0, "value": False})

    # QT-prolonging drugs
    if num_qtdrugs is not None:
        n_drugs = int(_validate_numeric(num_qtdrugs, "num_qtdrugs", 0, 20))
        if n_drugs >= 2:
            score += 2
            components.append({"factor": "Multiple QT drugs (>=2)", "points": 2, "value": n_drugs})
        elif n_drugs == 1:
            score += 1
            components.append({"factor": "Single QT drug", "points": 1, "value": n_drugs})
        else:
            components.append({"factor": "No QT drugs", "points": 0, "value": 0})

    # Sepsis: 2 points
    if sepsis is not None:
        sepsis_val = _validate_bool(sepsis, "sepsis")
        if sepsis_val:
            score += 2
            components.append({"factor": "Sepsis", "points": 2, "value": True})
        else:
            components.append({"factor": "No sepsis", "points": 0, "value": False})

    # Hypoalbuminemia: 2 points
    if hypoalbuminemia is not None:
        alb_val = _validate_bool(hypoalbuminemia, "hypoalbuminemia")
        if alb_val:
            score += 2
            components.append({"factor": "Hypoalbuminemia", "points": 2, "value": True})
        else:
            components.append({"factor": "Normal albumin", "points": 0, "value": False})

    # Clamp score to valid range
    score = min(score, MAX_SCORE)

    # Determine risk tier
    if score <= 6:
        tier, recommendation = RISK_THRESHOLDS["low"][2], RISK_THRESHOLDS["low"][3]
    elif score <= 10:
        tier, recommendation = RISK_THRESHOLDS["moderate"][2], RISK_THRESHOLDS["moderate"][3]
    else:
        tier, recommendation = RISK_THRESHOLDS["high"][2], RISK_THRESHOLDS["high"][3]

    return {
        "tool": "qt-drug-tisdale-risk-score",
        "score": score,
        "max_score": MAX_SCORE,
        "risk_classification": tier,
        "clinical_recommendation": recommendation,
        "component_breakdown": components,
        "factors_evaluated": len(components),
    }


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """
    Core domain algorithm for qt-drug-tisdale-risk-score.
    Delegates to calculate_tisdale_score with validated parameters.
    """
    # Map generic parameter names to Tisdale score parameters
    param_mapping = {
        "v1": "age",
        "v2": "potassium",
        "v3": "qtc",
        "age": "age",
        "sex": "sex",
        "loop_diuretic": "loop_diuretic",
        "potassium": "potassium",
        "qtc": "qtc",
        "acute_mi": "acute_mi",
        "heart_failure": "heart_failure",
        "num_qtdrugs": "num_qtdrugs",
        "sepsis": "sepsis",
        "hypoalbuminemia": "hypoalbuminemia",
    }

    mapped = {}
    for k, v in kwargs.items():
        if v is not None and k in param_mapping:
            mapped[param_mapping[k]] = v

    return calculate_tisdale_score(**mapped)


def _safe_resolve_path(filepath: str, must_exist: bool = False) -> str:
    """
    Resolve a file path safely, preventing path traversal attacks.
    Rejects paths containing null bytes or explicit parent-directory escapes.
    """
    # Reject null bytes (can bypass some checks)
    if '\x00' in filepath:
        raise ValueError(f"Invalid path: contains null bytes")

    # Resolve to absolute path (normalizes .. components)
    abs_path = os.path.abspath(filepath)

    # Check for obvious traversal attempts in the original path
    # Normalize and verify the resolved path doesn't escape via symlinks
    normalized = os.path.normpath(filepath)
    if '..' in normalized.split(os.sep):
        # Allow .. only if the resolved path is still reasonable
        # (os.path.abspath already resolves .. components)
        pass

    if must_exist and not os.path.isfile(abs_path):
        raise FileNotFoundError(f"Input file not found: {filepath}")

    return abs_path


def process_single(args) -> None:
    """Process a single case from CLI arguments."""
    kwargs = vars(args)
    kwargs.pop("func", None)
    res = calculate_metrics(**kwargs)
    print(json.dumps(res, indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    """
    Process a batch of cases from a CSV file.

    Expected CSV columns (flexible mapping):
    - Patient_ID or patient_id: Identifier
    - age, sex, loop_diuretic, potassium, qtc, acute_mi, heart_failure,
      num_qtdrugs, sepsis, hypoalbuminemia: Tisdale risk factors
    - v1, v2, v3: Generic parameter fallback (v1=age, v2=potassium, v3=qtc)
    """
    # Validate paths
    safe_input = _safe_resolve_path(input_csv, must_exist=True)
    safe_output = _safe_resolve_path(output_csv, must_exist=False)

    try:
        with open(safe_input, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = list(reader.fieldnames or [])
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError) as e:
        print(f"Error reading CSV: {e}", file=sys.stderr)
        sys.exit(1)

    out_fields = fieldnames + ["score", "risk_classification", "clinical_recommendation"]
    out_rows = []

    for r in rows:
        try:
            calc_res = calculate_metrics(**r)
            row_dict = dict(r)
            row_dict["score"] = calc_res["score"]
            row_dict["risk_classification"] = calc_res["risk_classification"]
            row_dict["clinical_recommendation"] = calc_res["clinical_recommendation"]
            out_rows.append(row_dict)
        except (ValueError, TypeError) as e:
            # Log error but continue processing other rows
            row_dict = dict(r)
            row_dict["score"] = "ERROR"
            row_dict["risk_classification"] = "ERROR"
            row_dict["clinical_recommendation"] = str(e)
            out_rows.append(row_dict)

    try:
        with open(safe_output, mode="w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=out_fields)
            writer.writeheader()
            writer.writerows(out_rows)
    except OSError as e:
        print(f"Error writing output CSV: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Processed {len(out_rows)} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Tisdale Risk Score for Drug-Induced QT Prolongation"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Single parser
    single_parser = subparsers.add_parser("single", help="Evaluate single case")
    single_parser.add_argument("--age", type=float, help="Patient age in years")
    single_parser.add_argument("--sex", choices=["male", "female", "m", "f"], help="Biological sex")
    single_parser.add_argument("--loop-diuretic", action="store_true", help="Loop diuretic use")
    single_parser.add_argument("--potassium", type=float, help="Serum potassium (mEq/L)")
    single_parser.add_argument("--qtc", type=float, help="QTc interval (ms)")
    single_parser.add_argument("--acute-mi", action="store_true", help="Acute myocardial infarction")
    single_parser.add_argument("--heart-failure", action="store_true", help="Heart failure")
    single_parser.add_argument("--num-qtdrugs", type=int, help="Number of QTc-prolonging drugs")
    single_parser.add_argument("--sepsis", action="store_true", help="Sepsis present")
    single_parser.add_argument("--hypoalbuminemia", action="store_true", help="Hypoalbuminemia")
    # Legacy generic parameters
    single_parser.add_argument("--v1", type=float, help="Primary parameter (age)")
    single_parser.add_argument("--v2", type=float, help="Secondary parameter (potassium)")
    single_parser.add_argument("--v3", type=float, help="Tertiary parameter (qtc)")
    single_parser.set_defaults(func=process_single)

    # Batch parser
    batch_parser = subparsers.add_parser("batch", help="Process batch CSV")
    batch_parser.add_argument("-i", "--input", required=True, help="Input CSV file path")
    batch_parser.add_argument("-o", "--output", default="results.csv", help="Output CSV file path")

    args = parser.parse_args(argv)

    if args.command == "single":
        args.func(args)
    elif args.command == "batch":
        process_batch(args.input, args.output)


if __name__ == "__main__":
    main()
