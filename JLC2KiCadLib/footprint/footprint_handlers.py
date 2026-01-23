import json
import logging
import re
from math import acos, cos, pi, pow, radians, sin, sqrt

from KicadModTree import (
    Arc,
    Circle,
    Line,
    Pad,
    Polygon,
    RectFill,
    RectLine,
    Text,
    Vector2D,
)

from .model3d import get_StepModel, get_WrlModel

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
    "svg_arc_to_points",
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
    "11": "",  # EasyEDA "Multilayer"
    "12": "F.Fab",
    "99": "",  # EasyEDA "Component shape layer"
    "100": "",  # EasyEDA "Pin soldering layer"
    "101": "",  # EasyEDA "Component marking layer"
}


def mil2mm(data):
    return float(data) / 3.937


def h_TRACK(data, kicad_mod, footprint_info):
    """
    Append a line to the footprint

    data : [
        0 : width
        1 : layer
        2 :
        3 : points list
        4 : id
    ]
    """

    width = mil2mm(data[0])

    points = [mil2mm(p) for p in data[3].split(" ") if p]

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
        0  : shape type
        1  : pad position x
        2  : pad position y
        3  : pad size x
        4  : pad size y
        5  : layer
        6  :
        7  : pad number
        8  : drill size
        9  : Polygon nodes
        10 : rotation
        11 : id
        12 : drill offset
        13 :
        14 : plated
        15 :
        16 :
        17 :
        18 :
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

    drill_diameter = float(mil2mm(data[8])) * 2
    drill_size = drill_diameter

    rotation = float(data[10])
    drill_offset = float(mil2mm(data[12])) if data[12] else 0

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
            f"footprint, h_PAD: Unrecognized pad layer. Using default SMT layer for "
            f"pad {pad_number}"
        )
        pad_type = Pad.TYPE_SMT
        pad_layer = Pad.LAYERS_SMT

    if shape_type == "OVAL":
        shape = Pad.SHAPE_OVAL

        if drill_offset == 0:
            drill_size = drill_diameter

        elif (drill_diameter < drill_offset) ^ (
            size[0] > size[1]
        ):  # invert the orientation of the drill hole if not in the same orientation
            # as the pad shape
            drill_size = [drill_diameter, drill_offset]
        else:
            drill_size = [drill_offset, drill_diameter]

    elif shape_type == "RECT":
        shape = Pad.SHAPE_RECT

        if drill_offset == 0:
            drill_size = drill_diameter
        else:
            drill_size = [drill_diameter, drill_offset]

    elif shape_type == "ELLIPSE":
        shape = Pad.SHAPE_CIRCLE

    elif shape_type == "POLYGON":
        shape = Pad.SHAPE_CUSTOM
        points = []
        for i, coord in enumerate(data[9].split(" ")):
            points.append(mil2mm(coord) - at[i % 2])
        primitives = [Polygon(nodes=zip(points[::2], points[1::2], strict=True))]
        size = [0.1, 0.1]

        drill_size = 1 if drill_offset == 0 else [drill_diameter, drill_offset]

    else:
        logging.error(
            f"footprint handler, pad : no correspondance found, using default "
            f"SHAPE_OVAL for pad {pad_number}"
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
    data : [
        0  : width
        1  : layer
        2  :
        3  : nodes
        4  :
        5  : id
    ]
    """

    width = data[0]
    layer = layer_correspondance[data[1]]
    svg_path = data[3]

    # Parse SVG path
    pattern = (
        r"M\s*([-\d.]+)[\s,]+([-\d.]+)\s*A\s*([-\d.]+)[\s,]+"
        r"([-\d.]+)[\s,]+([-\d.]+)[\s,]+(\d)[\s,]+(\d)[\s,]+([-\d.]+)[\s,]+([-\d.]+)"
    )

    match = re.search(pattern, svg_path)

    if not match:
        logging.error("footprint handler, h_ARC: failed to parse ARC")
        return

    # Extract values
    start_x, start_y = float(match.group(1)), float(match.group(2))
    rx, ry = float(match.group(3)), float(match.group(4))
    _ = float(match.group(5))  # rotation ?
    large_arc_flag = int(match.group(6))
    sweep_flag = int(match.group(7))
    end_x, end_y = float(match.group(8)), float(match.group(9))

    width = mil2mm(width)
    start_x = mil2mm(start_x)
    start_y = mil2mm(start_y)
    radius_x = mil2mm(rx)
    radius_y = mil2mm(ry)
    end_x = mil2mm(end_x)
    end_y = mil2mm(end_y)

    start = [start_x, start_y]
    end = [end_x, end_y]

    # Check if this is a full circle (start == end)
    if abs(start_x - end_x) < 1e-6 and abs(start_y - end_y) < 1e-6:
        # Full circle: center is offset from start by radius
        # Direction depends on sweep_flag
        radius = radius_x  # Assuming circular arc (rx == ry)
        # For sweep_flag=1 (clockwise in SVG), center is to the right
        # For sweep_flag=0 (counter-clockwise), center is to the left
        if sweep_flag == 1:
            center = [start_x + radius, start_y]
        else:
            center = [start_x - radius, start_y]
        kicad_mod.append(Circle(center=center, radius=radius, width=width, layer=layer))
        return

    if sweep_flag == 0:
        start, end = end, start

    # find the midpoint of start and end
    mid = [(start[0] + end[0]) / 2, (start[1] + end[1]) / 2]
    # create vector from start to mid:
    vec1 = Vector2D(mid[0] - start[0], mid[1] - start[1])

    # create vector that's normal to vec1:
    length_squared = radius_x * radius_y - pow(vec1.distance_to((0, 0)), 2)
    if length_squared < 0:
        length_squared = 0
        large_arc_flag = 1

    vec2 = vec1.rotate(-90) if large_arc_flag == 1 else vec1.rotate(90)

    magnitude = sqrt(vec2[0] ** 2 + vec2[1] ** 2)
    vec2 = Vector2D(vec2[0] / magnitude, vec2[1] / magnitude)

    length = sqrt(length_squared)
    cen = Vector2D(mid) + vec2 * length

    kicad_mod.append(Arc(start=start, end=end, width=width, center=cen, layer=layer))


def h_CIRCLE(data, kicad_mod, footprint_info):
    # append a Circle to the footprint

    if (
        data[4] == "100"
    ):  # they want to draw a circle on pads, we don't want that. This is an empirical
        # deduction, no idea if this is correct, but it seems to work on my tests
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


def svg_arc_to_points(x1, y1, rx, ry, rotation, large_arc_flag, sweep_flag, x2, y2):
    """
    Convert SVG arc to list of points using center parameterization.
    Uses SVG arc implementation algorithm from W3C spec F.6.5.

    Args:
        x1, y1: Start point
        rx, ry: Ellipse radii
        rotation: X-axis rotation in degrees
        large_arc_flag: 0 or 1
        sweep_flag: 0 or 1
        x2, y2: End point

    Returns:
        List of (x, y) tuples representing points along the arc
    """
    # Handle degenerate cases
    if x1 == x2 and y1 == y2:
        return []
    if rx == 0 or ry == 0:
        return [(x2, y2)]

    rx = abs(rx)
    ry = abs(ry)

    cos_rot = cos(radians(rotation))
    sin_rot = sin(radians(rotation))

    # Compute (x1', y1') - rotated coordinates
    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1_prime = cos_rot * dx + sin_rot * dy
    y1_prime = -sin_rot * dx + cos_rot * dy

    # Compute center (cx', cy')
    rx_sq = rx * rx
    ry_sq = ry * ry
    x1_prime_sq = x1_prime * x1_prime
    y1_prime_sq = y1_prime * y1_prime

    # Correct radii if needed (ensure arc is possible)
    lambda_sq = x1_prime_sq / rx_sq + y1_prime_sq / ry_sq
    if lambda_sq > 1:
        scale = sqrt(lambda_sq)
        rx *= scale
        ry *= scale
        rx_sq = rx * rx
        ry_sq = ry * ry

    # Calculate center
    denom = rx_sq * y1_prime_sq + ry_sq * x1_prime_sq
    if denom == 0:
        return [(x2, y2)]

    sign = -1 if large_arc_flag == sweep_flag else 1
    sq = max(0, (rx_sq * ry_sq - rx_sq * y1_prime_sq - ry_sq * x1_prime_sq) / denom)
    coef = sign * sqrt(sq)

    cx_prime = coef * rx * y1_prime / ry
    cy_prime = -coef * ry * x1_prime / rx

    # Compute center (cx, cy) in original coordinates
    cx = cos_rot * cx_prime - sin_rot * cy_prime + (x1 + x2) / 2
    cy = sin_rot * cx_prime + cos_rot * cy_prime + (y1 + y2) / 2

    # Calculate start angle and delta angle
    def angle_between(ux, uy, vx, vy):
        n = sqrt(ux * ux + uy * uy) * sqrt(vx * vx + vy * vy)
        if n == 0:
            return 0
        c = (ux * vx + uy * vy) / n
        c = max(-1, min(1, c))
        angle = acos(c)
        if ux * vy - uy * vx < 0:
            angle = -angle
        return angle

    theta1 = angle_between(1, 0, (x1_prime - cx_prime) / rx, (y1_prime - cy_prime) / ry)
    dtheta = angle_between(
        (x1_prime - cx_prime) / rx,
        (y1_prime - cy_prime) / ry,
        (-x1_prime - cx_prime) / rx,
        (-y1_prime - cy_prime) / ry,
    )

    # Adjust delta angle based on sweep flag
    if sweep_flag == 0 and dtheta > 0:
        dtheta -= 2 * pi
    elif sweep_flag == 1 and dtheta < 0:
        dtheta += 2 * pi

    # Generate points along the arc (adaptive resolution)
    num_segments = max(8, int(abs(dtheta) / (2 * pi) * 32))

    points = []
    for i in range(1, num_segments + 1):  # Skip first point (it's the current position)
        angle = theta1 + dtheta * i / num_segments
        x = cx + rx * cos(angle) * cos_rot - ry * sin(angle) * sin_rot
        y = cy + rx * cos(angle) * sin_rot + ry * sin(angle) * cos_rot
        points.append((x, y))

    return points


def h_SOLIDREGION(data, kicad_mod, footprint_info):
    layer = "Edge.Cuts" if data[3] == "npth" else layer_correspondance[data[0]]

    path = data[2]
    points = []
    current_pos = (0.0, 0.0)

    # Parse SVG path
    command_pattern = re.compile(
        r"([MLAZ])\s*"
        r"((?:[-+]?\d*\.?\d+[\s,]*)*)",
        re.IGNORECASE,
    )

    # Pattern to extract numbers
    number_pattern = re.compile(r"[-+]?\d*\.?\d+")

    for match in command_pattern.finditer(path):
        cmd = match.group(1).upper()
        params_str = match.group(2)
        params = [float(n) for n in number_pattern.findall(params_str)]

        if cmd == "M":
            # Move to: M x y
            if len(params) >= 2:
                current_pos = (params[0], params[1])
                points.append(current_pos)

        elif cmd == "L":
            # Line to: L x y
            if len(params) >= 2:
                current_pos = (params[0], params[1])
                points.append(current_pos)

        elif cmd == "A":
            # Arc: A rx ry rotation large-arc-flag sweep-flag x y
            if len(params) >= 7:
                rx = params[0]
                ry = params[1]
                rotation = params[2]
                large_arc_flag = int(params[3])
                sweep_flag = int(params[4])
                end_x = params[5]
                end_y = params[6]

                arc_points = svg_arc_to_points(
                    current_pos[0],
                    current_pos[1],
                    rx,
                    ry,
                    rotation,
                    large_arc_flag,
                    sweep_flag,
                    end_x,
                    end_y,
                )
                points.extend(arc_points)
                current_pos = (end_x, end_y)

        elif cmd == "Z":
            # Close path - no action needed, polygon will close automatically
            pass

    # Convert from mils to mm
    points = [(mil2mm(p[0]), mil2mm(p[1])) for p in points]

    if points:
        kicad_mod.append(Polygon(nodes=points, layer=layer))


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
        "VIA not supported. Via are often added for better heat dissipation. "
        "Be careful and read datasheet if needed."
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
    kicad_mod.append(
        Text(
            type="user",
            text=data[9],
            at=[mil2mm(data[1]), mil2mm(data[2])],
            layer="F.SilkS",
        )
    )


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
