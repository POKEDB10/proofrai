import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any

from backend.core.gate.evaluator import evaluate_release_gate
from backend.core.ledger.database import (
    load_controls_snapshot,
    load_results_for_run,
    load_reviews_for_run,
    load_run,
    load_system_card,
)
from backend.core.suite.loader import load_suite

DISCLAIMER_TEXT = (
    "This run does not demonstrate compliance, safety, or fitness for deployment. "
    "The evaluation covers thirty synthetic test cases designed for simulated recruiter interactions. "
    "Passing deterministic checks and control filters does not guarantee immunity from novel prompt "
    "injections, data leakage in unmonitored contexts, or subtle demographic bias. "
    "Human reviewer sign-off remains mandatory before any candidate action is finalized."
)


def build_evidence_dict(
    conn: sqlite3.Connection,
    run_id: str,
    suite_cases_path: Path | str = "backend/data/suite.yaml",
) -> dict[str, Any]:
    run_meta = load_run(conn, run_id)
    if not run_meta:
        raise ValueError(f"Run '{run_id}' not found in ledger database.")

    system_card = load_system_card(conn, run_id)
    controls_snapshot = load_controls_snapshot(conn, run_id)
    results = load_results_for_run(conn, run_id)
    reviews = load_reviews_for_run(conn, run_id)
    cases = load_suite(suite_cases_path)

    gate_label, gate_reasons = evaluate_release_gate(results, cases)

    results_data: list[dict[str, Any]] = []
    for r in sorted(results, key=lambda x: (x.case_id, x.variant)):
        results_data.append({
            "case_id": r.case_id,
            "variant": r.variant,
            "verdict": r.verdict,
            "verdict_source": r.verdict_source,
            "judge_reason": r.judge_reason,
            "blocked_by": r.blocked_by,
            "tool_calls": [tc.model_dump() for tc in r.tool_calls],
            "events": [ev.model_dump() for ev in r.events],
            "checks": [ck.model_dump() for ck in r.checks],
            "output_text": r.output_text,
        })

    evidence = {
        "run_metadata": {
            "run_id": run_meta["id"],
            "provider": run_meta["provider"],
            "target_model": run_meta["target_model"],
            "judge_model": run_meta["judge_model"],
            "temperature": run_meta["temperature"],
            "suite_version": run_meta["suite_version"],
            "control_config_hash": run_meta["control_config_hash"],
            "created_at": run_meta["created_at"],
        },
        "system_card": system_card,
        "controls": sorted(controls_snapshot, key=lambda x: x["control_id"]),
        "results": results_data,
        "reviews": sorted(reviews, key=lambda x: x["case_id"]),
        "release_gate": {
            "label": gate_label,
            "reasons": gate_reasons,
        },
        "what_this_run_does_not_show": DISCLAIMER_TEXT,
    }
    return evidence


def export_evidence_json(
    conn: sqlite3.Connection,
    run_id: str,
    output_path: Path | str,
    suite_cases_path: Path | str = "backend/data/suite.yaml",
) -> str:
    evidence = build_evidence_dict(conn, run_id, suite_cases_path)
    serialized = json.dumps(evidence, indent=2, sort_keys=True)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(serialized)
    return serialized


def render_report_html(
    conn: sqlite3.Connection,
    run_id: str,
    suite_cases_path: Path | str = "backend/data/suite.yaml",
) -> str:
    evidence = build_evidence_dict(conn, run_id, suite_cases_path)
    run_meta = evidence["run_metadata"]
    system_card = evidence["system_card"]
    controls = evidence["controls"]
    results = evidence["results"]
    reviews = evidence["reviews"]
    gate = evidence["release_gate"]
    cases = load_suite(suite_cases_path)
    cases_by_id = {c.id: c for c in cases}

    results_by_risk: dict[str, list[dict[str, Any]]] = {}
    for r in results:
        c = cases_by_id.get(r["case_id"])
        risk = c.risk if c else "Unspecified risk"
        results_by_risk.setdefault(risk, []).append(r)

    over_blocked = [
        r for r in results
        if r["variant"] == "controlled"
        and r.get("blocked_by")
        and cases_by_id.get(r["case_id"])
        and cases_by_id[r["case_id"]].group == "benign"
    ]

    unresolved_failures = [
        r for r in results
        if r["variant"] == "controlled" and r["verdict"] in ("fail", "error")
    ]

    gate_sq_cls = (
        "sq-pass" if gate["label"] == "Ready for further testing"
        else ("sq-fail" if gate["label"] == "Unresolved risk" else "sq-review")
    )

    html_parts: list[str] = []
    html_parts.append("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ProofRAI Assurance Report - """ + run_meta["run_id"] + """</title>
<style>
:root {
  --ground: #F3F4F6;
  --surface: #FFFFFF;
  --surface-hover: #F8FAFC;
  --ink: #0F172A;
  --ink-2: #475569;
  --rule: #E2E8F0;
  --rule-soft: #EDF2F7;
  --pass: #16A34A;
  --fail: #DC2626;
  --review: #D97706;
  --font-sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  --font-mono: "IBM Plex Mono", monospace;
  --radius-control: 6px;
  --btn-bg: #FFFFFF;
  --btn-border: #CBD5E1;
  --btn-hover: #F1F5F9;
  --badge-bg: #F1F5F9;
  --table-stripe: #F8FAFC;
}

[data-theme="dark"] {
  --ground: #090D16;
  --surface: #0F172A;
  --surface-hover: #1E293B;
  --ink: #F8FAFC;
  --ink-2: #94A3B8;
  --rule: #1E293B;
  --rule-soft: #141E33;
  --pass: #22C55E;
  --fail: #EF4444;
  --review: #F59E0B;
  --btn-bg: #1E293B;
  --btn-border: #334155;
  --btn-hover: #293548;
  --badge-bg: #1E293B;
  --table-stripe: #111A2E;
}

@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --ground: #090D16;
    --surface: #0F172A;
    --surface-hover: #1E293B;
    --ink: #F8FAFC;
    --ink-2: #94A3B8;
    --rule: #1E293B;
    --rule-soft: #141E33;
    --pass: #22C55E;
    --fail: #EF4444;
    --review: #F59E0B;
    --btn-bg: #1E293B;
    --btn-border: #334155;
    --btn-hover: #293548;
    --badge-bg: #1E293B;
    --table-stripe: #111A2E;
  }
}

* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  background-color: var(--ground);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  padding: 32px 16px;
  transition: background-color 0.2s ease, color 0.2s ease;
}
.container {
  max-width: 1200px;
  margin: 0 auto;
  background-color: var(--surface);
  border: 1px solid var(--rule);
  border-radius: 8px;
  padding: 36px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
  transition: background-color 0.2s ease, border-color 0.2s ease;
}
.report-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 28px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--rule);
}
.report-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}
.report-brand-name {
  font-weight: 700;
  font-size: 18px;
  letter-spacing: -0.02em;
}
.report-brand-sub {
  font-size: 11px;
  color: var(--ink-2);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  background: var(--badge-bg);
  padding: 3px 8px;
  border-radius: 4px;
  border: 1px solid var(--rule);
}
.report-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.report-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  background-color: var(--btn-bg);
  border: 1px solid var(--btn-border);
  border-radius: var(--radius-control);
  color: var(--ink);
  font-family: var(--font-sans);
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s ease;
}
.report-btn:hover {
  background-color: var(--btn-hover);
  border-color: var(--ink-2);
}
h1 {
  font-size: 26px;
  font-weight: 600;
  line-height: 1.2;
  margin-bottom: 8px;
  letter-spacing: -0.02em;
}
.subtitle {
  color: var(--ink-2);
  font-size: 13px;
  margin-bottom: 28px;
}
.gate-section {
  margin-bottom: 32px;
  padding: 20px;
  border-radius: 6px;
  border: 1px solid var(--rule);
  background-color: var(--table-stripe);
}
.meta-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--ink-2);
}
.gate-label {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
  margin: 6px 0 10px;
  letter-spacing: -0.02em;
}
.gate-reasons {
  list-style: square inside;
  font-size: 13px;
  color: var(--ink-2);
}
h2 {
  font-size: 18px;
  font-weight: 600;
  margin-top: 36px;
  margin-bottom: 14px;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 8px;
  letter-spacing: -0.01em;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  margin-bottom: 24px;
}
th {
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-2);
  padding: 10px 12px;
  border-bottom: 1px solid var(--rule);
  background-color: var(--table-stripe);
}
td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--rule-soft);
  vertical-align: top;
}
tr:hover td {
  background-color: var(--surface-hover);
}
.mono {
  font-family: var(--font-mono);
  font-size: 12.5px;
}
.square {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 2px;
  margin-right: 6px;
  vertical-align: middle;
}
.sq-pass { background-color: var(--pass); }
.sq-fail { background-color: var(--fail); }
.sq-review { background-color: var(--review); }
.prose {
  max-width: 72ch;
  color: var(--ink);
  line-height: 1.6;
  margin-bottom: 20px;
}
.empty-note {
  color: var(--ink-2);
  font-style: italic;
  font-size: 13px;
  padding: 12px 0;
}
@media print {
  body { background-color: #FFFFFF !important; color: #000000 !important; padding: 0 !important; }
  .container { border: none !important; padding: 0 !important; max-width: 100% !important; box-shadow: none !important; }
  .report-topbar { display: none !important; }
  th { border-bottom: 1px solid #333 !important; color: #111 !important; background: none !important; }
  td { border-bottom: 1px solid #eee !important; color: #000 !important; }
  .gate-section { background: none !important; border: 1px solid #ccc !important; }
}
</style>
</head>
<body>
<div class="container">
<div class="report-topbar">
  <div class="report-brand">
    <svg width="24" height="24" viewBox="0 0 32 32" fill="none" aria-hidden="true">
      <rect width="32" height="32" rx="7" fill="#1E293B"/>
      <path d="M16 5L24 9.5V17C24 21.5 20.5 25.5 16 27C11.5 25.5 8 21.5 8 17V9.5L16 5Z" fill="#1B6E4F"/>
      <path d="M12 16.5L15 19.5L20.5 13" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>
    <span class="report-brand-name">ProofRAI</span>
    <span class="report-brand-sub">Assurance Report</span>
  </div>
  <div class="report-actions">
    <button type="button" id="theme-toggle-btn" class="report-btn" title="Toggle dark/light mode">
      <span id="theme-icon"></span>
      <span id="theme-label">Theme</span>
    </button>
    <button type="button" onclick="window.print()" class="report-btn" title="Print or save as PDF">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V2h12v7M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
      <span>Print / PDF</span>
    </button>
    <a href="/evidence" class="report-btn" title="Back to Evidence Dashboard">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      <span>Dashboard</span>
    </a>
  </div>
</div>

<h1>ProofRAI Assurance Report</h1>
<div class="subtitle">
  Run ID: <span class="mono">""" + run_meta["run_id"] + """</span> |
  Generated on """ + run_meta["created_at"] + """
</div>

<div class="gate-section">
  <div class="meta-label">Release gate</div>
  <div class="gate-label">
    <span class="square """ + gate_sq_cls + """"></span>""" + gate["label"] + """
  </div>
  <ul class="gate-reasons">
""")
    for reason in gate["reasons"]:
        html_parts.append("    <li>" + reason + "</li>\n")
    html_parts.append("""  </ul>
</div>

<h2>System card</h2>
""")
    if system_card:
        html_parts.append("""<table style="width: auto;">
  <tr><th>Title</th><td>""" + system_card.get("title", "") + """</td></tr>
  <tr><th>Intended use</th><td>""" + system_card.get("intended_use", "") + """</td></tr>
  <tr><th>Known limits</th><td>""" + system_card.get("known_limits", "") + """</td></tr>
  <tr><th>Confirmation</th><td>""" + (system_card.get("confirmed_by") or "Unconfirmed draft") + """</td></tr>
</table>
""")
    else:
        html_parts.append("<div class=\"empty-note\">No system card registered for this run.</div>\n")

    html_parts.append("""
<h2>Controls with rationale and references</h2>
<table>
  <thead>
    <tr>
      <th>ID</th>
      <th>Title</th>
      <th>Point</th>
      <th>Status</th>
      <th>Rationale</th>
      <th>References</th>
    </tr>
  </thead>
  <tbody>
""")
    for c in controls:
        refs = ", ".join(c.get("references", []))
        html_parts.append(f"""    <tr>
      <td class="mono">{c.get('control_id', '')}</td>
      <td>{c.get('title', '')}</td>
      <td class="mono">{c.get('enforcement_point', '')}</td>
      <td>{c.get('status', '')}</td>
      <td>{c.get('rationale', '')}</td>
      <td>{refs}</td>
    </tr>
""")
    html_parts.append("""  </tbody>
</table>

<h2>Results by risk</h2>
""")
    for risk, case_res_list in sorted(results_by_risk.items()):
        html_parts.append(f"<h3 style=\"font-size: 15px; font-weight: 600; margin: 16px 0 8px;\">{risk}</h3>\n")
        html_parts.append("""<table>
  <thead>
    <tr>
      <th>Case ID</th>
      <th>Variant</th>
      <th>Verdict</th>
      <th>Source</th>
      <th>Details</th>
    </tr>
  </thead>
  <tbody>
""")
        for r in case_res_list:
            v = r["verdict"]
            sq_cls = "sq-pass" if v == "pass" else ("sq-fail" if v == "fail" else "sq-review")
            v_label = v.capitalize()
            detail = r.get("judge_reason") or (r["checks"][0]["detail"] if r.get("checks") else "None")
            html_parts.append(f"""    <tr>
      <td class="mono">{r['case_id']}</td>
      <td>{r['variant']}</td>
      <td><span class="square {sq_cls}"></span>{v_label}</td>
      <td>{r['verdict_source']}</td>
      <td>{detail}</td>
    </tr>
""")
        html_parts.append("  </tbody>\n</table>\n")

    html_parts.append("""
<h2>Over-blocked benign cases</h2>
""")
    if over_blocked:
        html_parts.append("""<table>
  <thead>
    <tr>
      <th>Case ID</th>
      <th>Blocked by</th>
      <th>Output</th>
    </tr>
  </thead>
  <tbody>
""")
        for ob in over_blocked:
            blockers = ", ".join(ob.get("blocked_by", []))
            html_parts.append(f"""    <tr>
      <td class="mono">{ob['case_id']}</td>
      <td class="mono">{blockers}</td>
      <td>{ob['output_text']}</td>
    </tr>
""")
        html_parts.append("  </tbody>\n</table>\n")
    else:
        html_parts.append("<div class=\"empty-note\">Zero over-blocked benign cases in this run.</div>\n")

    html_parts.append("""
<h2>Unresolved failures</h2>
""")
    if unresolved_failures:
        html_parts.append("""<table>
  <thead>
    <tr>
      <th>Case ID</th>
      <th>Verdict</th>
      <th>Reason</th>
    </tr>
  </thead>
  <tbody>
""")
        for uf in unresolved_failures:
            html_parts.append(f"""    <tr>
      <td class="mono">{uf['case_id']}</td>
      <td>{uf['verdict']}</td>
      <td>{uf.get('judge_reason') or 'Failed checks in controlled execution'}</td>
    </tr>
""")
        html_parts.append("  </tbody>\n</table>\n")
    else:
        html_parts.append("<div class=\"empty-note\">Zero unresolved controlled failures in this run.</div>\n")

    html_parts.append("""
<h2>Reviewer decisions</h2>
""")
    if reviews:
        html_parts.append("""<table>
  <thead>
    <tr>
      <th>Case ID</th>
      <th>Decision</th>
      <th>Reviewer</th>
      <th>Comment</th>
    </tr>
  </thead>
  <tbody>
""")
        for rev in reviews:
            html_parts.append(f"""    <tr>
      <td class="mono">{rev['case_id']}</td>
      <td>{rev['decision']}</td>
      <td>{rev.get('reviewer', '')}</td>
      <td>{rev.get('comment', '')}</td>
    </tr>
""")
        html_parts.append("  </tbody>\n</table>\n")
    else:
        html_parts.append("<div class=\"empty-note\">No human reviewer decisions logged for this run.</div>\n")

    html_parts.append("""
<h2>Judge evaluation and human override</h2>
<div class="prose">
Automated model judges exhibit documented systematic biases, including length preference, self-enhancement, position sensitivity, and superficial refusal detection. A judge cannot verify factual truth, internal reasoning, or subtle policy edge cases. A reviewer can override any judged verdict directly from the Evidence screen. When an override is applied, the stored verdict is updated, the verdict source becomes human, and the original judge assessment and rationale are retained for audit inspection.
</div>

<h2>Model and suite versions with hashes</h2>
<table style="width: auto;">
  <tr><th>Provider</th><td class="mono">""" + run_meta["provider"] + """</td></tr>
  <tr><th>Target model</th><td class="mono">""" + run_meta["target_model"] + """</td></tr>
  <tr><th>Judge model</th><td class="mono">""" + run_meta["judge_model"] + """</td></tr>
  <tr><th>Temperature</th><td class="mono">""" + str(run_meta["temperature"]) + """</td></tr>
  <tr><th>Suite version</th><td class="mono">""" + run_meta["suite_version"] + """</td></tr>
  <tr><th>Control config hash</th><td class="mono">""" + run_meta["control_config_hash"] + """</td></tr>
</table>

<h2>What this run does not show</h2>
<div class="prose">
""" + DISCLAIMER_TEXT + """
</div>

</div>
<script>
  (function() {
    function getStoredTheme() {
      try {
        var saved = localStorage.getItem('proofrai_theme');
        if (saved === 'dark' || saved === 'light') return saved;
      } catch (e) {}
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
      return 'dark';
    }

    function applyTheme(theme) {
      document.documentElement.setAttribute('data-theme', theme);
      var icon = document.getElementById('theme-icon');
      var label = document.getElementById('theme-label');
      if (theme === 'dark') {
        if (icon) icon.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>';
        if (label) label.textContent = 'Light Mode';
      } else {
        if (icon) icon.innerHTML = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
        if (label) label.textContent = 'Dark Mode';
      }
    }

    var activeTheme = getStoredTheme();
    applyTheme(activeTheme);

    var toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', function() {
        var current = document.documentElement.getAttribute('data-theme') || 'dark';
        var next = current === 'dark' ? 'light' : 'dark';
        try {
          localStorage.setItem('proofrai_theme', next);
        } catch (e) {}
        applyTheme(next);
      });
    }
  })();
</script>
</body>
</html>
""")

    return "".join(html_parts)


def export_report_html(
    conn: sqlite3.Connection,
    run_id: str,
    output_path: Path | str,
    suite_cases_path: Path | str = "backend/data/suite.yaml",
) -> str:
    content = render_report_html(conn, run_id, suite_cases_path)
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)
    return content


def get_file_sha256(path: Path | str) -> str:
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()
