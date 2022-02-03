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

	kicad_schematic.drawing += f"""
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

	pinNumber = data[2]
	pinName = data[13]

	X =  float(data[3]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
	Y = -float(data[4]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y

	if data[5] in ['0', '90', '180', '270']:
		rotation = (int(data[5]) + 180) % 360
	else :
		rotation = 0
		logging.warning(f'Schematic : pin number {pinNumber} : "{pinName}" failed to find orientation. Using Default orientation')

	if rotation == 0 or rotation == 180:
		length = abs(float(data[8].split('h')[-1])) * RELATIVE_OFFSET
	elif rotation == 90 or rotation == 270:
		length = abs(float(data[8].split('v')[-1])) * RELATIVE_OFFSET

	try :
		if  not kicad_schematic.pinNamesHide and data[9].split('^^')[1] == '0' :
			kicad_schematic.pinNamesHide = "(pin_names hide)"
		if  not kicad_schematic.pinNumbersHide and data[17].split('^^')[1] == '0':
			kicad_schematic.pinNumbersHide = "(pin_numbers hide)"

		nameSize   = float(data[16].replace('pt', '')) * RELATIVE_OFFSET
		numberSize = float(data[24].replace('pt', '')) * RELATIVE_OFFSET
	except :
		nameSize   = 0.6
		numberSize = 0.6

	kicad_schematic.drawing += f"""
      (pin {electrical_type} line
        (at {X} {Y} {rotation})
        (length {length})
        (name "{pinName}" (effects (font (size {nameSize} {nameSize}))))
        (number "{pinNumber}" (effects (font (size {numberSize} {numberSize}))))
      )"""

def h_T(data, kicad_schematic):
	"""
	Annotation handler
	"""

	try :
		mark = data[0]
		X =  float(data[1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_X
		Y = -float(data[2]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET_Y
		angle = (float(data[3]) * 10 + 1800) % 3600

		fontSize    = float(data[6].replace('pt', '')) * RELATIVE_OFFSET

		text = data[10]
		kicad_schematic.drawing += f"""
      (text
        "{text}"
        (at {X} {Y} {angle})
        (effects (font (size {fontSize} {fontSize})))
      )"""
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
