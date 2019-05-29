"""
USAGE: <python> aoi_gen.py <code file> <font x size> <font y size> <font vertical spacing> <global x offset>
    <global y offset> <AOI type> save_dframe=[true|false]

ARGUMENTS: 1. Code file: A relative path to the code file for which you wish to generate AOI's.
           2. Font x size: The width of the font in pixels.
           3. Font y size: The height of the font in pixels.
           4. Font vertical spacing: The vertical spacing of the font in pixels.
           5. Global x offset: The amount by which the first line of code is shifted from the upper-left
                corner of the stimulus, in pixels of width.
           6. Global y offset: The amount by which the first line of code is shifted from the upper-left
                corner of the stimulus, in pixels of height.
           7. AOI type: Any of "line" or "token".
           8. Option to save record of AOI's as a dataframe. If true, saves the dataframe to dfdump.csv
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import os
import json
from structs import Rect
from eyecode import aoi

# Check arguments
if len(sys.argv) != 9:
    print("USAGE: "+sys.argv[0]+" aoi_gen.py <code file> <font x size> <font y size> "
        "<font vertical spacing> <global x offset> "
        "<global y offset> <AOI type> save_dframe=[true|false]")
    exit(1)

# Validate data file path
data_fpath = sys.argv[1]
if not os.path.exists(data_fpath):
    print("ERROR: The relative path "+data_fpath+" does not "
        "name a file in the system.")
    exit(1)

# Validate integer numeric fields
for field in sys.argv[2:5]:
    try:
        x = int(field)
    except ValueError as e:
        print("ERROR: font size parameters must be valid integers")
        raise e

# Validate floating-point numeric fields
for field in sys.argv[5:7]:
    try:
        x = float(field)
    except ValueError as e:
        print("ERROR: offset parameters must be valid floats")
        raise e

font_size_x = int(sys.argv[2])
font_size_y = int(sys.argv[3])
font_spacing = int(sys.argv[4])
x_offset = float(sys.argv[5])
y_offset = float(sys.argv[6])

# Validate AOI type
aoi_type = sys.argv[7]
if aoi_type != "line" and aoi_type != "token":
    print("ERROR: aoi_type argument must be either 'line' or 'token'")
    exit(1)

# Validate save_dframe option
save_dframe_opt = sys.argv[8][12:]
save_dframe = (save_dframe_opt == "true")
if not save_dframe and save_dframe_opt != "false":
    print("ERROR: save_dframe argument must be either 'save_dframe=true' or 'save_dframe=false'")
    exit(1)

# Load code from file
with open(data_fpath, "r") as infile:
    code = infile.read()

# Replace all tabs with 4 spaces
code = code.replace("\t", " "*4)

# Generate AOI's
aois = aoi.code_to_aois(code, filename=data_fpath, font_size=(font_size_x, font_size_y),
                        line_offset=font_spacing)

# Add offset to all entries
for row_num in range(aois.shape[0]):
    aois.at[row_num, 'x'] += x_offset
    aois.at[row_num, 'y'] += y_offset

# Categorize AOI's
sub_aois = aois[aois.kind == "line"] if aoi_type == "line" \
    else aois[aois.kind == "token"]

# Print AOI's as JSON
rects = list()
for index, row in sub_aois.iterrows():
    rects.append(
        Rect(
            row['x'], row['x'] + row['width'],
            row['y'], row['y'] + row['height']
        ).as_dict()
    )

print(json.dumps(rects))

# If requested, dump dataframe to a file
sub_aois.to_csv("dfdump.csv")