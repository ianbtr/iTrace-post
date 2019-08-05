"""
Converts plugin logs so that they can be ingested by Ogama.
"""

import xml.etree.ElementTree as xtree
from fluorite import date_to_epoch
import pandas as pd
import glob

output_dir = "ogama_inputs"
raw_data_dir = "raw_data"
trials_dir = "trials_files"

raw_data_sources = glob.glob(raw_data_dir+"/*/P*bug*")

time_offset = 4 * 3600 * 1000

def to_event_time(unix_time, data):
    index = abs(data['unix_time_ms'] - unix_time).idxmin()
    return data.loc[index, 'tracker_time_us']

# Create an Ogama-importable CSV and Trials.txt file for each source.
for source in raw_data_sources:

    # Read and translate data from the plugin log
    try:
        plugin_logfile = glob.glob(source+"/*/eclipse*")[0]
    except IndexError:
        continue

    bug_number = source.split("-")[-1]
    subject = "-".join(source.split("\\")[-1].split("-")[-3:-1])

    try:
        trials_file = glob.glob(trials_dir+"/"+subject+"*"+bug_number+"*Trials.txt")[0]
    except IndexError:
        continue

    output_filepath = output_dir+"/"+subject+"_"+bug_number+"_ogama.csv"

    tree = xtree.parse(plugin_logfile)
    root = tree.getroot()
    gazes = root[1]

    df_dict = {
        "unix_time_ms": [],
        "tracker_time_us": [],
        "fix_x": [],
        "fix_y": []
    }

    for response in gazes:
        df_dict['unix_time_ms'].append(
            date_to_epoch(response.attrib['timestamp']) + time_offset)
        df_dict['tracker_time_us'].append(int(response.attrib['event_time'])/1000)
        df_dict['fix_x'].append(response.attrib['x'])
        df_dict['fix_y'].append(response.attrib['y'])

    data = pd.DataFrame.from_dict(df_dict).astype(
        {'unix_time_ms': 'int64', 'tracker_time_us': 'int64'})

    data = data.drop_duplicates(subset='tracker_time_us')

    data.to_csv(output_filepath, index=False)

    # Create Trials file for tracker times
    trials_data = pd.read_csv(trials_file)

    if "EventTime_us" in trials_data.columns:
        continue

    trials_data["EventTime_us"] = \
        list(map(lambda time: to_event_time(time, data),
                trials_data["StartTime"]))

    trials_data.to_csv(trials_dir+"/"+subject+"_"+bug_number+"_Trials.txt", index=False)