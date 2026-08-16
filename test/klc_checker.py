"""
Wrapper module for kicad-library-utils KLC check scripts.

This module provides Python functions to run check_symbol.py and check_footprint.py
from kicad-library-utils and parse their results.
"""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Return codes from KLC check scripts
RETURN_PASS = 0
RETURN_WARNINGS = 2
RETURN_ERRORS = 3

# Path to kicad-library-utils klc-check directory
KLC_CHECK_DIR = Path(__file__).parent.parent / "kicad-library-utils" / "klc-check"
CHECK_SYMBOL_SCRIPT = KLC_CHECK_DIR / "check_symbol.py"
CHECK_FOOTPRINT_SCRIPT = KLC_CHECK_DIR / "check_footprint.py"

# Global rule exclusions (names come from JLCPCB, not following KLC conventions)
EXCLUDED_SYMBOL_RULES = ["S4.4"]
EXCLUDED_FOOTPRINT_RULES = ["F9.3"]


@dataclass
class CheckResult:
    """Result of a KLC check."""

    passed: bool
    has_warnings: bool
    has_errors: bool
    return_code: int
    stdout: str
    stderr: str
    rule_violations: list[str]

    @property
    def summary(self) -> str:
        """Return a summary string of the result."""
        if self.passed and not self.has_warnings:
            return "PASS"
        elif self.has_warnings and not self.has_errors:
            return "WARNINGS"
        else:
            return "ERRORS"


def _run_check_script(
    script_path: Path,
    target_file: Path,
    exclude_rules: Optional[list[str]] = None,
    rules: Optional[list[str]] = None,
    verbose: bool = False,
) -> CheckResult:
    """
    Run a KLC check script and parse the results.

    Args:
        script_path: Path to the check script (check_symbol.py or check_footprint.py)
        target_file: Path to the file to check (.kicad_sym or .kicad_mod)
        exclude_rules: List of rules to exclude (e.g., ["S4.4", "S6.2"])
        rules: List of specific rules to run (if None, run all)
        verbose: Enable verbose output

    Returns:
        CheckResult with parsed results
    """
    if not script_path.exists():
        raise FileNotFoundError(f"KLC check script not found: {script_path}")

    if not target_file.exists():
        raise FileNotFoundError(f"Target file not found: {target_file}")

    cmd = [sys.executable, str(script_path)]

    if verbose:
        cmd.append("-v")

    if exclude_rules:
        cmd.extend(["--exclude", ",".join(exclude_rules)])

    if rules:
        cmd.extend(["-r", ",".join(rules)])

    cmd.append(str(target_file))

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=KLC_CHECK_DIR)

    # Parse violations from output
    rule_violations = []
    for line in result.stdout.split("\n"):
        # Look for rule violation patterns like "Violating S3.1" or "Rule S3.1"
        if "Violating" in line or "Rule" in line:
            rule_violations.append(line.strip())

    return CheckResult(
        passed=result.returncode == RETURN_PASS,
        has_warnings=result.returncode == RETURN_WARNINGS,
        has_errors=result.returncode == RETURN_ERRORS,
        return_code=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        rule_violations=rule_violations,
    )


def check_symbol(
    symbol_file: Path,
    exclude_rules: Optional[list[str]] = None,
    rules: Optional[list[str]] = None,
    verbose: bool = False,
) -> CheckResult:
    """
    Run KLC checks on a symbol file (.kicad_sym).

    Args:
        symbol_file: Path to the .kicad_sym file
        exclude_rules: Additional rules to exclude (beyond global exclusions)
        rules: Specific rules to run (if None, run all except excluded)
        verbose: Enable verbose output

    Returns:
        CheckResult with parsed results
    """
    all_excluded = list(EXCLUDED_SYMBOL_RULES)
    if exclude_rules:
        all_excluded.extend(exclude_rules)

    return _run_check_script(
        CHECK_SYMBOL_SCRIPT,
        symbol_file,
        exclude_rules=all_excluded,
        rules=rules,
        verbose=verbose,
    )


def check_footprint(
    footprint_file: Path,
    exclude_rules: Optional[list[str]] = None,
    rules: Optional[list[str]] = None,
    verbose: bool = False,
) -> CheckResult:
    """
    Run KLC checks on a footprint file (.kicad_mod).

    Args:
        footprint_file: Path to the .kicad_mod file
        exclude_rules: Additional rules to exclude (beyond global exclusions)
        rules: Specific rules to run (if None, run all except excluded)
        verbose: Enable verbose output

    Returns:
        CheckResult with parsed results
    """
    all_excluded = list(EXCLUDED_FOOTPRINT_RULES)
    if exclude_rules:
        all_excluded.extend(exclude_rules)

    return _run_check_script(
        CHECK_FOOTPRINT_SCRIPT,
        footprint_file,
        exclude_rules=all_excluded,
        rules=rules,
        verbose=verbose,
    )


def check_warnings_acceptable(
    result: CheckResult,
    allowed_warnings: Optional[list[str]] = None,
) -> bool:
    """
    Check if all warnings in the result are in the allowed list.

    Args:
        result: CheckResult from a KLC check
        allowed_warnings: List of rule names that are allowed to warn (e.g., ["S4.2"])

    Returns:
        True if all warnings are acceptable, False otherwise
    """
    if result.passed and not result.has_warnings:
        return True

    if result.has_errors:
        return False

    if not allowed_warnings:
        # No warnings allowed, but we have warnings
        return result.passed

    # Check if all violations are in the allowed list
    for violation in result.rule_violations:
        # Extract rule name from violation string
        is_allowed = any(rule in violation for rule in allowed_warnings)
        if not is_allowed:
            return False

    return True
