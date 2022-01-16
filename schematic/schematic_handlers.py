import logging

RELATIVE_OFFSET = 10
ABSOLUTE_OFFSET = 3000

def h_R(data, kicad_schematic): 
	"""
	S X1 Y1 X2 Y2 part dmg pen fill 

	Rectangle, from X1,Y1 to X2,Y2.
	"""
	
	if len(data) == 12:
		X1 = int(float(data[0])   * RELATIVE_OFFSET - ABSOLUTE_OFFSET) 	
		Y1 = - int(float(data[1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET) 	
		X2 = int(X1 + float(data[4]) * RELATIVE_OFFSET)						
		Y2 = int(Y1 - float(data[5]) * RELATIVE_OFFSET)						
	else : 
		X1 = int(float(data[0])   * RELATIVE_OFFSET - ABSOLUTE_OFFSET) 	
		Y1 = - int(float(data[1]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET) 	
		X2 = int(X1 + float(data[2]) * RELATIVE_OFFSET)			
		Y2 = int(Y1 - float(data[3]) * RELATIVE_OFFSET)			

	part = kicad_schematic.part
	dmg = "0"
	pen = "0"
	fill = "f"

	kicad_schematic.drawing += f"\nS {X1} {Y1} {X2} {Y2} {part} {dmg} {pen} {fill}"

def h_E(data, kicad_schematic):
	"""
	C X Y radius part dmg pen fill 

	Circle
	"""
	try :
		X1 = int(float(data[0]))*RELATIVE_OFFSET - ABSOLUTE_OFFSET
		Y1 = int(float(data[1]))*RELATIVE_OFFSET - ABSOLUTE_OFFSET
		radius = int(float(data[2]))
		dmg = "0"
		pen = "0"
		fill = "f"
		kicad_schematic.drawing += f"\nC {X1} {Y1} {radius} {kicad_schematic.part} {dmg} {pen} {fill}"
	except :
		logging.exception("schematic Circle ")

def h_P(data, kicad_schematic):
	"""
	Add Pin to the schematic

	X name pin X Y length orientation sizenum sizename part dmg type shape	
	
	Pin description. The pin name is not in double quotes. When a pin has no 
	name, parameter name is a “~”, but when a “~” is followed by a name, 
	the name has an overbar. The pin parameter is the pin number (it need 
	not be numeric and may be a “~”). Parameter orientation is a single letter,
	U(p), D(own), L(eft) or R(ight). The sizenum and sizename parameters 
	give the text sizes for the pin number and the pin name respectively. The 
	type is a single letter: I(nput), O(utout), B(idirectional), T(ristate), 
	P(assive), (open) C(ollector), (open) E(mitter), N(on-connected), 
	U(nspecified), or W for power input or w of power output. If the shape is 
	absent, the shape is a line, otherwise it is one of the letters I(nverted), 
	C(lock), L for input-low, V for output-low (there are more shapes...). If the 
	shape is prefixed with an “N”, the pin is invisible.

	"""
	pin_name = data[13].replace(" ", "_")
	pin_number = data[2]
	X =  int(data[3]) * RELATIVE_OFFSET - ABSOLUTE_OFFSET
	Y = -int(data[4]) * RELATIVE_OFFSET + ABSOLUTE_OFFSET
	length = 200
	if data[5] == '0':
		orientation = 'L'
		X += int(length/2)
	elif data[5] == '180':
		orientation = 'R'
		X -= int(length/2)
	elif data[5] == '90':
		orientation = 'D'
		Y += int(length/2)
	elif data[5] == '270':
		orientation = 'U'
		Y -= int(length/2)
	else :
		orientation = 'L'
		logging.warning(f'Schematic : pin number {pin_number} : "{pin_name}" failed to find orientation. Using Default orientation "Left" ')

	sizenum = "40"
	sizename = "40"
	dmg = "0"
	shape = ""

	if data[1] == '0':
		electrical_type = "U" # Unspecified
	elif data[1] == '1':
		electrical_type = "I" # Input
	elif data[1] == '2':
		electrical_type = "O" # Output
	elif data[1] == '3':
		electrical_type = "B" # Bidirectionnal
	elif data[1] == '4':
		electrical_type = "W" # Power input
	else : 
		electrical_type = "U" # Unspecified

	kicad_schematic.drawing += f"\nX {pin_name} {pin_number} {X} {Y} {length} {orientation} {sizenum} {sizename} {kicad_schematic.part} {dmg} {electrical_type} {shape}"

def h_T(data, kicad_schematic):
	"""
	T angle X Y size hidden part dmg text italic bold Halign Valign

	Text (which is not in a field). Parameter angle is in 0.1 degrees. Parameter
	hidden is 0 for visible text and 1 for hidden text. The text can be in double
	quotes, or it can be unquoted, but with the ~ character replacing spaces. 
	Parameter italic is the word “Italic” for italic text, or “Normal” for upright
	text. Parameter bold is 1 for bold and 0 for normal. Parameters Halign 
	and Valign are for the text alignment: C(entred), L(eft), R(ight), T(op) or 
	B(ottom).
	"""
	try :
		angle = int(data[3])*10 
		X = int(float(data[1]))*RELATIVE_OFFSET - ABSOLUTE_OFFSET
		Y = int(float(data[2]))*RELATIVE_OFFSET - ABSOLUTE_OFFSET
		if data[10] == "comment" or data[5] == "comment":
			size = 80
		else :
			size = int(data[5].replace('pt', ''))*10
		hidden = "0"
		part = kicad_schematic.part
		dmg = "0"
		text = data[6].replace(' ', '~')
		italic = "Normal"
		bold = "0"
		Halign = "C"
		Valign = "C"

		kicad_schematic.drawing += f"\nT {angle} {X} {Y} {size} {hidden} {part} {dmg} {text}  {italic} {bold} {Halign} {Valign}" 
	except :
		logging.exception("failed to add text to schematic")
		
def h_PL(data, kicad_schematic):
	"""
	P count part dmg pen X Y 

	fill Polygon with count vertices, and an X,Y position for each vertex. A filled 
	polygon is implicitly closed, other polygons are open.
	"""

	try :
		count = int(len(data[0].split(" "))/2)
		dmg = 0
		pen = 0
		fill = "f"
		kicad_schematic.drawing += f"\nP {count} {kicad_schematic.part} {dmg} {pen} {' '.join([str(round(float(i)*RELATIVE_OFFSET - ABSOLUTE_OFFSET)) for i in data[0].split(' ')])} {fill}"
	except :
		logging.exception("Schematic : failed to add a polygone")

def h_PG(data, kicad_schematic):
	"""
	closed polygone handler 
	"""
	
	try :
		count = int(len(data[0].split(" "))/2)
		dmg = 0
		pen = 0
		fill = 'f'
		kicad_schematic.drawing += f"\nP {count + 1} {kicad_schematic.part} {dmg} {pen} {' '.join([str(round(float(i)*RELATIVE_OFFSET - ABSOLUTE_OFFSET)) for i in data[0].split(' ') + data[0].split(' ')[:2]])} {fill}"
	except :
		logging.exception("Schematic : failed to add a polygone")

def h_A(data, kicad_schematic):
	"""
	A X Y radius start end part dmg pen fill Xstart Ystart Xend Yend

	Arc. The start and end parameters are angles in 0.1 degrees. The Xstart
	and Ystart parameters give the coordinate of the start point; it can be
	calculated from the radius and the start angle. Similarly, the Xend and
	Yend parameters give the coordinate of the end point. The arc is drawn in
	counter-clockwise direction, but the angles are swapped if there
	(normalized) difference exceeds 180 degrees
	"""

	pos = data[0].split(" ")
	Xstart = int(float(pos[1])) * RELATIVE_OFFSET * 1.2 - 2 * ABSOLUTE_OFFSET
	Ystart = int(float(pos[2])) * RELATIVE_OFFSET * 1.2 + ABSOLUTE_OFFSET 
	Xend = int(float(pos[9]))   * RELATIVE_OFFSET * 1.2 - 2 * ABSOLUTE_OFFSET
	Yend = int(float(pos[10]))  * RELATIVE_OFFSET * 1.2 + ABSOLUTE_OFFSET
	X = int((Xstart + Xend)/4) 
	Y = int((Ystart + Yend)/2) 

	radius = int((float(pos[4])/2) * RELATIVE_OFFSET * 1.2)
	start = "1800" 
	end = "0" 
	part = kicad_schematic.part 
	dmg = 0
	pen = 0

	kicad_schematic.drawing += f"\nA {X} {Y} {radius} {start} {end} {part} {dmg} {pen}"


handlers = {
	"R" : h_R, 
	"E" : h_E, 
	"P" : h_P, 
	"T" : h_T,
	"PL" : h_PL,
	"PG" : h_PG,
	"A" : h_A,
	}
