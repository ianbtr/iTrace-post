# iTrace-post
A module (and a bonus script) for processing output from the [iTrace plugin](www.i-trace.org).
Also performs automatic generation of Areas of Interest (AOI's) based on fixation data and
code location.

## Quick Start
Run `setup.py` like this:  
```$ python setup.py install```  
As soon as this completes, you're ready to import the `itrace_post` module into 
your project. Please note that you will need to copy the script `post2aoi.py` if 
you wish to use it in your project. You may also wish to use this script as an 
example when writing a similar script to read output from iTrace.

## Translation of iTrace Files
The `gaze2src` program is a part of the iTrace program suite that performs post-processing 
on raw iTrace data. The resulting data are stored in a tab-separated file and a 
SQL database file. The `post2csv` script in this project reads both these files and produces a 
CSV containing the line and column numbers of subjects' fixations, and assigns each fixation to 
a rectangular AOI.

## AOI Extraction And Assignment
Instead of pixels, the most basic spatial units are individual characters, corresponding to a particular source code file.
This perspective is feasible because iTrace records the line and column numbers associated with a
particular fixation. The position of a single character's cell is defined by zero-indexed line 
and column numbers. The `get_aoi_intersection` function produces a 2D numpy logical array describing 
the intersection between the subjects' gaze and the code in the file. (A single cell in this array 
represents a single character in the file). The rectangular bounding box of each region is considered
an AOI, and the bounding boxes are returned from this function as a JSON-style list, sorted by decreasing
area.

### Generating A Mask From Code
The size of a line of code is identified by its string length, after the removal of trailing newline 
characters and the conversion of all tab characters to 4 spaces. Other leading and trailing whitespace 
characters, such as spaces, are not removed from the code mask. This procedure is inspired by the 
[eyecode](https://github.com/synesthesiam/eyecode) project.

### Generating A Mask From Gaze Data
Gazes' durations are placed in a 2D numpy array, organized by gaze position. This array is smoothed
using Gaussian smoothing, and then a threshold is applied to reveal regions that attracted the 
majority of subjects' gazes. This procedure is inspired by the masking algorithm in the
[iMap](https://github.com/iBMLab/iMap4) project.

## Where This Project Fits With Everything Else
![alt text](img/chart.png)
