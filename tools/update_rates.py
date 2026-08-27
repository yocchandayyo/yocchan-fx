# -*- coding: utf-8 -*-
"""data/rates.json を日中足で更新する。

トップページのレートカードとミニチャートはこのファイルだけを見ている。
以前はECBの参考レート(frankfurter)を使っていたが、あれは平日1日1回の
公表値なので、15日分の折れ線のうち毎日1点しか入れ替わらず、
見た目がほとんど動かなかった。

そこで主データをYahoo Financeの15分足(直近5日)に変更した。
1本走らせるたびに線の形が変わる。ブラウザから直接は叩けない
(CORSヘッダが無い)ので、ここで取ってJSONに焼き込む。

Yahooは非公式APIなので落ちることがある。その場合は従来のECBに
自動で戻して、少なくとも古い数字が出続けることは避ける。

使い方:
    python tools/update_rates.py
"""
import json
import io
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

YF = "https://query1.finance.yahoo.com/v8/finance/chart/{}=X?interval=15m&range=5d"
ECB = "https://api.frankfurter.dev/v1"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "rates.json")

PAIRS = [
    ("USD/JPY", "USDJPY"),
    ("GBP/USD", "GBPUSD"),
    ("EUR/USD", "EURUSD"),
    ("GBP/JPY", "GBPJPY"),
]

JST = timezone(timedelta(hours=9))
POINTS = 60  # 折れ線に残す点の数


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (yocchan-fx)"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def digits(pair):
    return 2 if pair.endswith("JPY") else 4


def thin(values, n):
    """点が多すぎるので等間隔に間引く。最後の点は必ず残す。"""
    if len(values) <= n:
        return values
    step = (len(values) - 1) / float(n - 1)
    idx = sorted({int(round(i * step)) for i in range(n)} | {len(values) - 1})
    return [values[i] for i in idx]


def from_yahoo(pair, sym):
    d = fetch(YF.format(sym))
    res = d["chart"]["result"][0]
    q = res["indicators"]["quote"][0]["close"]
    ts = res["timestamp"]
    pts = [(t, v) for t, v in zip(ts, q) if v is not None]
    if len(pts) < 10:
        raise RuntimeError("日中足が足りません: " + pair)

    meta = res.get("meta", {})
    price = pts[-1][1]
    prev = meta.get("previousClose") or meta.get("chartPreviousClose") or pts[0][1]
    n = digits(pair)
    return {
        "pair": pair,
        "base": pair[:3],
        "quote": pair[4:],
        "price": round(price, n),
        "changePct": round((price - prev) / prev * 100, 2),
        "history": [round(v, n) for v in thin([v for _, v in pts], POINTS)],
    }, pts[-1][0]


def from_ecb():
    """Yahooが駄目なときの保険。従来どおりECBの日足。"""
    end = date.today()
    rng = "{}..{}".format((end - timedelta(days=30)).isoformat(), end.isoformat())
    usd = fetch("{}/{}?from=USD&to=JPY".format(ECB, rng))
    gbp = fetch("{}/{}?from=GBP&to=USD,JPY".format(ECB, rng))
    eur = fetch("{}/{}?from=EUR&to=USD".format(ECB, rng))

    def build(pair, resp, symbol):
        h = [resp["rates"][k][symbol] for k in sorted(resp["rates"])]
        n = digits(pair)
        return {
            "pair": pair,
            "base": pair[:3],
            "quote": pair[4:],
            "price": round(h[-1], n),
            "changePct": round((h[-1] - h[-2]) / h[-2] * 100, 2),
            "history": [round(v, n) for v in h[-15:]],
        }

    pairs = [
        build("USD/JPY", usd, "JPY"),
        build("GBP/USD", gbp, "USD"),
        build("EUR/USD", eur, "USD"),
        build("GBP/JPY", gbp, "JPY"),
    ]
    return pairs, sorted(usd["rates"])[-1]


def main():
    pairs, latest_ts, source = [], 0, "yahoo"
    try:
        for pair, sym in PAIRS:
            p, t = from_yahoo(pair, sym)
            pairs.append(p)
            latest_ts = max(latest_ts, t)
        stamp = datetime.fromtimestamp(latest_ts, JST)
        updated = stamp.strftime("%Y-%m-%d")
        updated_at = stamp.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print("日中足の取得に失敗、ECBに切り替えます:", e, file=sys.stderr)
        pairs, updated = from_ecb()
        updated_at = updated
        source = "ecb"

    data = {"updated": updated, "updatedAt": updated_at, "source": source, "pairs": pairs}
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("updated:", updated_at, "(" + source + ")")
    for p in pairs:
        print("  {:8} {:>10}  {:+.2f}%  {}点".format(
            p["pair"], p["price"], p["changePct"], len(p["history"])))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("失敗:", e, file=sys.stderr)
        sys.exit(1)
