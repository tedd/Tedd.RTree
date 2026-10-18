"""Render the exact consolidated table and aligned throughput plots.
Requires matplotlib. Set MPLCONFIGDIR to a task workspace when running.
"""
from pathlib import Path
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
STEM = "rtree-comparison-2026-10-18-unified"
data = json.loads((ROOT / (STEM + ".data.json")).read_text(encoding="utf-8-sig"))
rows = data["rows"]
assert len(rows) == 15 and len({r["label"] for r in rows}) == 15
BG, INK, GRAY, TEAL, LINE = "#f7faf9", "#13282f", "#61747b", "#087f78", "#d6e3df"
plt.rcParams.update({"font.family": "DejaVu Sans", "svg.fonttype": "none"})
fig = plt.figure(figsize=(24, 13.5), dpi=160, facecolor=BG)
fig.text(.035, .96, "Algorithms with Sol", fontsize=15, color=GRAY)
title = fig.text(.035, .89, "Tedd.", fontsize=51, weight="bold", color="#000000")
fig.canvas.draw()
right = title.get_window_extent(fig.canvas.get_renderer()).x1 / fig.bbox.width
fig.text(right, .89, "RTree", fontsize=51, weight="bold", color=TEAL)
fig.text(.035, .845, "Latest recorded results across six languages", fontsize=24, color=INK)
fig.text(.035, .807, "10,000 rectangles  ·  Uniform distribution  ·  64 mixed queries", fontsize=17, color=GRAY)
fig.text(.72, .90, "0.077 ms", fontsize=29, color=TEAL, weight="bold")
fig.text(.72, .87, "Tedd.RTree · 64 queries", fontsize=14, color=GRAY)
fig.text(.875, .90, "0.422 ms", fontsize=29, color=TEAL, weight="bold")
fig.text(.875, .87, "Tedd.RTree · Build", fontsize=14, color=GRAY)

bottom, height = .235, .51
ax = fig.add_axes([.035, bottom, .535, height])
ax.set_xlim(0, 1); ax.set_ylim(len(rows)-.5, -.5); ax.axis("off")
for i, row in enumerate(rows):
    own = row["label"] == "Tedd.RTree (C#)"
    ax.axhspan(i-.5, i+.5, color="#e8f6f1" if own else ("#ffffff" if i%2 else "#f1f7f5"), zorder=-2)
    ax.axhline(i+.5, color=LINE, linewidth=.65, zorder=-1)
    weight = "bold" if own else "normal"
    color = TEAL if own else INK
    ax.text(.012, i, row["label"], fontsize=16.5, color=color, weight=weight, va="center")
    ax.text(.735, i, row["queryDisplay"], fontsize=18, color=color, weight=weight, va="center", ha="right")
    ax.text(.895, i, row["buildDisplay"], fontsize=18, color=color, weight=weight, va="center", ha="right")
    ax.text(.975, i, row["series"], fontsize=15, color=GRAY, va="center", ha="right")
for x, label, align in [(.012, "Library (language)", "left"), (.735, "64 queries (ms)", "right"), (.895, "Build (ms)", "right"), (.975, "Run", "right")]:
    ax.text(x, -.94, label, fontsize=15, color=INK, weight="bold", ha=align, va="bottom", clip_on=False)

charts = [
    (.602, .166, "Query throughput", "k queries / second", "queryKPerSecond", 970, [0,250,500,750], ".0f"),
    (.81, .16, "Build throughput", "M entries / second", "buildMPerSecond", 29, [0,10,20], ".2f"),
]
bar_lengths=[]
for left, width, title, units, field, xmax, ticks, fmt in charts:
    chart = fig.add_axes([left, bottom, width, height], facecolor=BG)
    values = [r[field] for r in rows]
    colors = [TEAL if r["label"] == "Tedd.RTree (C#)" else "#9db4b5" for r in rows]
    bars = chart.barh(range(len(rows)), values, height=.58, color=colors, edgecolor="none", zorder=3)
    chart.set_ylim(len(rows)-.5, -.5); chart.set_xlim(0,xmax)
    chart.set_yticks([]); chart.set_xticks(ticks)
    chart.tick_params(axis="x", labelsize=13, colors=GRAY, length=0, pad=8)
    chart.grid(axis="x", color=LINE, linewidth=.7, zorder=0)
    for spine in chart.spines.values(): spine.set_visible(False)
    chart.set_title(title+"\n"+units+" · Higher is better", loc="left", fontsize=15, color=INK, weight="bold", pad=21)
    for i, value in enumerate(values):
        chart.text(value+xmax*.02, i, format(value,fmt), fontsize=12.5, color=INK, va="center")
    bar_lengths.append([b.get_width() for b in bars])
    assert all(abs(b.get_width()-value) < 1e-10 for b,value in zip(bars,values))

fig.text(.035,.172,"Latest available per implementation. Run markers identify different measurement series.",fontsize=16,color=INK)
fig.text(.035,.137,"A: 17 Oct 2026 optimized confirmation medians  ·  B: 17 Oct 2026 screening medians  ·  C: 30 Sep 2026 NuGet means",fontsize=14,color=GRAY)
fig.text(.035,.106,"Mixed runs, source revisions and API contracts; descriptive comparison. Tedd/static query gap is small.",fontsize=14,color=GRAY)
fig.text(.035,.075,"Ryzen 9 5950X  ·  Query widths: 0 / 20 / 200 / 1,000  ·  Enyim: unoptimized published binary",fontsize=13,color=GRAY)
fig.text(.97,.035,"github.com/tedd/Tedd.RTree",fontsize=14,color=GRAY,ha="right")
fig.savefig(ROOT / (STEM + ".png"), dpi=160, facecolor=BG)
svg_path = ROOT / (STEM + ".svg")
fig.savefig(svg_path, facecolor=BG)
svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines()) + "\n", encoding="utf-8")
print(json.dumps({"rows":len(rows),"bars":sum(map(len,bar_lengths)),"output":str(ROOT / (STEM + ".png"))}))
plt.close(fig)
