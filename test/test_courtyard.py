"""
Unit tests for automatic F.CrtYd (courtyard) generation.

These tests do not perform any network calls: they exercise the courtyard
bounding-box helpers, the individual footprint shape handlers, and the final
courtyard rectangle generation in `create_footprint` directly, using
synthetic EasyEDA-style shape data.

See https://github.com/TousstNicolas/JLC2KiCad_lib/issues/76 for background:
EasyEDA does not provide courtyard data, so a courtyard is approximated by
inflating the bounding box of the copper/fab/paste/mask/edge-cuts shapes by a
flat 0.25mm clearance, snapped to a 0.01mm grid (mirroring KiCad's own
EasyEDA importer behavior).
"""

from unittest.mock import patch

import pytest
from KicadModTree import Footprint, RectLine

from JLC2KiCadLib.footprint.footprint import (
    CRTYD_CLEARANCE,
    CRTYD_GRID,
    CRTYD_WIDTH,
    FootprintInfo,
    _snap_to_grid,
    create_footprint,
)
from JLC2KiCadLib.footprint.footprint_handlers import (
    CRTYD_RELEVANT_LAYERS,
    h_ARC,
    h_CIRCLE,
    h_HOLE,
    h_PAD,
    h_RECT,
    h_SVGNODE,
    h_TRACK,
    svg_arc_to_points,
    update_crtyd_bounds,
)


def mm2mil(value: float) -> str:
    """Convert a mm value to a mil string, as found in raw EasyEDA data."""
    return str(value * 3.937)


def new_footprint_info() -> FootprintInfo:
    return FootprintInfo(footprint_name="test_footprint")


class TestSnapToGrid:
    """Tests for the `_snap_to_grid` helper."""

    def test_already_on_grid(self):
        assert _snap_to_grid(1.23) == pytest.approx(1.23)

    def test_rounds_to_nearest_grid_point(self):
        assert _snap_to_grid(1.234) == pytest.approx(1.23)
        assert _snap_to_grid(1.236) == pytest.approx(1.24)

    def test_negative_values(self):
        assert _snap_to_grid(-1.234) == pytest.approx(-1.23)

    def test_custom_grid(self):
        assert _snap_to_grid(1.27, grid=0.1) == pytest.approx(1.3)


class TestUpdateCrtydBounds:
    """Tests for the `update_crtyd_bounds` helper and layer relevance set."""

    @pytest.mark.parametrize(
        "layer",
        [
            "F.Cu",
            "B.Cu",
            "F.Paste",
            "B.Paste",
            "F.Mask",
            "B.Mask",
            "F.Fab",
            "Edge.Cuts",
        ],
    )
    def test_relevant_layer_updates_bounds(self, layer):
        info = new_footprint_info()
        update_crtyd_bounds(info, layer, -1, 2, -3, 4)

        assert info.crtyd_min_X == -1
        assert info.crtyd_max_X == 2
        assert info.crtyd_min_Y == -3
        assert info.crtyd_max_Y == 4
        assert info.has_crtyd_bounds()

    @pytest.mark.parametrize("layer", ["F.SilkS", "B.Silks", "Cmts.User", "Dwgs.User"])
    def test_irrelevant_layer_is_noop(self, layer):
        info = new_footprint_info()
        update_crtyd_bounds(info, layer, -1, 2, -3, 4)

        assert not info.has_crtyd_bounds()

    def test_bounds_expand_across_multiple_calls(self):
        info = new_footprint_info()
        update_crtyd_bounds(info, "F.Cu", 0, 1, 0, 1)
        update_crtyd_bounds(info, "F.Fab", -5, 0.5, -5, 0.5)

        assert info.crtyd_min_X == -5
        assert info.crtyd_max_X == 1
        assert info.crtyd_min_Y == -5
        assert info.crtyd_max_Y == 1

    def test_relevant_layers_set_matches_expectations(self):
        assert {
            "F.Cu",
            "B.Cu",
            "F.Paste",
            "B.Paste",
            "F.Mask",
            "B.Mask",
            "F.Fab",
            "Edge.Cuts",
        } == CRTYD_RELEVANT_LAYERS


class TestFootprintInfoHasCrtydBounds:
    """Tests for `FootprintInfo.has_crtyd_bounds`."""

    def test_default_state_has_no_bounds(self):
        info = new_footprint_info()
        assert not info.has_crtyd_bounds()

    def test_after_update_has_bounds(self):
        info = new_footprint_info()
        update_crtyd_bounds(info, "F.Cu", -1, 1, -1, 1)
        assert info.has_crtyd_bounds()


class TestHandlersUpdateCrtydBounds:
    """
    Tests that individual footprint shape handlers correctly feed the
    courtyard bounding box (or correctly skip it) depending on layer.
    """

    def test_h_track_on_copper_layer_updates_crtyd_bounds(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # data: [width, layer, ?, points, id]. Layer "1" -> F.Cu
        data = ["1", "1", "", f"{mm2mil(0)} {mm2mil(0)} {mm2mil(2)} {mm2mil(1)}", "id"]

        h_TRACK(data, kicad_mod, info)

        assert info.has_crtyd_bounds()
        assert info.crtyd_min_X == pytest.approx(0)
        assert info.crtyd_max_X == pytest.approx(2)
        assert info.crtyd_min_Y == pytest.approx(0)
        assert info.crtyd_max_Y == pytest.approx(1)

    def test_h_track_on_silkscreen_layer_is_ignored(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # layer "3" -> F.SilkS, not relevant to courtyard
        data = ["1", "3", "", f"{mm2mil(0)} {mm2mil(0)} {mm2mil(2)} {mm2mil(1)}", "id"]

        h_TRACK(data, kicad_mod, info)

        assert not info.has_crtyd_bounds()

    def test_h_track_unknown_layer_falls_back_to_silkscreen(self, caplog):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        data = [
            "1",
            "15",
            "",
            f"{mm2mil(0)} {mm2mil(0)} {mm2mil(1)} {mm2mil(1)}",
            "id",
        ]

        with caplog.at_level("ERROR"):
            h_TRACK(data, kicad_mod, info)

        assert "layer correspondance not found" in caplog.text
        assert not info.has_crtyd_bounds()

    def test_h_pad_smd_updates_crtyd_bounds_with_half_diagonal(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # Standard SMD RECT pad, layer "1" (top copper), size 2x1mm at (0, 0)
        data = [
            "RECT",
            mm2mil(0),
            mm2mil(0),
            mm2mil(2),
            mm2mil(1),
            "1",
            "",
            "1",
            mm2mil(0),
            "",
            "0",
            "id",
            "",
            "",
            "Y",
        ]

        h_PAD(data, kicad_mod, info)

        half_diag = ((2 / 2) ** 2 + (1 / 2) ** 2) ** 0.5
        assert info.has_crtyd_bounds()
        assert info.crtyd_min_X == pytest.approx(-half_diag)
        assert info.crtyd_max_X == pytest.approx(half_diag)

    def test_h_pad_polygon_uses_exact_relative_points(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # POLYGON pad centered at (1, 1)mm with relative points forming a
        # 2x2mm square: absolute points (0,0), (2,0), (2,2), (0,2)
        polygon_points = " ".join(mm2mil(v) for v in [0, 0, 2, 0, 2, 2, 0, 2])
        data = [
            "POLYGON",
            mm2mil(1),
            mm2mil(1),
            mm2mil(0),
            mm2mil(0),
            "1",
            "",
            "1",
            mm2mil(0),
            polygon_points,
            "0",
            "id",
            "",
            "",
            "Y",
        ]

        h_PAD(data, kicad_mod, info)

        assert info.crtyd_min_X == pytest.approx(0)
        assert info.crtyd_max_X == pytest.approx(2)
        assert info.crtyd_min_Y == pytest.approx(0)
        assert info.crtyd_max_Y == pytest.approx(2)

    @pytest.mark.parametrize(
        ("shape_type", "size_x", "size_y", "drill", "offset"),
        [
            ("OVAL", 2, 1, 0.2, 0.1),
            ("OVAL", 1, 2, 0.2, 0.3),
            ("UNKNOWN", 2, 1, 0.2, 0.1),
        ],
    )
    def test_h_pad_handles_offset_and_unknown_shapes(
        self, shape_type, size_x, size_y, drill, offset, caplog
    ):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        data = [
            shape_type,
            mm2mil(0),
            mm2mil(0),
            mm2mil(size_x),
            mm2mil(size_y),
            "1",
            "",
            "1",
            mm2mil(drill),
            "",
            "0",
            "id",
            mm2mil(offset),
            "",
            "Y",
        ]

        with caplog.at_level("ERROR"):
            h_PAD(data, kicad_mod, info)

        assert info.has_crtyd_bounds()
        if shape_type == "UNKNOWN":
            assert "no correspondance found" in caplog.text

    def test_h_hole_is_always_relevant(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        data = [mm2mil(0), mm2mil(0), mm2mil(0.5)]

        h_HOLE(data, kicad_mod, info)

        assert info.has_crtyd_bounds()
        assert info.crtyd_min_X == pytest.approx(-0.5)
        assert info.crtyd_max_X == pytest.approx(0.5)

    def test_h_rect_on_relevant_layer_updates_bounds(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # data: [Xstart, Ystart, Xdelta, Ydelta, layer, ?, ?, width]
        # layer "12" -> F.Fab
        data = [
            mm2mil(0),
            mm2mil(0),
            mm2mil(3),
            mm2mil(2),
            "12",
            "",
            "",
            mm2mil(0.1),
        ]

        h_RECT(data, kicad_mod, info)

        assert info.crtyd_min_X == pytest.approx(0)
        assert info.crtyd_max_X == pytest.approx(3)
        assert info.crtyd_min_Y == pytest.approx(0)
        assert info.crtyd_max_Y == pytest.approx(2)

    def test_h_rect_on_silkscreen_layer_is_ignored(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # layer "3" -> F.SilkS
        data = [
            mm2mil(0),
            mm2mil(0),
            mm2mil(3),
            mm2mil(2),
            "3",
            "",
            "",
            mm2mil(0.1),
        ]

        h_RECT(data, kicad_mod, info)

        assert not info.has_crtyd_bounds()

    def test_h_circle_updates_bounds(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        # data: [x, y, radius, width, layer]; layer "1" -> F.Cu
        data = [mm2mil(1), mm2mil(1), mm2mil(0.5), mm2mil(0.1), "1"]

        h_CIRCLE(data, kicad_mod, info)

        assert info.crtyd_min_X == pytest.approx(0.5)
        assert info.crtyd_max_X == pytest.approx(1.5)
        assert info.crtyd_min_Y == pytest.approx(0.5)
        assert info.crtyd_max_Y == pytest.approx(1.5)

    def test_h_arc_full_circle_updates_bounds(self):
        info = new_footprint_info()
        kicad_mod = Footprint("test")
        radius_mil = 100.0
        # Full-circle arc: start == end, on F.Fab ("12")
        svg_path = f"M 0 0 A {radius_mil} {radius_mil} 0 1 1 0 0"
        data = ["1", "12", "", svg_path, "", "id"]

        h_ARC(data, kicad_mod, info)

        radius_mm = radius_mil / 3.937
        assert info.has_crtyd_bounds()
        assert info.crtyd_max_X - info.crtyd_min_X == pytest.approx(2 * radius_mm)
        assert info.crtyd_max_Y - info.crtyd_min_Y == pytest.approx(2 * radius_mm)

    def test_h_arc_rejects_malformed_svg(self, caplog):
        info = new_footprint_info()
        with caplog.at_level("ERROR"):
            h_ARC(["1", "12", "", "not-an-arc", "", "id"], Footprint("test"), info)
        assert "failed to parse ARC" in caplog.text

    def test_h_arc_full_circle_counterclockwise(self):
        info = new_footprint_info()
        data = ["1", "12", "", "M 0 0 A 100 100 0 1 0 0 0", "", "id"]

        h_ARC(data, Footprint("test"), info)

        assert info.has_crtyd_bounds()

    def test_unknown_circle_layer_falls_back(self, caplog):
        info = new_footprint_info()
        with caplog.at_level("ERROR"):
            h_CIRCLE(
                [mm2mil(0), mm2mil(0), mm2mil(1), mm2mil(0.1), "15"],
                Footprint("test"),
                info,
            )
        assert "layer correspondance not found" in caplog.text

    @pytest.mark.parametrize(
        "args",
        [(0, 0, 1, 1, 0, 0, 1, 0, 0), (0, 0, 0, 1, 0, 0, 1, 1, 1)],
    )
    def test_svg_arc_degenerate_cases(self, args):
        points = svg_arc_to_points(*args)
        assert points == [] or points == [(1, 1)]

    def test_svg_node_invalid_json_is_ignored(self, caplog):
        info = new_footprint_info()
        with caplog.at_level("ERROR"):
            result = h_SVGNODE(["not-json"], Footprint("test"), info)
        assert result == ()
        assert "failed to parse json data" in caplog.text

    def test_filled_rect_is_emitted(self):
        info = new_footprint_info()
        footprint = Footprint("test")
        data = [
            mm2mil(0),
            mm2mil(0),
            mm2mil(2),
            mm2mil(1),
            "12",
            "",
            "",
            mm2mil(0),
        ]

        h_RECT(data, footprint, info)

        assert info.has_crtyd_bounds()
        assert any(
            item.__class__.__name__ == "RectFill"
            for item in footprint.getNormalChilds()
        )


class TestCreateFootprintCourtyardGeneration:
    """
    End-to-end (but network-free) tests of the courtyard rectangle emitted
    by `create_footprint`, by mocking `get_footprint_info`.
    """

    def _run_create_footprint(self, footprint_shape, tmp_path):
        with patch(
            "JLC2KiCadLib.footprint.footprint.get_footprint_info"
        ) as mock_get_info:
            mock_get_info.return_value = (
                "test_footprint",
                "http://example.com/datasheet",
                footprint_shape,
                [0, 0],
            )
            create_footprint(
                footprint_component_uuid="fake-uuid",
                component_id="C1234",
                footprint_lib="footprint",
                output_dir=str(tmp_path),
                model_base_variable="",
                model_dir="packages3d",
                skip_existing=False,
                models=[],
            )

        mod_path = tmp_path / "footprint" / "test_footprint.kicad_mod"
        assert mod_path.is_file()
        return mod_path.read_text()

    def test_courtyard_rectangle_is_generated_for_smd_pad(self, tmp_path):
        # A single SMD RECT pad, 2x1mm at origin, on top copper ("1")
        pad_shape = "~".join(
            [
                "PAD",
                "RECT",
                mm2mil(0),
                mm2mil(0),
                mm2mil(2),
                mm2mil(1),
                "1",
                "",
                "1",
                mm2mil(0),
                "",
                "0",
                "id1",
                "",
                "",
                "Y",
            ]
        )

        content = self._run_create_footprint([pad_shape], tmp_path)

        assert "F.CrtYd" in content

        half_diag = ((2 / 2) ** 2 + (1 / 2) ** 2) ** 0.5
        expected_min = _snap_to_grid(-half_diag - CRTYD_CLEARANCE)
        expected_max = _snap_to_grid(half_diag + CRTYD_CLEARANCE)

        assert f"{expected_min}" in content or f"{expected_min:.2f}" in content
        assert f"{expected_max}" in content or f"{expected_max:.2f}" in content

    def test_courtyard_uses_expected_width_and_grid_constants(self):
        # Sanity check the constants used match KLC expectations.
        assert CRTYD_CLEARANCE == 0.25
        assert CRTYD_WIDTH == 0.05
        assert CRTYD_GRID == 0.01

    def test_no_courtyard_generated_when_no_relevant_shapes(self, tmp_path, caplog):
        # A single silkscreen track only: not relevant to courtyard bounds.
        track_shape = "~".join(
            [
                "TRACK",
                mm2mil(0.1),
                "3",  # F.SilkS
                "",
                f"{mm2mil(0)} {mm2mil(0)} {mm2mil(1)} {mm2mil(1)}",
                "id1",
            ]
        )

        with caplog.at_level("WARNING"):
            content = self._run_create_footprint([track_shape], tmp_path)

        assert "F.CrtYd" not in content
        assert any(
            "skipping courtyard generation" in record.message
            for record in caplog.records
        )

    def test_courtyard_rectangle_is_a_closed_rectline(self, tmp_path):
        pad_shape = "~".join(
            [
                "PAD",
                "RECT",
                mm2mil(0),
                mm2mil(0),
                mm2mil(2),
                mm2mil(2),
                "1",
                "",
                "1",
                mm2mil(0),
                "",
                "0",
                "id1",
                "",
                "",
                "Y",
            ]
        )

        content = self._run_create_footprint([pad_shape], tmp_path)

        # RectLine on F.CrtYd is emitted as 4 fp_line segments forming a
        # closed rectangle, each with the expected courtyard line width.
        crtyd_lines = [line for line in content.splitlines() if "F.CrtYd" in line]
        assert len(crtyd_lines) == 4
        assert all(f"(width {CRTYD_WIDTH})" in line for line in crtyd_lines)


def test_rectline_import_available():
    """Sanity check that RectLine is importable from KicadModTree (used for F.CrtYd)."""
    assert RectLine is not None
