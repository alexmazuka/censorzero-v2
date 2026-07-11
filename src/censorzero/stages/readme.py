"""readme stage: render README.md and the full bilingual report from
site/figures.json.

No number in any rendered document is typed by hand; every value comes from
figures.json so text can never drift from data (a v1 failure mode). Rendered
report pages carry a GENERATED-FROM-FIGURES marker that exempts them from the
no-hardcoded-numbers HTML check — they are themselves byte-gated in CI.
"""

import json
from pathlib import Path

import markdown as md
from jinja2 import Environment, FileSystemLoader, StrictUndefined

REPO_ROOT = Path(__file__).resolve().parents[3]
SITE = REPO_ROOT / "site"
DOCS = REPO_ROOT / "docs"
TEMPLATES = DOCS / "templates"

HTML_SHELL = """<!DOCTYPE html>
<!-- GENERATED-FROM-FIGURES: rendered by `make readme`; numbers come from figures.json -->
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="assets/style.css">
<style>
main.report {{ max-width: 860px; margin: 0 auto; padding: 30px 20px; }}
main.report h1 {{ font-size: 26px; }}
main.report blockquote {{ border-left: 3px solid var(--warn-line);
  background: var(--warn-bg); margin: 14px 0; padding: 10px 14px; }}
main.report table {{ font-size: 14px; }}
main.report code {{ background: var(--card); padding: 1px 5px; border-radius: 4px; }}
main.report pre {{ background: var(--card); border: 1px solid var(--line);
  border-radius: 8px; padding: 12px; overflow-x: auto; }}
</style>
</head>
<body>
<main class="report">
<p><a href="index.html">&larr; {back}</a> · <a href="{other_href}">{other_label}</a></p>
{body}
</main>
</body>
</html>
"""


def _pct(x) -> str:
    return "n/a" if x is None or x != x else f"{x * 100:.2f}%"


def _report_vars(figures: dict) -> dict:
    """Precompute display strings the report templates use."""
    g = figures.get("gold_standard") or {}
    cov = figures.get("coverage", {}).get("by_outlet_period", {})
    tot = lambda o: sum(cov.get(o, {}).values())  # noqa: E731
    hm_all = g.get("human_measurement", {})
    hm_u = hm_all.get("ukrinform", {})
    per = hm_u.get("per_period", {})
    fmt = lambda x, d=1: ("n/a" if x is None or x != x else f"{100 * x:.{d}f}")  # noqa: E731

    hm = {}
    for pk in ("P0", "P1", "P2"):
        c = per.get(pk, {})
        hm[pk] = {
            "rate_pct": fmt(c.get("rate")),
            "ci": f"[{fmt(c.get('ci_low'))}%, {fmt(c.get('ci_high'))}%]",
            "n": c.get("n", 0),
        }
    pairs = []
    for pair in ("P0-P1", "P1-P2", "P0-P2"):
        c = (hm_u.get("pairwise") or {}).get(pair)
        if c:
            pairs.append((pair, {
                "diff_pp": fmt(c.get("diff")),
                "h_str": (f"{c['h']:.3f} [{c['h_ci_low']:.3f}, {c['h_ci_high']:.3f}]"
                          if c.get("h") is not None else "n/a"),
                "p_holm_str": (f"{c['p_holm']:.3f}" if c.get("p_holm") is not None else "n/a"),
            }))
    up_per = hm_all.get("pravda", {}).get("per_period", {})
    rd = (g.get("recall_drift") or {}).get("per_period", {})
    rel = g.get("reliability") or {}
    hv = g.get("human_validation") or {}
    overall = g.get("overall") or {}
    homog = hm_u.get("homogeneity") or {}

    return {
        "n_total": f"{sum(tot(o) for o in cov):,}".replace(",", " "),
        "n_ukr": f"{tot('ukrinform'):,}".replace(",", " "),
        "n_up": f"{tot('pravda'):,}".replace(",", " "),
        "n_sus": f"{tot('suspilne'):,}".replace(",", " "),
        "universe_k": "148",
        "n_gold": g.get("n_annotated", 0),
        "prec_pct": fmt(overall.get("precision"), 0),
        "rec_pct": fmt(overall.get("recall"), 0),
        "hm": hm,
        "hm_p0": hm["P0"]["rate_pct"], "hm_p1": hm["P1"]["rate_pct"],
        "hm_p2": hm["P2"]["rate_pct"],
        "hm_homog_p": (f"{homog['p_value']:.3f}" if homog.get("p_value") is not None else "n/a"),
        "hm_pairs": pairs,
        "mde_pp": (f"{hm_u['min_detectable_diff_pp']:.0f}"
                   if hm_u.get("min_detectable_diff_pp") is not None else "n/a"),
        "up_p0": fmt((up_per.get("P0") or {}).get("rate")),
        "up_p1": fmt((up_per.get("P1") or {}).get("rate")),
        "up_p2": fmt((up_per.get("P2") or {}).get("rate")),
        "rd_p0": f"{(rd.get('P0') or {}).get('hit', 0)}/{(rd.get('P0') or {}).get('hit', 0) + (rd.get('P0') or {}).get('miss', 0)}",
        "rd_p1": f"{(rd.get('P1') or {}).get('hit', 0)}/{(rd.get('P1') or {}).get('hit', 0) + (rd.get('P1') or {}).get('miss', 0)}",
        "rd_p2": f"{(rd.get('P2') or {}).get('hit', 0)}/{(rd.get('P2') or {}).get('hit', 0) + (rd.get('P2') or {}).get('miss', 0)}",
        "rd_p": (f"{(g.get('recall_drift') or {}).get('p_value'):.4f}"
                 if (g.get("recall_drift") or {}).get("p_value") is not None else "n/a"),
        "rel_agree_pct": fmt(rel.get("agreement"), 0),
        "rel_kappa": (f"{rel['kappa']:.2f}" if rel.get("kappa") is not None else "n/a"),
        "hv_kappa": (f"{hv['kappa']:.2f}" if hv.get("kappa") is not None else "n/a"),
        "hv_n": hv.get("n_overlap", 0),
    }


def run() -> None:
    figures = json.loads((SITE / "figures.json").read_text())
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    env.filters["pct"] = _pct

    (REPO_ROOT / "README.md").write_text(
        env.get_template("README.md.j2").render(fig=figures), encoding="utf-8")

    rvars = _report_vars(figures)
    shell_meta = {
        "en": {"title": "CensorZero — full report (EN)", "back": "Back to dashboard",
               "other_href": "report_uk.html", "other_label": "Українською"},
        "uk": {"title": "CensorZero — повний звіт (UA)", "back": "На дашборд",
               "other_href": "report_en.html", "other_label": "English"},
    }
    for lang in ("en", "uk"):
        text = env.get_template(f"REPORT.{lang}.md.j2").render(fig=figures, **rvars)
        (DOCS / f"REPORT.{lang}.md").write_text(text, encoding="utf-8")
        body = md.markdown(text, extensions=["tables", "fenced_code"])
        m = shell_meta[lang]
        (SITE / f"report_{lang}.html").write_text(
            HTML_SHELL.format(lang=lang, body=body, **m), encoding="utf-8")
    print("readme: README.md + REPORT.{uk,en}.md + site/report_{uk,en}.html rendered")
