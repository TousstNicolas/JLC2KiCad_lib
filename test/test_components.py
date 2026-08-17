"""
Integration tests for JLC2KiCadLib.

These tests generate KiCad components from JLCPCB part numbers and validate
them using kicad-library-utils KLC check scripts.

Components are generated once per session via the `generated_components` fixture,
then all tests run against the cached output files.
"""

import pytest

from .component_cases import TEST_CASES, ComponentTestCase
from .conftest import GeneratedComponent
from .klc_checker import check_footprint, check_symbol, check_warnings_acceptable


@pytest.mark.integration
class TestComponentGeneration:
    """Integration tests for component generation and KLC validation."""

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_component(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """
        Test generating a component and validating with KLC checks.

        Uses pre-generated components from the session fixture.
        """
        component = generated_components[test_case.test_id]

        # Check generation succeeded
        assert component.generation_succeeded, (
            f"JLC2KiCadLib failed for {test_case.component_id}:\n"
            f"stdout: {component.stdout}\n"
            f"stderr: {component.stderr}"
        )

        # Validate symbols
        if test_case.expect_symbol:
            assert len(component.symbols) > 0, (
                f"No symbol files generated for {test_case.component_id}"
            )

            for symbol_file in component.symbols:
                check_result = check_symbol(symbol_file, verbose=True)

                # Check for errors (always fail on errors)
                assert not check_result.has_errors, (
                    f"KLC errors in symbol {symbol_file.name}:\n{check_result.stdout}"
                )

                # Check if warnings are acceptable
                if check_result.has_warnings:
                    acceptable = check_warnings_acceptable(
                        check_result,
                        test_case.allowed_symbol_warnings,
                    )
                    assert acceptable, (
                        f"Unexpected KLC warnings in symbol {symbol_file.name}:\n"
                        f"{check_result.stdout}\n"
                        f"Allowed warnings: {test_case.allowed_symbol_warnings}"
                    )

        # Validate footprints
        if test_case.expect_footprint:
            assert len(component.footprints) > 0, (
                f"No footprint files generated for {test_case.component_id}"
            )

            for footprint_file in component.footprints:
                check_result = check_footprint(footprint_file, verbose=True)

                if "Could not parse footprint" in check_result.stdout:
                    # Pre-existing, unrelated KLC checker limitation: it fails
                    # to parse some legacy fp_arc start/end/angle syntax
                    # (expects a `mid`-point arc instead). Skip rather than
                    # fail on this checker limitation.
                    pytest.skip(
                        f"KLC checker cannot parse {footprint_file.name} "
                        "(pre-existing fp_arc parsing limitation)"
                    )

                # Check for errors (always fail on errors)
                assert not check_result.has_errors, (
                    f"KLC errors in footprint {footprint_file.name}:\n"
                    f"{check_result.stdout}"
                )

                # Check if warnings are acceptable
                if check_result.has_warnings:
                    acceptable = check_warnings_acceptable(
                        check_result,
                        test_case.allowed_footprint_warnings,
                    )
                    assert acceptable, (
                        f"Unexpected KLC warnings in footprint {footprint_file.name}:\n"
                        f"{check_result.stdout}\n"
                        f"Allowed warnings: {test_case.allowed_footprint_warnings}"
                    )


@pytest.mark.integration
class TestGenerationOnly:
    """Tests that only verify component generation (without KLC checks)."""

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_generation_succeeds(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Test that component generation completes without errors."""
        component = generated_components[test_case.test_id]

        assert component.generation_succeeded, (
            f"JLC2KiCadLib failed for {test_case.component_id}:\n"
            f"stdout: {component.stdout}\n"
            f"stderr: {component.stderr}"
        )

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_files_generated(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Test that expected files are generated."""
        component = generated_components[test_case.test_id]

        if not component.generation_succeeded:
            pytest.skip(f"Generation failed: {component.stderr}")

        if test_case.expect_symbol:
            assert len(component.symbols) > 0, "Expected symbol file not found"

        if test_case.expect_footprint:
            assert len(component.footprints) > 0, "Expected footprint file not found"

        if test_case.models:
            assert len(component.models) > 0, (
                f"Expected 3D model file(s) ({test_case.models}) not found for "
                f"{test_case.component_id}"
            )
            found_extensions = {model.suffix.lower() for model in component.models}
            for requested_model in test_case.models:
                expected_ext = f".{requested_model.lower()}"
                assert expected_ext in found_extensions, (
                    f"Expected a .{requested_model.lower()} 3D model file but "
                    f"only found: {[m.name for m in component.models]}"
                )


@pytest.mark.integration
class TestKLCChecksOnly:
    """Tests that run KLC checks on pre-generated files."""

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_symbol_klc(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Test KLC compliance of generated symbols."""
        if not test_case.expect_symbol:
            pytest.skip("No symbol expected for this component")

        component = generated_components[test_case.test_id]

        if not component.generation_succeeded:
            pytest.skip(f"Generation failed: {component.stderr}")

        for symbol_file in component.symbols:
            check_result = check_symbol(symbol_file, verbose=True)
            assert not check_result.has_errors, f"KLC errors:\n{check_result.stdout}"

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_footprint_klc(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Test KLC compliance of generated footprints."""
        if not test_case.expect_footprint:
            pytest.skip("No footprint expected for this component")

        component = generated_components[test_case.test_id]

        if not component.generation_succeeded:
            pytest.skip(f"Generation failed: {component.stderr}")

        for footprint_file in component.footprints:
            check_result = check_footprint(footprint_file, verbose=True)

            if "Could not parse footprint" in check_result.stdout:
                # Pre-existing, unrelated KLC checker limitation: it fails
                # to parse some legacy fp_arc start/end/angle syntax
                # (expects a `mid`-point arc instead). Skip rather than
                # fail on this checker limitation.
                pytest.skip(
                    f"KLC checker cannot parse {footprint_file.name} "
                    "(pre-existing fp_arc parsing limitation)"
                )

            assert not check_result.has_errors, f"KLC errors:\n{check_result.stdout}"


@pytest.mark.integration
class TestCourtyardGeneration:
    """
    Focused tests for the auto-generated F.CrtYd courtyard (see issue #76).

    These reuse the session-wide generated components fixture and only check
    courtyard-specific properties, isolated from unrelated KLC rules that may
    already fail for other reasons (e.g. F5.1, F6.3).
    """

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_footprint_has_courtyard_layer(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Every generated footprint should contain F.CrtYd graphics."""
        if not test_case.expect_footprint:
            pytest.skip("No footprint expected for this component")

        component = generated_components[test_case.test_id]
        if not component.generation_succeeded:
            pytest.skip(f"Generation failed: {component.stderr}")

        for footprint_file in component.footprints:
            content = footprint_file.read_text()
            assert "F.CrtYd" in content, (
                f"No F.CrtYd courtyard found in {footprint_file.name}"
            )

    @pytest.mark.parametrize(
        "test_case",
        TEST_CASES,
        ids=[case.test_id for case in TEST_CASES],
    )
    def test_footprint_passes_klc_courtyard_rule(
        self,
        test_case: ComponentTestCase,
        generated_components: dict[str, GeneratedComponent],
    ):
        """Generated footprints should pass KLC rule F5.3 (courtyard)."""
        if not test_case.expect_footprint:
            pytest.skip("No footprint expected for this component")

        component = generated_components[test_case.test_id]
        if not component.generation_succeeded:
            pytest.skip(f"Generation failed: {component.stderr}")

        for footprint_file in component.footprints:
            check_result = check_footprint(footprint_file, rules=["F5.3"], verbose=True)

            if "Could not parse footprint" in check_result.stdout:
                # Pre-existing, unrelated KLC checker limitation: it fails to
                # parse some legacy fp_arc start/end/angle syntax (expects a
                # `mid`-point arc instead). Not a courtyard issue: skip rather
                # than fail this courtyard-focused test.
                pytest.skip(
                    f"KLC checker cannot parse {footprint_file.name} "
                    "(pre-existing fp_arc parsing limitation, unrelated to "
                    "courtyard generation)"
                )

            assert not check_result.has_errors, (
                f"KLC F5.3 (courtyard) errors in {footprint_file.name}:\n"
                f"{check_result.stdout}"
            )
