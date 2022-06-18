import json
import logging
from math import pow

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
            startX, startY, midX, midY, _, _, _, endX, endY = [
                val
                for val in data[2]
                .replace("M", "")
                .replace("A", "")
                .replace(",", " ")
                .split(" ")
                if val
            ]
        elif data[3][0] == "M":
            startX, startY, midX, midY, _, _, _, endX, endY = [
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

        start = [startX, startY]
        end = [endX, endY]
        midpoint = [end[0] + midX, end[1] + midY]

        sq1 = (
            pow(midpoint[0], 2)
            + pow(midpoint[1], 2)
            - pow(start[0], 2)
            - pow(start[1], 2)
        )
        sq2 = pow(end[0], 2) + pow(end[1], 2) - pow(start[0], 2) - pow(start[1], 2)

        centerX = ((start[1] - end[1]) / (start[1] - midpoint[1]) * sq1 - sq2) / (
            2 * (start[0] - end[0])
            - 2
            * (start[0] - midpoint[0])
            * (start[1] - end[1])
            / (start[1] - midpoint[1])
        )
        centerY = -(2 * (start[0] - midpoint[0]) * centerX + sq1) / (
            2 * (start[1] - midpoint[1])
        )
        center = [centerX, centerY]

        try:
            layer = layer_correspondance[data[1]]
        except KeyError:
            logging.warning("footprint handler, h_ARC : layer correspondance not found")
            layer = "F.SilkS"

        kicad_mod.append(
            Arc(center=center, start=start, end=end, width=width, layer=layer)
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
    pass


def h_SVGNODE(data, kicad_mod, footprint_info):
    # create 3D model as a WRL file

    get_3Dmodel(
        component_uuid=json.loads(data[0])["attrs"]["uuid"],
        footprint_info=footprint_info,
        kicad_mod=kicad_mod,
        translationZ=json.loads(data[0])["attrs"]["z"],
        rotation=json.loads(data[0])["attrs"]["c_rotation"],
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
    nodes = [
        [Xstart, Ystart],
        [Xstart + Xdelta, Ystart],
        [Xstart + Xdelta, Ystart + Ydelta],
        [Xstart, Ystart + Ydelta],
    ]

    kicad_mod.append(Polygon(nodes=nodes, layer=layer_correspondance[data[4]]))


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
                layer=layer_correspondance[data[7]],
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
