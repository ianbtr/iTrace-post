# Generate AOI's from a screenshot of the Minesweeper GUI

import pandas
from eyecode import aoi, plot
from PIL import Image

img = Image.open("code.png")
aois = aoi.find_rectangles(img)

print(aois)

line_aois = aois[aois.kind == "line"]
sub_line_aois = aois[aois.kind == "sub-line"]
token_aois = aois[aois.kind == "token"]

pl = plot.draw_rectangles(line_aois, img)
pl.save("lines.png")

pl2 = plot.draw_rectangles(sub_line_aois, img)
pl2.save("sub_lines.png")

pl3 = plot.draw_rectangles(token_aois, img)
pl3.save("tokens.png")

# Conclusion: Image parsing will not work on our code.