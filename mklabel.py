import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import zxingcpp
import dymo
from stuff import stuff

mainfont = ImageFont.truetype("IBMPlexSans-SemiBold.otf", 85)
tinyfont = ImageFont.truetype("IBMPlexSans-SemiBold.otf", 18)

def draw_wrapped_centered(draw, xy, text, max_width):
    x, y = xy

    def w(s):
        return draw.textlength(s, font=mainfont)

    line_h = draw.textbbox((0, 0), "Ag", font=mainfont)[3]
    words = text.split()
    lines = []
    line = ""

    for word in words:
        test = word if not line else line + " " + word
        if w(test) <= max_width:
            line = test
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    y -= (line_h * len(lines)) // 2

    for line in lines:
        draw.text((x, y), line, font=mainfont, fill=0)
        y += line_h

def make_label(code, desc):
    label_size = (1050, 510)

    os.system(f"qrencode --micro -l L -s 1 -o _tmp.png {code}")
    cim = Image.open("_tmp.png").convert("1")
    os.unlink("_tmp.png")
    # assert cim.size == (15, 15), str(cim)
    im = Image.new("1", label_size, 1)
    x = int(im.height * 11 // 10)

    cim = cim.resize((im.height, im.height))
    im.paste(cim, (0, 0))
    draw = ImageDraw.Draw(im)

    available_width = im.width - x
    bbox = draw.textbbox((0, 0), desc, font=mainfont)
    draw_wrapped_centered(draw, (x, im.height // 2), desc, available_width)

    draw.text((x, im.height - 20), code, fill=0, font=tinyfont)

    return im

def embed(im):
    im.save("out.png")
    sheet = Image.new("1", (3100, 670), 1)
    sheet.paste(im, (2050, 160))
    return sheet.transpose(Image.ROTATE_270)

def testsheet():
    sz = (3100, 670)
    im = Image.new("1", sz, 1)
    draw = ImageDraw.Draw(im)
    y0 = sz[1] // 2
    y1 = sz[1]
    for x in range(0, sz[0], 100):
        draw.line([(x, 0), (x, y1)], 0)
        draw.text((x, y0), str(x), fill=0, font=tinyfont)
    for x in range(0, sz[0], 10):
        draw.line([(x, y1 - 100), (x, y1)], 0)
    for y in range(0, sz[1], 10):
        if (y % 100) == 0:
            x = 100
        else:
            x = 50
        draw.line([(0, y), (x, y)], 0)
    (x0, y0, x1, y1) = (2050, 160, 3099, 669)
    draw.line([(x0, y0), (x1, y1)], 0)
    draw.line([(x1, y0), (x0, y1)], 0)
    draw.rectangle([(x0, y0), (x1, y1)], outline = 0)
    return im.transpose(Image.ROTATE_270)

if __name__ == "__main__":
    if 0:
        ims = [embed(make_label("000", "Scanalyzer"))]
    if 0:
        ims = [testsheet()]
    if 1:
        ss = [(n, d) for (n, d) in stuff if d and n in range(136, 999)]
        for (n,d) in ss:
            print(n, d)
        ims = [embed(make_label(str(n), d)) for (n, d) in ss]
    d = dymo.Dymo(open("test.raw", "wb"))
    d.reset()
    for im in ims:
        d.image(im)
