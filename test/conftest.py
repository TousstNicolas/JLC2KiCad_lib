"""
Pytest configuration and fixtures for JLC2KiCadLib integration tests.
"""

import io
import logging
import shutil
import tempfile
from argparse import Namespace
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from .component_cases import TEST_CASES

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class GeneratedComponent:
    """Holds the generated files and status for a component."""

    component_id: str
    output_dir: Path
    symbols: list[Path] = field(default_factory=list)
    footprints: list[Path] = field(default_factory=list)
    generation_succeeded: bool = False
    stdout: str = ""
    stderr: str = ""


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return the project root directory."""
    return PROJECT_ROOT


@pytest.fixture
def temp_output_dir():
    """
    Create a temporary directory for test outputs.

    This directory is cleaned up after each test.
    """
    temp_dir = tempfile.mkdtemp(prefix="jlc2kicad_test_")
    yield Path(temp_dir)
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def session_output_dir():
    """
    Create a temporary directory for session-wide test outputs.

    This directory persists for the entire test session and is cleaned up at the end.
    """
    temp_dir = tempfile.mkdtemp(prefix="jlc2kicad_session_")
    yield Path(temp_dir)
    # Cleanup at end of session
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def generated_components(
    session_output_dir: Path,
) -> dict[str, GeneratedComponent]:
    """
    Generate all test components once per session.

    This fixture calls JLC2KiCadLib directly (in-process) for each test case
    and caches the results. This allows coverage to track the code execution.

    Returns:
        Dict mapping test_id to GeneratedComponent (which may contain multiple components)
    """
    from JLC2KiCadLib.JLC2KiCadLib import add_component

    components: dict[str, GeneratedComponent] = {}

    for test_case in TEST_CASES:
        # Create a subdirectory for each test case
        test_id = test_case.test_id
        component_dir = session_output_dir / test_id
        component_dir.mkdir(exist_ok=True)

        # Build args namespace matching CLI arguments
        # Use test_case flags to control what gets generated

        # Parse custom arguments from test_case.args
        skip_existing = False
        if "--skip-existing" in test_case.args:
            skip_existing = True

        args = Namespace(
            output_dir=str(component_dir),
            footprint_creation=test_case.expect_footprint,
            symbol_creation=test_case.expect_symbol,
            symbol_lib=None,
            symbol_lib_dir="symbol",
            footprint_lib="footprint",
            models=test_case.models,  # Empty list = no 3D models (default)
            model_dir="packages3d",
            skip_existing=skip_existing,
            model_base_variable="",
        )

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Set up logging to capture output
        handler = logging.StreamHandler(stdout_capture)
        handler.setLevel(logging.DEBUG)
        root_logger = logging.getLogger()
        old_handlers = root_logger.handlers[:]
        root_logger.handlers = [handler]
        old_level = root_logger.level
        root_logger.setLevel(logging.DEBUG)

        generation_succeeded = True
        try:
            # Generate all components in this test case
            for comp_id in test_case.component_ids:
                add_component(comp_id, args)
        except Exception as e:
            stderr_capture.write(str(e))
            generation_succeeded = False
        finally:
            # Restore logging
            root_logger.handlers = old_handlers
            root_logger.setLevel(old_level)

        # Find generated files
        symbols = list(component_dir.rglob("*.kicad_sym"))
        footprints = list(component_dir.rglob("*.kicad_mod"))

        # Store by test_id (handles both single and multiple component cases)
        components[test_id] = GeneratedComponent(
            component_id=test_id,
            output_dir=component_dir,
            symbols=symbols,
            footprints=footprints,
            generation_succeeded=generation_succeeded,
            stdout=stdout_capture.getvalue(),
            stderr=stderr_capture.getvalue(),
        )

    return components


def find_generated_files(output_dir: Path) -> dict:
    """
    Find all generated KiCad files in the output directory.

    Args:
        output_dir: Directory to search

    Returns:
        Dict with keys 'symbols' and 'footprints' containing lists of paths
    """
    symbols = list(output_dir.rglob("*.kicad_sym"))
    footprints = list(output_dir.rglob("*.kicad_mod"))

    return {
        "symbols": symbols,
        "footprints": footprints,
    }
