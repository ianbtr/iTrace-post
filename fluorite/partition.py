"""
These functions allow you to partition a dataset into periods where a particular file was not being edited.

This may be useful for processing eye-tracking data, or other diagnostic information that was gathered during
the session.
"""

import datetime
import pandas as pd
import numpy as np
import glob
import os
import xml.etree.ElementTree

"""
A partitioner for gaze data.
"""

try:
    EPOCH = datetime.datetime.fromtimestamp(0)
except OSError:
    EPOCH = datetime.datetime.utcfromtimestamp(0)

def date_to_epoch(date_str):
    return (datetime.datetime.strptime(date_str[:-6], "%Y-%m-%dT%H:%M:%S.%f") - EPOCH) \
            .total_seconds() * 1000

class GazeDataPartition:
    def __init__(self, data_filename, offset_ms):
        self.files = dict()
        self.data_filename = data_filename
        self.data = None
        self.partition_count = None
        self.first_time = None
        self.last_time = None
        self.read_xml_data(data_filename, offset_ms)

    def read_xml_data(self, plugin_filename, offset_ms):  # TODO this part is kinda slow
        # Read plugin file
        tree = xml.etree.ElementTree.parse(plugin_filename)
        root = tree.getroot()
        gazes = root[1]

        df_dict = {"fix_time": [], "row_num": []}

        index = 0
        for response in gazes:
            df_dict["fix_time"].append(response.attrib['timestamp'])
            df_dict["row_num"].append(index)
            index += 1

        self.data = pd.DataFrame.from_dict(df_dict)

        # Create epoch time column
        self.data["sys_time"] = list(map(
            lambda dt_str: date_to_epoch(dt_str) + offset_ms,
            self.data["fix_time"]
        ))

        self.first_time = self.data["sys_time"].iloc[0]
        self.last_time = self.data["sys_time"].iloc[-1]

    """
    Similar to the normal behavior as create_partition, but with custom time steps
    """
    def _create_custom_partition(self, time_periods):
        count = 0
        for time_1, time_2 in time_periods:
            region = (self.data["sys_time"] >= time_1) & (self.data["sys_time"] < time_2)

            if not any(list(region)):
                continue

            self.data.loc[region, "Partition"] = int(count)
            count += 1

        self.partition_count = int(self.data["Partition"].dropna().max()) + 1

    """
    If used in conjunction with a saved timeline, these time parameters
    should align with the timeline.
    """
    def create_partition(self, period=None, num_parts=None, time_periods=None):
        if not sum(map(bool, [period, num_parts, time_periods])) == 1:
            raise ValueError(
                "Exactly one parameter ('period' or 'num_parts' or 'time_periods') should be specified"
            )

        if time_periods is not None:
            self._create_custom_partition(time_periods)
            return
        else:
            if period is not None:
                times = list(range(int(self.first_time), int(self.last_time), period))
            else:
                times = np.linspace(self.first_time, self.last_time, num_parts + 1)
                times = list(map(int, times))

        count = 0
        for i in range(len(times)-1):
            time_1, time_2 = times[i:i+2]
            self.data.loc[
                (self.data["sys_time"] >= time_1) &
                (self.data["sys_time"] < time_2),
                "Partition"
            ] = count
            count += 1

        if period is not None:
            self.data.loc[
                self.data["sys_time"] >= times[-1],
                "Partition"
            ] = count

        self.partition_count = self.data["Partition"].max() + 1

        return times[1] - times[0]

    """
    format="xml":
        output_name should name a directory where partitioned XML files can go.
        If this directory was created by the reader module, this function will write
        plugin files to the appropriate subdirectories.
    format="csv":
        save the dataframe to a CSV, with the name of the file being output_name.
    """
    def save_partition(self, output_name, formatting="xml"):
        if formatting is "csv":
            self.data.to_csv(output_name)
        elif formatting is "xml":
            infile = open(self.data_filename, "r")
            xml_lines = infile.readlines()
            infile.close()

            first_line = xml_lines.index("<gazes>\n") + 1
            suffix_line = xml_lines.index("</gazes>\n")

            for i in range(int(self.partition_count)):
                data_part = self.data[self.data["Partition"] == i]
                first_row = data_part.iloc[0]["row_num"]
                last_row = data_part.iloc[-1]["row_num"]
                lines_to_write = xml_lines[first_line + first_row: first_line + last_row]

                # Find directory to write to
                existing_partition = glob.glob(output_name+"/"+str(i)+"_*-*")

                try:
                    dir_name = existing_partition[0]
                except IndexError:
                    dir_name = output_name+"/"+str(i)
                    if not os.path.isdir(dir_name):
                        os.makedirs(dir_name)

                with open(dir_name+"/plugin_log.xml", "w") as ofile:
                    ofile.writelines(xml_lines[:first_line])
                    ofile.writelines(lines_to_write)
                    ofile.writelines(xml_lines[suffix_line:])
