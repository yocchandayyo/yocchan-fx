# -*- coding: utf-8 -*-
"""data/rates.json をECBの参考レート(frankfurter API)で更新する。

トップページのレート表示は本来ブラウザ側で同じAPIを直接叩くが、
APIが落ちているときは data/rates.json が代わりに表示される。
そのフォールバックが古いままだと数日前の数字が出てしまうので、
毎朝このスクリプトで作り直す。

使い方:
    python tools/update_rates.py
"""
import json
import io
import os
import sys
import urllib.request
from datetime import date, timedelta

API = "https://api.frankfurter.dev/v1"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "rates.json")


def fetch(path):
    req = urllib.request.Request(path, headers={"User-Agent": "yocchan-fx/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def series(resp, sym):
    return [resp["rates"][k][sym] for k in sorted(resp["rates"])]


def build(pair, resp, sym):
    h = series(resp, sym)
    if len(h) < 2:
        raise RuntimeError("履歴が足りません: " + pair)
    price = h[-1]
    prev = h[-2]
    return {
        "pair": pair,
        "base": pair[:3],
        "quote": pair[4:],
        "price": round(price, 2 if pair.endswith("JPY") else 4),
        "changePct": round((price - prev) / prev * 100, 2),
        "history": [round(v, 2 if pair.endswith("JPY") else 4) for v in h[-15:]],
    }


def main():
    end = date.today()
    start = end - timedelta(days=30)
    rng = "{}..{}".format(start.isoformat(), end.isoformat())

    usd = fetch("{}/{}?from=USD&to=JPY".format(API, rng))
    gbp = fetch("{}/{}?from=GBP&to=USD,JPY".format(API, rng))
    eur = fetch("{}/{}?from=EUR&to=USD".format(API, rng))

    pairs = [
        build("USD/JPY", usd, "JPY"),
        build("GBP/USD", gbp, "USD"),
        build("EUR/USD", eur, "USD"),
        build("GBP/JPY", gbp, "JPY"),
    ]
    updated = sorted(usd["rates"])[-1]

    data = {"updated": updated, "pairs": pairs}
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("updated:", updated)
    for p in pairs:
        print("  {:8} {:>10}  {:+.2f}%".format(p["pair"], p["price"], p["changePct"]))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("失敗:", e, file=sys.stderr)
        sys.exit(1)
