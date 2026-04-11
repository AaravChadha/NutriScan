"""
Phase 5.1.2 + 5.1.3 — run the LLM test cases and score them per dimension.

Usage:
    python eval/llm_accuracy.py              # run + print report
    python eval/llm_accuracy.py --out r.json # also save raw JSON for the poster
    python eval/llm_accuracy.py -q           # quiet mode (summary table only)

Scoring is substring-based and case-insensitive so we score concept
capture, not exact wording. Each test case contributes multiple checks
(one per dimension — allergen, preservative, nutrient, goal, risk, min
recommendations, forbidden terms). The overall score is the count of
checks passed / checks run across all cases.

This is deliberately simple so the numbers are easy to defend in a
research talk: the LLM either flagged the concept or it didn't.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Allow `python eval/llm_accuracy.py` to find the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval.llm_test_cases import load_test_cases  # noqa: E402
from src.llm.groq_client import GroqClient  # noqa: E402
from src.nutrition.fda_guidelines import compute_dv_percentages  # noqa: E402
from src.nutrition.models import (  # noqa: E402
    AnalysisResult,
    HealthProfile,
    NutritionData,
)


@dataclass
class CheckResult:
    dimension: str
    passed: bool
    detail: str


@dataclass
class TestResult:
    case_id: str
    description: str
    analysis: dict  # AnalysisResult fields for the report
    checks: list[CheckResult] = field(default_factory=list)
    error: str | None = None

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def total_count(self) -> int:
        return len(self.checks)


# ======================================================================
# Scoring helpers
# ======================================================================


def _contains_any(needle: str, haystacks: list[str]) -> bool:
    """Case-insensitive substring search across a list of strings."""
    needle_lc = needle.lower()
    return any(needle_lc in str(h).lower() for h in haystacks)


def _contains_conflict_with(term: str, goal_alignment: list[str]) -> bool:
    """True if some goal_alignment entry mentions the term AND is a CONFLICT.

    The LLM is prompted to format goal alignment as
    "<goal>: CONFLICT — <reason>" or "<goal>: SUPPORT — <reason>". We
    want both 'CONFLICT' and the nutrient term in the same entry, since
    that's what proves the profile threaded through correctly.
    """
    term_lc = term.lower()
    for entry in goal_alignment:
        s = str(entry).lower()
        if "conflict" in s and term_lc in s:
            return True
    return False


def score_case(case: dict, analysis: AnalysisResult) -> list[CheckResult]:
    """Run all dimension checks for one test case.

    Returns a list of CheckResult (one per expectation). Empty
    expectation lists are treated as vacuously passing so a case that
    doesn't test a dimension doesn't get a false positive or negative.
    """
    expected = case["expected"]
    checks: list[CheckResult] = []

    # 1. Allergen terms — each expected term must appear somewhere in allergen_flags
    for term in expected.get("allergen_terms", []):
        hit = _contains_any(term, analysis.allergen_flags)
        checks.append(
            CheckResult(
                dimension="allergen",
                passed=hit,
                detail=f"expected '{term}' in allergen_flags — "
                + ("FOUND" if hit else f"MISSING (got {analysis.allergen_flags})"),
            )
        )

    # 2. Preservative terms
    for term in expected.get("preservative_terms", []):
        hit = _contains_any(term, analysis.preservative_flags)
        checks.append(
            CheckResult(
                dimension="preservative",
                passed=hit,
                detail=f"expected '{term}' in preservative_flags — "
                + ("FOUND" if hit else f"MISSING (got {analysis.preservative_flags})"),
            )
        )

    # 3. Nutrient flag terms
    for term in expected.get("nutrient_flag_terms", []):
        hit = _contains_any(term, analysis.nutrient_flags)
        checks.append(
            CheckResult(
                dimension="nutrient",
                passed=hit,
                detail=f"expected '{term}' in nutrient_flags — "
                + ("FOUND" if hit else f"MISSING (got {analysis.nutrient_flags})"),
            )
        )

    # 4. Goal conflict terms — must appear in an entry marked CONFLICT
    for term in expected.get("goal_conflict_terms", []):
        hit = _contains_conflict_with(term, analysis.goal_alignment)
        checks.append(
            CheckResult(
                dimension="goal",
                passed=hit,
                detail=f"expected CONFLICT entry mentioning '{term}' — "
                + ("FOUND" if hit else f"MISSING (got {analysis.goal_alignment})"),
            )
        )

    # 5. Risk level — overall_risk must be in the allowed set
    risk_set = set(expected.get("risk_in", []))
    if risk_set:
        hit = analysis.overall_risk.lower() in {r.lower() for r in risk_set}
        checks.append(
            CheckResult(
                dimension="risk",
                passed=hit,
                detail=f"overall_risk={analysis.overall_risk!r} "
                + ("∈" if hit else "∉")
                + f" {sorted(risk_set)}",
            )
        )

    # 6. Minimum recommendations
    min_recs = expected.get("min_recommendations", 0)
    if min_recs:
        hit = len(analysis.recommendations) >= min_recs
        checks.append(
            CheckResult(
                dimension="min_recs",
                passed=hit,
                detail=f"len(recommendations)={len(analysis.recommendations)} "
                + (">=" if hit else "<")
                + f" {min_recs}",
            )
        )

    # 7. Forbidden allergen terms — none of these may appear (hallucination check)
    for term in expected.get("forbidden_allergen_terms", []):
        hit = not _contains_any(term, analysis.allergen_flags)
        checks.append(
            CheckResult(
                dimension="forbidden_allergen",
                passed=hit,
                detail=f"forbidden '{term}' in allergen_flags — "
                + ("absent" if hit else f"HALLUCINATED ({analysis.allergen_flags})"),
            )
        )

    # 8. Forbidden preservative terms
    for term in expected.get("forbidden_preservative_terms", []):
        hit = not _contains_any(term, analysis.preservative_flags)
        checks.append(
            CheckResult(
                dimension="forbidden_preservative",
                passed=hit,
                detail=f"forbidden '{term}' in preservative_flags — "
                + ("absent" if hit else f"HALLUCINATED ({analysis.preservative_flags})"),
            )
        )

    return checks


# ======================================================================
# Runner
# ======================================================================


def run_evaluation(verbose: bool = True) -> list[TestResult]:
    """Run all test cases through GroqClient.analyze and score results."""
    cases = load_test_cases()
    client = GroqClient()
    results: list[TestResult] = []

    for case in cases:
        if verbose:
            print(f"\n── {case['id']} ───────────────────────────────")
            print(f"   {case['description']}")

        nutrition = NutritionData(**case["nutrition"])
        profile = HealthProfile(**case["profile"])
        dv = compute_dv_percentages(nutrition)

        try:
            analysis = client.analyze(nutrition, profile, dv)
        except Exception as e:  # pragma: no cover — defensive
            if verbose:
                print(f"   ERROR: {e}")
            results.append(
                TestResult(
                    case_id=case["id"],
                    description=case["description"],
                    analysis={},
                    error=str(e),
                )
            )
            continue

        checks = score_case(case, analysis)
        result = TestResult(
            case_id=case["id"],
            description=case["description"],
            analysis={
                "allergen_flags": analysis.allergen_flags,
                "preservative_flags": analysis.preservative_flags,
                "nutrient_flags": analysis.nutrient_flags,
                "goal_alignment": analysis.goal_alignment,
                "recommendations": analysis.recommendations,
                "overall_risk": analysis.overall_risk,
                "summary": analysis.summary,
            },
            checks=checks,
        )
        results.append(result)

        if verbose:
            print(
                f"   → {result.passed_count}/{result.total_count} checks passed "
                f"(risk={analysis.overall_risk})"
            )
            for check in checks:
                marker = "✓" if check.passed else "✗"
                print(f"     {marker} [{check.dimension}] {check.detail}")

    return results


# ======================================================================
# Reporting
# ======================================================================


def print_report(results: list[TestResult]) -> None:
    """Print a summary table + per-dimension pass rates."""
    total_checks = sum(r.total_count for r in results)
    total_passed = sum(r.passed_count for r in results)

    print("\n" + "=" * 70)
    print("PHASE 5.1 — LLM EVALUATION REPORT")
    print("=" * 70)

    # Per-case summary
    print("\nPer-case results:")
    print(f"  {'case':<32} {'passed':<10} {'risk':<10} {'status'}")
    print(f"  {'-' * 32} {'-' * 10} {'-' * 10} {'-' * 10}")
    for r in results:
        if r.error:
            status = "ERROR"
            passed_str = "-"
            risk = "-"
        else:
            passed_str = f"{r.passed_count}/{r.total_count}"
            risk = r.analysis.get("overall_risk", "?")
            status = "PASS" if r.passed_count == r.total_count else "PARTIAL"
        print(f"  {r.case_id:<32} {passed_str:<10} {risk:<10} {status}")

    # Per-dimension pass rate (useful for the poster)
    dim_stats: dict[str, tuple[int, int]] = {}
    for r in results:
        for check in r.checks:
            passed, total = dim_stats.get(check.dimension, (0, 0))
            dim_stats[check.dimension] = (
                passed + (1 if check.passed else 0),
                total + 1,
            )

    print("\nPer-dimension pass rate:")
    for dim in sorted(dim_stats):
        passed, total = dim_stats[dim]
        pct = 100.0 * passed / total if total else 0.0
        print(f"  {dim:<24} {passed}/{total}  ({pct:5.1f}%)")

    print("\nOverall:")
    overall_pct = 100.0 * total_passed / total_checks if total_checks else 0.0
    print(f"  {total_passed}/{total_checks} checks passed ({overall_pct:.1f}%)")
    print("=" * 70)


def save_json(results: list[TestResult], path: str) -> None:
    """Serialize results to disk so the poster slide can reference the raw run."""
    payload = [
        {
            "case_id": r.case_id,
            "description": r.description,
            "analysis": r.analysis,
            "checks": [asdict(c) for c in r.checks],
            "passed_count": r.passed_count,
            "total_count": r.total_count,
            "error": r.error,
        }
        for r in results
    ]
    Path(path).write_text(json.dumps(payload, indent=2))
    print(f"\nSaved raw results to {path}")


def save_markdown_report(results: list[TestResult], path: str) -> None:
    """Write a human-readable markdown report suitable for the poster slide.

    Regenerated on every run so it always reflects the latest numbers;
    commit the refreshed file whenever prompts or test cases change.
    """
    total_checks = sum(r.total_count for r in results)
    total_passed = sum(r.passed_count for r in results)
    overall_pct = 100.0 * total_passed / total_checks if total_checks else 0.0

    # Per-dimension rollup
    dim_stats: dict[str, tuple[int, int]] = {}
    for r in results:
        for check in r.checks:
            passed, total = dim_stats.get(check.dimension, (0, 0))
            dim_stats[check.dimension] = (
                passed + (1 if check.passed else 0),
                total + 1,
            )

    lines: list[str] = []
    lines.append("# Phase 5.1 — LLM Evaluation Results")
    lines.append("")
    lines.append(
        f"**Overall:** {total_passed}/{total_checks} checks passed "
        f"(**{overall_pct:.1f}%**) across {len(results)} test cases."
    )
    lines.append("")
    lines.append(
        "Scoring is substring-based and case-insensitive — we test whether "
        "the LLM captures each concept, not whether it matches exact wording, "
        "because Groq phrases things differently across temperature=0.3 runs."
    )
    lines.append("")

    # Per-dimension table
    lines.append("## Per-dimension pass rate")
    lines.append("")
    lines.append("| Dimension | Passed | Total | Rate |")
    lines.append("|---|---|---|---|")
    for dim in sorted(dim_stats):
        passed, total = dim_stats[dim]
        pct = 100.0 * passed / total if total else 0.0
        lines.append(f"| {dim} | {passed} | {total} | {pct:.1f}% |")
    lines.append("")

    # Per-case summary
    lines.append("## Per-case summary")
    lines.append("")
    lines.append("| Case | Passed | Risk | Status |")
    lines.append("|---|---|---|---|")
    for r in results:
        if r.error:
            status = "ERROR"
            passed_str = "-"
            risk = "-"
        else:
            passed_str = f"{r.passed_count}/{r.total_count}"
            risk = r.analysis.get("overall_risk", "?")
            status = "PASS" if r.passed_count == r.total_count else "PARTIAL"
        lines.append(f"| `{r.case_id}` | {passed_str} | {risk} | {status} |")
    lines.append("")

    # Per-case details
    lines.append("## Per-case detail")
    lines.append("")
    for r in results:
        lines.append(f"### `{r.case_id}`")
        lines.append("")
        lines.append(f"_{r.description}_")
        lines.append("")
        if r.error:
            lines.append(f"**ERROR:** {r.error}")
            lines.append("")
            continue

        lines.append(f"- **Overall risk:** `{r.analysis.get('overall_risk', '?')}`")
        lines.append(f"- **Summary:** {r.analysis.get('summary', '')}")
        lines.append("")

        for section in (
            "allergen_flags",
            "preservative_flags",
            "nutrient_flags",
            "goal_alignment",
            "recommendations",
        ):
            items = r.analysis.get(section, [])
            if not items:
                lines.append(f"- **{section}:** (none)")
                continue
            lines.append(f"- **{section}:**")
            for item in items:
                lines.append(f"  - {item}")
        lines.append("")

        lines.append("**Checks:**")
        lines.append("")
        for check in r.checks:
            marker = "✓" if check.passed else "✗"
            lines.append(f"- {marker} **[{check.dimension}]** {check.detail}")
        lines.append("")

    Path(path).write_text("\n".join(lines) + "\n")
    print(f"Saved markdown report to {path}")


# ======================================================================
# CLI entry point
# ======================================================================


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the LLM evaluation suite.")
    parser.add_argument(
        "--out", help="Save raw results to a JSON file (for the poster)."
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Suppress per-check detail output."
    )
    args = parser.parse_args()

    results = run_evaluation(verbose=not args.quiet)
    print_report(results)

    # Always regenerate the markdown report as the primary written record
    # for Phase 5.1.4 / poster slide. JSON export is opt-in via --out.
    save_markdown_report(results, "eval/llm_accuracy_report.md")

    if args.out:
        save_json(results, args.out)

    # Non-zero exit if any case errored or any check failed — this lets us
    # wire the eval into CI later if we want to gate prompt changes on it.
    any_failures = any(
        r.error is not None or r.passed_count < r.total_count for r in results
    )
    return 1 if any_failures else 0


if __name__ == "__main__":
    sys.exit(main())
