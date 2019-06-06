import os
from structs import Rect
from eyecode import aoi
import numpy as np

"""
ARGUMENTS: x_res: Width of stimulus in pixels
           y_res: Height of stimulus in pixels
           
           Additional required arguments:
           1. Code file: A relative path to the code file for which you wish to generate AOI's.
           2. Font x size: The width of the font in pixels.
           3. Font y size: The height of the font in pixels.
           4. Font vertical spacing: The vertical spacing of the font in pixels.
           5. Global x offset: The amount by which the first line of code is shifted from the upper-left
                corner of the stimulus, in pixels of width.
           6. Global y offset: The amount by which the first line of code is shifted from the upper-left
                corner of the stimulus, in pixels of height.
           7. AOI type: Any of "line" or "token".

RETURNS:   A numpy logical array where code AOI's are marked as ones.
"""

def validate_arguments(arguments):
    # Validate data file path
    data_fpath = arguments[0]
    if not os.path.exists(data_fpath):
        print("ERROR: The relative path " + data_fpath + " does not "
                                                         "name a file in the system.")
        exit(1)

    # Validate integer numeric fields
    for field in arguments[1:4]:
        try:
            x = int(field)
        except ValueError as e:
            print("ERROR: font size parameters must be valid integers")
            raise e

    # Validate floating-point numeric fields
    for field in arguments[4:6]:
        try:
            x = float(field)
        except ValueError as e:
            print("ERROR: offset parameters must be valid floats")
            raise e

def generate_char_aois(x_res, y_res, *args):
    validate_arguments(args)

    data_fpath = args[0]

    # Disregard AOI type, and assume line AOI
    # Assume unit font size and spacing with no offset
    with open(data_fpath, "r") as infile:
        code = infile.readlines()

    # Replace all tabs with 4 spaces and remove trailing newlines
    for i in range(len(code)):
        code[i] = code[i].replace("\t", " "*4)
        code[i] = code[i].replace("\n", "")

    # Generate AOI's line by line
    regions = np.zeros((y_res, x_res))
    for i in range(len(code)):
        if len(code[i]) == 0: continue
        regions[i, 0:len(code[i])] = 1

    return regions

def generate_code_aois(x_res, y_res, *args):
    data_fpath = args[0]
    font_size_x = int(args[1])
    font_size_y = int(args[2])
    font_spacing = int(args[3])
    x_offset = float(args[4])
    y_offset = float(args[5])

    # Validate AOI type
    aoi_type = args[6]
    if aoi_type != "line" and aoi_type != "token":
        print("ERROR: aoi_type argument must be either 'line' or 'token'")
        exit(1)

    # Load code from file
    with open(data_fpath, "r") as infile:
        code = infile.read()

    # Replace all tabs with 4 spaces
    code = code.replace("\t", " " * 4)

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

    rects = list()
    for index, row in sub_aois.iterrows():
        rects.append(
            Rect(
                row['x'], row['x'] + row['width'],
                row['y'], row['y'] + row['height']
            )
        )

    # Create logical array
    regions = np.zeros((y_res, x_res))
    for rect in rects:
        if rect.top < 0: rect.top = 0
        if rect.left < 0: rect.left = 0
        regions[rect.top : rect.bottom + 1, rect.left : rect.right + 1] = 1

    return regions