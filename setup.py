import sys
import os

from setuptools import setup, find_packages


long_description = open(os.path.join(sys.path[0], "README.md")).read()

setup(
	name="JLC2KiCadLib",
	description="JLC2KiCad_lib is a python script that generate a component library (schematic, footprint and 3D model) for KiCad from the JLCPCB/easyEDA library.",
	long_description=long_description,
	long_description_content_type="text/markdown",
	url="https://github.com/TousstNicolas/JLC2KiCad_lib",
	version="1.0.7",
	author="TousstNicolas",
	license="MIT",
	install_requires=["KicadModTree", "requests"],
	packages_dir={"JLC2KiCadLib": "JLC2KiCadLib"},
	packages=find_packages(exclude=[]),
	entry_points={"console_scripts": ["JLC2KiCadLib = JLC2KiCadLib.JLC2KiCadLib:main"]},
	classifiers=[
		"Programming Language :: Python :: 3.6",
		"License :: OSI Approved :: MIT License",
		"Operating System :: OS Independent",
		"Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
	],
	python_requires=">=3.6",
)
