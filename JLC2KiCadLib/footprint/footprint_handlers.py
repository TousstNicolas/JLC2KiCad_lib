import json
import logging
from math import pow, acos, pi
import re

from KicadModTree import *
from .model3d import get_3Dmodel

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
    shape_correspondance = {
        "OVAL": "SHAPE_OVAL",
        "RECT": "SHAPE_RECT",
        "ELLIPSE": "SHAPE_CIRCLE",
        "POLYGON": "SHAPE_CUSTOM",
    }

    data[1] = mil2mm(data[1])
    data[2] = mil2mm(data[2])
    data[3] = mil2mm(data[3])
    data[4] = mil2mm(data[4])
    data[7] = mil2mm(data[7])

    pad_number = data[6]
    at = [data[1], data[2]]
    size = [data[3], data[4]]
    drill_size = data[7] * 2
    primitives = ""

    if data[0] in shape_correspondance:
        shape = shape_correspondance[data[0]]
    else:
        logging.error(
            "footprint handler, pad : no correspondance found, using default SHAPE_OVAL"
        )
        shape = "SHAPE_OVAL"

    # if pad is Circle, no rotation is specified
    if shape == "SHAPE_CIRCLE":
        rotation = 0
    else:
        rotation = float(data[9])

    if data[5] == "1":
        drill_size = 1
        pad_type = Pad.TYPE_SMT
        pad_layer = Pad.LAYERS_SMT
        if shape == "SHAPE_CUSTOM":
            points = []
            for i, coord in enumerate(data[8].split(" ")):
                points.append(mil2mm(coord) - at[i % 2])
            primitives = [Polygon(nodes=zip(points[::2], points[1::2]))]

    elif data[5] == "11" and shape == "SHAPE_OVAL":
        pad_type = Pad.TYPE_THT
        pad_layer = Pad.LAYERS_THT
        data[11] = mil2mm(data[11])
        if data[11] == 0:
            drill_size = data[7] * 2
        elif (data[7] * 2 < data[11]) ^ (
            size[0] > size[1]
        ):  # invert the orientation of the drill hole if not in the same orientation as the pad shape
            drill_size = [data[7] * 2, data[11]]
        else:
            drill_size = [data[11], data[7] * 2]

    elif data[5] == "11" and shape == "SHAPE_CIRCLE":
        pad_type = Pad.TYPE_THT
        pad_layer = Pad.LAYERS_THT

    elif data[5] == "11" and shape == "SHAPE_RECT":
        if float(data[11]) == 0:  # Check if the hole is oval
            pass
        else:
            drill_size = [drill_size, mil2mm(data[11])]

        pad_type = Pad.TYPE_THT
        pad_layer = Pad.LAYERS_THT

    else:
        logging.warning(
            f"footprint handler, pad : unknown assembly_process skiping pad n° : {pad_number}"
        )
        return ()

    # update footprint borders
    footprint_info.max_X = max(footprint_info.max_X, data[1])
    footprint_info.min_X = min(footprint_info.min_X, data[1])
    footprint_info.max_Y = max(footprint_info.max_Y, data[2])
    footprint_info.min_Y = min(footprint_info.min_Y, data[2])

    kicad_mod.append(
        Pad(
            number=pad_number,
            type=pad_type,
            shape=getattr(Pad, shape),
            at=at,
            size=size,
            rotation=rotation,
            drill=drill_size,
            layers=pad_layer,
            primitives=primitives,
        )
    )


def h_ARC(data, kicad_mod, footprint_info):
    # append an Arc to the footprint
    try:
        # parse the data
        if data[2][0] == "M":
            startX, startY, midX, midY, _, reversed, direction, endX, endY = [
                val
                for val in data[2]
                .replace("M", "")
                .replace("A", "")
                .replace(",", " ")
                .split(" ")
                if val
            ]
        elif data[3][0] == "M":
            startX, startY, midX, midY, _, reversed, direction, endX, endY = [
                val
                for val in data[3]
                .replace("M", "")
                .replace("A", "")
                .replace(",", " ")
                .split(" ")
                if val
            ]
        else:
            logging.warning(
                "footprint handler, h_ARC : failed to parse footprint ARC data"
            )
        width = data[0]

        width = mil2mm(width)
        startX = mil2mm(startX)
        startY = mil2mm(startY)
        midX = mil2mm(midX)
        midY = mil2mm(midY)
        endX = mil2mm(endX)
        endY = mil2mm(endY)

        if midX != midY:
            logging.warning("Unexpected arc, midX != midY")

        start = [startX, startY]
        end = [endX, endY]
        if direction == "0":
            start, end = end, start

        # find the midpoint of start and end
        mid = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
        # create vector from start to mid:
        vec1 = Vector2D(mid[0] - start[0], mid[1] - start[1])
        # create vector that's normal to vec1:

        length_squared = pow(midX, 2) - pow(vec1.distance_to((0, 0)), 2)
        if length_squared < 0:
            length_squared = 0
            reversed = "1"

        if reversed == "1":
            vec2 = vec1.rotate(-90)
            magnitude = sqrt(vec2[0] ** 2 + vec2[1] ** 2)
            vec2 = Vector2D(vec2[0] / magnitude, vec2[1] / magnitude)
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
            logging.warning("footprint handler, h_ARC : layer correspondance not found")
            layer = "F.SilkS"
        if reversed == "1":
            kicad_mod.append(
                Arc(
                    start=start,
                    end=end,
                    width=width,
                    angle=360 - angle,
                    center=cen,
                    layer=layer,
                )
            )
        else:
            kicad_mod.append(
                Arc(start=start, end=end, width=width, center=cen, layer=layer)
            )

    except Exception as e:
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
    get_3Dmodel(
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
