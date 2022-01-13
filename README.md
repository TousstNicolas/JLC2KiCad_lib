# JLC2KiCad_lib
JLC2KiCad_lib is a python script that generate a component library (schematic, footprint and 3D model) for KiCad from the JLCPCB/easyEDA library.
This script requires **Python 3.6** or higher.


## Usage 
```
positional arguments:
  JLCPCB_part_#         list of JLCPCB part # from the components you want to create

options:
  -h, --help            show this help message and exit
  -dir OUTPUT_DIR       base directory for output library files
  --model_path_relative
                        use --model_path_relative if you want the 3D model to be linked to the footprint using relative instead of absolute path, default is absolute
  --no_footprint        use --no_footprint if you do not want to create the footprint
  --no_schematic        use --no_schematic if you do not want to create the schematic
  -schematic_lib SCHEMATIC_LIB
                        set schematic library name, default is "default_lib"
  -footprint_lib FOOTPRINT_LIB
                        set footprint library name, default is "footprint"
  -logging_level LOGGING_LEVEL
                        set logging level. If DEBUG is used, the debug logs are only written in the log file if the option --log_file is set
  --log_file            use --log_file if you want logs to be written in a file
                        
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