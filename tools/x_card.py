# -*- coding: utf-8 -*-
"""
ヨル教授のX投稿用「予定カード」を作る。

チャートは「何が起きたか」を見せる画像だが、週明けのプレビューには
まだ起きていない予定しか無い。この画像は、見た人がそのまま保存して
週の間に見返せる一覧にすることだけを狙う。

  - 見出しを1行。その下に日付ごとの行を並べる
  - 重要な行(imp=hi)だけオレンジ。全部目立たせると一覧にならない
  - 行は最大8。それ以上はスマホ幅で潰れる

使い方:
  python tools/x_card.py --title "来週は日本が3連休" --sub "..." \
      --row "9/21(月)|日本休場 敬老の日|lo" ... --out out.png
"""
import argparse

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

# サイトの配色(assets/css/style.css)に合わせる
NIGHT = "#0B1A3A"
DUSK = "#17305F"
DAWN = "#F2A26B"
GRID = "#24406F"
TEXT = "#EEF2F8"
SUB = "#A9B8D3"

ASPECTS = {"16:9": (1600, 900), "1:1": (1200, 1200), "4:5": (1200, 1500)}


def pick_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Noto Sans JP", "BIZ UDPGothic", "Yu Gothic", "Meiryo"):
        if name in have:
            return name
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="画像の見出し。短く(15字前後)")
    ap.add_argument("--sub", default="", help="見出しの下の補足")
    ap.add_argument("--row", action="append", default=[],
                    help="'日付|内容|hi または lo' の形。最大8行")
    ap.add_argument("--foot", default="yocchan-fx.com")
    ap.add_argument("--aspect", choices=ASPECTS.keys(), default="4:5")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    if len(a.row) > 8:
        raise SystemExit("行が多すぎます(最大8)。読めなくなるので削ってください")

    font = pick_font()
    if font:
        plt.rcParams["font.family"] = font

    w, h = ASPECTS[a.aspect]
    fig = plt.figure(figsize=(w / 100, h / 100), dpi=100, facecolor=NIGHT)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    ax.set_facecolor(NIGHT)

    ax.text(0.07, 0.90, a.title, color=TEXT, fontsize=46, fontweight="bold",
            va="top", ha="left")
    y = 0.90 - 0.075
    if a.sub:
        ax.text(0.07, y, a.sub, color=SUB, fontsize=22, va="top", ha="left")
        y -= 0.05

    # 見出しと一覧の区切り
    y -= 0.03
    ax.plot([0.07, 0.93], [y, y], color=GRID, lw=2)

    # 行の高さは固定。行数が少ない日に間延びさせず、一覧として同じ密度で出す
    n = len(a.row)
    step = 0.082
    top = y - 0.06
    for i, raw in enumerate(a.row):
        parts = raw.split("|")
        day, body = parts[0], parts[1]
        imp = parts[2] if len(parts) > 2 else "lo"
        ry = top - step * i
        color = DAWN if imp == "hi" else TEXT
        ax.add_patch(plt.Rectangle((0.07, ry - 0.035), 0.86, 0.072,
                                   facecolor=DUSK if i % 2 == 0 else NIGHT,
                                   edgecolor="none", zorder=0))
        ax.text(0.09, ry, day, color=SUB, fontsize=24, va="center", ha="left")
        ax.text(0.30, ry, body, color=color, fontsize=26, va="center", ha="left",
                fontweight="bold" if imp == "hi" else "normal")

    ax.text(0.07, 0.05, a.foot, color=SUB, fontsize=20, va="center", ha="left")

    fig.savefig(a.out, facecolor=NIGHT)
    print("saved:", a.out)


if __name__ == "__main__":
    main()
