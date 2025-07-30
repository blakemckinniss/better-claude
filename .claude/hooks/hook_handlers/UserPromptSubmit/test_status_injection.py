"""Test status and coverage injection for quality awareness."""

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional


class TestStatusAnalyzer:
    """Analyze test results and coverage data."""

    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir)

    def _get_failure_message(self, testcase_element) -> str:
        """Safely extract failure message from testcase element."""
        failure_elem = testcase_element.find(".//failure")
        if failure_elem is not None:
            return failure_elem.get("message", "Unknown failure")

        error_elem = testcase_element.find(".//error")
        if error_elem is not None:
            return error_elem.get("message", "Unknown error")

        return "Unknown error"

    def _find_pytest_results(self) -> Optional[Dict[str, Any]]:
        """Find pytest results from various sources."""
        # Check for pytest-json-report output
        json_reports = list(
            self.project_dir.glob("**/.pytest_cache/pytest-report.json")
        )
        if json_reports:
            try:
                with open(json_reports[0]) as f:
                    report = json.load(f)
                    return {
                        "passed": report.get("summary", {}).get("passed", 0),
                        "failed": report.get("summary", {}).get("failed", 0),
                        "skipped": report.get("summary", {}).get("skipped", 0),
                        "duration": report.get("duration", 0),
                        "failures": [
                            {
                                "test": test["nodeid"],
                                "message": test.get("call", {}).get(
                                    "longrepr", "Unknown error"
                                ),
                            }
                            for test in report.get("tests", [])
                            if test.get("outcome") == "failed"
                        ][:3],  # Top 3 failures
                    }
            except:
                pass

        # Check for junit XML output
        junit_files = list(self.project_dir.glob("**/pytest-junit.xml")) + list(
            self.project_dir.glob("**/test-results.xml")
        )
        if junit_files:
            try:
                import xml.etree.ElementTree as ET

                tree = ET.parse(junit_files[0])
                root = tree.getroot()

                # Parse test suite results
                testsuite = root.find(".//testsuite") or root
                return {
                    "passed": int(testsuite.get("tests", 0))
                    - int(testsuite.get("failures", 0))
                    - int(testsuite.get("errors", 0)),
                    "failed": int(testsuite.get("failures", 0))
                    + int(testsuite.get("errors", 0)),
                    "skipped": int(testsuite.get("skipped", 0)),
                    "duration": float(testsuite.get("time", 0)),
                    "failures": [
                        {
                            "test": tc.get("name", "Unknown"),
                            "message": self._get_failure_message(tc),
                        }
                        for tc in root.findall(".//testcase")
                        if tc.find(".//failure") is not None
                        or tc.find(".//error") is not None
                    ][:3],
                }
            except:
                pass

        return None

    def _find_jest_results(self) -> Optional[Dict[str, Any]]:
        """Find Jest test results."""
        # Check for jest-results.json
        jest_results = list(self.project_dir.glob("**/jest-results.json"))
        if jest_results:
            try:
                with open(jest_results[0]) as f:
                    data = json.load(f)
                    return {
                        "passed": data.get("numPassedTests", 0),
                        "failed": data.get("numFailedTests", 0),
                        "skipped": data.get("numPendingTests", 0),
                        "duration": (data.get("endTime", 0) - data.get("startTime", 0))
                        / 1000,
                        "failures": [
                            {
                                "test": (
                                    result.get("ancestorTitles", [])[-1]
                                    if result.get("ancestorTitles")
                                    else "Unknown"
                                ),
                                "message": result.get(
                                    "failureMessages", ["Unknown error"]
                                )[0],
                            }
                            for result in data.get("testResults", [])
                            for assertion in result.get("assertionResults", [])
                            if assertion.get("status") == "failed"
                        ][:3],
                    }
            except:
                pass

        return None

    def _find_coverage_data(self) -> Optional[Dict[str, Any]]:
        """Find coverage data from various sources."""
        coverage_data = {}

        # Python coverage
        coverage_files = list(self.project_dir.glob("**/.coverage")) + list(
            self.project_dir.glob("**/coverage.json")
        )
        if coverage_files:
            try:
                # Try to read coverage.py JSON format
                json_cov = self.project_dir / "coverage.json"
                if json_cov.exists():
                    with open(json_cov) as f:
                        data = json.load(f)
                        total_lines = sum(
                            len(v["executed_lines"]) + len(v["missing_lines"])
                            for v in data["files"].values()
                        )
                        covered_lines = sum(
                            len(v["executed_lines"]) for v in data["files"].values()
                        )
                        coverage_data["python"] = {
                            "percentage": (
                                (covered_lines / total_lines * 100)
                                if total_lines > 0
                                else 0
                            ),
                            "files": len(data["files"]),
                            "uncovered_files": [
                                {
                                    "file": f,
                                    "coverage": len(d["executed_lines"])
                                    / (
                                        len(d["executed_lines"])
                                        + len(d["missing_lines"])
                                    )
                                    * 100,
                                }
                                for f, d in data["files"].items()
                                if len(d["missing_lines"]) > 0
                            ][:5],  # Top 5 uncovered files
                        }
                else:
                    # Try to parse .coverage SQLite file
                    import sqlite3

                    conn = sqlite3.connect(coverage_files[0])
                    cursor = conn.cursor()

                    # Get summary stats
                    cursor.execute("SELECT COUNT(DISTINCT file_id) FROM line_bits")
                    file_count = cursor.fetchone()[0]

                    coverage_data["python"] = {
                        "files": file_count,
                        "status": "Coverage data found (details in .coverage file)",
                    }
                    conn.close()
            except:
                pass

        # JavaScript coverage (Jest/NYC)
        lcov_files = list(self.project_dir.glob("**/lcov.info")) + list(
            self.project_dir.glob("**/coverage-final.json")
        )
        if lcov_files:
            try:
                if lcov_files[0].name == "coverage-final.json":
                    with open(lcov_files[0]) as f:
                        data = json.load(f)
                        total_statements = 0
                        covered_statements = 0

                        for file_data in data.values():
                            statements = file_data.get("s", {})
                            total_statements += len(statements)
                            covered_statements += sum(
                                1 for v in statements.values() if v > 0
                            )

                        coverage_data["javascript"] = {
                            "percentage": (
                                (covered_statements / total_statements * 100)
                                if total_statements > 0
                                else 0
                            ),
                            "files": len(data),
                        }
                else:
                    # Parse lcov.info
                    with open(lcov_files[0]) as f:
                        content = f.read()
                        # Extract summary line
                        match = re.search(r"LF:(\d+)\s+LH:(\d+)", content)
                        if match:
                            total_lines = int(match.group(1))
                            hit_lines = int(match.group(2))
                            coverage_data["javascript"] = {
                                "percentage": (
                                    (hit_lines / total_lines * 100)
                                    if total_lines > 0
                                    else 0
                                ),
                            }
            except:
                pass

        return coverage_data if coverage_data else None

    def find_test_results(self) -> Dict[str, Any]:
        """Find and parse recent test results."""
        results = {
            "pytest": self._find_pytest_results(),
            "jest": self._find_jest_results(),
            "coverage": self._find_coverage_data(),
        }

        # Remove empty results
        return {k: v for k, v in results.items() if v}

    def get_ci_status(self) -> Optional[Dict[str, Any]]:
        """Get CI/CD pipeline status if available."""
        ci_data = {}

        # GitHub Actions
        ga_dir = self.project_dir / ".github" / "workflows"
        if ga_dir.exists():
            ci_data["github_actions"] = {
                "workflows": len(list(ga_dir.glob("*.yml")))
                + len(list(ga_dir.glob("*.yaml"))),
                "status": "Check GitHub for latest run status",
            }

        # GitLab CI
        if (self.project_dir / ".gitlab-ci.yml").exists():
            ci_data["gitlab_ci"] = {"configured": True}

        # Jenkins
        if (self.project_dir / "Jenkinsfile").exists():
            ci_data["jenkins"] = {"configured": True}

        return ci_data if ci_data else None


async def get_test_status_injection(prompt: str, project_dir: str) -> str:
    """Create test status injection."""
    analyzer = TestStatusAnalyzer(project_dir)

    try:
        test_results = analyzer.find_test_results()
        ci_status = analyzer.get_ci_status()

        if not test_results and not ci_status:
            return ""

        injection_parts = []

        # Test results summary
        for framework, results in test_results.items():
            if framework == "coverage":
                continue  # Handle separately

            if isinstance(results, dict) and "passed" in results:
                total = (
                    results["passed"] + results["failed"] + results.get("skipped", 0)
                )
                status = "✅" if results["failed"] == 0 else "❌"

                injection_parts.append(
                    f"{status} {framework.upper()}: {results['passed']}/{total} passed",
                )

                # Add failure details
                if results.get("failures"):
                    injection_parts.append("  Recent failures:")
                    for failure in results["failures"]:
                        test_name = (
                            failure["test"].split("::")[-1]
                            if "::" in failure["test"]
                            else failure["test"]
                        )
                        injection_parts.append(f"  - {test_name[:50]}")

        # Coverage summary
        coverage_data = test_results.get("coverage", {})
        for lang, cov in coverage_data.items():
            if "percentage" in cov:
                emoji = (
                    "🟢"
                    if cov["percentage"] > 80
                    else "🟡"
                    if cov["percentage"] > 60
                    else "🔴"
                )
                injection_parts.append(
                    f"{emoji} {lang.capitalize()} coverage: {cov['percentage']:.1f}%",
                )

                # Low coverage files
                if cov.get("uncovered_files"):
                    injection_parts.append("  Low coverage files:")
                    for file_info in cov["uncovered_files"][:3]:
                        filename = Path(file_info["file"]).name
                        injection_parts.append(
                            f"  - {filename}: {file_info['coverage']:.0f}%"
                        )

        # CI status
        if ci_status:
            injection_parts.append(f"CI/CD: {', '.join(ci_status.keys())}")

        if injection_parts:
            # Check if tests mentioned in prompt
            test_keywords = [
                "test",
                "coverage",
                "pytest",
                "jest",
                "unit",
                "integration",
            ]
            is_test_related = any(
                keyword in prompt.lower() for keyword in test_keywords
            )

            if is_test_related or any(
                "❌" in part or "🔴" in part for part in injection_parts
            ):
                # Include full details if test-related or there are failures
                return f"<test-status>\n{'\n'.join(injection_parts)}\n</test-status>\n"
            else:
                # Minimal summary otherwise
                return "<test-status>Tests passing, coverage healthy</test-status>\n"

        return ""

    except Exception as e:
        # Don't let test analysis errors break the hook
        return f"<!-- Test status error: {str(e)} -->\n"
