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

function applyLang() {
  document.documentElement.lang = LANG;
  $("#lang").textContent = LANG === "uk" ? "EN" : "UA";
  document.querySelectorAll("[data-i18n]").forEach(n => { n.textContent = T(n.dataset.i18n); });
  buildNav(); renderVerdict(); renderRates(); renderContrasts();
  renderSensitivity(); renderPeriods(); renderGold(); renderVerification();
  renderLimits(); renderExplorer();
}

function buildNav() {
  const nav = $("#nav"); nav.innerHTML = "";
  [["#tldr", "nav_tldr"], ["#method", "nav_method"], ["#sensitivity", "nav_sens"],
   ["#validation", "nav_valid"], ["#verification", "nav_verif"], ["#limits", "nav_limits"],
   ["#explorer", "nav_explorer"]].forEach(([href, k]) => {
    const a = el("a", null, T(k)); a.href = href; nav.appendChild(a);
  });
}

function renderVerdict() {
  const box = $("#verdict"); box.innerHTML = "";
  const v = FIG.verdict || {};
  const coverageThin = (FIG.rates?.parket?.P1?.n || 0) < 50;
  let msg, cls;
  if (coverageThin) { msg = T("verdict_pending"); cls = ""; }
  else if (v.implied_pattern_supported) { msg = T("verdict_supported"); cls = "yes"; }
  else { msg = T("verdict_not"); cls = "no"; }
  const span = el("span", "flag " + cls, msg);
  box.appendChild(span);
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
  const host = $("#explorer-out"); host.innerHTML = "";
  if (!EXPLORER) { host.appendChild(el("p", "fine", "n/a")); return; }
  const tbl = el("table");
  const head = el("tr"); [T("ex_outlet"), T("ex_period"), "month", T("ex_n"), T("ex_parket"), T("ex_balance")].forEach(t => head.appendChild(el("th", null, t)));
  const thead = el("thead"); thead.appendChild(head); tbl.appendChild(thead);
  const tb = el("tbody");
  (EXPLORER.shards || []).slice(0, 400).forEach(s => {
    const tr = el("tr");
    [s.outlet, s.period, s.month, s.n, s.n_parket, s.n_balance].forEach((v, i) =>
      tr.appendChild(el("td", null, i >= 3 ? Number(v).toLocaleString() : v)));
    tb.appendChild(tr);
  });
  tbl.appendChild(tb); host.appendChild(tbl);
}

boot();
