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
.mini-button:focus-visible {
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
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap:10px;
  margin: 0 0 14px;
  padding:10px;
  border:1px solid var(--line);
  border-radius:20px;
  background:rgba(248,251,253,.90);
  backdrop-filter:blur(16px);
  box-shadow:0 12px 34px rgba(19,39,58,.08);
}
.freshness-bar div {
  border:1px solid rgba(13,59,102,.08);
  border-radius:14px;
  padding:9px 10px;
  background:rgba(255,255,255,.78);
}
.freshness-bar span {
  display:block;
  color:var(--muted);
  font-size:11px;
  margin-bottom:4px;
}
.freshness-bar strong {
  display:block;
  font-size:13px;
  color:var(--ink);
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
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
.data-center-panel {
  margin:0 0 16px;
  border-color:rgba(13,59,102,.18);
  background:linear-gradient(180deg, rgba(255,255,255,.96), rgba(239,246,250,.96));
}
.data-center-brief {
  display:grid;
  grid-template-columns:repeat(3,minmax(0,1fr));
  gap:10px;
  margin:12px 0;
}
.data-center-brief span,
.data-center-brief strong {
  border:1px solid var(--line);
  border-radius:14px;
  padding:10px 12px;
  background:#fff;
  color:var(--ink);
  font-size:13px;
  line-height:1.45;
}
.data-center-row.warn td { background:#fff9ed; }
.data-center-row.blocked td { background:#fff1ef; }
.data-center-alert-box {
  margin-top:12px;
  border:1px solid var(--line);
  border-radius:16px;
  padding:12px;
  background:#fff;
  color:var(--ink);
}
.data-center-alert-box.high {
  border-color:#e6aaa1;
  background:#fff3f0;
}
.data-center-alert-box strong { display:block; margin-bottom:6px; }
.data-center-alert-list {
  margin:0;
  padding-left:18px;
  color:var(--ink-soft);
  line-height:1.65;
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
@media (max-width:1080px) {
  .stock-data-block-grid,
  .stock-pro-grid,
  .stock-diagnosis-grid { grid-template-columns:repeat(2,minmax(0,1fr)); }
  .stock-pro-head,
  .stock-pro-bear,
  .stock-summary-lines { grid-template-columns:1fr; }
}
@media (max-width:680px) {
  .stock-data-block-grid,
  .stock-pro-grid,
  .stock-diagnosis-grid { grid-template-columns:1fr; }
}

"""
