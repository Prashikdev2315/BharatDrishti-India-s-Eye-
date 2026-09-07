from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

# ── Palette ──────────────────────────────────────────────────────────────────
BG      = RGBColor(0x0D, 0x0D, 0x1A)   # deep navy-black
SAFFRON = RGBColor(0xFF, 0x99, 0x33)   # Indian saffron
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
LGREY   = RGBColor(0xCC, 0xCC, 0xCC)
DGREY   = RGBColor(0x2A, 0x2A, 0x3E)   # card bg
GREEN   = RGBColor(0x4C, 0xAF, 0x50)
RED     = RGBColor(0xEF, 0x53, 0x50)

W, H = Inches(13.333), Inches(7.5)     # 16:9

prs = Presentation()
prs.slide_width  = W
prs.slide_height = H

blank_layout = prs.slide_layouts[6]    # completely blank

# ── Helpers ───────────────────────────────────────────────────────────────────

def add_slide():
    s = prs.slides.add_slide(blank_layout)
    bg = s.background.fill
    bg.solid()
    bg.fore_color.rgb = BG
    return s

def box(slide, x, y, w, h, fill=None, line=None):
    shape = slide.shapes.add_shape(1, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.line.fill.background()
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = line
        shape.line.width = Pt(1.5)
    else:
        shape.line.fill.background()
    return shape

def txbox(slide, text, x, y, w, h,
          size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT,
          wrap=True):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = wrap
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return tb

def heading(slide, text, y=0.25):
    txbox(slide, text, 0.4, y, 12.5, 0.7,
          size=32, bold=True, color=SAFFRON, align=PP_ALIGN.LEFT)

def rule(slide, y):
    ln = slide.shapes.add_shape(1, Inches(0.4), Inches(y), Inches(12.5), Inches(0.04))
    ln.fill.solid(); ln.fill.fore_color.rgb = SAFFRON
    ln.line.fill.background()

def bullets(slide, items, x, y, w, h, size=18, color=LGREY):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    for i, item in enumerate(items):
        p = tf.add_paragraph() if i > 0 else tf.paragraphs[0]
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(4)
        run = p.add_run()
        run.text = item
        run.font.size = Pt(size)
        run.font.color.rgb = color

def card(slide, x, y, w, h, title, body, title_size=15, body_size=13):
    box(slide, x, y, w, h, fill=DGREY, line=SAFFRON)
    # title
    tb = slide.shapes.add_textbox(Inches(x+0.1), Inches(y+0.1), Inches(w-0.2), Inches(0.35))
    tf = tb.text_frame
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = title
    r.font.size = Pt(title_size); r.font.bold = True; r.font.color.rgb = SAFFRON
    # body
    tb2 = slide.shapes.add_textbox(Inches(x+0.1), Inches(y+0.45), Inches(w-0.2), Inches(h-0.55))
    tf2 = tb2.text_frame; tf2.word_wrap = True
    for i, line in enumerate(body):
        p2 = tf2.add_paragraph() if i > 0 else tf2.paragraphs[0]
        p2.alignment = PP_ALIGN.CENTER
        r2 = p2.add_run(); r2.text = line
        r2.font.size = Pt(body_size); r2.font.color.rgb = WHITE

# ═════════════════════════════════════════════════════════════════════════════
# Slide 1 — Title
# ═════════════════════════════════════════════════════════════════════════════
s1 = add_slide()

# Saffron accent bar at top
box(s1, 0, 0, 13.333, 0.12, fill=SAFFRON)

# Main title
txbox(s1, "BharatDrishti", 1.0, 1.5, 11.3, 1.4,
      size=72, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)

# Subtitle
txbox(s1, "India's Eye", 1.0, 2.9, 11.3, 0.7,
      size=36, bold=False, color=WHITE, align=PP_ALIGN.CENTER)

# Tagline
txbox(s1, "Sovereign Satellite Intelligence  ·  Powered by Deep-Tech AI",
      1.0, 3.65, 11.3, 0.5,
      size=20, color=LGREY, align=PP_ALIGN.CENTER)

# Rule
rule(s1, 4.35)

# Stats row
stats = [
    ("41M", "Parameters"),
    ("94.95%", "Val Accuracy"),
    ("< 3 sec", "Per Region"),
    ("100%", "Sovereign"),
]
for i, (val, lbl) in enumerate(stats):
    cx = 1.2 + i * 2.9
    txbox(s1, val, cx, 4.55, 2.6, 0.55,
          size=28, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)
    txbox(s1, lbl, cx, 5.1, 2.6, 0.35,
          size=15, color=LGREY, align=PP_ALIGN.CENTER)

# Bottom bar
box(s1, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s1, "Track: Sovereign Technology for India  |  AI Infra & Compute",
      0, 7.3, 13.333, 0.2, size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 2 — Problem
# ═════════════════════════════════════════════════════════════════════════════
s2 = add_slide()
box(s2, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s2, "Problem — India's Geospatial Blind Spot")
rule(s2, 0.98)

bullets(s2, [
    "▸  290 TB of Sentinel-2 imagery over Indian territory captured daily — left unanalysed",
    "▸  All major change-detection platforms are foreign-controlled:",
    "     Google Earth Engine (US)   ·   Planet Labs (US subscription)   ·   Maxar (US DoD)",
    "▸  No sovereign, offline-capable AI platform exists for strategic monitoring",
    "▸  Critical stakeholders remain blind to rapid land-cover changes:",
], 0.5, 1.1, 12.3, 2.8, size=19)

# Stakeholder cards
stakeholders = [
    ("ISRO", "Needs automated\nchange alerts"),
    ("NDMA", "Flood disaster\nresponse"),
    ("Defence", "Border infra\nmonitoring"),
    ("Urban\nPlanners", "Unauthorised\nconstruction"),
]
for i, (title, body) in enumerate(stakeholders):
    cx = 0.5 + i * 3.2
    card(s2, cx, 3.95, 3.0, 1.5, title, body.split("\n"), title_size=16, body_size=13)

txbox(s2, "Result: India remains dependent on foreign infrastructure for its own strategic territory",
      0.5, 5.6, 12.3, 0.5, size=17, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)

box(s2, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s2, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 3 — Solution
# ═════════════════════════════════════════════════════════════════════════════
s3 = add_slide()
box(s3, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s3, "Solution — What BharatDrishti Does")
rule(s3, 0.98)

txbox(s3, "End-to-end sovereign geospatial intelligence platform",
      0.5, 1.1, 12.3, 0.45, size=20, bold=True, color=WHITE)

bullets(s3, [
    "▸  Ingests free Copernicus CDSE Sentinel-2 L2A GeoTIFFs — zero foreign-API cost",
    "▸  Runs ChangeFormerV6 (41M-param Siamese Transformer) for bi-temporal change detection",
    "▸  Produces per-pixel change heatmap, binary mask, NDVI diff map, GeoJSON polygons",
    "▸  Generates automated natural-language intelligence brief — no manual report writing",
    "▸  100% offline-capable — deployable on ISRO servers or air-gapped military networks",
    "▸  Replaces Google Earth Engine / Planet Labs with Made-in-India sovereign technology",
], 0.5, 1.65, 12.3, 3.0, size=18)

# Output type cards
outputs = [
    ("Heatmap", "Per-pixel change\nprobability 0–1"),
    ("Binary Mask", "Morphologically\ncleaned"),
    ("NDVI Diff", "Vegetation health\nT2 − T1"),
    ("GeoJSON", "Polygons with\nconfidence + area"),
    ("AI Brief", "Natural-language\nintelligence report"),
]
for i, (t, b) in enumerate(outputs):
    cx = 0.3 + i * 2.56
    card(s3, cx, 4.85, 2.4, 1.5, t, b.split("\n"), title_size=14, body_size=12)

box(s3, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s3, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 4 — Architecture
# ═════════════════════════════════════════════════════════════════════════════
s4 = add_slide()
box(s4, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s4, "Architecture — Four Sovereign Layers")
rule(s4, 0.98)

arch = [
    ("Sentinel-2\nData Pipeline",
     "sentinel_fetch.py",
     ["CDSE live download", "On-disk cache", "Synthetic fallback", "L2A GeoTIFF pairs"]),
    ("ChangeFormerV6\nAI Inference",
     "inference.py",
     ["41M Siamese Transformer", "Bi-temporal forward pass", "NDVI computation", "GeoJSON polygon extract"]),
    ("FastAPI\nBackend",
     "api.py",
     ["Lazy model loading", "Response caching", "10 REST endpoints", "< 3 s response"]),
    ("React/Leaflet\nFrontend",
     "frontend/",
     ["Before/after slider", "GeoJSON polygon map", "NDVI diff panel", "AI analysis panel"]),
]

for i, (title, file, pts) in enumerate(arch):
    cx = 0.3 + i * 3.25
    # card background
    box(s4, cx, 1.2, 3.0, 5.0, fill=DGREY, line=SAFFRON)
    # Layer number
    txbox(s4, f"Layer {i+1}", cx, 1.25, 3.0, 0.3,
          size=12, color=SAFFRON, align=PP_ALIGN.CENTER)
    # Title
    txbox(s4, title, cx, 1.55, 3.0, 0.65,
          size=16, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
    # filename tag
    box(s4, cx+0.2, 2.25, 2.6, 0.3, fill=RGBColor(0x10,0x10,0x28), line=SAFFRON)
    txbox(s4, file, cx+0.2, 2.25, 2.6, 0.3,
          size=11, color=SAFFRON, align=PP_ALIGN.CENTER)
    # bullets
    for j, pt in enumerate(pts):
        txbox(s4, f"· {pt}", cx+0.15, 2.65 + j*0.52, 2.7, 0.45,
              size=13, color=LGREY)

    # Arrow (not after last)
    if i < 3:
        txbox(s4, "→", 3.3 + i*3.25 - 0.05, 3.5, 0.3, 0.4,
              size=24, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)

box(s4, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s4, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 5 — Results
# ═════════════════════════════════════════════════════════════════════════════
s5 = add_slide()
box(s5, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s5, "Results — Three Indian Regions Validated")
rule(s5, 0.98)

# Headline stats
hstats = [
    ("39", "Change Polygons\nNavi Mumbai"),
    ("297.71 km²", "Change Area\nNavi Mumbai"),
    ("3 Regions", "India Coverage"),
    ("< 3 sec", "Per Inference"),
]
for i, (val, lbl) in enumerate(hstats):
    cx = 0.4 + i * 3.2
    box(s5, cx, 1.1, 3.0, 1.3, fill=DGREY, line=SAFFRON)
    txbox(s5, val, cx, 1.15, 3.0, 0.6,
          size=26, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)
    txbox(s5, lbl, cx, 1.75, 3.0, 0.55,
          size=13, color=LGREY, align=PP_ALIGN.CENTER)

# Table header
cols = [2.5, 1.7, 1.7, 1.5, 2.2, 2.0]
headers = ["Region", "Polygons", "Area (km²)", "Change %", "Confidence", "Category"]
x_start = 0.35
header_y = 2.65
row_h = 0.62

for j, (hdr, cw) in enumerate(zip(headers, cols)):
    cx = x_start + sum(cols[:j])
    box(s5, cx, header_y, cw, 0.4, fill=SAFFRON)
    txbox(s5, hdr, cx, header_y, cw, 0.4,
          size=14, bold=True, color=BG, align=PP_ALIGN.CENTER)

# Table rows
rows = [
    ("Navi Mumbai", "39", "297.71", "46.9 %", "42% *", "construction"),
    ("Assam / Bihar", "3",  "12.2",  "46.4 %", "38% *", "water_body_change"),
    ("Ladakh",        "2",  "2.0",   "9.0 %",  "34% *", "construction"),
]
row_colors = [DGREY, RGBColor(0x1E,0x1E,0x32), DGREY]
for ri, (row, rc) in enumerate(zip(rows, row_colors)):
    ry = header_y + 0.4 + ri * row_h
    for j, (cell, cw) in enumerate(zip(row, cols)):
        cx = x_start + sum(cols[:j])
        box(s5, cx, ry, cw, row_h - 0.05, fill=rc, line=RGBColor(0x44,0x44,0x66))
        txbox(s5, cell, cx, ry, cw, row_h - 0.05,
              size=15, color=WHITE, align=PP_ALIGN.CENTER)

txbox(s5, "All results from outputs/<region>/result.json  ·  CPU inference  ·  spectral-diff fallback active",
      0.35, 6.2, 12.5, 0.35, size=11, color=LGREY, align=PP_ALIGN.CENTER)

txbox(s5, "* Conservative scores reflect domain gap: trained on 0.5m LEVIR-CD, running on 10m Sentinel-2. Fine-tuning → 85%+ confidence.",
      0.35, 6.55, 12.5, 0.4, size=10, color=LGREY, align=PP_ALIGN.LEFT)

box(s5, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s5, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 6 — AI Deep Tech
# ═════════════════════════════════════════════════════════════════════════════
s6 = add_slide()
box(s6, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s6, "AI Deep Tech — ChangeFormerV6")
rule(s6, 0.98)

# Left column — model details
bullets(s6, [
    "▸  Siamese Transformer — dual MiT-b2 hierarchical encoders",
    "▸  Self-attention at 1/4 · 1/8 · 1/16 · 1/32 resolution scales",
    "▸  Element-wise difference module across T1/T2 feature maps",
    "▸  Lightweight MLP decoder → change probability heatmap",
    "▸  41M parameters  ·  94.95% val accuracy on LEVIR-CD",
    "▸  CNN baseline: ~91–92%  →  Transformer gains: +3 pp",
], 0.5, 1.1, 6.0, 3.1, size=17)

# Right column — NDVI + confidence
box(s6, 6.9, 1.1, 6.0, 1.55, fill=DGREY, line=SAFFRON)
txbox(s6, "NDVI = (B08 − B04) / (B08 + B04)", 6.9, 1.15, 6.0, 0.4,
      size=15, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)
bullets(s6, [
    "· delta < −0.15  →  vegetation_loss",
    "· delta > +0.15  →  vegetation_gain",
    "· Range −1.0 to +1.0",
], 7.0, 1.6, 5.8, 0.9, size=13)

box(s6, 6.9, 2.8, 6.0, 1.35, fill=DGREY, line=SAFFRON)
txbox(s6, "Confidence & Fallback", 6.9, 2.85, 6.0, 0.35,
      size=15, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)
bullets(s6, [
    "· Current range: 0.34 – 0.42  (domain gap, not a bug)",
    "· Spectral-diff fallback when mean prob < 0.3",
    "· Domain gap: LEVIR-CD (Texas RGB 0.5 m) vs Sentinel-2 (India 10 m)",
], 7.0, 3.25, 5.8, 0.75, size=13)

# Bottom — change categories
txbox(s6, "Change Categories", 0.5, 4.3, 12.3, 0.4,
      size=17, bold=True, color=SAFFRON)
cats = [
    ("construction", "Red↑ NIR↓\nbare soil", RED),
    ("vegetation_loss", "NDVI delta\n< −0.15", RGBColor(0xFF,0x70,0x00)),
    ("vegetation_gain", "NDVI delta\n> +0.15", GREEN),
    ("water_body_change", "Red↓ NIR↓\nBlue high", RGBColor(0x42,0xA5,0xF5)),
    ("general_change", "Mixed\nsignature", LGREY),
]
for i, (name, heur, col) in enumerate(cats):
    cx = 0.3 + i * 2.6
    box(s6, cx, 4.75, 2.4, 1.35, fill=DGREY, line=col)
    txbox(s6, name, cx, 4.8, 2.4, 0.38, size=12, bold=True, color=col, align=PP_ALIGN.CENTER)
    txbox(s6, heur, cx, 5.2, 2.4, 0.75, size=12, color=LGREY, align=PP_ALIGN.CENTER)

box(s6, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s6, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ═════════════════════════════════════════════════════════════════════════════
# Slide 7 — Roadmap
# ═════════════════════════════════════════════════════════════════════════════
s7 = add_slide()
box(s7, 0, 0, 13.333, 0.12, fill=SAFFRON)
heading(s7, "Roadmap — From Prototype to National Platform")
rule(s7, 0.98)

stages = [
    ("Stage 1\n(Now)",
     "Functional Prototype",
     ["3 regions validated", "CPU offline inference", "Full pipeline operational", "100% open-source"]),
    ("Stage 2\n(Production)",
     "Sovereign Cloud Deploy",
     ["Live CDSE / ISRO Bhuvan feed", "NIC cloud / ISRO servers", "NVIDIA T4 → < 1 s inference", "FastAPI production hardening"]),
    ("Stage 3\n(Scale)",
     "National Coverage",
     ["Celery + Redis task queue", "4–8 T4 GPU fleet", "Threshold-based alert system", "All 3.29M km² of India"]),
    ("Stage 4\n(Fine-tune)",
     "85%+ Confidence",
     ["100–500 Indian Sentinel-2 pairs", "Fine-tune from LEVIR checkpoint", "Single A100, ~12–18 hours", "Confidence: 0.3–0.5 → 0.7–0.9"]),
]

for i, (label, title, pts) in enumerate(stages):
    cx = 0.3 + i * 3.25
    box(s7, cx, 1.15, 3.0, 5.1, fill=DGREY, line=SAFFRON)
    txbox(s7, label, cx, 1.2, 3.0, 0.5,
          size=14, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)
    txbox(s7, title, cx, 1.72, 3.0, 0.45,
          size=13, bold=False, color=WHITE, align=PP_ALIGN.CENTER)
    # divider
    box(s7, cx+0.1, 2.22, 2.8, 0.03, fill=SAFFRON)
    for j, pt in enumerate(pts):
        txbox(s7, f"· {pt}", cx+0.15, 2.32 + j*0.52, 2.7, 0.45,
              size=13, color=LGREY)
    # Arrows
    if i < 3:
        txbox(s7, "→", 3.3 + i*3.25 - 0.05, 3.55, 0.3, 0.4,
              size=22, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)

# Bottom call to action
box(s7, 0.4, 6.45, 12.5, 0.62, fill=RGBColor(0x1E,0x10,0x05), line=SAFFRON)
txbox(s7,
      "ISRO integration · Fine-tuning on Indian data · 85%+ confidence · "
      "Atmanirbhar Bharat geospatial sovereignty",
      0.5, 6.5, 12.3, 0.55,
      size=16, bold=True, color=SAFFRON, align=PP_ALIGN.CENTER)

box(s7, 0, 7.3, 13.333, 0.2, fill=DGREY)
txbox(s7, "BharatDrishti  ·  Sovereign Technology for India", 0, 7.3, 13.333, 0.2,
      size=11, color=LGREY, align=PP_ALIGN.CENTER)

# ── Save ──────────────────────────────────────────────────────────────────────
out = r"C:\Users\dell\Desktop\times\ChangeFormer\BharatDrishti_deck.pptx"
prs.save(out)
print(f"Saved: {out}")
