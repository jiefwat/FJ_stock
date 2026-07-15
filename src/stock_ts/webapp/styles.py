# ruff: noqa: E501
from __future__ import annotations

CSS = r"""
:root {
  color-scheme: light;
  --bg: #edf2f5;
  --bg-strong: #d9e3eb;
  --panel: #f8fbfd;
  --panel-strong: #e5edf2;
  --panel-glass: rgba(248, 251, 253, .82);
  --ink: #13273a;
  --ink-soft: #27435b;
  --muted: #5f7486;
  --line: #cad7e1;
  --line-strong: #aebecd;
  --brand: #0d3b66;
  --brand-2: #19538d;
  --accent: #b4853a;
  --accent-soft: #f0e4ca;
  --amber: #a86811;
  --red: #b4483d;
  --green-soft: #dfeee9;
  --shadow: 0 28px 70px rgba(19, 39, 58, .10);
  --mono: "SFMono-Regular", "JetBrains Mono", "IBM Plex Mono", Menlo, monospace;
  --display: "Aptos Display", "SF Pro Display", "PingFang SC", "Helvetica Neue", sans-serif;
  --body: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
* { box-sizing: border-box; }
html { scroll-behavior: auto; }
body {
  margin: 0;
  min-height: 100vh;
  color: var(--ink);
  font-family: var(--body);
  background:
    radial-gradient(circle at 12% 0%, rgba(180, 133, 58, .14), transparent 26%),
    radial-gradient(circle at 100% 0%, rgba(13, 59, 102, .10), transparent 24%),
    linear-gradient(180deg, #f6f9fb, var(--bg));
}
a { color: inherit; text-decoration: none; }
button,
input,
select,
textarea { font: inherit; }
button:focus-visible,
input:focus-visible,
select:focus-visible,
textarea:focus-visible,
.nav-item:focus-visible,
.workflow-card:focus-visible,
.ghost-button:focus-visible,
.primary-button:focus-visible,
.danger-button:focus-visible,
.mini-button:focus-visible,
.research-tape-data-link:focus-visible,
.research-overflow summary:focus-visible,
.stock-evidence summary:focus-visible,
.data-source-ledger summary:focus-visible,
.market-intraday-ledger summary:focus-visible {
  outline: 3px solid rgba(180, 133, 58, .28);
  outline-offset: 2px;
}
.app-shell { display: grid; grid-template-columns: 248px minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 24px 14px 16px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,0)),
    linear-gradient(180deg, #142b41, #102033);
  color: #e8f2fa;
  border-right: 1px solid rgba(255,255,255,.08);
}
.brand-mark { display:flex; gap:12px; align-items:center; margin-bottom: 26px; }
.logo {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display:grid;
  place-items:center;
  background: linear-gradient(135deg, #f3e2bf, #b4853a);
  color:#142b41;
  font-family: var(--display);
  font-weight: 900;
  letter-spacing: .03em;
}
.brand-title { font-size: 18px; font-weight: 800; letter-spacing: .02em; font-family: var(--display); }
.brand-subtitle { color: rgba(232,242,250,.64); font-size: 12px; margin-top: 3px; }
.nav-group { display:grid; gap:6px; margin: 18px 0 20px; }
.nav-item {
  width:100%;
  border:1px solid transparent;
  text-align:left;
  cursor:pointer;
  padding: 10px 12px;
  border-radius: 14px;
  color: rgba(232,242,250,.84);
  background:transparent;
  display:flex;
  justify-content:space-between;
  align-items:center;
}
.nav-item:hover,
.nav-item.active {
  background: rgba(248,251,253,.10);
  color: #fff;
  border-color: rgba(180, 133, 58, .28);
}
.nav-item span {
  color: rgba(232,242,250,.56);
  font-size: 11px;
  letter-spacing: .08em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.sidebar-note {
  margin-top:auto;
  padding:14px;
  border:1px solid rgba(255,255,255,.08);
  background:rgba(255,255,255,.05);
  border-radius:16px;
  color:rgba(232,242,250,.74);
  font-size:13px;
  line-height:1.6;
}
.sidebar-account-card {
  display:grid;
  gap:7px;
  margin:0 0 12px;
  padding:12px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:16px;
  background:rgba(255,255,255,.07);
}
.sidebar-account-card span,
.sidebar-account-card small { color:rgba(232,242,250,.66); font-size:12px; }
.sidebar-account-card strong { color:#fff; font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.sidebar-account-actions { display:flex; flex-wrap:wrap; gap:7px; align-items:center; }
.sidebar-account-actions form { margin:0; }
.sidebar-account-link { display:inline-flex; align-items:center; min-height:30px; padding:6px 9px; font-size:12px; background:rgba(255,255,255,.10); color:#e8f2fa; border-color:rgba(255,255,255,.14); }

.quick-stock-search {
  display:grid;
  grid-template-columns:minmax(0, 1fr);
  gap:8px;
  padding:12px;
  margin: 0 0 14px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:18px;
  background:rgba(255,255,255,.06);
}
.quick-stock-search input {
  width:100%;
  border:1px solid rgba(255,255,255,.12);
  border-radius:12px;
  padding:10px 11px;
  color:#fff;
  background:rgba(7,18,29,.34);
}
.quick-stock-search input::placeholder { color:rgba(232,242,250,.52); }
.quick-stock-search button {
  border:0;
  border-radius:12px;
  padding:10px 12px;
  color:#142b41;
  background:linear-gradient(135deg, #f3e2bf, #b4853a);
  font-weight:900;
  cursor:pointer;
}
.sidebar-context {
  padding: 16px;
  margin-bottom: 14px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.06);
  border-radius: 18px;
}
.sidebar-context-label {
  display: block;
  color: rgba(232,242,250,.56);
  font-size: 11px;
  letter-spacing: .10em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.sidebar-context strong {
  display: block;
  margin-top: 8px;
  font-size: 17px;
  color: #fff;
}
.sidebar-context p {
  margin: 8px 0 0;
  color: rgba(232,242,250,.72);
  font-size: 13px;
  line-height: 1.6;
}
.workspace { padding: 14px 18px 20px; overflow: hidden; }
.topbar {
  display:grid;
  grid-template-columns: minmax(280px, .52fr) minmax(0, 1.48fr);
  gap:10px;
  align-items:stretch;
  margin-bottom: 10px;
}
.topbar-copy,
.desk-status {
  border:1px solid var(--line);
  background: var(--panel-glass);
  border-radius: 18px;
  box-shadow: 0 8px 20px rgba(19, 39, 58, .06);
}
.topbar-copy {
  padding: 13px 16px;
  background: linear-gradient(180deg, rgba(255,255,255,.84), rgba(248,251,253,.94));
}
.topbar-copy.compact { display:grid; align-content:center; gap:5px; }
.topbar-line { display:flex; align-items:center; justify-content:space-between; gap:12px; }
.domain-pill {
  flex:0 0 auto;
  border:1px solid var(--line);
  border-radius:999px;
  padding:6px 9px;
  color:var(--muted);
  background:rgba(255,255,255,.72);
  font-size:11px;
  font-family:var(--mono);
}
.eyebrow {
  color: var(--brand);
  font-weight: 800;
  letter-spacing: .12em;
  font-size: 11px;
  text-transform: uppercase;
  font-family: var(--mono);
}
h1 {
  margin: 0;
  font-size: clamp(21px, 2.2vw, 28px);
  line-height: 1.05;
  letter-spacing:-.04em;
  font-family: var(--display);
}
.lead {
  max-width: 520px;
  color: var(--muted);
  line-height: 1.4;
  font-size: 13px;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.desk-status {
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap:8px;
  padding: 10px;
}
.desk-status-card {
  border:1px solid var(--line);
  border-radius: 13px;
  padding: 10px;
  background: rgba(255,255,255,.74);
}
.desk-status-label {
  display:block;
  color: var(--muted);
  font-size: 11px;
  letter-spacing: .08em;
  text-transform: uppercase;
  font-family: var(--mono);
}
.desk-status-value {
  display:block;
  margin-top: 5px;
  font-size: 15px;
  font-weight: 800;
  color: var(--ink);
}
.desk-status-note {
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.status-pills { display:flex; flex-wrap:wrap; gap:10px; justify-content:flex-end; }
.status-pill {
  border:1px solid var(--line);
  background:rgba(255,255,255,.78);
  border-radius:999px;
  padding:9px 13px;
  color:var(--muted);
  font-size:13px;
}
.module {
  margin: 12px 0;
  border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.90), rgba(248,251,253,.90));
  border-radius:18px;
  padding:14px;
  box-shadow: 0 14px 34px rgba(19, 39, 58, .07);
}
.module-view { display:none; animation: reveal .24s ease both; }
.module-view.active { display:block; }
@keyframes reveal { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.module-header { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom: 10px; }
.module-header-meta { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:10px; }
.module-refresh-tools { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:8px; color:var(--muted); font-size:12px; }
.module-refresh-tools form { margin:0; }
.module-refresh-button { padding:7px 10px; font-size:12px; }
.module-title { margin:0; font-size: 19px; letter-spacing:-.03em; font-family: var(--display); }
.module-desc {
  margin:4px 0 0;
  color:var(--muted);
  line-height:1.42;
  font-size: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.kpi-grid { display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:14px; }
.kpi-card { border:1px solid var(--line); background:linear-gradient(180deg, #ffffff, #f1f6fa); border-radius:20px; padding:14px; min-height: 102px; }
.kpi-label { color:var(--muted); font-size:13px; }
.kpi-value { margin-top:7px; font-size:26px; font-weight:900; letter-spacing:-.04em; font-family: var(--display); }
.kpi-foot {
  margin-top:7px;
  color:var(--muted);
  font-size:12px;
  line-height:1.35;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.grid-2 { display:grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap:16px; }
.grid-3 { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:16px; }
.portfolio-overall-summary .grid-3 { align-items:start; gap:12px; }
.portfolio-overall-summary .kpi-card { min-height:0; padding:12px 13px; align-self:start; }
.portfolio-overall-summary .kpi-label { font-weight:900; color:var(--ink); }
.compact-list { font-size:13px; line-height:1.45; }
.compact-list li + li { margin-top:6px; }
.portfolio-analysis-table {
  table-layout:fixed;
}
.portfolio-analysis-table th:nth-child(1),
.portfolio-analysis-table td:nth-child(1) { width:18%; }
.portfolio-analysis-table th:nth-child(2),
.portfolio-analysis-table td:nth-child(2) { width:66%; }
.portfolio-analysis-table th:nth-child(3),
.portfolio-analysis-table td:nth-child(3) { width:16%; }
.portfolio-analysis-table td {
  padding:10px 9px;
  vertical-align:top;
}
.portfolio-analysis-table .action-cell {
  white-space:normal;
}
.portfolio-analysis-table .action-cell form {
  margin:0 0 6px;
}
.portfolio-analysis-table .portfolio-inline-button,
.portfolio-analysis-table .danger-button {
  width:100%;
  padding:7px 8px;
  font-size:12px;
}
.portfolio-analysis-stack {
  display:grid;
  gap:5px;
  min-width:0;
}
.portfolio-analysis-line {
  display:grid;
  grid-template-columns:68px minmax(0,1fr);
  gap:8px;
  margin:0;
  color:var(--ink-soft);
  font-size:13px;
  line-height:1.42;
}
.portfolio-analysis-line strong { color:var(--ink); }
.portfolio-analysis-line span {
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.panel { border:1px solid var(--line); background:rgba(255,255,255,.80); border-radius:20px; padding:15px; }
.panel h3 { margin:0 0 12px; font-size:16px; font-family: var(--display); }
.score-row { display:grid; grid-template-columns: 92px minmax(0, 1fr) 64px; gap:12px; align-items:center; margin:12px 0; }
.score-label { color:var(--muted); font-size:13px; }
.score-bar { height: 10px; border-radius:999px; background:#dde6ee; overflow:hidden; }
.score-fill { height:100%; border-radius:999px; background:linear-gradient(90deg, var(--brand), var(--accent)); }
.score-value { font-weight:800; text-align:right; font-family: var(--mono); }
.tag-list { display:flex; flex-wrap:wrap; gap:8px; }
.tag { display:inline-flex; align-items:center; gap:6px; border:1px solid #d7c39d; background:#f8f0df; color:#7b5b26; border-radius:999px; padding:7px 10px; font-size:13px; }
.risk-pill { display:inline-block; border-radius:999px; padding:5px 9px; font-size:12px; font-weight:700; }
.risk-pill.low { background:#e3f0ea; color:#245b47; }
.risk-pill.mid { background:#f5ecd9; color:#7b5b26; }
.risk-pill.high { background:#fae4e1; color:#a13e33; }
.note-list { margin:0; padding-left:18px; color:var(--muted); line-height:1.7; }
.sector-strip { display:grid; gap:10px; }
.sector-item { display:grid; grid-template-columns: 90px minmax(0, 1fr) 54px; align-items:center; gap:12px; }
.compare-chart {
  display: grid;
  gap: 10px;
  margin-top: 12px;
}
.compare-row {
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(0, 1.15fr) 78px;
  gap: 12px;
  align-items: center;
  padding: 12px 14px;
  border: 1px solid rgba(13,59,102,.10);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(255,255,255,.96), rgba(241,246,250,.96));
}
.compare-copy strong {
  display: block;
  font-size: 14px;
}
.compare-copy span {
  display: block;
  margin-top: 4px;
  color: var(--muted);
  font-size: 12px;
}
.compare-track {
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: #dde6ee;
}
.compare-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent));
}
.compare-fill.positive {
  background: linear-gradient(90deg, var(--brand), var(--accent));
}
.compare-fill.negative {
  background: linear-gradient(90deg, #9a4338, #d98c56);
}
.compare-value {
  text-align: right;
  font-family: var(--mono);
  font-size: 13px;
  font-weight: 800;
  color: var(--ink-soft);
}
.data-table { width:100%; border-collapse:separate; border-spacing:0 9px; font-size:14px; }
.data-table th { text-align:left; color:var(--muted); font-size:12px; font-weight:800; padding:0 10px 2px; }
.data-table td { background:rgba(255,255,255,.86); border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:12px 10px; vertical-align:top; }
.data-table td:first-child { border-left:1px solid var(--line); border-radius:14px 0 0 14px; }
.data-table td:last-child { border-right:1px solid var(--line); border-radius:0 14px 14px 0; }
.compact-sector-table td { padding:9px 8px; line-height:1.42; }
.compact-sector-table th { padding-left:8px; padding-right:8px; }
.cell-clamp {
  display:-webkit-box;
  -webkit-line-clamp:4;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.cell-clamp.tight { -webkit-line-clamp:3; }
.name-cell strong { display:block; font-size:15px; }
.name-cell span { color:var(--muted); font-size:12px; }
.reason-list { margin:0; padding-left:16px; color:var(--muted); line-height:1.55; }
.report-copy {
  width:100%;
  min-height:360px;
  resize:vertical;
  border:1px solid var(--line);
  border-radius:18px;
  padding:16px;
  background:#12253b;
  color:#edf5fb;
  font-family: var(--mono);
  line-height:1.55;
}
.stock-switch-panel { display:grid; gap:14px; overflow:hidden; }
.stock-switch-panel .editor-toolbar { margin-bottom:0; }
.stock-form {
  display:grid;
  grid-template-columns:minmax(220px,520px) auto;
  gap:10px;
  align-items:center;
  justify-content:start;
  margin:0;
  min-width:0;
}
.stock-form input[type="hidden"] { display:none; }
.stock-form input {
  width:100%;
  min-width:0;
  border:1px solid var(--line);
  border-radius:14px;
  padding:12px 14px;
  font-size:15px;
  background:#fff;
}
.stock-form button {
  min-width:96px;
  white-space:nowrap;
  border:0;
  border-radius:14px;
  padding:12px 18px;
  color:white;
  background:linear-gradient(135deg,var(--brand),var(--brand-2));
  font-weight:800;
  cursor:pointer;
}
.stock-quick-lanes {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
  min-width:0;
}
.stock-quick-lane {
  min-width:0;
  border:1px solid rgba(13,59,102,.10);
  border-radius:14px;
  padding:11px;
  background:rgba(255,255,255,.56);
}
.stock-quick-lane > span {
  display:block;
  margin-bottom:8px;
  color:var(--muted);
  font-size:12px;
  font-weight:900;
  letter-spacing:.02em;
}
.stock-quick-lane em {
  color:var(--muted);
  font-size:13px;
  font-style:normal;
}
.action-list {
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  min-width:0;
}
.stock-switch-panel .mini-button {
  display:inline-flex;
  align-items:center;
  gap:4px;
  max-width:100%;
  min-height:34px;
  white-space:nowrap;
}
.stock-switch-panel .mini-button span {
  color:#0d3b66;
  font-family:var(--mono);
  font-weight:900;
}
@media (max-width: 760px) {
  .stock-form,
  .stock-quick-lanes {
    grid-template-columns:minmax(0,1fr);
  }
  .stock-form button {
    width:100%;
  }
}
.app-toolbar {
  position:sticky;
  top:8px;
  z-index:10;
  display:grid;
  grid-template-columns: minmax(240px,1fr) auto auto;
  gap:10px;
  align-items:end;
  margin:0 0 10px;
  padding:10px;
  border:1px solid var(--line);
  background:rgba(248,251,253,.84);
  backdrop-filter:blur(14px);
  border-radius:16px;
  box-shadow:0 8px 18px rgba(19,39,58,.05);
}
.app-toolbar label { display:grid; gap:5px; color:var(--muted); font-size:12px; font-weight:800; }
.app-toolbar input,
.app-toolbar select {
  width:100%;
  border:1px solid var(--line);
  background:#fff;
  color:var(--ink);
  border-radius:14px;
  padding:10px 12px;
  font-size:14px;
}
.app-toolbar button {
  border:0;
  border-radius:16px;
  padding:13px 18px;
  color:#fff;
  background:linear-gradient(135deg,var(--brand),var(--brand-2));
  font-weight:900;
  cursor:pointer;
  align-self:end;
}
.source-badge {
  align-self:end;
  border:1px solid var(--line);
  border-radius:14px;
  padding:11px 12px;
  color:var(--brand);
  background:#fff;
  font-size:13px;
  font-weight:900;
  white-space:nowrap;
}
.desk-strip {
  display:grid;
  grid-template-columns: minmax(0, 1fr);
  gap:10px;
  margin: 0 0 12px;
}
.desk-strip-card {
  border:1px solid var(--line);
  border-radius:18px;
  background:rgba(255,255,255,.82);
  padding:13px 14px;
  box-shadow:0 10px 24px rgba(19,39,58,.05);
}
.desk-strip-card h3 {
  margin:0 0 12px;
  font-size:16px;
  font-family: var(--display);
}
.desk-strip-meta {
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-bottom:12px;
}
.desk-strip-summary {
  color:var(--muted);
  line-height:1.5;
  font-size:13px;
}
.desk-strip-detail {
  display:grid;
  gap:10px;
}
.desk-strip-detail .metric-list {
  margin-top: 4px;
}
.desk-strip-actions {
  display:grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap:8px;
}
.desk-jump {
  border:1px solid rgba(13,59,102,.14);
  border-radius:14px;
  padding:10px;
  background:linear-gradient(180deg, #fff, #eef4f8);
  text-align:left;
  cursor:pointer;
  color:var(--ink);
}
.desk-jump strong {
  display:block;
  font-size:14px;
}
.desk-jump span {
  display:block;
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.desk-jump:hover { border-color:rgba(13,59,102,.30); }
.view-title { display:flex; align-items:center; justify-content:space-between; gap:12px; margin: 0 0 10px; color:var(--muted); font-size:13px; }
.view-title strong { color:var(--brand); }
.footer-warning { color:var(--amber); font-size:13px; margin-top:14px; line-height:1.6; }
.quality-banner { border:1px solid #ddc7a2; background:#f7f0e4; color:#7b5b26; border-radius:20px; padding:14px 16px; margin-bottom:16px; line-height:1.65; }
.quality-banner.good { border-color:#b8d4c8; background:#ebf5f0; color:#245b47; }
.debate-card { border:1px solid var(--line); border-radius:18px; padding:16px; background:rgba(255,255,255,.76); }
.debate-card h4 { margin:0 0 9px; font-size:16px; }
.scenario-list { display:grid; gap:10px; }
.scenario-item { border:1px solid var(--line); border-radius:16px; padding:12px; background:#fdfefe; line-height:1.55; color:var(--muted); }
.research-lane { display:grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap:14px; }
.lane-card { border:1px solid var(--line); border-radius:20px; padding:16px; background:linear-gradient(180deg,#fff,#f0f6fa); min-height:150px; }
.lane-card strong { display:block; font-size:16px; margin-bottom:8px; }
.matrix-grid { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:14px; }
.matrix-card { border:1px solid var(--line); border-radius:18px; padding:15px; background:rgba(255,255,255,.78); }
.matrix-card h4 { margin:0 0 8px; font-size:15px; }
.metric-list { display:grid; gap:8px; }
.metric-line { display:flex; justify-content:space-between; gap:12px; border-bottom:1px dashed var(--line); padding-bottom:7px; color:var(--muted); }
.command-deck { display:grid; grid-template-columns: 1.2fr .8fr; gap:16px; align-items:stretch; }
.command-card {
  position:relative;
  overflow:hidden;
  border:1px solid rgba(13,59,102,.16);
  background:
    linear-gradient(135deg, rgba(180,133,58,.14), transparent 28%),
    linear-gradient(135deg, #13273a, #17344d);
  border-radius:30px;
  padding:22px;
  min-height:260px;
  color:#edf5fb;
}
.command-card:after {
  content:"";
  position:absolute;
  inset:auto -10% -35% auto;
  width:240px;
  height:240px;
  border-radius:999px;
  background:rgba(255,255,255,.10);
}
.command-card h2 { margin:0 0 8px; font-size:32px; letter-spacing:-.04em; font-family: var(--display); }
.command-signal {
  display:inline-flex;
  align-items:center;
  gap:8px;
  border:1px solid rgba(255,255,255,.18);
  background:rgba(255,255,255,.08);
  border-radius:999px;
  padding:8px 11px;
  font-size:12px;
  color:#dce9f4;
  font-family: var(--mono);
}
.command-summary { max-width:62%; margin:16px 0 22px; line-height:1.7; color:rgba(237,245,251,.80); }
.command-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; position:relative; z-index:1; }
.command-metric { border:1px solid rgba(255,255,255,.14); background:rgba(255,255,255,.10); border-radius:18px; padding:13px; backdrop-filter:blur(12px); }
.command-metric span { display:block; color:rgba(237,245,251,.66); font-size:11px; letter-spacing:.06em; text-transform:uppercase; }
.command-metric strong { display:block; margin-top:6px; font-size:18px; letter-spacing:-.03em; }
.evidence-rail { border:1px solid var(--line); background:linear-gradient(180deg,#ffffff,#eef4f8); border-radius:30px; padding:20px; }
.evidence-rail h3 { margin:0 0 14px; font-size:20px; }
.evidence-step { display:grid; grid-template-columns:28px minmax(0,1fr); gap:10px; padding:10px 0; border-bottom:1px dashed var(--line); }
.evidence-dot { width:28px; height:28px; border-radius:999px; display:grid; place-items:center; background:#16324f; color:#edf5fb; font-weight:900; font-size:12px; font-family: var(--mono); }
.evidence-step strong { display:block; font-size:14px; }
.evidence-step p { margin:4px 0 0; color:var(--muted); line-height:1.55; font-size:13px; }
.action-strip { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; margin-top:16px; }
.action-card { border:1px solid var(--line); border-radius:20px; padding:16px; background:rgba(255,255,255,.78); }
.action-card strong { display:block; font-size:15px; margin-bottom:6px; }
.action-card p { display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.workflow-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:16px; }
.workflow-card { border:1px solid rgba(13,59,102,.14); border-radius:18px; padding:14px; background:linear-gradient(180deg,#fff,#eef4f8); text-align:left; cursor:pointer; color:var(--ink); box-shadow:0 12px 34px rgba(19,39,58,.08); }
.workflow-card strong { display:block; font-size:15px; margin-bottom:6px; }
.workflow-card span { display:block; color:var(--muted); line-height:1.45; font-size:12px; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.workflow-card:hover { transform:translateY(-2px); border-color:rgba(13,59,102,.34); transition:.18s ease; }
.today-list { display:grid; gap:10px; counter-reset: today; }
.today-item { display:grid; grid-template-columns:34px minmax(0,1fr) auto; gap:10px; align-items:center; border:1px solid var(--line); border-radius:16px; padding:11px; background:rgba(255,255,255,.76); }
.today-item:before { counter-increment: today; content:counter(today); width:34px; height:34px; border-radius:12px; display:grid; place-items:center; background:#17344d; color:#edf5fb; font-weight:900; font-family: var(--mono); }
.today-item strong { display:block; }
.today-item span { color:var(--muted); font-size:12px; line-height:1.4; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden; }
.mini-button { border:1px solid rgba(13,59,102,.16); border-radius:999px; padding:8px 11px; background:rgba(255,255,255,.72); color:#16426b; font-weight:800; cursor:pointer; }
.current-module-indicator { display:flex; justify-content:space-between; align-items:center; gap:10px; margin:-4px 0 14px; padding:10px 14px; border:1px solid var(--line); border-radius:18px; background:rgba(255,255,255,.64); color:var(--muted); font-size:13px; }
.current-module-indicator strong { color:var(--brand); }
.inline-form { margin:0; }
.portfolio-form-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.field-stack { display:grid; gap:6px; color:var(--muted); font-size:12px; font-weight:800; }
.field-stack input { width:100%; border:1px solid var(--line); background:#fff; color:var(--ink); border-radius:14px; padding:10px 12px; font-size:14px; }
.field-stack textarea,
.field-stack select {
  width:100%;
  border:1px solid var(--line);
  background:#fff;
  color:var(--ink);
  border-radius:14px;
  padding:10px 12px;
  font-size:14px;
}
.form-section-grid { display:grid; gap:14px; }
.form-section-card {
  border:1px solid var(--line);
  border-radius:20px;
  padding:16px;
  background:linear-gradient(180deg,#fff,#f4f8fb);
}
.form-section-card h4 {
  margin:0 0 12px;
  font-size:15px;
  font-family:var(--display);
}
.field-span-2 { grid-column: span 2; }
.form-actions { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-top:14px; }
.form-hint { color:var(--muted); font-size:12px; line-height:1.5; }
.primary-button { border:0; border-radius:14px; padding:11px 16px; color:#fff; background:linear-gradient(135deg,var(--brand),var(--brand-2)); font-weight:900; cursor:pointer; }
.danger-button { border:1px solid rgba(180,72,61,.16); border-radius:12px; padding:8px 12px; color:var(--red); background:#fff4f2; font-weight:800; cursor:pointer; }
.notice-banner { border:1px solid var(--line); border-radius:18px; padding:14px 16px; margin-bottom:16px; line-height:1.6; }
.notice-banner.success { border-color:#b7dfbf; background:#eaf8ee; color:#205a33; }
.notice-banner.error { border-color:#f0c36d; background:#fff7df; color:#7a4b00; }
.action-cell { white-space:nowrap; }
.ghost-button { border:1px solid rgba(13,59,102,.16); border-radius:12px; padding:8px 12px; color:var(--brand); background:#f5f9fc; font-weight:800; cursor:pointer; }
.portfolio-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
.compact-table td, .compact-table th { white-space:nowrap; }
.compact-table td:nth-child(1) { white-space:normal; }
.editor-toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; }
.section-subtitle {
  margin:0;
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.detail-shell {
  margin-top: 14px;
  border: 1px solid var(--line);
  border-radius: 18px;
  background: rgba(255,255,255,.74);
  overflow: hidden;
}
.detail-shell > summary {
  list-style: none;
  cursor: pointer;
  padding: 12px 14px;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  font-weight:800;
  color: var(--ink);
}
.detail-shell > summary::-webkit-details-marker { display:none; }
.detail-shell > summary::after {
  content: "更多";
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: .04em;
}
.detail-shell[open] > summary::after { content: "收起"; }
.detail-body { padding: 0 14px 14px; }
.compact-detail { margin-top: 8px; border-radius: 14px; }
.compact-detail > summary { padding: 9px 12px; font-size: 13px; }
.compact-detail .detail-body { padding: 0 10px 10px; }
.compact-detail .quality-banner { margin: 0; border-radius: 14px; padding: 11px 12px; font-size: 13px; }
.portfolio-list-meta { display:flex; flex-wrap:wrap; gap:8px; margin-bottom:12px; }
.portfolio-chip { border:1px solid var(--line); background:#fff; border-radius:999px; padding:7px 10px; color:var(--muted); font-size:12px; }
.portfolio-action-bar {
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin-bottom:14px;
}
.portfolio-inline-button {
  border:1px solid rgba(13,59,102,.16);
  border-radius:14px;
  padding:10px 14px;
  background:#fff;
  color:var(--brand);
  font-weight:800;
  cursor:pointer;
}
.portfolio-inline-button.primary {
  border:0;
  color:#fff;
  background:linear-gradient(135deg,var(--brand),var(--brand-2));
}
.empty-state {
  border:1px dashed var(--line);
  border-radius:18px;
  padding:18px;
  background:rgba(255,255,255,.62);
  color:var(--muted);
  text-align:center;
}
.empty-state strong {
  display:block;
  color:var(--ink);
  font-size:15px;
  margin-bottom:6px;
}
.empty-state p {
  margin:0;
  line-height:1.6;
  font-size:13px;
}
.portfolio-control-grid {
  display:grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap:12px;
}
.portfolio-flag {
  border:1px solid var(--line);
  border-radius:18px;
  padding:14px;
  background:linear-gradient(180deg, #fff, #f3f7fa);
}
.portfolio-flag span {
  display:block;
  color:var(--muted);
  font-size:12px;
}
.portfolio-flag strong {
  display:block;
  margin-top:6px;
  font-size:17px;
}
.portfolio-table td strong + span {
  display:block;
  margin-top:4px;
  color:var(--muted);
  font-size:12px;
}
.table-note {
  display:grid;
  gap:6px;
  min-width: 220px;
}
.table-note span {
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
}
.stock-workspace { display:grid; grid-template-columns:minmax(0,1.3fr) minmax(300px,.9fr); gap:16px; align-items:start; }
.stock-main,
.stock-side { display:grid; gap:16px; }
.ticket-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:14px; }
.ticket-card { border:1px solid var(--line); border-radius:18px; padding:13px; background:linear-gradient(180deg,#fff,#f2f7fb); }
.ticket-card span { display:block; color:var(--muted); font-size:12px; }
.ticket-card strong { display:block; margin-top:6px; font-size:18px; }
.signal-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.signal-card { border:1px solid var(--line); border-radius:18px; padding:14px; background:linear-gradient(180deg,#fff,#eef4f8); }
.signal-card span { display:block; color:var(--muted); font-size:12px; }
.signal-card strong { display:block; margin-top:7px; font-size:20px; font-family: var(--display); }
.analysis-grid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px; }
.stack-list { display:grid; gap:12px; }
.stack-card { border:1px solid var(--line); border-radius:18px; padding:14px; background:#fff; }
.stack-card strong { display:block; margin-bottom:7px; }
.debate-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
.advice-board { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.module-subgrid { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr); gap:16px; }
.summary-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }
.summary-card {
  border:1px solid var(--line);
  border-radius:18px;
  padding:14px;
  background:linear-gradient(180deg,#fff,#f3f7fa);
}
.summary-card span {
  display:block;
  color:var(--muted);
  font-size:11px;
  margin-bottom:6px;
}
.summary-card strong {
  display:block;
  font-size:16px;
  margin-bottom:5px;
}
.report-summary-list {
  margin: 0;
  padding-left: 18px;
  color: var(--muted);
  line-height: 1.7;
}
.report-summary-list li + li {
  margin-top: 6px;
}
.ops-flow {
  display: grid;
  gap: 10px;
}
.ops-step {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  border: 1px solid var(--line);
  border-radius: 15px;
  padding: 11px;
  background: rgba(255,255,255,.76);
}
.ops-step-index {
  width: 34px;
  height: 34px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #17344d;
  color: #edf5fb;
  font-weight: 900;
  font-family: var(--mono);
}
.ops-step strong {
  display: block;
  margin-bottom: 5px;
}
.ops-step p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.compact-note-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.compact-note-card {
  border:1px solid var(--line);
  border-radius:16px;
  padding:13px;
  background:#fff;
}
.compact-note-card strong {
  display:block;
  margin-bottom:8px;
  font-size:15px;
}
.compact-note-card ul { margin:0; padding-left:18px; color:var(--muted); line-height:1.65; }
.compact-metric-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.compact-metric-card {
  border:1px solid var(--line);
  border-radius:16px;
  padding:13px;
  background:rgba(255,255,255,.78);
}
.compact-metric-card span {
  display:block;
  color:var(--muted);
  font-size:12px;
}
.compact-metric-card strong {
  display:block;
  margin-top:7px;
  font-size:18px;
}
.freshness-bar {
  position: sticky;
  top: 10px;
  z-index: 20;
  display:grid;
  grid-template-columns:minmax(190px,1.35fr) repeat(2,minmax(110px,1fr)) auto;
  gap:0;
  margin: 0 0 14px;
  padding:0;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:18px;
  background:#fffdf8;
  backdrop-filter:blur(16px);
  box-shadow:0 12px 34px rgba(19,39,58,.08);
}
.research-tape-primary {
  display:grid;
  align-content:center;
  gap:4px;
  min-width:0;
  padding:13px 16px;
  color:#edf5fa;
  background:linear-gradient(135deg,#10283d,#173a55);
}
.research-tape-primary span,
.research-tape-item span {
  display:block;
  font-family:var(--mono);
  font-size:9px;
  font-weight:850;
  letter-spacing:.07em;
  text-transform:uppercase;
}
.research-tape-primary span { color:#d7b978; }
.research-tape-primary strong {
  display:block;
  font-family:var(--display);
  font-size:18px;
  line-height:1.15;
  color:#fff;
}
.research-tape-primary small {
  color:#b9cad6;
  font-size:10px;
  line-height:1.35;
}
.research-tape-item {
  display:grid;
  align-content:center;
  gap:5px;
  min-width:0;
  padding:12px;
  border-left:1px solid var(--line);
  background:rgba(255,253,248,.78);
}
.research-tape-item span { color:var(--muted); }
.research-tape-item strong {
  display:block;
  color:var(--ink);
  font-family:var(--mono);
  font-size:12px;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}
.research-tape-data-link {
  display:grid;
  place-items:center;
  gap:8px;
  padding:12px;
  color:var(--brand);
  background:var(--accent-soft);
  font-size:11px;
  font-weight:900;
  white-space:nowrap;
}
.research-tape-data-link span { color:var(--accent); font-family:var(--mono); }
.research-tape[data-gate-level="high"] .research-tape-primary {
  background:linear-gradient(135deg,#472527,#7d342f);
}
.research-tape[data-gate-level="mid"] .research-tape-primary {
  background:linear-gradient(135deg,#3d321c,#76551f);
}
.data-center-summary {
  display:flex;
  align-items:center;
  gap:12px;
  margin:0 0 14px;
  padding:10px 14px;
  border:1px solid var(--line);
  border-radius:16px;
  background:#fff;
  color:var(--muted);
  font-size:13px;
}
.data-center-summary strong {
  color:var(--ink);
  flex:1;
}
.data-center-summary a {
  color:var(--accent);
  font-weight:700;
  text-decoration:none;
}
.data-center-summary.warn { border-color:#dfc28e; background:#fffaf0; }
.data-center-summary.blocked { border-color:#e6aaa1; background:#fff3f0; }
.data-command-center {
  margin:0 0 16px;
  border-color:rgba(13,59,102,.18);
  background:rgba(255,253,248,.96);
}
.data-command-toolbar { margin-bottom:14px; }
.data-readiness-brief {
  display:grid;
  grid-template-columns:minmax(230px,.78fr) minmax(0,1.72fr);
  min-height:218px;
  margin:0 0 20px;
  overflow:hidden;
  border:1px solid rgba(16,40,61,.16);
  border-radius:20px;
  background:#fffdf8;
  box-shadow:0 18px 38px rgba(16,40,61,.08);
}
.data-readiness-state {
  display:grid;
  align-content:center;
  gap:8px;
  padding:28px;
  color:#eef5f8;
  background:#10283d;
}
.data-readiness-brief.state-blocked .data-readiness-state {
  box-shadow:inset 6px 0 0 #7d342f;
}
.data-readiness-brief.state-warn .data-readiness-state {
  box-shadow:inset 6px 0 0 #bd8b33;
}
.data-readiness-brief.state-ready .data-readiness-state {
  box-shadow:inset 6px 0 0 #247153;
}
.data-readiness-state > span,
.data-readiness-metrics span,
.data-readiness-thesis small span {
  color:#d7b978;
  font-family:var(--mono);
  font-size:9px;
  font-weight:850;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.data-readiness-state h3 {
  margin:0;
  color:#fff;
  font-family:var(--display);
  font-size:36px;
  line-height:1;
}
.data-readiness-state strong {
  color:#dce9ef;
  font-size:13px;
  line-height:1.55;
}
.data-readiness-thesis {
  display:grid;
  align-content:center;
  gap:18px;
  padding:28px 30px;
}
.data-readiness-thesis > p {
  margin:0;
  color:var(--ink);
  font-family:var(--display);
  font-size:20px;
  font-weight:850;
  line-height:1.4;
}
.data-readiness-metrics {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  border:1px solid var(--line);
  border-radius:14px;
  overflow:hidden;
}
.data-readiness-metrics > div {
  display:grid;
  gap:5px;
  padding:12px;
  background:#fff;
}
.data-readiness-metrics > div + div { border-left:1px solid var(--line); }
.data-readiness-metrics span { color:var(--muted); }
.data-readiness-metrics strong {
  color:var(--ink);
  font-family:var(--mono);
  font-size:20px;
}
.data-readiness-thesis small {
  display:flex;
  gap:10px;
  align-items:flex-start;
  color:var(--ink-soft);
  font-size:12px;
  line-height:1.55;
}
.data-readiness-thesis small span { flex:0 0 auto; margin-top:2px; color:var(--accent); }
.data-operations-grid {
  display:grid;
  grid-template-columns:minmax(0,1.22fr) minmax(330px,.78fr);
  gap:18px;
  align-items:start;
}
.data-recovery-section,
.data-impact-section {
  min-width:0;
  padding:18px;
  border:1px solid var(--line);
  border-radius:18px;
  background:rgba(255,255,255,.72);
}
.data-recovery-rail { display:grid; gap:12px; }
.data-recovery-step {
  position:relative;
  display:grid;
  grid-template-columns:48px minmax(0,1fr);
  gap:12px;
  min-width:0;
}
.data-recovery-step::before {
  content:"";
  position:absolute;
  z-index:0;
  top:44px;
  bottom:-20px;
  left:23px;
  width:1px;
  background:rgba(189,139,51,.34);
}
.data-recovery-step:last-child::before { display:none; }
.data-recovery-number {
  position:relative;
  z-index:1;
  display:grid;
  place-items:center;
  width:46px;
  height:46px;
  border:1px solid rgba(189,139,51,.44);
  border-radius:50%;
  color:#805b1f;
  background:#fff9ec;
  font-family:var(--mono);
  font-size:12px;
  font-weight:900;
}
.data-recovery-step.severity-blocked .data-recovery-number {
  border-color:rgba(125,52,47,.42);
  color:#7d342f;
  background:#fff3f0;
}
.data-recovery-copy {
  min-width:0;
  padding:14px 15px;
  border:1px solid var(--line);
  border-radius:14px;
  background:#fff;
}
.data-recovery-copy header,
.data-impact-lane header {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
}
.data-recovery-copy header strong,
.data-impact-lane header strong { color:var(--ink); font-size:15px; }
.data-recovery-copy header em,
.data-impact-lane header em {
  padding:3px 8px;
  border-radius:999px;
  color:#7d342f;
  background:#fff3f0;
  font-family:var(--mono);
  font-size:9px;
  font-style:normal;
  font-weight:900;
}
.data-recovery-copy p {
  display:grid;
  grid-template-columns:68px minmax(0,1fr);
  gap:8px;
  margin:10px 0 0;
  color:var(--ink-soft);
  font-size:12px;
  line-height:1.5;
}
.data-recovery-copy p span,
.data-recovery-copy small span {
  color:var(--muted);
  font-family:var(--mono);
  font-size:9px;
  font-weight:850;
  letter-spacing:.04em;
}
.data-recovery-copy small {
  display:grid;
  grid-template-columns:68px minmax(0,1fr);
  gap:8px;
  margin-top:10px;
  padding-top:10px;
  border-top:1px dashed var(--line);
  color:var(--muted);
  line-height:1.45;
}
.data-recovery-empty {
  padding:22px;
  border:1px dashed rgba(36,113,83,.34);
  border-radius:14px;
  background:#f2faf6;
}
.data-recovery-empty strong { color:#247153; }
.data-recovery-empty p { margin:8px 0 0; color:var(--muted); }
.data-impact-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
.data-impact-lane {
  min-width:0;
  padding:13px;
  border:1px solid var(--line);
  border-left:4px solid #247153;
  border-radius:12px;
  background:#fff;
}
.data-impact-lane.state-blocked { border-left-color:#7d342f; }
.data-impact-lane.state-warn { border-left-color:#bd8b33; }
.data-impact-lane.state-warn header em { color:#805b1f; background:#fff9ec; }
.data-impact-lane.state-ready header em { color:#247153; background:#eef8f2; }
.data-impact-lane p { min-height:38px; margin:10px 0 8px; color:var(--ink-soft); font-size:11px; line-height:1.45; }
.data-impact-lane small { color:var(--muted); font-size:10px; line-height:1.4; }
.data-source-ledger {
  margin-top:18px;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:16px;
  background:#fffdf8;
}
.data-source-ledger summary {
  cursor:pointer;
  list-style:none;
  padding:14px 16px;
  color:var(--brand);
  font-size:12px;
  font-weight:900;
}
.data-source-ledger summary::-webkit-details-marker { display:none; }
.data-source-ledger summary::after { content:"＋"; float:right; color:var(--accent); }
.data-source-ledger[open] summary::after { content:"－"; }
.data-ledger-scroll { overflow:auto; border-top:1px solid var(--line); }
.data-ledger-table { width:100%; border-collapse:collapse; table-layout:fixed; }
.data-ledger-table th,
.data-ledger-table td {
  padding:10px;
  border-bottom:1px solid var(--line);
  color:var(--ink-soft);
  font-size:10px;
  line-height:1.45;
  text-align:left;
  vertical-align:top;
  overflow-wrap:anywhere;
}
.data-ledger-table th { color:var(--muted); background:#f3f0e8; font-family:var(--mono); font-size:9px; }
.data-ledger-card td:first-child { color:var(--ink); }
.data-ledger-card.state-blocked td { background:#fff5f2; }
.data-ledger-card.state-warn td { background:#fffbf1; }
.data-ledger-card td:nth-child(1),
.data-ledger-card td:nth-child(2) { width:9%; }
.data-ledger-card td:nth-child(3) { width:15%; }
.data-ledger-card td:nth-child(4) { width:18%; }
.data-ledger-empty td { padding:18px; color:var(--muted); text-align:center; }
@media (max-width: 920px) {
  .data-operations-grid { grid-template-columns:1fr; }
}
.sector-top5-panel,
.market-mover-panel,
.market-mover-strip {
  margin-top:12px;
  padding:12px;
  border:1px solid var(--line);
  border-radius:16px;
  background:rgba(255,255,255,.84);
}
.sector-top5-head {
  display:flex;
  align-items:baseline;
  justify-content:space-between;
  gap:12px;
  margin-bottom:10px;
}
.sector-top5-head strong { color:var(--ink); }
.sector-top5-head span,
.market-mover-strip span {
  color:var(--muted);
  font-size:12px;
}
.compact-sector-table td { vertical-align:top; }
.market-mover-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
}
.market-mover-card {
  border:1px solid rgba(13,59,102,.10);
  border-radius:14px;
  padding:10px;
  background:#fff;
}
.market-mover-card span {
  display:block;
  color:var(--muted);
  font-size:11px;
  margin-bottom:5px;
}
.market-mover-card strong { display:block; font-size:14px; }
.market-mover-card p {
  margin:6px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
}
.action-desk {
  display:grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, .8fr);
  gap:16px;
  align-items:stretch;
}
.action-desk-hero {
  position:relative;
  overflow:hidden;
  border:1px solid rgba(13,59,102,.16);
  border-radius:26px;
  padding:22px;
  background:linear-gradient(135deg, rgba(180,133,58,.18), transparent 34%), linear-gradient(135deg, #11263b, #173b59);
  color:#f3f8fc;
}
.action-desk-hero h3 { margin:0 0 12px; font-size:30px; letter-spacing:-.04em; font-family:var(--display); }
.action-desk-hero p { margin:0; color:rgba(243,248,252,.78); line-height:1.7; }
.action-desk-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:18px; }
.action-desk-metric { border:1px solid rgba(255,255,255,.16); border-radius:16px; padding:13px; background:rgba(255,255,255,.10); }
.action-desk-metric span { display:block; color:rgba(243,248,252,.64); font-size:12px; }
.action-desk-metric strong { display:block; margin-top:7px; font-size:17px; }
.action-copy-button {
  margin-top:14px;
  border:1px solid rgba(255,255,255,.22);
  border-radius:14px;
  padding:11px 14px;
  color:#142b41;
  background:linear-gradient(135deg, #f3e2bf, #b4853a);
  font-weight:900;
  cursor:pointer;
}
.action-lanes { display:grid; gap:10px; }
.action-lane { border:1px solid var(--line); border-radius:20px; padding:16px; background:rgba(255,255,255,.84); text-align:left; color:var(--ink); cursor:pointer; }
.action-lane strong { display:block; font-size:16px; margin-bottom:6px; }
.action-lane p { margin:0; color:var(--muted); line-height:1.55; font-size:13px; }
.portfolio-queue-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.portfolio-queue-lane { border:1px solid var(--line); border-radius:20px; padding:15px; background:linear-gradient(180deg,#fff,#f0f6fa); min-height:160px; }
.portfolio-queue-lane h3 { margin:0 0 10px; font-size:16px; }
.queue-stock { border-top:1px dashed var(--line); padding:10px 0 0; margin-top:10px; }
.queue-stock strong { display:block; }
.queue-stock span { display:block; color:var(--muted); font-size:12px; margin-top:4px; line-height:1.45; }
.stock-workspace-drawer { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(300px,.55fr); gap:16px; align-items:start; margin-top:16px; }
.evidence-drawer { position:sticky; top:86px; border:1px solid var(--line); border-radius:22px; padding:16px; background:linear-gradient(180deg,#fff,#edf4f8); box-shadow:0 16px 40px rgba(19,39,58,.08); }
.evidence-drawer h3 { margin:0 0 12px; font-size:18px; font-family:var(--display); }
.drawer-row { border-top:1px dashed var(--line); padding:11px 0; }
.drawer-row:first-of-type { border-top:0; padding-top:0; }
.drawer-row span { display:block; color:var(--muted); font-size:12px; margin-bottom:4px; }
.drawer-row strong { display:block; line-height:1.45; }
.split-focus {
  display:grid;
  grid-template-columns:minmax(0,1.1fr) minmax(280px,.9fr);
  gap:16px;
  align-items:start;
}
.portfolio-command-console {
  display:grid;
  grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr);
  gap:16px;
  margin:16px 0;
  align-items:stretch;
}
.portfolio-command-hero {
  position:relative;
  overflow:hidden;
  min-height:220px;
  border:1px solid rgba(13,59,102,.18);
  border-radius:30px;
  padding:22px;
  color:#f4f8fb;
  background:
    radial-gradient(circle at 86% 18%, rgba(229,185,111,.28), transparent 28%),
    linear-gradient(135deg, #17202a, #1f415d);
}
.portfolio-command-console.risk .portfolio-command-hero {
  background:
    radial-gradient(circle at 86% 18%, rgba(229,185,111,.24), transparent 28%),
    linear-gradient(135deg, #3b1d1c, #183049);
}
.portfolio-command-console.steady .portfolio-command-hero {
  background:
    radial-gradient(circle at 86% 18%, rgba(229,185,111,.22), transparent 28%),
    linear-gradient(135deg, #123329, #1f4d3e);
}
.portfolio-command-hero h3 {
  margin:10px 0 12px;
  font-family:var(--display);
  font-size:clamp(30px, 4vw, 52px);
  letter-spacing:-.05em;
  line-height:1;
}
.portfolio-command-hero p {
  margin:0;
  max-width:760px;
  color:rgba(244,248,251,.78);
  line-height:1.7;
}
.portfolio-command-meta {
  position:absolute;
  left:22px;
  right:22px;
  bottom:20px;
  display:flex;
  justify-content:space-between;
  gap:12px;
  border-top:1px solid rgba(255,255,255,.14);
  padding-top:14px;
}
.portfolio-command-meta span {
  color:rgba(244,248,251,.62);
  font-family:var(--mono);
  font-size:12px;
}
.portfolio-command-meta strong {
  color:#fff;
  text-align:right;
}
.portfolio-command-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.portfolio-command-card {
  border:1px solid var(--line);
  border-radius:24px;
  padding:16px;
  background:
    linear-gradient(135deg, rgba(13,59,102,.07), transparent 36%),
    rgba(255,255,255,.9);
}
.portfolio-command-card span {
  display:block;
  color:var(--brand);
  font-family:var(--mono);
  font-size:11px;
  font-weight:900;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.portfolio-command-card strong {
  display:block;
  margin-top:10px;
  font-size:18px;
  line-height:1.35;
}
.portfolio-command-card p {
  margin:9px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.portfolio-exposure-layout {
  display:grid;
  grid-template-columns:minmax(0,1.2fr) minmax(260px,.8fr);
  gap:14px;
}
.portfolio-exposure-bars,
.portfolio-weight-tiles {
  display:grid;
  gap:10px;
}
.portfolio-exposure-row {
  display:grid;
  grid-template-columns:minmax(130px,.8fr) minmax(0,1.1fr) 64px;
  gap:12px;
  align-items:center;
  border:1px solid var(--line);
  border-radius:18px;
  padding:12px;
  background:#fff;
}
.portfolio-exposure-row strong,
.portfolio-exposure-row span,
.portfolio-exposure-row em {
  display:block;
}
.portfolio-exposure-row span {
  margin-top:3px;
  color:var(--muted);
  font-size:12px;
}
.portfolio-exposure-row i {
  display:block;
  height:12px;
  border-radius:999px;
  overflow:hidden;
  background:#dde6ee;
}
.portfolio-exposure-row i b {
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg, var(--brand), var(--accent));
}
.portfolio-exposure-row.hot i b {
  background:linear-gradient(90deg, #9a4338, #d98c56);
}
.portfolio-exposure-row.steady i b {
  background:linear-gradient(90deg, #2f855a, #8fbf9f);
}
.portfolio-exposure-row em {
  color:var(--ink);
  font-family:var(--mono);
  font-style:normal;
  font-weight:900;
  text-align:right;
}
.portfolio-weight-tile {
  border:1px solid var(--line);
  border-radius:18px;
  padding:13px;
  background:linear-gradient(180deg,#fff,#f2f7fb);
}
.portfolio-weight-tile.risk {
  border-color:#efb9b2;
  background:linear-gradient(180deg,#fff,#fff3f1);
}
.portfolio-weight-tile span {
  display:block;
  color:var(--muted);
  font-family:var(--mono);
  font-size:11px;
}
.portfolio-weight-tile strong {
  display:block;
  margin-top:5px;
}
.portfolio-weight-tile p {
  margin:6px 0 0;
  color:var(--muted);
  font-size:12px;
}
.market-console {
  background:
    linear-gradient(135deg, rgba(180,133,58,.10), transparent 30%),
    linear-gradient(180deg, rgba(255,255,255,.94), rgba(240,246,250,.92));
}
.market-header {
  align-items:center;
}
.market-state-pill {
  border:1px solid var(--line);
  border-radius:999px;
  padding:8px 12px;
  background:#fff;
  color:var(--ink-soft);
  font-size:12px;
  font-weight:900;
}
.market-state-pill.hot { border-color:#b8d4c8; background:#e7f4ee; color:#245b47; }
.market-state-pill.cold { border-color:#efb9b2; background:#fff0ee; color:#973b31; }
.market-state-pill.balanced { border-color:#ddc7a2; background:#fbf3e5; color:#7b5b26; }
.market-focus-board {
  display:grid;
  grid-template-columns:minmax(260px,1.15fr) repeat(3,minmax(0,.95fr));
  gap:12px;
  margin:14px 0 16px;
}
.market-focus-main,
.market-focus-card {
  border:1px solid var(--line);
  border-radius:22px;
  padding:16px;
  background:#fff;
}
.market-focus-main {
  color:#edf5fb;
  background:linear-gradient(135deg, #102a43, #174565);
}
.market-focus-board.hot .market-focus-main {
  background:linear-gradient(135deg, #123329, #176047);
}
.market-focus-board.cold .market-focus-main {
  background:linear-gradient(135deg, #4a2020, #183049);
}
.market-focus-main span,
.market-focus-card span {
  display:block;
  color:var(--muted);
  font-size:12px;
  font-weight:900;
}
.market-focus-main span,
.market-focus-main p {
  color:rgba(237,245,251,.76);
}
.market-focus-main strong,
.market-focus-card strong {
  display:block;
  margin-top:9px;
  font-family:var(--display);
  font-size:24px;
  line-height:1.12;
  letter-spacing:-.04em;
}
.market-focus-main strong {
  color:#fff;
  font-size:34px;
}
.market-focus-main p,
.market-focus-card p {
  margin:10px 0 0;
  color:var(--muted);
  line-height:1.55;
  font-size:13px;
}
.market-focus-main .market-action-snapshot {
  margin-top:12px;
}
.market-focus-main .score-bar {
  margin-top:12px;
  background:rgba(255,255,255,.20);
}
.market-focus-main .score-fill {
  background:#d9b26f;
}
.market-focus-facts {
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin:-4px 0 16px;
}
.market-focus-facts span,
.market-focus-facts a {
  border:1px solid var(--line);
  border-radius:999px;
  padding:7px 10px;
  color:var(--muted);
  background:rgba(255,255,255,.78);
  font-size:12px;
}
.market-focus-facts a {
  color:var(--brand);
  font-weight:900;
}
.market-command-grid {
  display:grid;
  grid-template-columns:minmax(0,1.04fr) minmax(340px,.96fr);
  gap:16px;
  align-items:stretch;
}
.market-gate-card {
  position:relative;
  overflow:hidden;
  min-height:310px;
  border:1px solid rgba(13,59,102,.18);
  border-radius:28px;
  padding:22px;
  color:#edf5fb;
  background:
    radial-gradient(circle at 82% 22%, rgba(255,255,255,.18), transparent 28%),
    linear-gradient(135deg, #11263b, #173b59);
}
.market-gate-card.hot {
  background:
    radial-gradient(circle at 82% 22%, rgba(255,255,255,.18), transparent 28%),
    linear-gradient(135deg, #123329, #17533f);
}
.market-gate-card.cold {
  background:
    radial-gradient(circle at 82% 22%, rgba(255,255,255,.16), transparent 28%),
    linear-gradient(135deg, #3a1b1b, #183049);
}
.market-gate-copy {
  position:relative;
  z-index:1;
  max-width:68%;
}
.market-kicker {
  display:inline-flex;
  border:1px solid rgba(255,255,255,.18);
  border-radius:999px;
  padding:7px 10px;
  color:rgba(237,245,251,.72);
  background:rgba(255,255,255,.08);
  font-family:var(--mono);
  font-size:11px;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.market-gate-card h3 {
  margin:14px 0 10px;
  font-size:clamp(28px, 4vw, 48px);
  letter-spacing:-.05em;
  line-height:1;
  font-family:var(--display);
}
.market-gate-card p {
  margin:0;
  color:rgba(237,245,251,.78);
  line-height:1.65;
}
.market-action-snapshot {
  display:inline-flex;
  gap:8px;
  align-items:center;
  margin-top:14px;
  border:1px solid rgba(255,255,255,.16);
  border-radius:999px;
  padding:8px 11px;
  background:rgba(255,255,255,.08);
}
.market-action-snapshot span {
  color:rgba(237,245,251,.62);
  font-size:12px;
}
.market-action-snapshot strong {
  color:#fff;
  font-size:13px;
}
.market-heat-dial {
  position:absolute;
  right:22px;
  top:24px;
  width:128px;
  height:128px;
  border-radius:999px;
  display:grid;
  place-items:center;
  background:
    radial-gradient(circle at center, #172d44 0 56%, transparent 58%),
    conic-gradient(#e5b96f var(--heat), rgba(255,255,255,.18) 0);
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.12);
}
.market-heat-dial span {
  display:block;
  font-size:32px;
  font-weight:900;
  font-family:var(--display);
}
.market-heat-dial small {
  position:absolute;
  margin-top:48px;
  color:rgba(237,245,251,.62);
  font-family:var(--mono);
  font-size:10px;
  letter-spacing:.12em;
  text-transform:uppercase;
}
.market-score-wrap {
  position:absolute;
  left:22px;
  right:22px;
  bottom:72px;
  height:8px;
}
.market-score-wrap .score-bar {
  height:100%;
  background:rgba(255,255,255,.16);
}
.market-gate-footer {
  position:absolute;
  inset:auto 22px 22px;
  display:grid;
  gap:7px;
  border-top:1px solid rgba(255,255,255,.14);
  padding-top:14px;
}
.market-gate-footer span {
  color:rgba(237,245,251,.60);
  font-family:var(--mono);
  font-size:12px;
}
.market-gate-footer strong {
  color:#fff;
  line-height:1.45;
}
.market-tape-card,
.market-panel {
  border-radius:28px;
}
.market-tape-card {
  border:1px solid var(--line);
  padding:18px;
  background:
    linear-gradient(135deg, rgba(13,59,102,.08), transparent 32%),
    rgba(255,255,255,.86);
}
.market-tape-head {
  display:flex;
  justify-content:space-between;
  gap:12px;
  margin-bottom:12px;
}
.market-tape-head span {
  color:var(--brand);
  font-size:12px;
  font-weight:900;
  letter-spacing:.08em;
  text-transform:uppercase;
  font-family:var(--mono);
}
.market-tape-head strong {
  color:var(--muted);
  font-size:12px;
}
.market-index-spine {
  display:grid;
  gap:9px;
}
.market-index-row {
  display:grid;
  grid-template-columns:minmax(108px,.8fr) minmax(0,1.2fr) 82px;
  gap:12px;
  align-items:center;
  border:1px solid rgba(13,59,102,.09);
  border-radius:16px;
  padding:11px 12px;
  background:rgba(255,255,255,.78);
}
.market-index-name strong,
.market-index-value strong {
  display:block;
  font-size:14px;
}
.market-index-name span,
.market-index-value span {
  display:block;
  margin-top:3px;
  color:var(--muted);
  font-size:11px;
  font-family:var(--mono);
}
.market-index-track {
  height:10px;
  border-radius:999px;
  overflow:hidden;
  background:#dde6ee;
}
.market-index-track i {
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg, var(--brand), var(--accent));
}
.market-index-row.down .market-index-track i {
  background:linear-gradient(90deg, #9a4338, #d98c56);
}
.market-index-row.down .market-index-value strong {
  color:var(--red);
}
.market-radar-grid {
  display:grid;
  grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  gap:16px;
  margin-top:16px;
}
.market-radar-grid.wide-left {
  grid-template-columns:minmax(0,1.22fr) minmax(300px,.78fr);
}
.market-lamp-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:12px;
  margin-top:14px;
}
.market-lamp {
  border:1px solid var(--line);
  border-radius:18px;
  padding:14px;
  background:#fff;
}
.market-lamp.hot { border-color:#b8d4c8; background:#eef8f3; }
.market-lamp.cold { border-color:#efb9b2; background:#fff3f1; }
.market-lamp.balanced { border-color:#ddc7a2; background:#fbf5e9; }
.market-lamp span,
.market-risk-card span {
  display:block;
  color:var(--muted);
  font-size:11px;
  font-family:var(--mono);
  letter-spacing:.08em;
  text-transform:uppercase;
}
.market-lamp strong {
  display:block;
  margin-top:7px;
  font-size:17px;
}
.market-lamp p {
  margin:7px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
}
.market-risk-stack,
.market-watch-stack {
  display:grid;
  gap:10px;
  margin-top:14px;
}
.market-risk-card {
  border:1px solid rgba(180,72,61,.16);
  border-radius:18px;
  padding:13px;
  background:linear-gradient(180deg, #fff, #fff3f1);
}
.market-risk-card strong {
  display:block;
  margin-top:6px;
  line-height:1.5;
}
.market-sector-heatmap {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.market-sector-tile {
  border:1px solid rgba(13,59,102,.12);
  border-radius:20px;
  padding:14px;
  text-align:left;
  color:var(--ink);
  background:linear-gradient(180deg, #fff, #eef5f9);
  cursor:pointer;
}
.market-sector-tile span,
.market-sector-tile strong,
.market-sector-tile em {
  display:block;
}
.market-sector-tile span {
  font-size:15px;
  font-weight:900;
}
.market-sector-tile strong {
  margin-top:7px;
  color:var(--brand);
  font-family:var(--mono);
}
.market-sector-tile i {
  display:block;
  height:9px;
  margin:11px 0;
  border-radius:999px;
  overflow:hidden;
  background:#dde6ee;
}
.market-sector-tile i b {
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg, var(--brand), var(--accent));
}
.market-sector-tile em {
  color:var(--muted);
  font-size:12px;
  font-style:normal;
  line-height:1.45;
}
.market-watch-item {
  display:grid;
  grid-template-columns:34px minmax(0,1fr);
  gap:10px;
  align-items:start;
  border:1px solid var(--line);
  border-radius:16px;
  padding:11px;
  background:#fff;
}
.market-watch-item span {
  width:34px;
  height:34px;
  display:grid;
  place-items:center;
  border-radius:12px;
  background:#17344d;
  color:#edf5fb;
  font-weight:900;
  font-family:var(--mono);
}
.market-watch-item p {
  margin:0;
  color:var(--muted);
  line-height:1.5;
  font-size:13px;
}
.market-action-bar {
  margin-top:14px;
}
@media (max-width: 1280px) {
  .topbar,
  .stock-workspace,
  .stock-workspace-drawer,
  .action-desk,
  .command-deck,
  .portfolio-command-console,
  .market-focus-board,
  .market-command-grid,
  .market-radar-grid,
  .market-radar-grid.wide-left { grid-template-columns: 1fr; }
  .desk-status { grid-template-columns: repeat(4, minmax(0, 1fr)); }
}
@media (max-width: 1120px) {
  .app-shell { grid-template-columns: 1fr; }
  .sidebar { position:relative; height:auto; }
  .nav-group { grid-template-columns: repeat(3, minmax(0,1fr)); }
  .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .grid-2,
  .grid-3,
  .research-lane,
  .matrix-grid,
  .action-strip,
  .app-toolbar,
  .workflow-grid,
  .portfolio-form-grid,
  .portfolio-kpis,
  .ticket-grid,
  .signal-grid,
  .analysis-grid,
  .debate-grid,
  .advice-board,
  .module-subgrid,
  .summary-grid,
  .compact-note-grid,
  .compact-metric-grid,
  .freshness-bar,
  .data-center-brief,
  .market-mover-grid,
  .action-desk-grid,
  .portfolio-queue-grid,
  .split-focus,
  .desk-strip-actions,
  .portfolio-control-grid,
  .portfolio-command-grid,
  .portfolio-exposure-layout,
  .market-sector-heatmap { grid-template-columns: 1fr; }
  .evidence-drawer { position:static; }
  .command-summary { max-width:100%; }
  .field-span-2 { grid-column: span 1; }
  .topbar { grid-template-columns: 1fr; }
  .desk-status { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 680px) {
  .workspace { padding:18px; }
  .nav-group { grid-template-columns: 1fr; }
  .kpi-grid,
  .desk-status,
  .compare-row,
  .market-lamp-grid,
  .market-index-row { grid-template-columns: 1fr; }
  .market-gate-copy { max-width:100%; }
  .market-heat-dial { position:relative; right:auto; top:auto; margin:18px 0 74px; }
  .data-center-summary {
    display:grid;
    grid-template-columns:minmax(0,1fr) auto;
    gap:6px 12px;
    align-items:start;
  }
  .data-center-summary > strong {
    grid-column:1 / -1;
    grid-row:2;
    line-height:1.45;
  }
  .data-center-summary > span:nth-of-type(2) {
    grid-column:1;
    grid-row:3;
  }
  .data-center-summary > a {
    grid-column:2;
    grid-row:1 / 4;
    align-self:center;
    white-space:nowrap;
  }
  .data-table { font-size:12px; }
  .compare-value { text-align: left; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .module-view,
  .workflow-card:hover { animation:none; transform:none; transition:none; }
}
.workspace-shell { display:grid; gap:14px; }
.workspace-panel-tabs {
  display:flex;
  gap:10px;
  margin: 0 0 12px;
  padding: 8px;
  border:1px solid var(--line);
  border-radius:18px;
  background:rgba(255,255,255,.72);
}
.workspace-panel-tab {
  border:0;
  border-radius:12px;
  padding:10px 14px;
  background:transparent;
  color:var(--muted);
  cursor:pointer;
  font-weight:800;
}
.workspace-panel-tab.active {
  background:linear-gradient(135deg,var(--brand),var(--brand-2));
  color:#fff;
}
.workspace-pane { display:none; }
.workspace-pane.active { display:block; }
.workspace-pane .module { margin-top: 0; }
.workspace-pane .module + .module { margin-top: 16px; }
.workspace-module-hidden { display:none; }
.toast {
  position: fixed;
  right: 22px;
  bottom: 22px;
  z-index: 50;
  max-width: min(360px, calc(100vw - 32px));
  padding: 12px 16px;
  border-radius: 14px;
  border: 1px solid rgba(180, 133, 58, .35);
  background: #142b41;
  color: #fff;
  box-shadow: 0 18px 42px rgba(19, 39, 58, .22);
  transform: translateY(10px);
  opacity: 0;
  transition: opacity .18s ease, transform .18s ease;
}
.toast.visible {
  transform: translateY(0);
  opacity: 1;
}
.copy-buffer {
  position: fixed;
  left: 22px;
  bottom: 22px;
  z-index: 49;
  width: min(520px, calc(100vw - 44px));
  height: 120px;
  padding: 12px;
  border: 1px solid var(--line-strong);
  border-radius: 14px;
  background: #fff;
  color: var(--ink);
  box-shadow: 0 18px 42px rgba(19, 39, 58, .18);
}
.stock-tabs {
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  margin: 0 0 14px;
  padding:8px;
  border:1px solid var(--line);
  border-radius:18px;
  background:rgba(255,255,255,.72);
}
.stock-tab {
  border:0;
  border-radius:12px;
  padding:10px 14px;
  background:transparent;
  color:var(--muted);
  cursor:pointer;
  font-weight:800;
}
.stock-tab.active {
  background:#17344d;
  color:#fff;
}
.stock-tab-panel { display:none; }
.stock-tab-panel.active { display:block; }

/* Professional terminal skin: compact, high-contrast, data-first. */
:root {
  --canvas: #eef1ed;
  --grid-line: rgba(19, 39, 58, .045);
  --surface-1: #fffdf8;
  --surface-2: #f4f0e8;
  --surface-3: #e9edf0;
  --ink: #101923;
  --ink-soft: #26394b;
  --muted: #687684;
  --line: #d7d2c8;
  --line-strong: #b8c0c7;
  --brand: #183954;
  --brand-2: #2b5876;
  --accent: #bd8b33;
  --accent-soft: #f4ead5;
  --up: #c84e3a;
  --down: #1f8a5b;
  --amber: #9a6a12;
  --red: #b94336;
  --green-soft: #e5f3ed;
  --shadow: 0 14px 36px rgba(16, 25, 35, .08);
}
body {
  background:
    radial-gradient(circle at 86% 2%, rgba(189, 139, 51, .16), transparent 24%),
    radial-gradient(circle at 0% 0%, rgba(24, 57, 84, .12), transparent 26%),
    repeating-linear-gradient(0deg, transparent 0 31px, var(--grid-line) 31px 32px),
    repeating-linear-gradient(90deg, transparent 0 31px, var(--grid-line) 31px 32px),
    linear-gradient(180deg, #f8f6f1 0%, var(--canvas) 100%);
}
.app-shell {
  grid-template-columns: 226px minmax(0, 1fr);
}
.sidebar {
  padding: 22px 12px 14px;
  background:
    linear-gradient(90deg, rgba(189,139,51,.20), transparent 1px),
    linear-gradient(180deg, #111d29 0%, #0b1520 100%);
  border-right: 1px solid rgba(255,255,255,.10);
}
.brand-mark {
  margin-bottom: 18px;
  padding: 0 4px;
}
.logo {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background:
    linear-gradient(135deg, rgba(255,255,255,.45), transparent 36%),
    linear-gradient(135deg, #f0c978, #a56e1d);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.24);
}
.brand-title {
  font-size: 17px;
  letter-spacing: .01em;
}
.brand-subtitle {
  color: rgba(232,242,250,.58);
  line-height: 1.35;
}
.nav-group {
  gap: 4px;
  margin: 14px 0 18px;
}
.nav-item {
  min-height: 42px;
  padding: 9px 11px;
  border-radius: 11px;
  font-weight: 760;
}
.nav-item:hover,
.nav-item.active {
  background: linear-gradient(90deg, rgba(255,255,255,.13), rgba(255,255,255,.05));
  border-color: rgba(189,139,51,.34);
  box-shadow: inset 3px 0 0 var(--accent);
}
.sidebar-note {
  padding: 12px;
  border-radius: 13px;
  background: rgba(255,255,255,.045);
  font-size: 12px;
}
.workspace {
  padding: 16px 18px 20px;
}
.workspace-shell {
  gap: 12px;
}
.workspace-pane.active {
  animation: reveal .18s ease both;
}
.module {
  position: relative;
  overflow: hidden;
  margin: 0;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(16,25,35,.13);
  background:
    linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,253,248,.88)),
    var(--surface-1);
  box-shadow: var(--shadow);
}
.module::before {
  content: "";
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, var(--up), var(--accent), var(--down));
}
.module-header {
  align-items: center;
  margin-bottom: 12px;
}
.module-title {
  font-size: 22px;
  letter-spacing: -.04em;
}
.module-title::after {
  content: "";
  display: block;
  width: 34px;
  height: 2px;
  margin-top: 6px;
  background: var(--accent);
}
.module-desc {
  color: #6e7b86;
}
.panel {
  border-radius: 14px;
  padding: 13px;
  border-color: rgba(16,25,35,.10);
  background:
    linear-gradient(180deg, rgba(255,255,255,.86), rgba(248,246,240,.82)),
    var(--surface-1);
  box-shadow: 0 1px 0 rgba(255,255,255,.70) inset;
}
.panel h3 {
  margin-bottom: 10px;
  font-size: 16px;
  letter-spacing: -.02em;
}
.grid-2,
.grid-3,
.summary-grid,
.workflow-grid,
.compact-note-grid,
.compact-metric-grid,
.portfolio-form-grid,
.ticket-grid,
.signal-grid,
.analysis-grid,
.debate-grid,
.advice-board,
.module-subgrid {
  gap: 12px;
}
.summary-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}
.summary-card {
  position: relative;
  min-height: 92px;
  border-radius: 14px;
  padding: 12px 12px 12px 15px;
  border-color: rgba(16,25,35,.10);
  background:
    linear-gradient(180deg, #ffffff, #f7f4ed);
  box-shadow: 0 10px 24px rgba(16,25,35,.045);
}
.summary-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, var(--accent), var(--brand-2));
}
.summary-card span,
.ticket-card span,
.signal-card span,
.desk-status-label {
  color: #75808a;
  font-size: 11px;
  letter-spacing: .04em;
}
.summary-card strong {
  font-size: 17px;
  color: var(--ink);
  line-height: 1.25;
}
.kpi-foot,
.section-subtitle,
.reason-list,
.compact-note-card ul {
  color: #66727d;
}
.workflow-grid {
  margin-top: 10px;
}
.workflow-card,
.desk-jump {
  border-radius: 14px;
  padding: 12px;
  border-color: rgba(24,57,84,.15);
  background:
    linear-gradient(135deg, rgba(189,139,51,.08), transparent 48%),
    linear-gradient(180deg, #ffffff, #f3f0e8);
  box-shadow: 0 9px 22px rgba(16,25,35,.055);
}
.workflow-card:hover,
.desk-jump:hover,
.portfolio-inline-button:hover,
.ghost-button:hover,
.primary-button:hover {
  transform: translateY(-1px);
  filter: saturate(1.06);
}
.workflow-card strong {
  font-size: 15px;
}
.workflow-card span {
  line-height: 1.45;
}
.data-table {
  border-collapse: collapse;
  border-spacing: 0;
  font-size: 13px;
}
.data-table th {
  padding: 8px 10px;
  color: #6b7480;
  background: rgba(233,237,240,.72);
  border-bottom: 1px solid var(--line);
}
.data-table td {
  padding: 10px;
  background: rgba(255,255,255,.72);
  border: 0;
  border-bottom: 1px solid rgba(16,25,35,.08);
}
.data-table td:first-child,
.data-table td:last-child {
  border-left: 0;
  border-right: 0;
  border-radius: 0;
}
.data-table tbody tr:hover td {
  background: #fff8ea;
}
.name-cell strong {
  font-size: 14px;
}
.name-cell span {
  color: #7a858f;
}
.risk-pill,
.status-pill,
.portfolio-chip,
.source-badge {
  border-radius: 999px;
  border-color: rgba(16,25,35,.12);
  background: rgba(255,255,255,.72);
}
.risk-pill.low {
  color: #116340;
  background: #e7f5ee;
}
.risk-pill.mid {
  color: #855c12;
  background: #fbefd8;
}
.risk-pill.high {
  color: #a7352b;
  background: #fbe5df;
}
.score-bar,
.compare-track {
  height: 8px;
  background: #e0ded8;
}
.score-fill,
.compare-fill.positive {
  background: linear-gradient(90deg, var(--down), var(--accent));
}
.compare-fill.negative {
  background: linear-gradient(90deg, var(--up), #d98c56);
}
.primary-button,
.app-toolbar button,
.stock-form button,
.portfolio-inline-button.primary,
.workspace-panel-tab.active {
  background: linear-gradient(135deg, #183954, #0f2639);
  box-shadow: 0 8px 18px rgba(24,57,84,.18);
}
.ghost-button,
.portfolio-inline-button {
  background: #fffaf0;
  border-color: rgba(24,57,84,.16);
  color: #173a56;
}
.field-stack input,
.field-stack textarea,
.field-stack select,
.stock-form input,
.app-toolbar input,
.app-toolbar select {
  border-radius: 11px;
  background: #fffdf8;
}
.report-copy {
  background:
    repeating-linear-gradient(0deg, transparent 0 27px, rgba(255,255,255,.04) 27px 28px),
    #101923;
  border-color: rgba(255,255,255,.12);
}
.empty-state {
  background: rgba(255,253,248,.72);
}
.toast {
  background: #101923;
}

.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 28px;
  color: var(--ink);
  background:
    radial-gradient(circle at 82% 10%, rgba(189,139,51,.22), transparent 24%),
    radial-gradient(circle at 15% 12%, rgba(24,57,84,.20), transparent 28%),
    repeating-linear-gradient(0deg, transparent 0 35px, rgba(18,33,46,.04) 35px 36px),
    linear-gradient(135deg, #f4efe4 0%, #e9e5da 100%);
}
.login-card {
  width: min(1080px, 100%);
  min-height: 620px;
  display: grid;
  grid-template-columns: minmax(0, 1.05fr) minmax(360px, .95fr);
  overflow: hidden;
  border: 1px solid rgba(16,25,35,.12);
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255,255,255,.74), rgba(255,253,248,.82));
  box-shadow: 0 34px 90px rgba(16,25,35,.18), inset 0 1px 0 rgba(255,255,255,.82);
}
.login-side,
.login-panel {
  position: relative;
  padding: 34px;
}
.login-side {
  display: grid;
  align-content: space-between;
  color: #f8efe0;
  background:
    linear-gradient(135deg, rgba(189,139,51,.26), transparent 44%),
    radial-gradient(circle at 86% 12%, rgba(255,255,255,.16), transparent 22%),
    linear-gradient(135deg, #142638 0%, #08131f 100%);
}
.login-side::after {
  content: "";
  position: absolute;
  inset: 18px;
  pointer-events: none;
  border-radius: 22px;
  border: 1px solid rgba(255,255,255,.08);
}
.login-brand {
  margin: 0;
  padding: 0;
  color: #fff;
}
.login-brand .brand-title {
  color: #fff;
}
.login-brand .brand-subtitle {
  color: rgba(248,239,224,.68);
}
.login-side-copy {
  max-width: 520px;
  position: relative;
  z-index: 1;
}
.login-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #bd8b33;
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 900;
  letter-spacing: .12em;
  text-transform: uppercase;
}
.login-kicker::before {
  content: "";
  width: 22px;
  height: 2px;
  background: currentColor;
}
.login-side h1 {
  margin: 18px 0 16px;
  color: #fff8ea;
  font-family: "Avenir Next Condensed", "Avenir Next", "PingFang SC", sans-serif;
  font-size: clamp(42px, 6vw, 74px);
  line-height: .92;
  letter-spacing: -.06em;
}
.login-side p {
  margin: 0;
  max-width: 440px;
  color: rgba(248,239,224,.72);
  font-size: 17px;
  line-height: 1.75;
}
.login-proof-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.login-proof-grid div {
  min-height: 118px;
  padding: 14px;
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 16px;
  background: rgba(255,255,255,.06);
  backdrop-filter: blur(8px);
}
.login-proof-grid span {
  color: rgba(248,239,224,.46);
  font-family: var(--mono);
  font-size: 11px;
}
.login-proof-grid strong {
  display: block;
  margin-top: 12px;
  color: #fff8ea;
  font-size: 16px;
}
.login-proof-grid p {
  margin-top: 7px;
  color: rgba(248,239,224,.60);
  font-size: 12px;
  line-height: 1.55;
}
.login-panel {
  display: grid;
  align-content: center;
  background: linear-gradient(180deg, rgba(255,255,255,.64), rgba(250,247,237,.86));
}
.login-panel h2 {
  margin: 14px 0 8px;
  font-family: "Avenir Next Condensed", "Avenir Next", "PingFang SC", sans-serif;
  font-size: 46px;
  line-height: 1;
  letter-spacing: -.05em;
}
.login-panel > p {
  margin: 0 0 22px;
  color: var(--muted);
  line-height: 1.7;
}
.login-form {
  display: grid;
  gap: 14px;
}
.login-form label {
  display: grid;
  gap: 8px;
  color: #596674;
  font-size: 13px;
  font-weight: 900;
}
.login-form input {
  width: 100%;
  height: 52px;
  border: 1px solid rgba(16,25,35,.14);
  border-radius: 14px;
  padding: 0 15px;
  color: var(--ink);
  background: #fffdf8;
  box-shadow: inset 0 1px 0 rgba(255,255,255,.70);
}
.login-form input:focus {
  border-color: rgba(189,139,51,.68);
  outline: 4px solid rgba(189,139,51,.16);
}
.login-form .login-remember-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #4f5c68;
  font-size: 13px;
  font-weight: 800;
}
.login-form .login-remember-row input {
  width: 18px;
  height: 18px;
  padding: 0;
  accent-color: #17344d;
  box-shadow: none;
}
.login-form button {
  height: 52px;
  border: 0;
  border-radius: 14px;
  color: #fff;
  font-weight: 900;
  cursor: pointer;
  background:
    linear-gradient(135deg, rgba(204,154,55,.30), transparent 52%),
    linear-gradient(135deg, #17344d, #071725);
  box-shadow: 0 14px 28px rgba(16,25,35,.18);
}
.login-form button:hover {
  transform: translateY(-1px);
  filter: saturate(1.08);
}
.login-error {
  margin-bottom: 16px;
  border: 1px solid rgba(185,67,54,.22);
  border-radius: 14px;
  padding: 12px 14px;
  color: #9d2f25;
  background: #fbe5df;
  font-weight: 800;
}
.login-register {
  margin-top: 16px;
  border: 1px solid rgba(16,25,35,.10);
  border-radius: 16px;
  background: rgba(255,253,248,.72);
}
.login-register summary {
  list-style: none;
  padding: 14px 15px;
  color: #17344d;
  cursor: pointer;
  font-weight: 900;
}
.login-register summary::-webkit-details-marker {
  display: none;
}
.login-form-register {
  padding: 0 15px 15px;
}
.login-foot {
  margin-top: 18px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.6;
}

/* UI polish pass: make the app read like a focused research terminal. */
body {
  color: #101923;
  background:
    radial-gradient(circle at 90% -4%, rgba(204, 154, 55, .20), transparent 24%),
    radial-gradient(circle at 0% 4%, rgba(29, 68, 93, .18), transparent 25%),
    repeating-linear-gradient(0deg, transparent 0 35px, rgba(18, 33, 46, .035) 35px 36px),
    linear-gradient(180deg, #f5f1e7 0%, #ece8dc 100%);
}
.app-shell {
  grid-template-columns: 216px minmax(0, 1fr);
}
.sidebar {
  background:
    linear-gradient(180deg, rgba(211, 158, 58, .12), rgba(211, 158, 58, 0) 34%),
    linear-gradient(180deg, #132233 0%, #07111c 100%);
}
.brand-mark {
  gap: 10px;
}
.brand-title {
  font-family: "Avenir Next", "PingFang SC", sans-serif;
  font-weight: 900;
}
.nav-item {
  letter-spacing: -.01em;
}
.nav-item span {
  opacity: .72;
}
.workspace {
  padding: 14px 16px 18px;
}
.module {
  padding: 18px;
  border-radius: 20px;
  background:
    linear-gradient(180deg, rgba(255, 252, 244, .96), rgba(250, 247, 237, .94));
  box-shadow:
    0 22px 52px rgba(17, 28, 39, .10),
    inset 0 1px 0 rgba(255,255,255,.86);
}
.module-header {
  min-height: 34px;
}
.module-title {
  font-family: "Avenir Next Condensed", "Avenir Next", "PingFang SC", sans-serif;
  font-size: 24px;
  font-weight: 900;
}
.module-title::after {
  width: 42px;
  background: linear-gradient(90deg, var(--accent), transparent);
}
.panel {
  border-radius: 16px;
  background:
    linear-gradient(180deg, rgba(255,255,255,.72), rgba(247,244,235,.72));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.74);
}
.workflow-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}
.workflow-card,
.desk-jump {
  border-radius: 13px;
  background:
    linear-gradient(180deg, #fffef9, #f4efe2);
  box-shadow: 0 10px 22px rgba(17,28,39,.06);
}
.workflow-card strong,
.desk-jump strong {
  font-family: "Avenir Next", "PingFang SC", sans-serif;
  letter-spacing: -.01em;
}
.summary-card {
  min-height: 82px;
  background:
    linear-gradient(180deg, #fffef8, #f2ede1);
}
.data-table {
  overflow: hidden;
  border: 1px solid rgba(16,25,35,.09);
  border-radius: 12px;
  background: #fffdf8;
}
.data-table th {
  font-family: var(--mono);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .06em;
  background: #ebe5d8;
}
.data-table td {
  background: rgba(255,253,248,.86);
}
.primary-button,
.app-toolbar button,
.stock-form button,
.portfolio-inline-button.primary,
.workspace-panel-tab.active {
  color: #fff;
  background:
    linear-gradient(135deg, rgba(204,154,55,.28), transparent 52%),
    linear-gradient(135deg, #17344d, #071725);
}
.workspace-panel-tabs {
  padding: 4px;
  border-radius: 14px;
  background: rgba(17,28,39,.06);
}
.workspace-panel-tab {
  border-radius: 11px;
}

.trading-screen {
  background:
    radial-gradient(circle at 12% 0%, rgba(204,154,55,.15), transparent 24%),
    linear-gradient(180deg, #fffdf7, #f2ecdf);
}
.trading-hero {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}
.trading-price-card {
  border: 1px solid rgba(16,25,35,.10);
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #fffef9, #f3edde);
  box-shadow: 0 12px 26px rgba(17,28,39,.07);
}
.trading-price-card span,
.trading-signal-card span {
  display: block;
  color: #6b7884;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: .04em;
}
.trading-price-card strong {
  display: block;
  margin-top: 6px;
  font-size: 28px;
  line-height: 1.05;
  color: #101923;
}
.trading-price-card p,
.trading-signal-card p {
  margin: 8px 0 0;
  color: #63717e;
  font-size: 13px;
  line-height: 1.45;
}
.trading-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.75fr) minmax(320px, .75fr);
  gap: 16px;
}
.trading-chart-panel {
  position: relative;
  min-height: 590px;
  border: 1px solid rgba(16,25,35,.10);
  border-radius: 20px;
  padding: 14px;
  background: #fffdf7;
  overflow: hidden;
}
.trading-chart-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}
.trading-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.trading-tabs span {
  border: 1px solid rgba(16,25,35,.10);
  border-radius: 999px;
  padding: 6px 10px;
  color: #63717e;
  background: #f7f2e7;
  font-size: 12px;
  font-weight: 800;
}
.trading-tabs .active {
  color: #fff;
  background: #17344d;
}
.kline-chart-host {
  height: 500px;
  width: 100%;
  border-radius: 16px;
  background:
    repeating-linear-gradient(0deg, transparent 0 39px, rgba(16,25,35,.05) 39px 40px),
    linear-gradient(180deg, #fbfaf5, #f5efe2);
}
.kline-fallback {
  position: absolute;
  left: 28px;
  bottom: 74px;
  max-width: 520px;
  border: 1px solid rgba(180,133,58,.30);
  border-radius: 12px;
  padding: 9px 11px;
  color: #805d1f;
  background: rgba(255,248,225,.92);
  font-size: 12px;
}
.chart-level-rails {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  margin-top: 10px;
}
.chart-level-rails span {
  border: 1px solid rgba(16,25,35,.10);
  border-radius: 12px;
  padding: 9px 10px;
  color: #17344d;
  background: #f7f2e7;
  font-size: 13px;
  font-weight: 800;
}
.trading-side-panel {
  display: grid;
  gap: 12px;
  align-content: start;
}
.tight-panel {
  padding: 14px;
}
.trading-signal-grid {
  display: grid;
  gap: 10px;
}
.trading-signal-card {
  border: 1px solid rgba(16,25,35,.10);
  border-left: 4px solid var(--accent);
  border-radius: 14px;
  padding: 12px;
  background: #fffdf8;
}
.trading-signal-card strong {
  display: block;
  margin-top: 6px;
  color: #101923;
  line-height: 1.4;
}
@media (max-width: 1280px) {
  .summary-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .trading-hero { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .trading-grid { grid-template-columns: 1fr; }
}
@media (max-width: 1120px) {
  .app-shell { grid-template-columns: 1fr; }
  .summary-grid { grid-template-columns: 1fr; }
  .login-card {
    grid-template-columns: 1fr;
  }
  .login-side {
    min-height: 420px;
  }
}
@media (max-width: 680px) {
  .workspace,
  .workspace-pane,
  .workspace-shell {
    min-width: 0;
    max-width: 100vw;
  }
  .workspace { padding: 12px; overflow: hidden; }
  .module {
    min-width: 0;
    max-width: 100%;
    padding: 12px;
    border-radius: 14px;
    overflow: hidden;
  }
  .sidebar {
    position: relative;
    height: auto;
    width: 100%;
    max-width: 100vw;
    overflow: hidden;
    padding: 16px 12px 12px;
  }
  .brand-mark {
    margin-bottom: 12px;
  }
  .nav-group {
    display: flex;
    gap: 8px;
    margin: 8px -12px 0;
    width: calc(100% + 24px);
    max-width: calc(100% + 24px);
    padding: 0 12px 6px;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
  }
  .nav-item {
    flex: 0 0 136px;
    min-height: 42px;
    scroll-snap-align: start;
  }
  .sidebar-note {
    display: none;
  }
  .workflow-grid {
    grid-template-columns: 1fr;
  }
  .grid-2,
  .grid-3,
  .summary-grid,
  .workflow-grid,
  .compact-note-grid,
  .compact-metric-grid,
  .portfolio-form-grid,
  .ticket-grid,
  .signal-grid,
  .analysis-grid,
  .debate-grid,
  .advice-board,
  .module-subgrid,
  .trading-hero,
  .trading-grid,
  .chart-level-rails {
    grid-template-columns: minmax(0, 1fr) !important;
  }
  .kline-chart-host { height: 420px; }
  .trading-chart-toolbar { align-items: flex-start; flex-direction: column; }
  .panel,
  .summary-card,
  .workflow-card,
  .desk-jump {
    min-width: 0;
  }
  .lead,
  .workflow-card span,
  .desk-jump span,
  .name-cell span,
  .kpi-foot,
  .data-table td {
    overflow-wrap: anywhere;
    word-break: break-word;
  }
  .data-table,
  .candidates-table {
    display: block;
    width: 100%;
    overflow-x: auto;
  }
  .login-page {
    padding: 14px;
  }
  .login-card {
    min-height: 0;
    border-radius: 20px;
  }
  .login-side,
  .login-panel {
    padding: 22px;
  }
  .login-side {
    min-height: 0;
    gap: 28px;
  }
  .login-side h1 {
    font-size: 42px;
  }
  .login-proof-grid {
    grid-template-columns: 1fr;
  }
  .login-proof-grid div {
    min-height: auto;
  }
  .login-panel h2 {
    font-size: 36px;
  }
}
.market-barometer-strip {
  display:grid;
  grid-template-columns:minmax(240px,.85fr) minmax(260px,1fr) minmax(280px,1fr);
  gap:14px;
  align-items:center;
  margin:16px 0;
  border:1px solid rgba(13,59,102,.16);
  border-radius:28px;
  padding:16px;
  background:linear-gradient(135deg, #f7fafb, #eaf2f5);
}
.market-barometer-title span,
.opportunity-funnel-hero .eyebrow,
.stock-verdict-card .eyebrow {
  display:inline-flex;
  color:var(--accent);
  font-family:var(--mono);
  font-size:11px;
  font-weight:900;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.market-barometer-title strong {
  display:block;
  margin-top:8px;
  font-size:18px;
}
.market-barometer-title p,
.market-barometer-facts span {
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.market-barometer-rail {
  display:grid;
  grid-template-columns:repeat(3,1fr);
  overflow:hidden;
  border-radius:999px;
  min-height:42px;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.5);
}
.market-barometer-rail i {
  display:grid;
  place-items:center;
  color:#fff;
  font-style:normal;
  font-weight:900;
}
.market-barometer-rail .defense { background:#159a5b; }
.market-barometer-rail .balance { background:#b7791f; }
.market-barometer-rail .attack { background:#d8342a; }
.market-barometer-facts {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:8px;
}
.market-barometer-facts span {
  border:1px solid var(--line);
  border-radius:14px;
  padding:9px;
  background:#fff;
}
.opportunity-funnel-panel {
  display:grid;
  grid-template-columns:minmax(260px,.8fr) minmax(360px,1fr) minmax(280px,.8fr);
  gap:14px;
  margin:16px 0;
}
.opportunity-funnel-hero,
.stock-verdict-card {
  border:1px solid rgba(13,59,102,.18);
  border-radius:28px;
  padding:18px;
  color:#edf5fb;
  background:linear-gradient(135deg, #102a43, #174565);
}
.opportunity-funnel-hero h3,
.stock-verdict-card h3 {
  margin:10px 0;
  font-family:var(--display);
  font-size:34px;
  letter-spacing:-.04em;
}
.opportunity-funnel-hero p,
.stock-verdict-card p {
  color:rgba(237,245,251,.76);
  line-height:1.65;
}
.opportunity-channel-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
}
.opportunity-channel,
.opportunity-filter-box,
.stock-six-wall,
.stock-bull-bear {
  border:1px solid var(--line);
  border-radius:22px;
  padding:14px;
  background:rgba(255,255,255,.92);
}
.opportunity-channel strong,
.opportunity-channel span {
  display:block;
}
.opportunity-channel span,
.opportunity-filter-box p {
  margin-top:6px;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.opportunity-filter-box ul { margin:8px 0 12px; }
.opportunity-filter-box .primary-button { display:inline-flex; }
.stock-verdict-wall {
  display:grid;
  grid-template-columns:minmax(280px,.75fr) minmax(420px,1.25fr);
  gap:14px;
  margin:16px 0;
}
.stock-six-wall { padding:16px; }
.stock-six-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
}
.stock-dimension-card {
  border:1px solid var(--line);
  border-radius:18px;
  padding:12px;
  background:linear-gradient(180deg,#fff,#f5f9fb);
}
.stock-dimension-card h4 { margin:0 0 8px; }
.stock-dimension-card p {
  margin:6px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
}
.stock-dimension-card b {
  display:inline-flex;
  margin-right:6px;
  color:var(--brand);
}
.stock-bull-bear { grid-column:1 / -1; }
.portfolio-budget-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.portfolio-budget-bar,
.portfolio-budget-note {
  border:1px solid var(--line);
  border-radius:18px;
  padding:13px;
  background:#fff;
}
.portfolio-budget-bar span,
.portfolio-budget-bar strong,
.portfolio-budget-note span,
.portfolio-budget-note strong {
  display:block;
}
.portfolio-budget-bar i {
  display:block;
  height:12px;
  margin:10px 0;
  overflow:hidden;
  border-radius:999px;
  background:#dde6ee;
}
.portfolio-budget-bar i b {
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg, #2b6cb0, #c53030);
}
.portfolio-budget-note p { color:var(--muted); font-size:12px; line-height:1.55; }
.portfolio-lane-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:12px;
}
.portfolio-lane {
  border:1px solid var(--line);
  border-radius:20px;
  padding:12px;
  background:#fff;
}
.portfolio-lane h4 { margin:0 0 10px; }
.portfolio-lane-card {
  display:block;
  border:1px solid var(--line);
  border-radius:16px;
  padding:10px;
  margin-top:8px;
  background:#f8fbfd;
}
.portfolio-lane-card strong,
.portfolio-lane-card span { display:block; }
.portfolio-lane-card span,
.portfolio-lane-card p {
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
}
.portfolio-lane-card.muted { opacity:.74; }
@media (max-width: 1080px) {
  .market-barometer-strip,
  .opportunity-funnel-panel,
  .stock-verdict-wall { grid-template-columns:1fr; }
  .stock-six-grid,
  .portfolio-budget-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .portfolio-lane-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width: 680px) {
  .market-barometer-facts,
  .opportunity-channel-grid,
  .stock-six-grid,
  .portfolio-budget-grid,
  .portfolio-lane-grid { grid-template-columns:1fr; }
}

.opportunity-cards-panel {
  margin:16px 0;
  background:linear-gradient(135deg, rgba(16,42,67,.06), rgba(255,255,255,.94));
}
.opportunity-card-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.opportunity-candidate-card {
  position:relative;
  display:grid;
  gap:9px;
  border:1px solid var(--line);
  border-radius:22px;
  padding:15px;
  background:#fff;
  box-shadow:0 16px 36px rgba(19,39,58,.07);
}
.opportunity-candidate-card p {
  margin:0;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.opportunity-candidate-head {
  display:grid;
  grid-template-columns:1fr auto;
  gap:4px 10px;
  align-items:start;
}
.opportunity-candidate-head span {
  color:var(--muted);
  font-family:var(--mono);
  font-size:11px;
}
.opportunity-candidate-head strong {
  font-size:18px;
}
.opportunity-candidate-head em {
  grid-column:2;
  grid-row:1 / span 2;
  align-self:center;
  border-radius:999px;
  padding:6px 9px;
  color:#fff;
  background:#2b6cb0;
  font-style:normal;
  font-size:11px;
  font-weight:900;
}
.opportunity-candidate-card.只观察 .opportunity-candidate-head em { background:#b7791f; }
.opportunity-candidate-card.待补数据 .opportunity-candidate-head em { background:#718096; }
.portfolio-boundary-panel {
  background:linear-gradient(180deg,#fff,#f7fafb);
}
.stock-verdict-card .metric-list {
  margin-top:12px;
}
.stock-verdict-card .metric-line {
  border-color:rgba(255,255,255,.18);
  background:rgba(255,255,255,.08);
}
.stock-verdict-card .metric-line span,
.stock-verdict-card .metric-line strong {
  color:#edf5fb;
}
@media (max-width: 1080px) {
  .opportunity-card-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width: 680px) {
  .opportunity-card-grid { grid-template-columns:1fr; }
}


/* 简洁模式：保留功能字段，降低装饰感。 */
.simple-panel,
.portfolio-command-hero.simple-panel,
.opportunity-funnel-hero.simple-panel,
.stock-verdict-card.simple-panel,
.market-gate-card {
  color:var(--ink);
  background:#fff;
  border:1px solid var(--line);
  box-shadow:none;
}
.portfolio-command-hero.simple-panel h3,
.opportunity-funnel-hero.simple-panel h3,
.stock-verdict-card.simple-panel h3,
.market-gate-card h3 {
  font-family:var(--body);
  font-size:22px;
  letter-spacing:0;
}
.portfolio-command-hero.simple-panel p,
.opportunity-funnel-hero.simple-panel p,
.stock-verdict-card.simple-panel p,
.market-gate-card p {
  color:var(--muted);
}
.portfolio-command-meta {
  position:static;
  margin-top:14px;
  border-top:1px solid var(--line);
}
.portfolio-command-meta span,
.portfolio-command-meta strong,
.stock-verdict-card .metric-line span,
.stock-verdict-card .metric-line strong {
  color:var(--ink);
}
.stock-verdict-card .metric-line {
  border-color:var(--line);
  background:#f8fbfd;
}
.market-heat-dial {
  display:none;
}
.market-gate-copy {
  max-width:none;
}
.market-gate-footer {
  position:static;
  margin-top:12px;
}
.opportunity-candidate-card {
  box-shadow:none;
}
.opportunity-focus-grid {
  display:grid;
  grid-template-columns:1fr;
  gap:16px;
}
.opportunity-table-scroll {
  overflow-x:auto;
  padding-bottom:2px;
}
.opportunity-dimension-table {
  min-width:960px;
  table-layout:fixed;
}
.opportunity-dimension-table th:nth-child(1),
.opportunity-dimension-table td:nth-child(1) { width:12%; }
.opportunity-dimension-table th:nth-child(2),
.opportunity-dimension-table td:nth-child(2) { width:28%; }
.opportunity-dimension-table th:nth-child(3),
.opportunity-dimension-table td:nth-child(3) { width:17%; }
.opportunity-dimension-table th:nth-child(4),
.opportunity-dimension-table td:nth-child(4) { width:27%; }
.opportunity-dimension-table th:nth-child(5),
.opportunity-dimension-table td:nth-child(5) { width:16%; }
.opportunity-focus-panel .data-table td {
  vertical-align:top;
  line-height:1.42;
  padding-top:10px;
  padding-bottom:10px;
}
.opportunity-focus-panel .name-cell strong {
  font-size:15px;
}
.opportunity-focus-panel .name-cell span {
  margin-top:3px;
}



.market-distribution-panel,
.market-strength-panel,
.market-analysis-panel {
  margin-top:16px;
}
.market-distribution-bars {
  display:grid;
  gap:10px;
  margin-top:12px;
}
.market-distribution-row {
  display:grid;
  grid-template-columns:72px minmax(0,1fr) 54px;
  gap:10px;
  align-items:center;
  color:var(--ink);
  font-size:13px;
}
.market-distribution-row i {
  display:block;
  height:12px;
  overflow:hidden;
  border-radius:999px;
  background:#e6edf2;
}
.market-distribution-row i b {
  display:block;
  height:100%;
  border-radius:999px;
  background:linear-gradient(90deg,#159a5b,#c27a18,#d8342a);
}
.market-sector-heatmap-panel {
  margin-top:16px;
  background:#111927;
  color:#e8edf5;
  border-color:#263247;
}
.market-sector-heatmap-panel h3 {
  display:flex;
  flex-wrap:wrap;
  gap:10px;
  align-items:baseline;
  color:#f3f6fb;
}
.market-sector-heatmap-panel h3 span {
  color:#8793a8;
  font-size:13px;
  font-family:var(--body);
}
.market-sector-heatmap-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:12px;
}
.market-sector-heat-card {
  border:1px solid #293448;
  border-radius:14px;
  background:#0d1420;
  padding:12px;
  color:#e8edf5;
  text-align:left;
}
.market-sector-heat-head {
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:center;
  margin-bottom:12px;
}
.market-sector-heat-head strong {
  font-size:15px;
}
.market-sector-heat-head span {
  color:#768398;
  font-size:12px;
  font-weight:700;
}
.market-sector-heat-head em {
  color:#ff746c;
  font-style:normal;
  font-weight:900;
  font-family:var(--mono);
}
.market-sector-heat-card.down .market-sector-heat-head em {
  color:#37d295;
}
.market-sector-heat-cells {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:4px;
}
.market-sector-heat-cell {
  border-radius:6px;
  padding:9px 6px;
  text-align:center;
  background:#183a34;
}
.market-sector-heat-cell.up {
  background:#893331;
}
.market-sector-heat-cell.down {
  background:#123e35;
}
.market-sector-heat-cell.flat {
  background:#263348;
}
.market-sector-heat-cell small,
.market-sector-heat-cell strong {
  display:block;
}
.market-sector-heat-cell small {
  color:#d7dde8;
  font-size:11px;
  font-weight:800;
}
.market-sector-heat-cell strong {
  margin-top:3px;
  color:#f5f7fb;
  font-family:var(--mono);
  font-size:13px;
}
.market-sector-duo {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:16px;
}
.market-analysis-panel p {
  margin:0;
  color:var(--ink);
  font-size:15px;
  line-height:1.7;
}
@media (max-width:980px) {
  .market-sector-duo { grid-template-columns:1fr; }
  .market-sector-heatmap-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width:640px) {
  .market-sector-heatmap-grid { grid-template-columns:1fr; }
}

.market-event-card-list {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
  margin-top:14px;
}
.market-event-card {
  border:1px solid var(--line);
  border-radius:14px;
  background:#fffdfa;
  padding:10px 12px;
}
.market-event-head {
  display:flex;
  flex-wrap:wrap;
  align-items:center;
  gap:6px 8px;
  margin-bottom:6px;
}
.market-event-time { border:1px solid var(--line); background:#fff; color:var(--muted); border-radius:999px; padding:5px 9px; font-size:12px; font-weight:800; white-space:nowrap; }
.market-event-theme {
  border:1px solid #dccba9;
  background:#f8f0df;
  color:#765622;
  border-radius:999px;
  padding:5px 9px;
  font-size:12px;
  font-weight:900;
  white-space:nowrap;
}
.market-event-stocks {
  color:var(--ink);
  font-weight:800;
  line-height:1.35;
  font-size:13px;
  display:-webkit-box;
  -webkit-line-clamp:1;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
.market-event-reason {
  margin:0;
  color:var(--ink-soft);
  font-size:12px;
  line-height:1.45;
  overflow-wrap:anywhere;
  display:-webkit-box;
  -webkit-line-clamp:2;
  -webkit-box-orient:vertical;
  overflow:hidden;
}
@media (max-width:980px) {
  .market-event-card-list { grid-template-columns:1fr; }
}

.stock-data-audit-panel {
  margin:16px 0;
}
.stock-data-block-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
}
.stock-data-block {
  border:1px solid var(--line);
  border-radius:16px;
  padding:12px;
  background:#fff;
}
.stock-data-block.missing {
  border-color:#efb9b2;
  background:#fff8f6;
}
.stock-data-block span,
.stock-data-block strong,
.stock-data-block em {
  display:block;
}
.stock-data-block span {
  color:var(--muted);
  font-size:12px;
}
.stock-data-block strong {
  margin-top:6px;
}
.stock-data-block p,
.stock-data-block em {
  margin:7px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
  font-style:normal;
}
.stock-pro-brief,
.stock-diagnosis-panel,
.stock-final-summary {
  margin:16px 0;
}
.stock-pro-head {
  display:grid;
  grid-template-columns:minmax(0,1fr) minmax(220px,.32fr);
  gap:16px;
  align-items:stretch;
}
.stock-pro-head h3,
.stock-diagnosis-panel h3,
.stock-final-summary h3 {
  margin:4px 0 6px;
}
.stock-pro-head p {
  margin:0;
  color:var(--muted);
  line-height:1.6;
}
.stock-pro-verdict {
  border:1px solid rgba(13,59,102,.14);
  border-radius:20px;
  padding:14px;
  background:#f8fbfd;
}
.stock-pro-verdict span,
.stock-pro-verdict strong,
.stock-pro-verdict em,
.stock-pro-grid span,
.stock-pro-grid strong,
.stock-pro-bear strong,
.stock-pro-bear span,
.stock-summary-lines span,
.stock-summary-lines strong {
  display:block;
}
.stock-pro-verdict span,
.stock-pro-grid span,
.stock-summary-lines span {
  color:var(--muted);
  font-size:12px;
}
.stock-pro-verdict strong {
  margin-top:6px;
  font-size:22px;
}
.stock-pro-verdict em {
  margin-top:8px;
  color:var(--muted);
  font-style:normal;
  font-size:12px;
}
.stock-pro-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:10px;
  margin-top:14px;
}
.stock-pro-grid div,
.stock-pro-bear,
.stock-diagnosis-card,
.stock-summary-lines div {
  border:1px solid var(--line);
  border-radius:18px;
  padding:12px;
  background:#fff;
}
.stock-pro-grid strong {
  margin-top:6px;
  font-size:13px;
  line-height:1.45;
}
.stock-pro-bear {
  display:grid;
  grid-template-columns:.55fr 1fr 1fr 1fr;
  gap:10px;
  align-items:center;
  margin-top:12px;
  background:#fbf7f2;
}
.stock-pro-bear span {
  color:var(--muted);
  font-size:12px;
  line-height:1.45;
}
.stock-diagnosis-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.stock-diagnosis-card {
  background:linear-gradient(180deg,#fff,#f7fafb);
}
.stock-diagnosis-card div {
  display:flex;
  justify-content:space-between;
  gap:10px;
  align-items:baseline;
}
.stock-diagnosis-card h4 {
  margin:0;
  font-size:17px;
}
.stock-diagnosis-card div span {
  color:var(--muted);
  font-size:12px;
  white-space:nowrap;
}
.stock-diagnosis-card > strong {
  display:block;
  margin-top:10px;
  line-height:1.45;
}
.stock-diagnosis-card p {
  margin:8px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.5;
}
.stock-diagnosis-card b {
  margin-right:6px;
  color:var(--brand);
}
.stock-summary-lines {
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:10px;
}
.stock-summary-lines div {
  background:#fff;
}
.stock-summary-lines strong {
  margin-top:6px;
  line-height:1.45;
}
.stock-summary-lines p {
  margin:8px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.market-research-workspace,
.stock-research-workspace {
  display:grid;
  gap:18px;
}
.market-state-strip,
.stock-identity-strip {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr)) auto;
  gap:1px;
  overflow:hidden;
  border:1px solid #23364a;
  border-radius:22px;
  background:#23364a;
  box-shadow:0 18px 44px rgba(16,32,51,.14);
}
.market-state-strip > div,
.stock-identity-strip > div {
  min-width:0;
  padding:16px 18px;
  background:linear-gradient(145deg,#142b41,#102033);
  color:#edf5fb;
}
.market-state-strip span,
.stock-identity-strip span,
.market-thesis-board span,
.stock-thesis-board span,
.investment-memo-card > span,
.research-scenario-card > span,
.stock-evidence-card span,
.research-actions > span {
  display:block;
  color:#8ea7ba;
  font-size:11px;
  font-weight:800;
  letter-spacing:.12em;
  text-transform:uppercase;
}
.market-state-strip strong,
.stock-identity-strip strong {
  display:block;
  margin-top:7px;
  font-family:var(--mono);
  font-size:18px;
  line-height:1.2;
}
.market-state-strip .module-refresh-tools,
.stock-identity-strip .module-refresh-tools {
  align-self:center;
  padding:0 12px;
}
.market-thesis-board,
.stock-thesis-board {
  display:grid;
  grid-template-columns:minmax(0,1.35fr) minmax(280px,.65fr);
  gap:1px;
  overflow:hidden;
  border:1px solid #d7c49d;
  border-radius:26px;
  background:#d7c49d;
}
.market-thesis-main,
.market-risk-card,
.stock-thesis-status,
.thesis-conflict {
  padding:22px;
  background:linear-gradient(145deg,#fffdf7,#f4ead6);
}
.market-risk-card,
.thesis-conflict {
  background:linear-gradient(145deg,#192f43,#112337);
  color:#f4f8fb;
}
.market-thesis-board h3,
.stock-thesis-board h3,
.research-actions h3 {
  margin:8px 0 12px;
  max-width:900px;
  font-family:var(--display);
  font-size:clamp(20px,2.3vw,32px);
  line-height:1.18;
}
.market-thesis-board ul {
  margin:10px 0 0;
  padding-left:18px;
  line-height:1.65;
}
.market-risk-card > strong,
.thesis-conflict > strong {
  display:block;
  margin-top:8px;
  font-size:17px;
  line-height:1.45;
}
.market-risk-card small {
  display:block;
  margin-top:12px;
  color:#d7b978;
  line-height:1.55;
}
.market-session-ruler {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:1px;
  overflow:hidden;
  border:1px solid #23364a;
  border-radius:18px;
  background:#23364a;
  box-shadow:0 12px 28px rgba(16,32,51,.10);
}
.market-session-ruler > div {
  position:relative;
  display:grid;
  grid-template-columns:auto 1fr;
  grid-template-rows:auto auto;
  gap:2px 10px;
  align-items:center;
  padding:12px 18px;
  background:#fffdf8;
}
.market-session-ruler > div:not(:last-child)::after {
  content:"";
  position:absolute;
  right:-6px;
  z-index:2;
  width:11px;
  height:11px;
  border-top:1px solid #23364a;
  border-right:1px solid #23364a;
  background:#fffdf8;
  transform:rotate(45deg);
}
.market-session-ruler span {
  grid-row:1 / -1;
  display:grid;
  place-items:center;
  width:32px;
  height:32px;
  border-radius:50%;
  color:#fff;
  background:#10283d;
  font-family:var(--mono);
  font-size:10px;
  font-weight:900;
}
.market-session-ruler strong { color:var(--ink); font-family:var(--display); font-size:14px; }
.market-session-ruler small { color:var(--muted); font-size:10px; }
.market-session-phase {
  display:grid;
  gap:18px;
  min-width:0;
  padding:18px;
  border:1px solid var(--line);
  border-radius:20px;
  background:rgba(255,253,248,.72);
}
.market-session-phase.phase-pre { border-top:3px solid #10283d; }
.market-session-phase.phase-live { border-top:3px solid #bd8b33; }
.market-session-phase.phase-close { border-top:3px solid #247153; }
.market-session-heading {
  display:flex;
  gap:12px;
  align-items:center;
  padding-bottom:12px;
  border-bottom:1px solid var(--line);
}
.market-session-heading > span {
  color:var(--accent);
  font-family:var(--mono);
  font-size:12px;
  font-weight:900;
  letter-spacing:.08em;
}
.market-session-heading h3,
.market-session-heading p { margin:0; }
.market-session-heading h3 { font-family:var(--display); font-size:21px; }
.market-session-heading p { margin-top:3px; color:var(--muted); font-size:11px; }
.market-intraday-ledger {
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:15px;
  background:#fffdf8;
}
.market-intraday-ledger summary {
  cursor:pointer;
  list-style:none;
  padding:14px 16px;
  color:var(--brand);
  font-size:12px;
  font-weight:900;
}
.market-intraday-ledger summary::-webkit-details-marker { display:none; }
.market-intraday-ledger summary::after { content:"＋"; float:right; color:var(--accent); }
.market-intraday-ledger[open] summary::after { content:"－"; }
.market-intraday-ledger-body {
  display:grid;
  gap:14px;
  padding:0 14px 14px;
  border-top:1px solid var(--line);
}
.market-intraday-ledger-body > :first-child { margin-top:14px; }
.market-decision-panel {
  overflow:hidden;
  padding:18px;
  border:1px solid var(--line);
  border-radius:20px;
  background:
    linear-gradient(135deg, rgba(183,133,52,.08), transparent 42%),
    rgba(255,255,255,.82);
}
.market-decision-rail {
  position:relative;
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:16px;
  background:#fff;
}
.market-decision-rail-step {
  position:relative;
  display:grid;
  grid-template-columns:auto 1fr;
  gap:10px;
  min-height:142px;
  padding:16px 20px 16px 15px;
  border-right:1px solid var(--line);
  animation:marketRailReveal .45s ease both;
}
.market-decision-rail-step:nth-child(2) { animation-delay:.04s; }
.market-decision-rail-step:nth-child(3) { animation-delay:.08s; }
.market-decision-rail-step:nth-child(4) { animation-delay:.12s; }
.market-decision-rail-step:nth-child(5) { animation-delay:.16s; }
.market-decision-rail-step:last-child { border-right:0; }
.market-decision-rail-step:not(:last-child)::after {
  content:"";
  position:absolute;
  top:50%;
  right:-6px;
  z-index:2;
  width:11px;
  height:11px;
  border-top:1px solid var(--line-strong);
  border-right:1px solid var(--line-strong);
  background:#fff;
  transform:translateY(-50%) rotate(45deg);
}
.market-decision-rail-step > span {
  display:grid;
  width:24px;
  height:24px;
  place-items:center;
  border-radius:50%;
  color:#fff;
  background:var(--brand);
  font-family:var(--mono);
  font-size:9px;
  font-weight:900;
}
.market-decision-rail-step div { display:grid; align-content:start; gap:7px; }
.market-decision-rail-step small { color:var(--accent); font-family:var(--mono); font-size:9px; font-weight:900; letter-spacing:.06em; }
.market-decision-rail-step strong { color:var(--ink); font-size:13px; line-height:1.45; }
.market-decision-rail-step p { margin:0; color:var(--muted); font-size:11px; line-height:1.5; }
.market-decision-rail-step.downgrade > span { background:var(--red); }
.market-decision-rail-step.paused { background:#f4f5f4; }
.market-decision-rail-step.paused > span { background:var(--line-strong); }
.market-decision-rail-step.paused small,
.market-decision-rail-step.paused strong { color:var(--muted); }
@keyframes marketRailReveal {
  from { opacity:0; transform:translateY(8px); }
  to { opacity:1; transform:translateY(0); }
}
.research-section-heading {
  display:flex;
  gap:12px;
  align-items:flex-start;
  margin:4px 0 12px;
}
.research-section-heading > span {
  display:grid;
  width:34px;
  height:34px;
  place-items:center;
  flex:0 0 auto;
  border-radius:50%;
  background:#b4853a;
  color:#fff;
  font-family:var(--mono);
  font-size:11px;
  font-weight:900;
}
.research-section-heading h3,
.research-section-heading p {
  margin:0;
}
.research-section-heading h3 {
  font-family:var(--display);
  font-size:20px;
}
.research-section-heading p {
  margin-top:4px;
  color:var(--muted);
  font-size:12px;
}
.market-dimension-grid {
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:10px;
  margin-bottom:14px;
}
.market-dimension-card,
.stock-evidence-card,
.investment-memo-card,
.research-scenario-card {
  border:1px solid var(--line);
  border-radius:18px;
  padding:15px;
  background:linear-gradient(180deg,#fff,#f6f9fb);
}
.market-dimension-card > div,
.stock-evidence-card > div {
  display:flex;
  justify-content:space-between;
  gap:8px;
  align-items:center;
}
.market-dimension-card strong,
.stock-evidence-card strong,
.investment-memo-card strong,
.research-scenario-card strong {
  display:block;
  margin-top:10px;
  line-height:1.45;
}
.market-dimension-card p,
.investment-memo-card p,
.research-scenario-card p {
  margin:8px 0 0;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.market-dimension-card small,
.stock-evidence-card small,
.research-scenario-card small {
  display:block;
  margin-top:10px;
  color:var(--muted);
  font-size:11px;
  line-height:1.45;
}
.evidence-status {
  border-radius:999px;
  padding:4px 7px;
  background:#e5edf2;
  color:#405970;
  font-family:var(--mono);
  font-size:9px;
  font-style:normal;
  font-weight:800;
  letter-spacing:.04em;
}
.evidence-status.complete { background:#dfeee9; color:#24624d; }
.evidence-status.degraded,
.evidence-status.stale { background:#f0e4ca; color:#865b16; }
.evidence-status.missing,
.evidence-status.blocked { background:#f5dfdc; color:#8f3f37; }
.research-scenario-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:12px;
}
.research-scenario-card:nth-child(1) { border-top:3px solid #2c8061; }
.research-scenario-card:nth-child(2) { border-top:3px solid #b4853a; }
.research-scenario-card:nth-child(3) { border-top:3px solid #b4483d; }
.stock-thesis-status {
  display:grid;
  align-content:center;
}
.stock-thesis-status > strong {
  color:#8b682f;
  font-family:var(--mono);
}
.thesis-evidence-pair {
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:10px;
  margin-top:14px;
}
.thesis-evidence-pair p {
  margin:0;
  border:1px solid rgba(255,255,255,.1);
  border-radius:14px;
  padding:12px;
  color:#dbe6ee;
  font-size:12px;
  line-height:1.55;
}
.thesis-evidence-pair b {
  display:block;
  margin-bottom:5px;
  color:#d7b978;
}
.investment-memo-grid {
  display:grid;
  grid-template-columns:repeat(4,minmax(0,1fr));
  gap:12px;
}
.investment-memo-card ul {
  margin:9px 0 0;
  padding-left:17px;
  color:var(--muted);
  font-size:12px;
  line-height:1.55;
}
.investment-memo-card .memo-next-checks {
  border-top:1px dashed var(--line);
  padding-top:8px;
  color:var(--brand);
}
.stock-evidence-grid {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
  margin-bottom:14px;
}
.research-actions {
  border-left:4px solid #b4853a;
  border-radius:0 18px 18px 0;
  padding:17px 20px;
  background:#f4ead6;
}
.research-actions h3 {
  margin-bottom:0;
  font-size:20px;
}
.trade-plan-section {
  display:grid;
  gap:10px;
}
.evidence-audit,
.agent-debate {
  border:1px solid var(--line);
  border-radius:18px;
  overflow:hidden;
  background:#fff;
}
.evidence-audit summary,
.agent-debate summary {
  cursor:pointer;
  padding:14px 16px;
  color:var(--ink-soft);
  font-weight:800;
}
.evidence-audit[open] summary,
.agent-debate[open] summary { border-bottom:1px solid var(--line); }
.evidence-audit .data-table { margin:12px; width:calc(100% - 24px); }
.stock-dossier { display:grid; gap:18px; }
.dossier-decision-brief {
  display:grid;
  grid-template-columns:minmax(210px,.34fr) minmax(0,1fr);
  overflow:hidden;
  border:1px solid #244762;
  border-radius:20px;
  color:#edf5fa;
  background:
    linear-gradient(110deg, rgba(180,133,58,.18), transparent 42%),
    linear-gradient(145deg, #10283d, #173a55);
  box-shadow:var(--shadow);
}
.dossier-stance {
  display:grid;
  align-content:center;
  gap:8px;
  padding:24px;
  border-right:1px solid rgba(255,255,255,.12);
}
.dossier-stance span,
.dossier-grade span,
.dossier-evidence-pair span,
.dossier-heading > span,
.dossier-section-title > span,
.dossier-position-grid span {
  color:#d7b978;
  font-family:var(--mono);
  font-size:11px;
  font-weight:800;
  letter-spacing:.09em;
  text-transform:uppercase;
}
.dossier-stance h3 {
  margin:0;
  font-family:var(--display);
  font-size:clamp(30px,4vw,48px);
  line-height:1;
}
.dossier-stance > strong { color:#f1d89f; font-size:14px; }
.dossier-thesis { display:grid; gap:13px; padding:24px; }
.dossier-thesis > p { margin:0; font-size:17px; font-weight:760; line-height:1.65; }
.dossier-thesis > small { color:#b9cad6; line-height:1.55; }
.dossier-grade { display:flex; align-items:center; justify-content:space-between; gap:16px; }
.dossier-grade strong { font-family:var(--mono); font-size:14px; }
.dossier-core-conflict {
  display:grid;
  grid-template-columns:auto minmax(0,1fr);
  gap:10px;
  align-items:start;
  padding:12px 0;
  border-top:1px solid rgba(255,255,255,.12);
  border-bottom:1px solid rgba(255,255,255,.12);
}
.dossier-core-conflict span,
.dossier-research-meta span {
  color:#d7b978;
  font-family:var(--mono);
  font-size:10px;
  font-weight:850;
  letter-spacing:.08em;
}
.dossier-core-conflict strong { color:#fff; font-size:14px; line-height:1.55; }
.dossier-research-meta { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.dossier-research-meta > div {
  display:grid;
  gap:6px;
  padding:10px;
  border:1px solid rgba(255,255,255,.10);
  border-radius:11px;
  background:rgba(255,255,255,.035);
}
.dossier-research-meta strong { color:#dce8f1; font-size:12px; line-height:1.5; }
.dossier-evidence-pair { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.dossier-evidence-pair > div {
  display:grid;
  gap:6px;
  padding:12px;
  border:1px solid rgba(255,255,255,.12);
  border-radius:13px;
  background:rgba(255,255,255,.04);
}
.dossier-evidence-pair strong { font-size:13px; line-height:1.55; }
.dossier-price,
.decision-rail-step strong,
.dossier-position-grid strong { font-variant-numeric: tabular-nums; }
.stock-dossier-grid,
.dossier-action-grid {
  display:grid;
  grid-template-columns:minmax(0,1.25fr) minmax(300px,.75fr);
  gap:16px;
  align-items:start;
}
.dossier-panel,
.dossier-position-panel {
  border:1px solid var(--line);
  border-radius:18px;
  padding:18px;
  background:rgba(255,255,255,.82);
  box-shadow:0 14px 34px rgba(19,39,58,.06);
}
.dossier-heading { display:flex; justify-content:space-between; gap:14px; align-items:baseline; margin-bottom:8px; }
.dossier-heading h3,
.dossier-section-title h3 { margin:0; font-family:var(--display); color:var(--ink); }
.decision-rail { position:relative; display:grid; }
.decision-rail::before {
  content:"";
  position:absolute;
  top:20px;
  bottom:20px;
  left:104px;
  width:1px;
  background:linear-gradient(var(--accent), var(--line-strong), var(--red));
}
.decision-rail-step {
  position:relative;
  display:grid;
  grid-template-columns:92px minmax(0,1fr);
  gap:24px;
  padding:14px 0;
  border-bottom:1px solid var(--line);
  animation:dossierRailReveal .46s ease both;
}
.decision-rail-step:last-child { border-bottom:0; }
.decision-rail-step::before {
  content:"";
  position:absolute;
  top:20px;
  left:100px;
  width:9px;
  height:9px;
  border:2px solid #fff;
  border-radius:50%;
  background:var(--accent);
  box-shadow:0 0 0 1px var(--line-strong);
}
.decision-rail-step.downgrade::before,
.decision-rail-step.invalid::before { background:var(--red); }
.decision-rail-step > span { color:var(--muted); font-size:12px; font-weight:800; }
.decision-rail-step div { display:grid; gap:5px; }
.decision-rail-step strong { color:var(--ink); line-height:1.45; }
.decision-rail-step p { margin:0; color:var(--muted); font-size:12px; }
.risk-register { display:grid; gap:10px; }
.risk-register-item {
  display:grid;
  gap:7px;
  padding:13px;
  border:1px solid var(--line);
  border-left:4px solid var(--amber);
  border-radius:13px;
  background:#fff;
}
.risk-register-item.severity-critical,
.risk-register-item.severity-high { border-left-color:var(--red); background:#fff9f8; }
.risk-register-item > div { display:flex; justify-content:space-between; gap:10px; }
.risk-register-item span { color:var(--red); font-family:var(--mono); font-size:10px; font-weight:900; }
.risk-register-item p { margin:0; color:var(--ink); font-size:13px; line-height:1.5; }
.risk-register-item small { color:var(--muted); line-height:1.45; }
.dossier-empty-state { padding:14px; border:1px dashed var(--line); border-radius:12px; color:var(--muted); }
.dossier-position-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; }
.dossier-position-grid > div { display:grid; gap:7px; padding:12px; border:1px solid var(--line); border-radius:12px; background:#fff; }
.dossier-position-grid strong { color:var(--ink); font-size:13px; line-height:1.5; }
.dossier-position-grid .prohibited { grid-column:1/-1; border-color:rgba(180,72,61,.34); background:#fff7f5; }
.dossier-position-grid .prohibited span { color:var(--red); }
.dossier-section-title { display:grid; grid-template-columns:auto 1fr; gap:6px 14px; align-items:baseline; margin:4px 0 12px; }
.dossier-section-title p { grid-column:2; margin:0; color:var(--muted); font-size:12px; }
.dossier-diagnostic-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.dossier-diagnostic-card { display:grid; gap:10px; padding:16px; border:1px solid var(--line); border-top:3px solid var(--line-strong); border-radius:16px; background:#fff; }
.dossier-diagnostic-card.status-blocked { border-top-color:var(--red); }
.dossier-diagnostic-card.status-degraded { border-top-color:var(--amber); }
.dossier-diagnostic-card.status-complete { border-top-color:#2c8061; }
.dossier-diagnostic-card > div { display:flex; justify-content:space-between; gap:10px; }
.dossier-diagnostic-card h4 { margin:0; color:var(--ink); }
.dossier-diagnostic-card > div span { color:var(--muted); font-family:var(--mono); font-size:10px; text-transform:uppercase; }
.dossier-diagnostic-card > strong { color:var(--ink); line-height:1.55; }
.diagnostic-facts,
.diagnostic-risks { margin:0; padding-left:17px; color:var(--muted); font-size:12px; line-height:1.55; }
.diagnostic-risks { color:var(--red); }
.dossier-diagnostic-card small { color:var(--muted); border-top:1px dashed var(--line); padding-top:9px; line-height:1.5; }
.dossier-scenario-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.dossier-scenario-card { display:grid; gap:9px; padding:16px; border:1px solid var(--line); border-radius:16px; background:#fff; }
.dossier-scenario-card:nth-child(1) { border-top:3px solid #2c8061; }
.dossier-scenario-card:nth-child(2) { border-top:3px solid var(--accent); }
.dossier-scenario-card:nth-child(3) { border-top:3px solid var(--red); }
.dossier-scenario-card span { color:var(--brand); font-family:var(--mono); font-size:11px; font-weight:900; }
.dossier-scenario-card strong,
.dossier-scenario-card p { margin:0; color:var(--ink); font-size:13px; line-height:1.55; }
.dossier-scenario-card p b { display:inline-block; min-width:38px; color:var(--muted); }
.dossier-scenario-card small { color:var(--muted); }
.dossier-thesis-spine,
.weighted-evidence {
  padding:18px;
  border:1px solid var(--line);
  border-radius:18px;
  background:rgba(255,255,255,.82);
  box-shadow:0 14px 34px rgba(19,39,58,.06);
}
.dossier-thesis-spine > h3,
.weighted-evidence > h3 { margin:0 0 12px; font-family:var(--display); color:var(--ink); }
.thesis-spine {
  position:relative;
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:14px;
}
.thesis-spine::before {
  content:"";
  position:absolute;
  top:21px;
  left:12%;
  right:12%;
  height:2px;
  background:linear-gradient(90deg, var(--line-strong), var(--accent), var(--brand));
}
.thesis-spine-step {
  position:relative;
  z-index:1;
  display:grid;
  gap:10px;
  min-width:0;
  padding:14px;
  border:1px solid var(--line);
  border-radius:14px;
  background:#fff;
}
.thesis-spine-step > span {
  justify-self:start;
  padding:4px 8px;
  border:1px solid var(--line);
  border-radius:999px;
  color:var(--brand);
  background:var(--panel);
  font-family:var(--mono);
  font-size:10px;
  font-weight:900;
}
.thesis-spine-step > strong { color:var(--ink); font-size:13px; line-height:1.6; }
.weighted-evidence-list {
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:14px;
  background:#fff;
}
.weighted-evidence-row {
  display:grid;
  grid-template-columns:minmax(150px,.34fr) minmax(0,1fr);
  border-bottom:1px solid var(--line);
  box-shadow:inset 4px 0 0 var(--line-strong);
}
.weighted-evidence-row:last-child { border-bottom:0; }
.weighted-evidence-row > header {
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  gap:6px 8px;
  align-content:start;
  padding:14px;
  background:var(--panel);
}
.weighted-evidence-row > header span { color:var(--ink); font-weight:850; }
.weighted-evidence-row > header em {
  color:var(--muted);
  font-family:var(--mono);
  font-size:10px;
  font-style:normal;
}
.weighted-evidence-row > header strong {
  grid-column:1/-1;
  justify-self:start;
  padding:4px 8px;
  border-radius:999px;
  color:var(--ink-soft);
  background:var(--panel-strong);
  font-size:11px;
}
.weighted-evidence-row > div { display:grid; gap:7px; padding:14px 16px; }
.weighted-evidence-row p,
.weighted-evidence-row small { margin:0; color:var(--ink-soft); font-size:12px; line-height:1.55; }
.weighted-evidence-row p b,
.weighted-evidence-row small b { margin-right:8px; color:var(--muted); font-family:var(--mono); font-size:10px; }
.weighted-evidence-row small { color:var(--muted); }
.weighted-evidence-row[data-direction="支持"] { box-shadow:inset 4px 0 0 #2c8061; }
.weighted-evidence-row[data-direction="支持"] > header strong { color:#1f674e; background:#e5f2ed; }
.weighted-evidence-row[data-direction="反证"] { box-shadow:inset 4px 0 0 var(--red); }
.weighted-evidence-row[data-direction="反证"] > header strong { color:#94372f; background:#f8e7e4; }
.weighted-evidence-row[data-direction="未知"] { box-shadow:inset 4px 0 0 #8798a6; }
.weighted-evidence-row[data-direction="未知"] > header strong { color:#536879; background:#e8eef2; }
.dossier-evidence-ledger,
.dossier-supporting-evidence { border:1px solid var(--line); border-radius:16px; overflow:hidden; background:#fff; }
.dossier-evidence-ledger summary,
.dossier-supporting-evidence summary { cursor:pointer; padding:14px 16px; color:var(--ink-soft); font-weight:800; }
@keyframes dossierRailReveal {
  from { opacity:0; transform:translateY(8px); }
  to { opacity:1; transform:translateY(0); }
}
@media (max-width: 760px) {
  .dossier-decision-brief,
  .stock-dossier-grid,
  .dossier-action-grid,
  .dossier-diagnostic-grid,
  .dossier-scenario-grid,
  .dossier-research-meta,
  .thesis-spine,
  .weighted-evidence-row { grid-template-columns:1fr; }
  .dossier-stance { border-right:0; border-bottom:1px solid rgba(255,255,255,.12); }
  .dossier-position-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .dossier-evidence-pair { grid-template-columns:1fr; }
  .thesis-spine::before {
    top:28px;
    bottom:28px;
    left:27px;
    right:auto;
    width:2px;
    height:auto;
    background:linear-gradient(var(--line-strong), var(--accent), var(--brand));
  }
  .thesis-spine-step { padding-left:16px; }
  .weighted-evidence-row > header { grid-template-columns:minmax(0,1fr) auto auto; }
  .weighted-evidence-row > header strong { grid-column:auto; }
  .decision-rail::before { left:86px; }
  .decision-rail-step { grid-template-columns:74px minmax(0,1fr); }
  .decision-rail-step::before { left:82px; }
}
@media (max-width: 480px) {
  .dossier-position-grid { grid-template-columns:1fr; }
  .dossier-stance,
  .dossier-thesis,
  .dossier-panel,
  .dossier-position-panel { padding:15px; }
}
@media (prefers-reduced-motion: reduce) {
  .decision-rail-step { animation:none; }
}
.opportunity-dossier { display:grid; gap:18px; }
.opportunity-gate-brief {
  display:grid;
  grid-template-columns:minmax(220px,.34fr) minmax(0,1fr);
  overflow:hidden;
  border:1px solid #244762;
  border-radius:20px;
  color:#edf5fa;
  background:
    linear-gradient(110deg, rgba(189,139,51,.20), transparent 42%),
    linear-gradient(145deg, #10283d, #173a55);
  box-shadow:var(--shadow);
}
.opportunity-gate-state {
  display:grid;
  align-content:center;
  gap:8px;
  padding:24px;
  border-right:1px solid rgba(255,255,255,.12);
}
.opportunity-gate-state span,
.opportunity-gate-metrics span,
.candidate-evidence-pair span {
  color:#d7b978;
  font-family:var(--mono);
  font-size:10px;
  font-weight:850;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.opportunity-gate-state h3 {
  margin:0;
  font-family:var(--display);
  font-size:clamp(30px,4vw,48px);
  line-height:1;
}
.opportunity-gate-state > strong { color:#f1d89f; line-height:1.45; }
.opportunity-gate-thesis { display:grid; gap:14px; padding:24px; }
.opportunity-gate-thesis > p { margin:0; font-size:17px; font-weight:760; line-height:1.6; }
.opportunity-gate-thesis > small { color:#b9cad6; line-height:1.5; }
.opportunity-gate-metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:9px; }
.opportunity-gate-metrics > div {
  display:grid;
  gap:6px;
  padding:11px;
  border:1px solid rgba(255,255,255,.12);
  border-radius:12px;
  background:rgba(255,255,255,.04);
}
.opportunity-gate-metrics strong { font-family:var(--mono); font-size:15px; }
.opportunity-funnel-rail {
  display:grid;
  grid-template-columns:repeat(5,minmax(0,1fr));
  gap:0;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:16px;
  background:rgba(255,255,255,.78);
}
.opportunity-funnel-step {
  position:relative;
  display:grid;
  gap:5px;
  min-height:112px;
  padding:15px 22px 15px 15px;
  border-right:1px solid var(--line);
  animation:dossierRailReveal .46s ease both;
}
.opportunity-funnel-step:last-child { border-right:0; }
.opportunity-funnel-step:not(:last-child)::after {
  content:"";
  position:absolute;
  top:50%;
  right:-6px;
  z-index:2;
  width:11px;
  height:11px;
  border-top:1px solid var(--line-strong);
  border-right:1px solid var(--line-strong);
  background:#fff;
  transform:translateY(-50%) rotate(45deg);
}
.opportunity-funnel-step span { color:var(--muted); font-size:11px; font-weight:800; }
.opportunity-funnel-step strong { font-family:var(--mono); font-size:26px; color:var(--ink); }
.opportunity-funnel-step p { margin:0; color:var(--muted); font-size:11px; line-height:1.45; }
.opportunity-funnel-step.stage-excluded strong { color:var(--red); }
.opportunity-funnel-step.stage-eligible strong { color:#247153; }
.opportunity-research-grid {
  display:grid;
  grid-template-columns:minmax(0,1.45fr) minmax(280px,.55fr);
  gap:16px;
  align-items:start;
}
.candidate-decision-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.candidate-decision-card {
  display:grid;
  gap:11px;
  padding:16px;
  border:1px solid var(--line);
  border-top:3px solid var(--accent);
  border-radius:16px;
  background:#fff;
}
.candidate-decision-card.state-eligible { border-top-color:#2c8061; }
.candidate-decision-card.state-excluded { border-top-color:var(--red); background:#fff9f8; }
.candidate-decision-card.state-blocked { border-top-color:var(--line-strong); background:#f4f5f4; }
.candidate-decision-card header { display:flex; justify-content:space-between; gap:12px; }
.candidate-decision-card header div { display:grid; gap:3px; }
.candidate-decision-card header span { color:var(--muted); font-family:var(--mono); font-size:10px; }
.candidate-decision-card header strong { color:var(--ink); font-size:17px; }
.candidate-decision-card header em {
  align-self:start;
  padding:4px 8px;
  border-radius:999px;
  color:var(--brand);
  background:var(--accent-soft);
  font-size:10px;
  font-style:normal;
  font-weight:850;
}
.candidate-strategy,
.candidate-next-step,
.candidate-exclusion { margin:0; color:var(--ink-soft); font-size:12px; line-height:1.5; }
.candidate-exclusion { color:var(--red); }
.candidate-decision-card > small { color:var(--muted); font-family:var(--mono); font-size:10px; }
.candidate-evidence-pair { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.candidate-evidence-pair > div { padding:10px; border:1px solid var(--line); border-radius:11px; background:#faf9f5; }
.candidate-evidence-pair ul { margin:7px 0 0; padding-left:16px; color:var(--muted); font-size:11px; line-height:1.5; }
.opportunity-risk-register {
  display:grid;
  gap:10px;
  padding:17px;
  border:1px solid var(--line);
  border-radius:17px;
  background:rgba(255,255,255,.78);
}
.opportunity-risk-item { display:grid; gap:7px; padding:12px; border-left:4px solid var(--amber); border-radius:11px; background:#fff; }
.opportunity-risk-item.severity-critical,
.opportunity-risk-item.severity-high { border-left-color:var(--red); }
.opportunity-risk-item > div { display:flex; justify-content:space-between; gap:8px; }
.opportunity-risk-item span { color:var(--red); font-family:var(--mono); font-size:9px; font-weight:900; }
.opportunity-risk-item p { margin:0; color:var(--ink); font-size:12px; line-height:1.45; }
.opportunity-risk-item small { color:var(--muted); line-height:1.4; }
.opportunity-source-ledger { overflow:hidden; border:1px solid var(--line); border-radius:15px; background:#fff; }
.opportunity-source-ledger summary { cursor:pointer; padding:14px 16px; color:var(--ink-soft); font-weight:800; }
.opportunity-source-ledger ul { margin:0; padding:0 32px 16px; color:var(--muted); font-size:12px; line-height:1.55; }
.research-overflow {
  width:100%;
  margin-top:12px;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:14px;
  background:rgba(255,253,248,.72);
}
.research-overflow summary {
  cursor:pointer;
  list-style:none;
  padding:13px 15px;
  color:var(--brand);
  font-size:12px;
  font-weight:900;
}
.research-overflow summary::-webkit-details-marker { display:none; }
.research-overflow summary::after { content:"＋"; float:right; color:var(--accent); }
.research-overflow[open] summary::after { content:"－"; }
.research-overflow > div { padding:0 12px 12px; }
.candidate-overflow,
.portfolio-queue-overflow,
.portfolio-boundary-overflow { width:100%; }
@media (min-width: 921px) {
  .opportunity-risk-register { position:sticky; top:92px; }
}
@media (max-width: 920px) {
  .opportunity-research-grid { grid-template-columns:1fr; }
  .opportunity-funnel-rail { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .opportunity-funnel-step { border-bottom:1px solid var(--line); }
}
@media (max-width: 760px) {
  .opportunity-gate-brief,
  .candidate-decision-grid,
  .candidate-evidence-pair,
  .opportunity-gate-metrics,
  .opportunity-funnel-rail { grid-template-columns:1fr; }
  .opportunity-gate-state { border-right:0; border-bottom:1px solid rgba(255,255,255,.12); }
  .opportunity-funnel-step { min-height:0; border-right:0; }
  .opportunity-funnel-step:not(:last-child)::after { display:none; }
}
@media (max-width: 680px) {
  .research-overflow { border-radius:12px; }
  .research-overflow > div { padding:0 8px 8px; }
}
@media (prefers-reduced-motion: reduce) {
  .opportunity-funnel-step { animation:none; }
}
.portfolio-dossier { display:grid; gap:18px; margin-top:16px; }
.portfolio-verdict-brief {
  display:grid;
  grid-template-columns:minmax(230px,.34fr) minmax(0,1fr);
  overflow:hidden;
  border:1px solid #244762;
  border-radius:20px;
  color:#edf5fa;
  background:
    linear-gradient(118deg, rgba(186,132,43,.22), transparent 45%),
    linear-gradient(145deg, #10283d, #173a55);
  box-shadow:var(--shadow);
}
.portfolio-verdict-state { display:grid; align-content:center; gap:8px; padding:24px; border-right:1px solid rgba(255,255,255,.12); }
.portfolio-verdict-state span,
.portfolio-verdict-metrics span,
.portfolio-queue-reason span,
.portfolio-trigger-pair span,
.portfolio-prohibited span {
  color:#d7b978;
  font-family:var(--mono);
  font-size:10px;
  font-weight:850;
  letter-spacing:.08em;
  text-transform:uppercase;
}
.portfolio-verdict-state h3 { margin:0; font-family:var(--display); font-size:clamp(30px,4vw,48px); line-height:1; }
.portfolio-verdict-state > strong { color:#f1d89f; line-height:1.45; }
.portfolio-verdict-thesis { display:grid; gap:14px; padding:24px; }
.portfolio-verdict-thesis > p { margin:0; font-size:17px; font-weight:760; line-height:1.6; }
.portfolio-verdict-thesis > small { color:#b9cad6; line-height:1.5; }
.portfolio-verdict-metrics { display:grid; grid-template-columns:.55fr .55fr 1.5fr; gap:9px; }
.portfolio-verdict-metrics > div { display:grid; gap:6px; padding:11px; border:1px solid rgba(255,255,255,.12); border-radius:12px; background:rgba(255,255,255,.04); }
.portfolio-verdict-metrics strong { font-size:13px; line-height:1.45; }
.portfolio-metric-strip { display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:9px; }
.portfolio-metric { display:grid; gap:5px; padding:14px; border:1px solid var(--line); border-top:3px solid var(--line-strong); border-radius:13px; background:#fff; }
.portfolio-metric.status-critical,
.portfolio-metric.status-risk { border-top-color:var(--red); }
.portfolio-metric.status-watch { border-top-color:var(--amber); }
.portfolio-metric.status-steady { border-top-color:#2c8061; }
.portfolio-metric span { color:var(--muted); font-size:10px; font-weight:800; }
.portfolio-metric strong { color:var(--ink); font-family:var(--mono); font-size:18px; }
.portfolio-metric small { color:var(--muted); font-size:10px; line-height:1.4; }
.portfolio-dossier-grid { display:grid; grid-template-columns:minmax(0,1.4fr) minmax(280px,.6fr); gap:16px; align-items:start; }
.portfolio-treatment-queue { display:grid; gap:10px; }
.portfolio-queue-item { display:grid; gap:10px; padding:16px; border:1px solid var(--line); border-left:4px solid var(--amber); border-radius:15px; background:#fff; }
.portfolio-queue-item.state-critical { border-left-color:var(--red); }
.portfolio-queue-item.state-steady { border-left-color:#2c8061; }
.portfolio-queue-item.state-blocked { border-left-color:var(--line-strong); background:#f4f5f4; }
.portfolio-queue-item header { display:grid; grid-template-columns:auto 1fr auto; gap:10px; align-items:start; }
.portfolio-queue-item header > span { color:var(--accent); font-family:var(--mono); font-size:11px; font-weight:900; }
.portfolio-queue-item header div { display:grid; gap:3px; }
.portfolio-queue-item header strong { color:var(--ink); }
.portfolio-queue-item header small { color:var(--muted); font-family:var(--mono); font-size:10px; }
.portfolio-queue-item header em { padding:4px 8px; border-radius:999px; color:var(--brand); background:var(--accent-soft); font-size:10px; font-style:normal; font-weight:850; }
.portfolio-cost-context { margin:0; color:var(--ink-soft); font-family:var(--mono); font-size:11px; }
.portfolio-queue-reason { display:grid; grid-template-columns:70px 1fr; gap:10px; align-items:start; padding:10px; border-radius:10px; background:#faf9f5; }
.portfolio-queue-reason span,
.portfolio-trigger-pair span { color:var(--muted); }
.portfolio-queue-reason p { margin:0; color:var(--ink); font-size:12px; line-height:1.5; }
.portfolio-trigger-pair { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
.portfolio-trigger-pair > div { display:grid; gap:5px; padding-top:9px; border-top:1px dashed var(--line); }
.portfolio-trigger-pair strong { color:var(--ink-soft); font-size:11px; line-height:1.45; }
.portfolio-exposure-register { display:grid; gap:10px; padding:17px; border:1px solid var(--line); border-radius:17px; background:rgba(255,255,255,.78); }
.portfolio-exposure { display:grid; gap:7px; padding:12px; border-left:4px solid var(--amber); border-radius:11px; background:#fff; }
.portfolio-exposure.severity-critical,
.portfolio-exposure.severity-high { border-left-color:var(--red); }
.portfolio-exposure > div { display:flex; justify-content:space-between; gap:10px; }
.portfolio-exposure strong { color:var(--ink); font-size:12px; }
.portfolio-exposure span { color:var(--red); font-family:var(--mono); font-weight:900; }
.portfolio-exposure p { margin:0; color:var(--muted); font-size:11px; line-height:1.45; }
.portfolio-boundary-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }
.portfolio-boundary-card { display:grid; gap:11px; padding:16px; border:1px solid var(--line); border-radius:16px; background:#fff; }
.portfolio-boundary-card header { display:flex; justify-content:space-between; gap:10px; }
.portfolio-boundary-card header div { display:grid; gap:3px; }
.portfolio-boundary-card header strong { color:var(--ink); }
.portfolio-boundary-card header small { color:var(--muted); font-family:var(--mono); font-size:10px; }
.portfolio-boundary-card header em { color:var(--brand); font-size:11px; font-style:normal; font-weight:850; }
.portfolio-boundary-card dl { display:grid; gap:7px; margin:0; }
.portfolio-boundary-card dl > div { display:grid; grid-template-columns:104px 1fr; gap:9px; }
.portfolio-boundary-card dt { color:var(--muted); font-size:10px; }
.portfolio-boundary-card dd { margin:0; color:var(--ink-soft); font-size:11px; line-height:1.45; }
.portfolio-prohibited { display:grid; grid-template-columns:74px 1fr; gap:8px; margin:0; padding:10px; border:1px solid rgba(180,72,61,.24); border-radius:10px; color:var(--red); background:#fff7f5; font-size:11px; line-height:1.45; }
.portfolio-prohibited span { color:var(--red); }
.portfolio-supporting-evidence { overflow:hidden; border:1px solid var(--line); border-radius:15px; background:#fff; }
.portfolio-supporting-evidence summary { cursor:pointer; padding:14px 16px; color:var(--ink-soft); font-weight:800; }
.portfolio-supporting-body { padding:0 14px 14px; }
.portfolio-stale-audit { margin-top:0 !important; }
@media (max-width: 920px) {
  .portfolio-dossier-grid { grid-template-columns:1fr; }
  .portfolio-metric-strip { grid-template-columns:repeat(3,minmax(0,1fr)); }
}
@media (max-width: 760px) {
  .portfolio-verdict-brief,
  .portfolio-verdict-metrics,
  .portfolio-metric-strip,
  .portfolio-boundary-grid,
  .portfolio-trigger-pair { grid-template-columns:1fr; }
  .portfolio-verdict-state { border-right:0; border-bottom:1px solid rgba(255,255,255,.12); }
  .portfolio-queue-item header { grid-template-columns:auto 1fr; }
  .portfolio-queue-item header em { grid-column:2; justify-self:start; }
}
@media (prefers-reduced-motion: reduce) {
  .portfolio-queue-item { animation:none; }
}
@media (max-width:1080px) {
  .stock-data-block-grid,
  .stock-pro-grid,
  .stock-diagnosis-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .stock-pro-head,
  .stock-pro-bear,
  .stock-summary-lines { grid-template-columns:1fr; }
  .market-state-strip,
  .stock-identity-strip { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .market-thesis-board,
  .stock-thesis-board { grid-template-columns:1fr; }
  .market-dimension-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .market-decision-rail { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .market-decision-rail-step { border-bottom:1px solid var(--line); }
  .investment-memo-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width:1120px) and (min-width:681px) {
  .research-tape {
    grid-template-columns:minmax(190px,1.4fr) repeat(2,minmax(130px,1fr)) auto;
  }
  .research-tape-item.secondary { display:none; }
}
@media (max-width:680px) {
  .workspace-pane[data-workspace="stock"] .module-header { display:none; }
  .stock-data-block-grid,
  .stock-pro-grid,
  .stock-diagnosis-grid { grid-template-columns:1fr; }
  .market-state-strip { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .stock-identity-strip {
    grid-template-columns:minmax(0,1.4fr) minmax(0,.7fr) minmax(0,1fr) auto;
    border-radius:16px;
  }
  .market-state-strip .module-refresh-tools { grid-column:1 / -1; padding:9px 12px; }
  .stock-identity-strip .module-refresh-tools { grid-column:auto; padding:7px; }
  .stock-identity-strip .module-refresh-tools > span { display:none; }
  .stock-identity-strip .module-refresh-button { padding:8px 9px; font-size:0; }
  .stock-identity-strip .module-refresh-button::after { content:"刷新"; font-size:11px; }
  .stock-identity-strip strong { margin-top:5px; font-size:13px; }
  .stock-identity-strip span { font-size:9px; letter-spacing:.06em; }
  .market-dimension-grid,
  .research-scenario-grid,
  .investment-memo-grid,
  .stock-evidence-grid,
  .thesis-evidence-pair { grid-template-columns:1fr; }
  .brand-subtitle { display:none; }
  .quick-stock-search {
    grid-template-columns:minmax(0,1fr) auto;
    gap:7px;
    padding:8px;
  }
  .quick-stock-search button { padding-inline:14px; white-space:nowrap; }
  .nav-item { flex-basis:112px; }
  .research-tape {
    position:relative;
    top:auto;
    grid-template-columns:repeat(3,minmax(0,1fr));
    margin-bottom:9px;
  }
  .research-tape-primary { grid-column:1 / -1; }
  .research-tape-item.secondary { display:none; }
  .research-tape-data-link {
    grid-template-columns:auto auto;
    justify-content:center;
    place-items:center;
    padding:9px 6px;
  }
  .data-readiness-brief,
  .data-operations-grid { grid-template-columns:1fr; }
  .data-readiness-brief { min-height:0; border-radius:16px; }
  .data-readiness-state,
  .data-readiness-thesis { padding:20px; }
  .data-readiness-state h3 { font-size:30px; }
  .data-readiness-thesis > p { font-size:17px; }
  .data-readiness-metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .data-readiness-metrics > div:nth-child(3) { border-left:0; border-top:1px solid var(--line); }
  .data-readiness-metrics > div:nth-child(4) { border-top:1px solid var(--line); }
  .data-recovery-section,
  .data-impact-section { padding:14px; border-radius:15px; }
  .data-impact-grid { grid-template-columns:1fr; }
  .data-recovery-step { grid-template-columns:38px minmax(0,1fr); gap:9px; }
  .data-recovery-number { width:36px; height:36px; font-size:10px; }
  .data-recovery-step::before { top:34px; bottom:-20px; left:18px; }
  .data-recovery-copy { padding:12px; }
  .data-recovery-copy p,
  .data-recovery-copy small { grid-template-columns:58px minmax(0,1fr); }
  .data-ledger-scroll { overflow:visible; padding:0 10px 10px; }
  .data-ledger-table,
  .data-ledger-table tbody,
  .data-ledger-card,
  .data-ledger-table td { display:block; width:100%; }
  .data-ledger-table thead { display:none; }
  .data-ledger-card {
    margin:0 0 10px;
    overflow:hidden;
    border:1px solid var(--line);
    border-radius:12px;
    background:#fff;
  }
  .data-ledger-table td {
    display:grid;
    grid-template-columns:76px minmax(0,1fr);
    gap:8px;
    padding:8px 10px;
  }
  .data-ledger-table td::before {
    content:attr(data-label);
    color:var(--muted);
    font-family:var(--mono);
    font-size:9px;
    font-weight:850;
  }
  .market-session-ruler { grid-template-columns:1fr; }
  .market-session-ruler > div { padding:10px 14px; }
  .market-session-ruler > div:not(:last-child)::after {
    right:auto;
    bottom:-6px;
    left:25px;
    transform:rotate(135deg);
  }
  .market-session-phase { grid-template-columns:1fr; padding:14px; border-radius:16px; }
  .market-session-heading { align-items:flex-start; }
  .market-intraday-ledger-body { padding:0 9px 9px; }
  .market-intraday-ledger .data-table {
    width:100%;
    overflow-x:auto;
  }
  .market-intraday-ledger .data-table th,
  .market-intraday-ledger .data-table td { min-width:92px; }
  .market-intraday-ledger .data-table th:last-child,
  .market-intraday-ledger .data-table td:last-child { min-width:260px; }
  .market-decision-rail { grid-template-columns:1fr; }
  .market-decision-rail-step { min-height:0; border-right:0; }
  .market-decision-rail-step:not(:last-child)::after { display:none; }
  .market-risk-card { order:-1; }
  .market-state-strip > div { padding:13px 15px; }
  .stock-identity-strip > div { padding:10px; }
}
@media (prefers-reduced-motion: reduce) {
  .market-decision-rail-step { animation:none; }
}

/* Essence mode keeps decisions visible and moves audit depth behind one quiet ledger. */
.essence-strip {
  display:grid;
  gap:0;
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:14px;
  background:rgba(255,255,255,.72);
}
.essence-evidence {
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:15px;
  background:#fff;
}
.essence-evidence > summary {
  cursor:pointer;
  padding:14px 16px;
  color:var(--ink);
  font-weight:850;
  list-style-position:inside;
}
.essence-evidence[open] > summary { border-bottom:1px solid var(--line); }
.essence-evidence-body { display:grid; gap:14px; padding:14px; }
.essence-evidence-body > h4 { margin:0; color:var(--ink); font-size:13px; }
.market-research-workspace,
.portfolio-dossier,
.stock-research-workspace,
.opportunity-dossier,
.data-command-center { gap:14px; }
.market-session-phase { gap:14px; }
.market-session-phase > section > h3,
.portfolio-dossier-grid h3,
.stock-dossier-grid h3,
.dossier-position-panel > h3,
.stock-dossier > section > h3,
.opportunity-dossier section > h3,
.data-operations-grid section > h3 { margin:0 0 10px; font-size:15px; }
.dossier-diagnostic-summary-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
.dossier-diagnostic-summary {
  display:grid;
  gap:6px;
  padding:12px;
  border:1px solid var(--line);
  border-left:3px solid var(--line-strong);
  border-radius:11px;
  background:#fff;
}
.dossier-diagnostic-summary > span { color:var(--muted); font-size:10px; font-weight:850; }
.dossier-diagnostic-summary > strong { color:var(--ink); font-size:12px; line-height:1.45; }
.portfolio-evidence .portfolio-treatment-queue:empty,
.opportunity-evidence .candidate-decision-grid:empty { display:none; }
@media (max-width: 760px) {
  .dossier-diagnostic-summary-grid { grid-template-columns:1fr; }
  .essence-evidence-body { padding:10px; }
  .market-session-ruler.essence-strip { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .market-session-ruler.essence-strip > div { min-width:0; padding:9px; }
  .market-session-ruler.essence-strip > div::after { display:none; }
}

.sr-only {
  position:absolute;
  width:1px;
  height:1px;
  padding:0;
  margin:-1px;
  overflow:hidden;
  clip:rect(0,0,0,0);
  white-space:nowrap;
  border:0;
}
.iwencai-research-console {
  position:relative;
  display:grid;
  gap:12px;
  overflow:hidden;
  padding:16px 16px 16px 20px;
  border:1px solid #b9c8d4;
  border-radius:15px;
  background:linear-gradient(145deg,rgba(255,255,255,.97),rgba(236,243,247,.92));
  box-shadow:0 12px 30px rgba(19,39,58,.07);
}
.iwencai-research-console::before {
  content:"";
  position:absolute;
  inset:0 auto 0 0;
  width:4px;
  background:linear-gradient(180deg,#d5b16a,#0d3b66);
}
.iwencai-research-header {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
}
.iwencai-research-header span,
.iwencai-result-heading span,
.iwencai-unknowns > span {
  color:var(--muted);
  font-family:var(--mono);
  font-size:10px;
  font-weight:800;
  letter-spacing:.09em;
  text-transform:uppercase;
}
.iwencai-research-header h3 {
  margin:4px 0 0;
  font-family:var(--display);
  font-size:18px;
  letter-spacing:-.02em;
}
.iwencai-connection {
  flex:0 0 auto;
  padding:6px 9px;
  border:1px solid var(--line);
  border-radius:999px;
  color:var(--muted);
  background:#fff;
  font-size:11px;
}
.iwencai-connection.connected { color:#176148; border-color:#9bc8b8; background:#edf8f3; }
.iwencai-connection.missing { color:#8a5a17; border-color:#dbc69c; background:#fff8e9; }
.iwencai-connection.blocked { color:#85433e; border-color:#dbb1ad; background:#fff2f1; }
.iwencai-question-rail { display:flex; flex-wrap:wrap; gap:7px; }
.iwencai-question-chip {
  min-height:32px;
  padding:6px 10px;
  border:1px solid var(--line);
  border-radius:9px;
  color:var(--ink-soft);
  background:rgba(255,255,255,.84);
  font-size:12px;
  font-weight:750;
  cursor:pointer;
}
.iwencai-question-chip:hover { border-color:#8fa8bc; background:#fff; }
.iwencai-research-form {
  display:grid;
  grid-template-columns:minmax(0,1fr) auto;
  gap:8px;
  align-items:stretch;
}
.iwencai-research-form.has-context {
  grid-template-columns:minmax(170px,.42fr) minmax(0,1fr) auto;
}
.iwencai-context-select {
  min-width:0;
  padding:0 12px;
  border:1px solid var(--line-strong);
  border-radius:10px;
  color:var(--ink);
  background:#fff;
  font:inherit;
}
.iwencai-context-select:focus-visible {
  outline:2px solid rgba(22,58,88,.2);
  outline-offset:1px;
  border-color:#567b99;
}
.iwencai-research-form textarea {
  width:100%;
  min-height:54px;
  resize:vertical;
  padding:10px 12px;
  border:1px solid var(--line-strong);
  border-radius:10px;
  color:var(--ink);
  background:#fff;
  line-height:1.45;
}
.iwencai-research-form button {
  min-width:104px;
  border:0;
  border-radius:10px;
  padding:0 15px;
  color:#f5f9fc;
  background:#163a58;
  font-weight:850;
  cursor:pointer;
}
.iwencai-research-form button:disabled { cursor:wait; opacity:.62; }
.iwencai-console-state {
  margin:0;
  color:var(--muted);
  font-size:11px;
  line-height:1.45;
}
.iwencai-research-result {
  display:grid;
  gap:10px;
  padding-top:12px;
  border-top:1px solid var(--line);
  animation:iwencai-result-in .2s ease both;
}
.iwencai-research-result[hidden] { display:none; }
@keyframes iwencai-result-in {
  from { opacity:0; transform:translateY(4px); }
  to { opacity:1; transform:translateY(0); }
}
.iwencai-result-heading { display:grid; gap:4px; }
.iwencai-result-heading strong { color:var(--ink); font-size:14px; line-height:1.5; }
.iwencai-fact-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; }
.iwencai-fact-card {
  display:grid;
  gap:6px;
  padding:10px;
  border:1px solid var(--line);
  border-radius:10px;
  background:#fff;
}
.iwencai-fact-card > div { display:flex; justify-content:space-between; gap:10px; }
.iwencai-fact-card span { color:var(--muted); font-size:11px; }
.iwencai-fact-card strong { color:var(--ink); font-size:12px; text-align:right; overflow-wrap:anywhere; }
.iwencai-relationship {
  margin:0;
  padding:9px 10px;
  border-left:3px solid var(--accent);
  color:var(--ink-soft);
  background:#fffaf0;
  font-size:12px;
  line-height:1.5;
}
.iwencai-unknowns ul { margin:5px 0 0; padding-left:18px; color:var(--muted); font-size:11px; line-height:1.55; }
.iwencai-audit,
.iwencai-boundary { display:block; color:var(--muted); font-size:10px; line-height:1.45; }
.iwencai-error { color:var(--red); font-size:12px; }
@media (max-width: 760px) {
  .iwencai-research-console { padding:13px 12px 13px 16px; gap:10px; }
  .iwencai-research-form,
  .iwencai-research-form.has-context { grid-template-columns:1fr; }
  .iwencai-context-select { width:100%; min-height:42px; }
  .iwencai-research-form button { min-height:42px; }
  .iwencai-fact-grid { grid-template-columns:1fr; }
  .iwencai-question-rail { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); }
  .iwencai-question-chip { width:100%; }
}
@media (prefers-reduced-motion: reduce) {
  .iwencai-research-result { animation:none; }
}

/* Three-second decision note: one verdict, one action, one risk, then audit depth. */
.essence-verdict,
.portfolio-verdict-brief,
.dossier-decision-brief,
.stock-thesis-board,
.opportunity-gate-brief {
  position:relative;
  overflow:hidden;
  border:1px solid #b8c8d4;
  border-left:5px solid var(--brand);
  border-radius:16px;
  background:linear-gradient(112deg,#fff 0%,#f4f8fa 72%,#eef4f7 100%);
  box-shadow:0 16px 38px rgba(19,39,58,.07);
  color:var(--ink);
}
.essence-verdict::after,
.portfolio-verdict-brief::after,
.dossier-decision-brief::after,
.stock-thesis-board::after,
.opportunity-gate-brief::after {
  content:"";
  position:absolute;
  inset:0 0 auto;
  height:1px;
  background:linear-gradient(90deg,var(--accent),transparent 52%);
}
.dossier-decision-brief .dossier-stance h3,
.portfolio-verdict-brief .portfolio-verdict-state h3,
.opportunity-gate-brief .opportunity-gate-state h3 { color:var(--ink); }
.dossier-decision-brief .dossier-stance,
.dossier-decision-brief .dossier-thesis,
.portfolio-verdict-brief .portfolio-verdict-state,
.portfolio-verdict-brief .portfolio-verdict-thesis,
.opportunity-gate-brief .opportunity-gate-state,
.opportunity-gate-brief .opportunity-gate-thesis { color:var(--ink); }
.dossier-decision-brief .dossier-stance span,
.dossier-decision-brief .dossier-core-conflict span,
.portfolio-verdict-brief .portfolio-verdict-state span,
.opportunity-gate-brief .opportunity-gate-state span { color:var(--brand); }
.dossier-decision-brief .dossier-core-conflict {
  border-color:var(--line);
}
.dossier-decision-brief .dossier-core-conflict strong,
.dossier-decision-brief .dossier-thesis > p,
.portfolio-verdict-brief .portfolio-verdict-thesis > p,
.opportunity-gate-brief .opportunity-gate-thesis > p { color:var(--ink); }
.portfolio-verdict-brief .portfolio-verdict-thesis > small,
.opportunity-gate-brief .opportunity-gate-thesis > small { color:var(--muted); }
.dossier-decision-brief .dossier-stance h3,
.portfolio-verdict-brief .portfolio-verdict-state h3,
.opportunity-gate-brief .opportunity-gate-state h3 {
  font-size:clamp(27px,3vw,38px);
}
.portfolio-queue-item header { grid-template-columns:minmax(0,1fr) auto; }
.essence-action-risk {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:8px;
  margin-top:12px;
}
.essence-action,
.essence-risk {
  display:grid;
  min-width:0;
  gap:5px;
  padding:11px 12px;
  border:1px solid var(--line);
  border-radius:11px;
  background:rgba(255,255,255,.88);
}
.essence-action { border-left:3px solid #2f7864; }
.essence-risk { border-left:3px solid var(--red); }
.essence-action > span,
.essence-risk > span {
  color:var(--muted);
  font-size:10px;
  font-weight:850;
  letter-spacing:.06em;
}
.essence-action > strong,
.essence-risk > strong {
  color:var(--ink);
  font-size:13px;
  line-height:1.5;
  overflow-wrap:anywhere;
}
.essence-focus-list {
  display:grid;
  gap:9px;
  min-width:0;
}
.essence-focus-list > h3 {
  margin:0;
  color:var(--ink);
  font-size:14px;
  letter-spacing:-.01em;
}
.stock-core-facts {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:8px;
}
.stock-core-fact {
  display:grid;
  min-width:0;
  gap:6px;
  padding:12px;
  border:1px solid var(--line);
  border-top:3px solid #7191a9;
  border-radius:11px;
  background:#fff;
}
.stock-core-fact.is-counter { border-top-color:var(--red); background:#fffafa; }
.stock-core-fact > span { color:var(--muted); font-size:10px; font-weight:850; }
.stock-core-fact > strong { color:var(--ink); font-size:13px; line-height:1.45; }
.stock-core-fact > small { color:var(--muted); font-size:10px; line-height:1.45; }
.essence-detail-meta { margin:0; color:var(--muted); font-size:11px; }
.portfolio-queue-audit { display:grid; gap:8px; }
.portfolio-queue-audit-item {
  display:grid;
  gap:7px;
  padding:12px;
  border:1px solid var(--line);
  border-radius:11px;
  background:#fff;
}
.portfolio-queue-audit-item header { display:flex; justify-content:space-between; gap:10px; }
.portfolio-queue-audit-item p { margin:0; color:var(--muted); font-size:11px; }
.portfolio-queue-audit-item dl { display:grid; gap:6px; margin:0; }
.portfolio-queue-audit-item dl > div { display:grid; grid-template-columns:88px 1fr; gap:8px; }
.portfolio-queue-audit-item dt { color:var(--muted); font-size:10px; }
.portfolio-queue-audit-item dd { margin:0; color:var(--ink-soft); font-size:11px; }
.portfolio-invalidation { display:grid; gap:4px; }
.portfolio-invalidation span { color:var(--muted); font-size:10px; }
.portfolio-invalidation strong { color:var(--ink); font-size:12px; }
.iwencai-research-disclosure {
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:13px;
  background:rgba(248,251,253,.82);
}
.iwencai-research-disclosure > summary,
.essence-evidence > summary {
  display:grid;
  grid-template-columns:minmax(0,1fr) auto auto;
  align-items:center;
  min-height:46px;
  gap:10px;
  padding:11px 14px;
  cursor:pointer;
  list-style:none;
  color:var(--ink-soft);
  font-size:12px;
  font-weight:850;
}
.iwencai-research-disclosure > summary::-webkit-details-marker,
.essence-evidence > summary::-webkit-details-marker { display:none; }
.iwencai-research-disclosure > summary::after,
.essence-evidence > summary::after {
  content:"+";
  display:grid;
  width:22px;
  height:22px;
  place-items:center;
  border:1px solid var(--line);
  border-radius:50%;
  color:var(--muted);
  background:#fff;
  font-family:var(--mono);
}
.iwencai-research-disclosure[open] > summary::after,
.essence-evidence[open] > summary::after { content:"-"; }
.iwencai-research-disclosure[open] > summary,
.essence-evidence[open] > summary { border-bottom:1px solid var(--line); }
.iwencai-research-disclosure > summary:focus-visible,
.essence-evidence > summary:focus-visible {
  outline:3px solid rgba(25,83,141,.22);
  outline-offset:-3px;
}
.iwencai-research-disclosure .iwencai-research-console {
  border:0;
  border-radius:0;
  box-shadow:none;
}
.iwencai-research-disclosure .iwencai-research-console::before { display:none; }
.essence-evidence-body > section { min-width:0; }

@media (max-width: 760px) {
  .essence-verdict,
  .portfolio-verdict-brief,
  .dossier-decision-brief,
  .stock-thesis-board,
  .opportunity-gate-brief,
  .essence-action-risk,
  .stock-core-facts { grid-template-columns:1fr; }
  .essence-action-risk { gap:7px; margin-top:9px; }
  .essence-action,
  .essence-risk,
  .stock-core-fact { padding:10px; }
  .iwencai-research-disclosure > summary,
  .essence-evidence > summary { min-height:44px; padding:9px 11px; }
  .portfolio-queue-audit-item dl > div { grid-template-columns:1fr; gap:2px; }
  .market-state-strip,
  .stock-identity-strip { min-width:0; }
  .market-state-strip > div,
  .stock-identity-strip > div { min-width:0; }
}
@media (prefers-reduced-motion: reduce) {
  .iwencai-research-disclosure > summary,
  .essence-evidence > summary { scroll-behavior:auto; }
}

/* Native research workspaces: one judgment, one action, one risk. */
.engine-workspace-root {
  background:
    linear-gradient(rgba(16,38,58,.035) 1px, transparent 1px),
    linear-gradient(90deg, rgba(16,38,58,.035) 1px, transparent 1px);
  background-size:32px 32px;
}
.engine-page-intro {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:18px;
  margin:0 0 16px;
  padding:12px 2px 14px;
  border-bottom:1px solid var(--line);
}
.engine-page-intro > div { display:flex; align-items:baseline; gap:14px; }
.engine-page-intro span {
  color:var(--muted);
  font:800 10px/1 var(--mono);
  letter-spacing:.14em;
}
.engine-page-intro strong {
  color:#10263a;
  font:850 20px/1.2 var(--display);
  letter-spacing:-.025em;
}
.engine-page-intro p { margin:0; color:var(--muted); font-size:12px; }
.engine-module,
.engine-system-module {
  display:grid;
  width:100%;
  max-width:1180px;
  margin:0 auto;
  gap:12px;
}
.engine-header {
  display:flex;
  align-items:flex-end;
  justify-content:space-between;
  gap:18px;
  min-width:0;
  padding:4px 2px 12px;
  border-bottom:1px solid var(--line-strong);
}
.engine-header > div:first-child { display:grid; gap:5px; }
.engine-header span {
  color:var(--muted);
  font-size:10px;
  font-weight:850;
  letter-spacing:.11em;
}
.engine-header h2 {
  margin:0;
  color:#10263a;
  font:900 clamp(25px,3vw,38px)/1 var(--display);
  letter-spacing:-.045em;
}
.engine-meta { display:grid; justify-items:end; gap:5px; }
.engine-meta time { color:var(--muted); font:750 10px/1.2 var(--mono); }
.engine-delivery {
  color:#426174;
  font:800 9px/1 var(--mono);
  letter-spacing:.04em;
}
.engine-delivery.is-stale { color:#a36d1d; }
.engine-service-state {
  display:inline-flex;
  align-items:center;
  gap:7px;
  color:var(--muted);
  font-size:11px;
  white-space:nowrap;
}
.engine-service-state::before {
  content:"";
  width:7px;
  height:7px;
  border-radius:50%;
  background:currentColor;
}
.engine-service-state.state-ready { color:#0e6a5c; }
.engine-service-state.state-blocked,
.engine-service-state.state-missing { color:#b64a3c; }
.engine-judgment {
  position:relative;
  display:grid;
  grid-template-columns:minmax(0,1.25fr) minmax(320px,.75fr);
  min-width:0;
  overflow:hidden;
  border:1px solid #cbd5d9;
  border-radius:9px;
  background:#fff;
  box-shadow:0 18px 42px rgba(16,38,58,.075);
}
.engine-signal-band {
  position:absolute;
  inset:0 0 auto;
  height:5px;
  overflow:hidden;
  background:#dce4e7;
}
.engine-signal-band i {
  display:block;
  width:34%;
  height:100%;
  background:#6e8290;
  transition:width .35s ease, background .25s ease;
}
.engine-judgment.state-complete .engine-signal-band i { width:100%; background:#0e6a5c; }
.engine-judgment.state-partial .engine-signal-band i { width:68%; background:#b4853a; }
.engine-judgment.state-empty .engine-signal-band i,
.engine-judgment.state-unavailable .engine-signal-band i { width:100%; background:#b64a3c; }
.engine-judgment.is-loading .engine-signal-band i {
  width:38%;
  background:#19538d;
  animation:engine-scan 1.15s ease-in-out infinite alternate;
}
@keyframes engine-scan { from { transform:translateX(-25%); } to { transform:translateX(190%); } }
.engine-verdict {
  display:grid;
  align-content:center;
  gap:10px;
  min-width:0;
  padding:34px 34px 30px;
  border-right:1px solid var(--line);
}
.engine-verdict > span,
.engine-action span,
.engine-risk span {
  color:var(--muted);
  font-size:10px;
  font-weight:900;
  letter-spacing:.08em;
}
.engine-decision-label {
  justify-self:start;
  display:inline-flex;
  align-items:center;
  min-height:27px;
  padding:6px 10px;
  border:1px solid #b9c8cd;
  border-radius:999px;
  color:#3f5866;
  background:#f2f6f6;
  font:900 11px/1 var(--mono);
  letter-spacing:.03em;
}
.engine-decision-label.state-positive {
  border-color:#91bdb2;
  color:#0c6658;
  background:#eff9f6;
}
.engine-decision-label.state-caution {
  border-color:#d6bd8c;
  color:#805b20;
  background:#fff8e9;
}
.engine-decision-label.state-negative {
  border-color:#d7aaa4;
  color:#9a4036;
  background:#fff4f2;
}
.engine-decision-label.state-neutral {
  border-color:#b9c8cd;
  color:#3f5866;
  background:#f2f6f6;
}
.engine-verdict h3 {
  max-width:22em;
  margin:0;
  color:#10263a;
  font:900 clamp(23px,3.2vw,43px)/1.16 var(--display);
  letter-spacing:-.045em;
}
.engine-verdict p { margin:0; color:var(--muted); font-size:12px; line-height:1.55; }
.engine-action-risk { display:grid; grid-template-rows:1fr 1fr; min-width:0; }
.engine-action,
.engine-risk { display:grid; align-content:center; gap:8px; min-width:0; padding:23px 26px; }
.engine-action { border-bottom:1px solid var(--line); }
.engine-action strong,
.engine-risk strong { color:var(--ink); font-size:14px; line-height:1.55; }
.engine-action { box-shadow:inset 3px 0 0 #0e6a5c; }
.engine-risk { box-shadow:inset 3px 0 0 #b64a3c; background:#fffafa; }
.engine-action-rail {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  overflow:hidden;
  border:1px solid #cbd5d9;
  border-radius:8px;
  background:rgba(255,255,255,.78);
}
.engine-action-rail button {
  min-height:44px;
  padding:9px 12px;
  border:0;
  border-right:1px solid var(--line);
  color:#304b5c;
  background:transparent;
  font-size:11px;
  font-weight:850;
  cursor:pointer;
}
.engine-action-rail button:last-child { border-right:0; }
.engine-action-rail button:hover { color:#10263a; background:#f1f6f7; }
.engine-action-rail button:focus-visible,
.engine-mobile-dock button:focus-visible,
.engine-risk:focus,
.engine-findings-block:focus,
.engine-disclosure:focus {
  outline:3px solid rgba(25,83,141,.28);
  outline-offset:2px;
}
.engine-risk,
.engine-findings-block,
.engine-disclosure { scroll-margin-top:16px; }
.engine-sections {
  display:grid;
  min-width:0;
  max-width:100%;
}
.engine-sections[hidden] { display:none; }
.engine-section-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:10px;
  min-width:0;
  max-width:100%;
}
.engine-research-section {
  display:grid;
  align-content:start;
  min-width:0;
  gap:12px;
  padding:15px;
  border:1px solid #cbd7da;
  border-radius:9px;
  background:rgba(255,255,255,.9);
  box-shadow:0 10px 28px rgba(16,38,58,.045);
}
.engine-research-section.is-theme { grid-column:1/-1; }
.engine-research-section.tone-positive { border-top:3px solid #5b9a8c; }
.engine-research-section.tone-negative { border-top:3px solid #b9675c; }
.engine-research-section-heading { display:grid; gap:5px; }
.engine-research-section-heading h3 {
  margin:0;
  color:#10263a;
  font:900 15px/1.25 var(--display);
  letter-spacing:-.015em;
}
.engine-research-section-heading p {
  margin:0;
  color:#566b76;
  font-size:11px;
  line-height:1.5;
}
.engine-theme-strip {
  display:flex;
  gap:8px;
  min-width:0;
  max-width:100%;
  overflow-x:auto;
  overscroll-behavior-inline:contain;
  scroll-snap-type:inline proximity;
  scrollbar-width:thin;
  scrollbar-color:#aebfc4 transparent;
  padding:1px 1px 7px;
}
.engine-theme-strip:focus-visible {
  outline:3px solid rgba(25,83,141,.28);
  outline-offset:3px;
}
.engine-theme-card {
  flex:0 0 clamp(200px,27vw,285px);
  display:grid;
  align-content:start;
  gap:8px;
  min-width:0;
  padding:13px;
  border:1px solid #c7d7d7;
  border-left:4px solid #4f9284;
  border-radius:7px;
  background:#f8fbfa;
  scroll-snap-align:start;
}
.engine-theme-card.state-partial,
.engine-theme-card.state-missing,
.engine-theme-card.state-failed {
  border-left-color:#bd8735;
  background:#fffaf0;
}
.engine-theme-card-meta,
.engine-stock-card-meta {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:8px;
}
.engine-theme-card-meta span,
.engine-theme-card-meta i,
.engine-stock-card-meta span,
.engine-stock-card-meta i {
  color:#657984;
  font:800 9px/1.2 var(--mono);
  font-style:normal;
}
.engine-theme-card > strong,
.engine-stock-card > strong,
.engine-divergence-card > strong { color:#10263a; font-size:14px; line-height:1.3; }
.engine-theme-card > p,
.engine-stock-card > p {
  margin:0;
  color:#405965;
  font-size:11px;
  line-height:1.5;
}
.engine-breadth-grid { display:grid; gap:10px; }
.engine-breadth-row { display:grid; gap:6px; min-width:0; }
.engine-breadth-meta { display:flex; align-items:center; justify-content:space-between; gap:9px; }
.engine-breadth-meta span { color:#536a76; font-size:10px; font-weight:850; }
.engine-breadth-meta strong { color:#10263a; font:900 11px/1 var(--mono); }
.engine-breadth-track {
  position:relative;
  overflow:hidden;
  height:8px;
  border-radius:999px;
  background:#e9eeef;
}
.engine-breadth-fill {
  display:block;
  width:0;
  height:100%;
  border-radius:inherit;
  background:#879aa3;
  transition:width .35s ease;
}
.engine-breadth-row.is-rise .engine-breadth-fill,
.engine-breadth-row.is-limit-up .engine-breadth-fill { background:#bd6158; }
.engine-breadth-row.is-fall .engine-breadth-fill,
.engine-breadth-row.is-limit-down .engine-breadth-fill { background:#378472; }
.engine-breadth-row.is-flat .engine-breadth-fill { background:#8999a0; }
.engine-breadth-row.is-pending .engine-breadth-track { background:#f2eee5; }
.engine-stock-card-grid,
.engine-divergence-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:8px;
}
.engine-candidate-group { display:grid; gap:8px; min-width:0; }
.engine-candidate-group + .engine-candidate-group {
  margin-top:4px;
  padding-top:12px;
  border-top:1px solid var(--line);
}
.engine-candidate-group-title {
  margin:0;
  color:#304b5c;
  font:900 12px/1.25 var(--display);
}
.engine-stock-card,
.engine-divergence-card {
  display:grid;
  align-content:start;
  min-width:0;
  gap:8px;
  padding:12px;
  border:1px solid #cfdbdd;
  border-radius:7px;
  background:#fff;
}
.engine-stock-card.state-partial,
.engine-stock-card.state-missing,
.engine-stock-card.state-failed,
.engine-divergence-card.state-partial,
.engine-divergence-card.state-missing,
.engine-divergence-card.state-failed { border-color:#d9c49b; background:#fffbf2; }
.engine-stock-theme {
  justify-self:start;
  display:inline-flex;
  max-width:100%;
  padding:4px 7px;
  border-radius:999px;
  color:#286f64;
  background:#edf7f4;
  font-size:9px;
  font-weight:850;
  overflow-wrap:anywhere;
}
.engine-stock-card > small,
.engine-divergence-card > small { color:#8a5249; font-size:9px; line-height:1.45; }
.engine-divergence-comparison { display:grid; grid-template-columns:1fr 1fr; gap:6px; }
.engine-divergence-comparison p {
  margin:0;
  padding:9px;
  border-radius:6px;
  font-size:10px;
  line-height:1.45;
}
.engine-divergence-comparison .is-strong { color:#955046; background:#fff1ef; }
.engine-divergence-comparison .is-weak { color:#226f60; background:#edf8f4; }
.engine-divergence-comparison .is-pending {
  grid-column:1/-1;
  color:#6b5a3d;
  background:#fff8e9;
}
.engine-section-empty {
  width:100%;
  padding:16px;
  border:1px dashed #c8d3d6;
  color:#657984;
  font-size:11px;
  text-align:center;
}
.engine-findings-block {
  display:grid;
  gap:9px;
  padding:14px;
  border:1px solid var(--line);
  border-radius:9px;
  background:rgba(255,255,255,.78);
}
.engine-section-heading { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.engine-section-heading h3 { margin:0; color:var(--ink); font-size:14px; }
.engine-section-heading small { color:var(--muted); font:750 10px/1 var(--mono); }
.engine-section-meta { display:flex; align-items:center; gap:9px; }
.engine-coverage {
  display:inline-flex;
  align-items:center;
  min-height:22px;
  padding:4px 8px;
  border:1px solid #d9c59d;
  border-radius:999px;
  color:#795a23;
  background:#fffaf0;
  font:800 9px/1 var(--mono);
}
.engine-coverage.is-complete { border-color:#9fc6bb; color:#0e6a5c; background:#f3fbf8; }
.engine-findings { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; }
.engine-finding-card {
  display:grid;
  align-content:start;
  min-width:0;
  gap:7px;
  padding:13px;
  border:1px solid var(--line);
  border-top:2px solid #718998;
  border-radius:7px;
  background:#fff;
}
.engine-finding-card:nth-child(2) { border-top-color:#0e6a5c; }
.engine-finding-card:nth-child(3) { border-top-color:#b4853a; }
.engine-finding-meta { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.engine-finding-rank {
  color:#496272;
  font:900 12px/1 var(--mono);
  letter-spacing:-.04em;
}
.engine-evidence-tag { color:var(--muted); font-size:9px; font-weight:850; }
.engine-finding-card > strong { color:var(--ink); font-size:13px; line-height:1.35; }
.engine-finding-card > p {
  min-height:3em;
  margin:0;
  color:var(--ink-soft);
  font-size:11px;
  line-height:1.5;
}
.engine-fact-list { display:grid; gap:5px; margin:3px 0 0; }
.engine-fact-list > div { display:grid; grid-template-columns:minmax(60px,.7fr) minmax(0,1.3fr); gap:7px; }
.engine-fact-list dt { color:var(--muted); font-size:9px; }
.engine-fact-list dd {
  margin:0;
  color:var(--ink);
  font:800 9px/1.35 var(--mono);
  overflow-wrap:anywhere;
}
.engine-empty {
  grid-column:1/-1;
  padding:19px;
  border:1px dashed var(--line-strong);
  color:var(--muted);
  font-size:11px;
  text-align:center;
}
.engine-module-items {
  display:grid;
  gap:9px;
  padding:14px;
  border:1px solid var(--line);
  border-radius:9px;
  background:rgba(245,249,249,.86);
}
.engine-module-items[hidden] { display:none; }
.engine-module-items-count { color:var(--muted); font:800 9px/1 var(--mono); }
.engine-module-item-grid {
  display:grid;
  grid-template-columns:repeat(2,minmax(0,1fr));
  gap:8px;
}
.workspace-pane[data-workspace="market"] .engine-module-item-grid,
.workspace-pane[data-workspace="stock"] .engine-module-item-grid {
  grid-template-columns:repeat(3,minmax(0,1fr));
}
.engine-module-item {
  display:grid;
  align-content:start;
  min-width:0;
  gap:7px;
  padding:13px;
  border:1px solid #cdd9dc;
  border-left:3px solid #258273;
  border-radius:7px;
  background:#fff;
}
.engine-module-item.state-missing,
.engine-module-item.state-failed { border-left-color:#bd8632; }
.engine-module-item-meta { display:flex; justify-content:space-between; gap:8px; }
.engine-module-item-meta span,
.engine-module-item-meta i { color:var(--muted); font:800 9px/1.2 var(--mono); font-style:normal; }
.engine-module-item > strong { color:var(--ink); font-size:13px; line-height:1.35; }
.engine-module-item > p { margin:0; color:var(--ink-soft); font-size:11px; line-height:1.5; }
.engine-module-item > small { color:#8b563f; font-size:10px; line-height:1.45; }
.engine-module-item-link {
  justify-self:start;
  color:#19538d;
  font-size:10px;
  font-weight:850;
  text-decoration:none;
}
.engine-module-item-link:hover { text-decoration:underline; }
.engine-actions { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:8px; align-items:start; }
.engine-disclosure {
  overflow:hidden;
  border:1px solid var(--line);
  border-radius:8px;
  background:rgba(255,255,255,.72);
}
.engine-disclosure > summary {
  min-height:43px;
  padding:12px 14px;
  cursor:pointer;
  list-style:none;
  color:var(--ink-soft);
  font-size:12px;
  font-weight:850;
}
.engine-disclosure > summary::-webkit-details-marker { display:none; }
.engine-disclosure > summary::after { content:"+"; float:right; color:var(--muted); font-family:var(--mono); }
.engine-disclosure[open] > summary { border-bottom:1px solid var(--line); }
.engine-disclosure[open] > summary::after { content:"-"; }
.engine-run-button {
  min-height:43px;
  padding:10px 18px;
  border:1px solid #10263a;
  border-radius:8px;
  color:#fff;
  background:#10263a;
  font-size:12px;
  font-weight:900;
  cursor:pointer;
}
.engine-run-button:disabled { cursor:not-allowed; opacity:.45; }
.engine-live-state { min-height:16px; margin:0; color:var(--muted); font-size:10px; }
.engine-details { display:grid; gap:8px; padding:10px; }
.engine-details > p { margin:0; color:var(--muted); font-size:11px; }
.engine-detail-section { display:grid; gap:7px; padding:10px; border:1px solid var(--line); background:#fff; }
.engine-detail-heading { display:flex; justify-content:space-between; gap:10px; }
.engine-detail-heading strong { color:var(--ink); font-size:12px; }
.engine-detail-heading span { color:var(--muted); font-size:9px; }
.engine-detail-heading .state-ready { color:#0e6a5c; }
.engine-detail-heading .state-insufficient { color:#a36d1d; }
.engine-detail-heading .state-failed,
.engine-detail-heading .state-missing { color:#b64a3c; }
.engine-detail-empty,
.engine-missing-note { margin:0; color:var(--muted); font-size:10px; }
.engine-system-card { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:8px; }
.engine-system-card > div { display:grid; gap:8px; padding:16px; border:1px solid var(--line); background:#fff; }
.engine-system-card span { color:var(--muted); font-size:10px; }
.engine-system-card strong { color:var(--ink); font-size:13px; line-height:1.45; }

.nav-item[data-engine-nav-state] { gap:7px; }
.nav-item[data-engine-nav-state] > span:not(.sr-only) { margin-left:auto; }
.engine-nav-state-dot {
  display:block;
  flex:0 0 auto;
  width:7px;
  height:7px;
  border-radius:50%;
  background:#7e8b93;
  box-shadow:0 0 0 3px rgba(126,139,147,.12);
}
[data-engine-nav-state="idle"] .engine-nav-state-dot { background:#7e8b93; }
[data-engine-nav-state="loading"] .engine-nav-state-dot {
  background:#4c88bd;
  box-shadow:0 0 0 3px rgba(76,136,189,.18);
  animation:engine-nav-pulse 1.15s ease-in-out infinite;
}
[data-engine-nav-state="complete"] .engine-nav-state-dot {
  background:#258273;
  box-shadow:0 0 0 3px rgba(37,130,115,.14);
}
[data-engine-nav-state="partial"] .engine-nav-state-dot {
  background:#bd8632;
  box-shadow:0 0 0 3px rgba(189,134,50,.14);
}
[data-engine-nav-state="unavailable"] .engine-nav-state-dot {
  background:#ba4e42;
  box-shadow:0 0 0 3px rgba(186,78,66,.14);
}
@keyframes engine-nav-pulse {
  50% { transform:scale(1.35); box-shadow:0 0 0 5px rgba(76,136,189,.08); }
}

.engine-mobile-dock { display:none; }

@media (max-width: 760px) {
  .essence-action-risk,
  .stock-core-facts { grid-template-columns:1fr; }
  .engine-app-shell .sidebar .nav-item[data-engine-nav-state] { display:none; }
  .engine-page-intro { align-items:flex-start; padding-top:4px; }
  .engine-page-intro > div { display:grid; gap:5px; }
  .engine-page-intro p { display:none; }
  .engine-header { align-items:flex-start; }
  .engine-header h2 { font-size:29px; }
  .engine-meta { max-width:44%; }
  .engine-judgment { grid-template-columns:minmax(0,1fr); }
  .engine-verdict { padding:28px 18px 22px; border-right:0; border-bottom:1px solid var(--line); }
  .engine-verdict h3 { font-size:27px; }
  .engine-action-risk { grid-template-rows:auto; }
  .engine-action,
  .engine-risk { padding:16px 18px; }
  .engine-action-rail button { padding-inline:7px; }
  .engine-findings { grid-template-columns:minmax(0,1fr); }
  .engine-section-grid,
  .engine-stock-card-grid,
  .engine-divergence-grid { grid-template-columns:minmax(0,1fr); }
  .engine-divergence-comparison { grid-template-columns:minmax(0,1fr); }
  .engine-module-item-grid,
  .workspace-pane[data-workspace="market"] .engine-module-item-grid,
  .workspace-pane[data-workspace="stock"] .engine-module-item-grid {
    grid-template-columns:minmax(0,1fr);
  }
  .engine-section-meta small { display:none; }
  .engine-finding-card > p { min-height:0; }
  .engine-actions { grid-template-columns:minmax(0,1fr); }
  .engine-run-button { width:100%; }
  .engine-system-card { grid-template-columns:minmax(0,1fr); }
  .engine-fact-list > div { grid-template-columns:82px minmax(0,1fr); }
  .engine-workspace-root {
    padding-bottom:calc(94px + env(safe-area-inset-bottom));
  }
  .engine-mobile-dock {
    position:fixed;
    z-index:80;
    right:10px;
    bottom:8px;
    left:10px;
    display:grid;
    grid-template-columns:repeat(4,minmax(0,1fr));
    gap:3px;
    padding:6px 6px calc(6px + env(safe-area-inset-bottom));
    border:1px solid rgba(130,151,160,.72);
    border-radius:13px;
    background:rgba(244,248,248,.96);
    box-shadow:0 18px 42px rgba(16,38,58,.22);
    backdrop-filter:blur(14px);
  }
  .engine-mobile-dock button {
    position:relative;
    display:grid;
    place-items:center;
    align-content:center;
    min-width:0;
    min-height:44px;
    gap:3px;
    padding:5px 3px;
    border:0;
    border-radius:8px;
    color:#5b6e78;
    background:transparent;
    cursor:pointer;
  }
  .engine-mobile-dock button.active {
    color:#10263a;
    background:#fff;
    box-shadow:inset 0 0 0 1px #c3d0d4, 0 4px 12px rgba(16,38,58,.08);
  }
  .engine-mobile-dock-index {
    color:#758894;
    font:850 8px/1 var(--mono);
    letter-spacing:.08em;
  }
  .engine-mobile-dock strong {
    overflow:hidden;
    max-width:100%;
    font-size:10px;
    line-height:1.15;
    text-overflow:ellipsis;
    white-space:nowrap;
  }
  .engine-mobile-dock .engine-nav-state-dot {
    position:absolute;
    top:7px;
    right:8px;
    width:6px;
    height:6px;
  }
}
@media (max-width: 640px) {
  .engine-app-shell .sidebar {
    display:grid;
    gap:5px;
    padding:8px 10px 6px;
  }
  .engine-app-shell .brand-mark {
    gap:8px;
    margin:0;
    padding:0;
  }
  .engine-app-shell .logo { width:30px; height:30px; border-radius:8px; }
  .engine-app-shell .brand-title { font-size:14px; }
  .engine-app-shell .sidebar-account-card {
    grid-template-columns:minmax(0,1fr) auto;
    align-items:center;
    gap:5px;
    margin:0;
    padding:5px 7px;
    border-radius:9px;
  }
  .engine-app-shell .sidebar-account-card > span,
  .engine-app-shell .sidebar-account-card > small { display:none; }
  .engine-app-shell .sidebar-account-card strong { font-size:11px; }
  .engine-app-shell .sidebar-account-actions { flex-wrap:nowrap; gap:4px; }
  .engine-app-shell .sidebar-account-link {
    min-height:24px;
    padding:3px 6px;
    font-size:9px;
  }
  .engine-app-shell .quick-stock-search {
    gap:5px;
    margin:0;
    padding:5px;
    border-radius:10px;
  }
  .engine-app-shell .quick-stock-search input,
  .engine-app-shell .quick-stock-search button {
    min-height:32px;
    padding:6px 8px;
    border-radius:8px;
  }
  .engine-app-shell .quick-stock-search input { font-size:16px; }
  .engine-app-shell .quick-stock-search button { font-size:11px; }
  .engine-app-shell .nav-group {
    display:grid;
    grid-template-columns:repeat(2,minmax(0,1fr));
    gap:5px;
    width:100%;
    max-width:100%;
    margin:0;
    padding:0;
    overflow:visible;
  }
  .engine-app-shell .nav-item {
    min-height:30px;
    padding:5px 8px;
    border-radius:8px;
    font-size:10px;
  }
  .engine-workspace-root {
    width:100%;
    max-width:100%;
    min-width:0;
    padding:8px 10px calc(94px + env(safe-area-inset-bottom));
    overflow-x:clip;
  }
  .engine-module { gap:7px; padding:8px; border-radius:11px; }
  .engine-header {
    align-items:center;
    gap:8px;
    padding:0 1px 6px;
  }
  .engine-header > div:first-child { gap:2px; }
  .engine-header span { font-size:8px; }
  .engine-header h2 { font-size:21px; }
  .engine-meta { max-width:48%; gap:2px; }
  .engine-meta time,
  .engine-delivery { font-size:10px; }
  .engine-service-state { gap:4px; font-size:10px; }
  .engine-service-state::before { width:5px; height:5px; }
  .engine-judgment { grid-template-columns:minmax(0,1fr); border-radius:7px; }
  .engine-signal-band { height:3px; }
  .engine-verdict {
    gap:6px;
    padding:12px;
    border-right:0;
    border-bottom:1px solid var(--line);
  }
  .engine-decision-label {
    min-height:22px;
    padding:4px 7px;
    font-size:10px;
  }
  .engine-verdict > span,
  .engine-action span,
  .engine-risk span { font-size:10px; }
  .engine-verdict h3 { font-size:20px; line-height:1.22; letter-spacing:-.025em; }
  .engine-action-risk {
    grid-template-columns:repeat(2,minmax(0,1fr));
    grid-template-rows:auto;
  }
  .engine-action,
  .engine-risk { gap:4px; padding:9px 10px; }
  .engine-action { border-right:1px solid var(--line); border-bottom:0; }
  .engine-action strong,
  .engine-risk strong { font-size:11px; line-height:1.35; }
  .engine-section-grid { grid-template-columns:minmax(0,1fr); gap:8px; }
  .engine-research-section { gap:8px; padding:10px; }
  .engine-research-section-heading { gap:3px; }
  .engine-research-section-heading h3 { font-size:14px; }
  .engine-theme-card { flex-basis:180px; gap:6px; padding:10px; }
  .engine-module,
  .engine-sections,
  .engine-research-section { max-width:100%; min-width:0; }
  .engine-section-grid { grid-template-columns:minmax(0,1fr); }
}
@media (prefers-reduced-motion: reduce) {
  .engine-signal-band i,
  .engine-nav-state-dot,
  .engine-breadth-fill { transition:none; animation:none !important; }
}

"""
