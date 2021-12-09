import requests 
import json
import re
import os
import logging

from KicadModTree import *
from schematic.schematic_handlers import *


template_lib_header = """\
EESchema-LIBRARY Version 2.4 \n# encoding utf-8
# created by JLC2KiCad_lib using the JLCPCB library
# for more info see https://github.com/TousstNicolas/JLC2KICAD_lib"""

template_lib_footer = \
"""
#
# End Library
"""
	

def create_schematic(schematic_component_uuid, footprint_name, datasheet_link, library_name, output_dir):

	class kicad_schematic():
		drawing = ""
		part = 0
	kicad_schematic = kicad_schematic()


	for component_uuid in schematic_component_uuid:

		kicad_schematic.part += 1

		data = json.loads(requests.get(f"https://easyeda.com/api/components/{component_uuid}").content.decode())
		schematic_shape = data["result"]["dataStr"]["shape"]
		symmbolic_prefix = data["result"]["packageDetail"]["dataStr"]["head"]["c_para"]["pre"].replace("?", "")
		
		refname_y = 50		#TODO
		compname_y = -100 	#TODO

		component_title = data["result"]["title"].replace("/", "_")
		filename = f"{output_dir}/Schematic/" + library_name + ".lib"
		
		logging.info(f"creating schematic {component_title} in {library_name}")

		for line in schematic_shape :
			args = [i for i in line.split("~") if i] # split and remove empty string in list
			model = args[0]
			logging.debug(args)
			if model not in handlers:
				logging.warning("Schematic : parsing model not in handler : " + model)
			else :
				handlers.get(model)(args[1:], kicad_schematic)

	template_lib_component = \
f"""
#
# {component_title}
#
DEF {component_title} {symmbolic_prefix} 0 40 Y Y {kicad_schematic.part} F N
F0 "{symmbolic_prefix}" 0 {refname_y} 50 H V C C N N
F1 "{component_title}" 0 {compname_y} 50 H V C C N N
F2 "{footprint_name}" 0 -400 50 H I C CIN
F3 "{datasheet_link}" -90 5 50 H I L CNN
DRAW\
{kicad_schematic.drawing}
ENDDRAW
ENDDEF"""
	
	if not os.path.exists(f"{output_dir}/Schematic"):
		os.makedirs(f"{output_dir}/Schematic")

	if os.path.exists(filename):
		update_library(library_name, component_title, template_lib_component, output_dir)
	else :
		with open(filename, "w") as f:	
			logging.info(f"writing in {filename} file")
			f.write(template_lib_header)
			f.write(template_lib_footer)
		update_library(library_name, component_title, template_lib_component, output_dir)
		


def update_library(library_name, component_title, template_lib_component, output_dir):
	"""
	if component is already in library,
	the library will be updated,
	if not already present in library,
	the component will be added at the beginning  
	"""
	
	with open(f"{output_dir}/Schematic/{library_name}.lib", 'rb+') as lib_file:
		pattern = f".#.# {component_title}.*?ENDDEF"
		file_content = lib_file.read().decode()

		# if component already in library, update the library,
		# if not, append at the end of the library
		if f"DEF {component_title}" in file_content:
			# use regex to find the old component template in the file and replace it with the new one 
			logging.info(f'found component in {library_name}, updating {library_name}')
			sub = re.sub(pattern= pattern, repl= template_lib_component, string= file_content, flags = re.DOTALL, count= 1)
			lib_file.seek(0)
			# delete the file content and rewrite it 
			lib_file.truncate()
			lib_file.write(sub.encode())
		else : 
			# move before the library footer and write the component template 
			lib_file.seek(-len(template_lib_footer),2)
			lib_file.truncate()
			lib_file.write(template_lib_component.encode())
			lib_file.write(template_lib_footer.encode())
		