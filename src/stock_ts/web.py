# ruff: noqa: E501
from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from html import escape
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from .analysis import analyze_candidates, analyze_stock
from .announcements import AnnouncementReport, fetch_cninfo_announcements
from .auth import AuthConfig, AuthUser, SessionManager, UserStore, is_auth_enabled
from .config import get_settings, save_dotenv_values
from .daily_decisions import read_decision_artifact
from .data_sources import build_data_source_matrix
from .deep_models import DeepStockReport
from .models import (
    CandidatePoolReport,
    CandidateStockRawData,
    Holding,
    MarketSnapshot,
    PortfolioAnalysisReport,
    PositionAnalysis,
    SectorAnalysisReport,
    StockRawData,
)
from .news import analyze_news
from .notification import dispatch_report
from .portfolio import delete_holding_csv, load_holdings_csv, upsert_holding_csv
from .portfolio_advice import PortfolioAdvice, PositionAdvice, build_portfolio_advice
from .professional_research import (
    EventRadar,
    TechnicalProfile,
    build_event_radar,
    build_technical_profile,
)
from .providers import create_provider
from .providers.base import StockDataProvider
from .research_playbook import DecisionDashboard
from .sector_labels import BOARD_LABELS, localize_sector_name
from .symbols import ResolvedSymbol, resolve_stock_query
from .trade_plan import TradePlan, build_trade_plan
from .webapp import (
    app_script as render_shell_script,
)
from .webapp import (
    build_workspace_sections,
    render_document,
    workspace_action,
)
from .webapp import (
    render_sidebar as render_shell_sidebar,
)
from .webapp.shell import (
    PUBLIC_SITE_DOMAIN,
    PUBLIC_SITE_LOGO,
    PUBLIC_SITE_NAME,
    PUBLIC_SITE_TAGLINE,
    WEB_DATA_PROVIDER,
)
from .workflows import DailyWorkflowResult, build_daily_report, build_deep_stock_report

DEFAULT_HOLDINGS_PATH = "data/portfolio/holdings.csv"
DEFAULT_USER_DATA_DIR = "data/auth/users"


CSS = """
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
html { scroll-behavior: smooth; }
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
.app-shell { display: grid; grid-template-columns: 282px minmax(0, 1fr); min-height: 100vh; }
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  padding: 28px 18px 18px;
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
.nav-group { display:grid; gap:8px; margin: 18px 0 28px; }
.nav-item {
  width:100%;
  border:1px solid transparent;
  text-align:left;
  cursor:pointer;
  padding: 12px 14px;
  border-radius: 16px;
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
  padding:16px;
  border:1px solid rgba(255,255,255,.08);
  background:rgba(255,255,255,.05);
  border-radius:18px;
  color:rgba(232,242,250,.74);
  font-size:13px;
  line-height:1.6;
}
.workspace { padding: 28px; overflow: hidden; }
.topbar {
  display:grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(360px, .95fr);
  gap:16px;
  align-items:stretch;
  margin-bottom: 18px;
}
.topbar-copy,
.desk-status {
  border:1px solid var(--line);
  background: var(--panel-glass);
  border-radius: 26px;
  box-shadow: var(--shadow);
}
.topbar-copy {
  padding: 24px 24px 22px;
  background:
    linear-gradient(135deg, rgba(180, 133, 58, .10), transparent 34%),
    linear-gradient(180deg, rgba(255,255,255,.80), rgba(248,251,253,.92));
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
  margin: 8px 0 8px;
  font-size: clamp(30px, 4.2vw, 48px);
  line-height: 1.02;
  letter-spacing:-.05em;
  font-family: var(--display);
}
.lead { max-width: 820px; color: var(--muted); line-height: 1.72; font-size: 15px; margin: 0; }
.desk-status {
  display:grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap:12px;
  padding: 18px;
}
.desk-status-card {
  border:1px solid var(--line);
  border-radius: 18px;
  padding: 14px;
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
  margin-top: 8px;
  font-size: 18px;
  font-weight: 800;
  color: var(--ink);
}
.desk-status-note {
  margin-top: 6px;
  color: var(--muted);
  font-size: 12px;
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
  margin: 16px 0;
  border:1px solid var(--line);
  background:linear-gradient(180deg, rgba(255,255,255,.90), rgba(248,251,253,.90));
  border-radius:28px;
  padding:22px;
  box-shadow: var(--shadow);
}
.module-view { display:none; animation: reveal .24s ease both; }
.module-view.active { display:block; }
@keyframes reveal { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:translateY(0); } }
.module-header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom: 18px; }
.module-header-meta { display:flex; flex-wrap:wrap; justify-content:flex-end; gap:10px; }
.module-title { margin:0; font-size: 24px; letter-spacing:-.03em; font-family: var(--display); }
.module-desc { margin:6px 0 0; color:var(--muted); line-height:1.6; }
.kpi-grid { display:grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap:14px; }
.kpi-card { border:1px solid var(--line); background:linear-gradient(180deg, #ffffff, #f1f6fa); border-radius:22px; padding:17px; min-height: 118px; }
.kpi-label { color:var(--muted); font-size:13px; }
.kpi-value { margin-top:8px; font-size:30px; font-weight:900; letter-spacing:-.04em; font-family: var(--display); }
.kpi-foot { margin-top:8px; color:var(--muted); font-size:12px; line-height:1.4; }
.grid-2 { display:grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap:16px; }
.grid-3 { display:grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap:16px; }
.panel { border:1px solid var(--line); background:rgba(255,255,255,.80); border-radius:22px; padding:18px; }
.panel h3 { margin:0 0 14px; font-size:18px; font-family: var(--display); }
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
.data-table { width:100%; border-collapse:separate; border-spacing:0 9px; font-size:14px; }
.data-table th { text-align:left; color:var(--muted); font-size:12px; font-weight:800; padding:0 10px 2px; }
.data-table td { background:rgba(255,255,255,.86); border-top:1px solid var(--line); border-bottom:1px solid var(--line); padding:12px 10px; vertical-align:top; }
.data-table td:first-child { border-left:1px solid var(--line); border-radius:14px 0 0 14px; }
.data-table td:last-child { border-right:1px solid var(--line); border-radius:0 14px 14px 0; }
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
.stock-form { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; margin-bottom: 0; }
.stock-form input { flex:1; border:1px solid var(--line); border-radius:14px; padding:12px 14px; font-size:15px; background:#fff; }
.stock-form button { border:0; border-radius:14px; padding:12px 18px; color:white; background:linear-gradient(135deg,var(--brand),var(--brand-2)); font-weight:800; cursor:pointer; }
.app-toolbar {
  position:sticky;
  top:12px;
  z-index:10;
  display:grid;
  grid-template-columns: 1fr 1.05fr 1.25fr auto;
  gap:12px;
  align-items:end;
  margin:0 0 16px;
  padding:14px;
  border:1px solid var(--line);
  background:rgba(248,251,253,.84);
  backdrop-filter:blur(14px);
  border-radius:24px;
  box-shadow:0 16px 40px rgba(19,39,58,.08);
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
.toolbar-heading {
  grid-column: 1 / -1;
  display:flex;
  justify-content:space-between;
  align-items:center;
  gap:12px;
  margin-bottom: 2px;
}
.toolbar-heading strong {
  font-size: 15px;
  font-family: var(--display);
}
.toolbar-heading span {
  color: var(--muted);
  font-size: 12px;
}
.toolbar-session-note {
  grid-column: 1 / -1;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.toolbar-badge {
  display:inline-flex;
  align-items:center;
  gap:6px;
  border:1px solid var(--line);
  border-radius:999px;
  padding:7px 11px;
  background:#fff;
  color:var(--ink-soft);
  font-size:12px;
}
.desk-strip {
  display:grid;
  grid-template-columns: 1.25fr .95fr;
  gap:16px;
  margin: 0 0 18px;
}
.desk-strip-card {
  border:1px solid var(--line);
  border-radius:24px;
  background:rgba(255,255,255,.82);
  padding:18px;
  box-shadow:0 16px 40px rgba(19,39,58,.06);
}
.desk-strip-card h3 {
  margin:0 0 12px;
  font-size:18px;
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
  line-height:1.65;
  font-size:14px;
}
.desk-strip-actions {
  display:grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap:10px;
}
.desk-jump {
  border:1px solid rgba(13,59,102,.14);
  border-radius:18px;
  padding:14px;
  background:linear-gradient(180deg, #fff, #eef4f8);
  text-align:left;
  cursor:pointer;
  color:var(--ink);
}
.desk-jump strong {
  display:block;
  font-size:15px;
  margin-bottom:6px;
}
.desk-jump span {
  display:block;
  color:var(--muted);
  font-size:13px;
  line-height:1.5;
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
.action-card strong { display:block; font-size:16px; margin-bottom:8px; }
.workflow-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-top:16px; }
.workflow-card { border:1px solid rgba(13,59,102,.14); border-radius:22px; padding:17px; background:linear-gradient(180deg,#fff,#eef4f8); text-align:left; cursor:pointer; color:var(--ink); box-shadow:0 12px 34px rgba(19,39,58,.08); }
.workflow-card strong { display:block; font-size:17px; margin-bottom:8px; }
.workflow-card span { display:block; color:var(--muted); line-height:1.55; font-size:13px; }
.workflow-card:hover { transform:translateY(-2px); border-color:rgba(13,59,102,.34); transition:.18s ease; }
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
  border-radius:30px;
  padding:22px;
  background:
    linear-gradient(135deg, rgba(180,133,58,.18), transparent 34%),
    linear-gradient(135deg, #11263b, #173b59);
  color:#f3f8fc;
}
.action-desk-hero h3 { margin:0 0 12px; font-size:30px; letter-spacing:-.04em; font-family:var(--display); }
.action-desk-hero p { margin:0; max-width:720px; color:rgba(243,248,252,.78); line-height:1.7; }
.action-desk-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:18px; }
.action-desk-metric { border:1px solid rgba(255,255,255,.16); border-radius:18px; padding:13px; background:rgba(255,255,255,.10); }
.action-desk-metric span { display:block; color:rgba(243,248,252,.64); font-size:12px; }
.action-desk-metric strong { display:block; margin-top:7px; font-size:18px; }
.action-lanes { display:grid; gap:10px; }
.action-lane { border:1px solid var(--line); border-radius:22px; padding:16px; background:rgba(255,255,255,.84); }
.action-lane strong { display:block; font-size:16px; margin-bottom:6px; }
.action-lane p { margin:0; color:var(--muted); line-height:1.55; font-size:13px; }
.portfolio-queue-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; }
.portfolio-queue-lane { border:1px solid var(--line); border-radius:22px; padding:15px; background:linear-gradient(180deg,#fff,#f0f6fa); min-height:160px; }
.portfolio-queue-lane h3 { margin:0 0 10px; font-size:16px; }
.queue-stock { border-top:1px dashed var(--line); padding:10px 0 0; margin-top:10px; }
.queue-stock strong { display:block; }
.queue-stock span { display:block; color:var(--muted); font-size:12px; margin-top:4px; line-height:1.45; }
.stock-workspace-drawer { display:grid; grid-template-columns:minmax(0,1.1fr) minmax(300px,.55fr); gap:16px; align-items:start; margin-top:16px; }
.evidence-drawer { position:sticky; top:16px; border:1px solid var(--line); border-radius:24px; padding:16px; background:linear-gradient(180deg,#fff,#edf4f8); box-shadow:0 16px 40px rgba(19,39,58,.08); }
.evidence-drawer h3 { margin:0 0 12px; font-size:18px; font-family:var(--display); }
.drawer-row { border-top:1px dashed var(--line); padding:11px 0; }
.drawer-row:first-of-type { border-top:0; padding-top:0; }
.drawer-row span { display:block; color:var(--muted); font-size:12px; margin-bottom:4px; }
.drawer-row strong { display:block; line-height:1.45; }
.today-list { display:grid; gap:10px; counter-reset: today; }
.today-item { display:grid; grid-template-columns:34px minmax(0,1fr) auto; gap:10px; align-items:center; border:1px solid var(--line); border-radius:18px; padding:12px; background:rgba(255,255,255,.76); }
.today-item:before { counter-increment: today; content:counter(today); width:34px; height:34px; border-radius:12px; display:grid; place-items:center; background:#17344d; color:#edf5fb; font-weight:900; font-family: var(--mono); }
.today-item strong { display:block; }
.today-item span { color:var(--muted); font-size:13px; }
.mini-button { border:1px solid rgba(13,59,102,.16); border-radius:999px; padding:8px 11px; background:rgba(255,255,255,.72); color:#16426b; font-weight:800; cursor:pointer; }
.current-module-indicator { display:flex; justify-content:space-between; align-items:center; gap:10px; margin:-4px 0 14px; padding:10px 14px; border:1px solid var(--line); border-radius:18px; background:rgba(255,255,255,.64); color:var(--muted); font-size:13px; }
.current-module-indicator strong { color:var(--brand); }
.inline-form { margin:0; }
.portfolio-form-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:12px; }
.field-stack { display:grid; gap:6px; color:var(--muted); font-size:12px; font-weight:800; }
.field-stack input,
.field-stack select { width:100%; border:1px solid var(--line); background:#fff; color:var(--ink); border-radius:14px; padding:10px 12px; font-size:14px; }
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
.portfolio-shell { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(320px,.95fr); gap:16px; align-items:start; }
.portfolio-shell .panel { height:100%; }
.portfolio-editor { position:sticky; top:92px; }
.portfolio-kpis { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:14px; margin-bottom:16px; }
.compact-table td, .compact-table th { white-space:nowrap; }
.compact-table td:nth-child(1) { white-space:normal; }
.editor-toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; }
.section-subtitle { margin:0; color:var(--muted); font-size:13px; line-height:1.55; }
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
  border-radius:20px;
  padding:16px;
  background:linear-gradient(180deg,#fff,#f3f7fa);
}
.summary-card span {
  display:block;
  color:var(--muted);
  font-size:12px;
  margin-bottom:8px;
}
.summary-card strong {
  display:block;
  font-size:18px;
  margin-bottom:6px;
}
.compact-note-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.compact-note-card {
  border:1px solid var(--line);
  border-radius:18px;
  padding:14px;
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
  border-radius:18px;
  padding:14px;
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
.split-focus {
  display:grid;
  grid-template-columns:minmax(0,1.1fr) minmax(280px,.9fr);
  gap:16px;
  align-items:start;
}
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at 20% 0%, rgba(180, 133, 58, .18), transparent 30%),
    linear-gradient(135deg, #102033, #18344e);
}
.login-card {
  width: min(440px, 100%);
  padding: 30px;
  border-radius: 28px;
  background: rgba(248, 251, 253, .96);
  border: 1px solid rgba(255,255,255,.36);
  box-shadow: 0 30px 80px rgba(7, 21, 35, .28);
}
.login-card h1 { margin:0 0 8px; font-family:var(--display); font-size:30px; }
.login-card p { color:var(--muted); margin:0 0 22px; line-height:1.65; }
.login-form { display:grid; gap:14px; }
.login-form label { display:grid; gap:7px; color:var(--muted); font-size:13px; font-weight:800; }
.login-form input {
  width:100%;
  border:1px solid var(--line);
  border-radius:14px;
  padding:12px 13px;
  background:#fff;
  color:var(--ink);
}
.login-form button {
  border:0;
  border-radius:14px;
  padding:13px 16px;
  color:#fff;
  background:linear-gradient(135deg,var(--brand),var(--brand-2));
  font-weight:900;
  cursor:pointer;
}
.login-error {
  border:1px solid rgba(180,72,61,.20);
  background:#fff4f2;
  color:var(--red);
  border-radius:14px;
  padding:10px 12px;
  margin-bottom:14px;
  font-weight:800;
}
.login-foot { margin-top:18px; font-size:12px; color:var(--muted); }
@media (max-width: 1280px) {
  .topbar,
  .desk-strip,
  .stock-workspace,
  .stock-workspace-drawer,
  .action-desk,
  .command-deck,
  .portfolio-shell { grid-template-columns: 1fr; }
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
  .action-desk-grid,
  .portfolio-queue-grid,
  .split-focus,
  .desk-strip-actions,
  .portfolio-control-grid { grid-template-columns: 1fr; }
  .evidence-drawer { position:static; }
  .command-summary { max-width:100%; }
  .field-span-2 { grid-column: span 1; }
  .portfolio-editor { position:static; }
  .desk-status { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 680px) {
  .workspace { padding:18px; }
  .nav-group { grid-template-columns: 1fr; }
  .kpi-grid,
  .desk-status { grid-template-columns: 1fr; }
  .data-table { font-size:12px; }
}
@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  .module-view,
  .workflow-card:hover { animation:none; transform:none; transition:none; }
}
"""


@dataclass(frozen=True)
class DataQualityView:
    status: str
    warnings: list[str]
    latest_date: str
    market_date: str
    requested_provider: str
    actual_provider: str
    candidate_price_reliable: bool
    candidate_universe_reliable: bool
    gate_level: str
    signal: str
    summary: str
    blocked_actions: list[str]


@dataclass(frozen=True)
class RiskGateView:
    gate: str
    level: str
    market_risk: str
    limit_down_risk: str
    data_risk: str
    event_risk: str
    portfolio_risk: str
    reason: str


@dataclass(frozen=True)
class PortfolioNotice:
    level: str
    message: str


@dataclass(frozen=True)
class SettingsNotice:
    level: str
    message: str


AnnouncementFetcher = Callable[..., AnnouncementReport]


def render_page(
    stock_code: str = "",
    holdings_path: str = "data/portfolio/holdings.csv",
    provider_name: str = "sample",
    provider: StockDataProvider | None = None,
    announcement_fetcher: AnnouncementFetcher | None = None,
    portfolio_notice: PortfolioNotice | None = None,
    settings_notice: SettingsNotice | None = None,
    edit_code: str = "",
    candidate_code: str = "",
    candidate_group: str = "all",
    candidate_strategy: str = "all",
    current_user: AuthUser | None = None,
) -> str:
    try:
        active_provider = provider or create_provider(provider_name)
        selected_stock_code = _default_stock_query(stock_code, holdings_path)
        resolved = resolve_stock_query(selected_stock_code)
        stock_raw = active_provider.fetch_stock(resolved.code)
        stock_report = analyze_stock(stock_raw)
        technical = build_technical_profile(stock_raw)
        daily = build_daily_report(
            active_provider,
            holdings_path=holdings_path,
            candidate_limit=20,
            provider_name=provider_name,
            allow_empty_portfolio=True,
        )
        stock = build_deep_stock_report(
            active_provider,
            resolved.code,
            market=daily.market,
            sectors=daily.sectors,
            portfolio=daily.portfolio,
            stock=stock_report,
            news=analyze_news(stock_raw.news_items, trade_date=daily.market.trade_date)
            if stock_raw.news_items
            else None,
        )
    except Exception as exc:
        return render_error_page(str(exc), provider_name=provider_name)

    market = daily.market
    sectors = daily.sectors
    candidates = daily.candidates
    portfolio = daily.portfolio
    if portfolio is None:
        return render_error_page(
            "未生成持仓分析，请检查 holdings 参数", provider_name=provider_name
        )
    candidate_universe = _safe_fetch_candidate_universe(active_provider)
    candidate_universe_metadata = _safe_fetch_candidate_universe_metadata(active_provider)
    screener_candidates = _build_screener_candidate_report(
        candidates,
        candidate_universe=candidate_universe,
        sectors=sectors,
        market=market,
        metadata=candidate_universe_metadata,
    )
    provider_class = active_provider.__class__.__name__
    quality = _assess_data_quality(
        requested_provider=provider_name,
        actual_provider=provider_class,
        resolved=resolved,
        stock=stock,
        market=market,
        candidates=candidates,
        candidate_universe=candidate_universe,
    )
    announcement_report = _safe_fetch_announcements(
        resolved.code,
        announcement_fetcher=announcement_fetcher,
    )
    event_radar = build_event_radar(announcement_report)
    risk_gate = _build_risk_gate(
        quality=quality,
        market=market,
        event_radar=event_radar,
        portfolio=portfolio,
    )
    daily_decisions = _read_latest_daily_decisions()
    trade_plan = build_trade_plan(
        stock_name=stock.name,
        latest_close=stock.latest_close,
        upside_score=stock.upside.score,
        risk_level=stock.risk_level,
        trend=stock.trend,
        technical=technical,
        event_radar=event_radar,
        data_quality_warnings=_trade_blocking_warnings(quality.warnings),
    )
    section_map = {
        "home": _render_home_module(
            quality=quality,
            market=market,
            sectors=sectors,
            portfolio=portfolio,
            candidates=candidates,
            risk_gate=risk_gate,
            provider_name=provider_name,
            holdings_path=holdings_path,
            daily_decisions=daily_decisions,
        ),
        "market": _render_compact_market_module(market, sectors, portfolio, candidates),
        "sector": _retitle_module(
            _render_compact_sector_module(sectors, candidate_universe),
            old_id="module-sectors",
            new_id="module-sector",
        ),
        "sentiment": _render_sentiment_module(candidate_universe, market, provider_class),
        "screener": _retitle_module(
            _render_candidates_module(
                screener_candidates,
                stock_code=resolved.query,
                provider_name=provider_name,
                holdings_path=holdings_path,
                candidate_code=candidate_code,
                candidate_group=candidate_group,
                candidate_strategy=candidate_strategy,
                candidate_universe_count=len(candidate_universe),
                candidate_universe_metadata=candidate_universe_metadata,
            ),
            old_id="module-smart-select",
            new_id="module-screener",
        ),
        "portfolio": _render_compact_portfolio_module(
            portfolio,
            market,
            holdings_path,
            resolved.query,
            provider_name,
            portfolio_notice,
            edit_code,
        ),
        "stock": _render_compact_stock_module(
            stock,
            resolved,
            portfolio,
            quality,
            technical,
            event_radar,
            announcement_report,
            trade_plan,
            stock_raw,
            sectors,
            candidates,
            provider_name=provider_name,
            holdings_path=holdings_path,
        ),
        "watchlist": _render_watchlist_module(stock),
        "daily": _retitle_module(
            _render_compact_report_module(daily, quality, risk_gate),
            old_id="module-report",
            new_id="module-daily",
        ),
        "notify": _retitle_module(
            _render_compact_status_module(
                provider_name,
                holdings_path,
                provider_class,
                resolved.query,
                settings_notice,
            ).replace("消息渠道", "消息自动化"),
            old_id="module-status",
            new_id="module-notify",
        ),
        "settings": _render_system_settings_module(
            quality,
            provider_name,
            provider_class,
            current_user=current_user,
            holdings_path=holdings_path,
        ),
    }
    shell = f"""
  <div class="app-shell">
      {render_shell_sidebar(resolved.query, holdings_path)}
    <main class="workspace">
      {_render_global_freshness_bar(quality, market, provider_class, risk_gate)}
      {build_workspace_sections(section_map)}
    </main>
  </div>
  {render_shell_script()}
"""
    return render_document(shell)


def _render_sidebar() -> str:
    items = [
        ("今日工作台", "module-overview", "起点"),
        ("重点结论", "module-command", "结论"),
        ("执行计划", "module-framework", "动作"),
        ("证据清单", "module-decision", "证据"),
        ("大盘分析", "module-market", "市场"),
        ("板块情况", "module-sectors", "主线"),
        ("持仓工作台", "module-portfolio", "组合"),
        ("候选标的池", "module-candidates", "候选"),
        ("个股工作台", "module-stock", "执行"),
        ("数据质量", "module-data-quality", "校验"),
        ("研究归档", "module-report", "归档"),
        ("系统状态", "module-status", "系统"),
    ]
    nav = "".join(
        f'<button class="nav-item" type="button" data-view="{anchor.removeprefix("module-")}">{label}<span>{number}</span></button>'
        for label, anchor, number in items
    )
    return f"""
    <aside class="sidebar">
      <div class="brand-mark"><div class="logo">{PUBLIC_SITE_LOGO}</div><div><div class="brand-title">{PUBLIC_SITE_NAME}</div><div class="brand-subtitle">{PUBLIC_SITE_TAGLINE}</div></div></div>
      <nav class="nav-group">{nav}</nav>
      <div class="sidebar-note">候选股票池用于研究排序与盘前准备；执行前仍需结合成交、板块延续与风险预算复核。</div>
    </aside>"""


def _next_action_for_dashboard(
    dashboard: DecisionDashboard,
    event_radar: EventRadar,
    quality: DataQualityView,
) -> str:
    if quality.warnings:
        return "先处理数据质量告警，再把结论用于复盘。"
    if event_radar.gate == "事件需复核":
        return "先打开公告原文复核事件风险，再判断技术信号是否有效。"
    if dashboard.confidence_score >= 70:
        return "进入盘中承接验证，确认量能、板块和指数是否共振。"
    return "保持观察，等待更高置信度或更清晰的风险收益结构。"


def _kpi(label: str, value: str, foot: str) -> str:
    return f'<div class="kpi-card"><div class="kpi-label">{escape(label)}</div><div class="kpi-value">{escape(value)}</div><div class="kpi-foot">{escape(foot)}</div></div>'


def _details_block(title: str, body: str, *, open: bool = False, note: str = "") -> str:
    note_html = f'<span class="section-subtitle">{escape(note)}</span>' if note else ""
    open_attr = " open" if open else ""
    return f"""
    <details class="detail-shell"{open_attr}>
      <summary><span>{escape(title)}</span>{note_html}</summary>
      <div class="detail-body">{body}</div>
    </details>"""


@dataclass(frozen=True)
class LimitBoardRow:
    code: str
    name: str
    sector: str
    latest_close: float
    pct_change: float
    amount: float = 0.0
    turnover_rate: float = 0.0


def _safe_fetch_candidate_universe(provider: StockDataProvider) -> list[CandidateStockRawData]:
    try:
        return provider.fetch_candidate_universe()
    except Exception:
        return []


def _safe_fetch_candidate_universe_metadata(provider: StockDataProvider) -> dict[str, str]:
    fetcher = getattr(provider, "fetch_candidate_universe_metadata", None)
    if not callable(fetcher):
        return {}
    try:
        metadata = fetcher()
    except Exception:
        return {}
    if not isinstance(metadata, dict):
        return {}
    return {str(key): str(value) for key, value in metadata.items() if value not in {None, ""}}


def _build_screener_candidate_report(
    fallback: CandidatePoolReport,
    *,
    candidate_universe: list[CandidateStockRawData],
    sectors: SectorAnalysisReport,
    market: MarketSnapshot,
    metadata: dict[str, str],
) -> CandidatePoolReport:
    if not _use_full_scan_candidates_for_screener(fallback, candidate_universe, metadata):
        return fallback
    limit = min(max(len(candidate_universe), len(fallback.candidates)), 80)
    try:
        return analyze_candidates(candidate_universe, sectors, market, limit=limit)
    except Exception:
        return fallback


def _use_full_scan_candidates_for_screener(
    fallback: CandidatePoolReport,
    candidate_universe: list[CandidateStockRawData],
    metadata: dict[str, str],
) -> bool:
    if metadata.get("scope") != "all_a_share":
        return False
    if len(candidate_universe) <= len(fallback.candidates):
        return False
    returned = _positive_int_text(metadata.get("returned_count"))
    scanned = _positive_int_text(metadata.get("scanned_count"))
    return bool(returned or scanned)


def _build_limit_board_rows(universe: list[CandidateStockRawData]) -> list[LimitBoardRow]:
    rows: list[LimitBoardRow] = []
    for item in universe:
        if len(item.bars) < 2:
            continue
        previous = item.bars[-2].close
        latest = item.bars[-1].close
        if previous <= 0:
            continue
        pct = (latest - previous) / previous * 100
        rows.append(
            LimitBoardRow(
                code=item.code,
                name=item.name,
                sector=item.sector or "未分类",
                latest_close=latest,
                pct_change=round(pct, 2),
                amount=item.amount,
                turnover_rate=item.turnover_rate,
            )
        )
    return rows


def _format_limit_count(count: int, *, provider_class: str) -> str:
    if provider_class == "TencentProvider" and count == 0:
        return "未返回"
    return str(count)


def _limit_count_note(provider_class: str) -> str:
    if provider_class == "TencentProvider":
        return "当前 Tencent 源不返回全市场涨跌停统计。"
    return "来自市场快照。"


def _render_limit_up_leader_cards(items: list[LimitBoardRow]) -> str:
    if not items:
        return "<p class='module-desc'>当前还没有足够的强势样本，先观察主线和情绪是否继续升温。</p>"
    return "".join(
        f"<div class='stack-card'><strong>{escape(item.name)}（{escape(item.code)}）</strong><div class='metric-list'><div class='metric-line'><span>所属方向</span><strong>{escape(item.sector)}</strong></div><div class='metric-line'><span>最新价</span><strong>{item.latest_close:.2f}</strong></div><div class='metric-line'><span>日涨跌</span><strong>{item.pct_change:.2f}%</strong></div></div></div>"
        for item in items
    )


def _render_limit_distribution_chart(
    items: list[LimitBoardRow],
    *,
    tone: str,
) -> str:
    if not items:
        return "<p class='module-desc'>当前样本不足，先观察情绪统计是否开始明显扩散。</p>"
    max_pct = max(abs(item.pct_change) for item in items) or 1
    return "".join(
        _render_compare_row(
            label=item.name,
            value=item.pct_change,
            value_text=f"{item.pct_change:.2f}%",
            detail=f"{item.sector} · {item.latest_close:.2f}",
            scale=max_pct,
            tone=tone,
        )
        for item in items
    )


def _market_scenarios(market: MarketSnapshot) -> str:
    bull = "指数放量、涨跌家数比继续改善、强势板块有第二日延续。"
    base = f"维持 {market.regime}，按结构性机会处理，先看主线和承接。"
    bear = "跌停或亏钱效应扩散，市场热度跌破 45/100，降低候选池进攻优先级。"
    return "".join(
        f'<div class="scenario-item"><strong>{escape(label)}：</strong>{escape(text)}</div>'
        for label, text in [("乐观", bull), ("基准", base), ("防守", bear)]
    )


def _render_market_execution_steps(market: MarketSnapshot) -> str:
    top_opportunity = market.opportunities[0] if market.opportunities else "先观察主线和承接"
    if market.heat_score >= 75:
        first_step = "先确认市场允许进攻"
        first_note = "热度较高，但仍需要先看指数、成交额和主线是否同步。"
    elif market.heat_score >= 55:
        first_step = "先按均衡节奏做"
        first_note = "市场并不差，但不适合无条件追高，优先选择结构更强的方向。"
    else:
        first_step = "先防守再观察"
        first_note = "热度偏弱，先保护已有仓位，不急着扩大新风险。"
    return "".join(
        [
            f'<div class="ops-step"><div class="ops-step-index">1</div><div><strong>{escape(first_step)}</strong><p>{escape(first_note)}</p></div></div>',
            f'<div class="ops-step"><div class="ops-step-index">2</div><div><strong>再看主线与机会</strong><p>{escape(top_opportunity)}</p></div></div>',
            '<div class="ops-step"><div class="ops-step-index">3</div><div><strong>最后决定仓位节奏</strong><p>如果风险信号开始增多，宁可慢一点，也不要只因为单日上涨就追进去。</p></div></div>',
        ]
    )


def _render_market_risk_signals(market: MarketSnapshot) -> str:
    items = [
        ("市场热度", f"{market.heat_score}/100"),
        ("短线情绪", market.dimensions[2].status if len(market.dimensions) >= 3 else "待确认"),
        ("资金状态", market.dimensions[3].status if len(market.dimensions) >= 4 else "待确认"),
        ("板块强度", market.dimensions[4].status if len(market.dimensions) >= 5 else "待确认"),
    ]
    return "".join(
        f"<div class='metric-line'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in items
    )


def _render_index_comparison_chart(market: MarketSnapshot) -> str:
    if not market.indices:
        return (
            "<p class='module-desc'>当前没有指数数据，先确认数据源或切回样例模式查看页面。</p>"
        )
    max_pct = max(abs(item.pct_chg) for item in market.indices) or 1
    return "".join(
        _render_compare_row(
            label=item.name,
            value=item.pct_chg,
            value_text=f"{item.pct_chg:.2f}%",
            detail=f"{item.close:.2f} · {item.amount:.1f} 亿",
            scale=max_pct,
        )
        for item in market.indices[:6]
    )


def _sector_confirmation_cards(sectors: SectorAnalysisReport) -> str:
    cards = []
    for item in sectors.sectors[:3]:
        cards.append(
            f"""
            <div class="matrix-card">
              <h4>{escape(item.name)}</h4>
              <div class="metric-list">
                <div class="metric-line"><span>热度</span><strong>{item.heat_score}/100</strong></div>
                <div class="metric-line"><span>持续性</span><strong>{escape(item.continuity)}</strong></div>
                <div class="metric-line"><span>资金</span><strong>{escape(item.fund_status)}</strong></div>
                <div class="metric-line"><span>风险</span><strong>{escape(item.risk)}</strong></div>
              </div>
            </div>
            """
        )
    return "".join(cards)


def _render_sector_strategy_steps(
    sectors: SectorAnalysisReport,
    top_sector,
) -> str:
    top_name = top_sector.name if top_sector is not None else "当前暂无明确主线"
    top_note = top_sector.continuity if top_sector is not None else "先等待板块数据刷新"
    return "".join(
        [
            f'<div class="ops-step"><div class="ops-step-index">1</div><div><strong>先确认主线：{escape(top_name)}</strong><p>{escape(top_note)}</p></div></div>',
            '<div class="ops-step"><div class="ops-step-index">2</div><div><strong>再分辨前排和跟风</strong><p>前排看延续和资金，跟风只观察。</p></div></div>',
            '<div class="ops-step"><div class="ops-step-index">3</div><div><strong>最后决定是否跟随</strong><p>分歧增多时，不因涨幅好看就追。</p></div></div>',
        ]
    )


def _render_sector_watch_cards(sectors: SectorAnalysisReport) -> str:
    items = sectors.sectors[:3]
    if not items:
        return "<p class='module-desc'>当前没有可用板块数据，先回到大盘确认整体环境。</p>"
    return "".join(
        f"<div class='stack-card'><strong>{escape(item.name)}</strong><div class='metric-list'><div class='metric-line'><span>热度</span><strong>{item.heat_score}/100</strong></div><div class='metric-line'><span>持续性</span><strong>{escape(item.continuity)}</strong></div><div class='metric-line'><span>资金状态</span><strong>{escape(item.fund_status)}</strong></div></div><p class='kpi-foot' style='margin-top:10px'>{escape(item.rotation_status)}</p></div>"
        for item in items
    )


def _render_sector_heat_chart(sectors: SectorAnalysisReport) -> str:
    if not sectors.sectors:
        return "<p class='module-desc'>当前没有板块数据，先回到大盘确认整体环境。</p>"
    return "".join(
        _render_compare_row(
            label=item.name,
            value=float(item.heat_score),
            value_text=f"{item.heat_score}/100",
            detail=f"{item.pct_chg:.2f}% · {item.continuity}",
            scale=100,
        )
        for item in sectors.sectors[:6]
    )


def _risk_pill(text: str) -> str:
    level = "low"
    if "高位" in text or "走弱" in text:
        level = "high"
    elif "缩量" in text or "风险" in text:
        level = "mid"
    return f'<span class="risk-pill {level}">{escape(text)}</span>'


def _render_add_holding_form(
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    position: PositionAnalysis | None,
    advice: PositionAdvice | None,
) -> str:
    code_value = position.holding.code if position else ""
    name_value = position.holding.name if position else ""
    shares_value = _format_form_number(position.holding.shares) if position else ""
    cost_price_value = _format_form_number(position.holding.cost_price) if position else ""
    sector_value = position.holding.sector if position else ""
    note_value = position.holding.note if position else ""
    button_text = "保存修改" if position else "保存持仓"
    hint = (
        f"当前建议：{advice.action}，目标仓位 {advice.target_weight}，止损 {advice.stop_loss:.2f}。"
        if advice is not None
        else "现价由数据源自动获取；保存后系统会自动刷新组合、成本、趋势和处理建议，盈亏也会同步更新。"
    )
    return f"""
      <form class="inline-form" method="post" action="/holdings">
        <input type="hidden" name="portfolio_action" value="upsert" />
        <input type="hidden" name="page_code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings_path" value="{escape(holdings_path)}" />
        <div class="portfolio-form-grid" style="margin-top:14px">
          <label class="field-stack">股票代码<input name="holding_code" value="{escape(code_value)}" placeholder="输入 6 位股票代码" required /></label>
          <label class="field-stack">股票名称<input name="holding_name" value="{escape(name_value)}" placeholder="输入股票简称" required /></label>
          <label class="field-stack">持股数量<input name="holding_shares" value="{escape(shares_value)}" placeholder="输入持股数量" required /></label>
          <label class="field-stack">成本价<input name="holding_cost_price" value="{escape(cost_price_value)}" placeholder="手动输入持仓成本价" required /></label>
          <label class="field-stack">所属行业<input name="holding_sector" value="{escape(sector_value)}" placeholder="输入行业分类" /></label>
          <label class="field-stack field-span-2">备注<input name="holding_note" value="{escape(note_value)}" placeholder="输入仓位角色、交易假设或风险备注" /></label>
        </div>
        <div class="form-actions">
          <div class="form-hint">{escape(hint)}</div>
          <button class="primary-button" type="submit">{button_text}</button>
        </div>
      </form>"""


def _render_portfolio_new_button() -> str:
    return '<button class="portfolio-inline-button primary" type="button" data-action="add-holding" data-scroll="portfolio-form">添加持仓</button>'


def _render_portfolio_action_deck(
    *,
    portfolio: PortfolioAnalysisReport,
    advice: PortfolioAdvice,
    editing_position: PositionAnalysis | None,
) -> str:
    focus_advice = advice.position_advices[0] if advice.position_advices else None
    edit_text = (
        f"正在编辑 {editing_position.holding.name}，改完后直接保存即可刷新组合建议。"
        if editing_position
        else "先从持仓列表点“编辑”，或直接用下方表单新增一只股票。"
    )
    priority_text = (
        f"{focus_advice.name} 当前建议 {focus_advice.action}，优先确认仓位和价格触发线。"
        if focus_advice
        else "当前没有持仓建议，先录入持仓再开始组合分析。"
    )
    return "".join(
        [
            "<div class='action-card'><strong>新增入口</strong><p class='section-subtitle'>点击“添加持仓”后，录入代码、数量、成本和行业，系统会自动纳入组合分析。</p></div>",
            f"<div class='action-card'><strong>当前编辑</strong><p class='section-subtitle'>{escape(edit_text)}</p></div>",
            f"<div class='action-card'><strong>优先处理</strong><p class='section-subtitle'>{escape(priority_text)} 当前持仓共 {len(portfolio.positions)} 只。</p></div>",
        ]
    )


def _portfolio_ui_add_steps(advice: PortfolioAdvice) -> str:
    steps = [
        "先录入股票代码、名称、数量和成本价，再补充行业与备注。",
        "新增后系统会自动把它纳入组合风险、趋势和调仓建议。",
    ]
    if advice.position_advices:
        steps.append("保存后先看调仓计划和持仓处理队列，确认这只股票在组合里的优先级。")
    return _li_join(steps)


def _render_portfolio_table_row(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    readonly: bool = False,
) -> str:
    action = advice.action if advice else "观察"
    next_check = advice.next_check if advice else "等待更多数据后再处理。"
    reason = advice.reason if advice else "先观察走势和市场匹配度。"
    trend = f"{position.trend} / {position.risk_level}"
    detail = f"{reason} 下一步：{next_check}"
    actions = _render_open_stock_form(position.holding.code, provider_name, holdings_path)
    if not readonly:
        actions += _render_edit_holding_form(
            position.holding.code,
            stock_code,
            provider_name,
            holdings_path,
        )
        actions += _render_delete_holding_form(
            position.holding.code,
            stock_code,
            provider_name,
            holdings_path,
        )
    return (
        f"<tr><td class='name-cell'><strong>{escape(position.holding.name)}</strong><span>{escape(position.holding.code)} · {escape(position.holding.sector or '未分类')}</span></td>"
        f"<td>{_format_form_number(position.holding.shares)}</td>"
        f"<td>{position.holding.cost_price:.2f}</td>"
        f"<td>{position.latest_price:.2f}</td>"
        f"<td><strong>{position.daily_pnl:.2f}</strong><span>{position.daily_pnl_ratio:.2f}%</span></td>"
        f"<td><strong>{position.pnl:.2f}</strong><span>{position.pnl_ratio:.2f}%</span></td>"
        f"<td>{position.weight:.1%}</td>"
        f"<td>{escape(trend)}</td>"
        f"<td><div class='table-note'>{_risk_pill(action)}<span>{escape(detail)}</span></div></td>"
        f"<td class='action-cell'>{actions}</td></tr>"
    )


def _render_portfolio_priority_queue(
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
) -> str:
    lanes = [
        ("必须先处理", "风险仓不补仓；先看止损、减仓和公告风险。", []),
        ("保护利润", "盈利但走弱时，先保利润，不扩大风险。", []),
        ("修复观察", "亏损但趋势改善时，只等放量修复确认。", []),
        ("继续持有", "趋势和风险都正常时，按条件持有跟踪。", []),
    ]
    lane_by_name = {name: items for name, _note, items in lanes}
    for position in portfolio.positions:
        if position.risk_level == "高" or (
            position.pnl < 0 and (position.trend == "下降趋势" or position.risk_level == "中")
        ):
            lane_by_name["必须先处理"].append(position)
        elif position.pnl >= 0 and (position.trend == "下降趋势" or position.risk_level in {"高", "中"}):
            lane_by_name["保护利润"].append(position)
        elif position.pnl < 0 and position.trend == "上升趋势":
            lane_by_name["修复观察"].append(position)
        else:
            lane_by_name["继续持有"].append(position)
    lane_html = "".join(
        _render_portfolio_priority_lane(name, note, items, advice_by_code)
        for name, note, items in lanes
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>持仓处理队列</h3><p class="section-subtitle">按今天先处理什么排序，不按股票代码排序。</p></div></div>
        <div class="portfolio-queue-grid">{lane_html}</div>
      </div>"""


def _render_portfolio_priority_lane(
    name: str,
    note: str,
    positions: list[PositionAnalysis],
    advice_by_code: dict[str, PositionAdvice],
) -> str:
    rows = "".join(
        _render_portfolio_priority_stock(position, advice_by_code.get(position.holding.code))
        for position in sorted(positions, key=lambda item: (item.risk_level != "高", -item.weight))[:4]
    )
    if not rows:
        rows = "<div class='queue-stock'><strong>暂无</strong><span>今天没有进入这一类的持仓。</span></div>"
    return f"""
      <div class="portfolio-queue-lane">
        <h3>{escape(name)}</h3>
        <p class="kpi-foot">{escape(note)}</p>
        {rows}
      </div>"""


def _render_portfolio_priority_stock(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
) -> str:
    action = advice.action if advice else "观察"
    trigger = advice.next_check if advice else "等待趋势和风险变化。"
    return f"""
      <div class="queue-stock">
        <strong>{escape(position.holding.name)}</strong>
        <span>{escape(position.holding.code)} · 仓位 {position.weight:.1%} · 盈亏 {position.pnl_ratio:.2f}%</span>
        <span>动作：{escape(action)}；触发：{escape(trigger)}</span>
      </div>"""


def _render_portfolio_queue_card(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    market: MarketSnapshot,
) -> str:
    action = advice.action if advice else "观察"
    next_check = advice.next_check if advice else "等待更多数据后再处理。"
    future_view = _portfolio_future_view(position, market)
    return (
        "<div class='stack-card'>"
        f"<strong>{escape(position.holding.name)}（{escape(position.holding.code)}）</strong>"
        f"<div class='metric-list'>"
        f"<div class='metric-line'><span>当前动作</span><strong>{escape(action)}</strong></div>"
        f"<div class='metric-line'><span>持仓成本</span><strong>{position.holding.cost_price:.2f}</strong></div>"
        f"<div class='metric-line'><span>最新价格</span><strong>{position.latest_price:.2f}</strong></div>"
        f"<div class='metric-line'><span>当日盈亏</span><strong>{position.daily_pnl:.2f}</strong></div>"
        f"<div class='metric-line'><span>总盈亏</span><strong>{position.pnl:.2f}</strong></div>"
        f"<div class='metric-line'><span>仓位占比</span><strong>{position.weight:.1%}</strong></div>"
        "</div>"
        f"<p class='kpi-foot' style='margin-top:10px'>{escape(future_view)}</p>"
        f"<p class='module-desc' style='margin-top:8px'>{escape(next_check)}</p>"
        "</div>"
    )


def _render_edit_holding_form(
    holding_code: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-portfolio")}" style="display:inline-flex;margin-right:8px">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <input type="hidden" name="edit" value="{escape(holding_code)}" />
        <button class="ghost-button" type="submit">编辑</button>
      </form>"""


def _render_delete_holding_form(
    holding_code: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    return f"""
      <form class="inline-form" method="post" action="/holdings" style="display:inline-flex" onsubmit="return window.confirm('确认删除这条持仓记录？')">
        <input type="hidden" name="portfolio_action" value="delete" />
        <input type="hidden" name="page_code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings_path" value="{escape(holdings_path)}" />
        <input type="hidden" name="holding_code" value="{escape(holding_code)}" />
        <button class="danger-button" type="submit">删除</button>
      </form>"""


def _render_open_stock_form(
    holding_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("module-stock")}" style="display:inline-flex;margin-right:8px">
        <input type="hidden" name="code" value="{escape(holding_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <button class="ghost-button" type="submit">个股分析</button>
      </form>"""


def _render_clear_edit_link(
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    edit_code: str,
) -> str:
    if not edit_code:
        return ""
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-portfolio")}">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <button class="ghost-button" type="submit">结束编辑</button>
      </form>"""


def _render_portfolio_notice(notice: PortfolioNotice | None) -> str:
    if notice is None or not notice.message:
        return ""
    level = "success" if notice.level == "success" else "error"
    return f'<div class="notice-banner {level}">{escape(notice.message)}</div>'


def _render_settings_notice(notice: SettingsNotice | None) -> str:
    if notice is None or not notice.message:
        return ""
    level = "success" if notice.level == "success" else "error"
    return f'<div class="notice-banner {level}">{escape(notice.message)}</div>'


def _render_cost_breakdown_items(positions: list[PositionAnalysis]) -> str:
    items = []
    underwater = [item for item in positions if item.pnl < 0]
    if underwater:
        names = "、".join(item.holding.name for item in underwater[:3])
        items.append(f"当前浮亏持仓：{names}，优先核对原始买入逻辑是否仍成立。")
    winners = [item for item in positions if item.pnl_ratio >= 15]
    if winners:
        names = "、".join(item.holding.name for item in winners[:3])
        items.append(f"盈利保护对象：{names}，适合用止盈观察和仓位回收控制回撤。")
    high_cost = [item for item in positions if item.latest_price < item.holding.cost_price * 0.92]
    if high_cost:
        names = "、".join(item.holding.name for item in high_cost[:3])
        items.append(f"成本压力较大的持仓：{names}，已明显弱于成本区，避免继续被动摊薄。")
    items.append("成本分析不只看盈亏，还要结合仓位大小、趋势方向和市场环境决定处理顺序。")
    return _li_join(items)


def _portfolio_cost_view(position: PositionAnalysis) -> str:
    if position.latest_price >= position.holding.cost_price * 1.08:
        return "明显高于成本，可优先保护利润"
    if position.latest_price >= position.holding.cost_price:
        return "略高于成本，适合跟踪趋势延续"
    if position.latest_price >= position.holding.cost_price * 0.95:
        return "接近成本线，重点看承接和量能"
    return "明显低于成本，先判断是否需要降风险"


def _portfolio_future_view(position: PositionAnalysis, market: MarketSnapshot) -> str:
    if position.trend == "上升趋势" and market.heat_score >= 60:
        return "若主线延续，可继续上看并滚动抬高止损"
    if position.trend == "下降趋势":
        return "弱势未扭转前，以防守和减仓优先"
    if position.risk_level == "高":
        return "波动较大，等待结构重新稳定后再判断"
    return "偏震荡，按计划等待突破或失效信号"


def _select_edit_position(
    positions: list[PositionAnalysis], edit_code: str
) -> PositionAnalysis | None:
    normalized = edit_code.strip()
    if not normalized:
        return None
    return next((item for item in positions if item.holding.code == normalized), None)


def _format_form_number(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _render_candidates_module(
    candidates: CandidatePoolReport,
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    candidate_group: str,
    candidate_strategy: str,
    candidate_universe_count: int | None = None,
    candidate_universe_metadata: dict[str, str] | None = None,
) -> str:
    universe_count = candidate_universe_count or len(candidates.candidates)
    metadata = candidate_universe_metadata or {}
    if not candidates.price_reliable:
        observation_rows = "".join(
            _render_candidate_observation_row(
                item,
                index=index,
                provider_name=provider_name,
                holdings_path=holdings_path,
            )
            for index, item in enumerate(candidates.candidates[:10], start=1)
        )
        observation_table = (
            f'<table class="data-table candidates-table"><thead><tr><th>#</th><th>股票</th><th>方向</th><th>观察依据</th><th>操作</th></tr></thead><tbody>{observation_rows}</tbody></table>'
            if observation_rows
            else "<div class='empty-state'><strong>暂无候选</strong></div>"
        )
        return f"""
    <section class="module" id="module-smart-select">
      <div class="module-header"><div><h2 class="module-title">智能选股</h2></div><div class="module-header-meta"><span class="status-pill">候选 {len(candidates.candidates)} 只</span></div></div>
      {_render_candidate_pool_status(candidates, universe_count=universe_count, metadata=metadata)}
      <div class="panel" style="margin-bottom:16px">
        <div class="editor-toolbar">
          <div><h3>筛选</h3></div>
          <button class="portfolio-inline-button" type="button" data-action="filter-candidates" disabled>等待数据刷新</button>
        </div>
      </div>
      <div class="panel" style="margin-bottom:16px">
        <div class="editor-toolbar">
          <div><h3>候选观察名单</h3></div>
          <div class="portfolio-list-meta"><span class="portfolio-chip">仅观察，不排序</span><span class="portfolio-chip">不展示评分/涨跌幅</span></div>
        </div>
        {observation_table}
      </div>
      {_candidate_accuracy_pause()}
    </section>"""


    group_key = _normalize_candidate_group(candidate_group)
    strategy_key = _normalize_candidate_strategy(candidate_strategy)
    strategy_candidates = _filter_candidates_by_strategy(candidates.candidates, strategy_key)
    filtered_candidates = _filter_candidates_by_group(strategy_candidates, group_key)
    display_candidates = filtered_candidates[:10]
    focus = _select_candidate(candidates, candidate_code)
    filtered_count = len(filtered_candidates)
    group_label = _candidate_group_label(group_key)
    rows = "".join(
        _render_candidate_list_row(
            item,
            index=index,
            stock_code=stock_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
        )
        for index, item in enumerate(display_candidates, start=1)
    )
    filter_tabs = _render_candidate_filter_tabs(
        stock_code=stock_code,
        provider_name=provider_name,
        holdings_path=holdings_path,
        candidate_code=candidate_code,
        active_group=group_key,
        active_strategy=strategy_key,
    )
    strategy_tabs = _render_candidate_strategy_tabs(
        stock_code=stock_code,
        provider_name=provider_name,
        holdings_path=holdings_path,
        candidate_code=candidate_code,
        active_group=group_key,
        active_strategy=strategy_key,
    )
    candidate_table_html = (
        f'<table class="data-table candidates-table"><thead><tr><th>#</th><th>股票</th><th>分数</th><th>方向</th><th>涨跌</th><th>入选理由</th><th>风险提醒</th><th>验证条件</th><th>操作</th></tr></thead><tbody>{rows}</tbody></table>'
        if rows
        else "<div class='empty-state'><strong>暂无数据</strong></div>"
    )
    focus_panel = _render_candidate_focus_panel(
        focus,
        stock_code=stock_code,
        provider_name=provider_name,
        holdings_path=holdings_path,
    )
    return f"""
    <section class="module" id="module-smart-select">
      <div class="module-header"><div><h2 class="module-title">智能选股</h2></div><div class="module-header-meta"><span class="status-pill">候选 {len(candidates.candidates)} 只</span></div></div>
      {_render_candidate_pool_status(candidates, universe_count=universe_count, metadata=metadata)}
      {_render_candidate_strategy_map(candidates.candidates)}
      <div class="panel" style="margin-bottom:16px">
        <div class="editor-toolbar">
          <div><h3>策略筛选</h3></div>
          <div class="portfolio-list-meta"><span class="portfolio-chip">当前策略：{escape(_candidate_strategy_label(strategy_key))}</span><span class="portfolio-chip">显示 {min(filtered_count, 10)} / {filtered_count}</span></div>
        </div>
        <div class="summary-grid" style="margin-bottom:12px">
          <div class="summary-card"><span>当前策略</span><strong>{escape(_candidate_strategy_label(strategy_key))}</strong></div>
          <div class="summary-card"><span>策略命中</span><strong>{filtered_count} 只</strong></div>
          <div class="summary-card"><span>优先级</span><strong>{escape(group_label)}</strong></div>
        </div>
        <div class="portfolio-action-bar">{strategy_tabs}</div>
        <div class="portfolio-action-bar">{filter_tabs}</div>
      </div>
      <div class="panel">
        <div class="editor-toolbar">
          <div><h3>候选观察名单</h3></div>
          <div class="portfolio-list-meta"><span class="portfolio-chip">按评分</span></div>
        </div>
        {candidate_table_html}
      </div>
      {focus_panel}
    </section>"""


def _render_candidate_pool_status(
    candidates: CandidatePoolReport,
    *,
    universe_count: int,
    metadata: dict[str, str] | None = None,
) -> str:
    metadata = metadata or {}
    top = candidates.candidates[0] if candidates.candidates and candidates.price_reliable else None
    next_research = f"{top.name} · {top.code}" if top else "等待真实日线"
    scanned_count = _positive_int_text(metadata.get("scanned_count")) or str(universe_count)
    returned_count = _positive_int_text(metadata.get("returned_count")) or str(universe_count)
    enriched_count = _positive_int_text(metadata.get("enriched_count"))
    enriched_display = (
        f"{enriched_count} / {returned_count}" if enriched_count else f"0 / {returned_count}"
    )
    enrichment_method = (
        metadata.get("enrichment_method") or "未补真实日线/主题，当前为行情截面预筛。"
    )
    selection_method = metadata.get("selection_method") or "当前数据源候选快照排序。"
    theme_ready = sum(
        1
        for item in candidates.candidates
        if item.sector and item.sector not in {"未识别主题", "未分类"}
    )
    theme_coverage = f"{theme_ready}/{len(candidates.candidates)}"
    scanned_number = int(scanned_count) if scanned_count.isdigit() else universe_count
    coverage_state = "覆盖较完整" if scanned_number >= 1000 else "覆盖不足"
    coverage_note = (
        f"已扫描 {scanned_count} 只，当前快照 {universe_count} 只。"
        if scanned_number >= 1000
        else f"仅覆盖 {universe_count} 只；需要刷新更大的 TDX MCP 快照后才能代表全市场。"
    )
    return f"""
      <div class="panel" style="margin-bottom:16px">
        <h3>候选池状态</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>扫描范围</span><strong>全市场A股</strong><p class="kpi-foot">TDX MCP 分页行情；来源不是持仓。</p></div>
          <div class="summary-card"><span>当前快照覆盖</span><strong>{universe_count} 只</strong><p class="kpi-foot">全市场扫描 {escape(scanned_count)} 只。</p></div>
          <div class="summary-card"><span>预筛候选</span><strong>{escape(returned_count)} 只</strong><p class="kpi-foot">{escape(selection_method)}</p></div>
          <div class="summary-card"><span>深度补强</span><strong>{escape(enriched_display)}</strong><p class="kpi-foot">{escape(enrichment_method)}</p></div>
          <div class="summary-card"><span>覆盖完整性</span><strong>{escape(coverage_state)}</strong><p class="kpi-foot">{escape(coverage_note)}</p></div>
          <div class="summary-card"><span>主题覆盖</span><strong>{escape(theme_coverage)}</strong></div>
          <div class="summary-card"><span>候选状态</span><strong>{"候选可排序" if candidates.price_reliable else "排序暂停"}</strong><p class="kpi-foot">下一只：{escape(next_research)}</p></div>
        </div>
      </div>"""


def _positive_int_text(value: object) -> str:
    text = str(value or "").strip()
    return text if text.isdigit() and int(text) > 0 else ""


def _render_candidate_strategy_map(candidates: list) -> str:
    cards = "".join(
        _render_candidate_strategy_card(candidates, key=key, label=label, focus=focus)
        for key, label, focus in _candidate_strategy_definitions()
        if key != "all"
    )
    return f"""
      <div class="panel" style="margin-bottom:16px">
        <div class="editor-toolbar"><div><h3>策略地图</h3><p class="section-subtitle">把候选池按用途拆开看：先找主线机会，再排除风险票。</p></div></div>
        <div class="summary-grid">{cards}</div>
      </div>"""


def _render_candidate_strategy_card(
    candidates: list,
    *,
    key: str,
    label: str,
    focus: str,
) -> str:
    items = _filter_candidates_by_strategy(candidates, key)
    top = items[0] if items else None
    top_text = f"{top.name} · {top.code}" if top else "暂无命中"
    detail = _candidate_strategy_detail(top, key) if top else "当前候选池没有匹配标的"
    return f"""
      <div class="summary-card">
        <span>{escape(label)}</span>
        <strong>{escape(top_text)}</strong>
        <p class="kpi-foot">{escape(focus)} · 命中 {len(items)} 只</p>
        <p class="kpi-foot">{escape(detail)}</p>
      </div>"""


def _candidate_strategy_detail(candidate, strategy: str) -> str:
    if strategy == "risk":
        return candidate.risks[0] if candidate.risks else "高风险先排除，再看是否值得下钻"
    if strategy == "cluster":
        return f"{candidate.sector} 方向出现多只候选，先看板块持续性"
    if strategy == "hot":
        return f"日涨跌 {candidate.pct_change:.2f}%，先看热度是否有成交承接"
    if strategy == "rebound":
        return f"日涨跌 {candidate.pct_change:.2f}%，只做反弹观察，不追确认前买点"
    if strategy == "low_volume":
        return f"低位或温和涨幅 {candidate.pct_change:.2f}%，重点确认是否放量不放风险"
    if strategy == "trend":
        return f"评分 {candidate.score}/100，趋势和涨跌共振时才进入下一步"
    if strategy == "quality":
        return "优先看估值、行业地位和财务质量；当前以风险少、评分稳做近似筛选"
    if strategy == "catalyst":
        return candidate.reasons[0] if candidate.reasons else "等待消息、公告或主题催化复核"
    if strategy == "pullback":
        return f"涨幅 {candidate.pct_change:.2f}%，只看强势股回踩后的二次确认"
    if strategy == "dividend":
        return "防守策略优先低波动、风险少和估值相对清晰方向"
    return candidate.reasons[0] if candidate.reasons else "等待验证条件"


def _render_candidate_list_row(
    item,
    *,
    index: int,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    reason = item.reasons[0] if item.reasons else "等待真实日线复核"
    risk = item.risks[0] if item.risks else "暂无明显风险"
    condition = item.watch_conditions[0] if item.watch_conditions else "等待次日确认"
    return (
        f"<tr><td>{index}</td><td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)} · {escape(item.sector)}</span></td>"
        f"<td><strong>{item.score}</strong></td><td>{escape(item.sector)}</td>"
        f"<td>{item.pct_change:.2f}%</td>"
        f"<td>{escape(reason)}</td>"
        f"<td>{escape(risk)}</td>"
        f"<td>{escape(condition)}</td>"
        f"<td class='action-cell'>{_render_candidate_research_link(item.code, provider_name, holdings_path)}</td></tr>"
    )


def _render_candidate_observation_row(
    item,
    *,
    index: int,
    provider_name: str,
    holdings_path: str,
) -> str:
    reason = item.reasons[0] if item.reasons else "等待真实日线复核"
    return (
        f"<tr><td>{index}</td><td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)}</span></td>"
        f"<td>{escape(item.sector)}</td><td>{escape(reason)}</td>"
        f"<td class='action-cell'>{_render_candidate_research_link(item.code, provider_name, holdings_path)}</td></tr>"
    )


def _candidate_accuracy_pause() -> str:
    return """
      <div class="quality-banner high">
        候选池缺少真实日线，已暂停排序、评分和涨跌幅展示。请刷新 TDX MCP 快照后再使用。
      </div>"""


def _render_compare_row(
    *,
    label: str,
    value: float,
    value_text: str,
    detail: str,
    scale: float,
    tone: str | None = None,
) -> str:
    width = max(8.0, min(abs(value) / max(scale, 1) * 100, 100))
    fill_tone = tone or ("negative" if value < 0 else "positive")
    return (
        "<div class='compare-row'>"
        f"<div class='compare-copy'><strong>{escape(label)}</strong><span>{escape(detail)}</span></div>"
        f"<div class='compare-track'><div class='compare-fill {escape(fill_tone)}' style='width:{width:.1f}%'></div></div>"
        f"<div class='compare-value'>{escape(value_text)}</div>"
        "</div>"
    )


def _render_candidate_focus_panel(
    candidate,
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    if candidate is None:
        return ""
    reason = candidate.reasons[0] if candidate.reasons else "待确认"
    risk = candidate.risks[0] if candidate.risks else "暂无"
    condition = candidate.watch_conditions[0] if candidate.watch_conditions else "等待确认"
    return f"""
      <div class="panel portfolio-editor">
        <div class="editor-toolbar">
          <div><h3>{escape(candidate.name)} · {escape(candidate.code)}</h3></div>
          {_render_clear_candidate_focus(stock_code, provider_name, holdings_path)}
        </div>
        <div class="metric-list">
          <div class="metric-line"><span>分数</span><strong>{candidate.score}/100</strong></div>
          <div class="metric-line"><span>方向</span><strong>{escape(candidate.sector)}</strong></div>
          <div class="metric-line"><span>最新价</span><strong>{candidate.latest_close:.2f}</strong></div>
          <div class="metric-line"><span>日涨跌</span><strong>{candidate.pct_change:.2f}%</strong></div>
          <div class="metric-line"><span>理由</span><strong>{escape(reason)}</strong></div>
          <div class="metric-line"><span>风险</span><strong>{escape(risk)}</strong></div>
          <div class="metric-line"><span>条件</span><strong>{escape(condition)}</strong></div>
        </div>
        <div class="form-actions">
          {_render_candidate_research_link(candidate.code, provider_name, holdings_path)}
        </div>
      </div>"""


def _render_candidate_research_link(
    candidate_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    query = urlencode(
        {
            "code": candidate_code,
            "provider": provider_name,
            "holdings": holdings_path,
        }
    )
    return f'<a class="primary-button" href="/?{query}#stock" aria-label="打开 {escape(candidate_code)} 个股分析">分析</a>'


def _render_clear_candidate_focus(
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-smart-select")}">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <button class="ghost-button" type="submit">关闭焦点</button>
      </form>"""


def _render_candidate_filter_tabs(
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    active_group: str,
    active_strategy: str,
) -> str:
    tabs = [
        ("all", "全部候选"),
        ("high", "高优先级"),
        ("mid", "中优先级"),
        ("watch", "观察级"),
    ]
    return "".join(
        _render_candidate_filter_tab(
            group=group,
            label=label,
            active_group=active_group,
            stock_code=stock_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
            candidate_code=candidate_code,
            candidate_strategy=active_strategy,
        )
        for group, label in tabs
    )


def _render_candidate_filter_tab(
    *,
    group: str,
    label: str,
    active_group: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    candidate_strategy: str,
) -> str:
    primary_class = " primary" if group == active_group else ""
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-smart-select")}" style="display:inline-flex">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <input type="hidden" name="candidate" value="{escape(candidate_code)}" />
        <input type="hidden" name="candidate_strategy" value="{escape(candidate_strategy)}" />
        <input type="hidden" name="candidate_tier" value="{escape(group)}" />
        <button class="portfolio-inline-button{primary_class}" type="submit" data-action="filter-candidates">{escape(label)}</button>
      </form>"""


def _render_candidate_strategy_tabs(
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    active_group: str,
    active_strategy: str,
) -> str:
    tabs = [(key, label) for key, label, _ in _candidate_strategy_definitions()]
    return "".join(
        _render_candidate_strategy_tab(
            strategy=strategy,
            label=label,
            active_strategy=active_strategy,
            stock_code=stock_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
            candidate_code=candidate_code,
            active_group=active_group,
        )
        for strategy, label in tabs
    )


def _render_candidate_strategy_tab(
    *,
    strategy: str,
    label: str,
    active_strategy: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    active_group: str,
) -> str:
    primary_class = " primary" if strategy == active_strategy else ""
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-smart-select")}" style="display:inline-flex">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <input type="hidden" name="candidate" value="{escape(candidate_code)}" />
        <input type="hidden" name="candidate_tier" value="{escape(active_group)}" />
        <input type="hidden" name="candidate_strategy" value="{escape(strategy)}" />
        <button class="portfolio-inline-button{primary_class}" type="submit" data-action="filter-candidates">{escape(label)}</button>
      </form>"""


def _render_candidate_refresh_form(
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    active_group: str,
) -> str:
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("workspace-smart-select")}" style="display:inline-flex">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <input type="hidden" name="candidate" value="{escape(candidate_code)}" />
        <input type="hidden" name="candidate_tier" value="{escape(active_group)}" />
        <button class="portfolio-inline-button" type="submit">刷新评分</button>
      </form>"""


def _render_candidate_quality_form(
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    active_group: str,
) -> str:
    return f"""
      <form class="inline-form" method="get" action="{workspace_action("module-data-quality")}" style="display:inline-flex">
        <input type="hidden" name="code" value="{escape(stock_code)}" />
        <input type="hidden" name="provider" value="{escape(provider_name)}" />
        <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
        <input type="hidden" name="candidate" value="{escape(candidate_code)}" />
        <input type="hidden" name="candidate_tier" value="{escape(active_group)}" />
        <button class="portfolio-inline-button" type="submit">查看数据质量</button>
      </form>"""


def _normalize_candidate_group(candidate_group: str) -> str:
    normalized = candidate_group.strip().lower()
    return normalized if normalized in {"all", "high", "mid", "watch"} else "all"


def _candidate_group_label(candidate_group: str) -> str:
    return {
        "all": "全部候选",
        "high": "高优先级",
        "mid": "中优先级",
        "watch": "观察级",
    }.get(candidate_group, "全部候选")


def _candidate_group_summary(candidate_group: str) -> str:
    return {
        "all": "展示全部候选，适合先看完整排序，再决定哪些标的进入个股分析。",
        "high": "只看高优先级候选，适合优先处理最值得花时间的标的。",
        "mid": "只看中优先级候选，适合补充研究和等待条件进一步明朗。",
        "watch": "只看观察级候选，适合找后备池和低优先级跟踪对象。",
    }.get(candidate_group, "展示全部候选，适合先看完整排序，再决定哪些标的进入个股分析。")


def _filter_candidates_by_group(candidates: list, candidate_group: str) -> list:
    if candidate_group == "high":
        return [item for item in candidates if item.score >= 75]
    if candidate_group == "mid":
        return [item for item in candidates if 60 <= item.score < 75]
    if candidate_group == "watch":
        return [item for item in candidates if item.score < 60]
    return list(candidates)


def _normalize_candidate_strategy(candidate_strategy: str) -> str:
    normalized = candidate_strategy.strip().lower()
    valid = {key for key, _, _ in _candidate_strategy_definitions()}
    return normalized if normalized in valid else "all"


def _candidate_strategy_label(candidate_strategy: str) -> str:
    return {key: label for key, label, _ in _candidate_strategy_definitions()}.get(
        candidate_strategy, "全部策略"
    )


def _candidate_strategy_definitions() -> list[tuple[str, str, str]]:
    return [
        ("all", "全部策略", "完整排序"),
        ("cluster", "资金抱团", "同一主题多股共振"),
        ("hot", "市场热度", "涨幅与评分同步靠前"),
        ("rebound", "超跌反弹", "回落后等待修复确认"),
        ("breakout", "强势突破", "高分且价格转强"),
        ("low_volume", "低位放量", "低位温和转强"),
        ("trend", "趋势共振", "分数、涨跌和板块同向"),
        ("quality", "业绩质量", "估值和风险更稳"),
        ("catalyst", "消息催化", "公告、新闻和主题触发"),
        ("pullback", "缩量回踩", "强势股回踩后确认"),
        ("dividend", "高股息防守", "弱市防守候选"),
        ("risk", "风险排查", "高风险先排除"),
    ]


def _filter_candidates_by_strategy(candidates: list, candidate_strategy: str) -> list:
    items = list(candidates)
    if candidate_strategy == "cluster":
        sector_counts: dict[str, int] = {}
        for item in items:
            sector_counts[item.sector] = sector_counts.get(item.sector, 0) + 1
        clustered = [item for item in items if sector_counts.get(item.sector, 0) >= 2]
        return sorted(
            clustered or items,
            key=lambda item: (sector_counts.get(item.sector, 0), item.score, item.pct_change),
            reverse=True,
        )
    if candidate_strategy == "hot":
        return sorted(items, key=lambda item: (item.pct_change, item.score), reverse=True)
    if candidate_strategy == "rebound":
        rebound = [item for item in items if item.pct_change <= 0]
        return sorted(
            rebound or items, key=lambda item: (item.score, -item.pct_change), reverse=True
        )
    if candidate_strategy == "breakout":
        breakout = [item for item in items if item.score >= 75 and item.pct_change > 0]
        return sorted(
            breakout or items, key=lambda item: (item.score, item.pct_change), reverse=True
        )
    if candidate_strategy == "low_volume":
        low_volume = [item for item in items if 0 <= item.pct_change <= 4 and item.score >= 60]
        return sorted(
            low_volume or items,
            key=lambda item: (item.score, -abs(item.pct_change - 2)),
            reverse=True,
        )
    if candidate_strategy == "trend":
        trend = [item for item in items if item.score >= 70 and item.pct_change > 0]
        return sorted(trend or items, key=lambda item: (item.score, item.pct_change), reverse=True)
    if candidate_strategy == "quality":
        quality = [item for item in items if item.score >= 68 and not item.risks]
        return sorted(
            quality or items, key=lambda item: (item.score, -len(item.risks)), reverse=True
        )
    if candidate_strategy == "catalyst":
        catalyst = [
            item
            for item in items
            if any(
                "消息" in reason or "公告" in reason or "主题" in reason for reason in item.reasons
            )
        ]
        return sorted(
            catalyst or items, key=lambda item: (len(item.reasons), item.score), reverse=True
        )
    if candidate_strategy == "pullback":
        pullback = [item for item in items if -3 <= item.pct_change <= 1 and item.score >= 65]
        return sorted(
            pullback or items, key=lambda item: (item.score, -abs(item.pct_change)), reverse=True
        )
    if candidate_strategy == "dividend":
        defensive = [
            item for item in items if item.score >= 60 and not item.risks and item.pct_change <= 3
        ]
        return sorted(
            defensive or items,
            key=lambda item: (100 - abs(item.pct_change), item.score),
            reverse=True,
        )
    if candidate_strategy == "risk":
        risk_items = [
            item
            for item in items
            if item.risks or item.score < 65 or item.pct_change >= 6 or item.pct_change <= -3
        ]
        return sorted(
            risk_items or items,
            key=lambda item: (len(item.risks), abs(item.pct_change), 100 - item.score),
            reverse=True,
        )
    return items


def _select_candidate(candidates: CandidatePoolReport, candidate_code: str):
    normalized = candidate_code.strip()
    if normalized:
        return next((item for item in candidates.candidates if item.code == normalized), None)
    return None


def _li_join(items: list[str]) -> str:
    return "".join(f"<li>{escape(item)}</li>" for item in items)


def _localize_display_text(text: str) -> str:
    localized = str(text)
    for raw, label in BOARD_LABELS.items():
        localized = localized.replace(raw, label)
    return localized


def _extract_markdown_highlights(
    markdown: str,
    heading: str,
    *,
    fallback: list[str] | str,
) -> list[str]:
    lines = markdown.splitlines()
    capture = False
    items: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == heading:
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture and stripped.startswith("- "):
            items.append(stripped[2:].strip())
    if items:
        return items
    if isinstance(fallback, str):
        return [fallback]
    return fallback


def _safe_fetch_announcements(
    query: str,
    *,
    announcement_fetcher: AnnouncementFetcher | None,
) -> AnnouncementReport | None:
    if announcement_fetcher is None and not _web_live_announcements_enabled():
        return None
    fetcher = announcement_fetcher or fetch_cninfo_announcements
    try:
        return fetcher(query, limit=5)
    except Exception:
        return None


def _web_live_announcements_enabled() -> bool:
    return os.getenv("STOCK_TS_WEB_LIVE_ANNOUNCEMENTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _trade_blocking_warnings(warnings: list[str]) -> list[str]:
    blocking_keywords = ["示例数据", "疑似降级", "未完成代码解析", "示例股票", "个股日期需复核"]
    return [
        warning for warning in warnings if any(keyword in warning for keyword in blocking_keywords)
    ]


def _format_ma_stack(technical: TechnicalProfile) -> str:
    def fmt(value: float | None) -> str:
        return "-" if value is None else f"{value:.2f}"

    return f"{fmt(technical.ma5)} / {fmt(technical.ma10)} / {fmt(technical.ma20)}"


def _render_announcement_rows(report: AnnouncementReport | None) -> str:
    if report is None or not report.items:
        return "<tr><td>--</td><td>未拉取到公告数据</td><td>待补充</td><td>--</td></tr>"
    return "".join(
        f"<tr><td>{escape(item.date)}</td><td>{escape(item.title)}</td><td>{escape(','.join(item.risk_flags) or '普通')}</td><td>{_announcement_link(item.url)}</td></tr>"
        for item in report.items[:5]
    )


def _announcement_link(url: str) -> str:
    if not url:
        return "--"
    safe_url = escape(url, quote=True)
    return f'<a href="{safe_url}" target="_blank" rel="noreferrer">PDF</a>'


def render_error_page(message: str, provider_name: str = "sample") -> str:
    safe_message = escape(message)
    safe_provider = escape(provider_name)
    body = f"""
  <div class="app-shell">
    {render_shell_sidebar()}
    <main class="workspace">
      <section class="workspace-pane active" id="settings" data-workspace="settings" data-legacy-id="workspace-settings">
      <div class="workspace-shell">
      <section class="module" id="module-settings">
        <div class="module-header"><div><h2 class="module-title">系统暂时无法生成复盘</h2><p class="module-desc">当前数据源或输入文件有问题。</p></div><span class="risk-pill high">错误</span></div>
        <div class="panel">
          <h3>错误信息</h3>
          <p>{safe_message}</p>
          <ul class="note-list">
            <li>当前 provider={safe_provider}，Web 页面固定使用 TDX MCP 快照。</li>
            <li>请先生成或更新 data/imports/tdx_snapshots.json。</li>
            <li>确认本地持仓账本存在且可读取。</li>
          </ul>
          <p class="footer-warning">免责声明：本页面仅用于研究与复盘，不构成投资建议。</p>
        </div>
      </section>
      </div>
      </section>
    </main>
  </div>
  {render_shell_script()}"""
    return render_document(body)


def _assess_data_quality(
    *,
    requested_provider: str,
    actual_provider: str,
    resolved: ResolvedSymbol,
    stock: DeepStockReport,
    market: MarketSnapshot,
    candidates: CandidatePoolReport,
    candidate_universe: list[CandidateStockRawData],
) -> DataQualityView:
    warnings = list(resolved.warnings)
    blocked_actions: list[str] = []
    candidate_price_reliable = candidates.price_reliable
    candidate_universe_reliable = _candidate_universe_prices_reliable(candidate_universe)
    if not candidate_price_reliable or not candidate_universe_reliable:
        warnings.append("候选排序暂停：候选池缺少真实日线。")
        blocked_actions.extend(["候选排序", "评分展示", "涨跌幅展示"])
    if requested_provider.strip().lower() == "sample" or actual_provider == "SampleDataProvider":
        warnings.append("示例数据：当前个股行情来自离线样例，只能验证流程，不能用于真实决策。")
    if (
        requested_provider.strip().lower() in {"auto", "akshare", "tencent"}
        and stock.trade_date <= "2026-06-03"
    ):
        warnings.append(
            "疑似降级数据：真实数据源不可用时返回了样例行情，请切换数据源或导入本地行情。"
        )
    if actual_provider == "TencentProvider":
        warnings.append("腾讯源当前提供指数与个股行情；板块和候选池仍使用样例结构兜底。")
    if stock.trade_date and market.trade_date and stock.trade_date < market.trade_date:
        warnings.append(f"个股日期需复核：个股 {stock.trade_date}，大盘 {market.trade_date}。")
    if stock.trade_date and market.trade_date and market.trade_date < stock.trade_date:
        warnings.append(f"大盘日期需刷新：大盘 {market.trade_date}，个股 {stock.trade_date}。")
    if resolved.source == "unresolved":
        warnings.append("股票名称未完成代码解析，可能查到错误标的或样例占位数据。")
    if stock.name == "示例股票":
        warnings.append("股票名称仍为示例股票，说明代码未被真实数据源或内置映射识别。")

    unique_warnings = list(dict.fromkeys(warnings))
    blocked_actions = list(dict.fromkeys(blocked_actions))
    if blocked_actions:
        status = "排序已暂停"
        gate_level = "blocked"
        signal = "暂停"
        summary = "排序暂停"
    elif unique_warnings:
        status = "需要人工确认"
        gate_level = "warn"
        signal = "降级"
        summary = "需确认"
    else:
        status = "可用于专业复盘"
        gate_level = "ok"
        signal = "可用"
        summary = "可用"
    return DataQualityView(
        status=status,
        warnings=unique_warnings,
        latest_date=stock.trade_date,
        market_date=market.trade_date,
        requested_provider=requested_provider,
        actual_provider=actual_provider,
        candidate_price_reliable=candidate_price_reliable,
        candidate_universe_reliable=candidate_universe_reliable,
        gate_level=gate_level,
        signal=signal,
        summary=summary,
        blocked_actions=blocked_actions,
    )


def _market_action_label(market: MarketSnapshot) -> str:
    if (
        market.heat_score >= 70
        and market.breadth_ratio >= 1.2
        and market.limit_up_count >= max(20, market.limit_down_count * 3)
    ):
        return "可以进攻"
    if market.heat_score >= 50 and market.breadth_ratio >= 0.8:
        return "控制仓位"
    return "防守观察"


def _sector_state_label(top) -> str:
    if top is None:
        return "等待数据"
    if top.risk != "风险可控" or top.continuity == "退潮或调整":
        return "分歧复核"
    if top.rotation_status == "市场主线":
        return "主线确认"
    if top.heat_score >= 70:
        return "轮动观察"
    return "等待确认"


def _limit_up_state_label(market: MarketSnapshot) -> str:
    if market.limit_up_count >= 60 and market.limit_up_count >= market.limit_down_count * 2:
        return "情绪偏强"
    if market.limit_up_count >= 25:
        return "情绪修复"
    return "情绪偏弱"


def _limit_down_state_label(market: MarketSnapshot) -> str:
    if market.limit_down_count >= 30:
        return "退潮风险"
    if market.limit_down_count >= 15:
        return "风险抬升"
    return "亏钱效应可控"


def _build_risk_gate(
    *,
    quality: DataQualityView,
    market: MarketSnapshot,
    event_radar: EventRadar,
    portfolio: PortfolioAnalysisReport,
) -> RiskGateView:
    market_risk = _market_action_label(market)
    limit_down_risk = _limit_down_state_label(market)
    data_risk = quality.signal
    event_risk = event_radar.gate
    portfolio_risk = _portfolio_risk_label(portfolio)
    blockers: list[str] = []
    warnings: list[str] = []

    if quality.gate_level == "blocked":
        blockers.append("数据暂停")
    elif quality.gate_level == "warn":
        warnings.append("数据降级")
    if limit_down_risk == "退潮风险":
        blockers.append("跌停退潮")
    elif limit_down_risk == "风险抬升":
        warnings.append("跌停抬升")
    if market_risk == "防守观察":
        warnings.append("市场防守")
    if event_radar.gate == "事件需复核" or event_radar.risk_score >= 80:
        blockers.append("事件复核")
    elif event_radar.gate == "公告待补充" or event_radar.risk_score >= 60:
        warnings.append("事件待补")
    if portfolio.health_score < 45 or portfolio.top_position_weight >= 0.45:
        warnings.append("持仓约束")

    if blockers:
        gate = "暂停行动"
        level = "high"
        reason = " / ".join(blockers[:2])
    elif warnings:
        gate = "控制仓位"
        level = "mid"
        reason = " / ".join(warnings[:2])
    elif market_risk == "可以进攻":
        gate = "可行动"
        level = "low"
        reason = "市场和数据通过"
    else:
        gate = "可观察"
        level = "mid"
        reason = "等待共振"
    return RiskGateView(
        gate=gate,
        level=level,
        market_risk=market_risk,
        limit_down_risk=limit_down_risk,
        data_risk=data_risk,
        event_risk=event_risk,
        portfolio_risk=portfolio_risk,
        reason=reason,
    )


def _portfolio_risk_label(portfolio: PortfolioAnalysisReport) -> str:
    if portfolio.health_score < 45:
        return "组合承压"
    if portfolio.top_position_weight >= 0.45:
        return "集中度高"
    if portfolio.risk_alerts:
        return "有风险项"
    return "可控"


def _retitle_module(html: str, *, old_id: str, new_id: str) -> str:
    return html.replace(f'id="{old_id}"', f'id="{new_id}"')


def _render_global_freshness_bar(
    quality: DataQualityView,
    market: MarketSnapshot,
    provider_class: str,
    risk_gate: RiskGateView,
) -> str:
    data_detail = _freshness_detail(quality)
    provider_label = "TDX MCP" if quality.requested_provider == WEB_DATA_PROVIDER else provider_class
    return f"""
      <div class="freshness-bar" aria-label="全局数据新鲜度">
        <div><span>交易日</span><strong>{escape(market.trade_date or quality.market_date or '待确认')}</strong></div>
        <div><span>行情</span><strong>{escape(quality.latest_date or '待确认')}</strong></div>
        <div><span>K线/资金/新闻/公告</span><strong>{escape(data_detail)}</strong></div>
        <div><span>数据状态</span><strong>{escape(quality.signal)}</strong></div>
        <div><span>来源</span><strong>{escape(provider_label)}</strong></div>
        <div><span>动作闸门</span><strong>{escape(risk_gate.gate)}</strong></div>
      </div>"""


def _freshness_detail(quality: DataQualityView) -> str:
    if quality.gate_level == "blocked":
        return "有缺口"
    if quality.gate_level == "warn":
        return "需复核"
    return "可用"


def _read_latest_daily_decisions() -> dict[str, object]:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    return read_decision_artifact(report_dir / "latest_decisions.json")


def _render_home_module(
    *,
    quality: DataQualityView,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport,
    candidates: CandidatePoolReport,
    risk_gate: RiskGateView,
    provider_name: str,
    holdings_path: str,
    daily_decisions: dict[str, object] | None = None,
) -> str:
    daily_decisions = daily_decisions or {}
    mainline = "、".join(sectors.market_mainline[:3]) if sectors.market_mainline else "待确认"
    first_risk = portfolio.risk_alerts[0] if portfolio.risk_alerts else "暂无突出风险"
    top_holding = max(portfolio.positions, key=lambda item: item.weight, default=None)
    top_holding_text = (
        f"{top_holding.holding.name} {top_holding.weight:.1%}" if top_holding else "未读取持仓"
    )
    candidate_label = (
        f"{candidates.candidates[0].name} · {candidates.candidates[0].code}"
        if candidates.candidates and candidates.price_reliable
        else "候选排序暂停"
    )
    structured_opportunity = _decision_first_opportunity(daily_decisions)
    if structured_opportunity:
        candidate_label = structured_opportunity
    risk_position = _highest_priority_position(portfolio)
    max_risk_holding = (
        f"{risk_position.holding.name} · {risk_position.risk_level}风险"
        if risk_position
        else "暂无突出风险"
    )
    structured_red = _decision_names(daily_decisions, "red")
    if structured_red:
        max_risk_holding = structured_red[0]
    suggested_position = _home_position_cap(portfolio, risk_gate)
    data_time = quality.latest_date or quality.market_date or market.trade_date
    market_summary = _decision_market_summary(daily_decisions) or market.summary
    next_actions = [
        (
            "先定风险闸门",
            risk_gate.gate,
            f"{market_summary}；大盘细节去 A股大盘看。",
            "market",
        ),
        (
            "再处理组合仓位",
            top_holding_text,
            first_risk,
            "portfolio",
        ),
        (
            "最后挑机会",
            candidate_label,
            f"主线：{mainline}。只做入口，不复述大盘拆解。",
            "screener",
        ),
    ]
    action_cards = "".join(
        f"""
        <button class="workflow-card" type="button" data-jump="{target}">
          <strong>{escape(label)}</strong>
          <span>{escape(value)} · {escape(note)}</span>
        </button>
        """
        for label, value, note, target in next_actions
    )
    home_facts = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(value)}</td></tr>"
        for label, value in [
            ("大盘", f"{market.regime} · 热度 {market.heat_score}/100"),
            (
                "上涨 / 下跌 / 平盘",
                f"{market.advancing_count} / {market.declining_count} / {market.unchanged_count}",
            ),
            ("涨停 / 跌停", f"{market.limit_up_count} / {market.limit_down_count}"),
            ("主线", mainline),
            ("持仓健康度", f"{portfolio.health_score}/100"),
            ("数据可信度", quality.status),
        ]
    )
    leading_rows = _render_home_sector_rows(
        sorted(sectors.sectors, key=lambda item: (item.pct_chg, item.heat_score), reverse=True)[:5],
        mode="lead",
    )
    lagging_rows = _render_home_sector_rows(
        sorted(sectors.sectors, key=lambda item: (item.pct_chg, item.advancing_ratio))[:5],
        mode="lag",
    )
    catalyst_items = _li_join(_home_catalyst_items(market, sectors)[:6])
    fund_text = (
        f"北向净流入 {market.northbound_net_inflow:.1f} 亿"
        if market.northbound_net_inflow is not None and market.northbound_net_inflow >= 0
        else (
            f"北向净流出 {abs(market.northbound_net_inflow):.1f} 亿"
            if market.northbound_net_inflow is not None
            else "资金明细未接入"
        )
    )
    strong_rows = _render_home_candidate_rows(
        candidates.candidates[:20],
        provider_name=provider_name,
        holdings_path=holdings_path,
        mode="strong",
    )
    risk_rows = _render_home_candidate_rows(
        _filter_candidates_by_strategy(candidates.candidates, "risk")[:20],
        provider_name=provider_name,
        holdings_path=holdings_path,
        mode="risk",
    )
    focus_cards = "".join(
        f"""
        <button class="workflow-card" type="button" data-jump="{target}">
          <strong>{escape(label)}</strong>
          <span>{escape(note)}</span>
        </button>
        """
        for target, label, note in [
            ("market", "看大盘", market.summary),
            ("portfolio", "处理持仓", first_risk),
            ("screener", "找机会", f"候选机会：{candidate_label}"),
            ("stock", "分析个股", top_holding_text),
        ]
    )
    decision_brief = _render_home_decision_brief(
        market=market,
        risk_gate=risk_gate,
        portfolio=portfolio,
        suggested_position=suggested_position,
        max_risk_holding=max_risk_holding,
        candidate_label=candidate_label,
        mainline=mainline,
        quality=quality,
    )
    traffic_light_actions = _render_home_traffic_light_actions(
        portfolio,
        candidates,
        daily_decisions=daily_decisions,
    )
    decision_limits = _render_home_decision_limits(daily_decisions)
    action_desk = f"""
      <div class="action-desk">
        <div class="action-desk-hero">
          <h3>今日行动台</h3>
          <p>{escape(market_summary)}；先按风险闸门决定仓位，再处理持仓，最后只看满足条件的机会。</p>
          <div class="action-desk-grid">
            <div class="action-desk-metric"><span>建议仓位</span><strong>{escape(suggested_position)}</strong></div>
            <div class="action-desk-metric"><span>最大风险持仓</span><strong>{escape(max_risk_holding)}</strong></div>
            <div class="action-desk-metric"><span>今日机会首位</span><strong>{escape(candidate_label)}</strong></div>
            <div class="action-desk-metric"><span>数据更新时间</span><strong>{escape(data_time)}</strong></div>
          </div>
          <button class="action-copy-button" type="button" data-copy-action-plan>复制今日行动</button>
        </div>
        <div class="action-lanes">
          <button class="action-lane" type="button" data-jump="portfolio"><strong>先处理风险</strong><p>{escape(first_risk)}；先看持仓处理队列，风险仓不补仓。</p></button>
          <button class="action-lane" type="button" data-jump="screener"><strong>再看机会</strong><p>{escape(candidate_label)}；只在主线延续和盘中承接时观察。</p></button>
          <button class="action-lane" type="button" data-jump="data-quality"><strong>最后看数据</strong><p>{escape(quality.summary)}；数据缺口会降低操作优先级。</p></button>
        </div>
      </div>"""
    return f"""
    <section class="module" id="module-home">
      <div class="module-header">
        <div><h2 class="module-title">今日行动台</h2></div>
        <span class="risk-pill {risk_gate.level}">{escape(risk_gate.gate)}</span>
      </div>
      {action_desk}
      {traffic_light_actions}
      {decision_limits}
      {decision_brief}
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>今日先做这三件事</h3></div><span class="portfolio-chip">{escape(market.trade_date)}</span></div>
        <div class="workflow-grid">{action_cards}</div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel">
          <h3>核心数据</h3>
          <table class="data-table"><thead><tr><th>项目</th><th>结果</th></tr></thead><tbody>{home_facts}</tbody></table>
        </div>
        <div class="panel">
          <h3>快速进入</h3>
          <div class="workflow-grid">{focus_cards}</div>
        </div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel">
          <h3>领涨板块 Top 5</h3>
          <table class="data-table"><thead><tr><th>板块</th><th>强弱</th><th>热度</th><th>分析原因</th></tr></thead><tbody>{leading_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>领跌板块 Top 5</h3>
          <table class="data-table"><thead><tr><th>板块</th><th>强弱</th><th>热度</th><th>风险原因</th></tr></thead><tbody>{lagging_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>资金与情绪</h3>
          <div class="summary-grid">
            <div class="summary-card"><span>资金</span><strong>{escape(fund_text)}</strong><p class="kpi-foot">未接入明细时不推断主力净流。</p></div>
            <div class="summary-card"><span>短线情绪</span><strong>{escape(_limit_up_state_label(market))}</strong><p class="kpi-foot">涨停 {market.limit_up_count} 家。</p></div>
            <div class="summary-card"><span>亏钱效应</span><strong>{escape(_limit_down_state_label(market))}</strong><p class="kpi-foot">跌停 {market.limit_down_count} 家。</p></div>
          </div>
        </div>
        <div class="panel">
          <h3>消息催化</h3>
          <ul class="reason-list">{catalyst_items}</ul>
        </div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel">
          <h3>强势股票 20</h3>
          <table class="data-table candidates-table"><thead><tr><th>#</th><th>股票</th><th>方向</th><th>原因</th><th>操作</th></tr></thead><tbody>{strong_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>风险股票 20</h3>
          <table class="data-table candidates-table"><thead><tr><th>#</th><th>股票</th><th>方向</th><th>风险原因</th><th>操作</th></tr></thead><tbody>{risk_rows}</tbody></table>
        </div>
      </div>
    </section>"""


def _render_home_decision_brief(
    *,
    market: MarketSnapshot,
    risk_gate: RiskGateView,
    portfolio: PortfolioAnalysisReport,
    suggested_position: str,
    max_risk_holding: str,
    candidate_label: str,
    mainline: str,
    quality: DataQualityView,
) -> str:
    posture = _home_trading_posture(market, risk_gate, portfolio, suggested_position)
    avoid = _home_avoid_action(market, risk_gate, quality)
    return f"""
      <div class="panel home-brief" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>今日交易简报</h3></div><span class="portfolio-chip">{escape(market.trade_date)}</span></div>
        <div class="summary-grid">
          <div class="summary-card"><span>今天先防守还是进攻</span><strong>{escape(posture)}</strong><p class="kpi-foot">{escape(risk_gate.reason)}</p></div>
          <div class="summary-card"><span>持仓先处理</span><strong>{escape(max_risk_holding)}</strong><p class="kpi-foot">先处理风险仓，再看盈利保护。</p></div>
          <div class="summary-card"><span>今日机会 10</span><strong>{escape(candidate_label)}</strong><p class="kpi-foot">主线：{escape(mainline)}；先观察，不等于买入。</p></div>
          <div class="summary-card"><span>今天不要做什么</span><strong>{escape(avoid)}</strong><p class="kpi-foot">不是买点不追，不用亏损理由补仓。</p></div>
        </div>
      </div>"""


def _render_home_traffic_light_actions(
    portfolio: PortfolioAnalysisReport,
    candidates: CandidatePoolReport,
    *,
    daily_decisions: dict[str, object] | None = None,
) -> str:
    if daily_decisions:
        structured = _render_decision_traffic_light_actions(daily_decisions)
        if structured:
            return structured
    red: list[str] = []
    yellow: list[str] = []
    green: list[str] = []
    held_names = {position.holding.name for position in portfolio.positions}
    for position in portfolio.positions:
        name = position.holding.name
        if position.risk_level == "高" or (
            position.pnl >= 0 and position.trend == "下降趋势"
        ):
            red.append(name)
        elif position.pnl >= 0 and position.trend == "上升趋势":
            green.append(name)
        elif position.pnl < 0 or position.trend == "下降趋势" or position.risk_level == "中":
            yellow.append(name)

    opportunities = [
        item.name
        for item in candidates.candidates
        if item.name not in held_names
    ][:4]
    return f"""
      <div class="panel home-brief" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>红黄绿处理顺序</h3><p class="section-subtitle">今天按颜色处理，不按喜好处理。</p></div></div>
        <div class="summary-grid">
          {_render_home_traffic_card("红灯", "先降风险", red, "不加仓；反弹优先锁利润或减风险")}
          {_render_home_traffic_card("黄灯", "等修复", yellow, "只看放量修复；不补亏、不追高")}
          {_render_home_traffic_card("绿灯", "持有跟踪", green, "按计划持有；跌破纪律线再减")}
          {_render_home_traffic_card("机会", "只观察", opportunities, "等主线延续和开盘承接；名单不等于买点")}
        </div>
      </div>"""


def _render_decision_traffic_light_actions(decisions: dict[str, object]) -> str:
    lights = decisions.get("traffic_lights")
    if not isinstance(lights, dict):
        return ""
    rows = [
        ("red", "红灯", "先降风险"),
        ("yellow", "黄灯", "等修复"),
        ("green", "绿灯", "持有跟踪"),
    ]
    cards = "".join(
        _render_home_traffic_card(
            label,
            action,
            _decision_names(decisions, key),
            _decision_first_reason(decisions, key) or "按结构化日报决策执行",
        )
        for key, label, action in rows
    )
    opportunities = [
        str(item.get("name", "")).strip()
        for item in _decision_list(decisions, "opportunities")
        if isinstance(item, dict) and item.get("name")
    ]
    cards += _render_home_traffic_card(
        "机会",
        "只观察",
        opportunities,
        "等主线延续和开盘承接；名单不等于买点",
    )
    return f"""
      <div class="panel home-brief" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>红黄绿处理顺序</h3><p class="section-subtitle">来自 latest_decisions.json；今天按颜色处理，不按喜好处理。</p></div></div>
        <div class="summary-grid">{cards}</div>
      </div>"""


def _render_home_decision_limits(decisions: dict[str, object]) -> str:
    action_limits = [str(item) for item in _decision_list(decisions, "action_limits") if item]
    automation = decisions.get("automation") if isinstance(decisions, dict) else None
    automation_advice = ""
    if isinstance(automation, dict):
        automation_advice = str(automation.get("advice") or "").strip()
    if not action_limits and not automation_advice:
        return ""
    limit_items = _li_join(action_limits or ["未触发交易限制"])
    advice = automation_advice or "自动更新未发现硬失败"
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>今日交易限制</h3><p class="section-subtitle">数据缺口直接变成操作限制，不把缺口当利好。</p></div></div>
        <div class="grid-2">
          <div class="compact-note-card"><strong>不能作为买入理由</strong><ul>{limit_items}</ul></div>
          <div class="compact-note-card"><strong>自动任务提醒</strong><ul>{_li_join([advice])}</ul></div>
        </div>
      </div>"""


def _render_home_traffic_card(
    label: str,
    action: str,
    names: list[str],
    note: str,
) -> str:
    visible = _join_limited_names(names) if names else "暂无"
    return f"""
      <div class="summary-card">
        <span>{escape(label)}</span>
        <strong>{escape(visible)}</strong>
        <p class="kpi-foot">{escape(action)}：{escape(note)}</p>
      </div>"""


def _join_limited_names(names: list[str], *, limit: int = 4) -> str:
    visible = names[:limit]
    suffix = f"等{len(names)}只" if len(names) > limit else ""
    return "、".join(visible) + suffix


def _decision_market_summary(decisions: dict[str, object]) -> str:
    market = decisions.get("market") if isinstance(decisions, dict) else None
    if not isinstance(market, dict):
        return ""
    return str(market.get("summary") or "").strip()


def _decision_first_opportunity(decisions: dict[str, object]) -> str:
    opportunities = _decision_list(decisions, "opportunities")
    for item in opportunities:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        code = str(item.get("code") or "").strip()
        if name:
            return f"{name} · {code}" if code else name
    return ""


def _decision_names(decisions: dict[str, object], light_key: str) -> list[str]:
    lights = decisions.get("traffic_lights") if isinstance(decisions, dict) else None
    if not isinstance(lights, dict):
        return []
    items = lights.get(light_key)
    if not isinstance(items, list):
        return []
    return [
        str(item.get("name", "")).strip()
        for item in items
        if isinstance(item, dict) and item.get("name")
    ]


def _decision_first_reason(decisions: dict[str, object], light_key: str) -> str:
    lights = decisions.get("traffic_lights") if isinstance(decisions, dict) else None
    items = lights.get(light_key) if isinstance(lights, dict) else None
    if not isinstance(items, list):
        return ""
    for item in items:
        if isinstance(item, dict) and item.get("reason"):
            return str(item["reason"]).strip()
    return ""


def _decision_list(decisions: dict[str, object], key: str) -> list[object]:
    value = decisions.get(key) if isinstance(decisions, dict) else None
    return value if isinstance(value, list) else []


def _home_trading_posture(
    market: MarketSnapshot,
    risk_gate: RiskGateView,
    portfolio: PortfolioAnalysisReport,
    suggested_position: str,
) -> str:
    if risk_gate.level == "high" or portfolio.health_score < 40:
        return f"防守，仓位 {suggested_position}"
    if market.heat_score >= 70 and risk_gate.level != "high":
        return f"谨慎进攻，仓位 {suggested_position}"
    if market.heat_score < 50:
        return f"先防守，仓位 {suggested_position}"
    return f"结构机会，仓位 {suggested_position}"


def _home_avoid_action(
    market: MarketSnapshot,
    risk_gate: RiskGateView,
    quality: DataQualityView,
) -> str:
    if quality.gate_level == "blocked":
        return "数据缺口时不交易"
    if risk_gate.level == "high" or market.limit_down_count >= 15:
        return "不追高，不补亏"
    if market.heat_score >= 75:
        return "高开不追，等承接"
    return "不是买点不追"


def _highest_priority_position(portfolio: PortfolioAnalysisReport) -> PositionAnalysis | None:
    if not portfolio.positions:
        return None

    def score(position: PositionAnalysis) -> tuple[int, float]:
        risk_score = {"高": 3, "中": 2, "低": 1}.get(position.risk_level, 0)
        trend_score = 2 if position.trend == "下降趋势" else 0
        loss_score = 2 if position.pnl < 0 else 0
        return (risk_score + trend_score + loss_score, position.weight)

    return max(portfolio.positions, key=score)


def _home_position_cap(portfolio: PortfolioAnalysisReport, risk_gate: RiskGateView) -> str:
    if risk_gate.level == "high" or portfolio.health_score < 40:
        return "3成以内"
    if portfolio.health_score < 60:
        return "5成以内"
    if portfolio.health_score < 70:
        return "6成以内"
    return "7成以内"


def _format_market_count(market: MarketSnapshot, field: str) -> str:
    if field == "advancing":
        return str(market.advancing_count)
    if field == "declining":
        return str(market.declining_count)
    if field in {"unchanged", "flat"}:
        return str(market.unchanged_count)
    return "0"


def _render_home_candidate_rows(
    items: list,
    *,
    provider_name: str,
    holdings_path: str,
    mode: str,
) -> str:
    if not items:
        return "<tr><td colspan='5'>当前候选池没有可展示股票。</td></tr>"
    rows = []
    for index, item in enumerate(items[:20], start=1):
        if mode == "risk":
            detail = item.risks[0] if item.risks else _candidate_strategy_detail(item, "risk")
        else:
            detail = item.reasons[0] if item.reasons else _candidate_strategy_detail(item, "hot")
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)} · {item.pct_change:.2f}%</span></td>"
            f"<td>{escape(item.sector)}</td>"
            f"<td>{escape(detail)}</td>"
            f"<td class='action-cell'>{_render_candidate_research_link(item.code, provider_name, holdings_path)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _home_catalyst_items(market: MarketSnapshot, sectors: SectorAnalysisReport) -> list[str]:
    items: list[str] = []
    for sector in sectors.sectors[:5]:
        if sector.pct_chg > 0 or sector.limit_up_count > 0 or sector.amount_change > 0:
            items.append(
                f"{sector.name}：涨跌 {sector.pct_chg:.2f}%，涨停 {sector.limit_up_count}，成交变化 {sector.amount_change:.2f}，{sector.rotation_status}"
            )
    items.extend(market.opportunities[:3])
    items.extend(market.tomorrow_watch[:2])
    if not items:
        items.append("当前数据源未返回明确催化，先看板块涨跌、扩散和涨停样本。")
    return items


def _render_home_sector_rows(items, *, mode: str) -> str:
    if not items:
        return "<tr><td colspan='4'>当前数据源未返回板块排行。</td></tr>"
    rows = []
    for index, item in enumerate(items, start=1):
        reason = _home_sector_judgement(item, mode=mode, rank=index)
        rows.append(
            f"<tr><td>{escape(item.name)}</td><td>{escape(_sector_move_text(item))}</td><td>{item.heat_score}</td><td>{escape(reason)}</td></tr>"
        )
    return "".join(rows)


def _sector_move_text(item) -> str:
    if "样本涨跌异常" in getattr(item, "risk", ""):
        return "样本异常"
    if item.limit_up_count > 0 and item.pct_chg >= 9.8:
        return f"样本强度 +{item.pct_chg:.2f}%"
    return f"{item.pct_chg:.2f}%"


def _home_sector_judgement(item, *, mode: str, rank: int) -> str:
    spread = f"扩散 {item.advancing_ratio:.0%}"
    amount = f"成交变化 {item.amount_change:.2f}亿"
    if "样本涨跌异常" in getattr(item, "risk", ""):
        return f"第{rank}位：涨跌口径异常，先看作强势样本，不按真实板块涨幅交易；{spread}，{amount}"
    if mode == "lag":
        if item.pct_chg >= 0:
            if item.risk != "风险可控":
                return (
                    f"第{rank}位相对落后：并非真实下跌，但强度掉队且有{item.risk}；"
                    f"{spread}，涨停 {item.limit_up_count}，{amount}"
                )
            if item.amount_change < 0.1:
                return (
                    f"第{rank}位成交跟进弱：涨幅仍为正，但量能不足，容易一日游；{spread}，{amount}"
                )
            return (
                f"第{rank}位相对落后：板块仍上涨，但排序靠后，次日要看是否掉队；{spread}，{amount}"
            )
        if item.advancing_ratio < 0.35:
            return f"普跌确认：多数成份走弱，先避开补跌扩散；{spread}，{amount}"
        return f"跌幅靠前但未完全扩散，重点看龙头是否止跌；{spread}，风险 {item.risk}"
    if item.limit_up_count >= 5:
        return f"涨停集中，资金抱团明显；{spread}，涨停 {item.limit_up_count}，{amount}"
    if item.amount_change >= 5:
        return f"成交显著放大，说明有增量资金参与；{spread}，涨停 {item.limit_up_count}"
    if item.risk != "风险可控":
        return f"强势但分歧高，只看前排承接；{spread}，风险 {item.risk}"
    if item.advancing_ratio >= 0.8:
        return f"上涨覆盖面较广，观察能否从前排扩散到低位；{spread}，资金 {item.fund_status}"
    return f"少数个股带动，持续性要看明日扩散；{spread}，涨停 {item.limit_up_count}"


def _render_sentiment_module(
    universe: list[CandidateStockRawData],
    market: MarketSnapshot,
    provider_class: str,
) -> str:
    up_state = _limit_up_state_label(market)
    down_state = _limit_down_state_label(market)
    conclusion = _sentiment_conclusion(market)
    up_analysis = _limit_up_analysis(market)
    down_analysis = _limit_down_analysis(market)
    risk_items = "".join(f"<li>{escape(item)}</li>" for item in _sentiment_risk_reminders(market))
    next_items = "".join(f"<li>{escape(item)}</li>" for item in _sentiment_next_checks(market))
    if not _candidate_universe_prices_reliable(universe):
        return f"""
    <section class="module" id="module-sentiment">
      <div class="module-header"><div><h2 class="module-title">涨跌停情绪</h2><p class="module-desc">先看赚钱效应，再看亏钱效应和风险处理。</p></div><span class="risk-pill mid">近似统计</span></div>
      <div class="summary-grid">
        <div class="summary-card"><span>情绪结论</span><strong>{escape(conclusion)}</strong><p class="kpi-foot">{escape(up_state)}；{escape(down_state)}</p></div>
        <div class="summary-card"><span>情绪周期</span><strong>{escape(up_state)}</strong><p class="kpi-foot">涨停分析：{escape(up_analysis)}</p></div>
        <div class="summary-card"><span>涨停板</span><strong>{_format_limit_count(market.limit_up_count, provider_class=provider_class)}</strong><p class="kpi-foot">{escape(up_analysis)}</p></div>
        <div class="summary-card"><span>跌停家数</span><strong>{_format_limit_count(market.limit_down_count, provider_class=provider_class)}</strong><p class="kpi-foot">{escape(down_analysis)}</p></div>
        <div class="summary-card"><span>风险状态</span><strong>{escape(down_state)}</strong><p class="kpi-foot">跌停风险：{escape(down_analysis)}</p></div>
        <div class="summary-card"><span>风险处理</span><strong>{escape(_sentiment_risk_action(market))}</strong><p class="kpi-foot">候选日线不足，先不做个股排序。</p></div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel"><h3>风险提醒</h3><ul class="reason-list">{risk_items}</ul></div>
        <div class="panel"><h3>下一步验证</h3><ul class="reason-list">{next_items}</ul></div>
      </div>
      {_candidate_accuracy_pause()}
    </section>"""
    rows = _build_limit_board_rows(universe)
    strongest_rows = sorted(rows, key=lambda item: item.pct_change, reverse=True)[:6]
    exact_up = sum(1 for item in rows if item.pct_change >= 9.5)
    downside_panel = _render_sentiment_downside_panel(
        market=market,
        provider_class=provider_class,
    )
    limit_down_detail_note = (
        f"已接入跌停明细 {len(market.limit_down_details)} 条，优先看是否波及持仓。"
        if market.limit_down_details
        else "当前快照未返回跌停明细时，不用候选池冒充全市场风险名单。"
    )
    return f"""
    <section class="module" id="module-sentiment">
      <div class="module-header"><div><h2 class="module-title">涨跌停情绪</h2><p class="module-desc">看涨停赚钱效应，也看跌停亏钱效应；有跌停数量但无明细时，重点做风险提醒。</p></div><span class="risk-pill mid">短线情绪</span></div>
      <div class="summary-grid">
        <div class="summary-card"><span>情绪结论</span><strong>{escape(conclusion)}</strong><p class="kpi-foot">{escape(up_state)}；{escape(down_state)}</p></div>
        <div class="summary-card"><span>情绪周期</span><strong>{escape(up_state)}</strong><p class="kpi-foot">涨停分析：{escape(up_analysis)}</p></div>
        <div class="summary-card"><span>涨停板</span><strong>{_format_limit_count(market.limit_up_count, provider_class=provider_class)}</strong><p class="kpi-foot">{escape(up_analysis)}</p></div>
        <div class="summary-card"><span>跌停家数</span><strong>{_format_limit_count(market.limit_down_count, provider_class=provider_class)}</strong></div>
        <div class="summary-card"><span>风险状态</span><strong>{escape(down_state)}</strong><p class="kpi-foot">跌停风险：{escape(down_analysis)}</p></div>
        <div class="summary-card"><span>候选涨停样本</span><strong>{exact_up}</strong></div>
        <div class="summary-card"><span>风险处理</span><strong>{escape(_sentiment_risk_action(market))}</strong><p class="kpi-foot">{escape(limit_down_detail_note)}</p></div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel"><h3>强势样本分析</h3><table class="data-table"><thead><tr><th>股票</th><th>方向</th><th>最新价</th><th>涨跌</th><th>涨停原因</th></tr></thead><tbody>{_render_limit_table_rows(strongest_rows, market=market)}</tbody></table><p class="section-subtitle" style="margin-top:12px">涨停原因优先看题材、情绪、成交和高弹性属性；强势样本来自候选池，不代表全市场涨停完整名单。</p></div>
        {downside_panel}
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel"><h3>风险提醒</h3><ul class="reason-list">{risk_items}</ul></div>
        <div class="panel"><h3>下一步验证</h3><ul class="reason-list">{next_items}</ul></div>
      </div>
    </section>"""


def _render_sentiment_downside_panel(
    *,
    market: MarketSnapshot,
    provider_class: str,
) -> str:
    if market.limit_down_details:
        rows = "".join(
            "<tr>"
            f"<td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)}</span></td>"
            f"<td>{escape(item.sector or '未识别主题')}</td>"
            f"<td>{item.latest_close:.2f}</td>"
            f"<td>{item.pct_chg:.2f}%</td>"
            f"<td>{escape(_limit_down_cause(item, market))}</td>"
            "</tr>"
            for item in market.limit_down_details[:20]
        )
        return f"""
        <div class="panel">
          <h3>跌停风险 / 跌停明细</h3>
          <table class="data-table"><thead><tr><th>股票</th><th>方向</th><th>最新价</th><th>跌幅</th><th>跌停原因</th></tr></thead><tbody>{rows}</tbody></table>
          <p class="section-subtitle" style="margin-top:12px">跌停原因按公告/名称特征、所属方向、跌幅制度和市场退潮共同判断；优先检查是否传导到持仓和主线板块。</p>
        </div>"""
    if market.limit_down_count > 0:
        count = _format_limit_count(market.limit_down_count, provider_class=provider_class)
        return f"""
        <div class="panel">
          <h3>跌停风险 / 当前快照未返回跌停明细</h3>
          <div class="empty-state">
            <strong>全市场跌停 {escape(count)} 家</strong>
            <p>当前快照没有跌停个股明细，暂不能逐股拆解跌停原因，也不能用右侧候选样本代表全市场弱势股。</p>
            <p>风险处理：先看跌停家数是否继续扩大，再决定是否降低追涨和高位题材仓位。</p>
          </div>
        </div>"""
    return """
        <div class="panel">
          <h3>跌停风险 / 跌停明细</h3>
          <div class="empty-state"><strong>当前未返回跌停明细</strong><p>跌停原因需要逐股明细、公告或盘口数据；没有跌停数量扩散时，重点观察强势板块是否继续扩散。</p></div>
        </div>"""


def _sentiment_conclusion(market: MarketSnapshot) -> str:
    up_state = _limit_up_state_label(market)
    down_state = _limit_down_state_label(market)
    if down_state == "退潮风险":
        return "强势与退潮并存"
    if up_state == "情绪偏强" and down_state == "亏钱效应可控":
        return "赚钱效应占优"
    if up_state == "情绪偏强":
        return "情绪强但有分歧"
    if down_state == "风险抬升":
        return "风险抬升"
    return "情绪待确认"


def _limit_up_analysis(market: MarketSnapshot) -> str:
    if market.limit_up_count >= 80:
        return "涨停数量高，赚钱效应强；但要确认跌停是否同步扩散。"
    if market.limit_up_count >= 30:
        return "涨停数量修复，适合优先看主线前排和板块扩散。"
    return "涨停数量不足，短线情绪偏弱，先降低追涨动作。"


def _limit_down_analysis(market: MarketSnapshot) -> str:
    if market.limit_down_count >= 30:
        return "跌停数量高，说明亏钱效应扩散，追高和高位接力要降权。"
    if market.limit_down_count >= 15:
        return "跌停数量抬升，说明分歧加大，先看风险是否继续扩散。"
    if market.limit_down_count > 0:
        return "有跌停但未扩散，继续观察是否向持仓或主线板块传导。"
    return "当前未返回跌停扩散，重点观察涨停强度能否延续。"


def _sentiment_risk_action(market: MarketSnapshot) -> str:
    if market.limit_down_count >= 30:
        return "降低追高"
    if market.limit_down_count >= 15:
        return "控制仓位"
    if market.limit_up_count >= 60:
        return "看前排承接"
    return "先观察"


def _sentiment_risk_reminders(market: MarketSnapshot) -> list[str]:
    detail_note = (
        f"已接入跌停明细 {len(market.limit_down_details)} 条，优先检查是否波及持仓方向。"
        if market.limit_down_details
        else "当前快照未返回跌停明细，不能把候选池当作全市场弱势名单。"
    )
    reminders = [
        f"全市场跌停 {market.limit_down_count} 家，风险状态：{_limit_down_state_label(market)}。",
        detail_note,
    ]
    if market.limit_down_count >= 30:
        reminders.append("跌停超过 30 家时，优先处理持仓风险，减少高位题材和追涨。")
    elif market.limit_down_count >= 15:
        reminders.append("跌停超过 15 家时，确认强势板块是否分歧，避免买入后排。")
    else:
        reminders.append("跌停未明显扩散时，重点看涨停前排是否继续打开空间。")
    return reminders


def _sentiment_next_checks(market: MarketSnapshot) -> list[str]:
    checks = [
        "涨停家数是否继续高于跌停家数。",
        "跌停家数是否从高位回落，或继续扩散到持仓方向。",
        "强势样本是否集中在同一主线，而不是无序轮动。",
    ]
    if market.limit_down_count >= 30:
        checks.append("如果明天跌停继续增加，候选只观察，不提高风险暴露。")
    else:
        checks.append("如果跌停不扩散且主线延续，再进入智能选股复核。")
    return checks


def _render_watchlist_module(stock: DeepStockReport) -> str:
    risk = stock.risks[0] if stock.risks else "暂无突出风险"
    trigger = stock.invalid_conditions[0] if stock.invalid_conditions else "跌破失效价降级观察"
    return f"""
    <section class="module" id="module-watchlist">
      <div class="module-header"><div><h2 class="module-title">自选研究</h2></div><span class="status-pill">低频跟踪</span></div>
      <div class="summary-grid">
        <div class="summary-card"><span>当前标的</span><strong>{escape(stock.name)} · {escape(stock.code)}</strong></div>
        <div class="summary-card"><span>观察分</span><strong>{stock.upside.score}/100</strong></div>
        <div class="summary-card"><span>核心风险</span><strong>{escape(risk)}</strong></div>
        <div class="summary-card"><span>触发条件</span><strong>{escape(trigger)}</strong></div>
        <div class="summary-card"><span>用途</span><strong>长期观察</strong><p class="kpi-foot">不影响今日交易；只沉淀假设、提醒和复盘线索。</p></div>
      </div>
      <div class="panel">
        <h3>添加自选</h3>
        <form class="portfolio-form-grid">
          <label class="field-stack">股票<input value="{escape(stock.code)}" /></label>
          <label class="field-stack">分组<input value="重点观察" /></label>
          <label class="field-stack field-span-2">研究假设<input value="{escape(stock.final_conclusion)}" /></label>
          <label class="field-stack field-span-2">提醒条件<input value="{escape(trigger)}" /></label>
          <div class="form-actions field-span-2"><button class="primary-button" type="button" data-action="add-watch-form">保存到自选</button></div>
        </form>
      </div>
    </section>"""


def _render_system_settings_module(
    quality: DataQualityView,
    provider_name: str,
    provider_class: str,
    *,
    current_user: AuthUser | None = None,
    holdings_path: str = DEFAULT_HOLDINGS_PATH,
) -> str:
    matrix = build_data_source_matrix(
        active_provider=provider_name,
        provider_class=provider_class,
        has_tdx_snapshot=True,
    )
    rows = "".join(
        f"<tr><td>{escape(item.name)}</td><td>{escape(item.status)}</td><td>{escape(item.coverage)}</td><td>{escape(item.limitation)}</td></tr>"
        for item in matrix
    )
    settings = get_settings()
    summary = settings.safe_summary()
    credential_rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{escape(_humanize_config_state(value))}</td></tr>"
        for name, value in [
            ("Tushare Token", summary["tushare_token"]),
            ("iTick API Key", summary["itick"]),
            ("邮件", summary["email"]),
            ("企业微信", summary["wechat"]),
            ("飞书", summary["feishu"]),
            ("AI 增强", summary["llm"]),
        ]
    )
    auth_panel = _render_auth_settings_panel(current_user=current_user, holdings_path=holdings_path)
    health_summary = _render_system_health_summary(
        quality=quality,
        settings_summary=summary,
        current_user=current_user,
    )
    return f"""
    <section class="module" id="module-settings">
      <div class="module-header"><div><h2 class="module-title">检查系统</h2></div><span class="risk-pill mid">{escape(quality.status)}</span></div>
      {health_summary}
      {_retitle_module(_render_compact_data_quality_module(quality), old_id="module-data-quality", new_id="module-settings-quality")}
      <div class="grid-2" style="margin-top:16px">
        <div class="panel"><h3>Provider 矩阵</h3><table class="data-table"><thead><tr><th>数据源</th><th>状态</th><th>覆盖</th><th>限制</th></tr></thead><tbody>{rows}</tbody></table></div>
        <div class="panel"><h3>凭证状态</h3><table class="data-table"><thead><tr><th>项目</th><th>状态</th></tr></thead><tbody>{credential_rows}</tbody></table></div>
      </div>
      {auth_panel}
    </section>"""


def _render_system_health_summary(
    *,
    quality: DataQualityView,
    settings_summary: dict[str, str],
    current_user: AuthUser | None,
) -> str:
    data_state = "正常" if quality.gate_level == "ok" else "需复核"
    email_state = "正常" if settings_summary.get("email") == "configured" else "未配置"
    account_state = "已登录" if current_user is not None else "按当前模式"
    pipeline_status = _read_key_value_status(
        Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily")) / "pipeline.status"
    )
    auto_state = _human_pipeline_status(pipeline_status.get("status", "未执行"))
    cards = [
        ("数据是否正常", data_state, quality.summary),
        ("邮件是否正常", email_state, "用于早间复盘和机会发送。"),
        ("账号是否正常", account_state, "持仓按账号隔离；行情和选股全站共享。"),
        ("自动更新是否正常", auto_state, "每 2 小时刷新一次，失败看下方监控。"),
    ]
    card_html = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong><p class='kpi-foot'>{escape(note)}</p></div>"
        for label, value, note in cards
    )
    return f"""
      <div class="panel">
        <div class="editor-toolbar"><div><h3>系统健康检查</h3><p class="section-subtitle">先看能不能用，再看工程细节。</p></div></div>
        <div class="summary-grid">{card_html}</div>
      </div>"""


def _render_auth_settings_panel(
    *,
    current_user: AuthUser | None = None,
    holdings_path: str = DEFAULT_HOLDINGS_PATH,
) -> str:
    config = AuthConfig.from_env()
    enabled = is_auth_enabled(config)
    status = "已开启" if enabled else "未开启"
    registration_status = "已开放" if should_allow_registration(config) else "未开放"
    username = config.admin_username if enabled else "未配置"
    db_path = str(config.db_path) if enabled else "未启用"
    current_username = (
        current_user.username if current_user is not None else ("未登录" if enabled else "未启用")
    )
    portfolio_mode = "按账号独立" if enabled else "本地单人文件"
    shared_scope = "行情 / 板块 / 选股 / 日报 / 消息配置" if enabled else "本机配置"
    logout_form = (
        """
        <form method="post" action="/logout">
          <button class="ghost-button" type="submit">退出登录</button>
        </form>"""
        if enabled
        else ""
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>账号体系</h3><p class="section-subtitle">账号负责登录和持仓隔离；行情、板块、选股、日报和消息配置保持全站一致。</p></div>
          <span class="portfolio-chip">登录保护：{escape(status)}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>当前账号</span><strong>{escape(current_username)}</strong><p class="kpi-foot">登录后自动使用自己的持仓账本。</p></div>
          <div class="summary-card"><span>持仓隔离</span><strong>{escape(portfolio_mode)}</strong><p class="kpi-foot">当前账本：{escape(holdings_path)}</p></div>
          <div class="summary-card"><span>共享能力</span><strong>全站一致</strong><p class="kpi-foot">{escape(shared_scope)}</p></div>
          <div class="summary-card"><span>开放注册</span><strong>{escape(registration_status)}</strong><p class="kpi-foot">开放后新账号注册即获得访问权限。</p></div>
          <div class="summary-card"><span>登录保护</span><strong>{escape(status)}</strong></div>
          <div class="summary-card"><span>管理员账号</span><strong>{escape(username)}</strong></div>
          <div class="summary-card"><span>账号库</span><strong>{escape(db_path)}</strong><p class="kpi-foot">只显示路径，不显示密码或会话密钥。</p></div>
        </div>
        <form class="portfolio-form-grid" method="post" action="/account/password" style="margin-top:14px">
          <label class="field-stack">当前密码<input name="current_password" type="password" autocomplete="current-password" /></label>
          <label class="field-stack">新密码<input name="new_password" type="password" autocomplete="new-password" /></label>
          <label class="field-stack">确认新密码<input name="confirm_password" type="password" autocomplete="new-password" /></label>
          <div class="form-actions"><button class="primary-button" type="submit">修改密码</button></div>
        </form>
        <div class="portfolio-action-bar" style="margin-top:12px">{logout_form}</div>
      </div>"""


def _render_compact_market_module(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport,
    candidates: CandidatePoolReport,
) -> str:
    top_sector = sectors.sectors[0] if sectors.sectors else None
    top_candidate = candidates.candidates[0] if candidates.candidates else None
    market_action = _market_action_label(market)
    market_reason = _market_decision_reason(market, top_sector)
    breadth_card = (
        f"{_format_market_count(market, 'advancing')} / "
        f"{_format_market_count(market, 'declining')} / "
        f"{_format_market_count(market, 'unchanged')}"
    )
    top_candidate_name = (
        top_candidate.name if top_candidate and candidates.price_reliable else "待更新"
    )
    index_rows = "".join(
        f"<tr><td>{escape(index.name)}</td><td>{index.close:.2f}</td><td>{index.pct_chg:.2f}%</td><td>{index.amount:.1f} 亿</td><td>{escape(_index_signal(index.pct_chg))}</td></tr>"
        for index in market.indices[:3]
    )
    lead_rows = _render_home_sector_rows(
        sorted(sectors.sectors, key=lambda item: item.heat_score, reverse=True)[:5],
        mode="lead",
    )
    opportunity_items = _li_join((market.opportunities or ["暂无明确机会"])[:3])
    risk_items = _li_join((market.risks or ["未触发硬风险"])[:3])
    watch_items = _li_join((market.tomorrow_watch or ["等待下一交易日确认"])[:3])
    decision_rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(value)}</td><td>{escape(note)}</td></tr>"
        for label, value, note in [
            ("上涨/下跌/平盘", breadth_card, _breadth_signal(market.breadth_ratio)),
            (
                "涨停/跌停",
                f"{market.limit_up_count} / {market.limit_down_count}",
                f"{_limit_up_state_label(market)}；{_limit_down_state_label(market)}",
            ),
            (
                "主线",
                top_sector.name if top_sector else "待确认",
                top_sector.rotation_status if top_sector else "等待板块数据",
            ),
            ("候选首位", top_candidate_name, "进入智能选股复核，不等于买入"),
            ("持仓健康度", f"{portfolio.health_score}/100", "决定能否扩大风险暴露"),
        ]
    )
    dimension_rows = "".join(
        f"<tr><td>{escape(item.name)}</td><td>{item.score}</td><td>{escape(item.status)}</td></tr>"
        for item in market.dimensions[:4]
    )
    quick_actions = "".join(
        f'<button class="portfolio-inline-button" type="button" data-jump="{target}">{escape(label)}</button>'
        for target, label in [
            ("sector", "看板块"),
            ("sentiment", "看情绪"),
            ("screener", "筛候选"),
            ("portfolio", "看持仓"),
        ]
    )
    return f"""
    <section class="module" id="module-market">
      <div class="module-header"><div><h2 class="module-title">A股大盘</h2></div><span class="risk-pill low">{escape(market.regime)}</span></div>
      <div class="panel">
        <div class="editor-toolbar"><div><h3>今日大盘 · 市场结论</h3></div><span class="portfolio-chip">{escape(market.trade_date)}</span></div>
        <div class="summary-grid">
          <div class="summary-card"><span>大盘环境</span><strong>{escape(market.regime)}</strong><p class="kpi-foot">{escape(market.summary)}</p></div>
          <div class="summary-card"><span>仓位动作</span><strong>{escape(market_action)}</strong><p class="kpi-foot">{escape(market_reason)}</p></div>
          <div class="summary-card"><span>市场热度</span><strong>{market.heat_score}/100</strong><div class="score-bar"><div class="score-fill" style="width:{market.heat_score}%"></div></div></div>
          <div class="summary-card"><span>主线</span><strong>{escape(top_sector.name if top_sector else "待确认")}</strong><p class="kpi-foot">{escape(top_sector.rotation_status if top_sector else "等待板块数据")}</p></div>
        </div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="panel">
          <h3>关键证据</h3>
          <table class="data-table"><thead><tr><th>项目</th><th>数值</th><th>判断依据</th></tr></thead><tbody>{decision_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>指数</h3>
          <table class="data-table"><thead><tr><th>指数</th><th>收盘</th><th>涨跌</th><th>成交额</th><th>判断</th></tr></thead><tbody>{index_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>市场分析维度</h3>
          <table class="data-table"><thead><tr><th>维度</th><th>评分</th><th>状态</th></tr></thead><tbody>{dimension_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>领涨板块 Top 5</h3>
          <table class="data-table"><thead><tr><th>板块</th><th>涨跌</th><th>热度</th><th>判断依据</th></tr></thead><tbody>{lead_rows}</tbody></table>
        </div>
        <div class="panel">
          <h3>机会与风险 · 机会 / 风险 / 明日</h3>
          <div class="compact-note-grid">
            <div class="compact-note-card"><strong>机会</strong><ul>{opportunity_items}</ul></div>
            <div class="compact-note-card"><strong>风险</strong><ul>{risk_items}</ul></div>
            <div class="compact-note-card"><strong>明日观察</strong><ul>{watch_items}</ul></div>
          </div>
          <div class="portfolio-action-bar" style="margin-top:12px">{quick_actions}</div>
        </div>
      </div>
    </section>"""


def _market_decision_reason(market: MarketSnapshot, top_sector) -> str:
    reasons = [
        f"涨跌家数比 {market.breadth_ratio:.2f}",
        f"涨停 {market.limit_up_count} / 跌停 {market.limit_down_count}",
    ]
    if top_sector is not None:
        reasons.append(f"主线 {top_sector.name}，热度 {top_sector.heat_score}/100")
    if market.heat_score < 50:
        reasons.append("市场热度偏低")
    elif market.heat_score >= 70:
        reasons.append("市场热度偏高")
    return "为什么：" + "；".join(reasons)


def _breadth_signal(value: float) -> str:
    if value >= 1.3:
        return "上涨明显多于下跌，允许看进攻机会。"
    if value >= 0.8:
        return "涨跌接近平衡，适合控制仓位做结构行情。"
    return "下跌多于上涨，优先防守，避免追高。"


def _index_signal(pct_chg: float) -> str:
    if pct_chg >= 1.0:
        return "强，支持风险偏好"
    if pct_chg > 0:
        return "小涨，偏结构行情"
    if pct_chg <= -1.0:
        return "弱，拖累大盘"
    return "偏弱或震荡"


def _render_compact_sector_module(
    sectors: SectorAnalysisReport,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    mainline_tags = "".join(
        f'<span class="tag">{escape(name)}</span>' for name in sectors.market_mainline[:4]
    )
    rows = "".join(
        _render_sector_theme_row(item, candidate_universe) for item in sectors.sectors[:8]
    )
    top = sectors.sectors[0] if sectors.sectors else None
    sector_state = _sector_state_label(top)
    top_representatives = (
        _sector_representative_stocks(top, candidate_universe) if top is not None else "候选池暂无"
    )
    top_reason = _sector_strength_reason(top) if top is not None else "等待板块数据"
    top_strategy = _sector_strategy(top) if top is not None else "等待主线确认"
    return f"""
    <section class="module" id="module-sectors">
      <div class="module-header"><div><h2 class="module-title">主线板块</h2></div><div class="tag-list">{mainline_tags}</div></div>
      <div class="summary-grid">
        <div class="summary-card"><span>主线状态</span><strong>{escape(sector_state)}</strong><p class="kpi-foot">板块结论：{escape(top_strategy)}</p></div>
        <div class="summary-card"><span>最强板块</span><strong>{escape(top.name if top else "--")}</strong><p class="kpi-foot">强势个股：{escape(top_representatives)}</p></div>
        <div class="summary-card"><span>为什么强</span><strong>{escape(top_reason)}</strong><p class="kpi-foot">热度 {top.heat_score if top else 0}/100</p></div>
        <div class="summary-card"><span>持续性判断</span><strong>{escape(top.continuity if top else "等待数据")}</strong><p class="kpi-foot">{escape(_sector_next_check(top) if top else "等待下一交易日确认")}</p></div>
      </div>
      <div class="panel" style="margin-top:16px">
        <h3>主题强弱榜</h3>
        <table class="data-table"><thead><tr><th>主题</th><th>强度证据</th><th>代表个股</th><th>风险点</th><th>操作策略</th><th>下一步验证</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
    </section>"""


def _render_sector_theme_row(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    strong_stock_text = _sector_representative_stocks(item, candidate_universe)
    conclusion = _sector_state_label(item)
    strength = _sector_strength_reason(item)
    next_check = _sector_next_check(item)
    strategy = _sector_strategy(item)
    risk = _sector_risk_text(item)
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>{escape(item.continuity)} · {escape(item.rotation_status)}</span></td>"
        f"<td>{escape(conclusion)}<span>{escape(strength)}</span></td>"
        f"<td>{escape(strong_stock_text)}</td>"
        f"<td>{escape(risk)}</td>"
        f"<td>{escape(strategy)}</td>"
        f"<td>{escape(next_check)}</td></tr>"
    )


def _sector_representative_stocks(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    strong_stocks = _strong_stocks_for_theme(candidate_universe, item.name)
    return (
        "、".join(f"{stock.name} {stock.pct_change:.2f}%" for stock in strong_stocks)
        or "候选池暂无同主题样本"
    )


def _sector_strength_reason(item) -> str:
    parts = [
        f"涨跌 {item.pct_chg:.2f}%",
        f"扩散 {item.advancing_ratio:.0%}",
        f"涨停 {item.limit_up_count}",
        f"成交变化 {item.amount_change:.1f}亿",
    ]
    if item.fund_status:
        parts.append(item.fund_status)
    return "；".join(parts)


def _sector_risk_text(item) -> str:
    if item.risk != "风险可控":
        if item.pct_chg >= 50:
            return f"{item.name}涨幅异常，先核对数据口径"
        if item.amount_change >= 35:
            return f"{item.name}放量过快，防资金兑现"
        if item.limit_up_count <= 1 and item.pct_chg >= 10:
            return f"{item.name}封板不足，防冲高回落"
        return f"{item.name}{item.risk}"
    if item.pct_chg >= 6 and item.limit_up_count <= 1:
        return f"{item.name}涨幅大但前排不足，注意冲高回落"
    if item.advancing_ratio < 0.55:
        return f"{item.name}扩散不足，容易一日游"
    return f"{item.name}风险低，继续确认前排承接"


def _sector_next_check(item) -> str:
    checks = [_sector_primary_next_check(item)]
    if item.limit_up_count >= 3:
        checks.append(f"{item.name}涨停梯队是否晋级")
    elif item.limit_up_count > 0:
        checks.append(f"{item.name}前排是否继续封板")
    else:
        checks.append(f"{item.name}是否出现涨停前排")
    if item.amount_change >= 30:
        checks.append(f"{item.name}放量后能否承接")
    elif item.advancing_ratio >= 0.7:
        checks.append(f"{item.name}扩散能否维持")
    else:
        checks.append(f"{item.name}扩散能否修复")
    return "；".join(dict.fromkeys(checks))


def _sector_primary_next_check(item) -> str:
    if item.pct_chg >= 50:
        return f"{item.name}先核实极端涨幅口径"
    if item.pct_chg >= 12 and item.limit_up_count <= 1:
        return f"{item.name}涨幅与涨停是否匹配"
    if item.amount_change >= 40:
        return f"{item.name}成交放大是否不是出货"
    if item.limit_up_count >= 3:
        return f"{item.name}涨停家数是否继续增加"
    if item.advancing_ratio >= 0.9:
        return f"{item.name}扩散满档后是否分化"
    return f"{item.name}代表个股是否继续强于指数"


def _sector_strategy(item) -> str:
    if item.pct_chg >= 50:
        return "异常涨幅先当口径/事件脉冲，只看龙头换手确认"
    if item.limit_up_count >= 3 and item.amount_change >= 20:
        return f"{item.name}梯队较完整，等龙头分歧回封，不追后排加速"
    if item.amount_change >= 35:
        return f"{item.name}放量 {item.amount_change:.1f} 亿，先看二次承接再观察"
    if item.pct_chg >= 12 and item.limit_up_count <= 1:
        return f"{item.name}涨幅大但封板少，只看首板质量"
    if item.advancing_ratio >= 0.9 and item.risk != "风险可控":
        return f"{item.name}扩散已满，等分化后挑前排"
    if item.risk != "风险可控":
        return f"{item.name}先看前排承接，分歧未消化前不追后排"
    if item.heat_score >= 80 and item.advancing_ratio >= 0.7:
        return f"{item.name}可优先观察，等待回踩或二次确认"
    if item.heat_score >= 60:
        if item.limit_up_count > 0:
            return f"{item.name}轮动观察，只看前排换手和封板质量"
        if item.amount_change >= 15:
            return f"{item.name}轮动观察，等放量后回踩不破再跟踪"
        if item.advancing_ratio >= 0.7:
            return f"{item.name}轮动观察，先确认扩散能否维持"
        return f"{item.name}轮动观察，暂只放入备选队列"
    return f"{item.name}暂不作为主线，只做备选观察"


def _strong_stocks_for_theme(
    candidate_universe: list[CandidateStockRawData],
    theme: str,
) -> list[LimitBoardRow]:
    normalized_theme = theme.strip()
    if not normalized_theme:
        return []
    rows = [
        row
        for row in _build_limit_board_rows(candidate_universe)
        if row.sector.strip() == normalized_theme
    ]
    return sorted(rows, key=lambda item: item.pct_change, reverse=True)[:3]


def _render_limit_table_rows(
    items: list[LimitBoardRow],
    *,
    market: MarketSnapshot | None = None,
) -> str:
    if not items:
        return "<tr><td colspan='5'>暂无样本</td></tr>"
    return "".join(
        "<tr>"
        f"<td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)}</span></td>"
        f"<td>{escape(item.sector)}</td>"
        f"<td>{item.latest_close:.2f}</td>"
        f"<td>{item.pct_change:.2f}%</td>"
        f"<td>{escape(_limit_up_cause(item, market))}</td>"
        "</tr>"
        for item in items
    )


def _limit_up_cause(item: LimitBoardRow, market: MarketSnapshot | None = None) -> str:
    theme = _theme_cause(item.sector)
    mechanism = _price_limit_mechanism(item.code, item.name, item.pct_change, up=True)
    emotion = ""
    if market is not None and market.limit_up_count >= 60:
        emotion = f"；市场涨停 {market.limit_up_count} 家，短线情绪助推"
    elif market is not None and market.limit_up_count >= 25:
        emotion = f"；市场涨停 {market.limit_up_count} 家，局部赚钱效应支撑"
    liquidity = ""
    if item.amount >= 10:
        liquidity = f"；成交额 {item.amount:.1f} 亿，有资金参与"
    elif item.turnover_rate >= 8:
        liquidity = f"；换手 {item.turnover_rate:.1f}%，筹码活跃"
    return f"{theme}；{mechanism}{liquidity}{emotion}"


def _limit_down_cause(item, market: MarketSnapshot) -> str:
    explicit = str(getattr(item, "reason", "") or "").strip()
    pieces: list[str] = []
    if explicit and explicit not in {
        "跌停封板风险",
        "20cm 跌停或极端退潮",
        "20cm 跌停或极端下跌",
        "10cm 跌停或大幅下跌",
    }:
        pieces.append(f"事件线索：{explicit}")
    if _name_has_st_or_delist(item.name):
        pieces.append("名称含 ST/退，优先按退市或流动性风险处理")
    if str(item.name).startswith("C"):
        pieces.append("C字头次新，高波动资金退潮")
    if _is_known_theme(item.sector):
        pieces.append(f"{item.sector}方向退潮或分歧扩散")
    else:
        pieces.append("题材未识别，需复核公告、龙虎榜和盘口异动")
    pieces.append(_price_limit_mechanism(item.code, item.name, item.pct_chg, up=False))
    if market.limit_down_count >= 30:
        pieces.append(f"全市场跌停 {market.limit_down_count} 家，亏钱效应扩散")
    elif market.limit_down_count >= 15:
        pieces.append(f"全市场跌停 {market.limit_down_count} 家，风险偏好下降")
    return "；".join(pieces[:4])


def _theme_cause(sector: str) -> str:
    if _is_known_theme(sector):
        return f"题材驱动：{sector}"
    return "题材未识别，先按个股独立异动观察"


def _is_known_theme(sector: str) -> bool:
    return bool(sector and sector not in {"未识别主题", "未分类", "沪深A股", "主板"})


def _name_has_st_or_delist(name: str) -> bool:
    upper = str(name).upper()
    return "ST" in upper or "退" in str(name)


def _price_limit_mechanism(code: str, name: str, pct_change: float, *, up: bool) -> str:
    abs_pct = abs(pct_change)
    if str(code).startswith(("300", "301", "688")) or abs_pct >= 19.5:
        board = "20cm高弹性"
    elif str(code).startswith(("8", "9")) or abs_pct >= 29.0:
        board = "北交所/高波动"
    else:
        board = "10cm主板"
    direction = "涨停" if up else "跌停"
    if _name_has_st_or_delist(name):
        board = "ST/退市高风险"
    return f"{board}{direction}，幅度 {pct_change:.2f}%"


def _candidate_universe_prices_reliable(universe: list[CandidateStockRawData]) -> bool:
    return bool(universe) and all(item.price_reliable for item in universe)


def _render_compact_portfolio_module(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
    holdings_path: str,
    stock_code: str,
    provider_name: str,
    notice: PortfolioNotice | None,
    edit_code: str,
) -> str:
    public_readonly = _is_public_readonly()
    advice = build_portfolio_advice(
        portfolio,
        market=market,
        holdings_path=holdings_path,
        transactions_path="data/portfolio/transactions.csv",
    )
    advice_by_code = {item.code: item for item in advice.position_advices}
    editing_position = _select_edit_position(portfolio.positions, edit_code)
    editing_advice = advice_by_code.get(editing_position.holding.code) if editing_position else None
    positions = "".join(
        _render_portfolio_table_row(
            position,
            advice_by_code.get(position.holding.code),
            stock_code=stock_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
            readonly=public_readonly,
        )
        for position in portfolio.positions
    )
    if not positions:
        positions = (
            '<tr><td colspan="10"><div class="empty-state">'
            "<strong>还没有持仓</strong>"
            "<p>点击添加持仓，录入股票代码、成本价和持仓数后，系统会自动计算当日盈亏、累计盈亏和组合风险。</p>"
            "</div></td></tr>"
        )
    notice_html = _render_portfolio_notice(notice)
    action_bar = (
        '<div class="portfolio-action-bar"><span class="portfolio-chip">线上安全模式：持仓数据只展示，不改服务器文件</span></div>'
        if public_readonly
        else f'<div class="portfolio-action-bar">{_render_portfolio_new_button()}</div>'
    )
    edit_panel = (
        """
      <div class="quality-banner" id="portfolio-form" style="margin-top:16px">
        当前可以查看组合风险、打开个股分析和复制复盘；新增或编辑持仓请在本地/私有环境完成，避免公开页面修改你的真实持仓文件。
      </div>"""
        if public_readonly
        else f"""
      <details class="detail-shell" id="portfolio-form">
        <summary>{"编辑持仓" if editing_position else "添加持仓"}</summary>
        <div class="detail-body">
          {_render_clear_edit_link(stock_code, provider_name, holdings_path, edit_code)}
          {_render_add_holding_form(stock_code, provider_name, holdings_path, editing_position, editing_advice)}
        </div>
      </details>"""
    )
    return f"""
    <section class="module" id="module-portfolio">
      <div class="module-header"><div><h2 class="module-title">我的持仓</h2></div><div class="module-header-meta"><span class="risk-pill mid">健康度 {portfolio.health_score}/100</span><span class="status-pill">持仓 {len(portfolio.positions)} 只</span></div></div>
      {notice_html}
      <div class="portfolio-kpis">
        {_kpi("总成本", f"{portfolio.total_cost:.2f}", "")}
        {_kpi("总市值", f"{portfolio.total_market_value:.2f}", "")}
        {_kpi("当日盈亏", f"{portfolio.daily_pnl:.2f}", "按前收价自动计算")}
        {_kpi("累计盈亏", f"{portfolio.total_pnl:.2f}", f"{portfolio.total_pnl_ratio:.2f}%")}
        {_kpi("第一大仓位", f"{portfolio.top_position_weight:.1%}", "")}
      </div>
      {_render_portfolio_priority_queue(portfolio, advice_by_code)}
      {_render_portfolio_position_overview(advice)}
      {_render_portfolio_overall_diagnosis(portfolio, market, advice)}
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>持仓列表</h3></div><span class="portfolio-chip">{escape(advice.overall_action)}</span></div>
        {action_bar}
        <table class="data-table portfolio-table"><thead><tr><th>股票</th><th>数量</th><th>成本</th><th>现价</th><th>当日盈亏</th><th>总盈亏</th><th>仓位</th><th>趋势</th><th>建议</th><th>操作</th></tr></thead><tbody>{positions}</tbody></table>
      </div>
      {edit_panel}
    </section>"""


def _render_portfolio_position_overview(advice: PortfolioAdvice) -> str:
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>整体仓位情况</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>记录内股票仓位</span><strong>100%</strong><p class="kpi-foot">现金未录入，仅代表已录入股票篮子</p></div>
          <div class="summary-card"><span>目标现金/低风险</span><strong>{escape(advice.target_cash)}</strong><p class="kpi-foot">按市场和组合风险自动给出</p></div>
          <div class="summary-card"><span>整体动作</span><strong>{escape(advice.overall_action)}</strong><p class="kpi-foot">先控风险，再看扩仓</p></div>
        </div>
      </div>"""


def _render_portfolio_overall_diagnosis(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
    advice: PortfolioAdvice,
) -> str:
    top_position = max(portfolio.positions, key=lambda item: item.weight, default=None)
    best = max(portfolio.positions, key=lambda item: item.pnl, default=None)
    worst = min(portfolio.positions, key=lambda item: item.pnl, default=None)
    top_sector = max(portfolio.sector_weights, key=lambda item: item[1], default=("", 0.0))
    weak_count = sum(
        1
        for position in portfolio.positions
        if position.trend == "下降趋势" or position.risk_level == "高"
    )
    first_step = advice.position_advices[0].name if advice.position_advices else "等待持仓"
    concentration = (
        f"{top_position.holding.name} {top_position.weight:.1%}" if top_position else "暂无持仓"
    )
    pnl_text = (
        f"贡献 {best.holding.name} {best.pnl:.0f} / 拖累 {worst.holding.name} {worst.pnl:.0f}"
        if best and worst
        else "盈亏数据不足"
    )
    sector_text = (
        f"{localize_sector_name(top_sector[0])} {top_sector[1]:.1%}"
        if top_sector[0]
        else "行业未分类"
    )
    top3_weight = sum(
        item.weight
        for item in sorted(portfolio.positions, key=lambda row: row.weight, reverse=True)[:3]
    )
    top3_text = f"{concentration} / 前三大 {top3_weight:.1%}"
    first_risk = portfolio.risk_alerts[0] if portfolio.risk_alerts else "暂无突出风险"
    market_action = _market_action_label(market)
    resonance = (
        f"{weak_count} 只弱势持仓，市场 {market.regime}"
        if weak_count
        else f"暂无明显共振，市场 {market.regime}"
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>组合整体诊断</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>第一大+前三大</span><strong>{escape(top3_text)}</strong></div>
          <div class="summary-card"><span>集中度</span><strong>{escape(concentration)}</strong></div>
          <div class="summary-card"><span>盈亏贡献</span><strong>{escape(pnl_text)}</strong></div>
          <div class="summary-card"><span>行业暴露</span><strong>{escape(sector_text)}</strong></div>
          <div class="summary-card"><span>风险共振</span><strong>{escape(resonance)}</strong></div>
          <div class="summary-card"><span>首要风险</span><strong>{escape(first_risk)}</strong></div>
          <div class="summary-card"><span>组合动作</span><strong>{escape(advice.overall_action)}</strong></div>
          <div class="summary-card"><span>市场约束</span><strong>{escape(market_action)}</strong></div>
          <div class="summary-card"><span>处理优先级</span><strong>{escape(first_step)}</strong></div>
          <div class="summary-card"><span>处理顺序</span><strong>{escape(first_step)}</strong></div>
          <div class="summary-card"><span>现金/低风险</span><strong>{escape(advice.target_cash)}</strong></div>
        </div>
      </div>"""


def _render_compact_stock_module(
    stock: DeepStockReport,
    resolved: ResolvedSymbol,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    trade_plan: TradePlan,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    candidates: CandidatePoolReport,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    driver = stock.upside.drivers[0] if stock.upside.drivers else stock.final_conclusion
    risk = stock.risks[0] if stock.risks else "暂无"
    invalid = stock.invalid_conditions[0] if stock.invalid_conditions else trade_plan.stop_loss
    announcement_rows = _render_announcement_rows(announcement_report)
    holding_view = _render_stock_holding_view(stock.code, portfolio)
    evidence_drawer = _render_stock_evidence_drawer(
        stock=stock,
        stock_raw=stock_raw,
        technical=technical,
        event_radar=event_radar,
        trade_plan=trade_plan,
        quality=quality,
        driver=driver,
        risk=risk,
        invalid=invalid,
    )
    return f"""
    <section class="module" id="module-stock">
      <div class="module-header"><div><h2 class="module-title">个股分析</h2></div><div class="module-header-meta"><span class="risk-pill mid">综合机会评分 {stock.upside.score}/100</span><span class="status-pill">{escape(stock.name)} · {escape(stock.code)}</span></div></div>
      {_render_stock_switcher(resolved, portfolio, candidates, provider_name, holdings_path)}
      <div class="stock-workspace-drawer">
        <div>
          <div class="ticket-grid">
            <div class="ticket-card"><span>收盘</span><strong>{stock.latest_close:.2f}</strong></div>
            <div class="ticket-card"><span>日期</span><strong>{escape(stock.trade_date)}</strong></div>
            <div class="ticket-card"><span>趋势</span><strong>{escape(stock.trend)}</strong></div>
            <div class="ticket-card"><span>风险</span><strong>{escape(stock.risk_level)}</strong></div>
          </div>
          {holding_view}
          {_render_stock_kline_panel(stock, stock_raw, portfolio, quality, technical, trade_plan, event_radar)}
          {_render_stock_compact_research_panel(stock, stock_raw, sectors, technical, event_radar, announcement_report, portfolio, quality, trade_plan, driver, risk, invalid)}
          <details class="detail-shell">
            <summary>公告</summary>
            <div class="detail-body">
              <div class="metric-list"><div class="metric-line"><span>事件闸门</span><strong>{escape(event_radar.gate)}</strong></div><div class="metric-line"><span>事件风险分</span><strong>{event_radar.risk_score}/100</strong></div></div>
              <table class="data-table"><thead><tr><th>日期</th><th>标题</th><th>风险</th><th>链接</th></tr></thead><tbody>{announcement_rows}</tbody></table>
            </div>
          </details>
        </div>
        {evidence_drawer}
      </div>
    </section>"""


def _render_stock_evidence_drawer(
    *,
    stock: DeepStockReport,
    stock_raw: StockRawData,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    trade_plan: TradePlan,
    quality: DataQualityView,
    driver: str,
    risk: str,
    invalid: str,
) -> str:
    news_title = stock_raw.news_items[0].title if stock_raw.news_items else ""
    news_text = news_title or "暂无明确消息事件"
    return f"""
      <aside class="evidence-drawer" aria-label="个股证据抽屉">
        <h3>个股证据抽屉</h3>
        <div class="drawer-row"><span>当前判断</span><strong>{escape(trade_plan.verdict)}</strong></div>
        <div class="drawer-row"><span>交易触发</span><strong>{escape(trade_plan.entry_trigger)}</strong></div>
        <div class="drawer-row"><span>风险原因</span><strong>{escape(risk)}；{escape(invalid)}</strong></div>
        <div class="drawer-row"><span>消息事件</span><strong>{escape(news_text)}</strong></div>
        <div class="drawer-row"><span>数据状态</span><strong>{escape(quality.signal)}</strong></div>
        <div class="drawer-row"><span>技术位置</span><strong>{escape(technical.structure)}</strong></div>
        <div class="drawer-row"><span>机会证据</span><strong>{escape(driver)}</strong></div>
        <div class="drawer-row"><span>事件闸门</span><strong>{escape(event_radar.gate)}</strong></div>
      </aside>"""


def _render_stock_switcher(
    resolved: ResolvedSymbol,
    portfolio: PortfolioAnalysisReport,
    candidates: CandidatePoolReport,
    provider_name: str,
    holdings_path: str,
) -> str:
    holding_links = _stock_quick_links(
        [(position.holding.code, position.holding.name) for position in portfolio.positions[:6]],
        provider_name,
        holdings_path,
    )
    candidate_links = _stock_quick_links(
        [(candidate.code, candidate.name) for candidate in candidates.candidates[:6]],
        provider_name,
        holdings_path,
    )
    return f"""
      <div class="panel stock-switch-panel">
        <div class="editor-toolbar">
          <div><h3>股票筛选</h3><p class="section-subtitle">输入代码或名称，K线和分析会一起切换。</p></div>
        </div>
        <form class="stock-form" method="get" action="{workspace_action("module-stock")}">
          <input type="hidden" name="provider" value="{escape(provider_name)}" />
          <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
          <input name="code" value="{escape(resolved.query)}" placeholder="输入股票代码或名称" />
          <button type="submit">切换股票</button>
        </form>
        <div class="stock-quick-lanes">
          <div class="stock-quick-lane"><span>我的持仓</span><div class="action-list">{holding_links or "<em>暂无持仓快捷</em>"}</div></div>
          <div class="stock-quick-lane"><span>候选前排</span><div class="action-list">{candidate_links or "<em>暂无候选快捷</em>"}</div></div>
        </div>
      </div>"""


def _stock_quick_links(
    items: list[tuple[str, str]],
    provider_name: str,
    holdings_path: str,
) -> str:
    links = []
    seen: set[str] = set()
    for code, name in items:
        if not code or code in seen:
            continue
        seen.add(code)
        query = urlencode({"code": code, "provider": provider_name, "holdings": holdings_path})
        links.append(
            f'<a class="mini-button" href="/?{query}#stock">{escape(name)}<span>{escape(code)}</span></a>'
        )
    return "".join(links)


def _fmt_optional(value: float | None) -> str:
    return "--" if value is None else f"{value:.2f}"


def _stock_sector_strength_text(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    mainline = [localize_sector_name(item) for item in sectors.market_mainline[:3]]
    sector_name = str(getattr(stock, "sector", "") or "").strip()
    if sector_name and sector_name not in {"未分类", "未识别主题"}:
        localized = localize_sector_name(sector_name)
        if localized in mainline:
            return f"{localized} 在主线内"
        return f"{localized}，主线：{'、'.join(mainline) if mainline else '待确认'}"
    return f"主线：{'、'.join(mainline)}" if mainline else "主线未确认"


def _stock_sector_strength_note(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    sector_name = str(getattr(stock, "sector", "") or "").strip()
    sector = next((item for item in sectors.sectors if item.name == sector_name), None)
    if sector is None:
        return "先看所属主题是否在主线，再看个股是否前排。"
    return f"热度 {sector.heat_score}/100，涨跌 {sector.pct_chg:.2f}%，{sector.rotation_status}。"


def _render_stock_compact_research_panel(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    trade_plan: TradePlan,
    driver: str,
    risk: str,
    invalid: str,
) -> str:
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock.code),
        None,
    )
    announcement_count = len(announcement_report.items) if announcement_report else 0
    rows = [
        (
            "技术面",
            f"{stock.trend} · MA5 {_fmt_optional(technical.ma5)}",
            f"盘口技术结构：{technical.structure}；RSI {_fmt_optional(technical.rsi14)}；量能比 {technical.volume_ratio:.2f}",
        ),
        ("基本面", _stock_valuation_text(stock_raw), _stock_valuation_note(stock_raw)),
        ("资金面", _stock_fund_flow_text(stock_raw), _stock_fund_flow_note(stock_raw)),
        (
            "消息/公告",
            _stock_news_text(event_radar, announcement_count, len(stock_raw.news_items)),
            _stock_news_note(stock_raw, event_radar),
        ),
        (
            "概念板块",
            _stock_sector_strength_text(stock, sectors),
            _stock_sector_strength_note(stock, sectors),
        ),
        (
            "成本位置",
            _stock_cost_position_text(position),
            _stock_cost_position_note(position, trade_plan, invalid),
        ),
    ]
    row_html = "".join(
        f"<tr><td><strong>{escape(label)}</strong></td><td>{escape(value)}</td><td>{escape(note)}</td></tr>"
        for label, value, note in rows
    )
    cost_text = (
        f"{position.holding.cost_price:.2f} / 盈亏 {position.pnl_ratio:.2f}%"
        if position
        else "当前账号未持仓"
    )
    cards = [
        ("当前动作", trade_plan.verdict),
        ("目标仓位", trade_plan.target_position),
        ("买入触发 / 开仓条件", _short_condition(trade_plan.entry_trigger, 48)),
        ("加仓条件", _short_condition(trade_plan.add_trigger, 48)),
        ("止损条件", _short_condition(trade_plan.stop_loss, 48)),
        ("降风险条件", _short_condition(trade_plan.reduce_trigger, 48)),
        ("风险边界 / 风控边界", f"{technical.invalid_line:.2f} / {invalid}"),
        ("不做事项", trade_plan.forbidden_actions[0] if trade_plan.forbidden_actions else "无"),
        ("持仓成本", cost_text),
        ("数据质量", quality.status),
    ]
    card_html = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in cards
    )
    risk_points = [
        risk,
        invalid,
        quality.warnings[0] if quality.warnings else "未触发数据质量硬风险",
    ]
    risk_html = _li_join([_short_condition(item, 70) for item in risk_points])
    trade_snapshot = [
        ("最终动作", trade_plan.verdict),
        ("今天怎么做", getattr(trade_plan, "today_action", trade_plan.reason)),
        ("买点/触发", _short_condition(trade_plan.entry_trigger, 54)),
        ("卖点/止损", _short_condition(trade_plan.stop_loss, 54)),
    ]
    trade_snapshot_html = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in trade_snapshot
    )
    scorecard_html = _render_stock_professional_scorecard(stock_raw, portfolio)
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>交易快照</h3><p class="section-subtitle">先看最终动作、触发和止损，再看证据。</p></div></div>
        <div class="summary-grid compact-summary-grid">{trade_snapshot_html}</div>
      </div>
      <div class="grid-2 stock-research-grid" style="margin-top:16px">
        <div class="panel">
          <h3>核心证据链 / 6 维判断 / 6个证据</h3>
          <div class="quality-banner good" style="margin-bottom:12px"><strong>一句最终动作：</strong>{escape(trade_plan.verdict)}；{escape(trade_plan.today_action if hasattr(trade_plan, "today_action") else trade_plan.entry_trigger)}</div>
          <table class="data-table"><thead><tr><th>维度</th><th>结论</th><th>依据</th></tr></thead><tbody>{row_html}</tbody></table>
        </div>
        <div class="panel">
          <h3>明确操作建议 / 执行条件 / 操作条件</h3>
          <div class="summary-grid compact-summary-grid">{card_html}</div>
        </div>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>3个风险</h3><p class="section-subtitle">只保留会改变今天动作的风险。</p></div></div>
        <ul class="reason-list">{risk_html}</ul>
      </div>
      {scorecard_html}"""


def _render_stock_professional_scorecard(
    stock_raw: StockRawData,
    portfolio: PortfolioAnalysisReport,
) -> str:
    if not stock_raw.bars:
        return ""
    report = analyze_stock(stock_raw)
    position = next(
        (item for item in portfolio.positions if item.holding.code == report.code), None
    )
    conflicts = "".join(f"<li>{escape(item)}</li>" for item in report.decision.core_conflicts[:3])
    holding_html = ""
    if position is not None:
        holding_state = _stock_holding_state(position)
        holding_html = f"""
        <div class="summary-card">
          <span>持仓成本视角</span><strong>{escape(holding_state)}</strong>
          <p class="kpi-foot">成本 {position.holding.cost_price:.2f} · 盈亏 {position.pnl_ratio:.2f}% · 仓位 {position.weight:.1%}</p>
        </div>"""
    decision_html = f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>决策摘要</h3><p class="section-subtitle">先给结论，再看证据；缺数据时降级为观察。</p></div>
          <span class="portfolio-chip">数据可信度：{escape(report.decision.data_reliability)}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>最终判断</span><strong>{escape(report.decision.verdict)}</strong><p class="kpi-foot">{escape(report.decision.today_action)}</p></div>
          <div class="summary-card"><span>今日动作</span><strong>{escape(report.decision.today_action)}</strong></div>
          <div class="summary-card"><span>不能做什么</span><strong>{escape(report.decision.forbidden_action)}</strong></div>
          <div class="summary-card"><span>转强条件</span><strong>{escape(report.decision.strengthen_condition)}</strong></div>
          <div class="summary-card"><span>离场条件</span><strong>{escape(report.decision.exit_condition)}</strong></div>
          {holding_html}
        </div>
        <div class="quality-banner" style="margin-top:12px"><strong>核心矛盾</strong><ul class="note-list">{conflicts}</ul></div>
      </div>"""
    rows = "".join(
        "<tr>"
        f"<td><strong>{escape(item.name)}</strong></td>"
        f"<td>{item.score}/100 · {escape(item.status)}</td>"
        f"<td>{escape(item.evidence)}</td>"
        f"<td>{escape(item.action)}</td>"
        "</tr>"
        for item in report.dimensions
    )
    return f"""{decision_html}
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>专业评分卡</h3></div>
        </div>
        <table class="data-table"><thead><tr><th>维度评分</th><th>分数</th><th>证据</th><th>动作</th></tr></thead><tbody>{rows}</tbody></table>
      </div>"""


def _stock_holding_state(position: PositionAnalysis) -> str:
    if position.pnl >= 0 and position.trend == "下降趋势":
        return "保护利润"
    if position.pnl < 0 and position.trend == "上升趋势":
        return "修复观察"
    if position.pnl < 0 and (position.trend == "下降趋势" or position.risk_level in {"高", "中"}):
        return "问题仓"
    if position.pnl >= 0 and position.trend == "上升趋势":
        return "保护利润 / 趋势持有"
    return "成本复核"


def _stock_cost_position_text(position: PositionAnalysis | None) -> str:
    if position is None:
        return "未持仓"
    if position.pnl_ratio >= 15:
        return f"盈利 {position.pnl_ratio:.2f}%"
    if position.pnl_ratio <= -10:
        return f"亏损 {abs(position.pnl_ratio):.2f}%"
    return f"接近成本 {position.pnl_ratio:.2f}%"


def _stock_cost_position_note(
    position: PositionAnalysis | None,
    trade_plan: TradePlan,
    invalid: str,
) -> str:
    if position is None:
        return "当前账号没有成本价，先按技术触发和风控线观察。"
    if position.pnl_ratio >= 15:
        return f"成本 {position.holding.cost_price:.2f}；优先保护利润，减仓触发：{trade_plan.reduce_trigger}"
    if position.pnl_ratio <= -10:
        return f"成本 {position.holding.cost_price:.2f}；不补亏，失效条件：{invalid}"
    return f"成本 {position.holding.cost_price:.2f}；按买入/止损触发执行，不临时加仓。"


def _stock_chart_url(stock_code: str, provider_name: str, holdings_path: str) -> str:
    query = urlencode(
        {
            "code": stock_code,
            "provider": provider_name,
            "holdings": holdings_path,
        }
    )
    return f"/?{query}#stock"


def _render_stock_kline_panel(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    technical: TechnicalProfile,
    trade_plan: TradePlan,
    event_radar: EventRadar,
) -> str:
    chart_id = f"kline-screen-{_safe_dom_id(stock.code)}"
    chart_payload = _kline_payload(stock_raw)
    latest = stock_raw.bars[-1] if stock_raw.bars else None
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock.code),
        None,
    )
    cost_line = f"{position.holding.cost_price:.2f}" if position else "未持仓"
    pnl_text = f"{position.pnl_ratio:.2f}%" if position else "未持仓"
    intraday_state = _intraday_state(stock_raw)
    signal_cards = _render_trade_signal_cards(
        technical=technical,
        trade_plan=trade_plan,
        latest_close=stock.latest_close,
        cost_price=position.holding.cost_price if position else None,
    )
    trend_rows = _render_five_day_trend_rows(
        stock=stock,
        technical=technical,
        trade_plan=trade_plan,
        event_radar=event_radar,
        quality=quality,
    )
    checklist = _li_join(trade_plan.intraday_checklist[:4])
    data_json = escape(json.dumps(chart_payload, ensure_ascii=False), quote=False)
    return f"""
    <div class="trading-screen stock-kline-panel">
      <div class="editor-toolbar">
        <div><h3>K线交易屏</h3><p class="section-subtitle">KLineChart：K线、分时状态、买卖条件和未来5天情景集中在本页。</p></div>
        <div class="toolbar-actions">
          <button type="button" class="mini-button" data-action="save-stock-plan">保存个股计划</button>
          <span class="portfolio-chip">{escape(quality.signal)}</span>
        </div>
      </div>
      <div class="trading-hero">
        <div class="trading-price-card">
          <span>当前价</span><strong>{stock.latest_close:.2f}</strong>
          <p>{escape(stock.trade_date)} · {escape(stock.trend)} · 机会分 {stock.upside.score}/100</p>
        </div>
        <div class="trading-price-card">
          <span>我的成本</span><strong>{escape(cost_line)}</strong>
          <p>持仓盈亏 {escape(pnl_text)}</p>
        </div>
        <div class="trading-price-card">
          <span>支撑 / 压力</span><strong>{technical.support:.2f} / {technical.resistance:.2f}</strong>
          <p>失效线 {technical.invalid_line:.2f}</p>
        </div>
        <div class="trading-price-card">
          <span>事件闸门</span><strong>{escape(event_radar.gate)}</strong>
          <p>事件风险 {event_radar.risk_score}/100</p>
        </div>
      </div>
      <div class="trading-grid">
        <div class="trading-chart-panel">
          <div class="trading-chart-toolbar">
            <strong>日K · MA · 成交量</strong>
            <div class="trading-tabs" aria-label="周期切换"><span class="active">日K</span><span>分时</span><span>5分钟</span><span>30分钟</span><span>周K</span></div>
          </div>
          <div class="kline-chart-host" id="{chart_id}" data-kline-screen></div>
          <div class="kline-fallback" data-kline-fallback>正在加载 KLineChart；如果网络拦截 CDN，将保留右侧交易计划。</div>
          <script type="application/json" data-kline-payload="{chart_id}">{data_json}</script>
          <div class="chart-level-rails">
            <span>买点：{escape(_short_condition(trade_plan.entry_trigger))}</span>
            <span>卖点/止损：{escape(_short_condition(trade_plan.stop_loss))}</span>
            <span>成本线：{escape(cost_line)}</span>
          </div>
        </div>
        <aside class="trading-side-panel">
          <div class="panel tight-panel">
            <h3>分时交易</h3>
            <div class="metric-list">
              <div class="metric-line"><span>状态</span><strong>{escape(intraday_state)}</strong></div>
              <div class="metric-line"><span>昨收/今收</span><strong>{escape(_latest_price_pair(latest, stock_raw))}</strong></div>
              <div class="metric-line"><span>量能比</span><strong>{technical.volume_ratio:.2f}</strong></div>
            </div>
            <p class="section-subtitle">分钟级成交明细必须等 TDX MCP 分时快照接入；当前不伪造分时线。</p>
          </div>
          <div class="panel tight-panel">
            <h3>建议买点 / 卖点</h3>
            <div class="trading-signal-grid">{signal_cards}</div>
          </div>
          <div class="panel tight-panel">
            <h3>盘中检查</h3>
            <ul class="note-list">{checklist}</ul>
          </div>
        </aside>
      </div>
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>未来5天交易趋势</h3><p class="section-subtitle">用情景推演表达，不承诺涨跌；每天只看一个关键条件。</p></div></div>
        <table class="data-table"><thead><tr><th>时间</th><th>趋势情景</th><th>关键价位</th><th>建议动作</th></tr></thead><tbody>{trend_rows}</tbody></table>
      </div>
      <script>{_kline_screen_script()}</script>
    </div>"""


def _safe_dom_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value) or "stock"


def _kline_payload(stock_raw: StockRawData) -> list[dict[str, float | int | str]]:
    return [
        {
            "timestamp": _date_to_timestamp_ms(bar.date),
            "date": bar.date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "volume": bar.volume,
        }
        for bar in stock_raw.bars[-180:]
    ]


def _date_to_timestamp_ms(date_text: str) -> int:
    try:
        from datetime import datetime

        return int(datetime.fromisoformat(date_text[:10]).timestamp() * 1000)
    except ValueError:
        return 0


def _intraday_state(stock_raw: StockRawData) -> str:
    sources = {item.lower() for item in stock_raw.data_sources}
    if any("minute" in item or "intraday" in item or "分时" in item for item in sources):
        return "已接入分时"
    return "分钟数据未接入"


def _latest_price_pair(latest, stock_raw: StockRawData) -> str:
    if latest is None:
        return "无日线"
    previous = stock_raw.bars[-2].close if len(stock_raw.bars) >= 2 else latest.close
    return f"{previous:.2f} / {latest.close:.2f}"


def _short_condition(text: str, limit: int = 36) -> str:
    cleaned = str(text).replace("；", "，").split("，")[0].strip()
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "..."


def _render_trade_signal_cards(
    *,
    technical: TechnicalProfile,
    trade_plan: TradePlan,
    latest_close: float,
    cost_price: float | None,
) -> str:
    cost_note = f"成本 {cost_price:.2f}" if cost_price is not None else "未持仓"
    items = [
        ("买点", _short_condition(trade_plan.entry_trigger), f"现价 {latest_close:.2f}"),
        ("加仓", _short_condition(trade_plan.add_trigger), f"压力 {technical.resistance:.2f}"),
        ("卖点/止损", _short_condition(trade_plan.stop_loss), f"失效 {technical.invalid_line:.2f}"),
        ("止盈", _short_condition(trade_plan.take_profit), cost_note),
    ]
    return "".join(
        f"<div class='trading-signal-card'><span>{escape(label)}</span><strong>{escape(value)}</strong><p>{escape(note)}</p></div>"
        for label, value, note in items
    )


def _render_five_day_trend_rows(
    *,
    stock: DeepStockReport,
    technical: TechnicalProfile,
    trade_plan: TradePlan,
    event_radar: EventRadar,
    quality: DataQualityView,
) -> str:
    latest = stock.latest_close
    rows = [
        (
            "T+1",
            _trend_case(latest, technical),
            f"{technical.support:.2f} / {technical.resistance:.2f}",
            "先看是否站稳昨日收盘，不追高开回落。",
        ),
        (
            "T+2",
            "放量确认",
            f"MA5 {technical.ma5:.2f}" if technical.ma5 else f"现价 {latest:.2f}",
            _short_condition(trade_plan.entry_trigger, 42),
        ),
        (
            "T+3",
            "分歧复核",
            f"止损 {technical.invalid_line:.2f}",
            _short_condition(trade_plan.reduce_trigger, 42),
        ),
        ("T+4", "主线验证", f"压力 {technical.resistance:.2f}", "板块仍在前排才保留进攻计划。"),
        (
            "T+5",
            "去留决策",
            f"目标 {max(technical.resistance, latest * 1.06):.2f}",
            _five_day_final_action(event_radar, quality),
        ),
    ]
    return "".join(
        f"<tr><td>{escape(day)}</td><td>{escape(scene)}</td><td>{escape(price)}</td><td>{escape(action)}</td></tr>"
        for day, scene, price, action in rows
    )


def _trend_case(latest: float, technical: TechnicalProfile) -> str:
    if latest >= technical.resistance:
        return "突破后确认"
    if latest <= technical.support * 1.03:
        return "支撑位防守"
    return "区间震荡"


def _five_day_final_action(event_radar: EventRadar, quality: DataQualityView) -> str:
    if quality.gate_level == "blocked":
        return "数据闸门未恢复前，只观察不执行。"
    if event_radar.gate == "事件需复核":
        return "公告风险未排除前，以降风险为主。"
    return "满足价格、量能、板块三项再保留交易计划。"


def _kline_screen_script() -> str:
    return r"""
    (function () {
      if (window.StockTsKlineScreens) {
        window.StockTsKlineScreens.refresh();
        return;
      }
      const state = { loading: false, loaded: !!(window.klinecharts || window.KLineChart) };
      function ensureLibrary(callback) {
        if (window.klinecharts || window.KLineChart) {
          state.loaded = true;
          callback();
          return;
        }
        if (state.loading) {
          window.setTimeout(() => ensureLibrary(callback), 120);
          return;
        }
        state.loading = true;
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/klinecharts@9.6.0/dist/klinecharts.min.js';
        script.onload = () => { state.loaded = true; callback(); };
        script.onerror = () => { state.loaded = false; };
        document.head.appendChild(script);
      }
      function renderOne(host) {
        if (!host || host.dataset.chartReady === '1') return;
        if (host.offsetWidth < 80 || host.offsetHeight < 80) return;
        const payloadNode = document.querySelector(`script[data-kline-payload="${host.id}"]`);
        if (!payloadNode) return;
        let rows = [];
        try { rows = JSON.parse(payloadNode.textContent || '[]'); } catch (_error) { rows = []; }
        if (!rows.length) return;
        ensureLibrary(() => {
          const lib = window.klinecharts || window.KLineChart;
          if (!lib || typeof lib.init !== 'function') return;
          try {
            const chart = lib.init(host);
            chart.applyNewData(rows);
            if (chart.createIndicator) {
              try { chart.createIndicator('MA', false, { id: 'candle_pane' }); } catch (_error) {}
              try { chart.createIndicator('VOL'); } catch (_error) {}
            }
            host.dataset.chartReady = '1';
            const fallback = host.parentElement ? host.parentElement.querySelector('[data-kline-fallback]') : null;
            if (fallback) fallback.hidden = true;
          } catch (_error) {
            host.dataset.chartReady = '0';
          }
        });
      }
      window.StockTsKlineScreens = {
        refresh() {
          document.querySelectorAll('[data-kline-screen]').forEach(renderOne);
        }
      };
      if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.StockTsKlineScreens.refresh());
      } else {
        window.StockTsKlineScreens.refresh();
      }
    })();
    """


def _render_stock_holding_view(stock_code: str, portfolio: PortfolioAnalysisReport) -> str:
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock_code),
        None,
    )
    if position is None:
        return """
        <div class="quality-banner" style="margin-top:14px">
          这只股票当前不在你的持仓里；如需按成本价分析，请先到“持仓风控”添加持仓。
        </div>"""
    cost_gap = position.latest_price - position.holding.cost_price
    cost_gap_ratio = (
        cost_gap / position.holding.cost_price * 100 if position.holding.cost_price else 0.0
    )
    if position.pnl >= 0:
        cost_note = "当前高于成本价，后续分析已结合你的成本价，重点看止盈和利润回撤。"
    else:
        cost_note = "当前低于成本价，后续分析已结合你的成本价，重点看失效线和是否继续持有。"
    return f"""
        <div class="panel" style="margin-top:14px">
          <div class="editor-toolbar">
            <div><h3>我的持仓视角 / 持仓成本视角</h3><p class="section-subtitle">{escape(cost_note)}</p></div>
            <span class="portfolio-chip">持仓数 {_format_form_number(position.holding.shares)}</span>
          </div>
          <div class="summary-grid">
            <div class="summary-card"><span>我的成本价</span><strong>{position.holding.cost_price:.2f}</strong></div>
            <div class="summary-card"><span>现价</span><strong>{position.latest_price:.2f}</strong></div>
            <div class="summary-card"><span>当日盈亏</span><strong>{position.daily_pnl:.2f}</strong><p class="kpi-foot">{position.daily_pnl_ratio:.2f}%</p></div>
            <div class="summary-card"><span>总盈亏</span><strong>{position.pnl:.2f}</strong><p class="kpi-foot">{position.pnl_ratio:.2f}%</p></div>
            <div class="summary-card"><span>距离成本价</span><strong>{cost_gap:.2f}</strong><p class="kpi-foot">{cost_gap_ratio:.2f}%</p></div>
          </div>
        </div>"""


def _render_stock_evidence_chain(
    stock: DeepStockReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    trade_plan: TradePlan,
) -> str:
    risk = stock.risks[0] if stock.risks else "暂无"
    invalid = stock.invalid_conditions[0] if stock.invalid_conditions else trade_plan.stop_loss
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>核心证据链</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>趋势证据</span><strong>{escape(stock.trend)}</strong><p class="kpi-foot">{escape(technical.structure)}</p></div>
          <div class="summary-card"><span>风险边界</span><strong>{escape(stock.risk_level)}</strong><p class="kpi-foot">{escape(risk)}；{escape(invalid)}</p></div>
          <div class="summary-card"><span>公告闸门</span><strong>{escape(event_radar.gate)}</strong><p class="kpi-foot">事件风险 {event_radar.risk_score}/100</p></div>
          <div class="summary-card"><span>操作条件</span><strong>{escape(trade_plan.verdict)}</strong><p class="kpi-foot">{escape(trade_plan.entry_trigger)}</p></div>
        </div>
      </div>"""


def _render_stock_five_dimension_panel(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
) -> str:
    pct = _stock_recent_pct(stock_raw)
    latest_volume = stock_raw.bars[-1].volume if stock_raw.bars else 0
    avg_volume = (
        sum(bar.volume for bar in stock_raw.bars[-5:]) / min(len(stock_raw.bars), 5)
        if stock_raw.bars
        else 0
    )
    volume_text = f"量能 {latest_volume / avg_volume:.2f}x" if avg_volume else "量能数据不足"
    pe_text = _stock_valuation_text(stock_raw)
    fund_text = _stock_fund_flow_text(stock_raw)
    news_count = len(announcement_report.items) if announcement_report else 0
    stock_news_count = len(stock_raw.news_items)
    news_text = _stock_news_text(event_radar, news_count, stock_news_count)
    concept_text = "、".join(localize_sector_name(item) for item in sectors.market_mainline[:3])
    rows = [
        ("基本面", pe_text, _stock_valuation_note(stock_raw)),
        ("资金面", fund_text, _stock_fund_flow_note(stock_raw)),
        ("消息面", news_text, _stock_news_note(stock_raw, event_radar)),
        ("统计面", f"近一日 {pct:.2f}% · {volume_text}", technical.structure),
        ("概念板块", concept_text or "概念映射未接入", "先看主线共振，再看个股位置"),
    ]
    cards = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong><p class='kpi-foot'>{escape(note)}</p></div>"
        for label, value, note in rows
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>五维分析</h3>
        <div class="summary-grid">{cards}</div>
        <div class="metric-list" style="margin-top:12px">
          <div class="metric-line"><span>综合判断</span><strong>{escape(stock.final_conclusion)}</strong></div>
        </div>
        {_render_stock_news_items(stock_raw)}
      </div>"""


def _render_stock_professional_diagnosis(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
) -> str:
    position = next((item for item in portfolio.positions if item.holding.code == stock.code), None)
    pct = _stock_recent_pct(stock_raw)
    volume_ratio = _stock_volume_ratio(stock_raw)
    cost_text = (
        f"成本 {position.holding.cost_price:.2f}，浮盈亏 {position.pnl_ratio:.2f}%"
        if position
        else "未在持仓中"
    )
    sector_text = "、".join(localize_sector_name(item) for item in sectors.market_mainline[:3])
    announcement_count = len(announcement_report.items) if announcement_report else 0
    rows = [
        (
            "技术趋势",
            stock.trend,
            f"{technical.structure}；支撑 {technical.support:.2f}，压力 {technical.resistance:.2f}",
        ),
        (
            "量价结构",
            f"近一日 {pct:.2f}% · 量能 {volume_ratio:.2f}x"
            if volume_ratio
            else f"近一日 {pct:.2f}%",
            "放量上涨优于缩量冲高；放量下跌需要降低观察优先级。",
        ),
        ("估值位置", _stock_valuation_text(stock_raw), _stock_valuation_note(stock_raw)),
        ("资金行为", _stock_fund_flow_text(stock_raw), _stock_fund_flow_note(stock_raw)),
        (
            "公告舆情",
            _stock_news_text(event_radar, announcement_count, len(stock_raw.news_items)),
            _stock_news_note(stock_raw, event_radar),
        ),
        ("板块强弱", sector_text or "主线未确认", "先看所属主题是否在主线，再看个股是否前排。"),
        ("持仓成本", cost_text, "有持仓时按成本价看止损、止盈和利润回撤；无持仓只做观察。"),
        (
            "风控边界",
            stock.invalid_conditions[0] if stock.invalid_conditions else "等待失效条件",
            f"风险等级 {stock.risk_level}；事件闸门 {event_radar.gate}。",
        ),
        (
            "证据充分度",
            quality.signal,
            "K线、资金、新闻、公告任一缺失时，结论降级为观察，不直接执行。",
        ),
    ]
    cards = "".join(
        "<div class='summary-card'>"
        f"<span>{escape(label)}</span><strong>{escape(value)}</strong>"
        f"<p class='kpi-foot'>{escape(note)}</p></div>"
        for label, value, note in rows
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>压缩证据</h3><p class="section-subtitle">先看证据是否充分，再看机会分；缺数据时不硬给买卖结论。</p></div>
        </div>
        <div class="summary-grid">{cards}</div>
      </div>"""


def _stock_valuation_text(stock_raw: StockRawData) -> str:
    if stock_raw.pe_ttm is None:
        return "估值未接入"
    pb = _optional_number(stock_raw.valuation.get("pb"))
    total_mv = _optional_number(stock_raw.valuation.get("total_mv"))
    parts = [f"PE(TTM) {stock_raw.pe_ttm:.1f}"]
    if pb is not None:
        parts.append(f"PB {pb:.2f}")
    if total_mv is not None:
        parts.append(f"市值 {total_mv / 100000000:.0f} 亿")
    return " · ".join(parts)


def _stock_valuation_note(stock_raw: StockRawData) -> str:
    source = stock_raw.valuation.get("source")
    date = stock_raw.valuation.get("date")
    if source:
        return f"来源 {source}{' · ' + str(date) if date else ''}"
    return "财务质量、营收利润和估值分位待接入"


def _stock_fund_flow_text(stock_raw: StockRawData) -> str:
    if stock_raw.fund_flow is None:
        return "资金明细未接入"
    pct = _optional_number(stock_raw.fund_flow_detail.get("main_net_pct"))
    source = str(stock_raw.fund_flow_detail.get("source") or "")
    label = "成交侧" if "active_volume" in source else "主力"
    direction = "净流入" if stock_raw.fund_flow >= 0 else "净流出"
    pct_text = f" · 净占比 {pct:.2f}%" if pct is not None else ""
    return f"{label}{direction} {abs(stock_raw.fund_flow):.2f} 亿{pct_text}"


def _stock_fund_flow_note(stock_raw: StockRawData) -> str:
    source = stock_raw.fund_flow_detail.get("source")
    date = stock_raw.fund_flow_detail.get("date")
    if source:
        return f"来源 {source}{' · ' + str(date) if date else ''}"
    return "当前优先使用资金/成交侧信号，不伪造主力净流"


def _stock_news_text(
    event_radar: EventRadar, announcement_count: int, stock_news_count: int
) -> str:
    parts = [event_radar.gate]
    if announcement_count:
        parts.append(f"公告 {announcement_count} 条")
    if stock_news_count:
        parts.append(f"新闻 {stock_news_count} 条")
    return "，".join(parts)


def _stock_news_note(stock_raw: StockRawData, event_radar: EventRadar) -> str:
    if stock_raw.news_items:
        first = stock_raw.news_items[0]
        return f"{first.source or '新闻源'}：{first.title}"
    return f"事件风险 {event_radar.risk_score}/100"


def _stock_volume_ratio(stock_raw: StockRawData) -> float:
    if not stock_raw.bars:
        return 0.0
    latest_volume = stock_raw.bars[-1].volume
    avg_volume = sum(bar.volume for bar in stock_raw.bars[-5:]) / min(len(stock_raw.bars), 5)
    return latest_volume / avg_volume if avg_volume else 0.0


def _render_stock_news_items(stock_raw: StockRawData) -> str:
    if not stock_raw.news_items:
        return ""
    rows = "".join(
        f"<tr><td>{escape(item.date[:10])}</td><td>{escape(item.source)}</td><td>{escape(item.title)}</td></tr>"
        for item in stock_raw.news_items[:5]
    )
    return f"""
        <div style="margin-top:12px">
          <table class="data-table"><thead><tr><th>日期</th><th>来源</th><th>个股新闻</th></tr></thead><tbody>{rows}</tbody></table>
        </div>"""


def _optional_number(value: object) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stock_recent_pct(stock_raw: StockRawData) -> float:
    if len(stock_raw.bars) < 2:
        return 0.0
    previous = stock_raw.bars[-2].close
    if not previous:
        return 0.0
    return (stock_raw.bars[-1].close - previous) / previous * 100


def _render_execution_conditions_panel(trade_plan: TradePlan) -> str:
    forbidden = trade_plan.forbidden_actions[0] if trade_plan.forbidden_actions else "无"
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>执行条件</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>开仓条件</span><strong>{escape(trade_plan.entry_trigger)}</strong></div>
          <div class="summary-card"><span>加仓条件</span><strong>{escape(trade_plan.add_trigger)}</strong></div>
          <div class="summary-card"><span>止损条件</span><strong>{escape(trade_plan.stop_loss)}</strong></div>
          <div class="summary-card"><span>降风险条件</span><strong>{escape(trade_plan.reduce_trigger)}</strong></div>
          <div class="summary-card"><span>不做事项</span><strong>{escape(forbidden)}</strong></div>
          <div class="summary-card"><span>执行结论</span><strong>{escape(trade_plan.verdict)} · {trade_plan.conviction}/100</strong></div>
        </div>
      </div>"""


def _render_compact_report_module(
    daily: DailyWorkflowResult,
    quality: DataQualityView,
    risk_gate: RiskGateView,
) -> str:
    one_liner = _extract_markdown_highlights(
        daily.markdown,
        "## 今日一句话",
        fallback="等待摘要",
    )[:1]
    candidate_value = (
        f"{len(daily.candidates.candidates)} 只" if quality.candidate_price_reliable else "排序暂停"
    )
    tomorrow_plan = (
        daily.market.tomorrow_watch[0] if daily.market.tomorrow_watch else "等待市场刷新"
    )
    risk_review = risk_gate.gate
    data_review = quality.signal
    latest_artifact = _render_latest_daily_artifact()
    return f"""
    <section class="module" id="module-report">
      <div class="module-header"><div><h2 class="module-title">每日复盘</h2></div><div class="module-header-meta"><span class="risk-pill mid">{escape(daily.market.trade_date)}</span></div></div>
      <div class="summary-grid">
        <div class="summary-card"><span>一句话</span><strong>{escape(_localize_display_text(one_liner[0] if one_liner else "等待摘要"))}</strong></div>
        <div class="summary-card"><span>市场</span><strong>{escape(daily.market.regime)}</strong></div>
        <div class="summary-card"><span>候选</span><strong>{escape(candidate_value)}</strong></div>
      </div>
      <div class="summary-grid" style="margin-top:16px">
        <div class="summary-card"><span>明日计划</span><strong>{escape(tomorrow_plan)}</strong></div>
        <div class="summary-card"><span>风险复核</span><strong>{escape(risk_review)}</strong><p class="kpi-foot">{escape(risk_gate.reason)}</p></div>
        <div class="summary-card"><span>数据复核</span><strong>{escape(data_review)}</strong></div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        {_render_daily_market_block(daily.market)}
        {_render_daily_sector_block(daily.sectors)}
        {_render_daily_portfolio_block(daily.portfolio)}
        {_render_daily_opportunity_block(daily.candidates, quality)}
      </div>
      {latest_artifact}
      <button class="ghost-button" type="button" data-copy-report>复制报告</button>
    </section>"""


def _render_latest_daily_artifact() -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    markdown_path = report_dir / "latest.md"
    status_path = report_dir / "latest.status"
    pipeline_path = report_dir / "pipeline.status"
    if not markdown_path.exists():
        return """
      <div class="panel" style="margin-top:16px">
        <h3>最新自动日报</h3>
        <div class="empty-state"><strong>未生成</strong><p>服务器定时任务跑通后，这里会显示盘后自动报告。</p></div>
      </div>"""
    markdown = markdown_path.read_text(encoding="utf-8", errors="ignore")
    status = _read_key_value_status(status_path)
    highlights = _extract_markdown_highlights(
        markdown,
        "## 今日一句话",
        fallback="最新自动日报已生成，请结合数据日期复核。",
    )[:3]
    portfolio_items = _extract_markdown_highlights(
        markdown,
        "## 持仓分析",
        fallback=[],
    )[:3]
    boundary_items = _extract_markdown_highlights(
        markdown,
        "## 数据边界",
        fallback=[],
    )[:3]
    trade_date = status.get("trade_date", "待确认")
    generated_at = status.get("generated_at", "待确认")
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>最新自动日报</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>生成状态</span><strong>{escape(status.get("status", "ok"))}</strong></div>
          <div class="summary-card"><span>交易日</span><strong>{escape(trade_date)}</strong></div>
          <div class="summary-card"><span>更新时间</span><strong>{escape(generated_at)}</strong></div>
        </div>
        <div class="panel-actions"><a class="ghost-button" href="#daily">查看完整报告</a></div>
        <div class="compact-note-grid" style="margin-top:12px">
          <div class="compact-note-card"><strong>结论</strong><ul>{_li_join([_localize_display_text(item) for item in highlights])}</ul></div>
          <div class="compact-note-card"><strong>持仓</strong><ul>{_li_join([_localize_display_text(item) for item in portfolio_items] or ["报告内暂无持仓摘要"])}</ul></div>
          <div class="compact-note-card"><strong>数据边界</strong><ul>{_li_join([_localize_display_text(item) for item in boundary_items] or ["未触发额外边界提示"])}</ul></div>
        </div>
        {_render_pipeline_status_panel(pipeline_path)}
      </div>"""


def _read_key_value_status(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    status: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        status[key.strip()] = value.strip()
    return status


def _render_pipeline_status_panel(status_path: Path | None = None) -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    path = status_path or (report_dir / "pipeline.status")
    status = _read_key_value_status(path)
    if not status:
        return """
        <div class="compact-note-card" style="margin-top:12px">
          <strong>流水线状态</strong>
          <ul><li>未生成 pipeline.status，等待下一次定时任务。</li></ul>
        </div>"""
    step_labels = [
        ("refresh", "全市场刷新"),
        ("tdx_enrich", "TDX补强"),
        ("external_enrich", "外部补强"),
        ("announcements", "公告"),
        ("report", "日报"),
    ]
    items = "".join(
        f"<li><strong>{escape(label)}</strong>：{escape(_human_pipeline_status(status.get(key, '未执行')))}</li>"
        for key, label in step_labels
    )
    meta = " · ".join(
        item
        for item in [
            f"状态 {status.get('status', 'unknown')}",
            status.get("generated_at", ""),
        ]
        if item
    )
    return f"""
        <div class="compact-note-card" style="margin-top:12px">
          <strong>流水线状态</strong>
          <p class="kpi-foot">{escape(meta)}</p>
          <ul>{items}</ul>
        </div>"""


def _render_automation_monitor_panel() -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    pipeline_path = report_dir / "pipeline.status"
    status = _read_key_value_status(pipeline_path)
    if not status:
        return """
        <div class="panel" style="margin-top:16px">
          <h3>自动更新监控</h3>
          <div class="empty-state">
            <strong>还没有运行记录</strong>
            <p>未找到 pipeline.status；请等待下一次定时任务，或先手动运行每日数据流水线。</p>
          </div>
        </div>"""
    generated_at = status.get("generated_at", "未记录")
    freshness = _automation_freshness_label(generated_at)
    failed_steps = _automation_failed_steps(status)
    advice = _automation_advice(failed_steps)
    step_rows = "".join(
        f"<tr><td>{escape(label)}</td><td>{escape(_human_pipeline_status(status.get(key, '未执行')))}</td></tr>"
        for key, label in [
            ("refresh", "全市场刷新"),
            ("tdx_enrich", "TDX补强"),
            ("external_enrich", "外部补强"),
            ("announcements", "公告"),
            ("report", "日报生成"),
        ]
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>自动更新监控</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>运行节奏</span><strong>每 2 小时</strong><p class="kpi-foot">服务器定时刷新行情、K线、新闻、公告和日报。</p></div>
          <div class="summary-card"><span>最近运行</span><strong>{escape(generated_at)}</strong><p class="kpi-foot">{escape(freshness)}</p></div>
          <div class="summary-card"><span>整体状态</span><strong>{escape(_human_pipeline_status(status.get("status", "未知")))}</strong><p class="kpi-foot">以 pipeline.status 为准。</p></div>
          <div class="summary-card"><span>处理建议</span><strong>{escape(advice)}</strong><p class="kpi-foot">先看 pipeline.status，再看定时任务日志。</p></div>
        </div>
        <table class="data-table" style="margin-top:12px"><thead><tr><th>步骤</th><th>结果</th></tr></thead><tbody>{step_rows}</tbody></table>
      </div>"""


def _automation_freshness_label(generated_at: str) -> str:
    if not generated_at or generated_at == "未记录":
        return "未记录运行时间"
    try:
        generated = datetime.fromisoformat(generated_at[:19])
    except ValueError:
        return "运行时间格式待复核"
    age_hours = (datetime.now() - generated).total_seconds() / 3600
    if age_hours <= 3:
        return "新鲜：在 3 小时内"
    if age_hours <= 8:
        return "需关注：超过 3 小时"
    return "已滞后：超过 8 小时"


def _automation_failed_steps(status: dict[str, str]) -> list[str]:
    failed = []
    labels = {
        "refresh": "全市场刷新",
        "tdx_enrich": "TDX补强",
        "external_enrich": "外部补强",
        "announcements": "公告",
        "report": "日报生成",
    }
    for key, label in labels.items():
        value = status.get(key, "")
        if str(value).lower().startswith(("failed", "partial")):
            failed.append(label)
    return failed


def _automation_advice(failed_steps: list[str]) -> str:
    if not failed_steps:
        return "继续观察"
    if "日报生成" in failed_steps:
        return "先修复日报"
    if "全市场刷新" in failed_steps or "TDX补强" in failed_steps:
        return "先修复行情"
    if "外部补强" in failed_steps:
        return "先复核新闻/资金"
    if "公告" in failed_steps:
        return "先复核公告"
    return "先看失败步骤"


def _human_pipeline_status(value: str) -> str:
    clean = str(value or "").strip()
    if not clean or clean == "未执行":
        return "未执行"
    lower = clean.lower()
    if lower == "ok":
        return "完成"
    if lower.startswith("failed"):
        if "timeout" in lower or "timed out" in lower:
            return "失败：超时"
        return "失败：待复核"
    if lower.startswith("partial"):
        if "news" in lower or "moneyflow" in lower:
            return "部分完成：新闻/资金缺口"
        return "部分完成"
    return _short_condition(clean.replace("subprocess.", ""), 36)


def _render_daily_market_block(market: MarketSnapshot) -> str:
    index_rows = "".join(
        f"<tr><td>{escape(item.name)}</td><td>{item.close:.2f}</td><td>{item.pct_chg:.2f}%</td></tr>"
        for item in market.indices[:4]
    )
    watch_items = _li_join([_localize_display_text(item) for item in market.tomorrow_watch[:3]])
    risk_items = _li_join([_localize_display_text(item) for item in market.risks[:2]])
    return f"""
        <div class="panel">
          <h3>大盘情况</h3>
          <div class="summary-grid">
            <div class="summary-card"><span>市场状态</span><strong>{escape(market.regime)}</strong></div>
            <div class="summary-card"><span>市场热度</span><strong>{market.heat_score}/100</strong></div>
            <div class="summary-card"><span>涨停 / 跌停</span><strong>{market.limit_up_count} / {market.limit_down_count}</strong></div>
          </div>
          <h3 style="margin-top:16px">主要指数</h3>
          <table class="data-table"><thead><tr><th>指数</th><th>收盘</th><th>涨跌</th></tr></thead><tbody>{index_rows}</tbody></table>
          <div class="compact-note-grid" style="margin-top:12px">
            <div class="compact-note-card"><strong>明日观察</strong><ul>{watch_items}</ul></div>
            <div class="compact-note-card"><strong>风险</strong><ul>{risk_items}</ul></div>
          </div>
        </div>"""


def _render_daily_sector_block(sectors: SectorAnalysisReport) -> str:
    mainline = [localize_sector_name(item) for item in sectors.market_mainline[:4]]
    mainline_tags = "".join(f'<span class="tag">{escape(item)}</span>' for item in mainline)
    rows = "".join(
        f"<tr><td>{escape(localize_sector_name(item.name))}</td><td>{item.heat_score}</td><td>{item.pct_chg:.2f}%</td><td>{escape(item.continuity)}</td></tr>"
        for item in sectors.sectors[:6]
    )
    notes = _li_join([_localize_display_text(item) for item in sectors.rotation_notes[:3]])
    return f"""
        <div class="panel">
          <h3>板块情况</h3>
          <div class="metric-list">
            <div class="metric-line"><span>主线板块</span><strong>{mainline_tags or "待确认"}</strong></div>
          </div>
          <table class="data-table" style="margin-top:12px"><thead><tr><th>板块</th><th>热度</th><th>涨跌</th><th>持续性</th></tr></thead><tbody>{rows}</tbody></table>
          <div class="compact-note-card" style="margin-top:12px"><strong>轮动判断</strong><ul>{notes}</ul></div>
        </div>"""


def _render_daily_portfolio_block(portfolio: PortfolioAnalysisReport | None) -> str:
    if portfolio is None:
        return """
        <div class="panel">
          <h3>我的持仓</h3>
          <div class="empty-state"><strong>未接入持仓</strong><p>添加持仓后展示组合健康度、行业暴露和持仓明细。</p></div>
        </div>"""
    sector_line = "、".join(
        f"{localize_sector_name(sector)} {weight:.1%}"
        for sector, weight in portfolio.sector_weights[:3]
    )
    rows = "".join(
        f"<tr><td class='name-cell'><strong>{escape(position.holding.name)}</strong><span>{escape(position.holding.code)}</span></td><td>{position.weight:.1%}</td><td>{position.pnl_ratio:.2f}%</td><td>{escape(position.trend)}</td><td>{escape(position.risk_level)}</td></tr>"
        for position in sorted(portfolio.positions, key=lambda item: item.weight, reverse=True)[:6]
    )
    if not rows:
        rows = (
            '<tr><td colspan="5"><div class="empty-state">'
            "<strong>还没有持仓</strong><p>添加持仓后展示组合健康度、行业暴露和持仓明细。</p>"
            "</div></td></tr>"
        )
    risk_items = _li_join([_localize_display_text(item) for item in portfolio.risk_alerts[:3]])
    return f"""
        <div class="panel">
          <h3>我的持仓</h3>
          <div class="summary-grid">
            <div class="summary-card"><span>组合健康度</span><strong>{portfolio.health_score}/100</strong></div>
            <div class="summary-card"><span>累计盈亏</span><strong>{portfolio.total_pnl_ratio:.2f}%</strong></div>
            <div class="summary-card"><span>第一大仓位</span><strong>{portfolio.top_position_weight:.1%}</strong></div>
          </div>
          <div class="metric-list" style="margin-top:12px"><div class="metric-line"><span>行业暴露</span><strong>{escape(sector_line or "未分类")}</strong></div></div>
          <h3 style="margin-top:16px">持仓明细</h3>
          <table class="data-table"><thead><tr><th>股票</th><th>仓位</th><th>盈亏</th><th>趋势</th><th>风险</th></tr></thead><tbody>{rows}</tbody></table>
          <div class="compact-note-card" style="margin-top:12px"><strong>持仓风险</strong><ul>{risk_items}</ul></div>
        </div>"""


def _render_daily_opportunity_block(
    candidates: CandidatePoolReport,
    quality: DataQualityView,
) -> str:
    if not quality.candidate_price_reliable:
        return """
        <div class="panel">
          <h3>未来机会</h3>
          <div class="empty-state"><strong>候选排序暂停</strong><p>缺少真实日线时不展示机会排序，避免误导。</p></div>
        </div>"""
    rows = "".join(
        f"<tr><td>{index}</td><td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)} · {escape(localize_sector_name(item.sector))}</span></td><td>{item.score}</td><td>{item.pct_change:.2f}%</td><td>{escape(item.watch_conditions[0] if item.watch_conditions else '等待承接确认')}</td></tr>"
        for index, item in enumerate(candidates.candidates[:6], start=1)
    )
    return f"""
        <div class="panel">
          <h3>未来机会</h3>
          <div class="summary-grid">
            <div class="summary-card"><span>候选数量</span><strong>{len(candidates.candidates)} 只</strong></div>
            <div class="summary-card"><span>机会观察</span><strong>{escape(candidates.candidates[0].name if candidates.candidates else "暂无")}</strong></div>
            <div class="summary-card"><span>数据状态</span><strong>{escape(quality.signal)}</strong></div>
          </div>
          <table class="data-table" style="margin-top:12px"><thead><tr><th>#</th><th>股票</th><th>分数</th><th>涨跌</th><th>触发</th></tr></thead><tbody>{rows}</tbody></table>
        </div>"""


def _render_compact_data_quality_module(quality: DataQualityView) -> str:
    quality_class = {
        "ok": "good",
        "warn": "",
        "blocked": "high",
    }.get(quality.gate_level, "")
    candidate_status = "可用" if quality.candidate_price_reliable else "排序暂停"
    universe_status = "可用" if quality.candidate_universe_reliable else "暂停展示"
    blocked = "、".join(quality.blocked_actions) if quality.blocked_actions else "无"
    warnings = _li_join(quality.warnings or ["未触发告警"])
    source_route = "".join(
        f'<div class="compact-metric-card"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
        for label, value in [
            ("主源", "TDX MCP"),
            ("兜底", "Tushare"),
            ("补充", "AKShare"),
            ("跨市场", "港股 / 美股"),
        ]
    )
    return f"""
    <section class="module" id="module-data-quality">
      <div class="module-header"><div><h2 class="module-title">数据质量</h2></div><span class="risk-pill mid">{escape(quality.status)}</span></div>
      <div class="summary-grid">
        <div class="summary-card"><span>全局数据信号</span><strong>{escape(quality.signal)}</strong></div>
        <div class="summary-card"><span>数据闸门</span><strong>{escape(quality.summary)}</strong></div>
        <div class="summary-card"><span>来源</span><strong>TDX MCP</strong></div>
        <div class="summary-card"><span>个股日期</span><strong>{escape(quality.latest_date)}</strong></div>
        <div class="summary-card"><span>大盘日期</span><strong>{escape(quality.market_date)}</strong></div>
        <div class="summary-card"><span>候选价格</span><strong>{escape(candidate_status)}</strong></div>
        <div class="summary-card"><span>涨跌样本</span><strong>{escape(universe_status)}</strong></div>
      </div>
      <div class="grid-2" style="margin-top:16px">
        <div class="quality-banner {quality_class}"><strong>暂停项：</strong>{escape(blocked)}</div>
        <div class="panel"><h3>告警</h3><ul class="note-list">{warnings}</ul></div>
      </div>
      <div class="panel" style="margin-top:16px">
        <h3>数据源路由</h3>
        <div class="compact-metric-grid">{source_route}</div>
        {_render_pipeline_status_panel()}
      </div>
      {_render_automation_monitor_panel()}
    </section>"""


def _render_compact_status_module(
    provider_name: str,
    holdings_path: str,
    provider_class: str,
    stock_code: str,
    notice: SettingsNotice | None,
) -> str:
    settings = get_settings()
    summary = settings.safe_summary()
    notice_html = _render_settings_notice(notice)
    email_status = _email_config_status_label(settings)
    wechat_status = _humanize_config_state(summary["wechat"])
    feishu_status = _humanize_config_state(summary["feishu"])
    report_style_options = "".join(
        f'<option value="{item}"{" selected" if item == settings.notification_report_style else ""}>{item}</option>'
        for item in ["auto", "full", "digest", "action"]
    )
    report_channels = ",".join(settings.notification_report_channels or [])
    cards = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in [
            ("邮件", email_status),
            ("企业微信", wechat_status),
            ("飞书", feishu_status),
            ("数据源", "TDX MCP"),
            ("适配器", provider_class),
        ]
    )
    if _is_public_readonly():
        return f"""
    <section class="module" id="module-status">
      <div class="module-header"><div><h2 class="module-title">消息渠道</h2></div></div>
      {notice_html}
      <div class="summary-grid">{cards}</div>
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>邮件日报</h3></div>
          <span class="portfolio-chip">服务器定时发送</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>发送内容</span><strong>每日复盘摘要</strong></div>
          <div class="summary-card"><span>发送时间</span><strong>工作日 08:30</strong></div>
          <div class="summary-card"><span>当前操作</span><strong>预览 / 复制</strong></div>
        </div>
        <div class="portfolio-action-bar" style="margin-top:14px">
          <button class="primary-button" type="button" data-action="send-dry-run">生成预览</button>
          <button class="ghost-button" type="button" data-copy-report>复制复盘内容</button>
        </div>
      </div>
    </section>"""
    return f"""
    <section class="module" id="module-status">
      <div class="module-header"><div><h2 class="module-title">消息渠道</h2></div></div>
      {notice_html}
      <div class="summary-grid">{cards}</div>
      <details class="detail-shell">
        <summary>渠道配置</summary>
        <div class="detail-body">
          <form class="inline-form" method="post" action="/settings">
            <input type="hidden" name="page_code" value="{escape(stock_code)}" />
            <input type="hidden" name="provider" value="{escape(provider_name)}" />
            <input type="hidden" name="holdings_path" value="{escape(holdings_path)}" />
            <input type="hidden" name="settings_provider" value="{WEB_DATA_PROVIDER}" />
            <div class="portfolio-form-grid">
              <label class="field-stack field-span-2">日报通道<input name="notification_report_channels" value="{escape(report_channels)}" placeholder="email,wechat,feishu" /></label>
              <label class="field-stack">日报样式<select name="notification_report_style">{report_style_options}</select></label>
              <label class="field-stack">邮件发送账号<input name="email_sender" value="{escape(settings.email_sender)}" /></label>
              <label class="field-stack">邮件密码<input type="password" name="email_password" value="" placeholder="留空保持原值" /></label>
              <label class="field-stack field-span-2">企业微信 Webhook<input type="password" name="wechat_webhook_url" value="" placeholder="留空保持原值" /></label>
              <label class="field-stack field-span-2">飞书 Webhook<input type="password" name="feishu_webhook_url" value="" placeholder="留空保持原值" /></label>
              <label class="field-stack field-span-2">iTick API Key<input type="password" name="itick_api_key" value="" placeholder="留空保持原值" /></label>
            </div>
            <div class="form-actions"><button class="primary-button" type="submit">保存配置</button></div>
          </form>
        </div>
      </details>
      <details class="detail-shell">
        <summary>测试</summary>
        <div class="detail-body">
          <form class="inline-form" method="post" action="/notification-test">
            <input type="hidden" name="page_code" value="{escape(stock_code)}" />
            <input type="hidden" name="provider" value="{escape(provider_name)}" />
            <input type="hidden" name="holdings_path" value="{escape(holdings_path)}" />
            <div class="portfolio-form-grid">
              <label class="field-stack">测试通道<select name="test_channel"><option value="email">email</option><option value="wechat">wechat</option><option value="feishu">feishu</option></select></label>
              <label class="field-stack">消息样式<select name="test_style">{report_style_options}</select></label>
              <input type="hidden" name="test_subject" value="{PUBLIC_SITE_NAME} 通知测试" />
              <input type="hidden" name="test_content" value="测试消息" />
              <label class="checkbox-line"><input type="checkbox" name="test_dry_run" value="1" checked />dry-run 不会真实发送</label>
            </div>
            <div class="form-actions"><button class="primary-button" type="submit">发送测试消息</button></div>
          </form>
        </div>
      </details>
      <details class="detail-shell">
        <summary>发送</summary>
        <div class="detail-body">
          <form class="inline-form" method="post" action="/dispatch-daily">
            <input type="hidden" name="page_code" value="{escape(stock_code)}" />
            <input type="hidden" name="provider" value="{escape(provider_name)}" />
            <input type="hidden" name="holdings_path" value="{escape(holdings_path)}" />
            <div class="portfolio-form-grid">
              <label class="field-stack field-span-2">发送通道<input name="dispatch_channels" value="{escape(report_channels)}" placeholder="email,wechat,feishu" /></label>
              <label class="field-stack">消息样式<select name="dispatch_style">{report_style_options}</select></label>
              <label class="checkbox-line"><input type="checkbox" name="dispatch_dry_run" value="1" checked />dry-run 不会真实发送</label>
            </div>
            <div class="form-actions"><button class="primary-button" type="submit" data-action="send-dry-run">发送今日复盘</button></div>
          </form>
        </div>
      </details>
    </section>"""


def _channel_readiness_tips(summary: dict[str, str]) -> list[str]:
    tips: list[str] = []
    if summary["email"] == "missing":
        tips.append("邮件通道尚未完成配置，如需发给个人或领导，先补齐发送账号、授权码和接收人。")
    if summary["wechat"] == "missing":
        tips.append("微信通道尚未配置，建议至少保留一个企业微信 webhook 作为快速通知出口。")
    if summary["feishu"] == "missing":
        tips.append("飞书通道未配置，如团队主要在飞书沟通，可以补一个群 webhook。")
    if summary["llm"] == "configured":
        tips.append("AI 增强已启用，适合先生成更完整的文字结论，再通过消息渠道对外发送。")
    if not tips:
        tips.append("当前主要发送通道都已准备好，可以直接做 dry-run 或发送正式复盘。")
    tips.append("真实发送前，先确认默认日报样式和发送通道是否与今天的使用场景一致。")
    return tips


def _humanize_config_state(value: str) -> str:
    return {
        "configured": "已配置",
        "missing": "待配置",
    }.get(value, value)


def _email_config_status_label(settings: object) -> str:
    sender = bool(getattr(settings, "email_sender", "").strip())
    password = bool(getattr(settings, "email_password", "").strip())
    if sender and password:
        return "已配置"
    if sender and not password:
        return "缺邮箱授权码"
    if password and not sender:
        return "缺发送账号"
    return "待配置"


def _humanize_feature_state(value: str) -> str:
    return {
        "configured": "已启用",
        "missing": "未启用",
    }.get(value, value)


def _render_channel_overview_cards(
    *,
    email_status: str,
    wechat_status: str,
    feishu_status: str,
) -> str:
    return "".join(
        [
            f"<div class='action-card'><strong>邮件</strong><p class='section-subtitle'>状态：{escape(email_status)}。适合给个人、领导或需要归档的日报发送。</p></div>",
            f"<div class='action-card'><strong>企业微信</strong><p class='section-subtitle'>状态：{escape(wechat_status)}。适合发盘后提醒、重点结论和团队同步。</p></div>",
            f"<div class='action-card'><strong>飞书</strong><p class='section-subtitle'>状态：{escape(feishu_status)}。适合把复盘直接同步到协作群。</p></div>",
        ]
    )


def _render_dispatch_action_cards(
    *,
    route: str,
    style: str,
    llm_status: str,
) -> str:
    return "".join(
        [
            f"<div class='action-card'><strong>默认路由</strong><p class='section-subtitle'>当前默认发送到 {escape(route)}，正式发送前先核对是否符合今天的使用场景。</p></div>",
            f"<div class='action-card'><strong>消息样式</strong><p class='section-subtitle'>当前默认样式 {escape(style)}，先用测试消息确认格式，再推送正式复盘。</p></div>",
            f"<div class='action-card'><strong>AI 文字增强</strong><p class='section-subtitle'>当前状态：{escape(llm_status)}。启用时更适合先生成完整结论，再对外发送。</p></div>",
        ]
    )


def _render_channel_test_cards(
    *,
    email_status: str,
    wechat_status: str,
    feishu_status: str,
) -> str:
    return "".join(
        [
            f"<div class='action-card'><strong>Email</strong><p class='section-subtitle'>状态：{escape(email_status)}。适合测试邮件标题、正文样式和归档链路。</p></div>",
            f"<div class='action-card'><strong>企业微信</strong><p class='section-subtitle'>状态：{escape(wechat_status)}。适合测试群提醒、Markdown 样式和 webhook 是否可达。</p></div>",
            f"<div class='action-card'><strong>飞书</strong><p class='section-subtitle'>状态：{escape(feishu_status)}。适合测试团队群接收和消息展示格式。</p></div>",
        ]
    )


def _render_dispatch_checks(
    *,
    route: str,
    style: str,
) -> str:
    return "".join(
        [
            f"<div class='action-card'><strong>检查路由</strong><p class='section-subtitle'>确认今天需要发送到 {escape(route)}，避免把复盘推到错误群或错误邮箱。</p></div>",
            f"<div class='action-card'><strong>检查样式</strong><p class='section-subtitle'>确认使用 {escape(style)} 样式，必要时先用测试消息看最终呈现。</p></div>",
            "<div class='action-card'><strong>检查 dry-run</strong><p class='section-subtitle'>最近一次 dry-run 无误后，再取消勾选正式发送，避免临门一脚出错。</p></div>",
        ]
    )


SESSION_COOKIE_NAME = "stock_ts_session"


def render_login_page(
    config: AuthConfig | None = None,
    *,
    error: str = "",
    next_path: str = "/",
) -> str:
    config = config or AuthConfig.from_env()
    error_html = f'<div class="login-error">{escape(error)}</div>' if error else ""
    register_html = ""
    if should_allow_registration(config):
        register_html = f"""
      <details class="login-register">
        <summary>没有账号？注册一个</summary>
        <form class="login-form login-form-register" method="post" action="/register">
          <input type="hidden" name="next" value="{escape(next_path, quote=True)}" />
          <label>注册邮箱<input name="username" type="email" autocomplete="username" placeholder="name@example.com" required /></label>
          <label>设置密码<input name="password" type="password" autocomplete="new-password" minlength="8" placeholder="至少 8 位" required /></label>
          <label>确认密码<input name="confirm_password" type="password" autocomplete="new-password" minlength="8" placeholder="再次输入密码" required /></label>
          <button type="submit">注册账号并进入</button>
        </form>
      </details>"""
    body = f"""
  <main class="login-page">
    <section class="login-card" aria-label="账号登录">
      <div class="login-side">
        <div class="brand-mark login-brand">
          <div class="logo">{PUBLIC_SITE_LOGO}</div>
          <div><div class="brand-title">{PUBLIC_SITE_NAME}</div><div class="brand-subtitle">A股投资研究终端</div></div>
        </div>
        <div class="login-side-copy">
          <span class="login-kicker">Research Terminal</span>
          <h1>投研工作台</h1>
          <p>同一套行情、板块、选股和日报能力；每个账号只隔离自己的持仓账本。</p>
        </div>
        <div class="login-proof-grid" aria-label="能力说明">
          <div><span>01</span><strong>持仓隔离</strong><p>每个账号独立成本和仓位。</p></div>
          <div><span>02</span><strong>数据共用</strong><p>行情、主题、日报保持一致。</p></div>
          <div><span>03</span><strong>风险优先</strong><p>先看风险，再做决策。</p></div>
        </div>
      </div>
      <div class="login-panel">
        <span class="login-kicker">Secure Access</span>
        <h2>账号登录</h2>
        <p>登录后查看你的持仓、设置和消息自动化。</p>
        {error_html}
        <form class="login-form" method="post" action="/login" autocomplete="off" data-login-form="login">
          <input type="hidden" name="next" value="{escape(next_path, quote=True)}" />
          <label>账号<input name="username" type="email" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="输入邮箱或账号" data-remember-username required /></label>
          <label>密码<input name="password" type="password" autocomplete="new-password" data-login-password data-lpignore="true" data-1p-ignore="true" placeholder="输入密码" required /></label>
          <label class="login-remember-row"><input name="remember_username" type="checkbox" value="1" data-remember-account /> <span>记住账号</span></label>
          <button type="submit">登录</button>
        </form>
        {register_html}
        <div class="login-foot">研究、观察、条件、风险；不构成投资建议。</div>
      </div>
    </section>
  </main>
  <script>
    (function () {{
      const rememberKey = 'stockTsRememberedUsername';
      function bootLoginMemory() {{
        const form = document.querySelector('[data-login-form="login"]');
        if (!form) return;
        const username = form.querySelector('[data-remember-username]');
        const password = form.querySelector('[data-login-password]');
        const remember = form.querySelector('[data-remember-account]');
        let userTouched = false;
        if (username) {{
          username.addEventListener('input', () => {{
            userTouched = true;
          }});
        }}
        function applyRememberedUsername() {{
          let remembered = '';
          try {{
            remembered = localStorage.getItem(rememberKey) || '';
          }} catch (_error) {{
            remembered = '';
          }}
          if (password) {{
            password.value = '';
          }}
          if (remembered && username && !userTouched) {{
            username.value = remembered;
            if (remember) remember.checked = true;
          }} else if (!remembered && username && !userTouched) {{
            username.value = '';
            if (remember) remember.checked = false;
          }}
        }}
        applyRememberedUsername();
        window.setTimeout(applyRememberedUsername, 80);
        window.setTimeout(applyRememberedUsername, 450);
        form.addEventListener('submit', () => {{
          if (!username || !remember) return;
          try {{
            if (remember.checked && username.value.trim()) {{
              localStorage.setItem(rememberKey, username.value.trim());
            }} else {{
              localStorage.removeItem(rememberKey);
            }}
          }} catch (_error) {{
            // 登录不依赖浏览器本地存储。
          }}
        }});
      }}
      if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', bootLoginMemory, {{ once: true }});
      }} else {{
        bootLoginMemory();
      }}
    }})();
  </script>"""
    return render_document(body)


def should_allow_registration(config: AuthConfig | None = None) -> bool:
    config = config or AuthConfig.from_env()
    return is_auth_enabled(config) and bool(config.allow_registration)


def should_require_login(
    path: str,
    *,
    headers: dict[str, str],
    config: AuthConfig | None = None,
) -> bool:
    config = config or AuthConfig.from_env()
    parsed_path = urlparse(path).path
    if parsed_path in {"/login", "/register", "/healthz"}:
        return False
    if not is_auth_enabled(config):
        return False
    return user_from_cookie_header(headers.get("Cookie", ""), config=config) is None


def user_from_cookie_header(
    cookie_header: str,
    *,
    config: AuthConfig | None = None,
) -> AuthUser | None:
    config = config or AuthConfig.from_env()
    if not is_auth_enabled(config):
        return None
    token = _session_token_from_cookie(cookie_header)
    if not token:
        return None
    session = SessionManager(
        config.session_secret,
        ttl_seconds=config.session_ttl_seconds,
    ).verify_session(token)
    if session is None:
        return None
    store = _auth_store(config)
    _bootstrap_auth_admin(config, store)
    return store.get_user(session.user_id)


def _session_token_from_cookie(cookie_header: str) -> str:
    if not cookie_header:
        return ""
    cookie = SimpleCookie()
    try:
        cookie.load(cookie_header)
    except Exception:
        return ""
    morsel = cookie.get(SESSION_COOKIE_NAME)
    return morsel.value if morsel is not None else ""


def _auth_store(config: AuthConfig | None = None) -> UserStore:
    config = config or AuthConfig.from_env()
    return UserStore(config.db_path)


def _bootstrap_auth_admin(
    config: AuthConfig | None = None,
    store: UserStore | None = None,
) -> AuthUser | None:
    config = config or AuthConfig.from_env()
    if not is_auth_enabled(config):
        return None
    store = store or _auth_store(config)
    return store.bootstrap_admin(config.admin_username, config.admin_password)


def _session_cookie_header(
    token: str,
    *,
    max_age: int,
    secure: bool,
) -> str:
    parts = [
        f"{SESSION_COOKIE_NAME}={token}",
        "Path=/",
        f"Max-Age={max_age}",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def _clear_session_cookie_header() -> str:
    return f"{SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"


def _is_secure_request(headers: object) -> bool:
    proto = ""
    try:
        proto = str(headers.get("X-Forwarded-Proto", ""))
    except AttributeError:
        proto = ""
    return proto.lower() == "https" or os.getenv("STOCK_TS_COOKIE_SECURE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _safe_next_path(value: str) -> str:
    parsed = urlparse(value or "/")
    if parsed.scheme or parsed.netloc:
        return "/"
    path = parsed.path or "/"
    if path in {"/login", "/logout", "/register"}:
        return "/"
    query = f"?{parsed.query}" if parsed.query else ""
    fragment = f"#{parsed.fragment}" if parsed.fragment else ""
    return f"{path}{query}{fragment}"


def _effective_holdings_path(
    user: AuthUser | None,
    requested_path: str = DEFAULT_HOLDINGS_PATH,
) -> str:
    if user is None:
        return requested_path or DEFAULT_HOLDINGS_PATH
    return str(_ensure_user_holdings_file(user))


def _ensure_user_holdings_file(user: AuthUser) -> Path:
    holdings_path = _user_portfolio_dir(user) / "holdings.csv"
    if holdings_path.exists():
        return holdings_path
    holdings_path.parent.mkdir(parents=True, exist_ok=True)
    holdings_path.write_text("code,name,shares,cost_price,sector,note\n", encoding="utf-8")
    return holdings_path


def _user_portfolio_dir(user: AuthUser) -> Path:
    base_dir = Path(os.getenv("STOCK_TS_USER_DATA_DIR", DEFAULT_USER_DATA_DIR))
    return base_dir / str(user.id)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        config = AuthConfig.from_env()
        if parsed.path == "/healthz":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/login":
            query = parse_qs(parsed.query)
            body = render_login_page(
                config,
                error=query.get("error", [""])[0],
                next_path=query.get("next", ["/"])[0],
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if should_require_login(self.path, headers=self.headers, config=config):
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": _safe_next_path(self.path),
                    }
                ),
            )
            self.end_headers()
            return
        current_user = user_from_cookie_header(self.headers.get("Cookie", ""), config=config)
        query = parse_qs(parsed.query)
        code = query.get("code", [""])[0]
        edit_code = query.get("edit", [""])[0]
        candidate_code = query.get("candidate", [""])[0]
        candidate_group = query.get("candidate_tier", ["all"])[0]
        candidate_strategy = query.get("candidate_strategy", ["all"])[0]
        provider_name = WEB_DATA_PROVIDER
        requested_holdings_path = query.get("holdings", [DEFAULT_HOLDINGS_PATH])[0]
        holdings_path = _effective_holdings_path(current_user, requested_holdings_path)
        notice_message = query.get("notice", [""])[0]
        notice_level = query.get("notice_level", ["success"])[0]
        portfolio_notice = (
            PortfolioNotice(level=notice_level, message=notice_message) if notice_message else None
        )
        settings_notice_message = query.get("settings_notice", [""])[0]
        settings_notice_level = query.get("settings_notice_level", ["success"])[0]
        settings_notice = (
            SettingsNotice(level=settings_notice_level, message=settings_notice_message)
            if settings_notice_message
            else None
        )
        body = render_page(
            stock_code=code,
            provider_name=provider_name,
            holdings_path=holdings_path,
            portfolio_notice=portfolio_notice,
            settings_notice=settings_notice,
            edit_code=edit_code,
            candidate_code=candidate_code,
            candidate_group=candidate_group,
            candidate_strategy=candidate_strategy,
            current_user=current_user,
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/login":
            self._handle_login_post()
            return
        if parsed.path == "/register":
            self._handle_register_post()
            return
        if parsed.path == "/logout":
            self.send_response(303)
            self.send_header("Set-Cookie", _clear_session_cookie_header())
            self.send_header("Location", "/login")
            self.end_headers()
            return
        config = AuthConfig.from_env()
        if should_require_login(self.path, headers=self.headers, config=config):
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": _safe_next_path(self.path),
                        "error": "请先登录",
                    }
                ),
            )
            self.end_headers()
            return
        if parsed.path == "/account/password":
            self._handle_password_post()
            return
        if _is_public_readonly():
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(f"Public read-only mode is enabled for {PUBLIC_SITE_DOMAIN}.".encode())
            return
        if parsed.path not in {"/holdings", "/settings", "/notification-test", "/dispatch-daily"}:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = parse_qs(payload)
        if parsed.path == "/settings":
            self._handle_settings_post(form)
            return
        if parsed.path == "/notification-test":
            self._handle_notification_test_post(form)
            return
        if parsed.path == "/dispatch-daily":
            self._handle_dispatch_daily_post(form)
            return
        self._handle_holdings_post(form)

    def _handle_login_post(self) -> None:
        config = AuthConfig.from_env()
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = parse_qs(payload)
        next_path = _safe_next_path(form.get("next", ["/"])[0])
        if not is_auth_enabled(config):
            self.send_response(303)
            self.send_header("Location", next_path)
            self.end_headers()
            return
        store = _auth_store(config)
        _bootstrap_auth_admin(config, store)
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        user = store.authenticate(username, password)
        if user is None:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": next_path,
                        "error": "账号或密码错误",
                    }
                ),
            )
            self.end_headers()
            return
        token = SessionManager(
            config.session_secret,
            ttl_seconds=config.session_ttl_seconds,
        ).issue_session(user_id=user.id, username=user.username)
        self.send_response(303)
        self.send_header(
            "Set-Cookie",
            _session_cookie_header(
                token,
                max_age=config.session_ttl_seconds,
                secure=_is_secure_request(self.headers),
            ),
        )
        self.send_header("Location", next_path)
        self.end_headers()

    def _handle_register_post(self) -> None:
        config = AuthConfig.from_env()
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = parse_qs(payload)
        next_path = _safe_next_path(form.get("next", ["/"])[0])
        if not should_allow_registration(config):
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": next_path,
                        "error": "当前未开放注册，请使用已有账号登录。",
                    }
                ),
            )
            self.end_headers()
            return
        username = form.get("username", [""])[0]
        password = form.get("password", [""])[0]
        confirm_password = form.get("confirm_password", [""])[0]
        if password != confirm_password:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": next_path,
                        "error": "两次密码不一致。",
                    }
                ),
            )
            self.end_headers()
            return
        store = _auth_store(config)
        _bootstrap_auth_admin(config, store)
        try:
            user = store.register_user(username, password)
        except ValueError as exc:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": next_path,
                        "error": str(exc),
                    }
                ),
            )
            self.end_headers()
            return
        token = SessionManager(
            config.session_secret,
            ttl_seconds=config.session_ttl_seconds,
        ).issue_session(user_id=user.id, username=user.username)
        self.send_response(303)
        self.send_header(
            "Set-Cookie",
            _session_cookie_header(
                token,
                max_age=config.session_ttl_seconds,
                secure=_is_secure_request(self.headers),
            ),
        )
        self.send_header("Location", next_path)
        self.end_headers()

    def _handle_password_post(self) -> None:
        config = AuthConfig.from_env()
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=config)
        if user is None:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?"
                + urlencode(
                    {
                        "next": "/#settings",
                        "error": "请先登录",
                    }
                ),
            )
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = parse_qs(payload)
        current_password = form.get("current_password", [""])[0]
        new_password = form.get("new_password", [""])[0]
        confirm_password = form.get("confirm_password", [""])[0]
        level = "success"
        if new_password != confirm_password:
            notice = "两次新密码不一致。"
            level = "error"
        else:
            try:
                changed = _auth_store(config).change_password(
                    user.id,
                    current_password,
                    new_password,
                )
                notice = "密码已更新，请使用新密码登录。" if changed else "当前密码不正确。"
                level = "success" if changed else "error"
            except ValueError as exc:
                notice = str(exc)
                level = "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _settings_redirect_url(
                code="",
                provider_name=WEB_DATA_PROVIDER,
                holdings_path=_effective_holdings_path(user),
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def _handle_holdings_post(self, form: dict[str, list[str]]) -> None:
        code = form.get("page_code", [""])[0]
        provider_name = WEB_DATA_PROVIDER
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=AuthConfig.from_env())
        requested_holdings_path = form.get("holdings_path", [DEFAULT_HOLDINGS_PATH])[0]
        holdings_path = _effective_holdings_path(user, requested_holdings_path)
        try:
            action = form.get("portfolio_action", ["upsert"])[0]
            if action == "delete":
                target_code = _required_form_value(form, "holding_code", "股票代码")
                delete_holding_csv(holdings_path, target_code)
                notice = f"已从持仓中删除 {target_code}。"
            else:
                holding = _holding_from_form(form)
                result = upsert_holding_csv(holdings_path, holding)
                verb = "新增" if result == "added" else "更新"
                notice = f"已{verb}持仓：{holding.name}（{holding.code}）。"
            level = "success"
        except ValueError as exc:
            notice = str(exc)
            level = "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _portfolio_redirect_url(
                code=code,
                provider_name=provider_name,
                holdings_path=holdings_path,
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def _handle_settings_post(self, form: dict[str, list[str]]) -> None:
        code = form.get("page_code", [""])[0]
        provider_name = WEB_DATA_PROVIDER
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=AuthConfig.from_env())
        requested_holdings_path = form.get("holdings_path", [DEFAULT_HOLDINGS_PATH])[0]
        holdings_path = _effective_holdings_path(user, requested_holdings_path)
        try:
            saved_provider = save_settings_from_form(form)
            notice = "渠道配置已保存。"
            level = "success"
        except ValueError as exc:
            saved_provider = provider_name
            notice = str(exc)
            level = "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _settings_redirect_url(
                code=code,
                provider_name=saved_provider,
                holdings_path=holdings_path,
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def _handle_notification_test_post(self, form: dict[str, list[str]]) -> None:
        code = form.get("page_code", [""])[0]
        provider_name = WEB_DATA_PROVIDER
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=AuthConfig.from_env())
        requested_holdings_path = form.get("holdings_path", [DEFAULT_HOLDINGS_PATH])[0]
        holdings_path = _effective_holdings_path(user, requested_holdings_path)
        channel = _required_choice(
            form.get("test_channel", ["wechat"])[0],
            "测试通道",
            {"email", "wechat", "feishu"},
        )
        style = _required_choice(
            form.get("test_style", ["auto"])[0],
            "消息样式",
            {"auto", "full", "digest", "action"},
        )
        subject = (
            form.get("test_subject", [f"{PUBLIC_SITE_NAME} 通知测试"])[0]
            or f"{PUBLIC_SITE_NAME} 通知测试"
        ).strip()
        content = (form.get("test_content", [""])[0] or "").strip() or "测试消息"
        dry_run = form.get("test_dry_run", [""])[0] == "1"
        result = dispatch_report(
            content,
            channels=[channel],
            subject=subject,
            dry_run=dry_run,
            style=style,
        )
        notice = result.items[0].detail if result.items else "未生成发送结果。"
        level = "success" if result.ok else "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _settings_redirect_url(
                code=code,
                provider_name=provider_name,
                holdings_path=holdings_path,
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def _handle_dispatch_daily_post(self, form: dict[str, list[str]]) -> None:
        code = form.get("page_code", [""])[0]
        provider_name = WEB_DATA_PROVIDER
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=AuthConfig.from_env())
        requested_holdings_path = form.get("holdings_path", [DEFAULT_HOLDINGS_PATH])[0]
        holdings_path = _effective_holdings_path(user, requested_holdings_path)
        style = _required_choice(
            form.get("dispatch_style", ["auto"])[0],
            "消息样式",
            {"auto", "full", "digest", "action"},
        )
        channels = _normalize_receivers(form.get("dispatch_channels", [""])[0] or "")
        dry_run = form.get("dispatch_dry_run", [""])[0] == "1"
        try:
            provider = create_provider(provider_name)
            daily = build_daily_report(
                provider,
                holdings_path=holdings_path,
                provider_name=provider_name,
                allow_empty_portfolio=True,
            )
            result = dispatch_report(
                daily.markdown,
                channels=channels
                or (get_settings().notification_report_channels or ["email", "wechat"]),
                subject=f"{PUBLIC_SITE_NAME} 早间复盘与机会（{daily.market.trade_date}）",
                dry_run=dry_run,
                style=style,
            )
            notice = result.items[0].detail if result.items else "未生成发送结果。"
            level = "success" if result.ok else "error"
        except Exception as exc:
            notice = f"发送失败：{exc}"
            level = "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _settings_redirect_url(
                code=code,
                provider_name=provider_name,
                holdings_path=holdings_path,
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return


def _holding_from_form(form: dict[str, list[str]]) -> Holding:
    code = _required_form_value(form, "holding_code", "股票代码")
    name = _required_form_value(form, "holding_name", "股票名称")
    shares = _positive_float(form.get("holding_shares", [""])[0], "持股数量")
    cost_price = _positive_float(form.get("holding_cost_price", [""])[0], "成本价")
    sector = (form.get("holding_sector", [""])[0] or "").strip()
    note = (form.get("holding_note", [""])[0] or "").strip()
    return Holding(
        code=code,
        name=name,
        shares=shares,
        cost_price=cost_price,
        sector=sector,
        note=note,
    )


def save_settings_from_form(
    form: dict[str, list[str]],
    *,
    env_file: str | Path = ".env",
) -> str:
    current = get_settings(env_file=env_file)
    provider = _required_choice(
        form.get("settings_provider", [""])[0],
        "默认数据源",
        {"auto", "tencent", "akshare", "tushare", "tdx-snapshot", "sample"},
    )
    sender = (form.get("email_sender", [""])[0] or "").strip()
    sender_name = (form.get("email_sender_name", [""])[0] or "").strip()
    receivers = _normalize_receivers(form.get("email_receivers", [""])[0] or "")
    email_password = (form.get("email_password", [""])[0] or "").strip()
    itick_api_key = (form.get("itick_api_key", [""])[0] or "").strip()
    wechat_webhook = (form.get("wechat_webhook_url", [""])[0] or "").strip()
    feishu_webhook = (form.get("feishu_webhook_url", [""])[0] or "").strip()
    wechat_msg_type = _required_choice(
        form.get("wechat_msg_type", ["markdown"])[0],
        "微信消息格式",
        {"markdown", "text"},
    )
    wechat_max_bytes = _positive_int(
        form.get("wechat_max_bytes", [str(current.wechat_max_bytes)])[0],
        "微信单条字节上限",
    )
    notification_report_channels = _normalize_receivers(
        form.get("notification_report_channels", [""])[0] or ""
    )
    notification_report_style = _required_choice(
        form.get("notification_report_style", [current.notification_report_style])[0],
        "默认日报样式",
        {"auto", "full", "digest", "action"},
    )

    updates = {
        "STOCK_TS_PROVIDER": provider,
        "EMAIL_SENDER": sender,
        "EMAIL_SENDER_NAME": sender_name or current.email_sender_name,
        "EMAIL_RECEIVERS": ",".join(receivers),
        "WECHAT_MSG_TYPE": wechat_msg_type,
        "WECHAT_MAX_BYTES": str(wechat_max_bytes),
        "NOTIFICATION_REPORT_CHANNELS": ",".join(
            notification_report_channels or (current.notification_report_channels or [])
        ),
        "NOTIFICATION_REPORT_STYLE": notification_report_style,
    }
    if email_password:
        updates["EMAIL_PASSWORD"] = email_password
    elif current.email_password:
        updates["EMAIL_PASSWORD"] = current.email_password
    if itick_api_key:
        updates["ITICK_API_KEY"] = itick_api_key
    elif current.itick_api_key:
        updates["ITICK_API_KEY"] = current.itick_api_key
    if wechat_webhook:
        updates["WECHAT_WEBHOOK_URL"] = wechat_webhook
    elif current.wechat_webhook_url:
        updates["WECHAT_WEBHOOK_URL"] = current.wechat_webhook_url
    if feishu_webhook:
        updates["FEISHU_WEBHOOK_URL"] = feishu_webhook
    elif current.feishu_webhook_url:
        updates["FEISHU_WEBHOOK_URL"] = current.feishu_webhook_url

    save_dotenv_values(updates, path=env_file)
    return provider


def _required_form_value(form: dict[str, list[str]], key: str, label: str) -> str:
    value = (form.get(key, [""])[0] or "").strip()
    if not value:
        raise ValueError(f"{label}不能为空。")
    return value


def _positive_float(value: str, label: str) -> float:
    normalized = value.strip()
    try:
        number = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{label}必须为数字。") from exc
    if number <= 0:
        raise ValueError(f"{label}必须大于 0。")
    return number


def _positive_int(value: str, label: str) -> int:
    normalized = value.strip()
    try:
        number = int(normalized)
    except ValueError as exc:
        raise ValueError(f"{label}必须为整数。") from exc
    if number <= 0:
        raise ValueError(f"{label}必须大于 0。")
    return number


def _required_choice(value: str, label: str, allowed: set[str]) -> str:
    normalized = value.strip().lower()
    if normalized not in allowed:
        raise ValueError(f"{label}不合法。")
    return normalized


def _normalize_receivers(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _portfolio_redirect_url(
    *,
    code: str,
    provider_name: str,
    holdings_path: str,
    notice: str,
    notice_level: str,
) -> str:
    query = urlencode(
        {
            "code": code,
            "provider": provider_name,
            "holdings": holdings_path,
            "notice": notice,
            "notice_level": notice_level,
        }
    )
    return f"/?{query}#module-portfolio"


def _settings_redirect_url(
    *,
    code: str,
    provider_name: str,
    holdings_path: str,
    notice: str,
    notice_level: str,
) -> str:
    query = urlencode(
        {
            "code": code,
            "provider": provider_name,
            "holdings": holdings_path,
            "settings_notice": notice,
            "settings_notice_level": notice_level,
        }
    )
    return f"/?{query}#module-status"


def _default_stock_query(stock_code: str, holdings_path: str) -> str:
    normalized = stock_code.strip()
    if normalized:
        return normalized
    try:
        holdings = load_holdings_csv(holdings_path)
    except Exception:
        return "600519"
    if not holdings:
        return "600519"
    first = holdings[0]
    return first.code or first.name


def _is_public_readonly() -> bool:
    return os.getenv("STOCK_TS_PUBLIC_READONLY", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _server_bind_address() -> tuple[str, int]:
    host = os.getenv("HOST") or os.getenv("STOCK_TS_HOST") or "127.0.0.1"
    port = int(os.getenv("PORT") or os.getenv("STOCK_TS_PORT") or "8501")
    return host, port


def main() -> None:
    host, port = _server_bind_address()
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"{PUBLIC_SITE_NAME} web page: http://{host}:{port} ({PUBLIC_SITE_DOMAIN} branding)")
    server.serve_forever()


if __name__ == "__main__":
    main()
