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
    return x >= int(rectangle["L"]) and \
        x <= int(rectangle["R"]) and \
        y >= int(rectangle["T"]) and \
        y <= int(rectangle["B"])

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

with open(dfpath, "rb") as infile:
    icsv = csv.DictReader(infile)

    for field in [x_fieldname, y_fieldname]:
        if field not in icsv.fieldnames:
            print("Field not found in data file: "+str(field))

    with open(sys.argv[5], "wb") as ofile:
        ocsv = csv.DictWriter(ofile, fieldnames=icsv.fieldnames+["AOI"])
        ocsv.writeheader()
        for row in icsv:

            # deduce aoi
            fix_x = row[x_fieldname]
            fix_y = row[y_fieldname]
            fix_aoi = None

            for i in range(len(aois)):
                if is_inside(aois[i], int(fix_x), int(fix_y)):
                    fix_aoi = i
                    break

            out_row = dict(row)

            if fix_aoi is None:
                fix_aoi = -1

            out_row["AOI"] = str(fix_aoi)
            ocsv.writerow(out_row)