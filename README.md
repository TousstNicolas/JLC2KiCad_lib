# JLC2KiCad_lib
JLC2KiCad_lib is a python script that generate a component library (schematic, footprint and 3D model) for KiCad from the JLCPCB/easyEDA library.
This script requires **Python 3.6** or higher.


## Usage 
```
JLC2KiCad_lib.py [-h] [-dir OUTPUT_DIR] [--no_footprint] [--no_schematic] [-schematic_lib SCHEMATIC_LIB]
                        [-footprint_lib FOOTPRINT_LIB] [-logging_level LOGGING_LEVEL] [--log_file]
                        JLCPCB_part_# [JLCPCB_part_# ...]
```

example usage : `python3 JLC2KiCad_lib.py C1337258 C24112 -dir My_lib -schematic_lib My_Schematic_lib --no_footprint`

This example will create the schematic for the two component specified, and will output the schematic in the `./My_lib/Schematic/My_Schematic_lib.lib` file.
The `--no_footprint` is used to disable the footprint generation.

The JLCPCB part # is found in the part info section of every component is the JLCPCB part library. 

## Dependencies 
This script relies on KicadModTree framework for the footprints generation. 
You can use `pip install KicadModTree==1.1.2` to install it using pip.

## Notes
* Even so I tested the script on a lot of components, be careful and always check the output footprint.
* The schematic generation still has some issues for components with complex geometries, but the pin should be correctly mapped.

## License 
Copyright © 2021 TousstNicolas 

The code is released under the MIT license