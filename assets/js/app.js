/* FXコンパス — data-driven rendering */
(() => {
  const CAT = {
    analysis:  { label: "相場分析",     cls: "c-analysis" },
    technical: { label: "テクニカル入門", cls: "c-technical" },
    news:      { label: "経済ニュース",   cls: "c-news" }
  };
  const AUTHOR = "よっちゃん(FX歴8年)";
  const $ = (sel, el = document) => el.querySelector(sel);

  /* データは毎朝更新されるので、キャッシュを使う前に必ずサーバーへ確認しにいく。
     変更がなければ304が返るだけなので通信量はほぼ増えない。 */
  const fetchJSON = (path) => fetch(path, { cache: "no-cache" }).then(r => {
    if (!r.ok) throw new Error(path + " " + r.status);
    return r.json();
  });

  /* 端末のローカル日付を YYYY-MM-DD で返す(UTCずれを避けるため toISOString は使わない) */
  const todayISO = () => {
    const d = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  };

  /* ---------- 広告(TCSアフィリエイト) ----------
     提携中の案件のみ。バナー画像はTCS側で差し替わるので、こちらはIDだけ持つ。
     景表法のステマ規制に合わせて、必ず「PR」表記とリスク注記を一緒に出す。 */
  const TCS_AC = "C142787";
  const ADS = {
    dmm:     { lc: "DMM2",  isq: 55,  alt: "DMM FX 口座開設" },
    gaitame: { lc: "NJT2",  isq: 74,  alt: "外為オンライン 口座開設" },
    matsui:  { lc: "MTI2",  isq: 205, alt: "松井証券 FX口座開設" },
    broadnet:{ lc: "FXTS1", isq: 79,  alt: "FXブロードネット 口座開設" },
    hirose:  { lc: "HIR99", isq: 48,  alt: "ヒロセ通商 LION FX 口座開設" },
    invast:  { lc: "INV12", isq: 222, alt: "トライオートFX 口座開設" },
    himawari:{ lc: "HIM99", isq: 60,  alt: "ひまわりFX 口座開設" },
    jfx:     { lc: "JFX1",  isq: 200, alt: "JFX MATRIX TRADER 口座開設" }
  };
  const adTag = (a) =>
    `<a href="https://www.tcs-asp.net/alink?AC=${TCS_AC}&LC=${a.lc}&SQ=0&isq=${a.isq}" target="_blank" rel="nofollow sponsored noopener">` +
    `<img src="https://img.tcs-asp.net/imagesender?ac=${TCS_AC}&lc=${a.lc}&isq=${a.isq}&psq=0" width="300" height="250" alt="${a.alt}" loading="lazy"></a>`;
  const AD_WHY = {
    matsui: "1通貨から。少額で試せて、サポートの評判が高い会社です",
    hirose: "約定力と情報量に定評。ポンド系のスプレッドが狭めです"
  };
  const adItem = (key) => `<div class="ad-item">${adTag(ADS[key])}<p class="ad-why">${AD_WHY[key] || ""}</p></div>`;
  const AD_NOTE = "FXは証拠金取引のため、相場の変動により預けた証拠金を上回る損失が出ることがあります。各社のリスク説明を確認のうえ、ご自身の判断でお申し込みください。";
  const adBox = (keys, title, more) =>
    `<div class="ad-box"><div class="ad-head"><span class="ad-pr">PR</span>${title}</div>` +
    `<div class="ad-grid">${keys.map(adItem).join("")}</div>` +
    `<p class="ad-more"><a href="https://www.tcs-asp.net/alink?AC=${TCS_AC}&LC=SBI50&SQ=0&isq=1" target="_blank" rel="nofollow sponsored noopener">1通貨から練習するなら SBI FXトレード →</a> 1通貨から取引でき、ドル円スプレッドが狭い。評判基準の比較で1位に置いています</p>` +
    `<p class="ad-more"><a href="https://www.tradingview.com/?aff_id=170482" target="_blank" rel="nofollow sponsored noopener">チャート分析に使っている TradingView →</a></p>` +
    (more ? `<p class="ad-more"><a href="brokers.html">選定は単価ではなく評判(満足度・処分歴・障害歴)で決めています → 口座比較</a></p>` : "") +
    `<p class="ad-note">${AD_NOTE}</p></div>`;

  /* ---------- small SVG builders ---------- */
  const polyPoints = (values, w, h, pad = 3) => {
    const min = Math.min(...values), max = Math.max(...values);
    const span = (max - min) || 1;
    return values.map((v, i) => {
      const x = pad + (i / (values.length - 1)) * (w - pad * 2);
      const y = h - pad - ((v - min) / span) * (h - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(" ");
  };

  const sparkSVG = (values, dir, animate) => {
    const pts = polyPoints(values, 120, 34);
    return `<svg class="spark ${dir}" viewBox="0 0 120 34" preserveAspectRatio="none" aria-hidden="true">
      <polyline class="${animate ? "draw" : ""}" points="${pts}"></polyline></svg>`;
  };

  const HERO_SHAPE = [3, 2.7, 3.3, 3.0, 3.7, 3.4, 4.2, 3.9, 4.5, 4.2, 5.0, 4.7, 5.3];
  /* 記事ヒーローの線は装飾。せめて本文の方向とは食い違わせない */
  const heroShape = (dir) => dir === "down" ? HERO_SHAPE.slice().reverse() : HERO_SHAPE;

  const heroChartSVG = (values) => {
    const pts = polyPoints(values, 300, 110, 4);
    return `<svg class="chart" viewBox="0 0 300 110" preserveAspectRatio="none" aria-hidden="true">
      <polyline points="${pts}"></polyline></svg>`;
  };

  const THUMBS = {
    line:  '<polyline points="12,46 26,38 38,42 52,28 62,20" fill="none" stroke="#1B4DD8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>',
    cross: '<polyline points="10,22 36,44 64,18" fill="none" stroke="#12945B" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/><polyline points="10,42 36,20 64,46" fill="none" stroke="#1B4DD8" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" opacity=".55"/>',
    gauge: '<path d="M14 46 A 24 24 0 0 1 60 46" fill="none" stroke="#E4E9F0" stroke-width="6" stroke-linecap="round"/><path d="M14 46 A 24 24 0 0 1 46 24" fill="none" stroke="#1B4DD8" stroke-width="6" stroke-linecap="round"/>',
    bars:  '<rect x="14" y="34" width="8" height="16" rx="2" fill="#9DB8F5"/><rect x="30" y="24" width="8" height="26" rx="2" fill="#1B4DD8"/><rect x="46" y="16" width="8" height="34" rx="2" fill="#0A1E4E"/>',
    doc:   '<rect x="20" y="12" width="34" height="42" rx="5" fill="none" stroke="#1B4DD8" stroke-width="2.5"/><line x1="28" y1="24" x2="46" y2="24" stroke="#9DB8F5" stroke-width="2.5" stroke-linecap="round"/><line x1="28" y1="32" x2="46" y2="32" stroke="#9DB8F5" stroke-width="2.5" stroke-linecap="round"/><line x1="28" y1="40" x2="40" y2="40" stroke="#9DB8F5" stroke-width="2.5" stroke-linecap="round"/>'
  };
  const thumbSVG = (type) =>
    `<svg viewBox="0 0 74 62" aria-hidden="true">${THUMBS[type] || THUMBS.line}</svg>`;

  const fmtDate = (iso) => {
    const [, m, d] = iso.split("-").map(Number);
    return `${m}月${d}日`;
  };
  /* ISO日付にn日足す(月またぎ対応) */
  const addDaysISO = (iso, n) => {
    const d = new Date(iso + "T00:00:00");
    d.setDate(d.getDate() + n);
    const p = (x) => String(x).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  };
  /* その指標発表日(または翌日以降2日以内)で最も早い相場観記事(analysis/news)を探す。
     day.articleId があれば手動指定を優先する */
  const findMorningArticle = (day, articles) => {
    if (day.articleId) {
      const forced = articles.find(a => a.id === day.articleId);
      if (forced) return forced;
    }
    if (!day.date) return null;
    const start = day.date, end = addDaysISO(day.date, 2);
    const candidates = articles
      .filter(a => (a.category === "analysis" || a.category === "news") && a.date >= start && a.date <= end)
      .sort((a, b) => a.date.localeCompare(b.date));
    return candidates[0] || null;
  };
  const fmtFullDate = (iso) => {
    const [y, m, d] = iso.split("-").map(Number);
    return `${y}年${m}月${d}日`;
  };
  const readMinutes = (a) => {
    let chars = (a.leadPara || "").length;
    (a.sections || []).forEach(s => (s.body || []).forEach(p => chars += p.length));
    return Math.max(2, Math.round(chars / 450));
  };

  /* ---------- rate board ---------- */
  const fmtPrice = (pair, v) => pair.endsWith("JPY") ? v.toFixed(2) : v.toFixed(4);

  const renderRates = (pairs) => {
    const board = $("#rateBoard");
    if (!board) return;
    board.innerHTML = pairs.map(p => {
      const dir = p.changePct > 0.005 ? "up" : p.changePct < -0.005 ? "down" : "flat";
      const sign = p.changePct > 0 ? "+" : p.changePct < 0 ? "−" : "±";
      const sparkDir = dir === "down" ? "down" : "up";
      return `<article class="rate-card">
        <div class="pair-row"><span class="pair">${p.pair}</span>
          <span class="chg ${dir}">${sign}${Math.abs(p.changePct).toFixed(2)}%</span></div>
        <div class="price">${fmtPrice(p.pair, p.price)}</div>
        ${sparkSVG(p.history, sparkDir, true)}
      </article>`;
    }).join("");
  };

  const loadRates = async () => {
    const data = await fetchJSON("data/rates.json");
    renderRates(data.pairs);
    const note = $("#rateNote");
    if (!note) return;
    const when = data.updatedAt || data.updated;
    /* 日中足はYahoo側にCORSが無いのでブラウザからは取り直せない。
       tools/update_rates.py が焼き込んだ値をそのまま出す */
    note.textContent = data.source === "ecb"
      ? `欧州中央銀行の参考レート(${when}時点)・1日1回更新`
      : `15分足の参考値(${when} JST時点)。リアルタイムではありません`;
  };


  /* ---------- 夜明けバンドの時計: FXの24時間(6:00起点)と「いま」 ---------- */
  const renderClock = () => {
    const marker = $("#nowMarker"), label = $("#nowLabel"), date = $("#mastDate");
    if (!marker) return;
    const tick = () => {
      const d = new Date();
      const mins = (d.getHours() * 60 + d.getMinutes() - 6 * 60 + 1440) % 1440;
      const pct = mins / 1440 * 100;
      marker.style.left = `${pct}%`;
      label.style.left = `${pct}%`;
      label.textContent = `いま ${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
      if (date) {
        const w = "日月火水木金土"[d.getDay()];
        date.textContent = `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日(${w})`;
      }
    };
    /* 最初は左端から「いま」まで動かす(reduced-motionではCSS側で即時) */
    tick();
    setInterval(tick, 60 * 1000);
  };

  /* ---------- article renderers ---------- */
  const cardHTML = (a) => {
    const c = CAT[a.category];
    return `<a class="article-card" href="post/${a.id}.html">
      <span class="thumb">${thumbSVG(a.thumb)}</span>
      <span class="meta">
        <span class="cat ${c.cls}">${c.label}</span>
        <h3>${a.title}</h3>
        <span class="lead-line">${a.lead}</span>
      </span>
      <span class="date">${fmtDate(a.date)}</span>
    </a>`;
  };

  const renderHome = async () => {
    const [articles, cal] = await Promise.all([
      fetchJSON("data/articles.json"),
      fetchJSON("data/calendar.json")
    ]);
    const featured = articles.find(a => a.featured) || articles[0];
    const rest = articles.filter(a => a.id !== featured.id);

    const fc = CAT[featured.category];
    const fh = featured.hero || {};
    $("#featured").innerHTML = `
      <span class="eyebrow">今朝の一本 · ${fc.label}</span>
      <h2>${featured.title}</h2>
      <p>${featured.lead}</p>
      <span class="more">続きを読む →</span>`;
    $("#featured").href = `post/${featured.id}.html`;

    const marketArticles = rest.filter(a => a.category === "analysis" || a.category === "news").slice(0, 6);
    const basicsArticles = rest.filter(a => a.category === "technical").slice(0, 6);
    $("#marketList").innerHTML = marketArticles.map(cardHTML).join("");
    $("#basicsList").innerHTML = basicsArticles.map(cardHTML).join("");

    const popularIds = ["2026-07-29-order-types", "2026-07-31-rsi-basics", "2026-08-02-moving-average"];
    $("#popularList").innerHTML = popularIds
      .map(id => articles.find(a => a.id === id)).filter(Boolean)
      .map((a, i) => `<li><span class="num">${i + 1}</span><a href="post/${a.id}.html">${a.title}</a></li>`)
      .join("");

    // 1日1件(重要度の高いもの)に絞り、「高」を優先しつつ時系列で3件表示
    const rank = { hi: 2, mid: 1, lo: 0 };
    const today = todayISO();
    const upcoming = cal.days.filter(d => !d.date || d.date >= today);
    const perDay = (upcoming.length ? upcoming : cal.days)
      .filter(day => day.items.length)
      .map((day, idx) => {
        const best = [...day.items].sort((a, b) => rank[b.imp] - rank[a.imp])[0];
        return { idx, label: day.label, date: day.date, articleId: day.articleId, ...best };
      });
    const picked = [...perDay]
      .sort((a, b) => (rank[b.imp] - rank[a.imp]) || (a.idx - b.idx))
      .slice(0, 3)
      .sort((a, b) => a.idx - b.idx);
    const impLabel = { hi: "高", mid: "中", lo: "低" };
    const shortDay = (label) => {
      const m = label.match(/(\d+)月(\d+)日\((.)\)/);
      return m ? `${m[1]}/${m[2]} ${m[3]}` : label;
    };
    $("#weekCal").innerHTML = picked.map(x => {
      let linkRow = "";
      if (x.date && x.date < today && x.imp === "hi") {
        const art = findMorningArticle(x, articles);
        if (art) linkRow = `<tr><td colspan="3" class="cal-mini-link"><a href="post/${art.id}.html">→ 翌朝の相場観を読む</a></td></tr>`;
      }
      return `<tr>
        <td class="d">${shortDay(x.label)}</td>
        <td>${x.country} ${x.name}</td>
        <td class="imp ${x.imp}">${impLabel[x.imp]}</td></tr>${linkRow}`;
    }).join("");
  };

  /* 「相場観」= analysis+news、「FX入門」= technical のグループ絞り込み。?cat= で共有・ブックマーク可能にする */
  const CAT_GROUP = { market: ["analysis", "news"], basics: ["technical"] };
  const renderList = async () => {
    const articles = await fetchJSON("data/articles.json");
    const listEl = $("#articleList");
    const chips = document.querySelectorAll(".filter-chips button");
    const draw = (key) => {
      const items = key === "all" ? articles
        : CAT_GROUP[key] ? articles.filter(a => CAT_GROUP[key].includes(a.category))
        : articles.filter(a => a.category === key);
      listEl.innerHTML = items.map(cardHTML).join("") ||
        `<p style="color:var(--muted);font-size:14px;">このカテゴリの記事はまだありません。毎朝の分析でこれから増えていきます。</p>`;
    };
    const select = (key) => {
      chips.forEach(b => b.classList.toggle("on", b.dataset.cat === key));
      draw(key);
      markNavCat();
    };
    chips.forEach(btn => btn.addEventListener("click", () => {
      const u = new URL(location.href);
      if (btn.dataset.cat === "all") u.searchParams.delete("cat");
      else u.searchParams.set("cat", btn.dataset.cat);
      history.replaceState(null, "", u);
      select(btn.dataset.cat);
    }));
    select(new URLSearchParams(location.search).get("cat") || "all");
  };

  const renderArticle = async () => {
    const id = new URLSearchParams(location.search).get("id");
    const articles = await fetchJSON("data/articles.json");
    const a = articles.find(x => x.id === id) || articles[0];
    const c = CAT[a.category];
    document.title = `${a.title} | よっちゃんのFX`;
    const canon = document.createElement("link"); canon.rel = "canonical"; canon.href = `https://yocchan-fx.com/post/${a.id}.html`; document.head.appendChild(canon);

    let heroHTML = "";
    if (a.hero) {
      const chg = a.hero.change || "";
      const dir = chg.startsWith("-") || chg.startsWith("−") ? "down" : "up";
      heroHTML = `<div class="hero-chart">
        ${heroChartSVG(heroShape(dir))}
        <span class="eyebrow">${a.hero.label || a.hero.pair}</span>
        <span class="big">${a.hero.price}<span class="chg-inline ${dir}">${chg}</span></span>
      </div>`;
    }

    const sectionsHTML = (a.sections || []).map(s => {
      const scen = (s.scenarios || []).map(sc =>
        `<div class="scenario-card s-${sc.tone}"><span class="tag">${sc.tag}</span><span>${sc.text}</span></div>`
      ).join("");
      return `<h2>${s.h}</h2>${(s.body || []).map(p => `<p>${p}</p>`).join("")}${scen ? `<div class="scenario">${scen}</div>` : ""}`;
    }).join("");

    const sourcesHTML = (a.sources || []).length
      ? `<div class="source-box"><div class="label">参考にした記事</div><ul>${
          a.sources.map(s => `<li><a href="${s.url}" target="_blank" rel="noopener noreferrer">${s.title}</a><span class="pub">${s.publisher}</span></li>`).join("")
        }</ul></div>`
      : "";

    let seeAlsoHTML = "";
    if (a.category === "technical") {
      const marketArticle = articles
        .filter(x => x.category === "analysis" || x.category === "news")
        .sort((x, y) => y.date.localeCompare(x.date))[0];
      if (marketArticle) {
        seeAlsoHTML = `<div class="see-also">実際の相場ではどう動くか。<a href="post/${marketArticle.id}.html">毎朝の相場観もあわせてどうぞ →</a></div>`;
      }
    } else {
      seeAlsoHTML = `<div class="see-also">用語でつまずいたら。<a href="articles.html?cat=basics">FX入門の記事一覧を見る →</a></div>`;
    }

    $("#article").innerHTML = `
      <span class="cat ${c.cls}">${c.label}</span>
      <h1>${a.title}</h1>
      <div class="byline"><span>${fmtFullDate(a.date)}</span><span>${readMinutes(a)}分で読める</span><span class="who"><img src="assets/img/fx_icon.png?v=3" alt="">${AUTHOR}</span></div>
      ${heroHTML}
      <div class="point-box"><div class="label">この記事のポイント</div>
        <ul>${a.points.map(p => `<li>${p}</li>`).join("")}</ul></div>
      <p class="lead-para">${a.leadPara}</p>
      ${sectionsHTML}
      ${a.memo ? `<div class="memo-box"><img class="memo-owl" src="assets/img/fx_icon.png?v=3" alt=""><div><b>ヨル教授メモ:</b> ${a.memo}</div></div>` : ""}
      ${seeAlsoHTML}
      ${adBox(["matsui", "hirose"], "FX口座の開設はこちら", true)}
      <div class="tag-row">タグ: ${(a.tags || []).map(t => `<span class="pill">${t}</span>`).join("")}</div>
      ${sourcesHTML}
      <div class="disclaimer-inline">当サイトの内容は情報提供を目的としたもので、特定の取引や売買タイミングを推奨するものではありません。投資の最終判断はご自身の責任でお願いします。</div>`;
  };

  const renderCalendar = async () => {
    const [cal, articles] = await Promise.all([
      fetchJSON("data/calendar.json"),
      fetchJSON("data/articles.json")
    ]);
    $("#calRange").textContent = cal.range;
    const today = todayISO();

    const dayRows = (days) => days.map(day => {
      const state = !day.date ? "" : day.date < today ? "past" : day.date === today ? "today" : "";
      const badge = state === "today" ? `<span class="today-badge">今日</span>` : "";
      let morningLink = "";
      if (state === "past" && day.items.some(it => it.imp === "hi")) {
        const art = findMorningArticle(day, articles);
        if (art) morningLink = `<a class="cal-morning-link" href="post/${art.id}.html">→ 翌朝の相場観を読む</a>`;
      }
      const dayRow = `<tr class="day-row ${state}"${state === "today" ? ' id="calToday"' : ""}>
          <td colspan="6">${day.label}${badge}${morningLink}</td></tr>`;
      const items = day.items.map(it => {
        const actual = it.actual
          ? `<td class="num actual">${it.actual}</td>`
          : `<td class="num" style="color:var(--muted);">--</td>`;
        return `
        <tr class="${it.imp === "hi" ? "hot" : ""} ${state}">
          <td class="d" style="font-family:var(--font-data);font-size:12.5px;">${it.time}</td>
          <td><span class="flag">${it.flag}</span>${it.country}</td>
          <td><span class="bar ${it.imp}"></span><span class="ind">${it.name}</span></td>
          <td class="num prev">${it.prev}</td>
          <td class="num">${it.forecast}</td>
          ${actual}
        </tr>`;
      }).join("");
      return dayRow + items;
    }).join("");

    const empty = `<tr><td colspan="6" style="color:var(--muted);font-size:13.5px;padding:20px 16px;">
        この条件に当てはまる指標はありません。</td></tr>`;

    /* データに含まれる月(YYYY-MM)を古い順に。初期表示は今月、無ければ今日に一番近い月 */
    const months = [...new Set(cal.days.map(d => d.date.slice(0, 7)))].sort();
    const thisMonth = today.slice(0, 7);
    let mi = months.indexOf(thisMonth);
    if (mi < 0) mi = Math.max(0, months.findIndex(m => m >= thisMonth));
    let hiOnly = false;

    const monthLabel = (m) => `${Number(m.slice(0, 4))}年${Number(m.slice(5, 7))}月`;

    const draw = () => {
      const m = months[mi];
      let days = cal.days.filter(d => d.date.slice(0, 7) === m);
      const total = days.reduce((s, d) => s + d.items.length, 0);
      if (hiOnly) days = days
        .map(d => ({ ...d, items: d.items.filter(it => it.imp === "hi") }))
        .filter(d => d.items.length);

      $("#calBody").innerHTML = dayRows(days) || empty;
      $("#calMonth").textContent = monthLabel(m);
      $("#calPrev").disabled = mi === 0;
      $("#calNext").disabled = mi === months.length - 1;
      $("#calRange").textContent =
        `${monthLabel(m)}の主要指標 ${total}件・時刻はすべて日本時間です`;

      const mark = $("#calToday");
      if (mark) mark.scrollIntoView({ block: "center", behavior: "smooth" });
    };

    $("#calPrev").addEventListener("click", () => { if (mi > 0) { mi--; draw(); } });
    $("#calNext").addEventListener("click", () => { if (mi < months.length - 1) { mi++; draw(); } });
    const hiBtn = $("#calHiOnly");
    hiBtn.addEventListener("click", () => {
      hiOnly = !hiOnly;
      hiBtn.classList.toggle("on", hiOnly);
      hiBtn.setAttribute("aria-pressed", String(hiOnly));
      draw();
    });
    draw();
  };

  /* グローバルナビの「相場観」「FX入門」は articles.html?cat=... へのリンクなので、
     現在地のクエリに合わせてどちらがアクティブかをJSで判定する */
  const markNavCat = () => {
    const links = document.querySelectorAll('.global-nav a[href*="cat="]');
    if (!links.length) return;
    const onList = document.body.dataset.page === "list";
    const cat = new URLSearchParams(location.search).get("cat") || "all";
    links.forEach(a => {
      const linkCat = new URL(a.getAttribute("href"), location.href).searchParams.get("cat");
      a.classList.toggle("active", onList && linkCat === cat);
    });
  };

  /* ---------- boot ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    markNavCat();
    const page = document.body.dataset.page;
    if (page === "home") {
      loadRates(); renderHome(); renderClock();
      const side = $("#adSidebar");
      if (side) side.innerHTML = adBox(["matsui", "hirose"], "FX口座を開くなら", true);
    }
    if (page === "list") renderList();
    if (page === "article") renderArticle();
    if (page === "calendar") renderCalendar();
  });
})();
