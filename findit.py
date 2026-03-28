import os
import sys
import json
from typing import Iterable, Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageChops
import numpy as np
import zxingcpp

from stuff import stuff_dict
from genpage import html_page

Pt = Tuple[float, float]

def _order_ccw(pts: np.ndarray) -> np.ndarray:
    """Order 2D points counterclockwise (stable for convex sets)."""
    c = pts.mean(axis=0)
    ang = np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0])
    return pts[np.argsort(ang)]

def _homography_from_4pts(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """
    DLT homography: src (u,v) -> dst (x,y), each 4x2.
    Returns 3x3 H such that [x,y,1]^T ~ H [u,v,1]^T
    """
    A = []
    for (u, v), (x, y) in zip(src, dst):
        A.append([ u, v, 1, 0, 0, 0, -x*u, -x*v, -x ])
        A.append([ 0, 0, 0, u, v, 1, -y*u, -y*v, -y ])
    A = np.asarray(A, dtype=float)
    _, _, Vt = np.linalg.svd(A)
    h = Vt[-1, :]
    H = h.reshape(3, 3)
    return H / H[2, 2]

def _apply_homography(H: np.ndarray, pts: np.ndarray) -> np.ndarray:
    """Apply H to Nx2 points."""
    ones = np.ones((pts.shape[0], 1), dtype=float)
    p = np.hstack([pts, ones])              # Nx3
    q = (H @ p.T).T                          # Nx3
    q = q[:, :2] / q[:, 2:3]
    return q

font = ImageFont.load_default()

def corners(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]

def label_corners(barcode_corners):
    square_uv = corners(66, 66, 441, 441)
    rect_uv = corners(0, 0, 1050, 510)

    square_xy = np.asarray(barcode_corners, dtype=float)
    square_uv = np.asarray(list(square_uv), dtype=float)
    rect_uv   = np.asarray(list(rect_uv),   dtype=float)
    H = _homography_from_4pts(square_uv, square_xy)
    rect_xy = _apply_homography(H, rect_uv)
    return [tuple(map(int, p)) for p in rect_xy]

def findit(term):
    fn = "b.jpg"
    im = Image.open(fn)
    barcodes = zxingcpp.read_barcodes(im)
    print(f"{len(barcodes)} barcodes found")
    dr = ImageDraw.Draw(im)
    bcdb = {}
    for bc in barcodes:
        # print(f"{bc.text} {bc.position}")
        p = bc.position
        vx = [(pt.x, pt.y) for pt in (p.top_left, p.top_right, p.bottom_right, p.bottom_left)]
        dr.polygon(vx, outline = "red", width = 1)
        dr.text(vx[2], bc.text, fill=(0, 0, 0), font=font)
        bcdb[int(bc.text)] = (fn, label_corners(vx))
    matches = []
    matte = Image.new("L", im.size, 85)
    dr = ImageDraw.Draw(matte)
    for code in bcdb:
        if term.lower() in stuff_dict[code].lower():
            (fn, vx) = bcdb[code]
            dr.polygon(vx, fill = 255)

    found = ImageChops.multiply(im, matte.convert("RGB"))
    found.save("out.png")

def layout_images(images, height):
    laid_out = []
    for im in images:
        sf = height / im.height
        sim = im.resize((int(im.width * sf), height))
        laid_out.append((im, sf, sim))

    images_per_row = 4
    row_widths = []
    for i in range(0, len(laid_out), images_per_row):
        row = laid_out[i:i + images_per_row]
        row_widths.append(sum(sim.width for (_, _, sim) in row))

    width = max(row_widths, default=0)
    rows = (len(laid_out) + images_per_row - 1) // images_per_row
    main = Image.new("RGB", (width, rows * height))
    print(f"{main=}")

    positioned = []
    x0 = 0
    y0 = 0
    for i, (im, sf, sim) in enumerate(laid_out):
        if i > 0 and i % images_per_row == 0:
            x0 = 0
            y0 += height
        main.paste(sim, (x0, y0))
        positioned.append((im, sf, sim, x0, y0))
        x0 += sim.width
    main.save("main.png")

    return main, positioned

def make_page():
    ims = []
    h = 600
    dir = "snap250327"
    ff = sorted([dir + "/" + f for f in os.listdir(dir) if f.endswith(".jpg")])

    for fn in ff:
        im = Image.open(fn)
        ims.append((fn, im))

    main, laid_out = layout_images((im for (_, im) in ims), h)
    atlas = []
    tiles = []
    code_to_files = {}
    for ((fn, im), (_, sf, sim, x0, y0)) in zip(ims, laid_out):
        tiles.append({
            "name": fn,
            "x0": x0,
            "y0": y0,
            "x1": x0 + sim.width,
            "y1": y0 + sim.height,
        })
        barcodes = zxingcpp.read_barcodes(im)
        bcdb = {}
        for bc in barcodes:
            p = bc.position
            vx = [(pt.x, pt.y) for pt in (p.top_left, p.top_right, p.bottom_right, p.bottom_left)]
            bcdb[int(bc.text)] = (fn, label_corners(vx))
        for code in bcdb:
            (fn, vx) = bcdb[code]
            code_to_files.setdefault(code, set()).add(fn)
            vx = [(x0 + int(x * sf), y0 + int(y * sf)) for (x, y) in vx]
            if code in stuff_dict:
                atlas.append((stuff_dict[code].lower(), vx))

    with open("index.html", "w") as f:
        f.write(html_page(main, json.dumps(atlas), tiles=tiles))

    labeled_codes = set(stuff_dict)
    found_labeled_codes = labeled_codes & set(code_to_files)
    missing_codes = sorted(labeled_codes - found_labeled_codes)
    duplicate_codes = sorted(
        code for code, files in code_to_files.items()
        if code in stuff_dict and len(files) > 1
    )

    print("Missing labels:")
    for code in missing_codes:
        print(f"  {code}: {stuff_dict[code]}")
    if not missing_codes:
        print("  none")

    print("Duplicate labels:")
    for code in duplicate_codes:
        files = ", ".join(sorted(code_to_files[code]))
        print(f"  {code}: {stuff_dict[code]} [{files}]")
    if not duplicate_codes:
        print("  none")

if __name__ == "__main__":
    # findit("")
    make_page()
