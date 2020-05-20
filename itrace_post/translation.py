import os
import csv
import datetime
from csv import QUOTE_NONE
import json
import glob
import sqlite3
import pandas
from .aoi import get_code_envelope, get_aoi_intersection

"""
Combines all the given data files and sorts the rows by time.
Parameters:
    all_csvs: A list of CSVs with the same data fields
    output_path: The path to save the resulting CSV
"""


def create_combined_archive(all_csvs, output_path):
    archives = [pandas.read_csv(
                    csv_file, parse_dates=["fix_time"], index_col=["fix_time"]
                )
                for csv_file in all_csvs]

    archive = pandas.concat(archives, ignore_index=False)

    archive = archive.sort_index()

    archive.to_csv(output_path)


"""
Convert the gaze2src database and TSV files to a CSV file with fixation, AOI, function and entity data.
Parameters:
    db_fpath: The path to a a database (db3) file created by gaze2src
    tsv_fpath: The path to the corresponding TSV file created by gaze2src
    code_dir: The directory containing the code that corresponds with the current time step
    outdir_name: Where to save outputs (AOI location files and data files)
    smoothing: The smoothing parameter for Gaussian smoothing
    threshold: The threshold parameter for creating a mask (after smoothing)
    func_dict: The path to a JSON function index describing the project.
    entity_dict: The path to a JSON entity index describing the project.
    time_offset: The number of milliseconds to add to all timestamps (use this to synchronize with FLUORITE data)
    compute_aois: If True, statistically infer the locations of AOIs.
"""


def post_to_aoi(db_fpath, tsv_fpath, code_dir, outdir_name, smoothing, threshold,
                func_dict=None, entity_dict=None, time_offset=0, compute_aois=False):

    post_to_csv(db_fpath, tsv_fpath, outdir_name, time_offset)

    # Get names of generated files
    generated_files = glob.glob(outdir_name+"/*.csv")

    for generated_file in generated_files:
        code_fname = generated_file[:-4].split("\\")[-1]
        code_fpath = code_dir+"/"+code_fname

        if compute_aois:
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

        if func_dict is not None or entity_dict is not None:
            if compute_aois:
                target_file = generated_file[:-4]+"_AOI.csv"
            else:
                target_file = generated_file

            code_fname_no_ext = trim_extension(code_fname)

            func_file = entity_file = None

            if func_dict is not None:
                with open(func_dict) as infile:
                    func_file_dict = json.load(infile)
                    func_file = func_file_dict[code_fname_no_ext] if code_fname_no_ext in func_file_dict.keys() else None

            if entity_dict is not None:
                with open(entity_dict) as infile:
                    entity_file_dict = json.load(infile)
                    entity_file = entity_file_dict[code_fname_no_ext] if code_fname_no_ext in entity_file_dict.keys() else None

            append_entity(
                target_file, "fix_line", func_file, entity_file, generated_file[:-4]+"_functions.csv"
            )


"""
Convert iTrace's database and TSV files to a CSV.

Parameters:
    db_fpath: The path to a a database (db3) file created by gaze2src
    tsv_fpath: The path to the corresponding TSV file created by gaze2src
    outdir_name: Where to save outputs (AOI location files and data files)
    offset_ms: The number of milliseconds to add to all timestamps (use this to synchronize with FLUORITE data)
"""


def post_to_csv(db_fpath, tsv_fpath, outdir_name, offset_ms):
    # Declare output fieldnames
    output_fieldnames = [
        "fix_col",
        "fix_line",
        "fix_time",
        "fix_dur",
        "pixel_x",
        "pixel_y",
        "left_pupil",
        "right_pupil",
        "which_file"
    ]

    # Read database into pandas dataframe
    conn = sqlite3.connect(db_fpath)

    # Select rows for which fixation_id is not null
    df = pandas.read_sql_query(
        "SELECT * FROM gazes WHERE fixation_id IS NOT NULL",
        conn
    )

    # Multi-file output
    open_files = dict()
    if not os.path.isdir(outdir_name):
        os.makedirs(outdir_name)

    try:
        epoch = datetime.datetime.fromtimestamp(0)
    except OSError:
        epoch = datetime.datetime.utcfromtimestamp(0)

    # Open tsv
    with open(tsv_fpath, "r", newline="") as infile:
        itsv = csv.DictReader(infile, delimiter='\t', quoting=QUOTE_NONE)

        current_fname, current_file, ocsv = None, None, None

        for input_row in itsv:
            fix_id = int(input_row["FIXATION_ID"])

            # Find all occurrences of this ID in the dataframe
            id_data = df.loc[df['fixation_id'] == fix_id]

            # There might not be any (if this is the case, continue)
            if id_data.shape[0] == 0:
                continue

            # Get fixation location by rounding the mean of line/column values
            means = id_data.loc[:, ['line_num', 'col_num']].mean()
            mean_line, mean_col = means['line_num'], means['col_num']

            try:
                nearest_line, nearest_col = int(round(mean_line)), int(round(mean_col))
            except ValueError:
                nearest_line, nearest_col = None, None

            # Get time stamp from df
            tstamp = id_data['time_stamp'].iloc[0]

            # Get file name
            fname = id_data['object_name'].iloc[0]

            # Get x, y coordinates
            pixel_x, pixel_y = input_row["X"], input_row["Y"]

            # Get pupil dilation
            diameter_left, diameter_right = input_row["LEFT_PUPIL"], input_row["RIGHT_PUPIL"]

            # Decide which file to write to
            #  (New file)
            if fname not in open_files.keys():
                if current_fname is not None:
                    current_file.close()
                current_fname = fname
                current_file = open_files[fname] = open(outdir_name + "/" + fname + ".csv", "w", newline="")
                ocsv = csv.DictWriter(current_file, fieldnames=output_fieldnames)
                ocsv.writeheader()

            # (File that was previously opened)
            elif fname != current_fname:
                current_file.close()
                current_fname = fname
                current_file = open_files[fname] = open(outdir_name + "/" + fname + ".csv", "a", newline="")
                ocsv = csv.DictWriter(current_file, fieldnames=output_fieldnames)

            # Write to output file
            ocsv.writerow({
                "fix_col": nearest_col if nearest_col else "NONE",
                "fix_line": nearest_line if nearest_line else "NONE",
                "fix_time": int((datetime.datetime.strptime(tstamp[:-6], "%Y-%m-%dT%H:%M:%S.%f") - epoch)
                                .total_seconds() * 1000 + offset_ms),
                "fix_dur": input_row["DURATION"],
                "pixel_x": pixel_x,
                "pixel_y": pixel_y,
                "left_pupil": diameter_left,
                "right_pupil": diameter_right,
                "which_file": fname
            })

        if current_file is not None:
            current_file.close()


def is_inside(rectangle, x, y):
    return int(rectangle["R"]) >= x >= int(rectangle["L"]) and \
        int(rectangle["B"]) >= y >= int(rectangle["T"])


"""
Takes a CSV with fixation data and appends a column specifying an AOI.

USAGE: append_aoi( <data file path>, <x field name>, <y field name>, 
                <itrace_post json path>, <output file path> )
                
NOTE: The parameter <itrace_post json path> must refer to a JSON file containing a list of AOI's
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

    with open(data_filepath, "r", newline="") as infile:
        icsv = csv.DictReader(infile)

        for field in [x_fieldname, y_fieldname]:
            if field not in icsv.fieldnames:
                raise ValueError(
                    "Field not found in data file: "+str(field)
                )

        with open(output_fpath, "w", newline="") as ofile:
            ocsv = csv.DictWriter(ofile, fieldnames=icsv.fieldnames+["AOI"])
            ocsv.writeheader()
            for row in icsv:

                # deduce itrace_post
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


"""
Adds function and entity columns to the data.
"""


def append_entity(data_filepath, line_fieldname, function_dict, entity_dict, output_fpath):
    with open(data_filepath, "r") as infile:
        icsv = csv.DictReader(infile)

        with open(output_fpath, "w", newline="") as ofile:
            ocsv = csv.DictWriter(ofile, fieldnames=icsv.fieldnames + ["function", "entity"])
            ocsv.writeheader()
            for row in icsv:
                out_row = dict(row)
                line_num = row[line_fieldname]
                entity_type = get_entity_type(line_num, entity_dict)
                function_name = get_function(line_num, function_dict)
                out_row["entity"] = entity_type
                out_row["function"] = function_name
                ocsv.writerow(out_row)


def get_function(line_num, function_dict):
    if function_dict is None:
        return "NONE"

    for key, loc in function_dict.items():
        if int(loc[0]) <= int(line_num) <= int(loc[1]):
            return key

    return "NONE"


def get_entity_type(line_num, entity_dict):
    if entity_dict is None:
        return "NONE"

    for key, loc in entity_dict.items():
        for loc2 in loc.values():
            if int(loc2[0]) <= int(line_num) <= int(loc2[1]):
                return key

    return "NONE"


def trim_extension(name):
    return os.path.splitext(name)[0]