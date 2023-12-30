# JLC2KiCadLib

<p style="text-align: center;">

[![PyPI version](https://badge.fury.io/py/JLC2KiCadLib.svg)](https://badge.fury.io/py/JLC2KiCadLib)
![Python versions](https://img.shields.io/pypi/pyversions/JLC2KiCadLib.svg)
[![Downloads](https://pepy.tech/badge/jlc2kicadlib)](https://pepy.tech/project/jlc2kicadlib)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

</p>

JLC2KiCadLib is a python script that generate a component library (symbol, footprint and 3D model) for KiCad from the JLCPCB/easyEDA library.
This script requires **Python 3.6** or higher.

## Example 



easyEDA origin | KiCad result
---- | ----
![JLCSymbol](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/JLC_Symbol_1.png) | ![KiCadSymbol](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/KiCad_Symbol_1.png)
![JLCFootprint](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/JLC_Footprint_1.png) | ![KiCadFootprint](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/KiCad_Footprint_1.png)
![JLC3Dmodel](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/JLC_3Dmodel.png) | ![KiCad3Dmodel](https://raw.githubusercontent.com/TousstNicolas/JLC2KiCad_lib/master/images/KiCad_3Dmodel.png)

## Installation

Install using pip: 

```
pip install JLC2KiCadLib
```

Install from source:

```
git clone https://github.com/TousstNicolas/JLC2KiCad_lib.git
cd JLC2KiCad_lib 
pip install . 
```

## Usage 

```
usage: JLC2KiCadLib [-h] [-dir OUTPUT_DIR] [--no_footprint] [--no_symbol] [-symbol_lib SYMBOL_LIB] [-footprint_lib FOOTPRINT_LIB]
                    [-models [{STEP,WRL} ...]] [--skip_existing] [-model_base_variable MODEL_BASE_VARIABLE]
                    [-logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}] [--log_file] [--version]
                    JLCPCB_part_# [JLCPCB_part_# ...]

take a JLCPCB part # and create the according component's kicad's library

positional arguments:
  JLCPCB_part_#         list of JLCPCB part # from the components you want to create

options:
  -h, --help            show this help message and exit
  -dir OUTPUT_DIR       base directory for output library files
  --no_footprint        use --no_footprint if you do not want to create the footprint
  --no_symbol           use --no_symbol if you do not want to create the symbol
  -symbol_lib SYMBOL_LIB
                        set symbol library name, default is "default_lib"
  -symbol_lib_dir SYMBOL_LIB_DIR
                        Set symbol library path, default is "symbol" (relative to OUTPUT_DIR)
  -footprint_lib FOOTPRINT_LIB
                        set footprint library name, default is "footprint"
  -models [{STEP,WRL} ...]
                        Select the 3D model you want to use. Default is STEP. 
                        If both are selected, only the STEP model will be added to the footprint (the WRL model will still be generated alongside the STEP model). 
                        If you do not want any model to be generated, use the --models without arguments
  -model_dir MODEL_DIR  Set directory for storing 3d models, default is "packages3d" (relative to FOOTPRINT_LIB)
  --skip_existing       use --skip_existing if you want do not want to replace already existing footprints and symbols
  -model_base_variable MODEL_BASE_VARIABLE
                        use -model_base_variable if you want to specify the base path of the 3D model using a path variable
  -logging_level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        set logging level. If DEBUG is used, the debug logs are only written in the log file if the option --log_file is set
  --log_file            use --log_file if you want logs to be written in a file
  --version             Print versin number and exit

exemple use : 
        JLC2KiCadLib C1337258 C24112 -dir My_lib -symbol_lib My_Symbol_lib --no_footprint
```

The only required arguments are the JLCPCP_part number (e.g. Cxxxxx)

Example usage : 
```
JLC2KiCadLib C1337258 C24112 -dir My_lib                       \
                             -model_dir My_model_dir           \
                             -footprint_lib My_footprint_lib   \
                             -symbol_lib_dir My_symbol_lib_dir \
                             -symbol_lib My_symbol_lib
```

This example will create the symbol, footprint and 3D model for the two components specified and will output the symbol in the `./My_lib/symbol/My_symbol_lib.lib` file, the footprint and 3D model will be created in the `./My_lib/Footprint`. This will result in the following tree to be created : 

```
My_lib
├── My_footprint_lib
│   ├── My_model_dir
│   │   ├── QFN-24_L4.0-W4.0-P0.50-BL-EP2.7.step
│   │   └── VQFN-48_L7.0-W7.0-P0.50-BL-EP5.5.step
│   ├── QFN-24_L4.0-W4.0-P0.50-BL-EP2.7.kicad_mod
│   └── VQFN-48_L7.0-W7.0-P0.50-BL-EP5.5.kicad_mod
└── My_symbol_lib_dir
    └── My_symbol_lib.kicad_sym
```

Most of those arguments are optional. The only required argument is the JLCPCB part #.

The JLCPCB part # is found in the part info section of every component in the JLCPCB part library. 

By default, the library folder will be created in the execution directory. You can specify an absolute path with the -dir option. 

## Dependencies 

JLC2KiCadLib relies on the [KicadModTree](https://gitlab.com/kicad/libraries/kicad-footprint-generator) framework to generate the footprints. 

## Notes

* Even so I tested the script on a lot of components, be careful and always check the output footprint and symbol.
* I consider this project completed. I will continue to maintain it if a bug report is filed, but I will not develop new functionality in the near future. If you feel that an important feature is missing, please open an issue to discuss it, then you can fork this project with a new branch before submitting a PR. 

## License 

Copyright © 2021 TousstNicolas 

The code is released under the MIT license
