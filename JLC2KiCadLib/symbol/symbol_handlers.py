import logging
import re

RELATIVE_OFFSET = 0.254
ABSOLUTE_OFFSET_X = 101.6
ABSOLUTE_OFFSET_Y = -63.5

__all__ = ["handlers", "h_R", "h_E", "h_P", "h_T", "h_PL", "h_PG", "h_PT", "h_A"]


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

    from math import acos, cos, pi, sin, sqrt

    # ruff: disable [E741]
    # Function reversed from https://easyeda.com/editor/6.5.5/js/editorPCB.min.js
    def getCenterParam(match):
        e = float([i for i in re.split(r" |,", match[0][1]) if i][0])
        t = float([i for i in re.split(r" |,", match[0][1]) if i][1])
        s = float([i for i in re.split(r" |,", match[1][1]) if i][0])
        l = float([i for i in re.split(r" |,", match[1][1]) if i][1])
        r = float([i for i in re.split(r" |,", match[1][1]) if i][3])
        o = float([i for i in re.split(r" |,", match[1][1]) if i][4])
        n = float([i for i in re.split(r" |,", match[1][1]) if i][5])
        a = float([i for i in re.split(r" |,", match[1][1]) if i][6])

        def c(e, t, n, a):
            i = e * n + t * a
            r = sqrt((e * e + t * t) * (n * n + a * a))
            o = acos(i / r)
            return o

        f = 2 * pi
        if o < 0:
            o = -o
        if s < 0:
            s = -s
        if o == s:
            l = 0
        C = sin(l)
        y = cos(l)
        b = (e - n) / 2
        v = (t - a) / 2
        S = (e + n) / 2
        P = (t + a) / 2
        if o < 0.00001 or s < 0.00001:
            h = c(1, 0, n - e, a - t)
            return (S, P, h, pi)
        A = y * b + C * v
        T = y * v - C * b
        D = A * A / (o * o) + T * T / (s * s)
        if D > 1:
            o *= sqrt(D)
            s *= sqrt(D)
        k = o * s
        M = o * T
        I = s * A
        L = M * M + I * I
        if not L:
            return (S, P, 0, 0)
        w = (k * k - L) / L
        w = sqrt(abs(w))
        O = w * M / s
        R = -w * I / o
        u = y * O - C * R + S
        g = C * O + y * R + P
        E = (A - O) / o
        N = (A + O) / o
        F = (T - R) / s
        x = (T + R) / s
        h = c(1, 0, E, F)
        m = c(E, F, -N, -x)
        while m > f:
            m -= f
        while m < 0:
            m += f
        if r != 0:
            m -= f
        return (u, g, h, m)

    # ruff: enable [E741]

    try:
        match = re.findall(r"([MA])([eE ,\-\+.\d]+)", data[0])
        cx, cy, theta, deltaTheta = getCenterParam(match)
        radius = float([i for i in re.split(r" |,", match[1][1]) if i][0])
        theta /= 2
        Xstart = cx + radius * cos(theta)
        Ystart = -(cy - radius * sin(theta))
        Xend = cx + radius * cos(theta + deltaTheta)
        Yend = -(cy - radius * sin(theta + deltaTheta))
        Xmid = cx + radius * cos(theta + deltaTheta / 2)
        Ymid = -(cy - radius * sin(theta + deltaTheta / 2))

        Xstart = mil2mm(Xstart - translation[0])
        Ystart = -mil2mm(Ystart - translation[1])
        Xend = mil2mm(Xend - translation[0])
        Yend = -mil2mm(Yend - translation[1])
        Xmid = mil2mm(Xmid - translation[0])
        Ymid = -mil2mm(Ymid - translation[1])

        kicad_symbol.drawing += f"""
      (arc
        (start {Xstart} {Ystart})
        (mid {Xmid} {Ymid})
        (end {Xend} {Yend})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""
    except Exception:
        logging.error("symbol : failed to add an arc")


handlers = {
    "R": h_R,
    "E": h_E,
    "P": h_P,
    "T": h_T,
    "PL": h_PL,
    "PG": h_PG,
    "PT": h_PT,
    "A": h_A,
    # "J" : h_NotYetImplemented,
    # "N" : h_NotYetImplemented,
    # "BE" : h_NotYetImplemented,
    # "AR" : h_NotYetImplemented,
    # "O" : h_NotYetImplemented,
}
