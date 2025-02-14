import json
import logging
from math import pow, acos, pi, sqrt
import re

from KicadModTree import (
    Line,
    Pad,
    Polygon,
    Vector2D,
    Arc,
    Circle,
    RectFill,
    Text,
    RectLine,
)
from .model3d import get_WrlModel, get_StepModel

__all__ = [
    "handlers",
    "h_TRACK",
    "h_PAD",
    "h_ARC",
    "h_CIRCLE",
    "h_SOLIDREGION",
    "h_SVGNODE",
    "h_VIA",
    "h_RECT",
    "h_HOLE",
    "h_TEXT",
    "mil2mm",
]

layer_correspondance = {
    "1": "F.Cu",
    "2": "B.Cu",
    "3": "F.SilkS",
    "4": "B.Silks",
    "5": "F.Paste",
    "6": "B.Paste",
    "7": "F.Mask",
    "8": "B.Mask",
    "10": "Edge.Cuts",
    "12": "F.Fab",
    "99": "F.SilkS",
    "100": "F.SilkS",
    "101": "F.SilkS",
}


def mil2mm(data):
    return float(data) / 3.937


def h_TRACK(data, kicad_mod, footprint_info):
    data[0] = mil2mm(data[0])
    width = data[0]
    try:
        points = [mil2mm(p) for p in data[2].split(" ") if p]
    except Exception:
        if len(data) > 5:
            points = [mil2mm(p) for p in data[3].split(" ") if p]
        else:
            logging.warning(
                "footprint handler, h_TRACK: error while parsing the line's points, skipping line"
            )
            return ()

    for i in range(int(len(points) / 2) - 1):
        start = [points[2 * i], points[2 * i + 1]]
        end = [points[2 * i + 2], points[2 * i + 3]]
        try:
            layer = layer_correspondance[data[1]]
        except Exception:
            logging.exception("footprint h_TRACK: layer correspondance not found")
            layer = "F.SilkS"

        # update footprint borders
        footprint_info.max_X = max(footprint_info.max_X, start[0], end[0])
        footprint_info.min_X = min(footprint_info.min_X, start[0], end[0])
        footprint_info.max_Y = max(footprint_info.max_Y, start[1], end[1])
        footprint_info.min_Y = min(footprint_info.min_Y, start[1], end[1])

        # append line to kicad_mod
        kicad_mod.append(Line(start=start, end=end, width=width, layer=layer))


def h_PAD(data, kicad_mod, footprint_info):
    """
    Append a pad to the footprint

    data : [
        0 : shape type
        1 : pad position x
        2 : pad position y
        3 : pad size x
        4 : pad size y
        5 : layer
        6 : pad number
        7 : drill size
        8 : Polygon nodes "skipped for some shapes"
        9 : rotation
        10 :
        11 : drill offset
        12 :
        13 :
        14 :
        15 :
        16 :
        17 : ? position
    ]
    """

    # PAD layer definition
    TOPLAYER = "1"
    BOTTOMLAYER = "2"
    MULTILAYER = "11"

    shape_type = data[0]
    at = [mil2mm(data[1]), mil2mm(data[2])]
    size = [mil2mm(data[3]), mil2mm(data[4])]
    layer = data[5]
    pad_number = data[6]
    drill_diameter = float(mil2mm(data[7])) * 2
    drill_size = drill_diameter

    # Some shape do not have coordinates, insert empty data to realign later index
    if shape_type in ["ELLIPSE"]:
        data.insert(8, "")

    rotation = float(data[9])
    drill_offset = float(mil2mm(data[11]))

    primitives = ""

    if layer == MULTILAYER:
        pad_type = Pad.TYPE_THT
        pad_layer = Pad.LAYERS_THT
    elif layer == TOPLAYER:
        pad_type = Pad.TYPE_SMT
        pad_layer = Pad.LAYERS_SMT
    elif layer == BOTTOMLAYER:
        pad_type = Pad.TYPE_SMT
        pad_layer = ["B.Cu", "B.Mask", "B.Paste"]
    else:
        logging.warning(
            f"footprint, h_PAD: Unrecognized pad layer. Using default SMT layer for pad {pad_number}"
        )
        pad_type = Pad.TYPE_SMT
        pad_layer = Pad.LAYERS_SMT

    if data[0] == "OVAL":
        shape = Pad.SHAPE_OVAL

        if drill_offset == 0:
            drill_size = drill_diameter
        elif (drill_diameter < drill_offset) ^ (
            size[0] > size[1]
        ):  # invert the orientation of the drill hole if not in the same orientation as the pad shape
            drill_size = [drill_diameter, drill_offset]
        else:
            drill_size = [drill_offset, drill_diameter]

    elif data[0] == "RECT":
        shape = Pad.SHAPE_RECT

        if drill_offset == 0:
            drill_size = drill_diameter
        else:
            drill_size = [drill_diameter, drill_offset]

    elif data[0] == "ELLIPSE":
        shape = Pad.SHAPE_CIRCLE

    elif data[0] == "POLYGON":
        shape = Pad.SHAPE_CUSTOM
        points = []
        for i, coord in enumerate(data[8].split(" ")):
            points.append(mil2mm(coord) - at[i % 2])
        primitives = [Polygon(nodes=zip(points[::2], points[1::2]))]
        size = [0.1, 0.1]

        if drill_offset == 0:  # Check if the hole is oval
            drill_size = 1
        else:
            drill_size = [drill_diameter, drill_offset]

    else:
        logging.error(
            f"footprint handler, pad : no correspondance found, using default SHAPE_OVAL for pad {pad_number}"
        )
        shape = Pad.SHAPE_OVAL

    # update footprint borders
    footprint_info.max_X = max(footprint_info.max_X, at[0])
    footprint_info.min_X = min(footprint_info.min_X, at[0])
    footprint_info.max_Y = max(footprint_info.max_Y, at[1])
    footprint_info.min_Y = min(footprint_info.min_Y, at[1])

    kicad_mod.append(
        Pad(
            number=pad_number,
            type=pad_type,
            shape=shape,
            at=at,
            size=size,
            rotation=rotation,
            drill=drill_size,
            layers=pad_layer,
            primitives=primitives,
        )
    )


def h_ARC(data, kicad_mod, footprint_info):
    """
    append an Arc to the footprint
    """
    # pylint: disable=unused-argument

    try:

        # "S$xx" is sometimes inserted at index 2 ?
        if "$" in data[2]:
            svg_path = data[3]
        else:
            svg_path = data[2]

        # Regular expression to match ARC pattern
        # coordinates can sometime be separated by a "," instead of a space, therefore we match it using [\s,*?]
        pattern = r"M\s*([\d\.\-]+)[\s,*?]([\d\.\-]+)\s?A\s*([\d\.\-]+)[\s,*?]([\d\.\-]+) ([\d\.\-]+) (\d) (\d) ([\d\.\-]+)[\s,*?]([\d\.\-]+)"

        match = re.search(pattern, svg_path)

        if not match:
            logging.error("footprint handler, h_ARC: Failed to parse ARC")
            return

        # Extract values
        start_x, start_y = float(match.group(1)), float(match.group(2))
        rx, ry = float(match.group(3)), float(match.group(4))
        _ = float(match.group(5))  # rotation ?
        large_arc_flag = int(match.group(6))
        sweep_flag = int(match.group(7))
        end_x, end_y = float(match.group(8)), float(match.group(9))

        width = data[0]

        width = mil2mm(width)
        start_x = mil2mm(start_x)
        start_y = mil2mm(start_y)
        mid_x = mil2mm(rx)
        mid_y = mil2mm(ry)
        end_x = mil2mm(end_x)
        end_y = mil2mm(end_y)

        start = [start_x, start_y]
        end = [end_x, end_y]
        if sweep_flag == 0:
            start, end = end, start

        # find the midpoint of start and end
        mid = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
        # create vector from start to mid:
        vec1 = Vector2D(mid[0] - start[0], mid[1] - start[1])

        # create vector that's normal to vec1:
        length_squared = mid_x * mid_y - pow(vec1.distance_to((0, 0)), 2)
        if length_squared < 0:
            length_squared = 0
            large_arc_flag = 1

        if large_arc_flag == 1:
            vec2 = vec1.rotate(-90)
        else:
            vec2 = vec1.rotate(90)

        magnitude = sqrt(vec2[0] ** 2 + vec2[1] ** 2)
        vec2 = Vector2D(vec2[0] / magnitude, vec2[1] / magnitude)

        # calculate the lenght from mid to centre using pythagoras:
        length = sqrt(length_squared)
        # calculate the centre using mid and vec2 with the correct length:
        cen = Vector2D(mid) + vec2 * length

        cen_start = cen - start
        cen_end = cen - end

        # calculate angle between cen_start and cen_end
        dot_product = cen_start.x * cen_end.x + cen_start.y * cen_end.y
        angle = (
            acos(
                round(
                    dot_product
                    / (cen_start.distance_to((0, 0)) * cen_end.distance_to((0, 0))),
                    4,
                )
            )
            * 180
            / pi
        )

        try:
            layer = layer_correspondance[data[1]]
        except KeyError:
            logging.warning(
                "footprint handler, h_ARC : layer correspondance not found. Adding arc on default F.Silks layer"
            )
            layer = "F.SilkS"

        if large_arc_flag == 1:
            angle = 360 - angle

        kicad_mod.append(
            Arc(start=start, end=end, width=width, center=cen, layer=layer)
        )

    except Exception:
        logging.exception("footprint handler, h_ARC: failed to add ARC")


def h_CIRCLE(data, kicad_mod, footprint_info):
    # append a Circle to the footprint

    if (
        data[4] == "100"
    ):  # they want to draw a circle on pads, we don't want that. This is an empirical deduction, no idea if this is correct, but it seems to work on my tests
        return ()

    data[0] = mil2mm(data[0])
    data[1] = mil2mm(data[1])
    data[2] = mil2mm(data[2])
    data[3] = mil2mm(data[3])

    center = [data[0], data[1]]
    radius = data[2]
    width = data[3]

    try:
        layer = layer_correspondance[data[4]]
    except KeyError:
        logging.exception(
            "footprint handler, h_CIRCLE : layer correspondance not found"
        )
        layer = "F.SilkS"

    kicad_mod.append(Circle(center=center, radius=radius, width=width, layer=layer))


def h_SOLIDREGION(data, kicad_mod, footprint_info):
    try:
        # edge cut in footprint
        if data[2] == "npth":
            if (
                "A" in data[1]
            ):  # A is present for when arcs are in the shape, help is needed to parse and format these
                logging.warning(
                    "footprint handler : h_SOLIDREGION, Edge.Cuts shape not handled, see https://github.com/TousstNicolas/JLC2KiCad_lib/issues/41 for more informations"
                )
                return

            # use regular expression to find all the numeric values in the string that come after "M" or "L" (other shapes are not yet handled)
            matches = re.findall(
                r"(?:M|L)\s+([-+]?\d*\.?\d+)\s+([-+]?\d*\.?\d+)", data[1]
            )

            # convert the list of numbers to a list of tuples with x, y coordinates
            points = [(mil2mm(m[0]), mil2mm(m[1])) for m in matches]

            # appends nods to footprint
            kicad_mod.append(Polygon(nodes=points, layer="Edge.Cuts"))

    except Exception:
        logging.exception("footprint handler, h_SOLIDREGION: failed to add SOLIDREGION")
        return


def h_SVGNODE(data, kicad_mod, footprint_info):
    # create 3D model as a WRL file
    # parse json data
    try:
        data = json.loads(data[0])
    except Exception:
        logging.exception("footprint handler, h_SVGNODE : failed to parse json data")
        return ()

    c_origin = data["attrs"]["c_origin"].split(",")
    if "STEP" in footprint_info.models:
        get_StepModel(
            component_uuid=data["attrs"]["uuid"],
            footprint_info=footprint_info,
            kicad_mod=kicad_mod,
            translationX=float(c_origin[0]),
            translationY=float(c_origin[1]),
            translationZ=data["attrs"]["z"],
            rotation=data["attrs"]["c_rotation"],
        )

    if "WRL" in footprint_info.models:
        get_WrlModel(
            component_uuid=data["attrs"]["uuid"],
            footprint_info=footprint_info,
            kicad_mod=kicad_mod,
            translationX=float(c_origin[0]),
            translationY=float(c_origin[1]),
            translationZ=data["attrs"]["z"],
            rotation=data["attrs"]["c_rotation"],
        )


def h_VIA(data, kicad_mod, footprint_info):
    logging.warning(
        "VIA not supported. Via are often added for better heat dissipation. Be careful and read datasheet if needed."
    )


def h_RECT(data, kicad_mod, footprint_info):
    Xstart = float(mil2mm(data[0]))
    Ystart = float(mil2mm(data[1]))
    Xdelta = float(mil2mm(data[2]))
    Ydelta = float(mil2mm(data[3]))
    start = [Xstart, Ystart]
    end = [Xstart + Xdelta, Ystart + Ydelta]
    width = mil2mm(data[7])

    if width == 0:
        # filled:
        kicad_mod.append(
            RectFill(
                start=start,
                end=end,
                layer=layer_correspondance[data[4]],
            )
        )
    else:
        # not filled:
        kicad_mod.append(
            RectLine(
                start=start,
                end=end,
                width=width,
                layer=layer_correspondance[data[4]],
            )
        )


def h_HOLE(data, kicad_mod, footprint_info):
    kicad_mod.append(
        Pad(
            number="",
            type=Pad.TYPE_NPTH,
            shape=Pad.SHAPE_CIRCLE,
            at=[mil2mm(data[0]), mil2mm(data[1])],
            size=mil2mm(data[2]) * 2,
            rotation=0,
            drill=mil2mm(data[2]) * 2,
            layers=Pad.LAYERS_NPTH,
        )
    )


def h_TEXT(data, kicad_mod, footprint_info):
    try:
        kicad_mod.append(
            Text(
                type="user",
                at=[mil2mm(data[1]), mil2mm(data[2])],
                text=data[8],
                layer="F.SilkS",
            )
        )
    except Exception:
        logging.warning("footprint handler, h_TEXT: failed to add text")


handlers = {
    "TRACK": h_TRACK,
    "PAD": h_PAD,
    "ARC": h_ARC,
    "CIRCLE": h_CIRCLE,
    "SOLIDREGION": h_SOLIDREGION,
    "SVGNODE": h_SVGNODE,
    "VIA": h_VIA,
    "RECT": h_RECT,
    "HOLE": h_HOLE,
    "TEXT": h_TEXT,
}
