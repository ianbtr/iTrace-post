"""
USAGE: <python> aoi_intersection.py <image width> <image height> <code filepath>
            <font size x> <font size y> <font vertical spacing> <x offset> <y offset>
            [line|token] <gaze data file> <x field> <y field> <Duration field>
            <Smoothing> <Threshold>
"""

import warnings
warnings.filterwarnings("ignore")

import sys
import json
import numpy as np
import matplotlib.pyplot as plt
from structs import Rect
from scipy.ndimage import label
from gaze_aoi import generate_gaze_aois
from code_aoi import generate_code_aois
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

if len(sys.argv) != 16:
    print("USAGE: <python> aoi_intersection.py <image width> <image height> <code filepath> "
            "<font size x> <font size y> <font vertical spacing> <x offset> <y offset> "
            "[line|token] <gaze data file> <x field> <y field> <Duration field>"
            "<Smoothing> <Threshold>")
    exit(1)

# Validate image dimensions
img_width, img_height = sys.argv[1:3]
for item in img_width, img_height:
    try: x = int(item)
    except ValueError as e:
        print("image dimensions must be integers")
        raise e
img_width, img_height = int(sys.argv[1]), int(sys.argv[2])

# Compute code mask
code_mask = generate_code_aois(img_width, img_height, *(sys.argv[3:10]))
#plt.imshow(code_mask)
#plt.savefig("code_mask.png", dpi=200)

# Compute gaze mask
gaze_mask = generate_gaze_aois(img_width, img_height, *(sys.argv[10:]))
#plt.imshow(gaze_mask)
#plt.savefig("gaze_mask.png", dpi=200)

# Merge masks
mask_intersection = np.logical_and(code_mask, gaze_mask)

# Identify regions
all_labels, num_features = label(mask_intersection)

# Create rectangles
rectangles = list()
#fig_rectangles = list()
for label in range(1, num_features+1):
    row_occurrences, col_occurrences = np.where(all_labels == label)
    left_extent = min(col_occurrences)
    right_extent = max(col_occurrences)
    top_extent = min(row_occurrences)
    bottom_extent = max(row_occurrences)

    rectangles.append(Rect(left_extent, right_extent,
                           top_extent, bottom_extent))

"""
    fig_rectangles.append(Rectangle((left_extent, top_extent),
                                    right_extent - left_extent,
                                    bottom_extent - top_extent,
                                    fill=False))


fig, ax = plt.subplots(1)
pc = PatchCollection(fig_rectangles, alpha=0.5, edgecolor='w')
ax.add_collection(pc)
plt.imshow(all_labels, cmap='Spectral')
plt.savefig('rects.png', dpi=200)
"""

# Dump rectangles in order of area
rectangles.sort(key=lambda rect: rect.area(), reverse=True)
rect_dict = list(map(lambda rect: rect.as_dict(), rectangles))
print(json.dumps(rect_dict))