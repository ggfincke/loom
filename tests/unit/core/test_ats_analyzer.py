# tests/unit/core/test_ats_analyzer.py
# Unit tests for ATS compatibility analyzer

from pathlib import Path
import pytest

from src.core.ats_analyzer import (
    ATSReport,
    ATSIssue,
    Severity,
    IssueCategory,
    calculate_score,
    generate_recommendations,
    analyze_docx_structure,
    analyze_resume_ats,
)


# * Test data structures
class TestATSIssue:
    # * Verify issue creation
    def test_issue_creation(self):
        issue = ATSIssue(
            category=IssueCategory.TABLE,
            severity=Severity.CRITICAL,
            description="Table detected",
            location="Line 5",
            suggestion="Remove table",
        )
        assert issue.category == IssueCategory.TABLE
        assert issue.severity == Severity.CRITICAL
        assert issue.description == "Table detected"
        assert issue.location == "Line 5"
        assert issue.suggestion == "Remove table"

    # * Verify issue to dict
    def test_issue_to_dict(self):
        issue = ATSIssue(
            category=IssueCategory.COLUMNS,
            severity=Severity.WARNING,
            description="Multi-column layout",
        )
        d = issue.to_dict()
        assert d["category"] == "columns"
        assert d["severity"] == "warning"
        assert d["description"] == "Multi-column layout"
        assert d["location"] is None
        assert d["suggestion"] is None


class TestATSReport:
    # * Verify report creation
    def test_report_creation(self):
        report = ATSReport(score=85)
        assert report.score == 85
        assert report.issues == []
        assert report.recommendations == []
        assert report.file_type == "docx"

    # * Verify report w/ issues
    def test_report_with_issues(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table found"),
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header text"),
            ATSIssue(IssueCategory.SECTION_HEADERS, Severity.INFO, "Non-standard"),
        ]
        report = ATSReport(score=65, issues=issues)
        assert report.critical_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1
        assert not report.passed  # has critical issues

    # * Verify report passed no critical
    def test_report_passed_no_critical(self):
        issues = [
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header text"),
            ATSIssue(IssueCategory.SECTION_HEADERS, Severity.INFO, "Non-standard"),
        ]
        report = ATSReport(score=88, issues=issues)
        assert report.passed  # no critical issues

    # * Verify report issues by severity
    def test_report_issues_by_severity(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table 1"),
            ATSIssue(IssueCategory.COLUMNS, Severity.CRITICAL, "Columns"),
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header"),
        ]
        report = ATSReport(score=50, issues=issues)
        critical = report.issues_by_severity(Severity.CRITICAL)
        assert len(critical) == 2
        warning = report.issues_by_severity(Severity.WARNING)
        assert len(warning) == 1
        info = report.issues_by_severity(Severity.INFO)
        assert len(info) == 0

    # * Verify report to dict
    def test_report_to_dict(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table found"),
        ]
        report = ATSReport(
            score=75,
            issues=issues,
            recommendations=["Remove tables"],
        )
        d = report.to_dict()
        assert d["version"] == 1
        assert d["score"] == 75
        assert d["passed"] is False
        assert d["file_type"] == "docx"
        assert d["summary"]["critical"] == 1
        assert d["summary"]["warning"] == 0
        assert d["summary"]["info"] == 0
        assert d["summary"]["total"] == 1
        assert len(d["issues"]) == 1
        assert d["recommendations"] == ["Remove tables"]


# * Test score calculation
class TestScoreCalculation:
    # * Verify perfect score no issues
    def test_perfect_score_no_issues(self):
        score = calculate_score([])
        assert score == 100

    # * Verify critical penalty
    def test_critical_penalty(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table"),
        ]
        score = calculate_score(issues)
        assert score == 75  # 100 - 25

    # * Verify warning penalty
    def test_warning_penalty(self):
        issues = [
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header"),
        ]
        score = calculate_score(issues)
        assert score == 90  # 100 - 10

    # * Verify info penalty
    def test_info_penalty(self):
        issues = [
            ATSIssue(IssueCategory.SECTION_HEADERS, Severity.INFO, "Info"),
        ]
        score = calculate_score(issues)
        assert score == 98  # 100 - 2

    # * Verify multiple issues
    def test_multiple_issues(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table"),
            ATSIssue(IssueCategory.COLUMNS, Severity.CRITICAL, "Columns"),
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header"),
        ]
        score = calculate_score(issues)
        assert score == 40  # 100 - 25 - 25 - 10

    # * Verify score floors at zero
    def test_score_floors_at_zero(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "1"),
            ATSIssue(IssueCategory.COLUMNS, Severity.CRITICAL, "2"),
            ATSIssue(IssueCategory.TEXTBOX, Severity.CRITICAL, "3"),
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "4"),
            ATSIssue(IssueCategory.COLUMNS, Severity.CRITICAL, "5"),
        ]
        score = calculate_score(issues)
        assert score == 0  # can't go negative


# * Test recommendation generation
class TestRecommendationGeneration:
    # * Verify no recommendations no issues
    def test_no_recommendations_no_issues(self):
        recs = generate_recommendations([])
        assert recs == []

    # * Verify table recommendation
    def test_table_recommendation(self):
        issues = [ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table")]
        recs = generate_recommendations(issues)
        assert any("table" in r.lower() for r in recs)

    # * Verify column recommendation
    def test_column_recommendation(self):
        issues = [ATSIssue(IssueCategory.COLUMNS, Severity.CRITICAL, "Columns")]
        recs = generate_recommendations(issues)
        assert any("column" in r.lower() for r in recs)

    # * Verify header footer recommendation
    def test_header_footer_recommendation(self):
        issues = [ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header")]
        recs = generate_recommendations(issues)
        assert any("header" in r.lower() or "footer" in r.lower() for r in recs)

    # * Verify multiple unique recommendations
    def test_multiple_unique_recommendations(self):
        issues = [
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table 1"),
            ATSIssue(IssueCategory.TABLE, Severity.CRITICAL, "Table 2"),
            ATSIssue(IssueCategory.HEADER_FOOTER, Severity.WARNING, "Header"),
        ]
        recs = generate_recommendations(issues)
        # should only have one recommendation per category
        assert len(recs) == 2


# * Test structural analysis w/ fixtures
class TestStructuralAnalysis:
    @pytest.fixture
    def fixtures_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "fixtures" / "documents"

    # Resume without tables/columns/etc should have no structural issues.
    # * Verify clean resume no issues
    def test_clean_resume_no_issues(self, fixtures_dir):
        clean_resume = fixtures_dir / "basic_formatted_resume.docx"
        if not clean_resume.exists():
            pytest.skip("Test fixture not found")
        issues = analyze_docx_structure(clean_resume)
        # should have no critical structural issues
        critical = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(critical) == 0

    # Resume w/ tables/headers should be flagged.
    # * Verify problem resume has issues
    def test_problem_resume_has_issues(self, fixtures_dir):
        problem_resume = fixtures_dir / "ats_problem_resume.docx"
        if not problem_resume.exists():
            pytest.skip("Test fixture not found")
        issues = analyze_docx_structure(problem_resume)
        # should detect tables
        table_issues = [i for i in issues if i.category == IssueCategory.TABLE]
        assert len(table_issues) > 0
        # should detect header/footer content
        header_footer_issues = [
            i for i in issues if i.category == IssueCategory.HEADER_FOOTER
        ]
        assert len(header_footer_issues) > 0


# * Test full analysis pipeline
class TestFullAnalysis:
    @pytest.fixture
    def fixtures_dir(self) -> Path:
        return Path(__file__).parent.parent.parent / "fixtures" / "documents"

    # Clean resume should score high.
    # * Verify analyze clean resume
    def test_analyze_clean_resume(self, fixtures_dir):
        clean_resume = fixtures_dir / "basic_formatted_resume.docx"
        if not clean_resume.exists():
            pytest.skip("Test fixture not found")
        report = analyze_resume_ats(clean_resume)
        assert report.score >= 80
        assert report.passed

    # Problem resume should have low score.
    # * Verify analyze problem resume
    def test_analyze_problem_resume(self, fixtures_dir):
        problem_resume = fixtures_dir / "ats_problem_resume.docx"
        if not problem_resume.exists():
            pytest.skip("Test fixture not found")
        report = analyze_resume_ats(problem_resume)
        assert report.score < 80
        assert report.critical_count > 0
        assert len(report.recommendations) > 0

    # Full report should have score, issues, & recommendations.
    # * Verify report includes all components
    def test_report_includes_all_components(self, fixtures_dir):
        problem_resume = fixtures_dir / "ats_problem_resume.docx"
        if not problem_resume.exists():
            pytest.skip("Test fixture not found")
        report = analyze_resume_ats(problem_resume)
        # verify structure
        assert isinstance(report.score, int)
        assert 0 <= report.score <= 100
        assert isinstance(report.issues, list)
        assert isinstance(report.recommendations, list)
        # verify JSON export works
        d = report.to_dict()
        assert "version" in d
        assert "score" in d
        assert "issues" in d
        assert "recommendations" in d
