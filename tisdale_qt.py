#!/usr/bin/env python3
"""Tisdale risk score for QTc prolongation in hospitalized patients.

Tisdale JE et al. Circ Cardiovasc Qual Outcomes. 2013;6:479-487.
DOI: 10.1161/CIRCOUTCOMES.113.000152.
"""
import argparse
import csv
import json
import math
import os
import re
from typing import Any, Dict, List, Optional

MAX_SCORE = 21
RISK_THRESHOLDS = {
    "low": (0, 6, "Low Risk", "Review QT-prolonging medications and clinical monitoring needs"),
    "moderate": (7, 10, "Moderate Risk", "Consider additional ECG monitoring and correction of modifiable risk factors"),
    "high": (11, 21, "High Risk", "Prompt medication review, electrolyte management and close ECG monitoring"),
}
FACTORS = (
    "age", "sex", "loop_diuretic", "potassium", "qtc", "acute_mi",
    "heart_failure", "num_qtdrugs", "sepsis",
)


def _validate_identifier(value: str, field_name: str) -> str:
    """Clean a display identifier; not a path or a PHI de-identification routine."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    cleaned = re.sub(r'[\\/:*?"<>|\x00-\x1f]', "", value.strip())
    if not cleaned:
        raise ValueError(f"{field_name} cannot be empty")
    return cleaned


def _validate_numeric(value: Any, field_name: str, min_val: float = 0.0,
                      max_val: float = 1000.0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric, not boolean")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not math.isfinite(number) or not min_val <= number <= max_val:
        raise ValueError(f"{field_name} must be finite and between {min_val} and {max_val}")
    return number


def _validate_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and math.isfinite(value) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1", "yes", "y"):
            return True
        if normalized in ("false", "0", "no", "n"):
            return False
    raise ValueError(f"{field_name} must be true/false, yes/no or 1/0")


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
    """Calculate the published 0–21-point Tisdale score.

    Absent factors are not assumed negative. An incomplete assessment returns
    a subtotal and an 'Incomplete' classification, not a low-risk conclusion.

    `hypoalbuminemia` is accepted for backwards compatibility but NEVER
    scored: it is not a component of the validated Tisdale model.
    """
    raw = dict(age=age, sex=sex, loop_diuretic=loop_diuretic, potassium=potassium,
               qtc=qtc, acute_mi=acute_mi, heart_failure=heart_failure,
               num_qtdrugs=num_qtdrugs, sepsis=sepsis)
    missing = [name for name in FACTORS if raw[name] is None or raw[name] == ""]
    components: List[Dict[str, Any]] = []
    warnings: List[str] = []
    if hypoalbuminemia is not None:
        _validate_bool(hypoalbuminemia, "hypoalbuminemia")
        warnings.append("Hypoalbuminemia is not part of the validated Tisdale score and was ignored.")

    def add(factor: str, points: int, value: Any) -> None:
        components.append({"factor": factor, "points": points, "value": value})

    if "age" not in missing:
        age_val = _validate_numeric(age, "age", 0, 150)
        add("Age >= 68 years", 1 if age_val >= 68 else 0, age_val)
    if "sex" not in missing:
        if not isinstance(sex, str) or sex.strip().lower() not in ("female", "f", "male", "m"):
            raise ValueError("sex must be male/female (or m/f)")
        sex_val = sex.strip().lower()
        add("Female sex", 1 if sex_val in ("female", "f") else 0, sex_val)
    if "loop_diuretic" not in missing:
        val = _validate_bool(loop_diuretic, "loop_diuretic")
        add("Loop diuretic", 1 if val else 0, val)
    if "potassium" not in missing:
        val = _validate_numeric(potassium, "potassium", 0.1, 10)
        add("Potassium <= 3.5 mEq/L", 2 if val <= 3.5 else 0, val)
    if "qtc" not in missing:
        val = _validate_numeric(qtc, "qtc", 200, 800)
        add("Admission QTc >= 450 ms", 2 if val >= 450 else 0, val)
    if "acute_mi" not in missing:
        val = _validate_bool(acute_mi, "acute_mi")
        add("Acute myocardial infarction", 2 if val else 0, val)
    if "heart_failure" not in missing:
        val = _validate_bool(heart_failure, "heart_failure")
        add("Heart failure", 3 if val else 0, val)
    if "num_qtdrugs" not in missing:
        val = _validate_numeric(num_qtdrugs, "num_qtdrugs", 0, 100)
        if not val.is_integer():
            raise ValueError("num_qtdrugs must be a whole number")
        count = int(val)
        add("QTc-prolonging drugs (0 / 1 / >=2)", 6 if count >= 2 else 3 if count == 1 else 0, count)
    if "sepsis" not in missing:
        val = _validate_bool(sepsis, "sepsis")
        add("Sepsis", 3 if val else 0, val)

    score = sum(component["points"] for component in components)
    if score > MAX_SCORE:
        raise AssertionError("Tisdale score exceeds the validated maximum")
    complete = not missing
    if complete:
        band = "low" if score <= 6 else "moderate" if score <= 10 else "high"
        classification = RISK_THRESHOLDS[band][2]
        recommendation = RISK_THRESHOLDS[band][3]
    else:
        classification = "Incomplete"
        recommendation = "Complete all nine risk factors before interpreting the risk category"
        warnings.append("Only a subtotal was calculated; missing factors may increase the risk score.")
        if score >= 11:
            warnings.append("The observed subtotal already meets the high-risk threshold.")
    return {
        "tool": "qt-drug-tisdale-risk-score",
        "score": score,
        "max_score": MAX_SCORE,
        "risk_classification": classification,
        "clinical_recommendation": recommendation,
        "component_breakdown": components,
        "factors_evaluated": len(components),
        "is_complete": complete,
        "missing_factors": missing,
        "warnings": warnings,
    }


def calculate_metrics(**kwargs) -> Dict[str, Any]:
    """Compatibility entry point; v1/v2/v3 map to age/potassium/QTc."""
    mapping = {**{name: name for name in FACTORS},
               "v1": "age", "v2": "potassium", "v3": "qtc",
               "hypoalbuminemia": "hypoalbuminemia"}
    result = {}
    for key, value in kwargs.items():
        if key in mapping and value is not None and value != "":
            target = mapping[key]
            if target in result and result[target] != value:
                raise ValueError(f"Conflicting values for {target}")
            result[target] = value
    return calculate_tisdale_score(**result)


def _safe_resolve_path(filepath: str, must_exist: bool = False) -> str:
    """Resolve a local CLI path. The CLI is not a sandbox for untrusted paths."""
    if not isinstance(filepath, str) or "\x00" in filepath:
        raise ValueError("Invalid path: contains null bytes or is not text")
    resolved = os.path.abspath(filepath)
    if must_exist and not os.path.isfile(resolved):
        raise FileNotFoundError(f"Input file not found: {filepath}")
    return resolved


def _spreadsheet_safe(value: Any) -> Any:
    """Prevent CSV-formula execution if an exported CSV is opened in a spreadsheet."""
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def process_single(args) -> None:
    data = vars(args).copy()
    data.pop("func", None)
    data.pop("command", None)
    print(json.dumps(calculate_metrics(**data), indent=2))


def process_batch(input_csv: str, output_csv: str) -> None:
    source = _safe_resolve_path(input_csv, must_exist=True)
    destination = _safe_resolve_path(output_csv)
    if os.path.samefile(source, destination) if os.path.exists(destination) else source == destination:
        raise ValueError("Input and output CSV files must be different")
    with open(source, encoding="utf-8-sig", newline="") as inp:
        reader = csv.DictReader(inp)
        fields = reader.fieldnames or []
        if not fields or len(fields) != len(set(fields)) or any(not f for f in fields):
            raise ValueError("CSV must have unique nonempty column headings")
        output_fields = list(dict.fromkeys(fields + ["score", "risk_classification",
                                                     "clinical_recommendation", "missing_factors"]))
        with open(destination, "w", encoding="utf-8", newline="") as out:
            writer = csv.DictWriter(out, fieldnames=output_fields)
            writer.writeheader()
            count = 0
            for record in reader:
                if None in record:
                    raise ValueError(f"CSV row {reader.line_num} has more values than columns")
                row = dict(record)
                try:
                    result = calculate_metrics(**record)
                    row["score"] = result["score"]
                    row["risk_classification"] = result["risk_classification"]
                    row["clinical_recommendation"] = result["clinical_recommendation"]
                    row["missing_factors"] = ";".join(result["missing_factors"])
                except (ValueError, TypeError) as exc:
                    row.update(score="ERROR", risk_classification="ERROR",
                               clinical_recommendation=str(exc), missing_factors="")
                writer.writerow({key: _spreadsheet_safe(value) for key, value in row.items()})
                count += 1
    print(f"Processed {count} records -> {output_csv}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Tisdale QTc prolongation risk score (0–21)")
    subparsers = parser.add_subparsers(dest="command", required=True)
    single = subparsers.add_parser("single", help="Evaluate a single assessment")
    single.add_argument("--age", type=float)
    single.add_argument("--sex", choices=["female", "male", "f", "m"])
    for flag in ("loop_diuretic", "acute_mi", "heart_failure", "sepsis"):
        single.add_argument("--" + flag.replace("_", "-"),
                            action=argparse.BooleanOptionalAction, default=None)
    single.add_argument("--potassium", type=float)
    single.add_argument("--qtc", type=float)
    single.add_argument("--num-qtdrugs", type=int)
    single.add_argument("--v1", type=float, help="Legacy alias for age")
    single.add_argument("--v2", type=float, help="Legacy alias for potassium")
    single.add_argument("--v3", type=float, help="Legacy alias for admission QTc")
    single.add_argument("--hypoalbuminemia", action=argparse.BooleanOptionalAction,
                        default=None, help="Deprecated: ignored (not a Tisdale factor)")
    single.set_defaults(func=process_single)
    batch = subparsers.add_parser("batch", help="Process a local CSV")
    batch.add_argument("-i", "--input", required=True)
    batch.add_argument("-o", "--output", default="results.csv")
    args = parser.parse_args(argv)
    if args.command == "single":
        process_single(args)
    else:
        process_batch(args.input, args.output)


if __name__ == "__main__":
    main()
