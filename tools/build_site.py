# -*- coding: utf-8 -*-
"""記事ごとの静的HTMLページと sitemap.xml / robots.txt を生成する。

入力の data/articles.json はこのサイトの運営側(Claude)が書く一次データで、外部ユーザーの入力は入らない。
本文(leadPara/sections/memo)は app.js と同じく意図したインラインHTML(リンク等)を許すため生のまま出力し、
タイトル・ポイント・タグ・参照元など平文のフィールドはエスケープする。

article.html?id=... はJSで描画するため検索エンジンに弱い。
このスクリプトが data/articles.json から /post/<id>.html を書き出し、
title・description・canonical・OGP・JSON-LD を静的に持たせる。

使い方: リポジトリ直下で `python tools/build_site.py`
記事を追加したら必ず実行してからコミットする。
"""
import json
import pathlib
import re
import html

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "data" / "articles.json"
OUT_DIR = ROOT / "post"
SITE = "https://yocchan-fx.com"
AUTHOR = "よっちゃん(FX歴8年)"
GA_ID = "G-M79V6CNK6L"
ADSENSE_CLIENT = "ca-pub-6679576726407478"
TCS_AC = "C142787"
CSS_VER = "20"

CAT = {
    "analysis": ("相場分析", "c-analysis"),
    "technical": ("テクニカル入門", "c-technical"),
    "news": ("経済ニュース", "c-news"),
}

FONTS = ("https://fonts.googleapis.com/css2?family=Shippori+Mincho+B1:wght@600;700;800&family=Zen+Kaku+Gothic+New:wght@700;900"
         "&family=Noto+Sans+JP:wght@400;500;700&family=IBM+Plex+Mono:wght@500;600&display=swap")


def esc(s):
    return html.escape(str(s), quote=True)


def read_minutes(a):
    chars = len(a.get("leadPara", ""))
    for s in a.get("sections", []):
        for p in s.get("body", []):
            chars += len(p)
    return max(2, round(chars / 450))


def fmt_full_date(iso):
    y, m, d = (int(x) for x in iso.split("-"))
    return f"{y}年{m}月{d}日"


def hero_svg(direction):
    up = [3, 2.7, 3.3, 3.0, 3.7, 3.4, 4.2, 3.9, 4.5, 4.2, 5.0, 4.7, 5.3]
    vals = up if direction == "up" else list(reversed(up))
    w, h, pad = 300, 110, 4
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    pts = " ".join(
        f"{pad + i / (len(vals) - 1) * (w - pad * 2):.1f},{h - pad - (v - lo) / span * (h - pad * 2):.1f}"
        for i, v in enumerate(vals)
    )
    return (f'<svg class="chart" viewBox="0 0 {w} {h}" preserveAspectRatio="none" aria-hidden="true">'
            f'<polyline points="{pts}"></polyline></svg>')


def tcs_link(lc, isq):
    return f"https://www.tcs-asp.net/alink?AC={TCS_AC}&amp;LC={lc}&amp;SQ=0&amp;isq={isq}"


def tcs_img(lc, isq, alt):
    return (f'<a href="{tcs_link(lc, isq)}" target="_blank" rel="nofollow sponsored noopener">'
            f'<img src="https://img.tcs-asp.net/imagesender?ac={TCS_AC}&amp;lc={lc}&amp;isq={isq}&amp;psq=0" '
            f'width="300" height="250" alt="{esc(alt)}" loading="lazy"></a>')


AD_NOTE = ("FXは証拠金取引のため、相場の変動により預けた証拠金を上回る損失が出ることがあります。"
           "各社のリスク説明を確認のうえ、ご自身の判断でお申し込みください。")


AD_WHY = {
    "matsui": "1通貨から。少額で試せて、サポートの評判が高い会社です",
    "hirose": "約定力と情報量に定評。ポンド系のスプレッドが狭めです",
}


def ad_item(lc, isq, alt, why_key):
    return f'<div class="ad-item">{tcs_img(lc, isq, alt)}<p class="ad-why">{esc(AD_WHY[why_key])}</p></div>'


def ad_box():
    return (
        '<div class="ad-box"><div class="ad-head"><span class="ad-pr">PR</span>FX口座の開設はこちら</div>'
        '<div class="ad-grid">' + ad_item("MTI2", 205, "松井証券 FX口座開設", "matsui") + ad_item("HIR99", 48, "ヒロセ通商 LION FX 口座開設", "hirose") + '</div>'
        f'<p class="ad-more"><a href="{tcs_link("SBI50", 1)}" target="_blank" rel="nofollow sponsored noopener">1通貨から練習するなら SBI FXトレード →</a> 1通貨から取引でき、ドル円スプレッドが狭い。評判基準の比較で1位に置いています</p>'
        '<p class="ad-more"><a href="https://www.tradingview.com/?aff_id=170482" target="_blank" rel="nofollow sponsored noopener">チャート分析に使っている TradingView →</a></p>'
        '<p class="ad-more"><a href="/brokers.html">選定は単価ではなく評判(満足度・処分歴・障害歴)で決めています → 口座比較</a></p>'
        f'<p class="ad-note">{AD_NOTE}</p></div>'
    )


def header_footer(active_cat=None):
    market_cls = ' class="active"' if active_cat == "market" else ""
    basics_cls = ' class="active"' if active_cat == "basics" else ""
    header = f'''<header class="site-header">
  <div class="wrap">
    <a class="brand" href="/" aria-label="よっちゃんのFX ホーム">
      <img class="avatar" src="/assets/img/fx_icon.png?v=3" alt="">
      <span>よっちゃんのFX</span>
    </a>
    <span class="stance">デイトレ歴8年。ドル円・ポンドドルを中心に、毎朝の相場観を淡々と記録する個人メディア</span>
    <nav class="global-nav" aria-label="グローバルナビゲーション">
      <a href="/">ホーム</a>
      <a href="/articles.html?cat=market"{market_cls}>相場観</a>
      <a href="/articles.html?cat=basics"{basics_cls}>FX入門</a>
      <a href="/brokers.html">口座比較</a>
      <a href="/vps.html">VPS</a>
      <a href="/calendar.html">経済指標</a>
      <a href="/about.html">このサイトについて</a>
    </nav>
  </div>
</header>'''
    footer = '''<footer class="site-footer">
  <div class="wrap">
    <nav class="fnav" aria-label="フッターナビゲーション">
      <a href="/">ホーム</a>
      <a href="/articles.html">記事一覧</a>
      <a href="/brokers.html">口座比較</a>
      <a href="/vps.html">自動売買向けVPS</a>
      <a href="/calendar.html">経済指標カレンダー</a>
      <a href="/about.html">このサイトについて</a>
      <a href="/disclaimer.html">免責事項</a>
      <a href="/privacy.html">プライバシーポリシー</a>
    </nav>
    <p class="legal">当サイトは情報提供を目的としたもので、特定の金融商品の売買を推奨・勧誘するものではありません。投資の最終判断はご自身の責任でお願いします。FX取引は元本を上回る損失が発生するおそれがあります。<br>© 2026 よっちゃんのFX</p>
  </div>
</footer>'''
    return header, footer


def article_body(a, latest_market_article=None):
    label, cls = CAT.get(a["category"], ("記事", ""))
    hero = ""
    if a.get("hero"):
        h = a["hero"]
        chg = h.get("change", "")
        direction = "down" if chg.startswith(("-", "−")) else "up"
        hero = (f'<div class="hero-chart">{hero_svg(direction)}'
                f'<span class="eyebrow">{esc(h.get("label") or h.get("pair", ""))}</span>'
                f'<span class="big">{esc(h.get("price", ""))}<span class="chg-inline {direction}">{esc(chg)}</span></span></div>')

    sections = []
    for s in a.get("sections", []):
        body = "".join(f"<p>{p}</p>" for p in s.get("body", []))
        scen = "".join(
            f'<div class="scenario-card s-{sc.get("tone", "mid")}"><span class="tag">{esc(sc.get("tag", ""))}</span><span>{sc.get("text", "")}</span></div>'
            for sc in s.get("scenarios", [])
        )
        sections.append(f"<h2>{s.get('h', '')}</h2>{body}" + (f'<div class="scenario">{scen}</div>' if scen else ""))

    points = "".join(f"<li>{esc(p)}</li>" for p in a.get("points", []))
    memo = (f'<div class="memo-box"><img class="memo-owl" src="/assets/img/fx_icon.png?v=3" alt=""><div><b>ヨル教授メモ:</b> {a["memo"]}</div></div>'
            if a.get("memo") else "")

    see_also = ""
    if a["category"] == "technical":
        if latest_market_article:
            see_also = (f'<div class="see-also">実際の相場ではどう動くか。'
                        f'<a href="/post/{latest_market_article["id"]}.html">毎朝の相場観もあわせてどうぞ →</a></div>')
    else:
        see_also = '<div class="see-also">用語でつまずいたら。<a href="/articles.html?cat=basics">FX入門の記事一覧を見る →</a></div>'

    tags = "".join(f'<span class="pill">{esc(t)}</span>' for t in a.get("tags", []))
    sources = ""
    if a.get("sources"):
        # 参照元は http(s) のURLだけ許可する
        safe = [s for s in a["sources"] if str(s.get("url", "")).startswith(("http://", "https://"))]
        items = "".join(
            f'<li><a href="{esc(s["url"])}" target="_blank" rel="noopener noreferrer">{esc(s["title"])}</a><span class="pub">{esc(s.get("publisher", ""))}</span></li>'
            for s in safe
        )
        sources = f'<div class="source-box"><div class="label">参考にした記事</div><ul>{items}</ul></div>'

    return f'''<span class="cat {cls}">{label}</span>
      <h1>{esc(a["title"])}</h1>
      <div class="byline"><span>{fmt_full_date(a["date"])}</span><span>{read_minutes(a)}分で読める</span><span class="who"><img src="/assets/img/fx_icon.png?v=3" alt="">{AUTHOR}</span></div>
      {hero}
      <div class="point-box"><div class="label">この記事のポイント</div><ul>{points}</ul></div>
      <p class="lead-para">{a.get("leadPara", "")}</p>
      {"".join(sections)}
      {memo}
      {see_also}
      {ad_box()}
      <div class="tag-row">タグ: {tags}</div>
      {sources}
      <div class="disclaimer-inline">当サイトの内容は情報提供を目的としたもので、特定の取引や売買タイミングを推奨するものではありません。投資の最終判断はご自身の責任でお願いします。</div>'''


def plain_text(s):
    return re.sub(r"<[^>]+>", "", s)


def build_page(a, verification_tag="", latest_market_article=None):
    label, _ = CAT.get(a["category"], ("記事", ""))
    url = f"{SITE}/post/{a['id']}.html"
    desc = plain_text(a.get("lead") or a.get("leadPara", ""))[:120]
    title = f"{a['title']} | よっちゃんのFX"
    active_cat = "basics" if a["category"] == "technical" else "market"
    header, footer = header_footer(active_cat)
    ld = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": a["title"],
        "description": desc,
        "datePublished": a["date"],
        "dateModified": a.get("updated", a["date"]),
        "author": {"@type": "Person", "name": "よっちゃん"},
        "publisher": {"@type": "Organization", "name": "よっちゃんのFX", "logo": {"@type": "ImageObject", "url": f"{SITE}/assets/img/fx_icon.png"}},
        "mainEntityOfPage": url,
        "image": f"{SITE}/assets/img/fx_cover.png",
        "articleSection": label,
        "keywords": ", ".join(a.get("tags", [])),
    }
    return f'''<!DOCTYPE html>
<html lang="ja">
<head>
<!-- Google tag (gtag.js) -->
<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={ADSENSE_CLIENT}" crossorigin="anonymous"></script>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{url}">
{verification_tag}
<meta property="og:title" content="{esc(a["title"])}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="article">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}/assets/img/fx_cover.png?v=3">
<meta property="og:site_name" content="よっちゃんのFX">
<meta property="article:published_time" content="{a["date"]}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:site" content="@yorukyouju_FX">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="{FONTS}" rel="stylesheet">
<link rel="icon" type="image/png" href="/assets/img/fx_icon.png?v=3">
<link rel="stylesheet" href="/assets/css/style.css?v={CSS_VER}">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
</head>
<body data-page="post">

{header}

<main class="wrap">
  <div class="page-head" style="max-width:780px;margin-left:auto;margin-right:auto;">
    <p class="crumb"><a href="/articles.html">← 記事一覧に戻る</a></p>
  </div>
  <article class="article-detail">
      {article_body(a, latest_market_article)}
  </article>
</main>

{footer}
</body>
</html>
'''


def build_sitemap(articles):
    static = ["", "articles.html", "brokers.html", "vps.html", "calendar.html", "about.html", "review-sbifx.html"]
    latest = articles[0]["date"] if articles else ""
    rows = [f"  <url><loc>{SITE}/{p}</loc><lastmod>{latest}</lastmod></url>" for p in static]
    for a in articles:
        rows.append(f"  <url><loc>{SITE}/post/{a['id']}.html</loc><lastmod>{a.get('updated', a['date'])}</lastmod></url>")
    return '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "\n".join(rows) + "\n</urlset>\n"


def main():
    articles = json.loads(ARTICLES.read_text(encoding="utf-8"))
    articles.sort(key=lambda a: a["date"], reverse=True)
    OUT_DIR.mkdir(exist_ok=True)
    tag_file = ROOT / "tools" / "gsc_verification.txt"
    verification_tag = tag_file.read_text(encoding="utf-8").strip() if tag_file.exists() else ""
    latest_market_article = next((x for x in articles if x["category"] in ("analysis", "news")), None)
    for a in articles:
        (OUT_DIR / f"{a['id']}.html").write_text(build_page(a, verification_tag, latest_market_article), encoding="utf-8")
    (ROOT / "sitemap.xml").write_text(build_sitemap(articles), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    print(f"built {len(articles)} pages -> post/, sitemap.xml, robots.txt")


if __name__ == "__main__":
    main()
