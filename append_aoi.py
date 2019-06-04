"""
Takes a CSV with fixation data and appends a column specifying an AOI.

USAGE: <python> append_aoi.py <data file path> <x field name> <y field name> <aoi json path> <output file path>

OUTPUT: The same CSV with an additional AOI column. AOI's are numbered 0-x, and a -1 indicates that the fixation is
    not inside any of the given AOI's. If a fixation is inside multiple AOI's, the AOI numbers will be joined with a
    forward slash.
"""

import sys
import csv
import os
import json

def is_inside(rectangle, x, y):
    pass

if len(sys.argv) < 6:
    print("USAGE: <python> append_aoi.py <data file path> <x field name> <y field name> <aoi json path> <output file path>")
    exit(1)

dfpath = sys.argv[1]

if not os.path.exists(dfpath):
    print("Data file does not exist at the given path: "+str(dfpath))
    exit(1)

json_fpath = sys.argv[4]

if not os.path.exists(json_fpath):
    print("Data file does not exist at the given path: "+str(json_fpath))
    exit(1)

x_fieldname, y_fieldname = sys.argv[2:4]

with open(json_fpath) as infile:
    aois = json.load(infile)

with open(dfpath) as infile:
    icsv = csv.DictReader(infile)

    for field in [x_fieldname, y_fieldname]:
        if field not in icsv.fieldnames:
            print("Field not found in data file: "+str(field))

    with open(sys.argv[5]) as ofile:
        ocsv = csv.DictWriter(ofile, fieldnames=icsv.fieldnames+["AOI"])
        for row in icsv:

            # deduce aoi
            fix_x = row[x_fieldname]
            fix_y = row[y_fieldname]
            fix_aoi = list()

            for i in range(len(aois)):
                if is_inside(aois[i], fix_x, fix_y):
                    fix_aoi.append(str(i))

            out_row = dict(row)
            out_row["AOI"] = "/".join(fix_aoi)
            ocsv.writerow(out_row)