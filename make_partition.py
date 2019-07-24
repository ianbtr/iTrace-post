"""
An example script (TODO make a notebook too.)
"""

import os
import glob
import subprocess
from subprocess import DEVNULL
from fluorite import ProjectHistory, GazeDataPartition
from itrace_post import post_to_aoi, create_combined_archive

"""
Parameters for gaze2src:
"""
FILTER = "ivt"
FILTER_ARGS = ["-v 30", "-u 60"]

def make_data_partition(function_index, fluorite_log, eclipse_log, core_log, output_dir):

    print("Partitioning data...")

    # Create a ProjectHistory object from a Fluorite log file
    phist = ProjectHistory(fluorite_log)

    # In our timezone at least, the time iTrace records is one hour behind that of Fluorite.
    time_offset = -1*3600*1000

    # Create a DataPartition to split the plugin log file
    data_part = GazeDataPartition(eclipse_log, time_offset)

    # Specify the length of a time segment and separate the data
    num_parts = 10
    time_delta = data_part.create_partition(num_parts=num_parts)

    timezone_offset = 5*1000*3600

    # Save a corresponding file timeline
    phist.save_timeline(output_dir, granularity=time_delta,
                        first_time=data_part.first_time + timezone_offset,
                        last_time=data_part.last_time + timezone_offset)

    # Save partitioned data. This will save files to the timeline directories.
    data_part.save_partition(output_dir)

    # Each folder in the "timeline" directory should now have enough data to run srcml, gaze2src and iTrace-post.
    print("Running gaze2src and generating AOIs...")

    dirs = os.listdir(output_dir)

    for sub_dir in dirs:
        print("\t"+sub_dir)
        prefix = output_dir+"/"+sub_dir

        # Create a tarball of code files
        subprocess.run(["tar", "-czf", prefix+"/src.tar.gz", prefix+"/code_files"],
                       stdout=DEVNULL, stderr=DEVNULL)

        # Run srcml
        subprocess.run(["srcml", prefix+"/src.tar.gz", "-o", prefix+"/src.xml"],
                       stdout=DEVNULL, stderr=DEVNULL)

        # Run gaze2src TODO allow external configuration of gaze2src and iTrace-post parameters
        subprocess.run(["gaze2src", core_log, prefix+"/plugin_log.xml", prefix+"/src.xml",
                        "-f", FILTER]+FILTER_ARGS+["-o", prefix+"/gaze2src"],
                       stdout=DEVNULL, stderr=DEVNULL)

        # Run iTrace-post
        itrace_prefix = prefix + "/gaze2src"

        try:
            fixations_tsv = glob.glob(itrace_prefix + "/fixations*.tsv")[0]
        except IndexError:
            continue

        fixations_db = glob.glob(itrace_prefix + "/rawgazes*.db3")[0]

        post_to_aoi(fixations_db, fixations_tsv, prefix+"/code_files",
                    prefix+"/post2aoi", 5.0, 0.01, func_dict=function_index,
                    time_offset=time_offset)

        unwanted_files = glob.glob(prefix + "/post2aoi/*.java.csv")
        unwanted_files.extend(glob.glob(prefix + "/post2aoi/*.java_AOI.csv"))
        # unwanted_files.extend(glob.glob(prefix + "/gaze2src/*"))
        unwanted_files.extend(glob.glob(prefix + "/*.tar.gz"))
        unwanted_files.extend(glob.glob(prefix + "/plugin_log.xml"))
        unwanted_files.extend(glob.glob(prefix + "/src.xml"))

        for file in unwanted_files:
            os.remove(file)

        # os.rmdir(prefix + "/gaze2src")

    # Collect CSVs and create main archive
    all_csvs = glob.glob(output_dir+"/*/post2aoi/*_functions.csv")
    create_combined_archive(all_csvs, output_dir+"/merged_data.csv")


#make_data_partition("Nick_bug1.json", "raw_data/Nick_bug1/fluorite_log.xml",
#                    "raw_data/Nick_bug1/eclipse_log.xml", "raw_data/Nick_bug1/core_log.xml",
#                    "raw_data/Nick_bug1_timeline")

#make_data_partition("Nick_bug2.json", "raw_data/Nick_bug2/fluorite_log.xml",
#                    "raw_data/Nick_bug2/eclipse_log.xml", "raw_data/Nick_bug2/core_log.xml",
#                    "raw_data/Nick_bug2_timeline")

normal_participants = ["P105", "P201", "P202", "P204", "P205"]

for participant in normal_participants:
    raw_dir_1 = 'raw_data/' + participant + "_bug1"

    fluorite_log1, eclipse_log1, core_log1 = \
        [glob.glob(raw_dir_1+"/"+matching_str)[0] for matching_str in
         ["Log*xml", "eclipse*xml", "core*xml"]]

    make_data_partition("bug1_pretty.json", fluorite_log1, eclipse_log1, core_log1,
                       "processed_data/"+participant+"_bug1_timeline")

    raw_dir2 = 'raw_data/' + participant + "_bug2"

    fluorite_log2, eclipse_log2, core_log2 = \
        [glob.glob(raw_dir2+"/"+matching_str)[0] for matching_str in
         ["Log*xml", "eclipse*xml", "core*xml"]]

    make_data_partition("bug2_pretty.json", fluorite_log2, eclipse_log2, core_log2,
                        "processed_data/"+participant+"_bug2_timeline")