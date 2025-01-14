"""
A set of classes that detect and compile edits to the code.
"""

import os
import json
import copy
import xml.etree.ElementTree

"""
A base class for edit events.

Fields:
    token_start: The index of the first character that is changed
    time_1: The time at which the change began
    repeat: A boolean describing whether or not the change is composed of multiple key events.
            (It is True if multiple key events contribute to the change).
    changed_file: The file that was changed.
    time_2: The time at which the change completed. May or may not be initialized depending on 
            the value of repeat.
"""


class DocumentChange:
    def __init__(self, token_start, start_time, changed_file, **kwargs):
        self.token_start = int(token_start)
        self.time_1 = int(start_time)
        self.repeat = False
        self.changed_file = changed_file

        if "end_time" in kwargs.keys() and kwargs["end_time"] is not None:
            self.time_2 = kwargs["end_time"]
            self.repeat = True


"""
A child class describing insertions.

Fields:
    string_inserted: The string that is inserted.
"""


class InsertionEvent(DocumentChange):
    def __init__(self, token_start=None, start_time=None,
                 string_inserted=None, changed_file=None, **kwargs):
        DocumentChange.__init__(self, token_start, start_time, changed_file, **kwargs)
        self.string_inserted = str(string_inserted)


"""
A child class describing deletions.

Fields:
    token_end: The index of the character that is one past the end of the deletion, prior to the occurrence of the
        deletion.
    string_deleted: The string that is deleted.
"""


class DeletionEvent(DocumentChange):
    def __init__(self, token_start=None, start_time=None,
                 token_end=None, string_deleted=None,
                 changed_file=None, **kwargs):
        DocumentChange.__init__(self, token_start, start_time, changed_file, **kwargs)
        self.token_end = int(token_end)
        self.string_deleted = string_deleted


"""
A child class describing replacements.

Fields:
    token_end: The index of the character that is one past the end of the deletion, prior to the occurrence of the
        deletion.
    replace_with: The string to insert.
"""


class ReplaceEvent(DocumentChange):
    def __init__(self, token_start=None, start_time=None,
                 token_end=None, replace_with=None,
                 changed_file=None, **kwargs):
        DocumentChange.__init__(self, token_start,
                                start_time, changed_file, **kwargs)
        self.token_end = int(token_end)
        self.replace_with = str(replace_with)


"""
A single file's editing timeline

Parameters:
    filename: the name of the file that a history is being recorded for
    initial_functions: A dictionary conforming to the format of a function index (see the relevant example),
        for a particular file. (A complete function index would contain keys for multiple files; this dictionary
        is the result of indexing by one of those keys).
    initial_entities: Similarly, a dictionary conforming to the format of an entity index (see the relevant example),
        for a particular file.
"""


class FileHistory:
    def __init__(self, filename, initial_content,
                 initial_functions=None, initial_entities=None):
        self.initial_functions = initial_functions
        self.initial_entities = initial_entities
        self.filename = str(filename)
        self.initial_content = initial_content
        self.changes = list()

    """
    Gets a snapshot of this file at a particular time stamp.
    Units are in milliseconds.
    Subsequent return values are new function/entity indices.
    """
    def get_snapshot(self, timestamp):
        content = self.initial_content
        functions = copy.deepcopy(self.initial_functions)
        entities = copy.deepcopy(self.initial_entities)
        for change in self.changes:
            if timestamp < change.time_1:
                break

            if type(change) is InsertionEvent:
                content = content[:change.token_start] + \
                    change.string_inserted + content[change.token_start:]

                if functions is not None and '\n' in change.string_inserted:
                    lines_added = change.string_inserted.count("\n")
                    prior_string = content[:change.token_start]
                    line_num_start = prior_string.count("\n")
                    functions = update_functions(functions, line_num_start, lines_added)
                    entities = update_entities(entities, line_num_start, lines_added)

            elif type(change) is DeletionEvent:
                content = content[:change.token_start] + \
                    content[change.token_end:]

                if functions is not None and '\n' in change.string_deleted:
                    lines_removed = change.string_deleted.count("\n")
                    prior_string = content[:change.token_start]
                    line_num_start = prior_string.count("\n")
                    functions = update_functions(functions, line_num_start, -1 * lines_removed)
                    entities = update_entities(entities, line_num_start, -1 * lines_removed)

            elif type(change) is ReplaceEvent:
                string_removed = content[change.token_start: change.token_end + 1]
                content = content[:change.token_start] + \
                    change.replace_with + content[change.token_end:]

                if functions is not None and ('\n' in string_removed or '\n' in change.replace_with):
                    net_lines_added = change.replace_with.count("\n") - string_removed.count("\n")
                    if net_lines_added == 0:
                        continue
                    prior_string = content[:change.token_start]
                    line_num_start = prior_string.count("\n")
                    functions = update_functions(functions, line_num_start, net_lines_added)
                    entities = update_entities(entities, line_num_start, net_lines_added)

            else:
                raise AssertionError("Bad type in change list: "+str(type(change)))

        return content, functions, entities

    """
    Updates the object by passing an XML element representing
    either an insertion or a deletion to this file.
    Guarantees that changes are sorted by starting time.
    """
    def update_history(self, change):
        if type(change) not in [InsertionEvent, DeletionEvent, ReplaceEvent]:
            raise ValueError(
                "Cannot append non-event type " +
                str(type(change))+" to FileHistory object"
            )

        self.changes.append(change)
        self.changes.sort(key=lambda c: c.time_1)


"""
Breaks the log file into several FileHistory objects

Parameters:
    logfile: Relative path to the FLUORITE log file
    
    func_location_file: Relative path to a JSON file describing the INITIAL
        locations of functions in the project. This dataset will be
        regenerated and returned with each call to get_snapshot().
        
    entity_location_file: Similar to the above, but for an entity index.
"""


class ProjectHistory:
    def __init__(self, logfile, func_location_file=None, entity_location_file=None):
        self.logfile = logfile
        self.initial_functions = self.initial_entities = None

        if func_location_file is not None:
            with open(func_location_file) as infile:
                self.initial_functions = json.load(infile)

        if entity_location_file is not None:
            with open(entity_location_file) as infile:
                self.initial_entities = json.load(infile)

        self.project_files = dict()

        self.launch_time = None
        self.line_separator = None

        self.parse_logfile()

    """
    Get a snapshot of a given file at a particular time stamp.
    Returns the entire snapshot as a string, as well as function/entity positions if any.
    """
    def get_snapshot(self, filename, timestamp):
        if filename not in self.project_files.keys():
            raise ValueError(
                "No mention of "+str(filename)+" is "
                "made in the log file "+str(self.logfile)
            )

        else:
            return self.project_files[filename]\
                .get_snapshot(timestamp)

    """
    Parse the log file. (Only performed on construction).
    """
    def parse_logfile(self):
        tree = xml.etree.ElementTree.parse(self.logfile)
        root = tree.getroot()

        # Get time at which the IDE was launched.
        self.launch_time = int(root.attrib['startTimestamp'])

        # Get line separator and un-escape it.
        self.line_separator = root.attrib['lineSeparator']\
            .replace("\\n", "\n")\
            .replace("\\r", "\r")

        if self.line_separator != "\r\n" and self.line_separator != "\n":
            raise NotImplementedError(
                "Line separator not supported: "+root.attrib['lineSeparator'] +
                "\nPlease report this issue."
            )

        # Iterate over logged items:
        current_file = None
        for child in root:

            # Parse FileOpenCommand elements
            if child.tag == "Command" and \
                    child.attrib["_type"] == "FileOpenCommand":
                snapshot_text = None
                for grandchild in child:

                    if grandchild.tag == "filePath":
                        current_file = grandchild.text

                    elif grandchild.tag == "snapshot":
                        if grandchild.text is None:
                            snapshot_text = ""
                        else:
                            snapshot_text = grandchild.text

                if current_file is None:
                    raise ValueError(
                        "Filepath tag not found in Command with attribute _type=FileOpenCommand."
                        " (This is the minimal content for a legal tag of this type)."
                    )

                # Adjust snapshot text to match real text
                if snapshot_text is not None:
                    snapshot_text = snapshot_text.replace("\n", self.line_separator)

                    # Construct FileHistory object from file snapshot and file name
                    short_name = trim_filepath(current_file)
                    short_name_no_ext = trim_extension(short_name)

                    if not self.initial_functions or short_name_no_ext not in self.initial_functions.keys():
                        init_funcs = None
                    else:
                        init_funcs = self.initial_functions[trim_extension(short_name)]

                    if not self.initial_entities or short_name_no_ext not in self.initial_entities:
                        init_entities = None
                    else:
                        init_entities = self.initial_entities[trim_extension(short_name)]

                    self.project_files[short_name] = \
                        FileHistory(short_name, snapshot_text,
                                    initial_functions=init_funcs,
                                    initial_entities=init_entities)

            # Parse DocumentChange elements
            elif child.tag == "DocumentChange":
                if current_file is None:
                    raise ValueError(
                        "Bad format: A DocumentChange element appeared "
                        "before any FileOpenCommand was registered."
                    )

                time_2 = None
                if 'timestamp2' in child.attrib.keys():
                    time_2 = self.launch_time + int(child.attrib['timestamp2'])

                if child.attrib['_type'] == "Delete":
                    sd = child[0].text.replace("\n", self.line_separator)
                    change = DeletionEvent(
                        token_start=int(child.attrib['offset']),
                        start_time=self.launch_time + int(child.attrib['timestamp']),
                        token_end=int(child.attrib['offset']) + int(child.attrib['length']),
                        changed_file=current_file,
                        string_deleted=sd,
                        end_time=time_2
                    )

                elif child.attrib['_type'] == "Insert":
                    si = child[0].text.replace("\n", self.line_separator)
                    change = InsertionEvent(
                        token_start=int(child.attrib['offset']),
                        start_time=self.launch_time + int(child.attrib['timestamp']),
                        string_inserted=si,
                        changed_file=current_file,
                        end_time=time_2
                    )

                elif child.attrib['_type'] == "Replace":
                    rw = child[1].text
                    if rw is not None:
                        rw = rw.replace("\n", self.line_separator)
                    else:
                        rw = ""
                    change = ReplaceEvent(
                        token_start=int(child.attrib['offset']),
                        start_time=self.launch_time + int(child.attrib['timestamp']),
                        token_end=int(child.attrib['offset']) + int(child.attrib['length']),
                        replace_with=rw,
                        changed_file=current_file,
                        end_time=time_2
                    )

                else:
                    continue

                self.project_files[trim_filepath(current_file)].update_history(change)

            else:
                continue  # ELSE: tag is neither of 'DocumentChange' or 'FileOpenCommand'

    """
    Returns a list of change objects for the entire project.
    """

    def get_all_changes(self):
        # Form global change list
        all_changes = list()
        for filehist in self.project_files.values():
            all_changes.extend(filehist.changes)

        return sorted(all_changes, key=lambda c: c.time_1)

    """
    Saves snapshots of all files that were ever opened at target_time.
    The parameters start_time and end_time are for display purposes only.
    They form the name of the output directory, preceded by output_prefix.
    """

    def save_snapshots(self, start_time, end_time, target_time, output_prefix):
        target_dir = output_prefix + "/" + str(start_time) + \
                     "-" + str(end_time) + "/code_files"

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        all_functions, all_entities = dict(), dict()

        for filehist in self.project_files.values():
            short_filename = trim_filepath(filehist.filename)
            fname_no_ext = trim_extension(short_filename)
            snapshot, functions, entities = filehist.get_snapshot(target_time)
            snapshot = snapshot.replace(self.line_separator, "\n")

            with open(target_dir + "/" + short_filename, "w") as ofile:
                ofile.write(snapshot)

            if functions is not None:
                all_functions[fname_no_ext] = copy.deepcopy(functions)

            if entities is not None:
                all_entities[fname_no_ext] = copy.deepcopy(entities)

        if self.initial_functions is not None:
            with open(target_dir + "/functions.json", "w") as ofile:
                json.dump(all_functions, ofile)

        if self.initial_entities is not None:
            with open(target_dir + "/entities.json", "w") as ofile:
                json.dump(all_entities, ofile)


    """
    Save a file timeline. Granularity is finest by default, meaning
    a new timeline frame is created for each edit. To make a different
    granularity, specify 'granularity' as an integer describing milliseconds. 
    This will require that you enter the first and last times you 
    wish to represent.
    """
    def save_timeline(self, directory_path, granularity="finest",
                      first_time=None, last_time=None):
        # Create directory if not already present
        if not os.path.isdir(directory_path):
            os.makedirs(directory_path)

        if granularity is "finest":
            if first_time is None or last_time is None:
                raise ValueError(
                    "Both first_time and last_time must be specified for the given option "
                    "granularity='finest'"
                )
            return self._save_full_timeline(directory_path, int(first_time), int(last_time))

        elif type(granularity) is int:
            self._save_periodic_timeline(directory_path, granularity,
                                         first_time, last_time)

        else:
            raise ValueError(
                "Granularity parameter "+str(granularity)+" is not supported."
            )

    """
    Save timeline at a given granularity
    """
    def _save_periodic_timeline(self, directory_path, time_step, first_time, last_time):
        if first_time is None or last_time is None:
            raise ValueError(
                "Time parameters must be integers representing milliseconds."
            )

        # Get list of time steps
        times = list(range(int(first_time), int(last_time), int(time_step)))

        count = 0
        for i in range(len(times)-1):
            this_time, next_time = times[i:i+2]
            self.save_snapshots(str(count) + "_" + str(this_time), next_time,
                                this_time+1, directory_path)
            count += 1

        self.save_snapshots(str(count) + "_" + str(times[-1]), "inf",
                            times[-1]+1, directory_path)

    """
    Save timeline at finest granularity
    """
    def _save_full_timeline(self, directory_path, first_time, last_time):
        # Get global change list
        all_changes = self.get_all_changes()

        count = 1

        periods = list()

        if len(all_changes) > 0:
            # Save initial change
            self.save_snapshots("0_" + str(first_time), all_changes[0].time_1, 0, directory_path)
            periods.append([first_time, all_changes[0].time_1])
        else:
            self.save_snapshots("0_"+str(first_time), "inf", 0, directory_path)
            return [[first_time, last_time]]

        # Loop through consecutive pairs of changes
        for i in range(len(all_changes)-1):
            this_change, next_change = all_changes[i:i+2]

            try:
                snapshot_start = this_change.time_2
            except AttributeError:
                snapshot_start = this_change.time_1

            snapshot_end = next_change.time_1

            self.save_snapshots(str(count) + "_" + str(snapshot_start),
                                snapshot_end, snapshot_start+1, directory_path)

            periods.append([snapshot_start, snapshot_end])

            if snapshot_end >= last_time:
                return periods

            count += 1

        # Save final state
        try:
            final_time = all_changes[-1].time_2
        except AttributeError:
            final_time = all_changes[-1].time_1

        self.save_snapshots(str(count) + "_" + str(final_time),
                            last_time, final_time+1, directory_path)

        periods.append([final_time, last_time])

        return periods


"""
A pair of utility functions to determine the positions of functions or entities after a change.
"""


def update_functions(functions, first_line, net_added):
    if functions is None:
        return functions

    for name, line_range in functions.items():
        if line_range[0] > first_line:
            line_range[0] += net_added
        if line_range[1] >= first_line:
            line_range[1] += net_added

    return functions


def update_entities(entities, first_line, net_added):
    if entities is None:
        return entities

    for key, val in entities.items():
        for name, line_range in val.items():
            if line_range[0] > first_line:
                line_range[0] += net_added
            if line_range[1] >= first_line:
                line_range[1] += net_added

    return entities


"""
Returns a file's 'short' name (without upper
directories) given the relative path.
"""


def trim_filepath(name):
    return name.split("\\")[-1].split("/")[-1]


"""
Removes the filename extension, if one exists.
"""


def trim_extension(name):
    return os.path.splitext(name)[0]
