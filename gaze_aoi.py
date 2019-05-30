import os
import csv
import numpy as np
from math import floor
import scipy.signal as scs

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
        print("ERROR: The relative path "+data_fpath+" does not name "
              "a file in the system.")
        exit(1)

    # Validate floating-point numeric fields
    for field in args[6:8]:
        try: x = float(field)
        except ValueError:
            print("ERROR: smoothing and threshold fields must be valid floating-point numbers.")
            exit(1)

    smoothing_parameter = float(args[6])
    masking_threshold = float(args[7])

    # Validate integer numeric fields
    for field in args[0:2]:
        try: x = int(field)
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
                print("ERROR: The specified field, "+field+", was "
                      "not found in the data file, "+data_fpath)
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
            np.arange(-floor(image_x_size/2.0)+0.5,
                      floor(image_x_size/2.0)-0.5),
            np.arange(-floor(image_y_size/2.0)+0.5,
                      floor(image_y_size/2.0)-0.5)
        )

    gaussian = np.exp(- (x**2 / smoothing_parameter**2) -
                   (y**2 / smoothing_parameter**2))
    gaussian = (gaussian - np.min(gaussian[:])) / (np.max(gaussian[:]) - np.min(gaussian[:]))

    fixmapMat = np.zeros((1, image_y_size, image_x_size))

    coordX   = np.round(np.array(fix_x)).astype(int)
    coordY   = np.round(np.array(fix_y)).astype(int)
    interval = np.array(fix_dur)
    index    = np.logical_and(
                np.logical_and(coordX > 0, coordY > 0),
                np.logical_and(coordX < image_x_size, coordY < image_y_size)
            )

    rawmap   = np.zeros((image_y_size, image_x_size))

    rawmap[coordY[index], coordX[index]] += interval[index]

    smoothed = scs.fftconvolve(rawmap, gaussian, mode='same')

    fixmapMat[0][:][:] = (smoothed-np.mean(smoothed[:])) / np.std(smoothed[:])

    return np.squeeze(np.mean(fixmapMat, 0)) > masking_threshold