import os
import sys
from typing import Iterable, Tuple, List

from PIL import Image, ImageDraw, ImageFont, ImageChops
import numpy as np
import zxingcpp

from stuff import stuff_dict

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
    fn = "IMG_3528.jpg"
    im = Image.open(fn)
    barcodes = zxingcpp.read_barcodes(im)
    print(f"{len(barcodes)} barcodes found")
    dr = ImageDraw.Draw(im)
    bcdb = {}
    for bc in barcodes:
        # print(f"{bc.text} {bc.position}")
        p = bc.position
        vx = [(pt.x, pt.y) for pt in (p.top_left, p.top_right, p.bottom_right, p.bottom_left)]
        dr.polygon(vx, outline = "red")
        dr.text(vx[2], bc.text, fill=(0, 0, 0), font=font)
        bcdb[int(bc.text)] = (fn, label_corners(vx))
    print(bcdb)
    matches = []
    matte = Image.new("L", im.size, 85)
    dr = ImageDraw.Draw(matte)
    for code in bcdb:
        if term.lower() in stuff_dict[code].lower():
            (fn, vx) = bcdb[code]
            dr.polygon(vx, fill = 255)

    found = ImageChops.multiply(im, matte.convert("RGB"))
    found.save("out.png")

if __name__ == "__main__":
    findit(sys.argv[1])
