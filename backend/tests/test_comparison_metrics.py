"""Offline arithmetic, assurance, exclusion and read-only operator contracts."""

import json
import math

import pytest

from backend.app.comparison import metrics
from backend.app.comparison.exploratory import match_exploratory
from backend.app.comparison.metrics import execute_exploratory_metrics as real_execute
from backend.app.schemas.comparison_metrics import summarize_residuals
from backend.app.schemas.exploratory_matching import ExploratoryMatchingReport
from backend.app.schemas.matching import NativeMatchingInput
from backend.app.storage import product_common
from backend.tests.test_exploratory_matching import example as example
from backend.tests.test_matching_engine import collection as collection
from backend.tests.test_matching_execution import integrated as integrated
from backend.tests.test_matching_local import audit_inputs as audit_inputs
from backend.tests.test_matching_local import pipeline as pipeline
from scripts import run_exploratory_metrics as cli


@pytest.fixture
def matching(example):
    return match_exploratory(*example)


@pytest.fixture
def report(matching):
    return metrics.summarize_exploratory(matching)


def test_known_native_residuals_and_no_source_changes(matching, report):
    before = matching.model_dump_json()
    assert report.summary.matched_pair_count == 6
    assert report.summary.bias == -0.25 and report.summary.rmse == 0.25
    assert all(r.model_minus_observation == -0.25 for r in report.residuals)
    assert (
        report.summary.total_sample_count == report.summary.evaluated_sample_count == 6
    )
    assert (
        report.summary.excluded_sample_count
        == report.summary.unevaluated_sample_count
        == 0
    )
    assert report.matching == matching and matching.model_dump_json() == before
    assert not report.comparison_ready and not report.independent_validation
    assert report.matching.strict_assessment.status == "blocked"
    assert report.weighting == "equal_weight_per_matched_sample"
    assert report.uncertainty == "not_propagated"
    assert metrics.serialize_metrics(report) == metrics.serialize_metrics(
        metrics.summarize_exploratory(matching)
    )


@pytest.mark.parametrize(
    "values,bias,rmse",
    [
        ((), None, None),
        ((0.0,), 0.0, 0.0),
        ((2.0,), 2.0, 2.0),
        ((-3.0, 4.0), 0.5, math.sqrt(12.5)),
        ((-2.0, 2.0), 0.0, 2.0),
        ((1e308, 1e308), 1e308, 1e308),
        ((-1e308, 1e308), 0.0, 1e308),
        ((5e-324, 5e-324), 5e-324, 5e-324),
    ],
)
def test_formula_boundaries(values, bias, rmse):
    actual_bias, actual_rmse = summarize_residuals(values)
    assert actual_bias == bias
    assert (
        actual_rmse == pytest.approx(rmse) if rmse is not None else actual_rmse is None
    )


@pytest.mark.parametrize(
    "values", [(float("nan"),), (float("inf"),), (-float("inf"),), (1.0,) * 5001]
)
def test_nonfinite_or_oversized_arithmetic_rejected(values):
    with pytest.raises(ValueError):
        summarize_residuals(values)


def reject_rows(matching, indices, reason="nearest_cell_masked", partial=False):
    """Explicit synthetic aggregation fixture; not authentic on-disk matching."""
    d = matching.model_dump()
    for i in indices:
        d["results"][i]["matched"] = False
        d["results"][i]["exclusions"] = (reason,)
    count = sum(row["matched"] for row in d["results"])
    d["matched_pair_count"] = count
    d["status"] = "partially_blocked" if partial else "evaluated"
    d["overlap_status"] = (
        "matched" if count else "not_evaluated" if partial else "no_valid_pairs"
    )
    return ExploratoryMatchingReport.model_validate(d)


@pytest.mark.parametrize("partial", [False, True])
def test_zero_pairs_are_null_not_zero(matching, partial):
    reason = "support_unresolved" if partial else "nearest_cell_masked"
    result = metrics.summarize_exploratory(
        reject_rows(matching, range(6), reason, partial)
    )
    assert result.summary.bias is result.summary.rmse is None
    assert not result.summary.metrics_available and result.residuals == ()
    assert result.summary.excluded_sample_count == 6
    assert result.summary.exclusion_counts == {reason: 6}
    assert result.status == ("partially_blocked" if partial else "evaluated")
    assert result.matching.overlap_status == (
        "not_evaluated" if partial else "no_valid_pairs"
    )


def test_one_pair_partial_summary_and_repeated_exclusion_counts(matching):
    m = reject_rows(matching, range(5), "support_unresolved", True)
    d = m.model_dump()
    d["results"][0]["exclusions"] = (
        "support_unresolved",
        "support_unresolved",
        "nearest_cell_masked",
    )
    result = metrics.summarize_exploratory(ExploratoryMatchingReport.model_validate(d))
    assert (
        result.summary.matched_pair_count == 1 and result.status == "partially_blocked"
    )
    assert result.summary.bias == -0.25 and result.summary.rmse == 0.25
    assert result.summary.exclusion_counts == {
        "support_unresolved": 5,
        "nearest_cell_masked": 1,
    }
    assert result.summary.excluded_sample_count == 5  # Reasons overlap, not samples.
    assert result.residuals[0].sample_id == matching.results[5].sample_id


def test_blocked_matching_has_unevaluated_not_excluded_samples(example):
    r, s = example
    d = r.model_dump()
    d["context"]["adjusted_depth_alignment"] = {"status": "unresolved"}
    blocked = match_exploratory(NativeMatchingInput.model_validate(d), s)
    result = metrics.summarize_exploratory(blocked)
    assert result.status == "blocked" and not result.summary.metrics_available
    assert (
        result.summary.total_sample_count
        == result.summary.unevaluated_sample_count
        == 6
    )
    assert (
        result.summary.evaluated_sample_count
        == result.summary.excluded_sample_count
        == 0
    )
    assert result.summary.bias is result.summary.rmse is None
    assert "adjusted_depth_alignment_unresolved" in result.matching.blockers


def test_equal_point_weighting_and_sign(matching):
    d = matching.model_dump()
    differences = (-3.0, 4.0, -3.0, 4.0, -3.0, 4.0)
    for row, delta in zip(d["results"], differences, strict=True):
        row["candidate"]["model_value"] = row["observation_value"] + delta
    result = metrics.summarize_exploratory(ExploratoryMatchingReport.model_validate(d))
    assert result.summary.bias == 0.5
    assert result.summary.rmse == pytest.approx(math.sqrt(12.5))
    assert tuple(r.model_minus_observation for r in result.residuals) == differences


@pytest.mark.parametrize(
    "kind",
    [
        "bias",
        "rmse",
        "count",
        "empty_zero",
        "residual",
        "identity",
        "hash",
        "mode",
        "ready",
        "assurance",
        "reason",
    ],
)
def test_forged_metrics_fail_serialization(report, kind):
    d = report.model_dump()
    if kind in ("bias", "rmse"):
        d["summary"][kind] = 99.0
    elif kind == "count":
        d["summary"]["matched_pair_count"] = 0
    elif kind == "empty_zero":
        d["summary"]["metrics_available"] = False
    elif kind == "residual":
        d["residuals"][0]["model_minus_observation"] = 0.25
    elif kind == "identity":
        d["residuals"][0]["source_sample_index"] = 10000
    elif kind == "hash":
        d["matching_sha256"] = "0" * 64
    elif kind == "mode":
        d["data_mode"] = "real"
    elif kind == "ready":
        d["comparison_ready"] = True
    elif kind == "assurance":
        d["assurance"] = "verified"
    else:
        d["summary"]["exclusion_counts"] = {"invented": 6}
    with pytest.raises(ValueError):
        metrics.serialize_metrics(type(report).model_construct(**d))


def test_wrong_report_type_rejected(matching):
    with pytest.raises(ValueError):
        metrics.summarize_exploratory(matching.strict_assessment)


def test_residual_overflow_fails_instead_of_serializing_infinity(matching):
    d = matching.model_dump()
    d["results"][0]["observation_value"] = -1e308
    d["results"][0]["candidate"]["model_value"] = 1e308
    with pytest.raises(ValueError):
        metrics.summarize_exploratory(ExploratoryMatchingReport.model_validate(d))


def test_output_budget_generation_and_serialization(matching, report, monkeypatch):
    monkeypatch.setattr(metrics, "MAX_METRICS_BYTES", 1)
    with pytest.raises(ValueError, match="budget"):
        metrics.summarize_exploratory(matching)
    with pytest.raises(ValueError, match="budget"):
        metrics.serialize_metrics(report)


def test_operator_uses_fresh_authenticated_matching(example, matching, monkeypatch):
    r, _ = example
    calls = []

    def matching_job(*args):
        calls.append(args)
        return matching

    monkeypatch.setattr(metrics, "execute_exploratory", matching_job)
    result = metrics.execute_exploratory_metrics("root", r.policy, "support")
    assert calls == [("root", r.policy, "support")]
    assert result.matching == matching


@pytest.fixture
def cli_setup(example, report, tmp_path, monkeypatch):
    path = tmp_path / "policy.yaml"
    path.write_text(example[0].policy.model_dump_json())
    monkeypatch.setattr(cli, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: report)
    return path


def test_cli_requires_opt_in_then_prints_json_only(cli_setup, capsys):
    before = cli_setup.read_bytes()
    with pytest.raises(SystemExit):
        cli.main(["--policy", "policy.yaml"])
    capsys.readouterr()
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 0
    output = capsys.readouterr()
    assert (
        not output.err and json.loads(output.out)["summary"]["matched_pair_count"] == 6
    )
    assert cli_setup.read_bytes() == before


@pytest.mark.parametrize("content", ["private: SECRET", "[broken", " " * 16385])
def test_bad_or_oversized_policy_is_sanitized(cli_setup, capsys, content):
    cli_setup.write_text(content)
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 2
    output = capsys.readouterr()
    assert not output.out and "SECRET" not in output.err


def test_policy_changed_before_output_is_rejected(cli_setup, capsys, monkeypatch):
    original = product_common.describe_file
    calls = 0

    def changed(*args):
        nonlocal calls
        calls += 1
        value = original(*args)
        return (
            value
            if calls == 1
            else value.model_copy(update={"modified_ns": value.modified_ns + 1})
        )

    monkeypatch.setattr(product_common, "describe_file", changed)
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 2
    assert not capsys.readouterr().out


def test_changed_sources_or_private_errors_do_not_leak(cli_setup, monkeypatch, capsys):
    def fail(*args):
        raise product_common.ProductError(
            "matching_execution_inputs_changed", "PRIVATE_SECRET"
        )

    # Restore the actual adapter instead of the CLI fixture's report stub.
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", real_execute)
    monkeypatch.setattr(metrics, "execute_exploratory", fail)
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 2
    output = capsys.readouterr()
    assert not output.out and "PRIVATE_SECRET" not in output.err
    assert "matching_execution_inputs_changed" in output.err


def test_cli_partial_returns_three_with_visible_subset(
    cli_setup, matching, monkeypatch, capsys
):
    result = metrics.summarize_exploratory(
        reject_rows(matching, [0], "support_unresolved", True)
    )
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: result)
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 3
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "partially_blocked"
    assert output["summary"]["matched_pair_count"] == 5


def test_cli_evaluated_empty_is_success_without_fabricated_metrics(
    cli_setup, matching, monkeypatch, capsys
):
    result = metrics.summarize_exploratory(reject_rows(matching, range(6)))
    monkeypatch.setattr(metrics, "execute_exploratory_metrics", lambda *a: result)
    assert cli.main(["--policy", "policy.yaml", "--accept-assumptions"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["summary"]["bias"] is None
    assert output["summary"]["rmse"] is None
    assert not output["summary"]["metrics_available"]
