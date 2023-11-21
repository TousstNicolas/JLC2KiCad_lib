import requests
import logging
import os
import re
from KicadModTree import *

wrl_header = """#VRML V2.0 utf8
#created by JLC2KiCad_lib using the JLCPCB library
#for more info see https://github.com/TousstNicolas/JLC2KICAD_lib
"""


def get_StepModel(component_uuid, footprint_info, kicad_mod):
    logging.info(f"Downloading STEP Model ...")

    # `qAxj6KHrDKw4blvCG8QJPs7Y` is a constant in
    # https://modules.lceda.cn/smt-gl-engine/0.8.22.6032922c/smt-gl-engine.js
    # and points to the bucket containing the step files.

    response = requests.get(
        f"https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{component_uuid}"
    )
    if response.status_code == requests.codes.ok:
        ensure_footprint_lib_directories_exist(footprint_info)
        filename = f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/{footprint_info.model_dir}/{footprint_info.footprint_name}.step"
        with open(filename, "wb") as f:
            f.write(response.content)

        logging.info(f"STEP model created at {filename}")

        if footprint_info.model_base_variable:
            if footprint_info.model_base_variable.startswith("$"):
                path_name = f'"{footprint_info.model_base_variable}/{footprint_info.footprint_name}.step"'
            else:
                path_name = f'"$({footprint_info.model_base_variable})/{footprint_info.footprint_name}.step"'
        else:
            path_name = filename

        kicad_mod.append(
            Model(
                filename=path_name,
            )
        )
        logging.info(f"added {path_name} to footprint")

    else:
        logging.error("request error, no Step model found")
        return


def get_WrlModel(
    component_uuid,
    footprint_info,
    kicad_mod,
    translationX,
    translationY,
    translationZ,
    rotation,
):
    logging.info("Creating WRL model ...")

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

    # find the lowest point of the model
    lowest_point = 0
    for point in vertices:
        if float(point.split(" ")[2]) < lowest_point:
            lowest_point = float(point.split(" ")[2])

    # convert lowest point to mm
    min_z = lowest_point * 2.54

    # calculate the translation Z value
    from .footprint_handlers import mil2mm

    Zmm = mil2mm(translationZ)
    translation_z = Zmm - min_z

    # find the x and y middle of the model
    x_list = []
    y_list = []
    for point in vertices:
        x_list.append(float(point.split(" ")[0]))
        y_list.append(float(point.split(" ")[1]))
    x_middle = (max(x_list) + min(x_list)) / 2
    y_middle = (max(y_list) + min(y_list)) / 2

    ensure_footprint_lib_directories_exist(footprint_info)

    filename = f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/{footprint_info.model_dir}/{footprint_info.footprint_name}.wrl"
    with open(filename, "w") as f:
        f.write(wrl_content)

    if footprint_info.model_base_variable:
        if footprint_info.model_base_variable.startswith("$"):
            path_name = f'"{footprint_info.model_base_variable}/{footprint_info.footprint_name}.wrl"'
        else:
            path_name = f'"$({footprint_info.model_base_variable})/{footprint_info.footprint_name}.wrl"'
    else:
        dirname = os.getcwd().replace("\\", "/").replace("/footprint", "")
        if os.path.isabs(filename):
            path_name = filename
        else:
            path_name = f"{dirname}/{filename}"

        # Calculate the translation between the center of the pads and the center of the whole footprint
    translation_x = translationX - footprint_info.origin[0]
    translation_y = translationY - footprint_info.origin[1]

    # Convert to inches
    translation_x_inches = translation_x / 100 + x_middle / 10
    translation_y_inches = -translation_y / 100 - y_middle / 10
    translation_z_inches = translation_z / 25.4

    # Check if a model has already been added to the footprint to prevent duplicates
    if any(isinstance(child, Model) for child in kicad_mod.getAllChilds()):
        logging.info(f"WRL model created at {filename}")
        logging.info(
            f"WRL model was not added to the footprint to prevent duplicates with STEP model"
        )
    else:
        kicad_mod.append(
            Model(
                filename=path_name,
                at=[translation_x_inches, translation_y_inches, translation_z_inches],
                rotate=[-float(axis_rotation) for axis_rotation in rotation.split(",")],
            )
        )
        logging.info(f"added {path_name} to footprintc")


def ensure_footprint_lib_directories_exist(footprint_info):
    if not os.path.exists(
        f"{footprint_info.output_dir}/{footprint_info.footprint_lib}"
    ):
        os.makedirs(f"{footprint_info.output_dir}/{footprint_info.footprint_lib}")

    if not os.path.exists(
        f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/{footprint_info.model_dir}"
    ):
        os.makedirs(
            f"{footprint_info.output_dir}/{footprint_info.footprint_lib}/{footprint_info.model_dir}"
        )
