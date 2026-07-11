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

function renderExplorer() {
  const ctl = $("#explorer-controls"); ctl.innerHTML = "";
  const state = window.__ex || { mode: "summary", outlet: "", period: "", month: "", flt: "all" };
  window.__ex = state;

  const mkSel = (labelKey, opts, key, onchange) => {
    const lab = el("label", null, T(labelKey));
    const sel = el("select");
    opts.forEach(([v, t]) => { const o = el("option", null, t); o.value = v; if (state[key] === v) o.selected = true; sel.appendChild(o); });
    sel.onchange = () => { state[key] = sel.value; onchange(); };
    lab.appendChild(sel); ctl.appendChild(lab);
    return sel;
  };

  mkSel("ex_mode", [["summary", T("ex_mode_sum")], ["articles", T("ex_mode_art")], ["gold", T("ex_mode_gold")]],
    "mode", renderExplorer);

  if (!EXPLORER) { $("#explorer-out").innerHTML = ""; $("#explorer-out").appendChild(el("p", "fine", "n/a")); return; }

  if (state.mode === "articles") {
    const outlets = [...new Set(EXPLORER.shards.map(s => s.outlet))].sort();
    if (!state.outlet) state.outlet = outlets[0] || "";
    mkSel("ex_outlet", outlets.map(o => [o, o]), "outlet", () => { state.period = ""; state.month = ""; renderExplorer(); });
    const periods = [...new Set(EXPLORER.shards.filter(s => s.outlet === state.outlet).map(s => s.period))].sort();
    if (!periods.includes(state.period)) state.period = periods[0] || "";
    mkSel("ex_period", periods.map(p => [p, p]), "period", () => { state.month = ""; renderExplorer(); });
    const months = EXPLORER.shards.filter(s => s.outlet === state.outlet && s.period === state.period).map(s => s.month).sort();
    if (!months.includes(state.month)) state.month = months[0] || "";
    mkSel("ex_month", months.map(m => [m, m]), "month", renderExplorer);
    mkSel("ex_filter", [["all", T("ex_f_all")], ["parket", T("ex_f_parket")], ["balance", T("ex_f_balance")], ["gold", T("ex_f_gold")]],
      "flt", renderExplorer);
    loadArticles(`explorer/${state.outlet}_${state.period}_${state.month}.json`, state.flt, false);
  } else if (state.mode === "gold") {
    mkSel("ex_filter", [["all", T("ex_f_all")], ["g_parket", T("ex_f_gparket")], ["g_non", T("ex_f_gnon")], ["g_mil", T("ex_f_gmil")]],
      "flt", renderExplorer);
    loadArticles("explorer/gold.json", state.flt, true);
  } else {
    renderSummaryTable();
  }
}

function renderSummaryTable() {
  const host = $("#explorer-out"); host.innerHTML = "";
  const tbl = el("table");
  const head = el("tr"); [T("ex_outlet"), T("ex_period"), "month", T("ex_n"), T("ex_parket"), T("ex_balance"), T("ex_goldn")].forEach(t => head.appendChild(el("th", null, t)));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  (EXPLORER.shards || []).forEach(s => {
    const tr = el("tr");
    [s.outlet, s.period, s.month, s.n, s.n_parket, s.n_balance, s.n_gold ?? 0].forEach((v, i) =>
      tr.appendChild(el("td", null, i >= 3 ? Number(v).toLocaleString() : v)));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); host.appendChild(tbl);
}

async function loadArticles(path, flt, isGold) {
  const host = $("#explorer-out"); host.innerHTML = "";
  host.appendChild(el("p", "fine", "…"));
  let rows;
  try { rows = await (await fetch(path)).json(); }
  catch (e) { host.innerHTML = ""; host.appendChild(el("p", "fine", "n/a")); return; }
  host.innerHTML = "";
  const match = (r) => {
    if (flt === "parket") return r.parket;
    if (flt === "balance") return r.balance_risk;
    if (flt === "gold") return r.gold_label != null;
    if (flt === "g_parket") return r.gold_label === "parket";
    if (flt === "g_non") return r.gold_label === "non_parket" && !r.gold_military;
    if (flt === "g_mil") return !!r.gold_military;
    return true;
  };
  const sel = rows.filter(match);
  host.appendChild(el("p", "coverage", `${T("ex_shown")}: ${Math.min(sel.length, 500).toLocaleString()} / ${sel.length.toLocaleString()}`));
  const tbl = el("table");
  const head = el("tr");
  const cols = isGold
    ? [T("ex_outlet"), T("ex_period"), T("ex_date"), T("ex_title"), T("ex_algostatus"), T("ex_goldstatus")]
    : [T("ex_date"), T("ex_title"), "src", T("ex_algostatus"), T("ex_goldstatus")];
  cols.forEach(t => head.appendChild(el("th", null, t)));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  const algoStatus = (r) => r.parket ? T("st_parket") : (r.balance_risk ? T("st_balance") : "—");
  const goldStatus = (r) => r.gold_label == null ? "" :
    (r.gold_military ? T("st_gmil") : (r.gold_label === "parket" ? T("st_gparket") : T("st_gnon")));
  sel.slice(0, 500).forEach(r => {
    const tr = el("tr");
    if (isGold) { tr.appendChild(el("td", null, r.outlet)); tr.appendChild(el("td", null, r.period)); }
    tr.appendChild(el("td", null, r.date_published));
    const tdT = el("td"); const a = el("a", null, r.title || r.url);
    a.href = r.url; a.target = "_blank"; a.rel = "noopener"; tdT.style.textAlign = "left"; tdT.appendChild(a); tr.appendChild(tdT);
    if (!isGold) tr.appendChild(el("td", null, String(r.sc)));
    tr.appendChild(el("td", null, algoStatus(r)));
    tr.appendChild(el("td", null, goldStatus(r)));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); host.appendChild(tbl);
}

boot();
