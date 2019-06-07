import os
import csv
import json
import sqlite3
import pandas as pd

"""
USAGE: post_to_csv( <path to iTrace output database>, 
    <path to iTrace output TSV>, <relative path to output directory> )
"""
def post_to_csv(db_fpath, tsv_fpath, outdir_name):
    # Declare output fieldnames
    output_fieldnames = [
        "fix_col",
        "fix_line",
        "fix_time",
        "fix_dur",
        "which_file"
    ]

    # Read database into pandas dataframe
    conn = sqlite3.connect(db_fpath)

    # Select rows for which fixation_id is not null
    df = pd.read_sql_query(
        "SELECT * FROM gazes WHERE fixation_id IS NOT NULL",
        conn
    )

    # Multi-file output
    open_files = dict()
    if not os.path.isdir(outdir_name):
        os.makedirs(outdir_name)

    # Open tsv
    with open(tsv_fpath, "rb") as infile:
        itsv = csv.DictReader(infile, delimiter='\t')

        current_fname, current_file, ocsv = None, None, None

        for input_row in itsv:
            fix_id = int(input_row["FIXATION_ID"])

            # Find all occurrences of this ID in the dataframe
            id_data = df.loc[df['fixation_id'] == fix_id]

            # Get fixation location by rounding the mean of line/column values
            # TODO is this really such a great idea?
            # TODO also we know that col_num is zero-indexed, but what about line_num?
            means = id_data.loc[:, ['line_num', 'col_num']].mean()
            mean_line, mean_col = means['line_num'], means['col_num']
            nearest_line, nearest_col = int(round(mean_line)), int(round(mean_col))

            # Get time stamp from df
            # TODO this assumes that the rows are ordered by timestamp (pretty sure this is the case)
            tstamp = id_data['time_stamp'].iloc[0]

            # Get file name
            fname = id_data['object_name'].iloc[0]

            # Decide which file to write to
            #  (New file)
            if fname not in open_files.keys():
                if current_fname is not None: current_file.close()
                current_fname = fname
                current_file = open_files[fname] = open(outdir_name + "/" + fname + ".csv", "wb")
                ocsv = csv.DictWriter(current_file, fieldnames=output_fieldnames)
                ocsv.writeheader()

            # (File that was previously opened)
            elif fname != current_fname:
                current_file.close()
                current_fname = fname
                current_file = open_files[fname] = open(outdir_name + "/" + fname + ".csv", "ab")
                ocsv = csv.DictWriter(current_file, fieldnames=output_fieldnames)

            # Write to output file
            ocsv.writerow({
                "fix_col": nearest_col,
                "fix_line": nearest_line,
                "fix_time": tstamp,
                "fix_dur": input_row["DURATION"],
                "which_file": fname
            })

        if current_file is not None: current_file.close()

def is_inside(rectangle, x, y):
    return x >= int(rectangle["L"]) and \
        x <= int(rectangle["R"]) and \
        y >= int(rectangle["T"]) and \
        y <= int(rectangle["B"])

"""
Takes a CSV with fixation data and appends a column specifying an AOI.

USAGE: append_aoi( <data file path>, <x field name>, <y field name>, 
                <aoi json path>, <output file path> )
                
NOTE: The parameter <aoi json path> must refer to a JSON file containing a list of AOI's
    in decreasing order of area. Each AOI is a rectangle of the following form:
    
    {
        "T": <top edge of AOI>,
        "L": <left edge of AOI>,
        "B": <bottom edge of AOI>,
        "R": <right edge of AOI>
    }

OUTPUT: The same CSV with an additional AOI column. AOI's are numbered beginning with zero, 
    and a -1 indicates that the fixation is not inside any of the given AOI's. If a 
    fixation is inside multiple AOI's, the AOI numbers will be joined with a forward slash.
"""
def append_aoi(data_filepath, x_fieldname, y_fieldname, aoi_filepath, output_fpath):

    if not os.path.exists(data_filepath):
        raise ValueError(
            "Data file does not exist at the given path: "+str(data_filepath)
        )

    if not os.path.exists(aoi_filepath):
        raise ValueError(
            "Data file does not exist at the given path: "+str(aoi_filepath)
        )

    with open(aoi_filepath) as infile:
        aois = json.load(infile)

    with open(data_filepath, "rb") as infile:
        icsv = csv.DictReader(infile)

        for field in [x_fieldname, y_fieldname]:
            if field not in icsv.fieldnames:
                raise ValueError(
                    "Field not found in data file: "+str(field)
                )

        with open(output_fpath, "wb") as ofile:
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