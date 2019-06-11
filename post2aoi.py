"""
USAGE: <python> post2aoi.py <input db path> <input tsv path> <code directory> <output directory>
    <smoothing> <threshold>

ARGUMENTS:
    1. Input db path: SQL database file produced by iTrace post-processor.
    2. Input tsv path: TSV file produced by iTrace post-processor.
    3. Output directory: Path to desired directory (data will be split by object)
    4. Smoothing: Smoothing parameter for Gaussian smoothing
    5. Threshold: Threshold for generating AOI's from duration heatmap.
        Consider that durations from iTrace are in nanoseconds. This number should probably be
        about 1000 or higher.
"""

import os
import sys
import glob
import json
from itrace_post import *

# Validate arguments
if len(sys.argv) < 7:
    print(
        "USAGE: <python> post2aoi.py <input db path> "
        "<input tsv path> <code directory> <output directory> "
        "<smoothing> <threshold>"
    )
    exit(1)

fpaths = sys.argv[1:3]
for path in fpaths:
    if not os.path.exists(path):
        print(
            "Path does not exist: "+path
        )
        exit(1)

db_fpath, tsv_fpath, code_dir, outdir_name = sys.argv[1:5]
smoothing, threshold = map(float, sys.argv[5:8])

print("Translating database...\n")
post_to_csv(db_fpath, tsv_fpath, outdir_name)

# Get names of generated files
generated_files = glob.glob(outdir_name+"/*.csv")

print("Generating AOI's...")
for generated_file in generated_files:
    print("\t"+generated_file)

    code_fname = generated_file[:-4].split("\\")[-1]
    code_fpath = code_dir+"/"+code_fname

    width, height = get_code_envelope(code_fpath)

    # Generate AOI
    mask, labels, rectangles = \
        get_aoi_intersection(
            width, height, code_fpath, generated_file,
            x_fieldname="fix_col", y_fieldname="fix_line",
            dur_fieldname="fix_dur", smoothing=smoothing,
            threshold=threshold
        )

    json_file = generated_file[:-4] + "_AOI.json"
    with open(json_file, "w") as ofile:
        ofile.write(
            json.dumps(rectangles)
        )

    append_aoi(
        generated_file, "fix_col", "fix_line",
        json_file, generated_file[:-4]+"_AOI.csv"
    )