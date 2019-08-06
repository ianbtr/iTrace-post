"""
An example script
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


def make_data_partition(function_index, entity_index, fluorite_log,
                        eclipse_log, core_log, output_dir, compute_aois=False):

    print("Partitioning data...")

    # Create a ProjectHistory object from a Fluorite log file
    phist = ProjectHistory(fluorite_log, func_location_file=function_index,
                           entity_location_file=entity_index)

    # In our timezone at least, the time iTrace records is 4 hours behind that of FLUORITE.
    time_offset = 4*3600*1000

    # Create a DataPartition to split the plugin log file
    data_part = GazeDataPartition(eclipse_log, time_offset)

    # Save a corresponding file timeline
    time_periods = phist.save_timeline(output_dir, granularity='finest',
                                       first_time=data_part.first_time,
                                       last_time=data_part.last_time)

    # Separate the data
    data_part.create_partition(time_periods=time_periods)

    # Save partitioned data. This will save files to the timeline directories.
    data_part.save_partition(output_dir)

    # Each folder in the "timeline" directory should now have enough data to run srcml, gaze2src and iTrace-post.
    print("Running gaze2src and generating AOIs...")

    dirs = os.listdir(output_dir)

    for sub_dir in dirs:
        print("\t"+sub_dir)
        prefix = output_dir+"/"+sub_dir

        if not os.path.exists(prefix+"/plugin_log.xml"):
            continue

        # Create a tarball of code files
        subprocess.run(["tar", "-czf", prefix+"/src.tar.gz", prefix+"/code_files"],
                       stdout=DEVNULL, stderr=DEVNULL)

        # Run srcml
        subprocess.run(["srcml", prefix+"/src.tar.gz", "-o", prefix+"/src.xml"],
                       stdout=DEVNULL, stderr=DEVNULL)

        # Run gaze2src
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

        function_archive = prefix+"/code_files/functions.json"
        entity_archive = prefix+"/code_files/entities.json"

        post_to_aoi(fixations_db, fixations_tsv, prefix+"/code_files",
                    prefix+"/post2aoi", 5.0, 0.01, func_dict=function_archive,
                    entity_dict=entity_archive, time_offset=time_offset, compute_aois=compute_aois)

        unwanted_files = glob.glob(prefix + "/post2aoi/*.java.csv")
        unwanted_files.extend(glob.glob(prefix + "/post2aoi/*.java_AOI.csv"))
        unwanted_files.extend(glob.glob(prefix + "/*.tar.gz"))
        unwanted_files.extend(glob.glob(prefix + "/src.xml"))

        for file in unwanted_files:
            os.remove(file)

        # os.rmdir(prefix + "/gaze2src")

    # Collect CSVs and create main archive
    all_csvs = glob.glob(output_dir+"/*/post2aoi/*_functions.csv")
    create_combined_archive(all_csvs, output_dir+"/merged_data.csv")


participants = ["P-107"]

for participant in participants:
    raw_dir_1 = 'raw_data/' + participant + "/" + participant + "-bug1"

    fluorite_log1, eclipse_log1, core_log1 = \
        [glob.glob(raw_dir_1+"/"+matching_str)[0] for matching_str in
         ["Log*xml", "*/eclipse*xml", "*/core*xml"]]

    make_data_partition("bug1_functions.json", "bug1_entities.json", fluorite_log1, eclipse_log1, core_log1,
                        "processed_data/"+participant+"_bug1_timeline", compute_aois=True)

    raw_dir2 = 'raw_data/' + participant + "/" + participant + "-bug2"

    fluorite_log2, eclipse_log2, core_log2 = \
        [glob.glob(raw_dir2+"/"+matching_str)[0] for matching_str in
         ["Log*xml", "*/eclipse*xml", "*/core*xml"]]

    make_data_partition("bug2_functions.json", "bug2_entities.json", fluorite_log2, eclipse_log2, core_log2,
                        "processed_data/"+participant+"_bug2_timeline", compute_aois=True)
