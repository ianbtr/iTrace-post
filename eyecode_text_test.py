"""
Reads a java file and creates AOI's
"""

from eyecode import aoi, plot

with open("MineGenerator.java", "r") as infile:
    code = infile.read()

# Replace tabs with 4 spaces
code = code.replace("\t", " "*4)

# Note: pixel-size of 10pt Consolas on my monitor is 18 x 32 px.
# The line offset in my IDE with my monitor is 6px.
aois = aoi.code_to_aois(code, filename="MineGenerator.java",
    font_size=(18, 32), line_offset=6)

lines = code.split("\n")

# Default font in eclipse is Consolas, size 10.
img = plot.draw_code(lines, font_size=32, line_offset=6)

token_img = plot.draw_rectangles(aois[aois.kind == "token"], img)
token_img.save("tokens.png")

sub_line_img = plot.draw_rectangles(aois[aois.kind == "sub-line"], img)
sub_line_img.save("sub_lines.png")

line_img = plot.draw_rectangles(aois[aois.kind == "line"], img)
line_img.save("lines.png")

names = aois[aois.kind == "line"].name
block_aois = aoi.combine_aois(aois, "line", names, "block", "block 1")
block_img = plot.draw_rectangles(block_aois[block_aois.kind == "block"], img)
block_img.save("block.png")