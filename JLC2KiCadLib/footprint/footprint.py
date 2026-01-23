import json
import logging
import os
from dataclasses import dataclass

import requests
from KicadModTree import Footprint, KicadFileHandler, Pad, Text, Translation

from .footprint_handlers import handlers, mil2mm


@dataclass
class FootprintInfo:
    max_X: float = -10000
    max_Y: float = -10000
    min_X: float = 10000
    min_Y: float = 10000
    footprint_name: str = ""
    output_dir: str = ""
    footprint_lib: str = ""
    model_base_variable: str = ""
    model_dir: str = ""
    origin: tuple = (0, 0)
    models: str = ""


def create_footprint(
    footprint_component_uuid,
    component_id,
    footprint_lib,
    output_dir,
    model_base_variable,
    model_dir,
    skip_existing,
    models,
):
    logging.info("Creating footprint ...")

    (
        footprint_name,
        datasheet_link,
        footprint_shape,
        translation,
    ) = get_footprint_info(footprint_component_uuid)

    if skip_existing and os.path.isfile(
        os.path.join(output_dir, footprint_lib, footprint_name + ".kicad_mod")
    ):
        logging.info(f"Footprint {footprint_name} already exists, skipping.")
        return f"{footprint_lib}:{footprint_name}", datasheet_link

    # init kicad footprint
    kicad_mod = Footprint(f'"{footprint_name}"')
    kicad_mod.setDescription(f"{footprint_name} footprint")  # TODO Set real description
    kicad_mod.setTags(f"{footprint_name} footprint {component_id}")

    footprint_info = FootprintInfo(
        footprint_name=footprint_name,
        output_dir=output_dir,
        footprint_lib=footprint_lib,
        model_base_variable=model_base_variable,
        model_dir=model_dir,
        origin=translation,
        models=models,
    )

    # for each line in data : use the appropriate handler
    for line in footprint_shape:
        args = [i for i in line.split("~")]  # split and remove empty string in list
        model = args[0]
        logging.debug(args)
        if model not in handlers:
            logging.warning(f"footprint : model not in handler :  {model}")
        else:
            handlers.get(model)(args[1:], kicad_mod, footprint_info)

    if any(
        isinstance(child, Pad) and child.type == Pad.TYPE_THT
        for child in kicad_mod.getAllChilds()
    ):
        kicad_mod.setAttribute("through_hole")
    else:
        kicad_mod.setAttribute("smd")

    kicad_mod.insert(Translation(-mil2mm(translation[0]), -mil2mm(translation[1])))

    # Translate the footprint max and min values to the origin
    footprint_info.max_X -= mil2mm(translation[0])
    footprint_info.max_Y -= mil2mm(translation[1])
    footprint_info.min_X -= mil2mm(translation[0])
    footprint_info.min_Y -= mil2mm(translation[1])

    # set general values
    kicad_mod.append(
        Text(
            type="reference",
            text="REF**",
            at=[
                (footprint_info.min_X + footprint_info.max_X) / 2,
                footprint_info.min_Y - 2,
            ],
            layer="F.SilkS",
        )
    )
    kicad_mod.append(
        Text(
            type="user",
            text="${REFERENCE}",
            at=[
                (footprint_info.min_X + footprint_info.max_X) / 2,
                (footprint_info.min_Y + footprint_info.max_Y) / 2,
            ],
            layer="F.Fab",
        )
    )
    kicad_mod.append(
        Text(
            type="value",
            text=footprint_name,
            at=[
                (footprint_info.min_X + footprint_info.max_X) / 2,
                footprint_info.max_Y + 2,
            ],
            layer="F.Fab",
        )
    )

    if not os.path.exists(f"{output_dir}/{footprint_lib}"):
        os.makedirs(f"{output_dir}/{footprint_lib}")

    # output kicad model
    file_handler = KicadFileHandler(kicad_mod)
    file_handler.writeFile(f"{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod")
    logging.info(f"Created '{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod'")

    # return the datasheet link and footprint name to be linked with the symbol
    return (f"{footprint_lib}:{footprint_name}", datasheet_link)


def get_footprint_info(footprint_component_uuid):
    # fetch the component data from easyeda library
    response = requests.get(
        f"https://easyeda.com/api/components/{footprint_component_uuid}"
    )

    if response.status_code == requests.codes.ok:
        data = json.loads(response.content.decode())
    else:
        logging.error(
            "create_footprint error. Requests returned with error code "
            f"{response.status_code}"
        )
        return ("", None, "", (0, 0))

    footprint_shape = data["result"]["dataStr"]["shape"]
    x = data["result"]["dataStr"]["head"]["x"]
    y = data["result"]["dataStr"]["head"]["y"]
    try:
        datasheet_link = data["result"]["dataStr"]["head"]["c_para"]["link"]
    except KeyError:
        datasheet_link = ""
        logging.warning("Could not retrieve datasheet link from EASYEDA")

    footprint_name = (
        data["result"]["title"]
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "_")
        .replace(")", "_")
    )

    if not footprint_name:
        footprint_name = "NoName"
        logging.warning(
            "Could not retrieve components information from EASYEDA, default name "
            "'NoName'."
        )

    return (footprint_name, datasheet_link, footprint_shape, (x, y))
