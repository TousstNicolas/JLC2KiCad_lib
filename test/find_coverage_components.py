"""
Script to find JLCPCB components that increase test coverage.

This script samples components from the JLCPCB CSV file, runs them through
the library, and identifies which components exercise new code paths.

It first runs the existing test suite to establish baseline coverage,
then only reports components that add NEW coverage beyond the baseline.
"""

import argparse
import csv
import json
import logging
import multiprocessing
import os
import random
import subprocess
import sys
import tempfile
from argparse import Namespace
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import requests

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from coverage import Coverage

from JLC2KiCadLib.JLC2KiCadLib import add_component

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Global configuration for component processing
COMPONENT_SKIP_EXISTING = False


def load_coverage_from_file(coverage_file: Path) -> set[tuple[str, int]]:
    """Load coverage data from an existing .coverage file."""
    lines_covered: set[tuple[str, int]] = set()

    if coverage_file.exists():
        cov = Coverage(data_file=str(coverage_file))
        cov.load()

        data = cov.get_data()
        for filename in data.measured_files():
            lines = data.lines(filename)
            if lines:
                for line in lines:
                    lines_covered.add((filename, line))

    return lines_covered


def get_baseline_coverage(coverage_file: Path | None = None) -> set[tuple[str, int]]:
    """
    Get baseline coverage from existing tests.

    Args:
        coverage_file: Optional path to existing .coverage file.
                      If provided, uses that file instead of running tests.

    Returns:
        Set of (filename, line_number) tuples representing covered lines
    """
    # If a coverage file is provided, use it directly
    if coverage_file:
        print("=" * 60)
        print(f"Loading baseline coverage from: {coverage_file}")
        print("=" * 60)

        if not coverage_file.exists():
            print(f"Error: Coverage file not found: {coverage_file}")
            return set()

        lines_covered = load_coverage_from_file(coverage_file)
        print(f"Baseline coverage: {len(lines_covered)} lines covered")
        print("=" * 60 + "\n")
        return lines_covered

    # Otherwise, run the tests
    print("=" * 60)
    print("Running existing tests to establish baseline coverage...")
    print("=" * 60)

    # Run pytest with coverage, using COVERAGE_FILE env var
    with tempfile.TemporaryDirectory(prefix="jlc_baseline_") as temp_dir:
        temp_coverage_file = Path(temp_dir) / ".coverage"

        # Set COVERAGE_FILE environment variable
        env = os.environ.copy()
        env["COVERAGE_FILE"] = str(temp_coverage_file)

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(PROJECT_ROOT / "test"),  # Explicitly specify test directory
                "--no-header",
                "-q",
                "--cov=JLC2KiCadLib",
                "--cov-report=",  # Suppress report output
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
            env=env,
        )

        if result.returncode != 0:
            print(f"Warning: Tests exited with code {result.returncode}")
            if result.stderr:
                print(f"stderr: {result.stderr[-500:]}")
            if result.stdout:
                print(f"stdout: {result.stdout[-500:]}")

        lines_covered = load_coverage_from_file(temp_coverage_file)

    print(f"Baseline coverage: {len(lines_covered)} lines covered")
    print("=" * 60 + "\n")

    return lines_covered


@dataclass
class CoverageStats:
    """Coverage statistics split by module."""

    total: set[tuple[str, int]]
    footprint: set[tuple[str, int]]
    symbol: set[tuple[str, int]]
    other: set[tuple[str, int]]

    @classmethod
    def from_lines(cls, lines: set[tuple[str, int]]) -> "CoverageStats":
        """Create CoverageStats by categorizing lines by file path."""
        footprint = set()
        symbol = set()
        other = set()

        for filename, line in lines:
            if "/footprint/" in filename or "\\footprint\\" in filename:
                footprint.add((filename, line))
            elif "/symbol/" in filename or "\\symbol\\" in filename:
                symbol.add((filename, line))
            else:
                other.add((filename, line))

        return cls(
            total=lines,
            footprint=footprint,
            symbol=symbol,
            other=other,
        )


@dataclass
class ComponentResult:
    """Result of testing a component."""

    component_id: str
    category: str
    description: str
    success: bool
    new_lines_covered: int
    total_lines_covered: int
    # Split by module
    new_footprint_lines: int = 0
    new_symbol_lines: int = 0
    new_other_lines: int = 0
    error: str = ""


def load_components_from_csv(csv_path: Path) -> list[dict]:
    """Load component list from JLCPCB CSV file."""
    components = []
    with open(csv_path, encoding="unicode_escape") as f:
        reader = csv.DictReader(f)
        for row in reader:
            components.append(row)
    return components


def check_component_exists(component_id: str) -> bool:
    """Check if a component exists on EasyEDA."""
    try:
        data = json.loads(
            requests.get(
                f"https://easyeda.com/api/products/{component_id}/svgs",
                timeout=10,
            ).content.decode()
        )
        return data.get("success", False)
    except Exception:
        return False


def run_component_with_coverage(
    component_id: str,
    output_dir: Path,
    existing_coverage: set[tuple[str, int]],
) -> tuple[bool, set[tuple[str, int]], str]:
    """
    Run a component through the library and measure coverage.

    Args:
        component_id: JLCPCB component ID
        output_dir: Output directory for generated files
        existing_coverage: Set of already covered lines (unused but kept for compatibility)

    Returns:
        Tuple of (success, lines_covered, error_message)
    """
    # Create coverage instance
    cov = Coverage(
        source=["JLC2KiCadLib"],
        branch=False,
    )

    args = Namespace(
        output_dir=str(output_dir),
        footprint_creation=True,
        symbol_creation=True,
        symbol_lib=None,
        symbol_lib_dir="symbol",
        footprint_lib="footprint",
        models=[],  # Skip 3D models for speed
        model_dir="packages3d",
        skip_existing=COMPONENT_SKIP_EXISTING,
        model_base_variable="",
    )

    # Suppress logging during test
    logging.disable(logging.CRITICAL)

    success = False
    error = ""
    lines_covered: set[tuple[str, int]] = set()

    try:
        cov.start()
        add_component(component_id, args)
        success = True
    except Exception as e:
        error = str(e)
    finally:
        cov.stop()
        logging.disable(logging.NOTSET)

    # Extract covered lines
    try:
        data = cov.get_data()
        for filename in data.measured_files():
            lines = data.lines(filename)
            if lines:
                for line in lines:
                    lines_covered.add((filename, line))
    except Exception:
        pass

    return success, lines_covered, error


@dataclass
class BaselineStats:
    """Baseline coverage statistics."""

    total: int
    footprint: int
    symbol: int
    other: int


def process_single_component(
    component_data: tuple[int, int, dict, Path],
) -> tuple[ComponentResult, set[tuple[str, int]]] | None:
    """
    Worker function to process a single component in parallel.

    Args:
        component_data: Tuple of (index, total_count, component_dict, temp_dir)

    Returns:
        Tuple of (ComponentResult, lines_covered) or None if component should be skipped
    """
    i, total_count, comp, temp_dir = component_data

    component_id = comp.get("LCSC Part", "")
    category = comp.get("First Category", "")
    description = comp.get("Description", "")[:50]

    print(
        f"[{i + 1}/{total_count}] Testing {component_id}...",
        end=" ",
        flush=True,
    )

    # Check if component exists
    if not check_component_exists(component_id):
        print("SKIP (not found)")
        return None

    # Create component-specific output dir
    comp_dir = temp_dir / component_id
    comp_dir.mkdir(exist_ok=True)

    # Run with coverage
    success, lines_covered, error = run_component_with_coverage(
        component_id,
        comp_dir,
        set(),  # Pass empty set since we'll calculate cumulative later
    )

    # Split coverage by category
    stats = CoverageStats.from_lines(lines_covered)

    if success:
        print(f"OK ({len(lines_covered)} lines)")
    else:
        print(f"FAIL: {error[:50]}")

    return ComponentResult(
        component_id=component_id,
        category=category,
        description=description,
        success=success,
        new_lines_covered=0,  # Will be calculated later
        total_lines_covered=len(lines_covered),
        new_footprint_lines=0,  # Will be calculated later
        new_symbol_lines=0,  # Will be calculated later
        new_other_lines=0,  # Will be calculated later
        error=error,
    ), lines_covered


def find_coverage_components(
    csv_path: Path,
    num_samples: int = 100,
    categories: list[str] | None = None,
    seed: int | None = None,
    skip_baseline: bool = False,
    coverage_file: Path | None = None,
    workers: int | None = None,
) -> tuple[list[ComponentResult], BaselineStats]:
    """
    Sample components and find ones that increase coverage.

    Args:
        csv_path: Path to JLCPCB CSV file
        num_samples: Number of components to sample
        categories: Optional list of categories to filter by
        seed: Random seed for reproducibility
        skip_baseline: If True, skip running existing tests for baseline
        coverage_file: Optional path to existing .coverage file for baseline
        workers: Number of parallel workers (default: CPU count)

    Returns:
        Tuple of (list of ComponentResult sorted by new lines covered, baseline_stats)
    """
    if seed is not None:
        random.seed(seed)

    # Get baseline coverage from existing tests
    if skip_baseline:
        print("Skipping baseline coverage (--skip-baseline flag)")
        baseline_coverage: set[tuple[str, int]] = set()
    else:
        baseline_coverage = get_baseline_coverage(coverage_file)

    # Split baseline into categories
    baseline_stats_raw = CoverageStats.from_lines(baseline_coverage)
    baseline_stats = BaselineStats(
        total=len(baseline_stats_raw.total),
        footprint=len(baseline_stats_raw.footprint),
        symbol=len(baseline_stats_raw.symbol),
        other=len(baseline_stats_raw.other),
    )

    print(f"  Footprint: {baseline_stats.footprint} lines")
    print(f"  Symbol: {baseline_stats.symbol} lines")
    print(f"  Other: {baseline_stats.other} lines")

    # Load components
    all_components = load_components_from_csv(csv_path)
    print(f"\nLoaded {len(all_components)} components from CSV")

    # Filter by category if specified
    if categories:
        all_components = [
            c for c in all_components if c.get("First Category") in categories
        ]
        print(
            f"Filtered to {len(all_components)} components in categories: {categories}"
        )

    # Sample components
    if len(all_components) > num_samples:
        sampled = random.sample(all_components, num_samples)
    else:
        sampled = all_components

    # Determine number of workers
    if workers is None:
        workers = multiprocessing.cpu_count()
    print(f"\nUsing {workers} parallel workers\n")

    # Store results with their coverage data
    results_with_coverage: list[tuple[ComponentResult, set[tuple[str, int]]]] = []

    with tempfile.TemporaryDirectory(prefix="jlc_coverage_") as temp_dir:
        temp_path = Path(temp_dir)

        # Prepare component data for parallel processing
        component_tasks = [
            (i, len(sampled), comp, temp_path) for i, comp in enumerate(sampled)
        ]

        # Process components in parallel
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_task = {
                executor.submit(process_single_component, task): task
                for task in component_tasks
            }

            # Collect results as they complete
            for future in as_completed(future_to_task):
                result = future.result()
                if result is not None:
                    component_result, lines_covered = result
                    results_with_coverage.append((component_result, lines_covered))

    # Now calculate cumulative coverage (post-process to determine new lines)
    # Sort by success first (successful ones first) to prioritize them in cumulative calc
    results_with_coverage.sort(
        key=lambda x: (not x[0].success, -x[0].total_lines_covered)
    )

    # Track cumulative coverage separately for each category
    cumulative_footprint: set[tuple[str, int]] = set(baseline_stats_raw.footprint)
    cumulative_symbol: set[tuple[str, int]] = set(baseline_stats_raw.symbol)
    cumulative_other: set[tuple[str, int]] = set(baseline_stats_raw.other)
    cumulative_total: set[tuple[str, int]] = set(baseline_coverage)

    results: list[ComponentResult] = []

    for component_result, lines_covered in results_with_coverage:
        # Split coverage by category
        stats = CoverageStats.from_lines(lines_covered)

        # Calculate new lines for each category
        new_footprint = stats.footprint - cumulative_footprint
        new_symbol = stats.symbol - cumulative_symbol
        new_other = stats.other - cumulative_other
        new_total = lines_covered - cumulative_total

        # Update the component result with actual new lines
        component_result.new_lines_covered = len(new_total)
        component_result.new_footprint_lines = len(new_footprint)
        component_result.new_symbol_lines = len(new_symbol)
        component_result.new_other_lines = len(new_other)

        if component_result.success:
            cumulative_footprint |= stats.footprint
            cumulative_symbol |= stats.symbol
            cumulative_other |= stats.other
            cumulative_total |= lines_covered

        results.append(component_result)

    # Sort by new lines covered (descending)
    results.sort(key=lambda x: x.new_lines_covered, reverse=True)
    return results, baseline_stats


def main():
    parser = argparse.ArgumentParser(
        description="Find JLCPCB components that increase test coverage"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path(__file__).parent.parent / "JLCPCB SMT Parts Library(20220617).csv",
        help="Path to JLCPCB CSV file",
    )
    parser.add_argument(
        "-n",
        "--num-samples",
        type=int,
        default=50,
        help="Number of components to sample",
    )
    parser.add_argument(
        "--categories",
        nargs="*",
        help="Filter by component categories",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for results (JSON)",
    )
    parser.add_argument(
        "--skip-baseline",
        action="store_true",
        help="Skip running existing tests for baseline coverage (start from 0)",
    )
    parser.add_argument(
        "--coverage-file",
        type=Path,
        help="Use existing .coverage file for baseline instead of running tests",
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Number of parallel workers (default: CPU count)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip generating files that already exist",
    )

    args = parser.parse_args()

    # Set global configuration for component processing
    global COMPONENT_SKIP_EXISTING
    COMPONENT_SKIP_EXISTING = args.skip_existing

    results, baseline = find_coverage_components(
        csv_path=args.csv,
        num_samples=args.num_samples,
        categories=args.categories,
        seed=args.seed,
        skip_baseline=args.skip_baseline,
        coverage_file=args.coverage_file,
        workers=args.workers,
    )

    # Print summary - split by module
    print("\n" + "=" * 70)
    print("FOOTPRINT COVERAGE BOOSTERS")
    print(f"Baseline: {baseline.footprint} lines")
    print("=" * 70)

    footprint_sorted = sorted(
        results, key=lambda x: x.new_footprint_lines, reverse=True
    )
    for r in footprint_sorted[:15]:
        if r.new_footprint_lines > 0:
            print(
                f"{r.component_id:10} +{r.new_footprint_lines:4} lines  {r.category[:30]}"
            )

    print("\n" + "=" * 70)
    print("SYMBOL COVERAGE BOOSTERS")
    print(f"Baseline: {baseline.symbol} lines")
    print("=" * 70)

    symbol_sorted = sorted(results, key=lambda x: x.new_symbol_lines, reverse=True)
    for r in symbol_sorted[:15]:
        if r.new_symbol_lines > 0:
            print(
                f"{r.component_id:10} +{r.new_symbol_lines:4} lines  {r.category[:30]}"
            )

    print("\n" + "=" * 70)
    print("TOTAL COVERAGE (sorted by total new lines)")
    print(
        f"Baseline: {baseline.total} lines (fp:{baseline.footprint}, sym:{baseline.symbol}, other:{baseline.other})"
    )
    print("=" * 70)

    for r in results[:15]:
        if r.new_lines_covered > 0:
            print(
                f"{r.component_id:10} +{r.new_lines_covered:4} total (fp+{r.new_footprint_lines}, sym+{r.new_symbol_lines})  {r.category[:25]}"
            )

    # Save to JSON if requested
    if args.output:
        output_data = {
            "baseline": {
                "total": baseline.total,
                "footprint": baseline.footprint,
                "symbol": baseline.symbol,
                "other": baseline.other,
            },
            "components": [
                {
                    "component_id": r.component_id,
                    "category": r.category,
                    "description": r.description,
                    "success": r.success,
                    "new_lines_covered": r.new_lines_covered,
                    "new_footprint_lines": r.new_footprint_lines,
                    "new_symbol_lines": r.new_symbol_lines,
                    "new_other_lines": r.new_other_lines,
                    "total_lines_covered": r.total_lines_covered,
                    "error": r.error,
                }
                for r in results
            ],
        }
        with open(args.output, "w") as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to {args.output}")

    # Print suggested test cases - split by module
    print("\n" + "=" * 70)
    print("SUGGESTED TEST CASES")
    print("=" * 70)

    # Footprint coverage boosters
    fp_boosters = [
        r.component_id
        for r in footprint_sorted
        if r.success and r.new_footprint_lines > 0
    ]
    if fp_boosters:
        print("\n# Footprint coverage boosters:")
        print(f"""    ComponentTestCase(
        component_id={fp_boosters[:15]},
        description="footprint coverage",
    ),""")

    # Symbol coverage boosters
    sym_boosters = [
        r.component_id for r in symbol_sorted if r.success and r.new_symbol_lines > 0
    ]
    if sym_boosters:
        print("\n# Symbol coverage boosters:")
        print(f"""    ComponentTestCase(
        component_id={sym_boosters[:15]},
        description="symbol coverage",
    ),""")


if __name__ == "__main__":
    main()
