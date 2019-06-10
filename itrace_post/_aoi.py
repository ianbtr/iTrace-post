import os
import csv
import json
import numpy
import scipy.ndimage
from math import floor
import scipy.signal

"""
A rectangle class
"""
class Rect:
    def __init__(self, left, right, top, bottom):
        self.left = left
        self.right = right
        self.top = top
        self.bottom = bottom
    def as_dict(self):
        return {
            "L": int(self.left),
            "R": int(self.right),
            "T": int(self.top),
            "B": int(self.bottom)
        }
    def area(self):
        return (self.right - self.left) * (self.bottom - self.top)

"""
Get the exact dimensions of the given code file in columns and lines.
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
USAGE: aoi_intersection( <stimulus width>, <stimulus height>, <stimulus filepath>,
    <gaze data filepath>, <x fieldname>, <y fieldname>, <duration fieldname>,
    smoothing=<smoothing parameter>, threshold=<threshold parameter>,
    character_resolution=[True|False], **kwargs)
    
Extra keyword arguments are used if character_resolution is False.

NOTE: If <font size x> is given as 1, character resolution is assumed and all other
    font size fields are disregarded.
    
OUTPUT: A triple containing a mask, a labeled mask, and a list of dictionaries describing
    rectangles that inscribe each distinct region in the mask.
"""
def get_aoi_intersection(img_width, img_height, code_filepath,
        gaze_data_filepath, x_fieldname, y_fieldname, dur_fieldname,
        smoothing=5.0, threshold=0.01, character_resolution=True, **kwargs):

    if not character_resolution:
        raise NotImplementedError(
            "Pixel resolution is not currently supported."
        )

    # Compute code mask for character-resolved stimulus
    code_mask = generate_code_mask(code_filepath, img_width, img_height)
    # plt.imshow(code_mask)
    # plt.savefig("code_mask.png", dpi=200)

    # Compute gaze mask
    gaze_mask = generate_gaze_mask(gaze_data_filepath, x_fieldname,
        y_fieldname, dur_fieldname, img_width, img_height,
        smoothing=smoothing, threshold=threshold)
    # plt.imshow(gaze_mask)
    # plt.savefig("gaze_mask.png", dpi=200)

    # Merge masks
    mask_intersection = numpy.logical_and(code_mask, gaze_mask)

    # Identify regions
    all_labels, num_features = scipy.ndimage.label(mask_intersection)

    # Create rectangles
    rectangles = list()
    # fig_rectangles = list()
    for label in range(1, num_features + 1):
        row_occurrences, col_occurrences = numpy.where(all_labels == label)
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
    return mask_intersection, all_labels, rect_dict

"""
USAGE: generate_char_aois(<code filepath>, <number of columns>, <number of liens> )
    
OUTPUT: A logical numpy array corresponding to the location of code in the given file.
    Each cell in the array corresponds to a character in the file, rather than a pixel.
    
NOTE: Tabs are assumed to be worth 4 spaces.
"""
def generate_code_mask(code_fpath, num_cols, num_lines):
    # Validate data filepath
    if not os.path.isfile(code_fpath):
        raise ValueError(
            "File not found: "+code_fpath
        )

    x_res, y_res = num_cols, num_lines

    # Disregard AOI type, and assume line AOI
    # Assume unit font size and spacing with no offset
    with open(code_fpath, "r") as infile:
        code = infile.readlines()

    # Replace all tabs with 4 spaces and remove trailing newlines
    for i in range(len(code)):
        code[i] = code[i].replace("\t", " "*4)
        code[i] = code[i].replace("\n", "")

    # Generate AOI's line by line
    regions = numpy.zeros((y_res, x_res))
    for i in range(len(code)):
        if len(code[i]) == 0: continue

        # Get end of leading whitespace
        line_start = len(code[i]) - len(code[i].lstrip())

        # Get beginning of trailing whitespace
        line_end = len(code[i].rstrip())

        regions[i, line_start:line_end] = 1

    return regions

"""
This code is for generating AOI's resolved to the pixel.
It is not currently in use.

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
    aois = itrace_post.code_to_aois(code, filename=data_fpath, font_size=(font_size_x, font_size_y),
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
    regions = numpy.zeros((y_res, x_res))
    for rect in rects:
        if rect.top < 0: rect.top = 0
        if rect.left < 0: rect.left = 0
        regions[rect.top : rect.bottom + 1, rect.left : rect.right + 1] = 1

    return regions
"""


"""
USAGE: generate_gaze_aois(data_file, x_fieldname, y_fieldname, dur_fieldname,
            stimulus_width, stimulus_height, smoothing=<smoothing parameter>,
            threshold=<threshold parameter>)

InumpyUT: data_file: A CSV-style file containing x, y and duration fields for fixations on the given stimulus.
       x_fieldname: The field name in the data file corresponding to the x-position of gazes.
       y_fieldname: The field name in the data file corresponding to the y-positions of gazes.
       dur_fieldname: The field name... corresponding to the duration of gazes.
       
OUTPUT: A logical array representing a mask due to the given smoothing and threshold parameters.
"""
def generate_gaze_mask(data_file, x_fieldname, y_fieldname, dur_fieldname,
                       stimulus_width, stimulus_height, smoothing=5.0, threshold=0.01):
    # Validate data file path
    if not os.path.exists(data_file):
        raise ValueError(
            "ERROR: The relative path " + data_file + " does not name "
            "a file in the system."
        )

    # Read data file
    fix_x = list()
    fix_y = list()
    fix_dur = list()

    with open(data_file, "r") as infile:
        icsv = csv.DictReader(infile)

        # Validate fieldnames
        for field in x_fieldname, y_fieldname, dur_fieldname:
            if field not in icsv.fieldnames:
                print("ERROR: The specified field, " + field + ", was "
                    "not found in the data file, " + data_file)
                exit(1)

        # Read data
        for row in icsv:
            fix_x.append(float(row[x_fieldname]))
            fix_y.append(float(row[y_fieldname]))
            fix_dur.append(float(row[dur_fieldname]))

    # TRANSLATION OF MATLAB SCRIPT:

    # Smooth the data and create a mask
    [x, y] = numpy.meshgrid(
        numpy.arange(-floor(stimulus_width / 2.0) + 0.5,
                  floor(stimulus_width / 2.0) - 0.5),
        numpy.arange(-floor(stimulus_height / 2.0) + 0.5,
                  floor(stimulus_height / 2.0) - 0.5)
    )

    gaussian = numpy.exp(- (x ** 2 / smoothing ** 2) -
                      (y ** 2 / smoothing ** 2))
    gaussian = (gaussian - numpy.min(gaussian[:])) / (numpy.max(gaussian[:]) - numpy.min(gaussian[:]))

    fixmapMat = numpy.zeros((1, stimulus_height, stimulus_width))

    coordX = numpy.round(numpy.array(fix_x)).astype(int)
    coordY = numpy.round(numpy.array(fix_y)).astype(int)
    interval = numpy.array(fix_dur)
    index = numpy.logical_and(
        numpy.logical_and(coordX > 0, coordY > 0),
        numpy.logical_and(coordX < stimulus_width, coordY < stimulus_height)
    )

    rawmap = numpy.zeros((stimulus_height, stimulus_width))

    rawmap[coordY[index], coordX[index]] += interval[index]

    smoothed = scipy.signal.fftconvolve(rawmap, gaussian, mode='same')

    fixmapMat[0][:][:] = (smoothed - numpy.mean(smoothed[:])) / numpy.std(smoothed[:])

    return numpy.squeeze(numpy.mean(fixmapMat, 0)) > threshold