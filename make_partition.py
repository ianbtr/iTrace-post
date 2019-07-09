"""
An example script (TODO make a notebook too.)
"""

import os
import glob
import subprocess
from subprocess import DEVNULL
from fluorite import ProjectHistory, GazeDataPartition
from itrace_post import post_to_aoi

# Specifies a branch of the MineSweeper code
WHICH_BUG = "bug2"

print("Partitioning data...")

# Create a ProjectHistory object from a Fluorite log file
phist = ProjectHistory("fluorite_log.xml")

# In our timezone at least, the time iTrace records is one hour behind that of Fluorite.
time_offset = -1*3600*1000

# Create a DataPartition from the
data_part = GazeDataPartition("eclipse_log.xml", time_offset)

# Specify the length of a time segment and separate the data
num_parts = 10
time_delta = data_part.create_partition(num_parts=num_parts)

# Save a corresponding file timeline
phist.save_timeline("timeline", granularity=time_delta, first_time=data_part.first_time,
                    last_time=data_part.last_time)

# Save partitioned data. This will save files to the timeline directories.
data_part.save_partition("timeline")

# All calls to gaze2src can use the same core file
core_fpath = "core_log.xml"

# Each folder in the "timeline" directory should now have enough data to run srcml, gaze2src and iTrace-post.
print("Running gaze2src and generating AOIs...")

dirs = os.listdir("timeline")

for sub_dir in dirs:
    print("\t"+sub_dir)
    prefix = "timeline/"+sub_dir

    # Create a tarball of code files
    subprocess.run(["tar", "-czf", prefix+"/src.tar.gz", prefix+"/code_files"],
                   stdout=DEVNULL, stderr=DEVNULL)

    # Run srcml
    subprocess.run(["srcml", prefix+"/src.tar.gz", "-o", prefix+"/src.xml"],
                   stdout=DEVNULL, stderr=DEVNULL)

    # Run gaze2src TODO allow external configuration of gaze2src and iTrace-post parameters
    subprocess.run(["gaze2src", core_fpath, prefix+"/plugin_log.xml", prefix+"/src.xml",
                    "-f", "ivt", "-v 45", "-u 1", "-o", prefix+"/gaze2src"],
                   stdout=DEVNULL, stderr=DEVNULL)

    # Run iTrace-post
    itrace_prefix = prefix + "/gaze2src"
    fixations_tsv = glob.glob(itrace_prefix + "/fixations*.tsv")[0]
    fixations_db = glob.glob(itrace_prefix + "/rawgazes*.db3")[0]

    post_to_aoi(fixations_db, fixations_tsv, prefix+"/code_files",
                prefix+"/post2aoi", 5.0, 0.01, func_dict="comments_and_functions_"+WHICH_BUG+".json")

    unwanted_files = glob.glob(prefix + "/post2aoi/*.java.csv")
    unwanted_files.extend(glob.glob(prefix + "/post2aoi/*.java_AOI.csv"))
    unwanted_files.extend(glob.glob(prefix + "/gaze2src/*"))
    unwanted_files.extend(glob.glob(prefix + "/*.tar.gz"))
    unwanted_files.extend(glob.glob(prefix + "/plugin_log.xml"))
    unwanted_files.extend(glob.glob(prefix + "/src.xml"))

    for file in unwanted_files:
        os.remove(file)

    os.rmdir(prefix + "/gaze2src")
