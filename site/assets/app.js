// Renders the whole page from figures.json (numbers) + I18N (labels).
// No study number is hardcoded in HTML; everything numeric flows from here.
let FIG = null, EXPLORER = null, LANG = localStorage.getItem("cz_lang") || "uk";

const $ = (s, r = document) => r.querySelector(s);
const el = (t, cls, txt) => { const e = document.createElement(t); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const T = (k) => (I18N[LANG] && I18N[LANG][k]) || k;
const pct = (x) => (x == null || Number.isNaN(x)) ? "—" : (x * 100).toFixed(2) + "%";
const f3 = (x) => (x == null || Number.isNaN(x)) ? "—" : Number(x).toFixed(3);
const f4 = (x) => (x == null || Number.isNaN(x)) ? "—" : Number(x).toFixed(4);

async function boot() {
  try {
    FIG = await (await fetch("figures.json")).json();
  } catch (e) { document.body.innerHTML = "<p style='padding:40px'>figures.json not built yet — run <code>make all</code>.</p>"; return; }
  try { EXPLORER = await (await fetch("explorer/index.json")).json(); } catch (e) { EXPLORER = null; }
  applyLang();
  $("#lang").onclick = () => { LANG = LANG === "uk" ? "en" : "uk"; localStorage.setItem("cz_lang", LANG); applyLang(); };
}

// Fill {TOKEN} placeholders in an i18n string with values from figures.json.
function fillTokens(str, map) {
  return str.replace(/\{([A-Z0-9_]+)\}/g, (_, k) => (map[k] != null ? map[k] : "—"));
}

function renderPress() {
  const cov = FIG.coverage?.by_outlet_period || {};
  const sum = (o) => Object.values(o || {}).reduce((a, b) => a + b, 0);
  const ukr = sum(cov.ukrinform);
  const ctrl = sum(cov.pravda) + sum(cov.suspilne);
  const g = FIG.gold_standard;
  const rate = (pk) => {
    const x = g && g.by_period && g.by_period[pk];
    return x && x.n ? (100 * (x.tp + x.fn) / x.n).toFixed(1) : null;
  };
  const map = {
    TOTAL: (ukr + ctrl).toLocaleString(LANG === "uk" ? "uk-UA" : "en-US"),
    UKR: ukr.toLocaleString(LANG === "uk" ? "uk-UA" : "en-US"),
    CTRL: ctrl.toLocaleString(LANG === "uk" ? "uk-UA" : "en-US"),
    GOLD_N: g ? g.n_annotated : null,
    PREC: g && g.overall && g.overall.precision != null ? (100 * g.overall.precision).toFixed(0) : null,
    REC: g && g.overall && g.overall.recall != null ? (100 * g.overall.recall).toFixed(0) : null,
    P0R: rate("P0"), P1R: rate("P1"), P2R: rate("P2"),
  };
  $("#press-what").textContent = fillTokens(T("press_what"), map);
  $("#press-f1").textContent = fillTokens(T("press_f1"), map);
  $("#press-f2").textContent = fillTokens(T("press_f2"), map);
  $("#press-f3").textContent = fillTokens(T("press_f3"), map);
  $("#press-cmd").textContent =
    "git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2\nuv sync --frozen && make verify";
}

function applyLang() {
  document.documentElement.lang = LANG;
  $("#lang").textContent = LANG === "uk" ? "EN" : "UA";
  document.querySelectorAll("[data-i18n]").forEach(n => { n.textContent = T(n.dataset.i18n); });
  buildNav(); renderPress(); renderVerdict(); renderRates(); renderContrasts();
  renderSensitivity(); renderPeriods(); renderGold(); renderVerification();
  renderLimits(); renderExplorer();
}

function buildNav() {
  const nav = $("#nav"); nav.innerHTML = "";
  [["#press", "nav_press"], ["#tldr", "nav_tldr"], ["#method", "nav_method"], ["#sensitivity", "nav_sens"],
   ["#validation", "nav_valid"], ["#verification", "nav_verif"], ["#limits", "nav_limits"],
   ["#explorer", "nav_explorer"]].forEach(([href, k]) => {
    const a = el("a", null, T(k)); a.href = href; nav.appendChild(a);
  });
  const rep = el("a", null, T("nav_report"));
  rep.href = LANG === "uk" ? "report_uk.html" : "report_en.html";
  nav.appendChild(rep);
}

function renderVerdict() {
  const box = $("#verdict"); box.innerHTML = "";
  const v = FIG.verdict || {};
  const ti = FIG.trend_interpretable || {};
  const coverageThin = (FIG.rates?.parket?.P1?.n || 0) < 50;
  let msg, cls;
  if (coverageThin) { msg = T("verdict_pending"); cls = ""; }
  else if (ti.recall_confounded === true) { msg = T("verdict_confounded"); cls = ""; }
  else if (v.implied_pattern_supported) { msg = T("verdict_supported"); cls = "yes"; }
  else { msg = T("verdict_not"); cls = "no"; }
  box.appendChild(el("span", "flag " + cls, msg));
  // Always show the validation one-liner when the gold standard has run.
  if (ti.status === "evaluated") {
    box.appendChild(el("div", "fine", T("verdict_gold_line")
      .replace("{P}", (ti.precision != null ? (ti.precision * 100).toFixed(0) : "—"))
      .replace("{R}", (ti.recall != null ? (ti.recall * 100).toFixed(0) : "—"))
      .replace("{S}", (ti.recall_spread_pp != null ? ti.recall_spread_pp.toFixed(0) : "—"))));
  }
}

function renderRates() {
  const host = $("#rates-table"); host.innerHTML = "";
  const r = FIG.rates; if (!r) return;
  const tbl = el("table");
  const head = el("tr");
  ["th_period", "th_parket", "th_balance", "th_n"].forEach(k => head.appendChild(el("th", null, T(k))));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  (FIG.periods || []).forEach(p => {
    const tr = el("tr");
    tr.appendChild(el("td", null, p.key + " — " + (LANG === "uk" ? p.label_ua : p.label_en)));
    tr.appendChild(el("td", null, pct(r.parket?.[p.key]?.standardized)));
    tr.appendChild(el("td", null, pct(r.balance?.[p.key]?.standardized)));
    tr.appendChild(el("td", null, (r.parket?.[p.key]?.n ?? "—").toLocaleString()));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); host.appendChild(tbl);
}

function renderContrasts() {
  const host = $("#contrasts-table"); host.innerHTML = "";
  const c = FIG.contrasts; if (!c) return;
  const tbl = el("table");
  const head = el("tr");
  ["th_contrast", "th_ra", "th_rb", "th_h", "th_praw", "th_pholm"].forEach(k => head.appendChild(el("th", null, T(k))));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  Object.keys(c).sort().forEach(label => {
    const x = c[label]; const tr = el("tr");
    tr.appendChild(el("td", null, label));
    tr.appendChild(el("td", null, pct(x.rate_a)));
    tr.appendChild(el("td", null, pct(x.rate_b)));
    tr.appendChild(el("td", null, `${f3(x.cohen_h)} [${f3(x.h_ci_low)}, ${f3(x.h_ci_high)}]`));
    tr.appendChild(el("td", null, f4(x.p_raw)));
    tr.appendChild(el("td", null, f4(x.p_holm)));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); host.appendChild(tbl);
}

function renderSensitivity() {
  const ctl = $("#sens-controls"); ctl.innerHTML = "";
  const opts = {
    sc_thr: [["1", "1"], ["2", "2"]],
    req_focus: [["1", T("yes")], ["0", T("no")]],
    ato: [["excluded", T("exc")], ["included", T("inc")]],
    univ: [["primary7", T("primary7")], ["plus_world", T("plusworld")]],
    std: [["direct", T("direct")], ["crude", T("crude")]],
  };
  const labels = { sc_thr: "sc_thr", req_focus: "req_focus", ato: "ato", univ: "univ", std: "std" };
  const state = window.__sens || { sc_thr: "1", req_focus: "1", ato: "excluded", univ: "primary7", std: "direct" };
  window.__sens = state;
  for (const key of Object.keys(opts)) {
    const lab = el("label", null, T(labels[key]));
    const sel = el("select");
    opts[key].forEach(([v, t]) => { const o = el("option", null, t); o.value = v; if (state[key] === v) o.selected = true; sel.appendChild(o); });
    sel.onchange = () => { state[key] = sel.value; renderSensOut(); };
    lab.appendChild(sel); ctl.appendChild(lab);
  }
  renderSensOut();
}

function renderSensOut() {
  const host = $("#sens-out"); host.innerHTML = "";
  const s = window.__sens;
  const key = `sc${s.sc_thr}_focus${s.req_focus}_ato${s.ato}_${s.univ}_${s.std}`;
  const cell = FIG.sensitivity?.[key];
  if (!cell) { host.appendChild(el("p", "fine", "n/a")); return; }
  ["parket", "balance"].forEach(outcome => {
    const tbl = el("table");
    const head = el("tr");
    head.appendChild(el("th", null, outcome === "parket" ? T("th_parket") : T("th_balance")));
    (FIG.periods || []).forEach(p => head.appendChild(el("th", null, p.key)));
    const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
    const tr = el("tr"); tr.appendChild(el("td", null, "rate"));
    (FIG.periods || []).forEach(p => tr.appendChild(el("td", null, pct(cell[outcome]?.[p.key]?.rate))));
    const tb = el("tbody"); tb.appendChild(tr); tbl.appendChild(tb);
    host.appendChild(tbl);
  });
}

function renderPeriods() {
  const host = $("#periods-list"); host.innerHTML = "";
  (FIG.periods || []).forEach(p => {
    const d = el("div", "period");
    d.innerHTML = `<b>${p.key}</b> ${p.start} → ${p.end}`;
    d.appendChild(document.createTextNode(" — " + (LANG === "uk" ? p.label_ua : p.label_en)));
    host.appendChild(d);
  });
  const body = $("#method-body"); body.innerHTML = "";
  const cov = FIG.coverage?.by_outlet_period;
  if (cov) {
    const line = el("p", "coverage", T("cov_note") + ": " +
      Object.entries(cov).map(([o, per]) => `${o} ` +
        Object.entries(per).map(([pk, n]) => `${pk}:${n.toLocaleString()}`).join(" ")).join("  •  "));
    body.appendChild(line);
  }
  if (FIG.notes) {
    Object.values(FIG.notes).forEach(t => body.appendChild(el("p", "fine", t)));
  }
}

function renderGold() {
  const host = $("#gold-out"); host.innerHTML = "";
  const g = FIG.gold_standard;
  if (!g) { host.appendChild(el("p", "fine", T("gold_pending"))); return; }
  const o = g.overall || {};
  const tbl = el("table");
  const head = el("tr"); ["", T("gold_prec"), T("gold_rec"), T("gold_f1"), T("gold_n")].forEach(t => head.appendChild(el("th", null, t)));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  const row = (name, x) => { const tr = el("tr"); tr.appendChild(el("td", null, name));
    tr.appendChild(el("td", null, f3(x.precision))); tr.appendChild(el("td", null, f3(x.recall)));
    tr.appendChild(el("td", null, f3(x.f1))); tr.appendChild(el("td", null, (x.n ?? "—").toLocaleString())); tb.appendChild(tr); };
  row("overall", o);
  Object.entries(g.by_period || {}).forEach(([pk, x]) => row(pk, x));
  tbl.appendChild(tb); host.appendChild(tbl);
  const rd = g.recall_drift || {};
  if (rd.confounded != null) {
    host.appendChild(el("p", "fine", T("gold_drift") + ": " + (rd.confounded ? T("gold_conf_yes") : T("gold_conf_no")) +
      (rd.p_value != null ? ` (p=${f4(rd.p_value)}, Δrecall=${(rd.recall_spread_pp ?? 0).toFixed(1)}pp)` : "")));
  }
}

function renderVerification() {
  $("#repro-cmd").textContent =
    "git clone https://github.com/alexmazuka/censorzero-v2 && cd censorzero-v2\nuv sync --frozen && make verify";
  const badge = $("#verif-badge"); badge.innerHTML = "";
  const a = el("a"); a.href = "https://github.com/alexmazuka/censorzero-v2/actions/workflows/verify.yml";
  a.className = "badge";
  const img = document.createElement("img");
  img.src = "https://github.com/alexmazuka/censorzero-v2/actions/workflows/verify.yml/badge.svg";
  img.alt = "CI status"; a.appendChild(img); badge.appendChild(a);
  const ht = $("#hash-table"); ht.innerHTML = "";
  const inputs = FIG.verification?.inputs_sha256;
  if (inputs) {
    Object.entries(inputs).slice(0, 40).forEach(([f, h]) => {
      ht.appendChild(el("div", "hash", `${f}  ${h}`));
    });
  }
}

function renderLimits() {
  const ul = $("#limits-list"); ul.innerHTML = "";
  const items = (FIG.limitations && FIG.limitations[LANG]) || [];
  items.forEach(t => ul.appendChild(el("li", null, t)));
}

// ---- Explorer: two tabs (Articles / Gold), designed for a non-technical
// visitor. Article data loads once per outlet (browse/{outlet}.json) and all
// filtering/search after that happens client-side with no further network
// calls. Gold data (blind annotation) is one small file, always fully loaded.

const EX = {
  outlet: "ukrinform", period: "all", status: "all", q: "",
  cache: {}, shown: 60,
};
const GOLD_EX = { status: "all", q: "", rows: null, shown: 60 };

function initExplorerTabs() {
  const tabs = $("#ex-tabs");
  tabs.querySelectorAll(".tab-btn").forEach(btn => {
    btn.onclick = () => switchExTab(btn.dataset.tab);
  });
  $("#cta-articles").onclick = () => { switchExTab("articles"); scrollToExplorer(); };
  $("#cta-gold").onclick = () => { switchExTab("gold"); scrollToExplorer(); };
  $("#ex-search").oninput = (e) => { EX.q = e.target.value; EX.shown = 60; renderArticleList(); };
  $("#gold-search").oninput = (e) => { GOLD_EX.q = e.target.value; GOLD_EX.shown = 60; renderGoldList(); };
}

function scrollToExplorer() {
  document.getElementById("explorer").scrollIntoView({ behavior: "smooth", block: "start" });
}

function switchExTab(tab) {
  window.__extab = tab;
  $("#ex-tabs").querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === tab));
  $("#pane-articles").style.display = tab === "articles" ? "" : "none";
  $("#pane-gold").style.display = tab === "gold" ? "" : "none";
  if (tab === "articles") renderArticlesPane();
  else renderGoldPane();
}

function renderArticlesPane() {
  $("#ex-search").placeholder = T("ph_search_articles");
  const outlets = Object.keys((EXPLORER && EXPLORER.by_outlet) || { ukrinform: 1, pravda: 1, suspilne: 1 });
  const outletChips = $("#ex-outlet-chips"); outletChips.innerHTML = "";
  outlets.forEach(o => {
    const c = el("div", "chip" + (EX.outlet === o ? " active" : ""), o);
    c.onclick = () => { EX.outlet = o; EX.period = "all"; EX.shown = 60; renderPeriodChips(); loadOutletThen(renderArticleList); };
    outletChips.appendChild(c);
  });
  renderPeriodChips();
  renderStatusChips("#ex-status-chips", [
    ["all", T("chip_all"), null],
    ["parket", T("badge_parket"), "dot-parket"],
    ["balance", T("badge_balance"), "dot-balance"],
  ], EX.status, (v) => { EX.status = v; EX.shown = 60; renderArticleList(); });
  loadOutletThen(renderArticleList);
}

function renderPeriodChips() {
  const periods = ["all", ...(FIG.periods || []).map(p => p.key)];
  const host = $("#ex-period-chips"); host.innerHTML = "";
  periods.forEach(p => {
    const label = p === "all" ? T("chip_all") : p;
    const c = el("div", "chip" + (EX.period === p ? " active" : ""), label);
    c.onclick = () => { EX.period = p; EX.shown = 60; renderArticleList(); };
    host.appendChild(c);
  });
}

function renderStatusChips(sel, opts, current, onPick) {
  const host = $(sel); host.innerHTML = "";
  opts.forEach(([v, label, dotClass]) => {
    const c = el("div", "chip" + (current === v ? " active" : ""));
    if (dotClass) c.appendChild(el("span", "dot " + dotClass));
    c.appendChild(document.createTextNode(label));
    c.onclick = () => onPick(v);
    host.appendChild(c);
  });
}

async function loadOutletThen(cb) {
  if (EX.cache[EX.outlet]) { cb(); return; }
  $("#ex-loading").textContent = T("loading");
  $("#explorer-out").innerHTML = "";
  try {
    const rows = await (await fetch(`explorer/browse/${EX.outlet}.json`)).json();
    EX.cache[EX.outlet] = rows;
  } catch (e) {
    $("#ex-loading").textContent = "";
    $("#explorer-out").innerHTML = "";
    $("#explorer-out").appendChild(el("p", "fine", "n/a"));
    return;
  }
  $("#ex-loading").textContent = "";
  cb();
}

function normSearch(s) { return (s || "").toLowerCase(); }

function renderArticleList() {
  const rows = EX.cache[EX.outlet] || [];
  const q = normSearch(EX.q);
  const filtered = rows.filter(r => {
    if (EX.period !== "all" && r.p !== EX.period) return false;
    if (EX.status === "parket" && r.a !== "parket") return false;
    if (EX.status === "balance" && r.a !== "balance") return false;
    if (q && !normSearch(r.t).includes(q)) return false;
    return true;
  });
  const host = $("#explorer-out"); host.innerHTML = "";
  host.appendChild(el("p", "coverage",
    fillTokens(T(EX.q || EX.status !== "all" || EX.period !== "all" ? "n_found" : "n_shown"),
      { N: filtered.length.toLocaleString(), TOTAL: rows.length.toLocaleString() })));
  if (!filtered.length) { host.appendChild(el("p", "fine", T("no_results"))); return; }
  const list = el("div", "article-list");
  filtered.slice(0, EX.shown).forEach(r => list.appendChild(articleRow(r)));
  host.appendChild(list);
  if (filtered.length > EX.shown) {
    const btn = el("button", "load-more", T("load_more"));
    btn.onclick = () => { EX.shown += 100; renderArticleList(); };
    host.appendChild(btn);
  }
}

function articleRow(r) {
  const row = el("div", "article-row");
  row.appendChild(el("div", "a-date", r.d ? r.d.slice(0, 10) : ""));
  const a = el("a", "a-title", r.t || r.u);
  a.href = r.u; a.target = "_blank"; a.rel = "noopener";
  row.appendChild(a);
  const badges = el("div", "a-badges");
  if (r.a === "parket") badges.appendChild(el("span", "badge badge-parket", T("badge_parket")));
  else if (r.a === "balance") badges.appendChild(el("span", "badge badge-balance", T("badge_balance")));
  if (r.g === "parket") badges.appendChild(el("span", "badge badge-parket", T("badge_gparket")));
  else if (r.g === "non_parket") badges.appendChild(el("span", "badge badge-nonparket", T("badge_gnonparket")));
  else if (r.g === "military") badges.appendChild(el("span", "badge badge-military", T("badge_gmilitary")));
  row.appendChild(badges);
  return row;
}

function renderGoldPane() {
  $("#gold-search").placeholder = T("ph_search_gold");
  renderStatusChips("#gold-status-chips", [
    ["all", T("chip_all"), null],
    ["parket", T("badge_gparket"), "dot-parket"],
    ["non_parket", T("badge_gnonparket"), "dot-nonparket"],
    ["military", T("badge_gmilitary"), "dot-military"],
  ], GOLD_EX.status, (v) => { GOLD_EX.status = v; GOLD_EX.shown = 60; renderGoldList(); });
  loadGoldThen(renderGoldList);
}

async function loadGoldThen(cb) {
  if (GOLD_EX.rows) { cb(); return; }
  $("#gold-explorer-out").innerHTML = "";
  $("#gold-explorer-out").appendChild(el("p", "fine", T("loading")));
  try {
    GOLD_EX.rows = await (await fetch("explorer/gold.json")).json();
  } catch (e) {
    $("#gold-explorer-out").innerHTML = "";
    $("#gold-explorer-out").appendChild(el("p", "fine", "n/a"));
    return;
  }
  cb();
}

function renderGoldList() {
  const rows = GOLD_EX.rows || [];
  const q = normSearch(GOLD_EX.q);
  const filtered = rows.filter(r => {
    if (GOLD_EX.status !== "all" && r.gold !== GOLD_EX.status) return false;
    if (q && !normSearch(r.title).includes(q)) return false;
    return true;
  });
  const host = $("#gold-explorer-out"); host.innerHTML = "";
  host.appendChild(el("p", "coverage",
    fillTokens(T(GOLD_EX.q || GOLD_EX.status !== "all" ? "n_found" : "n_shown"),
      { N: filtered.length.toLocaleString(), TOTAL: rows.length.toLocaleString() })));
  if (!filtered.length) { host.appendChild(el("p", "fine", T("no_results"))); return; }
  const list = el("div", "article-list");
  filtered.slice(0, GOLD_EX.shown).forEach(r => {
    const row = el("div", "article-row");
    row.appendChild(el("div", "a-date", (r.date_published || "").slice(0, 10)));
    const a = el("a", "a-title", r.title || r.url);
    a.href = r.url; a.target = "_blank"; a.rel = "noopener";
    row.appendChild(a);
    const badges = el("div", "a-badges");
    if (r.gold === "parket") badges.appendChild(el("span", "badge badge-parket", T("badge_gparket")));
    else if (r.gold === "military") badges.appendChild(el("span", "badge badge-military", T("badge_gmilitary")));
    else badges.appendChild(el("span", "badge badge-nonparket", T("badge_gnonparket")));
    row.appendChild(badges);
    list.appendChild(row);
  });
  host.appendChild(list);
  if (filtered.length > GOLD_EX.shown) {
    const btn = el("button", "load-more", T("load_more"));
    btn.onclick = () => { GOLD_EX.shown += 100; renderGoldList(); };
    host.appendChild(btn);
  }
}

function renderExplorer() {
  initExplorerTabs();
  switchExTab(window.__extab || "articles");
}

boot();
