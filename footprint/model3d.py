import requests
import logging
import os 

from KicadModTree import *


def get_3Dmodel(component_uuid, footprint_info, kicad_mod, translationZ, rotation):

	logging.info("creating 3D model ...")

	lines = requests.get(f"https://easyeda.com/analyzer/api/3dmodel/{component_uuid}").content.decode().split("\n")

	vertices = []
	faces = []
	color_change = []
	vertices_counter = 0
	last_change = 0
	translationX, translationY, translationZ = 0, 0, float(translationZ)/3.048 # foot to mm 

	for line in lines :
		if len(line) > 0 and line[0] == "v":
			_,  x, y, z = line.split(" ")
			vertices.append(' '.join([str(round(float(x)/2.54,4)), str(round(float(y)/2.54,4)), str(round(float(z)/2.54,4))]))  #TODO 
			vertices_counter += 1 
		elif len(line) > 0 and line[0] == "f":
			_, x, y, z = line.split(" ")
			faces.append(', '.join([str(int(x[:-2])-1), str(int(y[:-2])-1), str(int(z[:-2])-1), "-1"]))
		elif len(line) > 0 and line[0:2] == "Kd":
			_, r, g, b = line.split(" ")
			color_change.append([vertices_counter - last_change,  str(1-float(r)), str(1-float(g)), str(1-float(b))])
			last_change = vertices_counter
		elif len(line) > 0 and line[0:2] == "Ka":
			pass
		elif len(line) > 0 and line[0:2] == "Ks":
			pass
		elif len(line) > 0 and line[0:1] == "d":
			pass
		elif len(line) > 0 and line[0:6] == "newmtl" or line[0:6] == "endmtl" or line[0:6] == "usemtl" :
			pass
		elif len(line) == 0: 
			pass
		else : 
			logging.warning("3D model handler not supported")
			logging.debug(line)

	wrl_header = f"""#VRML V2.0 utf8
#created by JLC2KiCad_lib using the JLCPCB library
#for more info see https://github.com/TousstNicolas/JLC2KICAD_lib

Group {{
	translation {translationX} {translationY} {translationZ}
	children [
		Shape {{
			appearance Appearance {{
				material Material {{
					diffuseColor 1.0 1.0 1.0
					ambientIntensity 0.2
					specularColor 0.8 0.8 0.8
					shininess 0.4
					transparency 0
				}}
			}}
			geometry IndexedFaceSet {{
				ccw TRUE
				solid FALSE
				coord DEF co Coordinate {{
					point [
						"""

	wrl_vertices2faces = """,
					]
				}
				coordIndex [
					"""

	wrl_faces2colors = """
				]
				colorPerVertex TRUE
				color Color {
					color [
"""

	wrl_footer = """				]
				}
			}
		}
	]
}"""

	wrl_color_change = ""
	for change in color_change:
		wrl_color_change += ('' + ' '.join(change[1:]) + ",\n")*change[0]

	if not os.path.exists(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}"):
		os.makedirs(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}")
	if not os.path.exists(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d"):
		os.makedirs(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d")
	
	filename = f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d/{footprint_info.footprint_name}.wrl"
	with open(filename, "w") as f:
		f.write(wrl_header)
		f.write(',\n'.join(vertices))
		f.write(wrl_vertices2faces)
		f.write(',\n'.join(faces))
		f.write(wrl_faces2colors)
		f.write(wrl_color_change)
		f.write(wrl_footer)	    

	kicad_mod.append(Model(filename = f"{os.path.dirname(__file__)}\{filename}", rotate = [-float(axis_rotation) for axis_rotation in rotation.split(',')]))
	logging.info(f"added {filename} to footprint")
