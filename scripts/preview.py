"""変換した .osm / .osm.pbf の一部を、道路の種類ごとに色分けした画像にする（目視確認用）。

使い方:
    uv run --group preview scripts/preview.py out/N13-24_6441.osm.pbf preview.png 141.32 141.38 43.04 43.08
    （引数: 入力 出力画像 西端 東端 南端 北端）
"""

import argparse

import matplotlib
import osmium

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

# highway → (色, 線の太さ)。描く順（細い道 → 太い道）に並べる
STYLE = {
    "service": ("#bbbbbb", 0.3),
    "residential": ("#7f7f7f", 0.5),
    "footway": ("#2ca02c", 0.4),
    "steps": ("#2ca02c", 0.6),
    "road": ("#9467bd", 0.6),
    "construction": ("#8c564b", 0.8),
    "secondary": ("#e6c200", 1.4),
    "primary": ("#ff7f0e", 1.8),
    "motorway": ("#d62728", 2.2),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("src")
    parser.add_argument("out")
    parser.add_argument("bbox", nargs=4, type=float, metavar=("WEST", "EAST", "SOUTH", "NORTH"))
    args = parser.parse_args()
    x0, x1, y0, y1 = args.bbox

    lines = {k: [] for k in STYLE}
    bridges, tunnels = [], []
    ways = osmium.FileProcessor(args.src).with_locations().with_filter(osmium.filter.EntityFilter(osmium.osm.WAY))
    for w in ways:
        pts = [(n.lon, n.lat) for n in w.nodes]
        if not any(x0 <= x <= x1 and y0 <= y <= y1 for x, y in pts):
            continue
        lines.setdefault(w.tags.get("highway"), []).append(pts)
        if "bridge" in w.tags:
            bridges.append(pts)
        if "tunnel" in w.tags:
            tunnels.append(pts)

    fig, ax = plt.subplots(figsize=(11, 11), dpi=110)
    for k, (color, width) in STYLE.items():
        ax.add_collection(LineCollection(lines[k], colors=color, linewidths=width, label=f"{k} ({len(lines[k])})"))
    ax.add_collection(
        LineCollection(bridges, colors="#1f77b4", linewidths=2.5, alpha=0.6, label=f"bridge=yes ({len(bridges)})")
    )
    ax.add_collection(
        LineCollection(tunnels, colors="black", linewidths=2.5, linestyles=":", label=f"tunnel=yes ({len(tunnels)})")
    )
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / 0.73)  # 北緯43度付近で経度1度 ≒ 緯度0.73度の長さ
    ax.legend(loc="lower right", fontsize=9)
    ax.set_title(args.src.split("/")[-1])
    fig.savefig(args.out, bbox_inches="tight")


if __name__ == "__main__":
    main()
