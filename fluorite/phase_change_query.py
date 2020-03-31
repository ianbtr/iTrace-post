"""
A set of calculations of AFD and other typical & extendable eye-tracking metrics
"""

import os
import csv
import pandas as pd
import numpy as np
from math import sqrt


class PhaseQueryError(BaseException):
    pass


"""
Return a subset of fixation_data that corresponds to the given phase.
Phases are 1-indexed.
    Phase 1: times before 1st 10 on-target fixations
    Phase 2: times after 1st 10 on-target fixations, but before the 1st edit
    Phase 3: times after 1st edit
"""


def query_phase_change_data(which_phase, which_participant, which_bug, phase_data_path, fixation_data_path):
    phase_data = pd.read_csv(phase_data_path)
    fixation_data = pd.read_csv(fixation_data_path)

    # Filtering out null AOI's
    fixation_data = fixation_data[fixation_data.AOI != -1]

    assert fixation_data[fixation_data.AOI == -1].empty

    trial_info = phase_data[(phase_data["Participant"] == which_participant) &
                            (phase_data["Trial"] == which_bug)]

    if trial_info.empty:
        raise PhaseQueryError(
            "Did not find bug "+str(which_bug)+" for participant "+str(which_participant)
        )

    phase1_end = trial_info["Time of first 10 consecutive on-target fixations (ms after epoch)"].values[0]

    phase2_end = trial_info["Time of 1st significant edit (ms after epoch)"].values[0]

    if which_phase == 1:
        try:
            phase1_end_int = int(phase1_end)
        except ValueError:
            return fixation_data

        return fixation_data[fixation_data["fix_time"] < phase1_end_int]

    elif which_phase == 2:
        try:
            phase1_end_int = int(phase1_end)
        except ValueError:
            raise PhaseQueryError(
                "Phase 2 does not exist because phase 1 does not terminate"
            )

        try:
            phase2_end_int = int(phase2_end)
        except ValueError:
            return fixation_data[fixation_data["fix_time"] >= phase1_end_int]

        return fixation_data[(fixation_data["fix_time"] >= phase1_end_int) &
                             (fixation_data["fix_time"] < phase2_end_int)]

    elif which_phase == 3:
        try:
            phase2_end_int = int(phase2_end)
        except ValueError:
            raise PhaseQueryError(
                "Phase 3 does not exist because phase 2 does not terminate"
            )

        return fixation_data[fixation_data["fix_time"] >= phase2_end_int]

    raise ValueError(
        "Phase number must be 1, 2 or 3"
    )


def get_phase_number_from_time(time, which_participant, which_bug, phase_data_path):
    phase_data = pd.read_csv(phase_data_path)

    trial_info = phase_data[(phase_data["Participant"] == which_participant) &
                            (phase_data["Trial"] == which_bug)]

    if trial_info.empty:
        raise PhaseQueryError(
            "Did not find bug " + str(which_bug) + " for participant " + str(which_participant)
        )

    phase1_end = trial_info["Time of first 10 consecutive on-target fixations (ms after epoch)"].values[0]

    phase2_end = trial_info["Time of 1st significant edit (ms after epoch)"].values[0]

    num_phases = 1

    phase1_end_int = phase2_end_int = None

    try:
        phase1_end_int = int(phase1_end)
        num_phases = 2
        phase2_end_int = int(phase2_end)
        num_phases = 3
    except ValueError:
        pass

    if num_phases >= 2 and abs(time - phase1_end_int) >= 3600 * 1000:
        raise Warning("The given time is more than an hour off from candidate phase times. "
                      "Maybe you forgot to perform a timezone conversion?")

    if num_phases == 1:
        return 1

    elif num_phases == 2:
        assert phase1_end_int
        return 1 if time < phase1_end_int else 2

    elif num_phases == 3:
        assert phase1_end_int
        assert phase2_end_int
        if time < phase1_end_int:
            return 1
        elif time < phase2_end_int:
            return 2
        else:
            return 3

    else:
        raise ValueError("num_phases was "+str(num_phases))