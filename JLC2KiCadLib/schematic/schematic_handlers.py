import logging
import re

RELATIVE_OFFSET = 0.254
ABSOLUTE_OFFSET_X = 101.6
ABSOLUTE_OFFSET_Y = -63.5

__all__ = ["handlers", "h_R", "h_E", "h_P", "h_T", "h_PL", "h_PG", "h_PT", "h_A"]


def mil2mm(data):
    return float(data) / 3.937


def h_R(data, translation, kicad_schematic):
    """
    Rectangle handler
    """

    try:
        if len(data) == 12:
            X1 = float(data[0])
            Y1 = float(data[1])
            X2 = float(X1) + float(data[4])
            Y2 = float(Y1) + float(data[5])
        else:
            X1 = float(data[0])
            Y1 = float(data[1])
            X2 = float(X1) + float(data[2])
            Y2 = float(Y1) + float(data[3])

        X1 = mil2mm(X1 - translation[0])
        Y1 = -mil2mm(Y1 - translation[1])
        X2 = mil2mm(X2 - translation[0])
        Y2 = -mil2mm(Y2 - translation[1])

        kicad_schematic.drawing += f"""
      (rectangle
        (start {X1} {Y1})
        (end {X2} {Y2})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""
    except Exception as e:
        print(e)
        logging.error("Schematic : failed to add a rectangle")


def h_E(data, translation, kicad_schematic):
    """
    Circle
    """

    try:

        X1 = mil2mm(float(data[0]) - translation[0])
        Y1 = -mil2mm(float(data[1]) - translation[1])
        radius = mil2mm(float(data[2]))

        kicad_schematic.drawing += f"""
      (circle
        (center {X1} {Y1})
        (radius {radius})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""
    except Exception as e:
        print(e)
        logging.error("schematic : failed to add circle")


def h_P(data, translation, kicad_schematic):
    """
    Add Pin to the schematic
    """

    if len(data) == 24:  # sometimes, the rotation parameter is not in the list.
        data.insert(5, "0")
    elif len(data) == 28:
        data.insert(1, "0")

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

    pinNumber = data[2]
    pinName = data[13]

    X = mil2mm(float(data[3]) - translation[0])
    Y = -mil2mm(float(data[4]) - translation[1])

    if data[5] in ["0", "90", "180", "270"]:
        rotation = (int(data[5]) + 180) % 360
    else:
        rotation = 0
        logging.warning(
            f'Schematic : pin number {pinNumber} : "{pinName}" failed to find orientation. Using Default orientation'
        )

    if rotation == 0 or rotation == 180:
        length = mil2mm(abs(float(data[8].split("h")[-1])))
    elif rotation == 90 or rotation == 270:
        length = mil2mm(abs(float(data[8].split("v")[-1])))

    try:
        if not kicad_schematic.pinNamesHide and data[9].split("^^")[1] == "0":
            kicad_schematic.pinNamesHide = "(pin_names hide)"
        if not kicad_schematic.pinNumbersHide and data[17].split("^^")[1] == "0":
            kicad_schematic.pinNumbersHide = "(pin_numbers hide)"

        nameSize = mil2mm(float(data[16].replace("pt", "")))
        numberSize = mil2mm(float(data[24].replace("pt", "")))
    except Exception:
        nameSize = 1
        numberSize = 1

    kicad_schematic.drawing += f"""
      (pin {electrical_type} line
        (at {X} {Y} {rotation})
        (length {length})
        (name "{pinName}" (effects (font (size {nameSize} {nameSize}))))
        (number "{pinNumber}" (effects (font (size {numberSize} {numberSize}))))
      )"""


def h_T(data, translation, kicad_schematic):
    """
    Annotation handler
    """

    try:
        X = mil2mm(float(data[1]) - translation[0])
        Y = -mil2mm(float(data[2]) - translation[1])
        angle = (float(data[3]) * 10 + 1800) % 3600

        fontSize = mil2mm(float(data[6].replace("pt", "")))

        text = data[10]
        kicad_schematic.drawing += f"""
      (text
        "{text}"
        (at {X} {Y} {angle})
        (effects (font (size {fontSize} {fontSize})))
      )"""
    except Exception:
        logging.error("failed to add text to schematic")


def h_PL(data, translation, kicad_schematic):
    """
    Polygone handler
    """

    try:
        pathString = data[0].split(" ")
        polypts = []
        for i, _ in enumerate(pathString[::2]):
            polypts.append(
                f"(xy {mil2mm(float(pathString[2*i]) - translation[0])} {- mil2mm(float(pathString[2*i+1]) - translation[-1])})"
            )
        polystr = "\n          ".join(polypts)

        kicad_schematic.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""
    except Exception:
        logging.error("Schematic : failed to add a polygone")


def h_PG(data, translation, kicad_schematic):
    """
    Closed polygone handler
    """

    try:
        pathString = [i for i in data[0].split(" ") if i]
        polypts = []
        for i, _ in enumerate(pathString[::2]):
            polypts.append(
                f"(xy {mil2mm(float(pathString[2*i]) - translation[0])} {- mil2mm(float(pathString[2*i+1]) - translation[1])})"
            )
        polypts.append(polypts[0])
        polystr = "\n          ".join(polypts)

        kicad_schematic.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""
    except Exception:
        logging.error("Schematic : failed to add a polygone")


def h_PT(data, translation, kicad_schematic):
    """
    Triangle handler
    """

    try:
        data[0] = data[0].replace("M ", "").replace("L ", "").replace(" Z", "")
        h_PG(data, translation, kicad_schematic)
    except Exception:
        logging.error("Schematic : failed to add a triangle")


def h_A(data, translation, kicad_schematic):
    """
    Arc handler
    """

    from math import sqrt, acos, pi, sin, cos

    def getCenterParam(match):
        # Funciton reversed from https://easyeda.com/editor/6.5.5/js/editorPCB.min.js
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

        kicad_schematic.drawing += f"""
      (arc
        (start {Xstart} {Ystart})
        (mid {Xmid} {Ymid})
        (end {Xend} {Yend})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""
    except Exception:
        logging.error("Schematic : failed to add an arc")


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
