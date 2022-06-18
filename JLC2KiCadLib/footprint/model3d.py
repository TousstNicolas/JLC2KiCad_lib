import requests
import logging
import os
import re
from KicadModTree import *

wrl_header = """#VRML V2.0 utf8
#created by JLC2KiCad_lib using the JLCPCB library
#for more info see https://github.com/TousstNicolas/JLC2KICAD_lib
"""


def get_3Dmodel(component_uuid, footprint_info, kicad_mod, translationZ, rotation):
    logging.info("creating 3D model ...")

    response = requests.get(
        f"https://easyeda.com/analyzer/api/3dmodel/{component_uuid}"
    )
    if response.status_code == requests.codes.ok:
        text = response.content.decode()
    else:
        logging.error("request error, no 3D model found")
        return ()

    """
	translationX, translationY, translationZ = (
		0,
		0,
		float(translationZ) / 3.048,
	)  # foot to mm
	"""

    wrl_content = wrl_header

    # get material list
    pattern = "newmtl .*?endmtl"
    matchs = re.findall(pattern=pattern, string=text, flags=re.DOTALL)

    materials = {}
    for match in matchs:
        material = {}
        material_id = ""
        for value in match.split("\n"):
            if value[0:6] == "newmtl":
                material_id = value.split(" ")[1]
            elif value[0:2] == "Ka":
                material["ambientColor"] = value.split(" ")[1:]
            elif value[0:2] == "Kd":
                material["diffuseColor"] = value.split(" ")[1:]
            elif value[0:2] == "Ks":
                material["specularColor"] = value.split(" ")[1:]
            elif value[0] == "d":
                material["transparency"] = value.split(" ")[1]

        materials[material_id] = material

    # get vertices list
    pattern = "v (.*?)\n"
    matchs = re.findall(pattern=pattern, string=text, flags=re.DOTALL)

    vertices = []
    for vertice in matchs:
        vertices.append(
            " ".join(
                [str(round(float(coord) / 2.54, 4)) for coord in vertice.split(" ")]
            )
        )

    # get shape list
    shapes = text.split("usemtl")[1:]
    for shape in shapes:
        lines = shape.split("\n")
        material = materials[lines[0].replace(" ", "")]
        index_counter = 0
        link_dict = {}
        coordIndex = []
        points = []
        for line in lines[1:]:
            if len(line) > 0:
                face = [int(index) for index in line.replace("//", "").split(" ")[1:]]
                face_index = []
                for index in face:
                    if index not in link_dict:
                        link_dict[index] = index_counter
                        face_index.append(str(index_counter))
                        points.append(vertices[index - 1])
                        index_counter += 1
                    else:
                        face_index.append(str(link_dict[index]))
                face_index.append("-1")
                coordIndex.append(",".join(face_index) + ",")
        points.insert(-1, points[-1])

        shape_str = f"""
Shape{{
	appearance Appearance {{
		material  Material 	{{ 
			diffuseColor {' '.join(material['diffuseColor'])} 
			specularColor {' '.join(material['specularColor'])}
			ambientIntensity 0.2
			transparency {material['transparency']}
			shininess 0.5
		}}
	}}
	geometry IndexedFaceSet {{
		ccw TRUE 
		solid FALSE
		coord DEF co Coordinate {{
			point [
				{(", ").join(points)}
			]
		}}
		coordIndex [
			{"".join(coordIndex)}
		]
	}}
}}"""

        wrl_content += shape_str

    if not os.path.exists(
        f"{footprint_info.output_dir}/{footprint_info.footprint_lib}"
    ):
        os.makedirs(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}")
    if not os.path.exists(
        f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d"
    ):
        os.makedirs(
            f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d"
        )

    filename = f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/packages3d/{footprint_info.footprint_name}.wrl"
    with open(filename, "w") as f:
        f.write(wrl_content)

    if footprint_info.model_path_relative:
        dirname = ""
    else:
        dirname = os.getcwd().replace("\\", "/").replace("/footprint", "") + "/"

    kicad_mod.append(
        Model(
            filename=f"{dirname}{filename}",
            rotate=[-float(axis_rotation) for axis_rotation in rotation.split(",")],
        )
    )
    logging.info(f"added {filename} to footprint")
