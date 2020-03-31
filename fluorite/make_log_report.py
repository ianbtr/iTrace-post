"""
Parses the FLUORITE log and gives a report of the timing of a few different categories:
1. "Navigation" (Moving the caret, using the Find command, opening a file)
2. "Editing" (Insert, delete or replace)
3. "Inspection" (Select text, run/debug)
4. "Understanding" (None)
"""

from .phase_change_query import get_phase_number_from_time
import xml.etree.ElementTree

fields = ["p_name", "AOI", "Time (ms after epoch)", "dwell_duration", "phase_number"]


def add_aoi_row(ocsv, p_name, aoi_name, time, duration, phase_num):
    ocsv.writerow({
        "p_name": p_name,
        "AOI": aoi_name,
        "Time (ms after epoch)": time,
        "dwell_duration": duration,
        "phase_number": phase_num
    })


"""
Add rows to a CSV that can be used to generate alpscarf plots representing the FLUORITE log.

logfile_name: The path to the FLUORITE log file
output_csv: An open csv.DictWriter object
p_name: The name of the current participant
"""


def make_fluorite_log_report(logfile_name, output_csv, p_name, phase_change_file, tz_offset_ms):
    tree = xml.etree.ElementTree.parse(logfile_name)
    root = tree.getroot()
    launch_time = int(root.attrib['startTimestamp'])
    current_time = launch_time

    for child in root:
        event_start_time = launch_time + int(child.attrib["timestamp"])
        event_end_time = launch_time + int(child.attrib["timestamp2"]) if "timestamp2" in child.attrib.keys() else None

        participant = p_name[:4]
        bug_number = int(p_name[-1])
        phase_number = get_phase_number_from_time(event_start_time + tz_offset_ms, participant, bug_number, phase_change_file)

        # Add 'Understanding' section between last time and current time
        if current_time < event_start_time:
            add_aoi_row(output_csv, p_name, "Understanding", current_time, event_start_time - current_time, phase_number)
            current_time = event_start_time if not event_end_time else event_end_time

        duration = event_end_time - event_start_time if event_end_time else 1

        add_row_args = lambda name: add_aoi_row(output_csv, p_name, name, event_start_time, duration, phase_number)

        if event_start_time == 1563562215433:
            print("foo")

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