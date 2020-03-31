from fluorite import make_fluorite_log_report, alpscarf_fields
from glob import glob
from csv import DictWriter

data_dir = "raw_data\\Main"

ofile = open("fluorite_log_reports_debug.csv", "w", newline='')
ocsv = DictWriter(ofile, fieldnames=alpscarf_fields)
ocsv.writeheader()

tz_offset = 0

for p_dir in glob(data_dir+"/*"):
    for bug_dir in glob(p_dir+"/P*"):
        try:
            logfile_path = glob(bug_dir + "/*/Log*.xml")[0]
        except IndexError:
            logfile_path = glob(bug_dir + "/Log*.xml")[0]

        split_path = bug_dir.split("\\")

        participant = split_path[2][-3:]
        trial = split_path[3][-1]
        p_name = "P"+participant+"B"+trial

        make_fluorite_log_report(logfile_path, ocsv, p_name, "phase_changes.csv", tz_offset)
