"""
USAGE: <python> db2csv.py <input db path> <input tsv path> <output directory>

ARGUMENTS:
    1. Input db path: SQL database file produced by iTrace post-processor.
    2. Input tsv path: TSV file produced by iTrace post-processor.
    3. Output directory: Path to desired directory (data will be split by object)
"""

import os
import sys
import csv
import sqlite3
import pandas as pd

# Validate arguments
if len(sys.argv) < 4:
    print(
        "USAGE: <python> db2csv.py <input db path> "
        "<input tsv path> <output directory>"
    )
    exit(1)

fpaths = sys.argv[1:3]
for path in fpaths:
    if not os.path.exists(path):
        print(
            "Path does not exist: "+path
        )
        exit(1)

db_fpath, tsv_fpath, outdir_name = sys.argv[1:4]

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