import requests
import json
import logging
import os

from KicadModTree import *
from .footprint_handlers import *


def create_footprint(
    footprint_component_uuid,
    component_id,
    footprint_lib,
    output_dir,
    model_path_relative,
):
    logging.info("creating footprint ...")

    footprint_name, datasheet_link, footprint_shape = get_footprint_info(
        footprint_component_uuid
    )

    # init kicad footprint
    kicad_mod = Footprint(f'"{footprint_name}"')
    kicad_mod.setDescription(f"{footprint_name} footprint")  # TODO Set real description
    kicad_mod.setTags(f"{footprint_name} footprint")

    class footprint_info:
        def __init__(self, footprint_name, output_dir, footprint_lib):
            self.max_X, self.max_Y, self.min_X, self.min_Y = (
                -10000,
                -10000,
                10000,
                10000,
            )  # I will be using these to calculate the bounding box because the node.calculateBoundingBox() method does not seems to work for me
            self.footprint_name = footprint_name
            self.output_dir = output_dir
            self.footprint_lib = footprint_lib
            self.model_path_relative = model_path_relative

    footprint_info = footprint_info(
        footprint_name=footprint_name,
        output_dir=output_dir,
        footprint_lib=footprint_lib,
    )

    # for each line in data : use the appropriate handler
    for line in footprint_shape:
        args = [
            i for i in line.split("~") if i
        ]  # split and remove empty string in list
        model = args[0]
        logging.debug(args)
        if model not in handlers:
            logging.warning(f"footprint : model not in handler :  {model}")
        else:
            handlers.get(model)(args[1:], kicad_mod, footprint_info)

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
            text="REF**",
            at=[
                (footprint_info.min_X + footprint_info.max_X) / 2,
                footprint_info.max_Y + 4,
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

    # translate the footprint to be centered around 0,0
    kicad_mod.insert(
        Translation(
            -(footprint_info.min_X + footprint_info.max_X) / 2,
            -(footprint_info.min_Y + footprint_info.max_Y) / 2,
        )
    )

    if not os.path.exists(f"{output_dir}/{footprint_lib}"):
        os.makedirs(f"{output_dir}/{footprint_lib}")

    # output kicad model
    file_handler = KicadFileHandler(kicad_mod)
    file_handler.writeFile(f"{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod")
    logging.info(f"created '{output_dir}/{footprint_lib}/{footprint_name}.kicad_mod'")

    # return and datasheet link footprint name to be linked with the schematic
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
            f"create_footprint error. Requests returned with error code {response.status_code}"
        )
        return ()

    footprint_shape = data["result"]["dataStr"]["shape"]
    datasheet_link = data["result"]["dataStr"]["head"]["c_para"]["link"]
    footprint_name = (
        data["result"]["title"]
        .replace(" ", "_")
        .replace("/", "_")
        .replace("(", "_")
        .replace("(", "_")
    )

    if not footprint_name:
        footprint_name = "NoName"
        logging.warning(
            "Could not retrieve components information from EASYEDA, default name 'NoName'."
        )
    if not datasheet_link:
        datasheet_link = ""
        logging.warning("Could not retrieve datasheet link from EASYEDA")

    return (footprint_name, datasheet_link, footprint_shape)
