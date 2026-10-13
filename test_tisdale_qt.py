"""
Comprehensive test suite for Tisdale Risk Score calculation.
"""
import pytest
import os
import csv
from tisdale_qt import (
    calculate_metrics,
    calculate_tisdale_score,
    process_batch,
    _validate_identifier,
    _validate_numeric,
    _validate_bool,
    _safe_resolve_path,
    MAX_SCORE,
)


class TestCalculateTisdaleScore:
    """Tests for the validated Tisdale Risk Score algorithm."""

    def test_minimum_score(self):
        """Patient with no risk factors should score 0."""
        result = calculate_tisdale_score(
            age=30, sex="male", loop_diuretic=False, potassium=4.0,
            qtc=400, acute_mi=False, heart_failure=False,
            num_qtdrugs=0, sepsis=False, hypoalbuminemia=False
        )
        assert result["score"] == 0
        assert result["risk_classification"] == "Low Risk"

    def test_maximum_score(self):
        """Patient with all risk factors should score at most MAX_SCORE."""
        result = calculate_tisdale_score(
            age=80, sex="female", loop_diuretic=True, potassium=3.0,
            qtc=500, acute_mi=True, heart_failure=True,
            num_qtdrugs=3, sepsis=True, hypoalbuminemia=True
        )
        assert result["score"] == MAX_SCORE
        assert result["score"] <= 21
        assert result["risk_classification"] == "High Risk"

    def test_age_threshold(self):
        """Age >= 68 should add 1 point."""
        young = calculate_tisdale_score(age=67)
        old = calculate_tisdale_score(age=68)
        assert young["score"] == 0
        assert old["score"] == 1

    def test_female_sex(self):
        """Female sex should add 1 point."""
        male = calculate_tisdale_score(sex="male")
        female = calculate_tisdale_score(sex="female")
        assert male["score"] == 0
        assert female["score"] == 1

    def test_loop_diuretic(self):
        """Loop diuretic use should add 1 point."""
        no_diuretic = calculate_tisdale_score(loop_diuretic=False)
        with_diuretic = calculate_tisdale_score(loop_diuretic=True)
        assert no_diuretic["score"] == 0
        assert with_diuretic["score"] == 1

    def test_hypokalemia(self):
        """Potassium <= 3.5 should add 1 point."""
        normal_k = calculate_tisdale_score(potassium=3.6)
        low_k = calculate_tisdale_score(potassium=3.5)
        assert normal_k["score"] == 0
        assert low_k["score"] == 2

    def test_qtc_prolongation(self):
        """QTc >= 450 should add 2 points."""
        normal_qtc = calculate_tisdale_score(qtc=449)
        long_qtc = calculate_tisdale_score(qtc=450)
        assert normal_qtc["score"] == 0
        assert long_qtc["score"] == 2

    def test_acute_mi(self):
        """Acute MI should add 2 points."""
        no_mi = calculate_tisdale_score(acute_mi=False)
        with_mi = calculate_tisdale_score(acute_mi=True)
        assert no_mi["score"] == 0
        assert with_mi["score"] == 2

    def test_heart_failure(self):
        """Heart failure should add 3 points."""
        no_hf = calculate_tisdale_score(heart_failure=False)
        with_hf = calculate_tisdale_score(heart_failure=True)
        assert no_hf["score"] == 0
        assert with_hf["score"] == 3

    def test_multiple_qt_drugs(self):
        """Multiple QT drugs add 6 points, a single drug adds 3."""
        no_drugs = calculate_tisdale_score(num_qtdrugs=0)
        one_drug = calculate_tisdale_score(num_qtdrugs=1)
        two_drugs = calculate_tisdale_score(num_qtdrugs=2)
        assert no_drugs["score"] == 0
        assert one_drug["score"] == 3
        assert two_drugs["score"] == 6

    def test_sepsis(self):
        """Sepsis should add 3 points."""
        no_sepsis = calculate_tisdale_score(sepsis=False)
        with_sepsis = calculate_tisdale_score(sepsis=True)
        assert no_sepsis["score"] == 0
        assert with_sepsis["score"] == 3

    def test_hypoalbuminemia(self):
        """Hypoalbuminemia is not part of the Tisdale score."""
        normal_alb = calculate_tisdale_score(hypoalbuminemia=False)
        low_alb = calculate_tisdale_score(hypoalbuminemia=True)
        assert normal_alb["score"] == 0
        assert low_alb["score"] == 0
        assert low_alb["warnings"]

    def test_risk_classification_low(self):
        """Complete low-risk profile."""
        result = calculate_tisdale_score(
            age=30, sex="male", loop_diuretic=False, potassium=4,
            qtc=400, acute_mi=False, heart_failure=False,
            num_qtdrugs=0, sepsis=False
        )
        assert result["risk_classification"] == "Low Risk"

    def test_risk_classification_moderate(self):
        """Complete moderate-risk profile (9 points)."""
        result = calculate_tisdale_score(
            age=70, sex="female", loop_diuretic=False, potassium=4,
            qtc=460, acute_mi=True, heart_failure=True,
            num_qtdrugs=0, sepsis=False
        )
        assert result["score"] == 9
        assert result["risk_classification"] == "Moderate Risk"

    def test_risk_classification_high(self):
        """Complete high-risk profile."""
        result = calculate_tisdale_score(
            age=70, sex="female", loop_diuretic=False, potassium=4,
            qtc=460, acute_mi=True, heart_failure=True,
            num_qtdrugs=0, sepsis=True
        )
        assert result["score"] == 12
        assert result["risk_classification"] == "High Risk"

    def test_component_breakdown(self):
        """Result should include component breakdown."""
        result = calculate_tisdale_score(age=70, sex="female", potassium=3.2)
        assert "component_breakdown" in result
        assert len(result["component_breakdown"]) == 3

    def test_empty_input(self):
        """No parameters yield an incomplete zero-point subtotal."""
        result = calculate_tisdale_score()
        assert result["score"] == 0
        assert result["risk_classification"] == "Incomplete"

    def test_partial_input(self):
        """Partial parameters should calculate correctly."""
        result = calculate_tisdale_score(age=70, qtc=460)
        assert result["score"] == 3  # 1 (age) + 2 (qtc)


class TestInputValidation:
    """Tests for input validation functions."""

    def test_validate_identifier_valid(self):
        assert _validate_identifier("patient-001", "id") == "patient-001"

    def test_validate_identifier_strips_path_separators(self):
        result = _validate_identifier("../../etc/passwd", "path")
        assert "/" not in result
        assert "\\" not in result

    def test_validate_identifier_empty_raises(self):
        with pytest.raises(ValueError):
            _validate_identifier("", "id")

    def test_validate_numeric_valid(self):
        assert _validate_numeric(5.5, "val") == 5.5

    def test_validate_numeric_string_convertible(self):
        assert _validate_numeric("3.14", "val") == 3.14

    def test_validate_numeric_out_of_range(self):
        with pytest.raises(ValueError):
            _validate_numeric(1500, "val", max_val=1000)

    def test_validate_numeric_nan_raises(self):
        with pytest.raises(ValueError):
            _validate_numeric(float('nan'), "val")

    def test_validate_numeric_inf_raises(self):
        with pytest.raises(ValueError):
            _validate_numeric(float('inf'), "val")

    def test_validate_bool_true(self):
        assert _validate_bool(True, "flag") is True

    def test_validate_bool_false(self):
        assert _validate_bool(False, "flag") is False

    def test_validate_bool_string_true(self):
        assert _validate_bool("yes", "flag") is True

    def test_validate_bool_string_false(self):
        assert _validate_bool("no", "flag") is False


class TestCalculateMetrics:
    """Tests for the legacy calculate_metrics interface."""

    def test_basic_call(self):
        result = calculate_metrics(v1=70.0, v2=3.2, v3=460.0)
        assert "score" in result
        assert "risk_classification" in result
        assert result["score"] > 0

    def test_no_args(self):
        result = calculate_metrics()
        assert result["score"] == 0


class TestProcessBatch:
    """Tests for batch CSV processing."""

    def test_batch_creates_output(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text(
            "Patient_ID,age,sex,potassium,qtc\n"
            "PT-001,70,female,3.2,460\n"
            "PT-002,45,male,4.0,420\n",
            encoding="utf-8"
        )
        process_batch(str(csv_in), str(csv_out))
        assert csv_out.exists()

    def test_batch_output_content(self, tmp_path):
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text(
            "Patient_ID,age,sex\nPT-001,70,female\n",
            encoding="utf-8"
        )
        process_batch(str(csv_in), str(csv_out))
        content = csv_out.read_text(encoding="utf-8")
        assert "PT-001" in content
        assert "score" in content

    def test_batch_with_errors_continues(self, tmp_path):
        """Rows with invalid data should produce error entries, not crash."""
        csv_in = tmp_path / "in.csv"
        csv_out = tmp_path / "out.csv"
        csv_in.write_text(
            "Patient_ID,age\n"
            "PT-001,70\n"
            "PT-002,invalid\n",
            encoding="utf-8"
        )
        process_batch(str(csv_in), str(csv_out))
        content = csv_out.read_text(encoding="utf-8")
        assert "PT-001" in content
        assert "PT-002" in content

    def test_batch_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            process_batch(str(tmp_path / "nonexistent.csv"), str(tmp_path / "out.csv"))


class TestPathTraversal:
    """Tests for path traversal protection."""

    def test_safe_path_within_cwd(self):
        result = _safe_resolve_path("data/input.csv")
        assert os.path.isabs(result)

    def test_safe_path_null_bytes_blocked(self):
        """Null bytes in path should be rejected."""
        with pytest.raises(ValueError, match="null bytes"):
            _safe_resolve_path("data\x00/etc/passwd")

    def test_safe_path_existing_file(self, tmp_path):
        test_file = tmp_path / "test.csv"
        test_file.write_text("data")
        # Should work for any valid path
        result = _safe_resolve_path(str(test_file), must_exist=True)
        assert os.path.isabs(result)

    def test_safe_path_nonexistent_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            _safe_resolve_path(str(tmp_path / "missing.csv"), must_exist=True)
