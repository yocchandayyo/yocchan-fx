# -*- coding: utf-8 -*-
"""
ヨル教授のX投稿用チャート画像を作る。

サイトのスクショは「リンクカードと同じ絵」で情報が増えないうえ、
スマホの横500px程度では数字が潰れて読めない。この画像は、
本文を読まなくても1秒で「何が起きたか」が伝わることだけを狙う。

  - 見出し(主張)を大きく1行。これが画像の本体
  - 複数ペアを同じスタート地点(0%)からの変化率で重ねる。
    「ドル円は上がったがユーロドルは動いていない」のような
    ずれが、線の開き方でそのまま見える
  - 凡例は使わず、線の右端に名前と値を直接置く(目を往復させない)
  - データは毎回Yahoo Financeから取り直す。手で数字を書かない

使い方:
  python tools/x_chart.py --title "売られたのはドルではなく円" \
      --pairs USDJPY EURUSD GBPUSD --hours 18 --out out.png

  --focus で強調するペア(オレンジ)を選ぶ。省略時は先頭のペア。
"""
import argparse
import io
import json
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

JST = timezone(timedelta(hours=9))
YF = "https://query1.finance.yahoo.com/v8/finance/chart/{}=X?interval=15m&range=5d"

# サイトの配色(assets/css/style.css)に合わせる
NIGHT = "#0B1A3A"
DUSK = "#17305F"
DAWN = "#F2A26B"      # 強調ペア
MUTED = "#8FA3C4"     # その他のペア
GRID = "#24406F"
TEXT = "#EEF2F8"
SUB = "#A9B8D3"

LABEL = {
    "USDJPY": "ドル円", "EURUSD": "ユーロドル", "GBPUSD": "ポンドドル",
    "GBPJPY": "ポンド円", "EURJPY": "ユーロ円", "AUDJPY": "豪ドル円",
}

# 画像サイズ(px)。スマホのタイムラインで縦の占有を取りたいときは 4:5 / 1:1
ASPECTS = {"16:9": (1600, 900), "1:1": (1200, 1200), "4:5": (1200, 1500)}


def pick_font():
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Noto Sans JP", "BIZ UDPGothic", "Yu Gothic", "Meiryo"):
        if name in have:
            return name
    return None


def fetch(sym):
    req = urllib.request.Request(YF.format(sym), headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        d = json.load(r)
    res = d["chart"]["result"][0]
    closes = res["indicators"]["quote"][0]["close"]
    return [(datetime.fromtimestamp(t, JST), v)
            for t, v in zip(res["timestamp"], closes) if v is not None]


def digits(sym):
    return 2 if sym.endswith("JPY") else 4


def fmt(sym, v):
    return ("{:.%df}" % digits(sym)).format(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", required=True, help="画像の主張。短く(15字前後)")
    ap.add_argument("--sub", default="", help="見出しの下の補足。省略可")
    ap.add_argument("--pairs", nargs="+", default=["USDJPY", "EURUSD", "GBPUSD"])
    ap.add_argument("--focus", default=None, help="オレンジで強調するペア")
    ap.add_argument("--hours", type=float, default=18, help="終点から何時間さかのぼって描くか")
    ap.add_argument("--end", default=None,
                    help="終点(JST) 例 '2026-09-16 09:00'。朝の投稿は投稿時点で切る。"
                         "省略時は最新。描く時刻と投稿の時刻がずれると主張と線が食い違う")
    ap.add_argument("--aspect", choices=ASPECTS.keys(), default="16:9")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    focus = a.focus or a.pairs[0]
    font = pick_font()
    if font:
        plt.rcParams["font.family"] = font
    plt.rcParams["axes.unicode_minus"] = False

    # 全ペアで同じ時間窓にそろえる(窓がずれると変化率の比較が嘘になる)
    series = {s: fetch(s) for s in a.pairs}
    end = min(pts[-1][0] for pts in series.values())
    if a.end:
        end = min(end, datetime.strptime(a.end, "%Y-%m-%d %H:%M").replace(tzinfo=JST))
    start = end - timedelta(hours=a.hours)

    norm = {}
    for s, pts in series.items():
        w = [(t, v) for t, v in pts if start <= t <= end]
        if len(w) < 8:
            sys.exit("データが足りません: %s (%d本)" % (s, len(w)))
        base = w[0][1]
        norm[s] = {
            "t": [t for t, _ in w],
            "pct": [(v / base - 1) * 100 for _, v in w],
            "first": base, "last": w[-1][1],
        }

    W, H = ASPECTS[a.aspect]
    dpi = 200
    fig = plt.figure(figsize=(W / dpi, H / dpi), dpi=dpi, facecolor=NIGHT)

    # 見出し領域と描画領域の比率。縦長ほど見出しに余裕を持たせる
    top_band = {"16:9": 0.27, "1:1": 0.24, "4:5": 0.22}[a.aspect]
    fig.text(0.055, 1 - 0.075, a.title, color=TEXT, fontsize=30 if a.aspect == "16:9" else 32,
             fontweight="bold", va="top", ha="left")
    if a.sub:
        fig.text(0.055, 1 - top_band + 0.035, a.sub, color=SUB, fontsize=15, va="bottom", ha="left")

    ax = fig.add_axes([0.085, 0.14, 0.655, 1 - top_band - 0.17])
    ax.set_facecolor(NIGHT)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.axhline(0, color=SUB, linewidth=0.8, alpha=0.6)
    ax.tick_params(colors=SUB, labelsize=11, length=0)

    # 強調ペアを最後に描いて最前面に出す
    order = [s for s in a.pairs if s != focus] + [focus]
    for s in order:
        n = norm[s]
        is_f = s == focus
        ax.plot(n["t"], n["pct"], color=DAWN if is_f else MUTED,
                linewidth=4.2 if is_f else 2.4, alpha=1 if is_f else 0.85,
                solid_capstyle="round", zorder=3 if is_f else 2)

    # 右端ラベル。xは軸の外(軸座標)、yはデータ座標で置く。
    # ピクセルやポイントでずらすとdpiで幅が変わるので使わない
    lo, hi = ax.get_ylim()
    span = hi - lo
    pad = span * 0.06
    ax.set_ylim(lo - pad, hi + pad)
    lo, hi = ax.get_ylim()
    span = hi - lo
    gap = span * 0.16  # 2行ラベル1つぶんの高さ
    items = sorted(((norm[s]["pct"][-1], s) for s in a.pairs), reverse=True)
    ys = [y for y, _ in items]
    # 上から順に最小間隔を確保し、はみ出したら全体を持ち上げる
    for i in range(1, len(ys)):
        if ys[i - 1] - ys[i] < gap:
            ys[i] = ys[i - 1] - gap
    overflow = (lo + gap * 0.5) - ys[-1]
    if overflow > 0:
        ys = [y + overflow for y in ys]
    ys = [min(y, hi - gap * 0.5) for y in ys]
    tr = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
    for (y, s), yy in zip(items, ys):
        n = norm[s]
        is_f = s == focus
        chg = (n["last"] / n["first"] - 1) * 100
        col = DAWN if is_f else TEXT
        ax.text(1.025, yy + gap * 0.18, LABEL.get(s, s), transform=tr, color=col,
                fontsize=15 if is_f else 13, fontweight="bold", va="bottom", ha="left")
        ax.text(1.025, yy + gap * 0.14, "%+.2f%%  %s" % (chg, fmt(s, n["last"])), transform=tr,
                color=col, fontsize=12.5 if is_f else 11, va="top", ha="left")

    def pct(v, _):
        # 目盛りが0.05%刻みになる日に「+0.0%」が重ならないよう小数2桁まで出す
        s = ("%+.2f" % v).rstrip("0").rstrip(".")
        return ("0" if s in ("+0", "-0") else s) + "%"
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(pct))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M", tz=JST))
    ax.xaxis.set_major_locator(matplotlib.dates.HourLocator(interval=3, tz=JST))

    fig.text(0.055, 0.045,
             "%s〜%s JST・15分足・開始時点を0%%とした変化率・Yahoo Finance"
             % (start.strftime("%-m/%-d %H:%M") if sys.platform != "win32" else start.strftime("%#m/%#d %H:%M"),
                end.strftime("%H:%M")),
             color=SUB, fontsize=9.5, ha="left", va="bottom")
    fig.text(1 - 0.055, 0.045, "ヨル教授 @yorukyouju_FX", color=SUB, fontsize=10.5,
             ha="right", va="bottom")

    fig.savefig(a.out, dpi=dpi, facecolor=NIGHT)
    for s in a.pairs:
        n = norm[s]
        print("%-7s %s -> %s  %+.2f%%" % (s, fmt(s, n["first"]), fmt(s, n["last"]),
                                          (n["last"] / n["first"] - 1) * 100))
    print("window %s -> %s JST" % (start.strftime("%m/%d %H:%M"), end.strftime("%m/%d %H:%M")))
    print("saved", a.out, "%dx%d" % (W, H))


if __name__ == "__main__":
    main()
