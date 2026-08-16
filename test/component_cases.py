"""
Test case definitions for JLC2KiCadLib integration tests.

Each test case defines one or more JLCPCB component IDs and expected behavior.
"""

from dataclasses import dataclass, field


@dataclass
class ComponentTestCase:
    """A test case for one or more JLCPCB components."""

    component_id: str | list[str]  # Single ID or list of IDs
    description: str
    args: list[str] = field(default_factory=list)
    expect_footprint: bool = True
    expect_symbol: bool = True
    models: list[str] = field(
        default_factory=list
    )  # Empty = no 3D models, ["STEP"], ["WRL"], or ["STEP", "WRL"]
    allowed_symbol_warnings: list[str] = field(default_factory=list)
    allowed_footprint_warnings: list[str] = field(default_factory=list)

    @property
    def component_ids(self) -> list[str]:
        """Return component IDs as a list."""
        if isinstance(self.component_id, list):
            return self.component_id
        return [self.component_id]

    @property
    def test_id(self) -> str:
        """Return a test ID for pytest parametrization."""
        if isinstance(self.component_id, list):
            ids = "_".join(self.component_id[:3])  # Use first 3 IDs
            if len(self.component_id) > 3:
                ids += f"_plus{len(self.component_id) - 3}"
            return f"{ids}-{self.description.replace(' ', '_')}"
        return f"{self.component_id}-{self.description.replace(' ', '_')}"


# Default test cases covering various component types
TEST_CASES = [
    ComponentTestCase(
        component_id="C1019365",
        description="symbol h_AR handler",
        expect_footprint=False,
    ),
    ComponentTestCase(
        component_id=[
            "C585245",
            "C1341481",
            "C559118",
            "C2687297",
        ],
        description="footprint h_SOLIDREGION handler",
        expect_symbol=False,
    ),
    ComponentTestCase(
        component_id=[
            "C224994",
            "C338099",
            "C545582",
            "C1351206",
            "C900833",
            "C1552893",
            "C554202",
            "C118195",
            "C438406",
            "C2679247",
            "C508083",
            "C536284",
            "C166652",
            "C1390287",
            "C222151",
            "C385565",
            "C879210",
            "C1581941",
            "C88766",
        ],
        description="footprint coverage booster",
        expect_symbol=False,
    ),
    ComponentTestCase(
        component_id=[
            "C224994",
            "C336466",
            "C454958",
            "C1552893",
            "C487357",
            "C281172",
            "C35449",
            "C157716",
            "C166652",
            "C1334110",
            "C28064",
        ],
        description="symbol coverage booster",
        expect_footprint=False,
    ),
    ComponentTestCase(
        component_id=["C224994"],
        description="3D model coverage booster",
        expect_symbol=False,
        models=["STEP", "WRL"],
    ),
    ComponentTestCase(
        component_id=["C224994", "C224994"],
        description="Symbol library replacement",
        expect_footprint=False,
    ),
    ComponentTestCase(
        component_id=["C224994", "C224994"],
        description="Skip existing arguments",
        args=["--skip-existing"],
    ),
]


def get_test_ids() -> list[str]:
    """Return list of test IDs for pytest parametrization."""
    return [case.test_id for case in TEST_CASES]


def get_test_cases() -> list[ComponentTestCase]:
    """Return the list of test cases."""
    return TEST_CASES
