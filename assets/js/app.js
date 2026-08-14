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
    const local = await fetchJSON("data/rates.json");
    renderRates(local.pairs);
    const note = $("#rateNote");
    if (note) note.textContent = `レートは1日1回更新の参考値です(${local.updated}時点)`;
    try {
      const end = new Date();
      const start = new Date(end.getTime() - 30 * 864e5);
      const d = (x) => x.toISOString().slice(0, 10);
      const range = `${d(start)}..${d(end)}`;
      const [usd, gbp, eur] = await Promise.all([
        fetchJSON(`https://api.frankfurter.dev/v1/${range}?from=USD&to=JPY`),
        fetchJSON(`https://api.frankfurter.dev/v1/${range}?from=GBP&to=USD,JPY`),
        fetchJSON(`https://api.frankfurter.dev/v1/${range}?from=EUR&to=USD`)
      ]);
      const series = (resp, sym) =>
        Object.keys(resp.rates).sort().map(k => resp.rates[k][sym]);
      const build = (pair, resp, sym) => {
        const h = series(resp, sym);
        const price = h[h.length - 1];
        const prev = h[h.length - 2] || price;
        return { pair, price, changePct: ((price - prev) / prev) * 100, history: h.slice(-15) };
      };
      const live = [
        build("USD/JPY", usd, "JPY"),
        build("GBP/USD", gbp, "USD"),
        build("EUR/USD", eur, "USD"),
        build("GBP/JPY", gbp, "JPY")
      ];
      renderRates(live);
      const last = Object.keys(usd.rates).sort().pop();
      if (note) note.textContent = `欧州中央銀行の参考レート(${last}時点)・1日1回更新`;
    } catch (e) {
      /* offline or API unavailable — keep local fallback */
    }
  };

  /* ---------- article renderers ---------- */
  const cardHTML = (a) => {
    const c = CAT[a.category];
    return `<a class="article-card" href="article.html?id=${a.id}">
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
      <div class="visual">
        <span class="eyebrow">FEATURED · ${fc.label}</span>
        <span class="big">${fh.pair || ""} ${fh.price || ""}</span>
      </div>
      <div class="body">
        <span class="cat ${fc.cls}">${fc.label}</span>
        <h2>${featured.title}</h2>
        <p>${featured.lead}</p>
        <div>${(featured.tags || []).map(t => `<span class="pill" style="font-size:12px;background:var(--primary-soft);color:var(--primary);padding:3px 12px;border-radius:99px;margin-right:6px;">${t}</span>`).join("")}</div>
      </div>`;
    $("#featured").href = `article.html?id=${featured.id}`;

    $("#latestList").innerHTML = rest.slice(0, 3).map(cardHTML).join("");

    const popularIds = ["2026-07-29-order-types", "2026-07-31-rsi-basics", "2026-08-02-moving-average"];
    $("#popularList").innerHTML = popularIds
      .map(id => articles.find(a => a.id === id)).filter(Boolean)
      .map((a, i) => `<li><span class="num">${i + 1}</span><a href="article.html?id=${a.id}">${a.title}</a></li>`)
      .join("");

    // 1日1件(重要度の高いもの)に絞り、「高」を優先しつつ時系列で3件表示
    const rank = { hi: 2, mid: 1, lo: 0 };
    const today = todayISO();
    const upcoming = cal.days.filter(d => !d.date || d.date >= today);
    const perDay = (upcoming.length ? upcoming : cal.days)
      .filter(day => day.items.length)
      .map((day, idx) => {
        const best = [...day.items].sort((a, b) => rank[b.imp] - rank[a.imp])[0];
        return { idx, label: day.label, ...best };
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
    $("#weekCal").innerHTML = picked.map(x => `<tr>
        <td class="d">${shortDay(x.label)}</td>
        <td>${x.country} ${x.name}</td>
        <td class="imp ${x.imp}">${impLabel[x.imp]}</td></tr>`)
      .join("");
  };

  const renderList = async () => {
    const articles = await fetchJSON("data/articles.json");
    const listEl = $("#articleList");
    const chips = document.querySelectorAll(".filter-chips button");
    const draw = (key) => {
      const items = key === "all" ? articles : articles.filter(a => a.category === key);
      listEl.innerHTML = items.map(cardHTML).join("") ||
        `<p style="color:var(--muted);font-size:14px;">このカテゴリの記事はまだありません。毎朝の分析でこれから増えていきます。</p>`;
    };
    chips.forEach(btn => btn.addEventListener("click", () => {
      chips.forEach(b => b.classList.toggle("on", b === btn));
      draw(btn.dataset.cat);
    }));
    draw("all");
  };

  const renderArticle = async () => {
    const id = new URLSearchParams(location.search).get("id");
    const articles = await fetchJSON("data/articles.json");
    const a = articles.find(x => x.id === id) || articles[0];
    const c = CAT[a.category];
    document.title = `${a.title} | よっちゃんのFX`;

    let heroHTML = "";
    if (a.hero) {
      const chg = a.hero.change || "";
      const dir = chg.startsWith("-") || chg.startsWith("−") ? "down" : "up";
      heroHTML = `<div class="hero-chart">
        ${heroChartSVG([3, 2.7, 3.3, 3.0, 3.7, 3.4, 4.2, 3.9, 4.5, 4.2, 5.0, 4.7, 5.3])}
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
      <div class="tag-row">タグ: ${(a.tags || []).map(t => `<span class="pill">${t}</span>`).join("")}</div>
      ${sourcesHTML}
      <div class="disclaimer-inline">当サイトの内容は情報提供を目的としたもので、特定の取引や売買タイミングを推奨するものではありません。投資の最終判断はご自身の責任でお願いします。</div>`;
  };

  const renderCalendar = async () => {
    const cal = await fetchJSON("data/calendar.json");
    $("#calRange").textContent = cal.range;
    const today = todayISO();

    const dayRows = (days) => days.map(day => {
      const state = !day.date ? "" : day.date < today ? "past" : day.date === today ? "today" : "";
      const badge = state === "today" ? `<span class="today-badge">今日</span>` : "";
      const dayRow = `<tr class="day-row ${state}"${state === "today" ? ' id="calToday"' : ""}>
          <td colspan="6">${day.label}${badge}</td></tr>`;
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
        該当する指標がありません。</td></tr>`;

    const draw = (key) => {
      let days = cal.days;
      if (key === "ahead") days = days.filter(d => !d.date || d.date >= today);
      if (key === "hi") days = days
        .map(d => ({ ...d, items: d.items.filter(it => it.imp === "hi") }))
        .filter(d => d.items.length);
      $("#calBody").innerHTML = dayRows(days) || empty;
      const mark = $("#calToday");
      if (key === "all" && mark) mark.scrollIntoView({ block: "center", behavior: "smooth" });
    };

    const chips = document.querySelectorAll(".cal-chips button");
    chips.forEach(btn => btn.addEventListener("click", () => {
      chips.forEach(b => b.classList.toggle("on", b === btn));
      draw(btn.dataset.cal);
    }));
    draw("ahead");
  };

  /* ---------- boot ---------- */
  document.addEventListener("DOMContentLoaded", () => {
    const page = document.body.dataset.page;
    if (page === "home") { loadRates(); renderHome(); }
    if (page === "list") renderList();
    if (page === "article") renderArticle();
    if (page === "calendar") renderCalendar();
  });
})();
