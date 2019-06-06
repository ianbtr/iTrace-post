"""
USAGE: <python> xml2csv.py <x-fix input fieldname> <y-fix input fieldname>
            <time input fieldname> <projectfile input fieldname> <x-fix output fieldname>
            <y-fix output fieldname> <duration output fieldname> <time output fieldname>
            <output directory> <input files>

ARGUMENTS:
    1) x-fix input fieldname: The XML attribute corresponding to the x-location of fixations, in the iTrace log file.
    2) y-fix input fieldname: The XML attribute corresponding to the y-location of fixations, in the iTrace log file.
    3) time input fieldname: The XML attribute corresponding to time (in ms) in the iTrace log file.
    4) projectfile input fieldname: The XML attribute corresponding to the name of a given project file, in the
            iTrace log file.
    TODO etc.

OUTPUT: A collection of CSV files representing gazes on particular code files.
    Fixations are currently only recorded as x and y, and duration calculation
    may be implemented later.

NOTE: Can parse any number of input files from various subjects & trials.
"""

import os
import sys
import csv
import xml.etree.ElementTree as ET

# Validate and parse arguments
if len(sys.argv) < 11:
    print("USAGE: <python> xml2csv.py <x-fix input fieldname> <y-fix input fieldname> "
            "<time input fieldname> <projectfile input fieldname> <x-fix output fieldname> "
            "<y-fix output fieldname> <duration output fieldname> <time output fieldname> "
            "<output directory> <input files>")
    exit(1)

x_in, y_in, t_in, fname_in = sys.argv[1:5]
x_out, y_out, dur_out, t_out = sys.argv[5:9]
outdir_name = sys.argv[9]
infile_names = sys.argv[10:]

open_files = dict()

print("Warning: Duration calculation is not currently supported; all output durations are 1.0")

# Create output directory if not already exists
if not os.path.isdir(outdir_name):
    os.makedirs(outdir_name)

current_file = None

# Parse XML files
for infile_name in infile_names:
    tree = ET.parse(infile_name)
    root = tree.getroot()

    # Note: in both log files, the 'gazes' element
    #   is the second child of the root element.
    gaze_elt = root[1]
    num_items = len(gaze_elt)
    current_fname, ocsv = None, None

    for child in gaze_elt:

        # All tags should be responses, but just in case...
        if child.tag != "response": continue
        else:

            # Open new output file if a new file name appears
            child_fname = child.attrib[fname_in]

            # Start a new csv for an unfamiliar filename
            if child_fname not in open_files.keys():
                if current_file is not None: current_file.close()
                current_fname = child_fname
                current_file = open_files[child_fname] = open(outdir_name+"/"+child_fname+".csv", "wb")
                ocsv = csv.DictWriter(current_file, fieldnames=[x_out, y_out, dur_out, t_out])
                ocsv.writeheader()

            # Switch to a file that was already opened
            elif child_fname != current_fname:
                current_file.close()
                current_fname = child_fname
                open_files[child_fname].open('ab')
                current_file = open_files[child_fname]
                ocsv = csv.DictWriter(current_file, fieldnames=[x_out, y_out, dur_out, t_out])

            # Write to output
            ocsv.writerow({
                x_out: int(child.attrib[x_in])-1,
                y_out: int(child.attrib[y_in])-1,
                dur_out: 1.0, #TODO find a way to calculate duration?
                t_out: int(child.attrib[t_in])
            })

if current_file is not None: current_file.close()