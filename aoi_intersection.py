"""
USAGE: <python> aoi_intersection.py <image width> <image height> <code filepath>
            <font size x> <font size y> <font vertical spacing> <x offset> <y offset>
            [line|token] <gaze data file> <x field> <y field> <Duration field>
            <Smoothing> <Threshold>

NOTE: If <font size x> is given as 1, character resolution is assumed and all other
    font size fields are disregarded.
"""

import warnings
warnings.filterwarnings("ignore")

import sys
from code_aoi import *

if len(sys.argv) != 16:
    print("USAGE: <python> aoi_intersection.py <image width> <image height> <code filepath> "
            "<font size x> <font size y> <font vertical spacing> <x offset> <y offset> "
            "[line|token] <gaze data file> <x field> <y field> <Duration field>"
            "<Smoothing> <Threshold>")
    exit(1)

# Validate image dimensions
img_width, img_height = sys.argv[1:3]
for item in img_width, img_height:
    try: x = int(item)
    except ValueError as e:
        print("image dimensions must be integers")
        raise e
img_width, img_height = int(sys.argv[1]), int(sys.argv[2])

fsize_x = sys.argv[4]

print(get_aoi_intersection(img_width, img_height, sys.argv[3:]))