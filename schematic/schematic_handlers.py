import logging

RELATIVE_OFFSET = 0.1
ABSOLUTE_OFFSET_X = 40
ABSOLUTE_OFFSET_Y = -25

def h_R(data, kicad_schematic):
	"""
	Rectangle handler
	"""

	if len(data) == 12:
		X1 = float(data[0])
		Y1 = float(data[1])
		X2 = float(X1) + float(data[4])
		Y2 = float(Y1) + float(data[5])
	else :
		X1 = float(data[0])
		Y1 = float(data[1])
		X2 = float(X1) + float(data[2])
		Y2 = float(Y1) + float(data[3])

	X1 *=  RELATIVE_OFFSET
	Y1 *= -RELATIVE_OFFSET
	X2 *=  RELATIVE_OFFSET
	Y2 *= -RELATIVE_OFFSET

	X1 -= ABSOLUTE_OFFSET_X
	Y1 -= ABSOLUTE_OFFSET_Y
	X2 -= ABSOLUTE_OFFSET_X
	Y2 -= ABSOLUTE_OFFSET_Y

	kicad_schematic.drawing += f"""\
      (rectangle
        (start {X1} {Y1})
        (end {X2} {Y2})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""

def h_E(data, kicad_schematic):
	"""
	Circle
	"""

	try :
		X1 = 	 float(data[0]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
		Y1 = 	-float(data[1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y
		radius = float(data[2]) * RELATIVE_OFFSET
		kicad_schematic.drawing += f"""
      (circle
        (center {X1} {Y1})
        (radius {radius})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""
	except :
		logging.exception("schematic : failed to add circle")

def h_P(data, kicad_schematic):
	"""
	Add Pin to the schematic
	"""

	if data[1] == '0':
		electrical_type = "unspecified"
	elif data[1] == '1':
		electrical_type = "input"
	elif data[1] == '2':
		electrical_type = "output"
	elif data[1] == '3':
		electrical_type = "bidirectional"
	elif data[1] == '4':
		electrical_type = "power_in"
	else :
		electrical_type = "unspecified"

	pin_number = data[2]
	pin_name = data[13]

	X =  float(data[3]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
	Y = -float(data[4]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y

	if data[5] in ['0', '90', '180', '270']:
		rotation = (int(data[5]) + 180) % 360
	else :
		rotation = 0
		logging.warning(f'Schematic : pin number {pin_number} : "{pin_name}" failed to find orientation. Using Default orientation')

	if rotation == 0 or rotation == 180:
		length = abs(float(data[8].split('h')[-1])) * RELATIVE_OFFSET
	elif rotation == 90 or rotation == 270:
		length = abs(float(data[8].split('v')[-1])) * RELATIVE_OFFSET

	# nameVisible = True if data[9].split('^^')[1] == '1' else False
	# numberVisible = True if data[15].split('^^')[1] == '1' else False
	# Visible3 = True if data[21].split('^^')[1] == '1' else False
	# Visible4 = True if data[23].split('^^')[1] == '1' else False


	kicad_schematic.drawing += f"""
      (pin {electrical_type} line
        (at {X} {Y} {rotation})
        (length {length})
        (name "{pin_name}" (effects (font (size 0.612 0.612))))
        (number "{pin_number}" (effects (font (size 0.612 0.612))))
      )"""

def h_T(data, kicad_schematic):
	"""
	Annotation handler
	"""

	try :
		logging.warning("Annotation handler not yet implemented")
		X = float(data[1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
		Y = float(data[2]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y
		angle = float(data[3])*10

		text = data[6]

		fontSize    = data[6]
		fontWeight = data[7]

	# 	if data[10] == "comment" or data[5] == "comment":
	# 		size = 80
	# 	else :
	# 		size = float(data[5].replace('pt', ''))*10


	# 	kicad_schematic.drawing += f"""
    #   (text
    #     "{text}"
    #     (at {X} {Y} {angle})
    #     (effects
    #       (font
    #         (size {fontSize} {fontWeight})
    #         [(thickness THICKNESS)]
    #         [bold]
    #         [italic]
    #       )
    #       [(justify [left | right] [top | bottom] [mirror])]
    #       [hide]
    #     )
    #   )"""
	except :
		logging.exception("failed to add text to schematic")

def h_PL(data, kicad_schematic):
	"""
	Polygone handler
	"""

	try :
		pathString = data[0].split(' ')
		polypts = []
		for i, _ in enumerate(pathString[::2]):
			polypts.append(f"(xy {float(pathString[2*i]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X} {-float(pathString[2*i+1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y})")
		polystr = '\n          '.join(polypts)

		kicad_schematic.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""
	except :
		logging.exception("Schematic : failed to add a polygone")

def h_PG(data, kicad_schematic):
	"""
	Closed polygone handler
	"""

	try :
		pathString = data[0].split(' ')
		polypts = []
		for i, _ in enumerate(pathString[::2]):
			polypts.append(f"(xy {float(pathString[2*i]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X} {-float(pathString[2*i+1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y})")
		polypts.append(polypts[0])
		polystr = '\n          '.join(polypts)

		kicad_schematic.drawing += f"""
      (polyline
        (pts
          {polystr}
        )
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type background))
      )"""
	except :
		logging.exception("Schematic : failed to add a polygone")

def h_PT(data, kicad_schematic):
	"""
	Triangle handler
	"""

	data[0] = data[0].replace('M ', '').replace('L ', '').replace(' Z ', '')
	h_PG(data, kicad_schematic)

def h_A(data, kicad_schematic):
	"""
	Arc handler
	"""

	pathString = data[0].split(" ")
	Xstart 	= float(pathString[1])  * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
	Ystart 	= float(pathString[2])  * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y
	radius  = float(pathString[4])  * RELATIVE_OFFSET
	Xend 	= float(pathString[9])  * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
	Yend 	= float(pathString[10]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y

	Xmid = (Xstart + Xend) / 2
	Ymid = (Ystart + Yend) / 2 + radius

	kicad_schematic.drawing += f"""
      (arc
        (start {Xstart} {Ystart})
        (mid {Xmid} {Ymid})
        (end {Xend} {Yend})
        (stroke (width 0) (type default) (color 0 0 0 0))
        (fill (type none))
      )"""

handlers = {
	"R" : h_R,
	"E" : h_E,
	"P" : h_P,
	"T" : h_T,
	"PL" : h_PL,
	"PG" : h_PG,
	"PT" : h_PT,
	"A" : h_A,
	# "J" : h_NotYetImplemented,
	# "N" : h_NotYetImplemented,
	# "BE" : h_NotYetImplemented,
	# "AR" : h_NotYetImplemented,
	# "O" : h_NotYetImplemented,
	}
