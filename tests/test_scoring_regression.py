"""Clinical regression fixtures based on Tisdale et al. (2013), Table 5."""
import csv

import pytest

from tisdale_qt import MAX_SCORE, calculate_tisdale_score, calculate_metrics, process_batch, _validate_bool

NORMAL = dict(age=40, sex="male", loop_diuretic=False, potassium=4.2, qtc=420,
              acute_mi=False, heart_failure=False, num_qtdrugs=0, sepsis=False)


def scored(**updates):
    return calculate_tisdale_score(**{**NORMAL, **updates})


def test_published_maximum_and_component_total():
    result = scored(age=80, sex="female", loop_diuretic=True, potassium=3,
                    qtc=500, acute_mi=True, heart_failure=True,
                    num_qtdrugs=2, sepsis=True)
    assert result["score"] == 21 == MAX_SCORE
    assert sum(x["points"] for x in result["component_breakdown"]) == 21
    assert result["factors_evaluated"] == 9
    assert result["is_complete"] is True


@pytest.mark.parametrize("changes,points", [
    ({"age": 67}, 0), ({"age": 68}, 1),
    ({"sex": "female"}, 1), ({"loop_diuretic": True}, 1),
    ({"potassium": 3.5}, 2), ({"qtc": 450}, 2),
    ({"acute_mi": True}, 2), ({"heart_failure": True}, 3),
    ({"sepsis": True}, 3), ({"num_qtdrugs": 1}, 3),
    ({"num_qtdrugs": 2}, 6), ({"num_qtdrugs": 5}, 6),
])
def test_original_point_weights(changes, points):
    assert scored(**changes)["score"] == points


def test_hypoalbuminemia_is_not_a_factor():
    yes = scored(hypoalbuminemia=True)
    no = scored(hypoalbuminemia=False)
    assert yes["score"] == no["score"] == 0
    assert yes["warnings"]


def test_unknowns_cannot_be_interpreted_as_low_risk():
    result = calculate_tisdale_score(age=40, sex="male")
    assert result["score"] == 0
    assert result["risk_classification"] == "Incomplete"
    assert len(result["missing_factors"]) == 7


@pytest.mark.parametrize("updates", [
    {"sex": "unknown"}, {"potassium": 0}, {"qtc": float("nan")},
    {"age": True}, {"loop_diuretic": 2}, {"sepsis": "maybe"},
    {"num_qtdrugs": 1.9}, {"num_qtdrugs": -1},
])
def test_rejects_invalid_inputs(updates):
    with pytest.raises(ValueError):
        scored(**updates)


def test_blank_csv_cells_are_missing_not_negative(tmp_path):
    source, target = tmp_path / "in.csv", tmp_path / "out.csv"
    source.write_text("age,sex,heart_failure,num_qtdrugs\n68,female,,1\n", encoding="utf8")
    process_batch(str(source), str(target))
    with open(target, encoding="utf8", newline="") as f:
        row = next(csv.DictReader(f))
    assert row["score"] == "5"  # age 1, female 1, one QT drug 3
    assert row["risk_classification"] == "Incomplete"
    assert "heart_failure" in row["missing_factors"]


def test_csv_formula_injection_is_escaped(tmp_path):
    source, target = tmp_path / "in.csv", tmp_path / "out.csv"
    source.write_text('Patient_ID,age\n"=1+1",68\n', encoding="utf8")
    process_batch(str(source), str(target))
    with open(target, encoding="utf8", newline="") as f:
        row = next(csv.DictReader(f))
    assert row["Patient_ID"] == "'=1+1"


def test_source_and_destination_cannot_match(tmp_path):
    source = tmp_path / "data.csv"
    source.write_text("age\n68\n", encoding="utf8")
    with pytest.raises(ValueError):
        process_batch(str(source), str(source))


def test_false_cannot_be_coerced_from_unknown_string():
    with pytest.raises(ValueError):
        _validate_bool("yes please", "sepsis")


def test_legacy_mapping_validates_conflicting_values():
    with pytest.raises(ValueError):
        calculate_metrics(v1=68, age=70)
