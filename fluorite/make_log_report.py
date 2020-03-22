"""
Parses the FLUORITE log and gives a report of the timing of a few different categories:
1. "Navigation" (Moving the caret, using the Find command, opening a file)
2. "Editing" (Insert, delete or replace)
3. "Inspection" (Select text, run/debug)
4. "Understanding" (None)
"""

from csv import DictWriter
import xml.etree.ElementTree

fields = ["p_name", "AOI", "dwell_duration"]


def add_aoi_row(ocsv, p_name, aoi_name, duration):
    ocsv.writerow({
        "p_name": p_name,
        "AOI": aoi_name,
        "dwell_duration": duration
    })


"""
Add rows to a CSV that can be used to generate alpscarf plots representing the FLUORITE log.

logfile_name: The path to the FLUORITE log file
output_csv: An open csv.DictWriter object
p_name: The name of the current participant
"""


def make_fluorite_log_report(logfile_name, output_csv, p_name):
    tree = xml.etree.ElementTree.parse(logfile_name)
    root = tree.getroot()
    current_time = 0

    for child in root:
        event_start_time = int(child.attrib["timestamp"])
        event_end_time = int(child.attrib["timestamp2"]) if "timestamp2" in child.attrib.keys() else None

        # Add 'Understanding' section between last time and current time
        if current_time < event_start_time:
            add_aoi_row(output_csv, p_name, "Understanding", event_start_time - current_time)
            current_time = event_start_time if not event_end_time else event_end_time

        duration = event_end_time - event_start_time if event_end_time else 1

        add_row_args = lambda name: add_aoi_row(output_csv, p_name, name, duration)

        if child.tag == "DocumentChange":
            add_row_args("Editing")
        elif child.tag == "Command":
            cmd_type = child.attrib["_type"]
            if cmd_type in ["MoveCaretCommand", "FindCommand", "FileOpenCommand"]:
                add_row_args("Navigation")
            elif cmd_type in ["SelectTextCommand", "RunCommand"]:
                add_row_args("Inspection")
        else:
            add_row_args("Understanding")