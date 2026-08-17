"""
Unit tests for 3D model generation (`JLC2KiCadLib.footprint.model3d`).

These tests mock all network calls (`requests.get`) so they run offline and
deterministically, exercising the STEP/WRL download+conversion logic and its
error branches directly.
"""

from unittest.mock import MagicMock, patch

from KicadModTree import Footprint, Model

from JLC2KiCadLib.footprint.footprint import FootprintInfo
from JLC2KiCadLib.footprint.model3d import (
    ensure_footprint_lib_directories_exist,
    get_StepModel,
    get_WrlModel,
)

# A minimal but well-formed EasyEDA 3D model response: one material and one
# triangular face, sufficient to exercise material/vertex/shape parsing in
# get_WrlModel.
SAMPLE_WRL_SOURCE = """newmtl mat0
Ka 0.2 0.2 0.2
Kd 0.8 0.8 0.8
Ks 0.1 0.1 0.1
d 1
endmtl
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
usemtl mat0
f 1 2 3
"""

# Two triangular faces sharing an edge (vertices 1 and 2 reused): exercises
# the "vertex index already seen" branch of the WRL face-index deduplication.
SAMPLE_WRL_SOURCE_SHARED_VERTICES = """newmtl mat0
Ka 0.2 0.2 0.2
Kd 0.8 0.8 0.8
Ks 0.1 0.1 0.1
d 1
endmtl
v 0.0 0.0 0.0
v 1.0 0.0 0.0
v 0.0 1.0 0.0
v 1.0 1.0 0.0
usemtl mat0
f 1 2 3
f 2 4 3
"""


def new_footprint_info(tmp_path, model_base_variable="") -> FootprintInfo:
    return FootprintInfo(
        footprint_name="test_footprint",
        output_dir=str(tmp_path),
        footprint_lib="footprint",
        model_dir="packages3d",
        model_base_variable=model_base_variable,
        origin=(0, 0),
    )


class TestEnsureFootprintLibDirectoriesExist:
    def test_creates_missing_directories(self, tmp_path):
        info = new_footprint_info(tmp_path)

        ensure_footprint_lib_directories_exist(info)

        assert (tmp_path / "footprint").is_dir()
        assert (tmp_path / "footprint" / "packages3d").is_dir()

    def test_is_idempotent_when_directories_already_exist(self, tmp_path):
        info = new_footprint_info(tmp_path)

        ensure_footprint_lib_directories_exist(info)
        ensure_footprint_lib_directories_exist(info)  # should not raise

        assert (tmp_path / "footprint" / "packages3d").is_dir()


class TestGetStepModel:
    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_downloads_and_appends_model_on_success(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(status_code=200, content=b"fake-step-data")
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")

        get_StepModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=100,
            translationY=200,
            translationZ=50,
            rotation="0,0,90",
        )

        step_file = tmp_path / "footprint" / "packages3d" / "test_footprint.step"
        assert step_file.is_file()
        assert step_file.read_bytes() == b"fake-step-data"

        models = [
            child for child in footprint.getAllChilds() if isinstance(child, Model)
        ]
        assert len(models) == 1
        assert models[0].filename == "packages3d/test_footprint.step"

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_http_error_skips_model_creation(self, mock_get, tmp_path, caplog):
        mock_get.return_value = MagicMock(status_code=404, content=b"")
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")

        with caplog.at_level("ERROR"):
            get_StepModel(
                component_uuid="uuid-1",
                footprint_info=info,
                kicad_mod=footprint,
                translationX=0,
                translationY=0,
                translationZ=0,
                rotation="0,0,0",
            )

        assert "no Step model found" in caplog.text
        step_file = tmp_path / "footprint" / "packages3d" / "test_footprint.step"
        assert not step_file.exists()
        assert list(footprint.getAllChilds()) == []

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_uses_model_base_variable_with_dollar_prefix(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(status_code=200, content=b"data")
        info = new_footprint_info(tmp_path, model_base_variable="${KICAD_3RD_PARTY}")
        footprint = Footprint("test")

        get_StepModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        models = list(footprint.getAllChilds())
        assert (
            models[0].filename
        ) == '"${KICAD_3RD_PARTY}/packages3d/test_footprint.step"'

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_uses_model_base_variable_without_dollar_prefix(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(status_code=200, content=b"data")
        info = new_footprint_info(tmp_path, model_base_variable="KICAD_3RD_PARTY")
        footprint = Footprint("test")

        get_StepModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        models = list(footprint.getAllChilds())
        assert (
            models[0].filename
        ) == '"$(KICAD_3RD_PARTY)/packages3d/test_footprint.step"'


class TestGetWrlModel:
    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_downloads_and_converts_model_on_success(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(
            status_code=200, content=SAMPLE_WRL_SOURCE.encode()
        )
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")

        get_WrlModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        wrl_file = tmp_path / "footprint" / "packages3d" / "test_footprint.wrl"
        assert wrl_file.is_file()
        content = wrl_file.read_text()
        assert content.startswith("#VRML V2.0 utf8")
        assert "IndexedFaceSet" in content
        assert "diffuseColor 0.8 0.8 0.8" in content

        models = [
            child for child in footprint.getAllChilds() if isinstance(child, Model)
        ]
        assert len(models) == 1
        assert models[0].filename == "packages3d/test_footprint.wrl"

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_reused_vertex_indices_across_faces_are_deduplicated(
        self, mock_get, tmp_path
    ):
        mock_get.return_value = MagicMock(
            status_code=200, content=SAMPLE_WRL_SOURCE_SHARED_VERTICES.encode()
        )
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")

        get_WrlModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        wrl_file = tmp_path / "footprint" / "packages3d" / "test_footprint.wrl"
        content = wrl_file.read_text()
        # 4 unique vertices should be emitted only once each in the point
        # list, even though 2 of them are referenced by both faces.
        assert content.count("coordIndex") == 1

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_uses_model_base_variable_with_dollar_prefix(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(
            status_code=200, content=SAMPLE_WRL_SOURCE.encode()
        )
        info = new_footprint_info(tmp_path, model_base_variable="${KICAD_3RD_PARTY}")
        footprint = Footprint("test")

        get_WrlModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        models = list(footprint.getAllChilds())
        assert models[0].filename == (
            '"${KICAD_3RD_PARTY}/packages3d/test_footprint.wrl"'
        )

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_uses_model_base_variable_without_dollar_prefix(self, mock_get, tmp_path):
        mock_get.return_value = MagicMock(
            status_code=200, content=SAMPLE_WRL_SOURCE.encode()
        )
        info = new_footprint_info(tmp_path, model_base_variable="KICAD_3RD_PARTY")
        footprint = Footprint("test")

        get_WrlModel(
            component_uuid="uuid-1",
            footprint_info=info,
            kicad_mod=footprint,
            translationX=0,
            translationY=0,
            translationZ=0,
            rotation="0,0,0",
        )

        models = list(footprint.getAllChilds())
        assert models[0].filename == (
            '"$(KICAD_3RD_PARTY)/packages3d/test_footprint.wrl"'
        )

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_http_error_skips_model_creation(self, mock_get, tmp_path, caplog):
        mock_get.return_value = MagicMock(status_code=500, content=b"")
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")

        with caplog.at_level("ERROR"):
            result = get_WrlModel(
                component_uuid="uuid-1",
                footprint_info=info,
                kicad_mod=footprint,
                translationX=0,
                translationY=0,
                translationZ=0,
                rotation="0,0,0",
            )

        assert result == ()
        assert "no 3D model found" in caplog.text
        wrl_file = tmp_path / "footprint" / "packages3d" / "test_footprint.wrl"
        assert not wrl_file.exists()

    @patch("JLC2KiCadLib.footprint.model3d.requests.get")
    def test_wrl_model_not_added_if_step_model_already_present(
        self, mock_get, tmp_path, caplog
    ):
        # Simulate STEP model already having been added to the footprint
        # (i.e. both STEP and WRL requested): WRL file should still be
        # written to disk, but not appended as a second 3D model reference.
        mock_get.return_value = MagicMock(
            status_code=200, content=SAMPLE_WRL_SOURCE.encode()
        )
        info = new_footprint_info(tmp_path)
        footprint = Footprint("test")
        footprint.append(Model(filename="packages3d/test_footprint.step"))

        with caplog.at_level("INFO"):
            get_WrlModel(
                component_uuid="uuid-1",
                footprint_info=info,
                kicad_mod=footprint,
                translationX=0,
                translationY=0,
                translationZ=0,
                rotation="0,0,0",
            )

        wrl_file = tmp_path / "footprint" / "packages3d" / "test_footprint.wrl"
        assert wrl_file.is_file()

        models = [
            child for child in footprint.getAllChilds() if isinstance(child, Model)
        ]
        assert len(models) == 1  # still just the STEP model
        assert "prevent duplicates" in caplog.text
