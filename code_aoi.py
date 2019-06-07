import os
import csv
import json
import numpy as np
import scipy.ndimage
from math import floor
from eyecode import aoi
from structs import Rect
import scipy.signal as scs

"""
Get the exact dimensions of the file in columns and lines.
"""
def get_code_envelope(code_file):
    with open(code_file, "r") as infile:
        lines = infile.readlines()

    max_width, line_count = 0, 0
    for line in lines:
        if len(line) > max_width: max_width = len(line)
        line_count += 1

    return max_width, line_count

"""
USAGE: aoi_intersection( <image width> <image height> <code filepath>
            <font size x> <font size y> <font vertical spacing> <x offset> <y offset>
            ["line"|"token"] <gaze data file> <x field> <y field> <Duration field>
            <Smoothing> <Threshold> )

NOTE: If <font size x> is given as 1, character resolution is assumed and all other
    font size fields are disregarded.
"""
def get_aoi_intersection(img_width, img_height, *args):
    # Compute code mask for character-resolved stimulus
    if args[1] == 1:
        code_mask = generate_char_aois(img_width, img_height, *args[:7])
    # For actual pixels:
    else:
        code_mask = generate_code_aois(img_width, img_height, *args[:7])
    # plt.imshow(code_mask)
    # plt.savefig("code_mask.png", dpi=200)

    # Compute gaze mask
    gaze_mask = generate_gaze_aois(img_width, img_height, *args[7:])
    # plt.imshow(gaze_mask)
    # plt.savefig("gaze_mask.png", dpi=200)

    # Merge masks
    mask_intersection = np.logical_and(code_mask, gaze_mask)

    # Identify regions
    all_labels, num_features = scipy.ndimage.label(mask_intersection)

    # Create rectangles
    rectangles = list()
    # fig_rectangles = list()
    for label in range(1, num_features + 1):
        row_occurrences, col_occurrences = np.where(all_labels == label)
        left_extent = min(col_occurrences)
        right_extent = max(col_occurrences)
        top_extent = min(row_occurrences)
        bottom_extent = max(row_occurrences)

        rectangles.append(Rect(left_extent, right_extent,
                               top_extent, bottom_extent))

    """
        fig_rectangles.append(Rectangle((left_extent, top_extent),
                                        right_extent - left_extent,
                                        bottom_extent - top_extent,
                                        fill=False))


    fig, ax = plt.subplots(1)
    pc = PatchCollection(fig_rectangles, alpha=0.5, edgecolor='w')
    ax.add_collection(pc)
    plt.imshow(all_labels, cmap='Spectral')
    plt.savefig('rects.png', dpi=200)
    """

    # Dump rectangles in order of area
    rectangles.sort(key=lambda rect: rect.area(), reverse=True)
    rect_dict = list(map(lambda rect: rect.as_dict(), rectangles))
    return json.dumps(rect_dict)

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


"""
USAGE: generate_gaze_aois(<width> <height> <data as CSV> <X field> <Y field> <Duration field> <Smoothing> <Threshold>)

INPUT (Argument 1): The width of the stimulus, in pixels (INTEGER)
      (Argument 2): The height of the stimulus, in pixels (INTEGER)
      (Arguments 3-6): The relative path of a CSV with fields X, Y and duration, and the names of those fields as
                        they appear in the file. Data is for all participants on a single stimulus.
      (Argument 7): The smoothing parameter to apply during Gaussian smoothing. (FLOAT)
      (Argument 8): The threshold above which the given pixel may be eliminated from the mask and assigned a logical
                    value of 1. (FLOAT)

OUTPUT: A logical array representing a mask due to the given smoothing and threshold parameters.
"""
def generate_gaze_aois(*args):
    # Validate data file path
    data_fpath = args[2]
    if not os.path.exists(data_fpath):
        print("ERROR: The relative path " + data_fpath + " does not name "
                                                         "a file in the system.")
        exit(1)

    # Validate floating-point numeric fields
    for field in args[6:8]:
        try:
            x = float(field)
        except ValueError:
            print("ERROR: smoothing and threshold fields must be valid floating-point numbers.")
            exit(1)

    smoothing_parameter = float(args[6])
    masking_threshold = float(args[7])

    # Validate integer numeric fields
    for field in args[0:2]:
        try:
            x = int(field)
        except ValueError:
            print("ERROR: image size parameters must be valid integers.")
            exit(1)

    image_x_size = int(args[0])
    image_y_size = int(args[1])

    # Read data file
    fix_x = list()
    fix_y = list()
    fix_dur = list()
    with open(data_fpath, "r") as infile:
        icsv = csv.DictReader(infile)

        # Validate fieldnames
        for field in args[3:6]:
            if field not in icsv.fieldnames:
                print("ERROR: The specified field, " + field + ", was "
                                                               "not found in the data file, " + data_fpath)
                exit(1)

        x_fieldname = args[3]
        y_fieldname = args[4]
        dur_fieldname = args[5]

        # Read data

        for row in icsv:
            fix_x.append(float(row[x_fieldname]))
            fix_y.append(float(row[y_fieldname]))
            fix_dur.append(float(row[dur_fieldname]))

    # TRANSLATION OF MATLAB SCRIPT:

    # Smooth the data and create a mask
    [x, y] = np.meshgrid(
        np.arange(-floor(image_x_size / 2.0) + 0.5,
                  floor(image_x_size / 2.0) - 0.5),
        np.arange(-floor(image_y_size / 2.0) + 0.5,
                  floor(image_y_size / 2.0) - 0.5)
    )

    gaussian = np.exp(- (x ** 2 / smoothing_parameter ** 2) -
                      (y ** 2 / smoothing_parameter ** 2))
    gaussian = (gaussian - np.min(gaussian[:])) / (np.max(gaussian[:]) - np.min(gaussian[:]))

    fixmapMat = np.zeros((1, image_y_size, image_x_size))

    coordX = np.round(np.array(fix_x)).astype(int)
    coordY = np.round(np.array(fix_y)).astype(int)
    interval = np.array(fix_dur)
    index = np.logical_and(
        np.logical_and(coordX > 0, coordY > 0),
        np.logical_and(coordX < image_x_size, coordY < image_y_size)
    )

    rawmap = np.zeros((image_y_size, image_x_size))

    rawmap[coordY[index], coordX[index]] += interval[index]

    smoothed = scs.fftconvolve(rawmap, gaussian, mode='same')

    fixmapMat[0][:][:] = (smoothed - np.mean(smoothed[:])) / np.std(smoothed[:])

    return np.squeeze(np.mean(fixmapMat, 0)) > masking_threshold