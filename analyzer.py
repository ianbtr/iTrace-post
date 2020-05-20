"""
An example script
"""

import os
import glob
import pandas as pd
import subprocess
from subprocess import DEVNULL
from fluorite import ProjectHistory, GazeDataPartition
from itrace_post import post_to_aoi, create_combined_archive

"""
Parameters for gaze2src:
"""
FILTER = "ivt"
FILTER_ARGS = ["-v 30", "-u 60"]


def make_and_process_data_partition(function_index, entity_index, fluorite_log,
                        eclipse_log, core_log, output_dir, compute_aois=False):

    print("Partitioning data...")

    # Create a ProjectHistory object from a Fluorite log file
    phist = ProjectHistory(fluorite_log, func_location_file=function_index,
                           entity_location_file=entity_index)

    # In our timezone at least, the time iTrace records is 4 or 5 hours behind that of FLUORITE.
    # TODO since this varies, maybe check it automatically and round to the nearest hour difference.
    time_offset = 5*3600*1000

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
        if not os.path.isdir(output_dir + "/" + sub_dir):
            continue

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

        function_archive = prefix+"/code_files/functions.json" if function_index else None
        entity_archive = prefix+"/code_files/entities.json" if entity_index else None

        post_to_aoi(fixations_db, fixations_tsv, prefix+"/code_files",
                    prefix+"/post2aoi", 5.0, 0.01, func_dict=function_archive,
                    entity_dict=entity_archive, time_offset=time_offset, compute_aois=compute_aois)

        unwanted_files = glob.glob(prefix + "/post2aoi/*.java.csv")
        unwanted_files.extend(glob.glob(prefix + "/post2aoi/*.java_AOI.csv"))
        unwanted_files.extend(glob.glob(prefix + "/*.tar.gz"))
        unwanted_files.extend(glob.glob(prefix + "/src.xml"))

        for file in unwanted_files:
            os.remove(file)

    # END FOR

    # Collect CSVs and create main archive
    all_csvs = glob.glob(output_dir+"/*/post2aoi/*_functions.csv")
    create_combined_archive(all_csvs, output_dir+"/merged_data.csv")


def get_unique_matching_file(expr):
    candidates = glob.glob(expr)
    assert len(candidates) == 1
    return candidates[0]


participants = ["p102"]
data_dir = "rawdata"
pid_info = pd.read_csv("pid.csv")
patch_order_fieldname = "Order (git branch name, case_NUM)"

for participant in participants:
    participant_dir = data_dir + "/" + participant
    data_dirs = glob.glob(participant_dir + "/158*")
    fluorite_logs = glob.glob(participant_dir + "/fluorite/Log*xml")

    # 'fluorite' was frequently misspelled.
    if len(fluorite_logs) == 0:
        fluorite_logs = glob.glob(participant_dir + "/flourite/Log*xml")

    participant_upper_case = participant.upper()
    participant_metadata = pid_info[pid_info["PID"] == participant_upper_case]
    case_order_str = participant_metadata.iloc[0][patch_order_fieldname]
    case_order_list = case_order_str.split(", ")

    assert len(fluorite_logs) == len(data_dirs) == len(case_order_list) == 6

    for trial_index in range(6):
        participant_data_dir = data_dirs[trial_index]
        fluorite_log = fluorite_logs[trial_index]
        case_num_str = case_order_list[trial_index]

        eclipse_log = get_unique_matching_file(participant_data_dir + "/eclipse*xml")
        core_log = get_unique_matching_file(participant_data_dir + "/core*xml")

        trial_num_str = str(trial_index + 1)
        output_dir = "processed_data/"+participant+"/trial_"+trial_num_str

        # Get patch number from case number
        case_num = int(case_num_str)
        patch_num = case_num - 6 if case_num > 6 else case_num
        patch_num_str = str(patch_num)

        # Get annotations file from patch number
        annotation_file = "Annotations/case_"+patch_num_str+"_bug_annotation.json"

        # Write some diagnostic info
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_dir + "/info.txt", "w") as stampfile:
            stampfile.write("Trial number = "+trial_num_str+"\n"+
                            "Case number = "+case_num_str+"\n"+
                            "Patch number = "+patch_num_str+"\n"+
                            "Annotation file = "+annotation_file+"\n"+
                            "Participant = "+participant+"\n"+
                            "FLUORITE Log = "+fluorite_log+"\n"+
                            "IDE Log = "+eclipse_log+"\n"+
                            "Gaze Point Log = "+core_log)

        make_and_process_data_partition(annotation_file, None, fluorite_log, eclipse_log, core_log,
                                        output_dir, compute_aois=False)
