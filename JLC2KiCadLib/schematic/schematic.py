import requests
import json
import re
import os
import logging

from KicadModTree import *
from .schematic_handlers import *


template_lib_header = f"""\
(kicad_symbol_lib (version 20210201) (generator TousstNicolas/JLC2KiCad_lib)
"""

template_lib_footer = """
)"""


def create_schematic(
    schematic_component_uuid,
    footprint_name,
    datasheet_link,
    library_name,
    output_dir,
    component_id,
):
    class kicad_schematic:
        drawing = ""
        pinNamesHide = ""
        pinNumbersHide = ""

    kicad_schematic = kicad_schematic()

    ComponentName = ""
    for component_uuid in schematic_component_uuid:

        response = requests.get(f"https://easyeda.com/api/components/{component_uuid}")
        if response.status_code == requests.codes.ok:
            data = json.loads(response.content.decode())
        else:
            logging.error(
                f"create_schematic error. Requests returned with error code {response.status_code}"
            )
            return ()

        schematic_shape = data["result"]["dataStr"]["shape"]
        symmbolic_prefix = data["result"]["packageDetail"]["dataStr"]["head"]["c_para"][
            "pre"
        ].replace("?", "")
        component_title = (
            data["result"]["title"]
            .replace("/", "_")
            .replace(" ", "_")
            .replace(".", "_")
        )

        if not ComponentName:
            ComponentName = component_title
            component_title += "_0"
        if (
            len(schematic_component_uuid) >= 2
            and component_uuid == schematic_component_uuid[0]
        ):
            continue

        filename = f"{output_dir}/Schematic/" + library_name + ".kicad_sym"

        logging.info(f"creating schematic {component_title} in {library_name}")

        kicad_schematic.drawing += f'''\n    (symbol "{component_title}_0"'''
        for line in schematic_shape:
            args = [
                i for i in line.split("~") if i
            ]  # split and remove empty string in list
            model = args[0]
            logging.debug(args)
            if model not in handlers:
                logging.warning("Schematic : parsing model not in handler : " + model)
            else:
                handlers.get(model)(args[1:], kicad_schematic)
        kicad_schematic.drawing += """\n    )"""

    template_lib_component = f"""\
  (symbol "{ComponentName}" {kicad_schematic.pinNamesHide} {kicad_schematic.pinNumbersHide} (in_bom yes) (on_board yes)
    (property "Reference" "{symmbolic_prefix}" (id 0) (at 0 1.27 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Value" "{ComponentName}" (id 1) (at 0 -2.54 0)
      (effects (font (size 1.27 1.27)))
    )
    (property "Footprint" "{footprint_name}" (id 2) (at 0 -10.16 0)
      (effects (font (size 1.27 1.27) italic) hide)
    )
    (property "Datasheet" "{datasheet_link}" (id 3) (at -2.286 0.127 0)
      (effects (font (size 1.27 1.27)) (justify left) hide)
    )
    (property "ki_keywords" "{component_id}" (id 6) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    )
    (property "LCSC" "{component_id}" (id 4) (at 0 0 0)
      (effects (font (size 1.27 1.27)) hide)
    ){kicad_schematic.drawing}
  )"""

    if not os.path.exists(f"{output_dir}/Schematic"):
        os.makedirs(f"{output_dir}/Schematic")

    if os.path.exists(filename):
        update_library(library_name, ComponentName, template_lib_component, output_dir)
    else:
        with open(filename, "w") as f:
            logging.info(f"writing in {filename} file")
            f.write(template_lib_header)
            f.write(template_lib_footer)
        update_library(library_name, ComponentName, template_lib_component, output_dir)


def update_library(library_name, component_title, template_lib_component, output_dir):
    """
    if component is already in library,
    the library will be updated,
    if not already present in library,
    the component will be added at the beginning
    """

    with open(f"{output_dir}/Schematic/{library_name}.kicad_sym", "rb+") as lib_file:
        pattern = f'  \(symbol "{component_title}" \(pin_names (\n|.)*?\n  \)'
        file_content = lib_file.read().decode()

        if f'symbol "{component_title}" (pin_names' in file_content:
            # use regex to find the old component template in the file and replace it with the new one
            logging.info(
                f"found component already in {library_name}, updating {library_name}"
            )
            sub = re.sub(
                pattern=pattern,
                repl=template_lib_component,
                string=file_content,
                flags=re.DOTALL,
                count=1,
            )
            lib_file.seek(0)
            # delete the file content and rewrite it
            lib_file.truncate()
            lib_file.write(sub.encode())
        else:
            # move before the library footer and write the component template
            lib_file.seek(-len(template_lib_footer), 2)
            lib_file.truncate()
            lib_file.write(template_lib_component.encode())
            lib_file.write(template_lib_footer.encode())
