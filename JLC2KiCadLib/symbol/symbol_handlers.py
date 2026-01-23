import logging
import math
import re

RELATIVE_OFFSET = 0.254
ABSOLUTE_OFFSET_X = 101.6
ABSOLUTE_OFFSET_Y = -63.5

__all__ = [
    "handlers",
    "h_R",
    "h_E",
    "h_P",
    "h_T",
    "h_PL",
    "h_PG",
    "h_PT",
    "h_A",
    "h_AR",
]


def mil2mm(data):
    return float(data) / 3.937


def h_R(data, translation, kicad_symbol):
    """
    Rectangle handler
    data = {
    0  : x1
    1  : y1
    2  :
    3  :
    4  : width
    5  : length
    6  : stroke color
    7  : ?
    8  : stroke style : 0 = solid, 1 = dashed, 2 = dotted
    9  : fill color
    10 : id
    11 : locked
    }
    """

    x1 = float(data[0])
    y1 = float(data[1])
    width = float(data[4])
    length = float(data[5])

    x2 = x1 + width
    y2 = y1 + length

    x1_mm = mil2mm(x1 - translation[0])
    y1_mm = -mil2mm(y1 - translation[1])
    x2_mm = mil2mm(x2 - translation[0])
    y2_mm = -mil2mm(y2 - translation[1])

    if data[8] == 1:
        stroke_style = "dash"
    elif data[8] == 2:
        stroke_style = "dot"
    else:
        stroke_style = "default"

    kicad_symbol.drawing += f"""
      (rectangle
        (start {x1_mm} {y1_mm})
        (end {x2_mm} {y2_mm})
        (stroke (width 0) (type {stroke_style}) (color 0 0 0 0))
        (fill (type background))
      )"""


def h_E(data, translation, kicad_symbol):
    """
    Circle
    """

    x1 = mil2mm(float(data[0]) - translation[0])
    y1 = -mil2mm(float(data[1]) - translation[1])
    radius = mil2mm(float(data[2]))

    kicad_symbol.drawing += f"""
      (circle
        (center {x1} {y1})
        (radius {radius})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""


def h_P(data, translation, kicad_symbol):
    """
    Add Pin to the symbol
    data = [
    0  :
    1  : electrical type
    2  : pin number
    3  : x1
    4  : y1
    5  : rotation
    6  : id
    7  :
    8  :
    9  :
    10 :
    11 :
    12 :
    13 :
    14 :
    15 :
    16 :
    17 : name size
    18 :
    19 :
    20 :
    21 :
    22 :
    23 :
    24 : number size
    25 :
    ]
    """

    if data[1] == "0":
        electrical_type = "unspecified"
    elif data[1] == "1":
        electrical_type = "input"
    elif data[1] == "2":
        electrical_type = "output"
    elif data[1] == "3":
        electrical_type = "bidirectional"
    elif data[1] == "4":
        electrical_type = "power_in"
    else:
        electrical_type = "unspecified"

    pin_number = data[2]
    pin_name = data[13]

    x1 = round(mil2mm(float(data[3]) - translation[0]), 3)
    y1 = round(-mil2mm(float(data[4]) - translation[1]), 3)

    rotation = (int(data[5]) + 180) % 360 if data[5] else 180

    if rotation == 0 or rotation == 180:
        length = round(mil2mm(abs(float(data[8].split("h")[-1]))), 3)
    elif rotation == 90 or rotation == 270:
        length = mil2mm(abs(float(data[8].split("v")[-1])))
    else:
        length = 2.54
        logging.warning(
            f'symbol : pin number {pin_number} : "{pin_name}" failed to find length.'
            "Using Default length"
        )

    if data[9].split("^^")[1] != "0":
        kicad_symbol.pinNamesHide = ""
    if data[17].split("^^")[1] != "0":
        kicad_symbol.pinNumbersHide = ""

    name_size = mil2mm(float(data[16].replace("pt", ""))) if data[16] else 1
    number_size = mil2mm(float(data[24].replace("pt", ""))) if data[24] else 1

    kicad_symbol.drawing += f"""
      (pin {electrical_type} line
        (at {x1} {y1} {rotation})
        (length {length})
        (name "{pin_name}" (effects (font (size {name_size} {name_size}))))
        (number "{pin_number}" (effects (font (size {number_size} {number_size}))))
      )"""


def h_T(data, translation, kicad_symbol):
    """
    Text handler
    data = [
    0  :
    1  : x1
    2  : y1
    3  : rotation
    4  : color
    5  : font
    6  : font size
    7  :
    8  :
    9  :
    10 :
    11 : text
    12 :
    13 : anchor
    ]
    """

    x1 = mil2mm(float(data[1]) - translation[0])
    y1 = -mil2mm(float(data[2]) - translation[1])

    # From https://dev-docs.kicad.org/en/file-formats/sexpr-intro/index.html#_position_identifier
    # Symbol text ANGLEs are stored in tenth’s of a degree. All other ANGLEs are stored
    # in degrees.
    rotation = ((int(data[3]) + 180) % 360) * 10

    font_size = mil2mm(float(data[6].replace("pt", ""))) if data[6] else 15

    text = data[11]

    if data[13] == "middle":
        justify = "left"
    elif data[13] == "end":
        justify = "right"
    else:
        justify = "left"

    kicad_symbol.drawing += f"""
      (text
        "{text}"
        (at {x1} {y1} {rotation})
        (effects 
            (font (size {font_size} {font_size}))
            (justify {justify} bottom)
        )
      )"""


def h_PL(data, translation, kicad_symbol):
    """
    Polygone handler
    """

    path_string = data[0].split(" ")
    polypts = []
    for i, _ in enumerate(path_string[::2]):
        polypts.append(
            f"(xy {mil2mm(float(path_string[2 * i]) - translation[0])} "
            f"{-mil2mm(float(path_string[2 * i + 1]) - translation[-1])})"
        )
    polystr = "\n          ".join(polypts)

    kicad_symbol.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""


def h_PG(data, translation, kicad_symbol):
    """
    Closed polygone handler
    """

    path_string = [i for i in data[0].split(" ") if i]
    polypts = []
    for i, _ in enumerate(path_string[::2]):
        polypts.append(
            f"(xy {mil2mm(float(path_string[2 * i]) - translation[0])} "
            f"{-mil2mm(float(path_string[2 * i + 1]) - translation[1])})"
        )
    polypts.append(polypts[0])
    polystr = "\n          ".join(polypts)

    kicad_symbol.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""


def h_PT(data, translation, kicad_symbol):
    """
    Triangle handler
    """

    data[0] = (
        data[0].replace("M", "").replace("L", "").replace("Z", "").replace("C", "")
    )
    h_PG(data, translation, kicad_symbol)


def h_A(data, translation, kicad_symbol):
    """
    Arc handler
    """

    # Parse SVG path: "M x1 y1 A rx ry rotation large-arc sweep x2 y2"
    path = data[0].strip()

    # Split into M and A commands
    parts = re.split(r"[MA]", path)
    parts = [p.strip() for p in parts if p.strip()]

    # Parse M command (start point)
    start_coords = re.split(r"[\s,]+", parts[0])
    x1 = float(start_coords[0])
    y1 = float(start_coords[1])

    # Parse A command (arc parameters)
    arc_params = re.split(r"[\s,]+", parts[1])
    rx = float(arc_params[0])
    ry = float(arc_params[1])
    rotation = float(arc_params[2])
    large_arc_flag = int(arc_params[3])
    sweep_flag = int(arc_params[4])
    x2 = float(arc_params[5])
    y2 = float(arc_params[6])

    cos_rot = math.cos(math.radians(rotation))
    sin_rot = math.sin(math.radians(rotation))

    # Step 1: Compute (x1', y1')
    dx = (x1 - x2) / 2
    dy = (y1 - y2) / 2
    x1_prime = cos_rot * dx + sin_rot * dy
    y1_prime = -sin_rot * dx + cos_rot * dy

    # Step 2: Compute center (cx', cy')
    rx_sq = rx * rx
    ry_sq = ry * ry
    x1_prime_sq = x1_prime * x1_prime
    y1_prime_sq = y1_prime * y1_prime

    # Correct radii if needed
    lambda_sq = x1_prime_sq / rx_sq + y1_prime_sq / ry_sq
    if lambda_sq > 1:
        rx *= math.sqrt(lambda_sq)
        ry *= math.sqrt(lambda_sq)
        rx_sq = rx * rx
        ry_sq = ry * ry

    sign = -1 if large_arc_flag == sweep_flag else 1

    if (rx_sq * y1_prime_sq + ry_sq * x1_prime_sq) == 0:
        return

    sq = max(
        0,
        (rx_sq * ry_sq - rx_sq * y1_prime_sq - ry_sq * x1_prime_sq)
        / (rx_sq * y1_prime_sq + ry_sq * x1_prime_sq),
    )
    coef = sign * math.sqrt(sq)

    cx_prime = coef * rx * y1_prime / ry
    cy_prime = -coef * ry * x1_prime / rx

    # Step 3: Compute center (cx, cy)
    cx = cos_rot * cx_prime - sin_rot * cy_prime + (x1 + x2) / 2
    cy = sin_rot * cx_prime + cos_rot * cy_prime + (y1 + y2) / 2

    # Calculate angles for finding midpoint
    def angle_between(ux, uy, vx, vy):
        n = math.sqrt(ux * ux + uy * uy) * math.sqrt(vx * vx + vy * vy)
        c = (ux * vx + uy * vy) / n
        c = max(-1, min(1, c))  # Clamp to [-1, 1]
        angle = math.acos(c)
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

    if sweep_flag == 0 and dtheta > 0:
        dtheta -= 2 * math.pi
    elif sweep_flag == 1 and dtheta < 0:
        dtheta += 2 * math.pi

    # Calculate midpoint angle
    mid_angle = theta1 + dtheta / 2

    # Calculate midpoint coordinates
    x_mid = cx + rx * math.cos(mid_angle) * cos_rot - ry * math.sin(mid_angle) * sin_rot
    y_mid = cy + rx * math.cos(mid_angle) * sin_rot + ry * math.sin(mid_angle) * cos_rot

    # Convert to KiCad coordinates (mil to mm and apply translation)
    x1_mm = mil2mm(x1 - translation[0])
    y1_mm = -mil2mm(y1 - translation[1])
    x2_mm = mil2mm(x2 - translation[0])
    y2_mm = -mil2mm(y2 - translation[1])
    x_mid_mm = mil2mm(x_mid - translation[0])
    y_mid_mm = -mil2mm(y_mid - translation[1])

    kicad_symbol.drawing += f"""
      (arc
        (start {x1_mm} {y1_mm})
        (mid {x_mid_mm} {y_mid_mm})
        (end {x2_mm} {y2_mm})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""


def h_AR(data, translation, kicad_symbol):
    """
    Arrowhead handler

    data = {
        0  : type
        1  : x position
        2  : y position
        3  : id
        4  : rotation angle
        5  : SVG path
        6  : stroke color
        7  : ?
        8  : stroke width?
        9  : ?
    }
    """

    svg_path = data[5]

    # Remove SVG commands and extract coordinates
    path_cleaned = svg_path.replace("M", "").replace("L", "").replace("Z", "").strip()

    # Split into coordinate pairs
    coords = re.split(r"[\s,]+", path_cleaned)
    coords = [c for c in coords if c]

    polypts = []
    for i in range(0, len(coords) - 1, 2):
        x = float(coords[i])
        y = float(coords[i + 1])
        polypts.append(
            f"(xy {mil2mm(x - translation[0])} {-mil2mm(y - translation[1])})"
        )

    if not polypts:
        return

    # Close the polygon
    polypts.append(polypts[0])
    polystr = "\n          ".join(polypts)

    kicad_symbol.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""


handlers = {
    "R": h_R,
    "E": h_E,
    "P": h_P,
    "T": h_T,
    "PL": h_PL,
    "PG": h_PG,
    "PT": h_PT,
    "A": h_A,
    "AR": h_AR,
    # "J" : h_NotYetImplemented,
    # "N" : h_NotYetImplemented,
    # "BE" : h_NotYetImplemented,
    # "O" : h_NotYetImplemented,
}
