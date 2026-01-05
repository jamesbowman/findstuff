from __future__ import annotations

import base64
import html
import io
from typing import Optional
from PIL import Image


quad_js = "[[753, 697], [111, 97], [111, 69], [753, 69]]"

js = """
(function() {
  const quad = """ + quad_js + """; // [[x,y],...], in original image pixel coords
  const box = document.getElementById('searchBox');
  const poly = document.getElementById('quad');

  function setPolygonPoints() {
    poly.setAttribute('points', quad.map(p => p[0] + ',' + p[1]).join(' '));
  }

  // Expects:
  //   - global bcdb = [[name, [[x,y],[x,y],[x,y],[x,y]]], ...]
  //   - <svg id="overlay" viewBox="0 0 W H"> sitting over the image
  // Creates/updates <polygon class="bc-hit"> elements to highlight matches.
  
  function highlightBcdb(searchString) {
    const s = (searchString ?? "").trim().toLowerCase();
    const overlay = document.getElementById("overlay");
    if (!overlay) return;
  
    // Nuke previous highlights
    overlay.querySelectorAll("polygon.bc-hit").forEach(p => p.remove());
  
    // Helper: build polygon points string
    const ptsStr = (quad) => quad.map(p => `${p[0]},${p[1]}`).join(" ");
  
    for (const [name, quad] of (window.bcdb || [])) {
      const nm = String(name).toLowerCase();
      const ok = (!s) || nm.includes(s);
      if (!ok) continue;
  
      const poly = document.createElementNS("http://www.w3.org/2000/svg", "polygon");
      poly.setAttribute("class", "bc-hit");
      poly.setAttribute("points", ptsStr(quad));
      poly.setAttribute("vector-effect", "non-scaling-stroke");
      poly.setAttribute("fill", "rgba(255,235,59,0.18)");
      poly.setAttribute("stroke", "rgba(255,59,59,0.95)");
      poly.setAttribute("stroke-width", "3");
      poly.setAttribute("stroke-linejoin", "round");
  
      // Optional tooltip
      poly.appendChild(document.createElementNS("http://www.w3.org/2000/svg", "title"))
          .textContent = name;
  
      overlay.appendChild(poly);
    }
  }

  // Highlight quad iff there's any non-whitespace text
  function updateHighlight() {
    highlightBcdb(box.value);
  }

  // Initialize
  setPolygonPoints();
  updateHighlight();

  // Update on any input
  box.addEventListener('input', updateHighlight);
})();
"""

def html_page(
    pil_img: Image.Image,
    bcdb,
    quad_xy: Iterable[Pt] = ((753, 697), (111, 97), (111, 69), (753, 69)),
    *,
    title: str = "findstuff",
    placeholder: str = "Type to highlight…",
    input_value: str = "",
    image_alt: str = "Inlined image",
    image_max_width_px: int = 1920,
    background: str = "#0b0c10",
    foreground: str = "#e8e9ed",
) -> str:
    """
    Self-contained HTML with:
      - inline CSS
      - PIL image embedded as data: URL
      - a search box at top
      - an SVG overlay that highlights `quad_xy` whenever the input has any text

    quad_xy is in *image pixel coordinates* (same coordinate system as the original image).
    """
    # Encode image (PNG) as data URL
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG", optimize=True)
    png_b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    data_url = f"data:image/png;base64,{png_b64}"

    w, h = pil_img.size

    # Sanitize strings
    esc_title = html.escape(title, quote=True)
    esc_ph = html.escape(placeholder, quote=True)
    esc_val = html.escape(input_value, quote=True)
    esc_alt = html.escape(image_alt, quote=True)

    # Quad as JS array literal [[x,y],...]
    quad = list(quad_xy)
    if len(quad) != 4:
        raise ValueError("quad_xy must have exactly 4 points")
    quad_js = "[" + ",".join(f"[{float(x):.6g},{float(y):.6g}]" for x, y in quad) + "]"

    image_max_width_px = max(1, int(image_max_width_px))

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{esc_title}</title>
</head>
<body style="
  margin:0;
  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji','Segoe UI Emoji';
  background:{background};
  color:{foreground};
">
  <div style="
    position:sticky;
    top:0;
    z-index:10;
    background:rgba(0,0,0,0.55);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255,255,255,0.10);
  ">
    <div style="
      max-width:{image_max_width_px}px;
      margin:0 auto;
      padding:14px 16px;
      display:flex;
      gap:10px;
      align-items:center;
    ">
      <div style="font-weight:600; letter-spacing:0.2px; opacity:0.95;">
        {esc_title}
      </div>
      <div style="flex:1;"></div>
      <input
        id="searchBox"
        type="search"
        value="{esc_val}"
        placeholder="{esc_ph}"
        aria-label="Search"
        style="
          width:min(520px, 65vw);
          padding:10px 12px;
          border-radius:10px;
          border:1px solid rgba(255,255,255,0.14);
          background:rgba(255,255,255,0.06);
          color:{foreground};
          outline:none;
          font-size:14px;
        "
      />
    </div>
  </div>

  <main style="max-width:{image_max_width_px}px; margin:0 auto; padding:18px 16px 28px;">
    <div id="stage" style="
      position:relative;
      border-radius:16px;
      overflow:hidden;
      border:1px solid rgba(255,255,255,0.12);
      background: rgba(255,255,255,0.03);
      box-shadow: 0 10px 40px rgba(0,0,0,0.35);
    ">
      <img
        id="img"
        src="{data_url}"
        alt="{esc_alt}"
        style="display:block; width:100%; height:auto;"
      />
      <!-- Overlay is SVG so it scales with the image -->
      <svg
        id="overlay"
        viewBox="0 0 {w} {h}"
        preserveAspectRatio="none"
        style="
          position:absolute;
          inset:0;
          width:100%;
          height:100%;
          pointer-events:none;
        "
      >
        <polygon
          id="quad"
          points=""
          style="
            display:none;
            fill: rgba(255, 235, 59, 0.18);
            stroke: rgba(255, 235, 59, 0.95);
            stroke-width: 6;
            vector-effect: non-scaling-stroke;
          "
        />
      </svg>
    </div>
  </main>

  <script>
bcdb = {bcdb};
{js}
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    fn = "IMG_3528.jpg"
    im = Image.open(fn).resize((1000, 1000))
    with open("index.html", "w") as f:
        f.write(html_page(im))
