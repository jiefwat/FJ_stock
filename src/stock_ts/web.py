# ruff: noqa: E501
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from html import escape
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from .account_settings import (
    MorningEmailPreferences,
    load_morning_email_preferences,
    save_morning_email_preferences,
)
from .agentic_stock_analysis import StockAgentDecision, build_stock_agent_decision
from .analysis import analyze_candidates, analyze_stock
from .announcements import AnnouncementItem, AnnouncementReport, fetch_cninfo_announcements
from .auth import AuthConfig, AuthUser, SessionManager, UserStore, is_auth_enabled
from .config import get_settings, save_dotenv_values
from .daily_decisions import read_decision_artifact
from .data_sources import build_data_source_matrix
from .deep_models import DeepStockReport
from .indicators import pct_change, sma
from .models import (
    CandidatePoolReport,
    CandidateStockAnalysis,
    CandidateStockRawData,
    DailyBar,
    Holding,
    MarketSnapshot,
    NewsItem,
    NewsSentimentReport,
    PortfolioAnalysisReport,
    PositionAnalysis,
    SectorAnalysisReport,
    StockAnalysisReport,
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
from .symbols import ResolvedSymbol, resolve_stock_query, sector_for_code
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
.module-refresh-tools { display:flex; flex-wrap:wrap; align-items:center; justify-content:flex-end; gap:8px; color:var(--muted); font-size:12px; }
.module-refresh-tools form { margin:0; }
.module-refresh-button { padding:7px 10px; font-size:12px; }
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
.market-event-card-list { display:grid; gap:10px; margin-top:14px; }
.market-event-card { border:1px solid var(--line); border-radius:16px; background:#fffdfa; padding:13px 15px; }
.market-event-head { display:flex; flex-wrap:wrap; align-items:center; gap:8px 10px; margin-bottom:8px; }
.market-event-time { border:1px solid var(--line); background:#fff; color:var(--muted); border-radius:999px; padding:5px 9px; font-size:12px; font-weight:800; white-space:nowrap; }
.market-event-theme { border:1px solid #dccba9; background:#f8f0df; color:#765622; border-radius:999px; padding:5px 9px; font-size:12px; font-weight:900; white-space:nowrap; }
.market-event-stocks { color:var(--ink); font-weight:800; line-height:1.45; }
.market-event-reason { margin:0; color:var(--ink-soft); line-height:1.65; overflow-wrap:anywhere; }
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
.portfolio-analysis-stack { display:grid; gap:8px; min-width:360px; }
.portfolio-analysis-line { margin:0; color:var(--ink-soft); line-height:1.55; }
.portfolio-analysis-line strong { display:inline-block; min-width:64px; color:var(--ink); }
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
class DataCenterRow:
    category: str
    channel: str
    status: str
    latest_at: str
    coverage: str
    missing: str
    impact: str
    level: str


@dataclass(frozen=True)
class DataCenterView:
    status: str
    updated_at: str
    rows: list[DataCenterRow]
    alerts: list[str]


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
    data_center: DataCenterView


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
    candidate_source: str = "",
    candidate_strategy_label: str = "",
    candidate_evidence: str = "",
    current_user: AuthUser | None = None,
    refresh: bool = False,
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
            refresh=refresh,
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
        stock_raw=stock_raw,
        stock=stock,
        market=market,
        candidates=candidates,
        candidate_universe=candidate_universe,
        candidate_universe_metadata=candidate_universe_metadata,
        market_news=daily.news,
    )
    announcement_report = _safe_fetch_announcements(
        resolved.code,
        announcement_fetcher=announcement_fetcher,
    )
    if announcement_report is None or not announcement_report.items:
        announcement_report = _announcement_report_from_stock_raw(resolved.code, stock_raw)
    event_radar = build_event_radar(announcement_report)
    risk_gate = _build_risk_gate(
        quality=quality,
        market=market,
        event_radar=event_radar,
        portfolio=portfolio,
    )
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
    refresh_time = quality.data_center.updated_at
    section_map = {
        "market": _render_compact_market_module(
            market,
            sectors,
            portfolio,
            candidates,
            candidate_universe=candidate_universe,
            news=daily.news,
            refresh_time=refresh_time,
            stock_code=resolved.query,
            provider_name=provider_name,
            holdings_path=holdings_path,
        ),
        "portfolio": _render_compact_portfolio_module(
            portfolio,
            market,
            sectors,
            holdings_path,
            resolved.query,
            provider_name,
            portfolio_notice,
            edit_code,
            refresh_time=refresh_time,
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
            candidate_source=candidate_source,
            candidate_strategy_label=candidate_strategy_label,
            candidate_evidence=candidate_evidence,
            provider_name=provider_name,
            holdings_path=holdings_path,
            refresh_time=refresh_time,
        ),
        "opportunity": _render_hot_opportunity_module(
            sectors=sectors,
            candidates=screener_candidates,
            market=market,
            candidate_universe=candidate_universe,
            stock_code=resolved.query,
            provider_name=provider_name,
            holdings_path=holdings_path,
            candidate_code=candidate_code,
            candidate_group=candidate_group,
            candidate_strategy=candidate_strategy,
            candidate_universe_metadata=candidate_universe_metadata,
            quality=quality,
            refresh_time=refresh_time,
        ),
        "data-center": _render_data_center_panel(
            quality.data_center,
            stock_code=resolved.query,
            provider_name=provider_name,
            holdings_path=holdings_path,
        ),
        "account": _render_account_management_module(
            provider_name=provider_name,
            holdings_path=holdings_path,
            provider_class=provider_class,
            stock_code=resolved.query,
            notice=settings_notice,
            current_user=current_user,
        ),
    }
    auth_config = AuthConfig.from_env()
    shell = f"""
  <div class="app-shell">
      {render_shell_sidebar(
        resolved.query,
        holdings_path,
        current_username=current_user.username if current_user is not None else "",
        current_role=current_user.role if current_user is not None else "",
        auth_enabled=is_auth_enabled(auth_config),
      )}
    <main class="workspace">
      {_render_global_freshness_bar(quality, market, provider_class, risk_gate)}
      {_render_data_center_summary(quality.data_center)}
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
    latest_date: str = ""
    fund_flow: float | None = None
    pe_ttm: float | None = None
    news_items: list[NewsItem] = field(default_factory=list)
    announcements: list[dict[str, object]] = field(default_factory=list)


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
                latest_date=item.bars[-1].date,
                fund_flow=item.fund_flow,
                pe_ttm=item.pe_ttm,
                news_items=item.news_items,
                announcements=item.announcements,
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
        return "<p class='module-desc'>当前没有指数数据，先确认数据源或切回样例模式查看页面。</p>"
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
    return '<a class="portfolio-inline-button primary" href="#portfolio-form" data-action="add-holding" data-scroll="portfolio-form">添加持仓</a>'


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
    detail = f"{reason} 复核：{next_check}"
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
        elif position.pnl >= 0 and (
            position.trend == "下降趋势" or position.risk_level in {"高", "中"}
        ):
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
        <div class="editor-toolbar"><div><h3>持仓处理队列</h3><p class="section-subtitle">持仓风险处置按今天先处理什么排序，不按股票代码排序。</p></div></div>
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
        for position in sorted(positions, key=lambda item: (item.risk_level != "高", -item.weight))[
            :4
        ]
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
    return (
        f'<a class="ghost-button" href="{escape(_stock_chart_url(holding_code, provider_name, holdings_path), quote=True)}">'
        "个股分析</a>"
    )


def _render_clear_edit_link(
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    edit_code: str,
) -> str:
    if not edit_code:
        return ""
    query = urlencode(
        {
            "code": stock_code,
            "provider": provider_name,
            "holdings": holdings_path,
        }
    )
    return f'<a class="ghost-button" href="/?{query}#portfolio">结束编辑</a>'


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


def _announcement_report_from_stock_raw(query: str, stock_raw: StockRawData) -> AnnouncementReport | None:
    if not stock_raw.announcements:
        return None
    items = [_announcement_item_from_payload(stock_raw, payload) for payload in stock_raw.announcements]
    risk_events = [item for item in items if item.risk_flags]
    return AnnouncementReport(
        query=query,
        total=len(items),
        items=items,
        risk_events=risk_events,
        source="snapshot.cninfo",
    )


def _announcement_item_from_payload(
    stock_raw: StockRawData, payload: dict[str, object]
) -> AnnouncementItem:
    flags_payload = payload.get("risk_flags")
    flags = [str(item) for item in flags_payload] if isinstance(flags_payload, list) else []
    return AnnouncementItem(
        code=str(payload.get("code") or stock_raw.code),
        name=str(payload.get("name") or stock_raw.name),
        title=str(payload.get("title") or payload.get("announcementTitle") or ""),
        date=str(payload.get("date") or payload.get("announcement_date") or ""),
        url=str(payload.get("url") or ""),
        risk_flags=flags,
    )


def _web_live_announcements_enabled() -> bool:
    return os.getenv("STOCK_TS_WEB_LIVE_ANNOUNCEMENTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _trade_blocking_warnings(warnings: list[str]) -> list[str]:
    blocking_keywords = [
        "示例数据",
        "疑似降级",
        "未完成代码解析",
        "示例股票",
        "个股日期需复核",
        "数据已滞后",
    ]
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
    stock_raw: StockRawData,
    stock: DeepStockReport,
    market: MarketSnapshot,
    candidates: CandidatePoolReport,
    candidate_universe: list[CandidateStockRawData],
    candidate_universe_metadata: dict[str, str],
    market_news: NewsSentimentReport | None = None,
) -> DataQualityView:
    warnings = list(resolved.warnings)
    blocked_actions: list[str] = []
    candidate_price_reliable = candidates.price_reliable
    candidate_universe_reliable = _candidate_universe_prices_reliable(candidate_universe)
    freshness_warnings = _trade_date_freshness_warnings(
        requested_provider=requested_provider,
        actual_provider=actual_provider,
        stock_date=stock.trade_date,
        market_date=market.trade_date,
    )
    freshness_warnings.extend(
        _kline_freshness_warnings(
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            stock_raw=stock_raw,
            candidate_universe=candidate_universe,
        )
    )
    freshness_warnings.extend(_pipeline_freshness_warnings())
    if freshness_warnings:
        warnings.extend(freshness_warnings)
        blocked_actions.extend(["候选排序", "评分展示", "按今天盘面执行"])
        candidate_price_reliable = False
        candidate_universe_reliable = False
    warnings.extend(
        _multisource_context_warnings(
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            stock_raw=stock_raw,
            market_news=market_news,
        )
    )
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
    data_center = _build_data_center_view(
        requested_provider=requested_provider,
        actual_provider=actual_provider,
        stock_raw=stock_raw,
        stock=stock,
        market=market,
        candidates=candidates,
        candidate_universe=candidate_universe,
        candidate_universe_metadata=candidate_universe_metadata,
        market_news=market_news,
    )
    if data_center.alerts:
        unique_warnings = list(dict.fromkeys([*unique_warnings, *data_center.alerts]))
    gate_warnings = [warning for warning in unique_warnings if _is_global_quality_warning(warning)]
    if blocked_actions:
        status = "排序已暂停"
        gate_level = "blocked"
        signal = "暂停"
        summary = "排序暂停"
    elif gate_warnings:
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
        data_center=data_center,
    )


def _is_global_quality_warning(warning: str) -> bool:
    optional_stock_context_prefixes = (
        "多维数据缺口",
        "数据中台预警：公告",
        "数据中台预警：基本面",
    )
    return not warning.startswith(optional_stock_context_prefixes)


def _build_data_center_view(
    *,
    requested_provider: str,
    actual_provider: str,
    stock_raw: StockRawData,
    stock: DeepStockReport,
    market: MarketSnapshot,
    candidates: CandidatePoolReport,
    candidate_universe: list[CandidateStockRawData],
    candidate_universe_metadata: dict[str, str],
    market_news: NewsSentimentReport | None,
) -> DataCenterView:
    expected = _expected_latest_a_share_trade_date(_current_datetime())
    sample_mode = requested_provider.strip().lower() == "sample" or actual_provider == "SampleDataProvider"
    snapshot_source = candidate_universe_metadata.get("snapshot_source") or actual_provider
    snapshot_generated = candidate_universe_metadata.get("snapshot_generated_at", "")
    rows = [
        _data_center_row(
            category="大盘行情",
            channel=snapshot_source,
            latest_date=market.trade_date,
            updated_at=snapshot_generated,
            missing=[] if market.indices else ["指数表现"],
            coverage=f"指数 {len(market.indices)} 个",
            impact="影响市场摘要、风险项和目标仓位" if not market.indices else "不影响分析",
            expected=expected,
            critical=True,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="K线行情",
            channel=_data_center_channel(
                _source_for_block(
                    stock_raw,
                    ["daily", "kline", "tdx", "tencent", "tushare", "akshare"],
                    snapshot_source,
                ),
                candidate_universe_metadata.get("holding_kline_refresh_source", ""),
                candidate_universe_metadata.get("kline_refresh_source", ""),
            ),
            latest_date=_latest_bar_date(stock_raw.bars),
            updated_at=_first_present(
                candidate_universe_metadata.get("holding_kline_refresh_generated_at", ""),
                candidate_universe_metadata.get("kline_refresh_generated_at", ""),
                snapshot_generated,
            ),
            missing=_kline_missing_parts(stock_raw, candidate_universe),
            coverage=_coverage_ratio(candidate_universe_metadata, "snapshot_bars_count"),
            impact="影响技术面、候选排序和盘面执行",
            expected=expected,
            critical=True,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="技术面",
            channel="K线计算：MA / RSI / MACD / 量能",
            latest_date=_latest_bar_date(stock_raw.bars),
            updated_at=_first_present(
                candidate_universe_metadata.get("holding_kline_refresh_generated_at", ""),
                candidate_universe_metadata.get("kline_refresh_generated_at", ""),
                snapshot_generated,
            ),
            missing=[] if stock_raw.bars else ["技术指标输入K线"],
            coverage=_coverage_ratio(candidate_universe_metadata, "snapshot_bars_count"),
            impact="影响趋势、支撑压力和交易触发线",
            expected=expected,
            critical=False,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="候选池",
            channel=_data_center_channel(
                candidate_universe_metadata.get("source", ""),
                candidate_universe_metadata.get("bar_source", ""),
                snapshot_source,
            ),
            latest_date=candidates.trade_date,
            updated_at=_first_present(candidate_universe_metadata.get("generated_at", ""), snapshot_generated),
            missing=_candidate_missing_parts(candidates, candidate_universe),
            coverage=f"候选 {len(candidate_universe)} 只",
            impact="影响热点机会、候选列表和排序评分",
            expected=expected,
            critical=True,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="资金面",
            channel=_data_center_channel(
                str(stock_raw.fund_flow_detail.get("source") or ""),
                _source_for_block(stock_raw, ["moneyflow", "fund", "quote", "turnover", "akshare"], snapshot_source),
            ),
            latest_date=str(stock_raw.fund_flow_detail.get("date") or stock.trade_date or ""),
            updated_at=snapshot_generated,
            missing=[] if stock_raw.fund_flow is not None or stock_raw.fund_flow_detail else ["资金流/成交侧明细"],
            coverage=_coverage_ratio(candidate_universe_metadata, "snapshot_fund_flow_detail_count"),
            impact="影响资金面证据和承接判断",
            expected=expected,
            critical=False,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="新闻舆情",
            channel=_data_center_channel(
                _latest_news_source(stock_raw.news_items),
                _latest_news_source(market_news.items if market_news else []),
                candidate_universe_metadata.get("mcp_market_news_refresh_source", ""),
            ),
            latest_date=max(
                _latest_news_date(stock_raw.news_items),
                _latest_news_date(market_news.items if market_news else []),
            ),
            updated_at=_first_present(
                candidate_universe_metadata.get("mcp_market_news_refresh_generated_at", ""),
                candidate_universe_metadata.get("manual_context_refresh_generated_at", ""),
                candidate_universe_metadata.get("external_enrichment_generated_at", ""),
                snapshot_generated,
            ),
            missing=_news_missing_parts(stock_raw, market_news),
            coverage=_news_coverage_text(candidate_universe_metadata),
            impact="影响消息面、市场舆情和事件催化判断",
            expected=expected,
            critical=False,
            sample_mode=sample_mode,
        ),
        _data_center_row(
            category="公告",
            channel=_data_center_channel(
                _latest_announcement_source(stock_raw.announcements),
                _source_for_block(stock_raw, ["announcement", "cninfo"], snapshot_source),
            ),
            latest_date=_latest_announcement_date(stock_raw.announcements),
            updated_at=_first_present(
                candidate_universe_metadata.get("announcement_refresh_generated_at", ""),
                candidate_universe_metadata.get("manual_context_refresh_generated_at", ""),
                snapshot_generated,
            ),
            missing=[] if stock_raw.announcements else ["公告"],
            coverage=_coverage_ratio(
                candidate_universe_metadata, "snapshot_announcements_count", label="公告"
            ),
            impact="影响风险公告、财报事件和监管风险判断",
            expected=expected,
            critical=False,
            sample_mode=sample_mode,
            freshness_required=False,
        ),
        _data_center_row(
            category="基本面",
            channel=_data_center_channel(
                str(stock_raw.fundamental_metrics.get("source") or ""),
                _source_for_block(stock_raw, ["fina", "valuation", "profile", "tdx"], snapshot_source),
            ),
            latest_date=str(stock_raw.fundamental_metrics.get("date") or ""),
            updated_at=_first_present(
                candidate_universe_metadata.get("external_enrichment_generated_at", ""),
                candidate_universe_metadata.get("manual_context_refresh_generated_at", ""),
                snapshot_generated,
            ),
            missing=_fundamental_missing_parts(stock_raw),
            coverage=_fundamental_coverage_text(candidate_universe_metadata),
            impact="影响估值、财务质量和基本面证据",
            expected=expected,
            critical=False,
            sample_mode=sample_mode,
            freshness_required=False,
        ),
    ]
    data_chain_row = _data_chain_center_row()
    if data_chain_row is not None:
        rows.append(data_chain_row)
    alerts = [
        f"数据中台预警：{row.category}{row.status}，{row.impact}。"
        for row in rows
        if row.level in {"warn", "blocked"} and row.impact != "不影响分析"
    ]
    if any(row.level == "blocked" for row in rows):
        status = "影响分析"
    elif any(row.level == "warn" for row in rows):
        status = "需复核"
    else:
        status = "正常"
    return DataCenterView(
        status=status,
        updated_at=_format_beijing_time(
            _latest_data_chain_timestamp(
                snapshot_generated,
                *_metadata_refresh_timestamps(candidate_universe_metadata),
                _pipeline_status_generated_at(),
                _data_chain_status_generated_at(),
            )
            or "待确认"
        ),
        rows=rows,
        alerts=alerts,
    )


def _metadata_refresh_timestamps(metadata: dict[str, str]) -> list[str]:
    return [
        str(value)
        for key, value in metadata.items()
        if key.endswith("generated_at") and str(value or "").strip()
    ]


def _pipeline_status_generated_at() -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    status = _read_key_value_status(report_dir / "pipeline.status")
    return status.get("generated_at", "")


def _data_chain_status_generated_at() -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    payload = _read_json_file(report_dir / "data_chain_status.json")
    return str(payload.get("generated_at") or "")


def _latest_data_chain_timestamp(*values: str) -> str:
    latest_raw = ""
    latest_dt: datetime | None = None
    for value in values:
        raw = str(value or "").strip()
        if not raw or raw == "待确认":
            continue
        parsed = _parse_datetime_value(raw)
        if parsed is None:
            if not latest_raw:
                latest_raw = raw
            continue
        comparable = parsed.astimezone(timezone.utc)
        if latest_dt is None or comparable > latest_dt:
            latest_dt = comparable
            latest_raw = raw
    return latest_raw


def _format_beijing_time(value: str) -> str:
    raw = str(value or "").strip()
    if not raw or raw == "待确认":
        return raw or "待确认"
    parsed = _parse_datetime_value(raw)
    if parsed is None:
        return raw
    beijing = parsed.astimezone(timezone(timedelta(hours=8)))
    return f"{beijing:%Y-%m-%d %H:%M:%S} 北京时间"


def _parse_datetime_value(value: str) -> datetime | None:
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
    return parsed


def _data_center_row(
    *,
    category: str,
    channel: str,
    latest_date: str,
    updated_at: str,
    missing: list[str],
    coverage: str,
    impact: str,
    expected: str,
    critical: bool,
    sample_mode: bool,
    freshness_required: bool = True,
) -> DataCenterRow:
    missing = [item for item in missing if item]
    latest_text = latest_date or "未采集"
    if updated_at:
        latest_text = f"{latest_text} / 更新 {_format_beijing_time(updated_at)}"
    is_stale = (
        freshness_required and bool(latest_date) and _iso_date_is_before(latest_date, expected)
    )
    if sample_mode:
        status = "样例"
        level = "warn"
        impact = "只能验证流程，不能用于真实分析"
    elif missing or not latest_date:
        status = "未采集" if not latest_date else "缺字段"
        level = "blocked" if critical else "warn"
    elif is_stale:
        status = "已滞后"
        level = "blocked" if critical else "warn"
    else:
        status = "可用"
        level = "ok"
        impact = "不影响分析" if impact != "只能验证流程，不能用于真实分析" else impact
    return DataCenterRow(
        category=category,
        channel=channel or "待确认",
        status=status,
        latest_at=latest_text,
        coverage=coverage or "当前标的",
        missing="、".join(missing) if missing else "无",
        impact=impact,
        level=level,
    )


def _data_chain_center_row() -> DataCenterRow | None:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    payload = _read_json_file(report_dir / "data_chain_status.json")
    if not payload:
        return None
    status = str(payload.get("status") or "unknown")
    if status == "ok":
        display_status = "可用"
        level = "ok"
        impact = "不影响分析"
    elif status == "failed":
        display_status = "影响分析"
        level = "blocked"
        impact = "全链路存在阻断节点，相关模块只允许补数据和人工复核"
    else:
        display_status = "需复核"
        level = "warn"
        impact = "全链路存在降级节点，强结论需暂停"
    blockers = [str(item) for item in _json_list(payload.get("blockers")) if item]
    warnings = [str(item) for item in _json_list(payload.get("warnings")) if item]
    missing = "；".join((blockers or warnings)[:3]) or "无"
    modules = payload.get("modules")
    coverage = "五段链路"
    if isinstance(modules, dict):
        coverage = " / ".join(
            f"{key}:{str(value.get('status') or 'unknown')}"
            for key, value in modules.items()
            if isinstance(value, dict)
        )
    return DataCenterRow(
        category="全链路校验",
        channel="reports/daily/data_chain_status.json",
        status=display_status,
        latest_at=_format_beijing_time(str(payload.get("generated_at") or "待确认")),
        coverage=coverage,
        missing=missing,
        impact=impact,
        level=level,
    )


def _read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _json_list(value: object) -> list:
    return value if isinstance(value, list) else []


def _coverage_ratio(
    metadata: dict[str, str], count_key: str, *, label: str = "覆盖"
) -> str:
    count = metadata.get(count_key, "")
    total = metadata.get("snapshot_stock_count", "")
    if count and total:
        return f"{label} {count}/{total}"
    return "当前标的"


def _news_coverage_text(metadata: dict[str, str]) -> str:
    stock_news = _coverage_ratio(metadata, "snapshot_news_items_count", label="个股新闻")
    market_news = metadata.get("snapshot_market_news_count", "")
    if market_news:
        return f"{stock_news}；市场消息 {market_news} 条"
    return stock_news


def _fundamental_coverage_text(metadata: dict[str, str]) -> str:
    fundamentals = _coverage_ratio(
        metadata, "snapshot_fundamental_metrics_count", label="财务指标"
    )
    valuation = _coverage_ratio(metadata, "snapshot_valuation_count", label="估值")
    if valuation == "当前标的":
        return fundamentals
    return f"{fundamentals}；{valuation}"


def _data_center_channel(*values: str) -> str:
    parts: list[str] = []
    for value in values:
        for item in str(value or "").replace("、", ",").split(","):
            normalized = item.strip()
            if normalized and normalized not in parts:
                parts.append(normalized)
    return " / ".join(parts[:3])


def _first_present(*values: str) -> str:
    for value in values:
        if value:
            return str(value)
    return ""


def _kline_missing_parts(
    stock_raw: StockRawData, candidate_universe: list[CandidateStockRawData]
) -> list[str]:
    missing: list[str] = []
    if not stock_raw.bars:
        missing.append("个股K线")
    if not candidate_universe:
        missing.append("候选池K线")
    elif any(not item.bars for item in candidate_universe):
        missing.append("部分候选K线")
    return missing


def _candidate_missing_parts(
    candidates: CandidatePoolReport, candidate_universe: list[CandidateStockRawData]
) -> list[str]:
    missing: list[str] = []
    if not candidates.candidates:
        missing.append("候选列表")
    if not candidate_universe:
        missing.append("扫描样本")
    if not candidates.price_reliable:
        missing.append("候选价格")
    return missing


def _news_missing_parts(
    stock_raw: StockRawData, market_news: NewsSentimentReport | None
) -> list[str]:
    missing: list[str] = []
    if not market_news or not market_news.items:
        missing.append("市场新闻")
    if not stock_raw.news_items:
        missing.append("个股新闻")
    return missing


def _fundamental_missing_parts(stock_raw: StockRawData) -> list[str]:
    missing: list[str] = []
    has_hk_yahoo_fundamental = (
        str(stock_raw.fundamental_metrics.get("source") or "") == "yahoo.timeseries"
        and (
            stock_raw.fundamental_metrics.get("operating_revenue") is not None
            or stock_raw.fundamental_metrics.get("net_profit") is not None
        )
    )
    if stock_raw.pe_ttm is None and not stock_raw.valuation and not has_hk_yahoo_fundamental:
        missing.append("估值")
    if not stock_raw.fundamental_metrics:
        missing.append("财务指标")
    return missing


def _latest_news_source(items: list) -> str:
    if not items:
        return ""
    latest = max(items, key=lambda item: str(getattr(item, "date", "") or ""))
    return str(getattr(latest, "source", "") or "")


def _latest_announcement_source(items: list[dict[str, object]]) -> str:
    if not items:
        return ""
    latest = max(
        items,
        key=lambda item: str(
            item.get("date") or item.get("announcement_date") or item.get("公告日期") or ""
        ),
    )
    return str(latest.get("source") or latest.get("来源") or "")


def _trade_date_freshness_warnings(
    *,
    requested_provider: str,
    actual_provider: str,
    stock_date: str,
    market_date: str,
) -> list[str]:
    if requested_provider.strip().lower() == "sample" or actual_provider == "SampleDataProvider":
        return []
    expected = _expected_latest_a_share_trade_date(_current_datetime())
    stale_dates = [
        label
        for label, value in [("个股", stock_date), ("大盘", market_date)]
        if _iso_date_is_before(value, expected)
    ]
    if not stale_dates:
        return []
    joined = "、".join(stale_dates)
    return [
        f"数据已滞后：最近应为 {expected}，{joined}仍停留在旧交易日，不能按今天盘面执行。"
    ]


def _kline_freshness_warnings(
    *,
    requested_provider: str,
    actual_provider: str,
    stock_raw: StockRawData,
    candidate_universe: list[CandidateStockRawData],
) -> list[str]:
    if requested_provider.strip().lower() == "sample" or actual_provider == "SampleDataProvider":
        return []
    expected = _expected_latest_a_share_trade_date(_current_datetime())
    stock_latest = _latest_bar_date(stock_raw.bars)
    candidate_dates = [_latest_bar_date(item.bars) for item in candidate_universe]
    candidate_stale_dates = [
        date for date in candidate_dates if _iso_date_is_before(date, expected)
    ]
    candidate_missing_count = sum(1 for date in candidate_dates if not date)
    stale_parts = []
    if not stock_latest or _iso_date_is_before(stock_latest, expected):
        stale_parts.append(f"个股K线最晚 {stock_latest or '缺失'}")
    if candidate_stale_dates or candidate_missing_count:
        stale_parts.append(
            _candidate_kline_staleness_detail(
                candidate_dates,
                stale_dates=candidate_stale_dates,
                missing_count=candidate_missing_count,
            )
        )
    if not stale_parts:
        return []
    return [
        f"K线已滞后：最近应为 {expected}，{'，'.join(stale_parts)}，不能按今天盘面执行。"
    ]


def _candidate_kline_staleness_detail(
    dates: list[str],
    *,
    stale_dates: list[str],
    missing_count: int,
) -> str:
    if not dates:
        return "候选池K线最晚 缺失"
    affected = len(stale_dates) + missing_count
    total = len(dates)
    valid_dates = [date for date in dates if date]
    latest = max(valid_dates, default="")
    oldest = min(valid_dates, default="")
    if affected >= total:
        return f"候选池K线最晚 {latest or '缺失'}"
    return (
        f"候选池K线过期 {affected}/{total}"
        f"（最新 {latest or '缺失'}，最旧 {oldest or '缺失'}）"
    )


def _latest_bar_date(bars: list[DailyBar]) -> str:
    dates = [bar.date for bar in bars if getattr(bar, "date", "")]
    return max(dates) if dates else ""


def _multisource_context_warnings(
    *,
    requested_provider: str,
    actual_provider: str,
    stock_raw: StockRawData,
    market_news: NewsSentimentReport | None,
) -> list[str]:
    if requested_provider.strip().lower() == "sample" or actual_provider == "SampleDataProvider":
        return []
    expected = _expected_latest_a_share_trade_date(_current_datetime())
    warnings: list[str] = []
    market_news_latest = _latest_news_date(market_news.items if market_news else [])
    if not market_news_latest:
        warnings.append("市场新闻缺失：消息面和舆情分析不能代表当天盘面。")
    elif _iso_date_is_before(market_news_latest, expected):
        warnings.append(
            f"市场新闻已滞后：最近应为 {expected}，市场新闻最晚 {market_news_latest}。"
        )

    missing_blocks = _missing_stock_context_blocks(stock_raw)
    if missing_blocks:
        warnings.append(
            f"多维数据缺口：{'、'.join(missing_blocks)}缺失，不能输出完整股票分析。"
        )
    stock_news_latest = _latest_news_date(stock_raw.news_items)
    if stock_news_latest and _iso_date_is_before(stock_news_latest, expected):
        warnings.append(
            f"个股新闻已滞后：最近应为 {expected}，个股新闻最晚 {stock_news_latest}。"
        )
    announcement_latest = _latest_announcement_date(stock_raw.announcements)
    if announcement_latest and _iso_date_is_before(announcement_latest, expected):
        warnings.append(
            f"公告快照需复核：最近应为 {expected}，公告最晚 {announcement_latest}。"
        )
    return warnings


def _missing_stock_context_blocks(stock_raw: StockRawData) -> list[str]:
    missing: list[str] = []
    if stock_raw.fund_flow is None and not stock_raw.fund_flow_detail:
        missing.append("资金面")
    if not stock_raw.news_items:
        missing.append("消息面")
    if not stock_raw.announcements:
        missing.append("公告")
    if (
        stock_raw.pe_ttm is None
        and not stock_raw.valuation
        and not stock_raw.fundamental_metrics
    ):
        missing.append("基本面")
    return missing


def _latest_news_date(items: list) -> str:
    dates = [str(getattr(item, "date", "") or "")[:10] for item in items]
    return max([date for date in dates if date], default="")


def _latest_announcement_date(items: list[dict[str, object]]) -> str:
    dates = [
        str(
            item.get("date")
            or item.get("announcement_date")
            or item.get("公告日期")
            or ""
        )[:10]
        for item in items
        if isinstance(item, dict)
    ]
    return max([date for date in dates if date], default="")


def _pipeline_freshness_warnings() -> list[str]:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    status = _read_key_value_status(report_dir / "pipeline.status")
    if not status:
        return []
    generated_at = status.get("generated_at", "")
    age_hours = _hours_since(generated_at)
    if age_hours is not None and age_hours > 8:
        return ["自动更新已滞后：超过 8 小时，先刷新数据流水线。"]
    failed_steps = _automation_failed_steps(status)
    if failed_steps:
        failed_text = "、".join(failed_steps)
        return [f"自动更新未完整：{failed_text}失败或部分完成，先修复流水线。"]
    return []


def _current_datetime() -> datetime:
    override = os.getenv("STOCK_TS_NOW", "").strip()
    if override:
        return datetime.fromisoformat(override.replace("Z", "+00:00"))
    return datetime.now()


def _expected_latest_a_share_trade_date(now: datetime) -> str:
    current = now.date()
    if current.weekday() < 5 and (now.hour, now.minute) < (15, 30):
        current -= timedelta(days=1)
    while current.weekday() >= 5:
        current -= timedelta(days=1)
    return current.isoformat()


def _iso_date_is_before(value: str, expected: str) -> bool:
    try:
        candidate = datetime.fromisoformat(str(value)[:10]).date()
        expected_date = datetime.fromisoformat(expected).date()
    except ValueError:
        return False
    return candidate < expected_date


def _hours_since(value: str) -> float | None:
    if not value:
        return None
    try:
        started = datetime.fromisoformat(value[:19])
    except ValueError:
        return None
    now = _normalize_local_datetime(_current_datetime())
    started = _normalize_local_datetime(started)
    return (now - started).total_seconds() / 3600


def _normalize_local_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone().replace(tzinfo=None)


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
    provider_label = (
        "TDX MCP" if quality.requested_provider == WEB_DATA_PROVIDER else provider_class
    )
    return f"""
      <div class="freshness-bar" aria-label="全局数据新鲜度">
        <div><span>交易日</span><strong>{escape(market.trade_date or quality.market_date or "待确认")}</strong></div>
        <div><span>行情</span><strong>{escape(quality.latest_date or "待确认")}</strong></div>
        <div><span>K线/资金/新闻/公告</span><strong>{escape(data_detail)}</strong></div>
        <div><span>数据状态</span><strong>{escape(quality.signal)}</strong></div>
        <div><span>来源</span><strong>{escape(provider_label)}</strong></div>
        <div><span>动作闸门</span><strong>{escape(risk_gate.gate)}</strong></div>
      </div>"""


def _render_module_refresh_tools(
    *,
    refresh_time: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    workspace: str,
) -> str:
    action = f"/#{workspace}"
    return f"""
      <div class="module-refresh-tools">
        <span>数据刷新时间：{escape(refresh_time or "待确认")}</span>
        <form method="get" action="{escape(action, quote=True)}">
          <input type="hidden" name="code" value="{escape(stock_code)}" />
          <input type="hidden" name="provider" value="{escape(provider_name)}" />
          <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
          <input type="hidden" name="workspace" value="{escape(workspace)}" />
          <input type="hidden" name="refresh" value="1" />
          <button class="ghost-button module-refresh-button" type="submit">手动刷新数据</button>
        </form>
      </div>"""


def _manual_refresh_command() -> list[str]:
    custom = os.getenv("STOCK_TS_MANUAL_REFRESH_COMMAND", "").strip()
    if custom:
        return shlex.split(custom)
    python = os.getenv("STOCK_TS_PIPELINE_PYTHON", "").strip() or sys.executable
    report_dir = os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily")
    return [
        python,
        "scripts/run_daily_pipeline.py",
        "--python",
        python,
        "--snapshot",
        os.getenv("STOCK_TS_TDX_SNAPSHOT_PATH", "data/imports/tdx_snapshots.json"),
        "--holdings",
        os.getenv("STOCK_TS_PIPELINE_HOLDINGS_PATH", DEFAULT_HOLDINGS_PATH),
        "--provider",
        "tdx-snapshot",
        "--candidate-limit",
        os.getenv("STOCK_TS_PIPELINE_CANDIDATE_LIMIT", "300"),
        "--enrich-limit",
        os.getenv("STOCK_TS_PIPELINE_ENRICH_LIMIT", "50"),
        "--external-enrich-timeout",
        os.getenv("STOCK_TS_PIPELINE_EXTERNAL_ENRICH_TIMEOUT", "300"),
        "--announcement-limit",
        os.getenv("STOCK_TS_PIPELINE_ANNOUNCEMENT_LIMIT", "5"),
        "--output-dir",
        report_dir,
        "--html-dir",
        os.getenv("STOCK_TS_DAILY_HTML_DIR", "reports/html"),
        "--announcement-dir",
        os.getenv("STOCK_TS_ANNOUNCEMENT_DIR", "reports/announcements"),
    ]


def _trigger_manual_data_refresh() -> str:
    report_dir = Path(os.getenv("STOCK_TS_DAILY_REPORT_DIR", "reports/daily"))
    report_dir.mkdir(parents=True, exist_ok=True)
    requested_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
    request_path = report_dir / "manual_refresh.status"
    log_path = report_dir / "manual_refresh.log"
    command = _manual_refresh_command()
    request_path.write_text(
        "\n".join(
            [
                "status=starting",
                f"requested_at={requested_at}",
                f"command={shlex.join(command)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    try:
        with log_path.open("ab") as log_file:
            log_file.write(f"\n== manual refresh {requested_at} ==\n".encode())
            subprocess.Popen(
                command,
                cwd=Path.cwd(),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=os.environ.copy(),
            )
    except Exception as exc:
        request_path.write_text(
            "\n".join(
                [
                    "status=failed_to_start",
                    f"requested_at={requested_at}",
                    f"error={type(exc).__name__}: {exc}",
                    f"command={shlex.join(command)}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return "failed_to_start"
    request_path.write_text(
        "\n".join(
            [
                "status=started",
                f"requested_at={requested_at}",
                f"command={shlex.join(command)}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return "started"


def _manual_refresh_redirect_location(query: dict[str, list[str]]) -> str:
    workspace = (query.get("workspace", [""])[0] or "").strip()
    cleaned: dict[str, list[str]] = {
        key: values
        for key, values in query.items()
        if key not in {"refresh", "workspace"} and values
    }
    location = "/"
    if cleaned:
        location += "?" + urlencode(cleaned, doseq=True)
    if workspace:
        location += f"#{workspace}"
    return location


def _render_data_center_panel(
    data_center: DataCenterView,
    *,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    rows_to_show = _simple_data_center_rows(data_center.rows)
    rows = "".join(
        f"""
        <tr id="{escape(_data_center_anchor(row.category))}" class="data-center-row {escape(row.level)}">
          <td>{escape(row.category)}</td>
          <td>{escape(row.status)}</td>
          <td>{escape(row.latest_at)}</td>
          <td>{escape(_simple_data_center_impact(row))}</td>
        </tr>"""
        for row in rows_to_show
    )
    alerts = _simple_data_center_alerts(rows_to_show)
    alert_items = "".join(
        f'<li class="data-center-alert">{escape(item)}</li>' for item in alerts
    )
    conclusion = _simple_data_center_conclusion(data_center, rows_to_show)
    return f"""
      <section class="module panel data-center-panel" id="module-data-center" aria-label="数据中台">
        <div class="editor-toolbar">
          <div><h3>数据中台</h3><p class="section-subtitle">只看数据能不能用、哪里有问题、是否影响分析。</p></div>
          <div class="module-header-meta">
            <span class="portfolio-chip">{escape(data_center.status)} · {escape(data_center.updated_at)}</span>
            {_render_module_refresh_tools(refresh_time=data_center.updated_at, stock_code=stock_code, provider_name=provider_name, holdings_path=holdings_path, workspace="data-center")}
          </div>
        </div>
        <div class="data-center-brief">
          <span>数据状态：{escape(data_center.status)}</span>
          <span>更新时间：{escape(data_center.updated_at)}</span>
          <strong>结论：{escape(conclusion)}</strong>
        </div>
        <table class="data-table">
          <thead><tr><th>数据</th><th>状态</th><th>更新时间</th><th>影响</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <div class="data-center-alert-box {'high' if data_center.status == '影响分析' else ''}">
          <strong>预警</strong><ul class="data-center-alert-list">{alert_items}</ul>
        </div>
      </section>"""


def _simple_data_center_rows(rows: list[DataCenterRow]) -> list[DataCenterRow]:
    core_categories = ["K线行情", "资金面", "新闻舆情", "公告", "基本面", "全链路校验"]
    by_category = {row.category: row for row in rows}
    return [by_category[item] for item in core_categories if item in by_category]


def _simple_data_center_impact(row: DataCenterRow) -> str:
    if row.missing and row.missing != "无":
        return f"{row.impact}；缺口：{row.missing}"
    return row.impact


def _simple_data_center_conclusion(
    data_center: DataCenterView, rows: list[DataCenterRow]
) -> str:
    if data_center.status == "影响分析":
        blocked = [row.category for row in rows if row.level == "blocked"]
        return f"{'、'.join(blocked[:3])} 会影响分析" if blocked else "有数据缺口会影响分析"
    if data_center.status == "需复核":
        warnings = [row.category for row in rows if row.level == "warn"]
        return f"{'、'.join(warnings[:3])} 需复核" if warnings else "部分数据需复核"
    return "数据可用"


def _simple_data_center_alerts(rows: list[DataCenterRow]) -> list[str]:
    alerts = [
        _simple_data_center_alert(row)
        for row in rows
        if row.level in {"warn", "blocked"} and row.impact != "不影响分析"
    ]
    return alerts[:3] or ["暂无影响分析的预警"]


def _simple_data_center_alert(row: DataCenterRow) -> str:
    if row.missing and row.missing != "无":
        return f"{row.category}：{row.status}，{row.missing}，{row.impact}"
    return f"{row.category}：{row.status}，{row.impact}"


def _render_data_center_summary(data_center: DataCenterView) -> str:
    blocked_count = sum(1 for row in data_center.rows if row.level == "blocked")
    warn_count = sum(1 for row in data_center.rows if row.level == "warn")
    if blocked_count:
        message = f"{blocked_count} 个数据域影响分析，先核对数据中台"
        level = "blocked"
    elif warn_count:
        message = f"{warn_count} 个数据域需复核"
        level = "warn"
    else:
        message = "数据可用"
        level = "ok"
    return f"""
      <div class="data-center-summary {escape(level)}" aria-label="数据中台摘要">
        <span>数据中台：{escape(data_center.status)}</span>
        <strong>{escape(message)}</strong>
        <span>更新 {escape(data_center.updated_at)}</span>
        <a href="#data-center">查看完整状态</a>
      </div>"""


def _data_center_anchor(category: str) -> str:
    mapping = {
        "大盘行情": "data-domain-market",
        "K线行情": "data-domain-kline",
        "技术面": "data-domain-technical",
        "候选池": "data-domain-candidates",
        "资金面": "data-domain-fund",
        "新闻舆情": "data-domain-news",
        "公告": "data-domain-announcement",
        "基本面": "data-domain-fundamental",
        "全链路校验": "data-domain-chain",
    }
    return mapping.get(category, f"data-domain-{category}")


def _freshness_detail(quality: DataQualityView) -> str:
    kline_warning = next(
        (warning for warning in quality.warnings if warning.startswith("K线已滞后")),
        "",
    )
    if kline_warning:
        return kline_warning
    if any("自动更新已滞后" in warning for warning in quality.warnings):
        return "自动更新已滞后，先刷新数据流水线"
    if any("数据已滞后" in warning for warning in quality.warnings):
        return "已滞后，不能按今天盘面执行"
    context_warnings = [
        warning
        for warning in quality.warnings
        if warning.startswith("市场新闻")
    ]
    if context_warnings:
        return "；".join(context_warnings[:2])
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
        if position.risk_level == "高" or (position.pnl >= 0 and position.trend == "下降趋势"):
            red.append(name)
        elif position.pnl >= 0 and position.trend == "上升趋势":
            green.append(name)
        elif position.pnl < 0 or position.trend == "下降趋势" or position.risk_level == "中":
            yellow.append(name)

    opportunities = [item.name for item in candidates.candidates if item.name not in held_names][:4]
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
        return f"第{rank}位涨停集中：资金抱团明显；{spread}，涨停 {item.limit_up_count}，{amount}"
    if item.amount_change >= 5:
        if item.amount_change >= 20:
            return (
                f"第{rank}位成交爆发：量能变化过大，先防高位分歧；"
                f"{spread}，涨停 {item.limit_up_count}，{amount}"
            )
        if item.amount_change >= 10:
            return (
                f"第{rank}位增量资金较强：需要看前排能否继续承接；"
                f"{spread}，涨停 {item.limit_up_count}，{amount}"
            )
        return (
            f"第{rank}位温和放量：有增量资金参与，但仍需次日确认；"
            f"{spread}，涨停 {item.limit_up_count}，{amount}"
        )
    if item.risk != "风险可控":
        return f"第{rank}位强势但分歧高：只看前排承接；{spread}，风险 {item.risk}，{amount}"
    if item.advancing_ratio >= 0.8:
        return (
            f"第{rank}位覆盖面较广：观察能否从前排扩散到低位；"
            f"{spread}，资金 {item.fund_status}，{amount}"
        )
    return (
        f"第{rank}位少数个股带动：持续性看明日扩散；{spread}，涨停 {item.limit_up_count}，{amount}"
    )


def _render_hot_opportunity_module(
    *,
    sectors: SectorAnalysisReport,
    candidates: CandidatePoolReport,
    market: MarketSnapshot,
    candidate_universe: list[CandidateStockRawData],
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    candidate_code: str,
    candidate_group: str,
    candidate_strategy: str,
    candidate_universe_metadata: dict[str, str] | None = None,
    quality: DataQualityView | None = None,
    refresh_time: str = "",
) -> str:
    del candidate_code, candidate_group, candidate_strategy, candidate_universe_metadata
    rows = _render_opportunity_recommendation_rows(
        sectors=sectors,
        candidates=candidates,
        candidate_universe=candidate_universe,
        provider_name=provider_name,
        holdings_path=holdings_path,
        quality=quality,
    )
    if not rows:
        rows = "<tr><td colspan='3'>暂无推荐；等待板块和候选股票刷新。</td></tr>"
    mainline = "、".join(sectors.market_mainline[:3]) or (
        sectors.sectors[0].name if sectors.sectors else "待确认"
    )
    candidate_state = "排序暂停" if quality and quality.gate_level == "blocked" else f"推荐 {min(len(candidates.candidates), 10)} 只"
    return f"""
    <section class="module" id="module-opportunity">
      <div class="module-header"><div><h2 class="module-title">热点机会</h2><p class="module-desc">只展示推荐板块、推荐股票和推荐原因。</p></div><div class="module-header-meta"><span class="risk-pill mid">{escape(mainline)}</span><span class="status-pill">{escape(candidate_state)}</span>{_render_module_refresh_tools(refresh_time=refresh_time, stock_code=stock_code, provider_name=provider_name, holdings_path=holdings_path, workspace="opportunity")}</div></div>
      <div class="panel opportunity-focus-panel">
        <table class="data-table candidates-table"><thead><tr><th>推荐板块</th><th>推荐股票</th><th>推荐原因</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
    </section>"""


def _render_opportunity_recommendation_rows(
    *,
    sectors: SectorAnalysisReport,
    candidates: CandidatePoolReport,
    candidate_universe: list[CandidateStockRawData],
    provider_name: str,
    holdings_path: str,
    quality: DataQualityView | None,
) -> str:
    sector_rows = "".join(
        _render_opportunity_recommendation_sector_row(item, candidate_universe)
        for item in sectors.sectors[:3]
    )
    raw_by_code = _candidate_raw_lookup(candidate_universe)
    candidate_rows = "".join(
        _render_opportunity_recommendation_candidate_row(
            item,
            raw=raw_by_code.get(item.code),
            provider_name=provider_name,
            holdings_path=holdings_path,
            pool_price_reliable=candidates.price_reliable,
            quality=quality,
        )
        for item in candidates.candidates[:7]
    )
    return sector_rows + candidate_rows


def _render_opportunity_recommendation_candidate_row(
    item: CandidateStockAnalysis,
    *,
    raw: CandidateStockRawData | None = None,
    provider_name: str,
    holdings_path: str,
    pool_price_reliable: bool,
    quality: DataQualityView | None = None,
) -> str:
    reason = _opportunity_candidate_cause(item, raw=raw)
    reason = f"个股原因：{reason}"
    stale = bool(quality and any("数据已滞后" in warning for warning in quality.warnings))
    if stale:
        reason = f"{reason}；风险原因：数据质量：已滞后，不能排到前列"
    elif not (pool_price_reliable and item.price_reliable):
        reason = f"{reason}；风险原因：待补数据"
    else:
        reason = f"{reason}；入选原因：价格可靠"
    query = urlencode({"code": item.code, "provider": provider_name, "holdings": holdings_path})
    stock_link = f'<a href="/?{query}#stock">{escape(item.name)}<span>{escape(item.code)}</span></a>'
    return (
        "<tr>"
        f"<td>{escape(localize_sector_name(item.sector) or '未识别主题')}</td>"
        f"<td class='name-cell'><strong>{stock_link}</strong></td>"
        f"<td>{escape(reason)}</td>"
        "</tr>"
    )


def _candidate_raw_lookup(
    candidate_universe: list[CandidateStockRawData],
) -> dict[str, CandidateStockRawData]:
    return {item.code: item for item in candidate_universe}


def _opportunity_candidate_cause(
    item: CandidateStockAnalysis,
    *,
    raw: CandidateStockRawData | None = None,
) -> str:
    if raw is not None and raw.bars:
        return "；".join(
            [
                _opportunity_week_trend_reason(raw),
                _opportunity_technical_reason(raw),
                _opportunity_fund_reason(raw),
                _opportunity_news_reason(raw),
                _opportunity_valuation_reason(raw),
            ]
        )
    causes: list[str] = []
    raw_reasons = item.reasons[:4]
    if any("强度" in reason for reason in raw_reasons):
        causes.append("所属板块强度靠前，具备主线筛选价值")
    if any("短期均线" in reason for reason in raw_reasons):
        causes.append("价格站上短期均线，趋势结构未破")
    if any("市场主线" in reason for reason in raw_reasons):
        causes.append("与当前主线同向，优先进入复核名单")
    if any("资金净流入" in reason for reason in raw_reasons):
        causes.append("资金流入提供承接线索")
    if any("量能放大" in reason for reason in raw_reasons):
        causes.append("量能放大，说明有新增资金关注")
    if not causes:
        causes = raw_reasons or ["等待补充技术、资金或消息证据"]
    return "；".join(causes[:3])


def _opportunity_week_trend_reason(raw: CandidateStockRawData) -> str:
    bars = raw.bars[-5:]
    if len(bars) < 2:
        return "一周趋势：K线不足，不能判断周内延续"
    week_pct = pct_change(bars[0].close, bars[-1].close)
    up_days = sum(1 for previous, current in zip(bars, bars[1:]) if current.close > previous.close)
    down_days = sum(1 for previous, current in zip(bars, bars[1:]) if current.close < previous.close)
    latest_pct = pct_change(bars[-2].close, bars[-1].close)
    recent_high = max(bar.close for bar in bars)
    pullback_from_high = pct_change(recent_high, bars[-1].close)
    if down_days >= 2 and pullback_from_high <= -4:
        state = (
            f"近5日转弱 {week_pct:.2f}%，从周内高点回落 {pullback_from_high:.2f}%，"
            "先看承接是否恢复"
        )
    elif week_pct >= 8 and up_days >= 3:
        state = f"近5日上涨 {week_pct:.2f}%，{up_days} 天收涨，趋势延续较强"
    elif week_pct >= 3:
        state = f"近5日上涨 {week_pct:.2f}%，但需看是否继续放量"
    elif week_pct <= -3 and down_days >= 2:
        state = f"近5日转弱 {week_pct:.2f}%，反弹前先看止跌"
    elif latest_pct < -2:
        state = f"近5日震荡 {week_pct:.2f}%，最新一日回落 {latest_pct:.2f}%"
    else:
        state = f"近5日震荡 {week_pct:.2f}%，还不是单边趋势"
    return f"一周趋势：{state}"


def _opportunity_technical_reason(raw: CandidateStockRawData) -> str:
    closes = [bar.close for bar in raw.bars]
    latest = raw.bars[-1]
    ma5 = sma(closes, min(5, len(closes))) or latest.close
    ma10 = sma(closes, min(10, len(closes))) or ma5
    recent_high = max(bar.high for bar in raw.bars[-5:])
    recent_low = min(bar.low for bar in raw.bars[-5:])
    if latest.close >= ma5 >= ma10:
        trend = f"站上5日线 {ma5:.2f}，短线结构偏强"
    elif latest.close >= ma5:
        trend = f"站上5日线 {ma5:.2f}，但10日线仍需确认"
    else:
        trend = f"低于5日线 {ma5:.2f}，技术面先降级观察"
    return f"技术面：{trend}；5日区间 {recent_low:.2f}-{recent_high:.2f}"


def _opportunity_fund_reason(raw: CandidateStockRawData) -> str:
    volumes = [bar.volume for bar in raw.bars]
    volume_ratio = _candidate_volume_ratio(volumes)
    fund_flow = raw.fund_flow or 0.0
    amount_text = f"成交额 {raw.amount:.1f}亿" if raw.amount else "成交额待补"
    turnover_text = f"换手 {raw.turnover_rate:.1f}%" if raw.turnover_rate else "换手待补"
    if fund_flow > 0:
        flow = f"净流入 {fund_flow:.2f}亿"
    elif fund_flow < 0:
        flow = f"净流出 {abs(fund_flow):.2f}亿"
    else:
        flow = "净流向待确认"
    if volume_ratio >= 1.3:
        volume = f"量能放大 {volume_ratio:.2f}x"
    elif volume_ratio <= 0.8 and volume_ratio > 0:
        volume = f"量能收缩 {volume_ratio:.2f}x"
    elif volume_ratio > 0:
        volume = f"量能平稳 {volume_ratio:.2f}x"
    else:
        volume = "量能待补"
    return f"资金面：{flow}，{volume}，{turnover_text}，{amount_text}"


def _candidate_volume_ratio(volumes: list[float]) -> float:
    if len(volumes) < 2:
        return 0.0
    latest = volumes[-1]
    base = sum(volumes[-5:]) / min(len(volumes), 5)
    return latest / base if base else 0.0


def _opportunity_news_reason(raw: CandidateStockRawData) -> str:
    if raw.news_items:
        latest = raw.news_items[0]
        source = latest.source or "新闻源"
        title = _short_condition(latest.title or latest.summary or "未命名消息", 34)
        return f"消息面：{source}最新消息“{title}”，需确认是否构成催化"
    if raw.announcements:
        latest = raw.announcements[0]
        title = str(latest.get("title") or latest.get("公告标题") or "未命名公告")
        return f"消息面：公告“{_short_condition(title, 34)}”，先排查风险/催化属性"
    return "消息面：未接入个股新闻，不作为推荐理由"


def _opportunity_valuation_reason(raw: CandidateStockRawData) -> str:
    if raw.pe_ttm is None:
        return "基本面：估值待补，不能用低估值解释机会"
    if raw.pe_ttm >= 70:
        return f"基本面：PE(TTM) {raw.pe_ttm:.1f} 偏高，防止题材高位分歧"
    if raw.pe_ttm <= 25:
        return f"基本面：PE(TTM) {raw.pe_ttm:.1f} 相对不高，估值压力较小"
    return f"基本面：PE(TTM) {raw.pe_ttm:.1f}，重点看业绩与题材是否匹配"


def _render_opportunity_recommendation_sector_row(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    risk = _sector_risk_text(item)
    reason_parts = [
        f"板块原因：{_opportunity_sector_cause(item, candidate_universe)}",
        f"入选原因：{_opportunity_sector_entry_reason(item)}",
    ]
    if risk:
        reason_parts.append(f"风险原因：{risk}")
    return (
        "<tr>"
        f"<td>{escape(localize_sector_name(item.name))}</td>"
        f"<td>{escape(_sector_representative_stocks(item, candidate_universe))}</td>"
        f"<td>{escape('；'.join(part for part in reason_parts if part))}</td>"
        "</tr>"
    )


def _opportunity_sector_cause(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    evidence = _sector_causal_evidence(item.name, candidate_universe)
    if evidence:
        return "；".join(evidence[:3])
    return "未识别明确消息/公告/基本面催化，只能列为观察方向，不把涨跌当原因"


def _opportunity_sector_entry_reason(item) -> str:
    parts: list[str] = []
    if item.rotation_status == "市场主线":
        parts.append("处在市场主线")
    elif item.rotation_status == "轮动增强":
        parts.append("轮动强度提升")
    if item.continuity in {"持续性强", "持续性观察"}:
        parts.append(item.continuity)
    if item.fund_status == "资金活跃":
        parts.append("资金面：资金活跃，等待消息/公告/基本面确认")
    elif item.amount_change > 0:
        parts.append("资金面：成交放大，等待消息/公告/基本面确认")
    return "；".join(parts) if parts else "仅作观察，等待资金、消息、公告和基本面确认"


def _render_opportunity_candidate_cards(
    candidates: CandidatePoolReport,
    provider_name: str,
    holdings_path: str,
    *,
    quality: DataQualityView | None = None,
) -> str:
    if not candidates.candidates:
        body = """
          <div class="empty-state">
            <strong>候选列表暂无</strong>
            <p>候选池为空时不做机会排序，先刷新快照或补充候选源。</p>
          </div>"""
    else:
        body = "".join(
            _render_opportunity_candidate_card(
                item,
                candidates.price_reliable,
                provider_name,
                holdings_path,
                quality=quality,
            )
            for item in candidates.candidates[:6]
        )
    return f"""
      <div class="panel opportunity-cards-panel">
        <div class="editor-toolbar">
          <div><h3>候选列表</h3><p class="section-subtitle">每张卡只回答策略、证据、风险、数据质量和下一步，不把观察优先级写成买入评级。</p></div>
          <span class="portfolio-chip">可验证 / 只观察 / 风险排除 / 待补数据</span>
        </div>
        <div class="opportunity-card-grid">{body}</div>
      </div>"""


def _render_opportunity_candidate_card(
    item: CandidateStockAnalysis,
    pool_price_reliable: bool,
    provider_name: str,
    holdings_path: str,
    *,
    quality: DataQualityView | None = None,
) -> str:
    strategy = _candidate_card_strategy(item)
    evidence = "；".join(item.reasons[:2]) if item.reasons else "等待补充技术、资金或消息证据"
    query = urlencode(
        {
            "code": item.code,
            "provider": provider_name,
            "holdings": holdings_path,
            "candidate_source": "opportunity",
            "candidate_strategy_label": strategy,
            "candidate_evidence": evidence,
        }
    )
    risk = "；".join(item.risks[:2]) if item.risks else "未识别重大风险，仍需复核公告和流动性"
    stale = bool(quality and any("数据已滞后" in warning for warning in quality.warnings))
    price_ready = pool_price_reliable and item.price_reliable and not stale
    if stale:
        data_quality = "数据质量：已滞后，不能排到前列"
    elif price_ready:
        data_quality = "数据质量：Provider/交易日一致，价格可排序"
    else:
        data_quality = "数据质量：待补数据，不能排到前列"
    tag = "待补数据" if not price_ready else "只观察" if item.score < 70 else "可验证"
    return f"""
          <article class="opportunity-candidate-card {escape(tag)}">
            <div class="opportunity-candidate-head">
              <span>{escape(item.code)}</span>
              <strong>{escape(item.name)}</strong>
              <em>{escape(tag)}</em>
            </div>
            <p>策略：{escape(strategy)}</p>
            <p>入选证据：{escape(evidence)}</p>
            <p>主要风险：{escape(risk)}</p>
            <p>{escape(data_quality)}</p>
            <a class="primary-button" href="/?{query}#stock">进入股票分析验证六维证据；不直接买入</a>
          </article>"""


def _candidate_card_strategy(item: CandidateStockAnalysis) -> str:
    reason_text = "；".join(item.reasons)
    if "放量" in reason_text or "突破" in reason_text:
        return "放量突破"
    if item.pct_change < -3:
        return "超跌修复"
    if item.score >= 75:
        return "主线强势 + 资金抱团"
    return "主线观察"


def _render_opportunity_strategy_funnel(
    market: MarketSnapshot,
    top_sector,
    top_candidate,
    candidates: CandidatePoolReport,
    metadata: dict[str, str],
) -> str:
    gate = "允许验证" if market.heat_score >= 55 and market.limit_down_count < 20 else "只观察"
    if not candidates.price_reliable:
        gate = "待补数据"
    top_name = top_candidate.name if top_candidate else "待刷新候选"
    sector_name = top_sector.name if top_sector else "主线待确认"
    scan_total = metadata.get("universe_size") or metadata.get("scanned") or str(len(candidates.candidates))
    channels = [
        ("主线强势", f"{sector_name} 是否连续扩散"),
        ("资金抱团", "成交额、量能和换手是否健康"),
        ("放量突破", f"{top_name} 是否突破后站稳"),
        ("超跌修复", "风险释放后再看企稳，不接飞刀"),
        ("公告催化", "财报、回购、订单和政策线索只做触发"),
        ("风险排除", "数据过期、公告风险、跌停和流动性不足先剔除"),
    ]
    channel_html = "".join(
        f"<div class='opportunity-channel'><strong>{escape(label)}</strong><span>{escape(note)}</span></div>"
        for label, note in channels
    )
    excluded = _opportunity_exclusion_reasons(market, candidates)
    return f"""
      <div class="opportunity-funnel-panel">
        <div class="opportunity-funnel-hero simple-panel">
          <h3>机会状态</h3>
          <p>先看闸门，再按策略筛选，最后进入个股分析。</p>
          <div class="market-action-snapshot"><span>机会总闸门</span><strong>{escape(gate)}</strong></div>
        </div>
        <div class="panel opportunity-channel-panel"><h3>策略通道</h3><div class="opportunity-channel-grid">{channel_html}</div></div>
        <div class="opportunity-filter-box">
          <h3>筛选条件</h3>
          <p>扫描范围 {escape(scan_total)}；Provider 与交易日见全局状态条；价格质量：{escape("可靠" if candidates.price_reliable else "待补数据")}。</p>
          <h3>风险排除</h3>
          <ul>{_li_join(excluded)}</ul>
          <a class="primary-button" href="#stock" data-jump="stock">进入股票分析</a>
        </div>
      </div>"""


def _opportunity_exclusion_reasons(
    market: MarketSnapshot,
    candidates: CandidatePoolReport,
) -> list[str]:
    reasons: list[str] = []
    if market.limit_down_count >= 20:
        reasons.append(f"跌停 {market.limit_down_count} 家，追高候选全部降级。")
    if not candidates.price_reliable:
        reasons.append("候选价格数据不可靠，排序只作为待验证清单。")
    candidate_risks = [
        risk
        for candidate in candidates.candidates[:4]
        for risk in candidate.risks[:1]
        if risk
    ]
    if candidate_risks:
        reasons.extend(candidate_risks[:2])
    if not reasons:
        reasons.append("未识别重大风险，但仍需逐只复核公告、流动性和买点偏离。")
    return reasons


def _render_opportunity_sector_row(item, candidate_universe: list[CandidateStockRawData]) -> str:
    risk = _sector_risk_text(item)
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.rotation_status)}</span></td>"
        f"<td>{item.heat_score}/100<span>{escape(_sector_strength_reason(item))}</span></td>"
        f"<td>{item.advancing_ratio:.0%}</td>"
        f"<td>{escape(_sector_representative_stocks(item, candidate_universe))}</td>"
        f"<td>{escape(_sector_next_check(item))}<span>{escape(risk)}</span></td></tr>"
    )


def _render_opportunity_theme_row(item, candidate_universe: list[CandidateStockRawData]) -> str:
    risk = _sector_risk_text(item)
    reason_parts = [
        _sector_strength_reason(item),
        f"扩散 {item.advancing_ratio:.0%}",
        item.continuity,
    ]
    if risk:
        reason_parts.append(risk)
    reason = "；".join(part for part in reason_parts if part)
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>{escape(item.rotation_status)}</span></td>"
        f"<td>{item.heat_score}/100</td>"
        f"<td>{escape(_sector_representative_stocks(item, candidate_universe))}</td>"
        f"<td>{escape(reason)}</td></tr>"
    )


def _render_opportunity_focused_candidate_row(
    item: CandidateStockAnalysis,
    *,
    provider_name: str,
    holdings_path: str,
    pool_price_reliable: bool,
    quality: DataQualityView | None = None,
) -> str:
    reason = "；".join(item.reasons[:2]) if item.reasons else "等待补充技术、资金或消息证据"
    stale = bool(quality and any("数据已滞后" in warning for warning in quality.warnings))
    if stale:
        reason = f"{reason}；数据质量：已滞后，不能排到前列"
    elif not (pool_price_reliable and item.price_reliable):
        reason = f"{reason}；数据质量：待补数据"
    query = urlencode(
        {
            "code": item.code,
            "provider": provider_name,
            "holdings": holdings_path,
            "candidate_source": "opportunity",
            "candidate_strategy_label": _candidate_card_strategy(item),
            "candidate_evidence": reason,
        }
    )
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>{escape(item.code)}</span></td>"
        f"<td>{escape(item.sector)}</td>"
        f"<td>{escape(reason)}</td>"
        f'<td><a class="primary-button" href="/?{query}#stock" data-jump="stock">进入个股分析</a></td></tr>'
    )


def _render_opportunity_candidate_row(
    item,
    *,
    provider_name: str,
    holdings_path: str,
    stock_code: str,
) -> str:
    del stock_code
    reason = "；".join(item.reasons[:2]) if item.reasons else "等待补充技术/资金/消息证据"
    next_step = item.watch_conditions[0] if item.watch_conditions else "进入个股分析复核"
    query = urlencode(
        {
            "code": item.code,
            "provider": provider_name,
            "holdings": holdings_path,
            "candidate_source": "opportunity",
            "candidate_strategy_label": _candidate_card_strategy(item),
            "candidate_evidence": reason,
        }
    )
    return (
        f"<tr><td>{escape(item.code)}</td>"
        f"<td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.sector)}</span></td>"
        f"<td>{item.score}/100</td>"
        f"<td>{item.pct_change:.2f}%</td>"
        f"<td>{escape(reason)}</td>"
        f"<td><a class='primary-button' href='/?{query}#stock'>进入股票分析<span>{escape(next_step)}</span></a></td></tr>"
    )


def _opportunity_action(market: MarketSnapshot, top_sector, top_candidate) -> str:
    if market.heat_score < 45 or market.limit_down_count >= 20:
        return "先防守"
    if top_sector is None or top_candidate is None:
        return "等数据补齐"
    if top_sector.heat_score >= 70 and market.limit_up_count >= 20:
        return "聚焦前排"
    return "观察轮动"


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
        <div class="panel" style="grid-column:1 / -1"><h3>风险提醒</h3><ul class="reason-list">{risk_items}</ul></div>
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
        <div class="panel" style="grid-column:1 / -1"><h3>风险提醒</h3><ul class="reason-list">{risk_items}</ul></div>
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
    username = "已配置" if enabled else "未配置"
    db_path = str(config.db_path) if enabled else "未启用"
    current_username = (
        current_user.username if current_user is not None else ("未登录" if enabled else "未启用")
    )
    current_role = current_user.role if current_user is not None else ("未登录" if enabled else "本地")
    portfolio_mode = "按账号独立" if enabled else "本地单人文件"
    shared_scope = "行情 / 板块 / 选股 / 日报 / 消息配置" if enabled else "本机配置"
    logout_form = (
        """
        <form method="post" action="/logout">
          <button class="ghost-button" type="submit">退出登录</button>
        </form>"""
        if enabled and current_user is not None
        else ""
    )
    password_form = (
        """
        <form class="portfolio-form-grid" method="post" action="/account/password" style="margin-top:14px">
          <label class="field-stack">当前密码<input name="current_password" type="password" autocomplete="current-password" /></label>
          <label class="field-stack">新密码<input name="new_password" type="password" autocomplete="new-password" /></label>
          <label class="field-stack">确认新密码<input name="confirm_password" type="password" autocomplete="new-password" /></label>
          <div class="form-actions"><button class="primary-button" type="submit">修改密码</button></div>
        </form>"""
        if enabled and current_user is not None
        else '<div class="portfolio-action-bar" style="margin-top:12px"><a class="ghost-button" href="/login">登录 / 注册</a></div>'
    )
    morning_email_panel = _render_morning_email_settings_panel(current_user)
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>账号体系</h3><p class="section-subtitle">账号负责登录和持仓隔离；行情、板块、选股、日报和消息配置保持全站一致。</p></div>
          <span class="portfolio-chip">登录保护：{escape(status)}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>当前账号</span><strong>{escape(current_username)}</strong><p class="kpi-foot">登录后自动使用自己的持仓账本。</p></div>
          <div class="summary-card"><span>账号角色</span><strong>角色：{escape(current_role)}</strong><p class="kpi-foot">owner 可维护全局配置；member 只管理自己的持仓。</p></div>
          <div class="summary-card"><span>持仓隔离</span><strong>{escape(portfolio_mode)}</strong><p class="kpi-foot">当前账本：{escape(holdings_path)}</p></div>
          <div class="summary-card"><span>共享能力</span><strong>全站一致</strong><p class="kpi-foot">{escape(shared_scope)}</p></div>
          <div class="summary-card"><span>开放注册</span><strong>{escape(registration_status)}</strong><p class="kpi-foot">开放后新账号注册即获得访问权限。</p></div>
          <div class="summary-card"><span>登录保护</span><strong>{escape(status)}</strong></div>
          <div class="summary-card"><span>管理员账号</span><strong>{escape(username)}</strong></div>
          <div class="summary-card"><span>账号库</span><strong>{escape(db_path)}</strong><p class="kpi-foot">只显示路径，不显示密码或会话密钥。</p></div>
        </div>
        {password_form}
        <div class="portfolio-action-bar" style="margin-top:12px">{logout_form}</div>
      </div>
      {morning_email_panel}"""


def _render_morning_email_settings_panel(current_user: AuthUser | None) -> str:
    if current_user is None:
        return ""
    preferences = load_morning_email_preferences(
        current_user.id,
        username=current_user.username,
        user_data_dir=os.getenv("STOCK_TS_USER_DATA_DIR", DEFAULT_USER_DATA_DIR),
    )
    settings = get_settings()
    email_status = _email_config_status_label(settings)
    enabled_checked = " checked" if preferences.enabled else ""
    receiver = preferences.receiver or (current_user.username if "@" in current_user.username else "")
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>每日晨报邮箱</h3><p class="section-subtitle">配置当前账号的接收邮箱和发送时间；SMTP 发送账号由系统统一配置。</p></div>
          <span class="portfolio-chip">发送通道：{escape(email_status)}</span>
        </div>
        <form class="portfolio-form-grid" method="post" action="/account/morning-email">
          <label class="field-stack field-span-2">接收邮箱<input name="morning_email_receiver" value="{escape(receiver)}" placeholder="name@example.com，多个用英文逗号分隔" /></label>
          <label class="field-stack">发送时间<input name="morning_email_time" type="time" value="{escape(preferences.send_time)}" /></label>
          <label class="checkbox-line"><input type="checkbox" name="morning_email_enabled" value="1"{enabled_checked} />启用自动晨报</label>
          <div class="form-actions"><button class="primary-button" type="submit">保存晨报配置</button></div>
        </form>
        <form class="portfolio-action-bar" method="post" action="/account/morning-email/send" style="margin-top:12px">
          <button class="ghost-button" type="submit">立即发送晨报</button>
        </form>
      </div>"""


def _render_account_management_module(
    *,
    provider_name: str,
    holdings_path: str,
    provider_class: str,
    stock_code: str,
    notice: SettingsNotice | None,
    current_user: AuthUser | None = None,
) -> str:
    del provider_class
    account_panel = _render_auth_settings_panel(
        current_user=current_user,
        holdings_path=holdings_path,
    )
    notice_html = _render_settings_notice(notice)
    owner_tools = ""
    if current_user is not None and current_user.role == "owner":
        owner_tools = _render_compact_status_module(
            provider_name,
            holdings_path,
            "tdx-snapshot",
            stock_code,
            notice,
        )
    else:
        owner_tools = """
      <div class="panel" style="margin-top:16px">
        <h3>普通账号权限</h3>
        <p class="section-subtitle">普通账号只管理自己的持仓、成本、股数和个股分析；行情、数据刷新、邮件和全局配置由管理员统一维护。</p>
      </div>"""
    return f"""
    <section class="module" id="module-account">
      <div class="module-header"><div><h2 class="module-title">账户管理</h2><p class="module-desc">登录、退出、密码和个人持仓账本。行情、板块、机会和数据中台全站一致。</p></div><span class="status-pill">正规账户体系</span></div>
      {notice_html}
      {account_panel}
      {owner_tools}
    </section>"""


def _render_compact_market_module(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    portfolio: PortfolioAnalysisReport,
    candidates: CandidatePoolReport,
    *,
    candidate_universe: list[CandidateStockRawData] | None = None,
    news: NewsSentimentReport | None = None,
    refresh_time: str,
    stock_code: str,
    provider_name: str,
    holdings_path: str,
) -> str:
    del portfolio
    candidate_universe = candidate_universe or []
    distribution = _render_market_distribution_chart(market, candidate_universe, candidates)
    strong_sectors = _render_market_strength_sector_panel(
        "强势板块Top5", sectors, candidate_universe, reverse=True
    )
    weak_sectors = _render_market_strength_sector_panel(
        "弱势板块Top5", sectors, candidate_universe, reverse=False
    )
    analysis_panel = _render_professional_market_diagnosis(market, sectors, candidate_universe)
    wide_move_panel = _render_market_wide_move_panel(
        candidate_universe,
        candidates,
        provider_name=provider_name,
        holdings_path=holdings_path,
    )
    event_panel = _render_market_sentiment_panel(news, candidate_universe=candidate_universe)
    return f"""
    <section class="module market-console" id="module-market">
      <div class="module-header market-header">
        <div>
          <h2 class="module-title">每日大盘</h2>
          <p class="module-desc">当前时刻股票涨跌统计、强弱板块与分析。</p>
        </div>
        <div class="module-header-meta">
          <span class="market-state-pill {_market_risk_tone(market)}">{escape(market.trade_date)}</span>
          {_render_module_refresh_tools(refresh_time=refresh_time, stock_code=stock_code, provider_name=provider_name, holdings_path=holdings_path, workspace="market")}
        </div>
      </div>
      {distribution}
      {wide_move_panel}
      <div class="market-sector-duo">
        {strong_sectors}
        {weak_sectors}
      </div>
      {analysis_panel}
      {event_panel}
    </section>"""


def _render_market_distribution_chart(
    market: MarketSnapshot,
    candidate_universe: list[CandidateStockRawData],
    candidates: CandidatePoolReport,
) -> str:
    pct_values = _market_distribution_pct_values(candidate_universe, candidates)
    bins = [
        ("涨停", market.limit_up_count),
        (">6%", sum(1 for value in pct_values if value > 6)),
        (">3%", sum(1 for value in pct_values if value > 3)),
        ("0~3%", sum(1 for value in pct_values if 0 < value <= 3)),
        ("平盘", _format_market_count(market, "unchanged")),
        ("-3~0%", sum(1 for value in pct_values if -3 <= value < 0)),
        ("<-3%", sum(1 for value in pct_values if value < -3)),
        ("<-6%", sum(1 for value in pct_values if value < -6)),
        ("跌停", market.limit_down_count),
    ]
    counts = [count if isinstance(count, int) else 0 for _, count in bins]
    max_count = max(counts) if counts else 1
    bars = "".join(
        _render_market_distribution_bar(label, count, max_count)
        for label, count in bins
    )
    breadth = (
        f"{_format_market_count(market, 'advancing')} / "
        f"{_format_market_count(market, 'declining')} / "
        f"{_format_market_count(market, 'unchanged')}"
    )
    return f"""
      <div class="panel market-distribution-panel">
        <div class="editor-toolbar">
          <div><h3>股票涨跌统计</h3></div>
          <span class="portfolio-chip">上涨/下跌/平盘 {escape(breadth)}</span>
        </div>
        <div class="market-distribution-bars">{bars}</div>
      </div>"""


def _render_market_wide_move_panel(
    candidate_universe: list[CandidateStockRawData],
    candidates: CandidatePoolReport,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    rows = _market_wide_move_rows(candidate_universe, candidates)
    all_up_rows = [item for item in rows if item.pct_change > 6]
    all_down_rows = [item for item in rows if item.pct_change < -6]
    up_rows = all_up_rows[:8]
    down_rows = all_down_rows[:8]
    if not up_rows and not down_rows:
        return """
      <div class="panel market-wide-move-panel">
        <div class="editor-toolbar"><div><h3>大涨大跌分析</h3></div><span class="portfolio-chip">暂无 &gt;6% / &lt;-6% 样本</span></div>
        <p class="section-subtitle">当前候选池没有返回大幅波动股票，先看涨跌统计和强弱板块。</p>
      </div>"""
    table_rows = _render_market_wide_move_rows(
        up_rows,
        direction=">6%上涨",
        up=True,
        provider_name=provider_name,
        holdings_path=holdings_path,
    )
    table_rows += _render_market_wide_move_rows(
        down_rows,
        direction="<-6%下跌",
        up=False,
        provider_name=provider_name,
        holdings_path=holdings_path,
    )
    theme_summary = _render_wide_move_theme_summary(all_up_rows, all_down_rows)
    return f"""
      <div class="panel market-wide-move-panel">
        <div class="editor-toolbar">
          <div><h3>大涨大跌分析</h3></div>
          <span class="portfolio-chip">&gt;6%上涨 {len(all_up_rows)} / &lt;-6%下跌 {len(all_down_rows)}</span>
        </div>
        {theme_summary}
        <table class="data-table compact-sector-table">
          <thead><tr><th>方向</th><th>股票</th><th>板块</th><th>分析</th></tr></thead>
          <tbody>{table_rows}</tbody>
        </table>
      </div>"""


def _render_wide_move_theme_summary(
    up_rows: list[LimitBoardRow],
    down_rows: list[LimitBoardRow],
) -> str:
    stats = _wide_move_theme_stats(up_rows, down_rows)
    if not stats:
        return ""
    summary = "、".join(
        f"{theme}：{counts['up']}只大涨，{counts['down']}只大跌"
        for theme, counts in stats[:4]
    )
    conclusion = _wide_move_theme_conclusion(stats)
    return f"""
        <div class="compact-note-card" style="margin:12px 0">
          <strong>板块扩散结论</strong>
          <p class="section-subtitle">{escape(summary)}；{escape(conclusion)}</p>
        </div>"""


def _wide_move_theme_stats(
    up_rows: list[LimitBoardRow],
    down_rows: list[LimitBoardRow],
) -> list[tuple[str, dict[str, int]]]:
    stats: dict[str, dict[str, int]] = {}
    for item in up_rows:
        theme = item.sector or "未分类"
        stats.setdefault(theme, {"up": 0, "down": 0})["up"] += 1
    for item in down_rows:
        theme = item.sector or "未分类"
        stats.setdefault(theme, {"up": 0, "down": 0})["down"] += 1
    sorted_stats = sorted(
        stats.items(),
        key=lambda item: (item[1]["up"] + item[1]["down"], item[1]["up"], -item[1]["down"]),
        reverse=True,
    )
    known_stats = [item for item in sorted_stats if _is_known_theme(item[0])]
    return known_stats or sorted_stats


def _wide_move_theme_conclusion(stats: list[tuple[str, dict[str, int]]]) -> str:
    strongest = max(stats, key=lambda item: item[1]["up"], default=None)
    weakest = max(stats, key=lambda item: item[1]["down"], default=None)
    pieces: list[str] = []
    if strongest and strongest[1]["up"] >= 2:
        pieces.append(f"{strongest[0]}出现板块共振")
    elif strongest and strongest[1]["up"] == 1:
        pieces.append("上涨更偏个股异动")
    if weakest and weakest[1]["down"] >= 2:
        pieces.append(f"{weakest[0]}出现板块退潮")
    elif weakest and weakest[1]["down"] == 1:
        pieces.append(f"{weakest[0]}先按单股风险复核")
    return "；".join(pieces) if pieces else "大幅波动样本不足，先观察持续性"


def _market_wide_move_rows(
    candidate_universe: list[CandidateStockRawData],
    candidates: CandidatePoolReport,
) -> list[LimitBoardRow]:
    rows = _build_limit_board_rows(candidate_universe)
    if not rows:
        rows = [
            LimitBoardRow(
                code=item.code,
                name=item.name,
                sector=item.sector,
                latest_close=item.latest_close,
                pct_change=item.pct_change,
            )
            for item in candidates.candidates
        ]
    big_up = sorted(
        (item for item in rows if item.pct_change > 6),
        key=lambda item: item.pct_change,
        reverse=True,
    )
    big_down = sorted(
        (item for item in rows if item.pct_change < -6),
        key=lambda item: item.pct_change,
    )
    return big_up + big_down


def _render_market_wide_move_rows(
    rows: list[LimitBoardRow],
    *,
    direction: str,
    up: bool,
    provider_name: str,
    holdings_path: str,
) -> str:
    if not rows:
        return (
            "<tr>"
            f"<td>{escape(direction)}</td>"
            "<td colspan='3'>暂无样本</td>"
            "</tr>"
        )
    return "".join(
        "<tr>"
        f"<td>{escape(direction)}</td>"
        f"<td class='name-cell'><strong>{_render_wide_move_stock_link(item, provider_name=provider_name, holdings_path=holdings_path)}</strong></td>"
        f"<td>{escape(item.sector)}</td>"
        f"<td>{escape(_wide_move_analysis(item, up=up))}</td>"
        "</tr>"
        for item in rows
    )


def _render_wide_move_stock_link(
    item: LimitBoardRow,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    query = urlencode({"code": item.code, "provider": provider_name, "holdings": holdings_path})
    label = f"{item.name} {item.pct_change:.2f}%"
    return (
        f'<a href="/?{escape(query)}#stock" data-jump="stock" '
        f'aria-label="查看 {escape(item.name)} 个股分析">'
        f"{escape(label)}<span>{escape(item.code)}</span></a>"
    )


def _wide_move_analysis(item: LimitBoardRow, *, up: bool) -> str:
    evidence = _candidate_causal_evidence(item)
    if evidence:
        return "；".join(evidence[:4])
    direction = "上涨" if up else "下跌"
    return (
        f"未识别明确消息/公告/基本面原因；当前只是{direction}异动，"
        "需继续查新闻、公告、财务和资金面"
    )


def _market_distribution_pct_values(
    candidate_universe: list[CandidateStockRawData],
    candidates: CandidatePoolReport,
) -> list[float]:
    values = [
        _candidate_raw_pct_change(item)
        for item in candidate_universe
        if _candidate_raw_pct_change(item) is not None
    ]
    if values:
        return [value for value in values if value is not None]
    return [item.pct_change for item in candidates.candidates]


def _candidate_raw_pct_change(item: CandidateStockRawData) -> float | None:
    if len(item.bars) < 2:
        return None
    previous = item.bars[-2].close
    latest = item.bars[-1].close
    if previous == 0:
        return None
    return (latest - previous) / previous * 100


def _render_market_distribution_bar(label: str, count: int | str, max_count: int) -> str:
    numeric = count if isinstance(count, int) else 0
    width = 0 if max_count <= 0 else max(4 if numeric else 0, numeric / max_count * 100)
    return f"""
        <div class="market-distribution-row">
          <span>{escape(label)}</span>
          <i><b style="width:{width:.0f}%"></b></i>
          <strong>{escape(str(count))}</strong>
        </div>"""


def _render_market_strength_sector_panel(
    title: str,
    sectors: SectorAnalysisReport,
    candidate_universe: list[CandidateStockRawData],
    *,
    reverse: bool,
) -> str:
    sorted_sectors = sorted(sectors.sectors, key=lambda item: item.pct_chg, reverse=reverse)[:5]
    if not sorted_sectors:
        rows = "<tr><td colspan='4'>暂无板块数据</td></tr>"
    else:
        rows = "".join(
            _render_market_strength_sector_row(item, candidate_universe, reverse=reverse)
            for item in sorted_sectors
        )
    return f"""
      <div class="panel market-strength-panel">
        <h3>{escape(title)}</h3>
        <table class="data-table compact-sector-table">
          <thead><tr><th>板块</th><th>涨跌</th><th>对应股票</th><th>分析</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _render_market_strength_sector_row(
    item,
    candidate_universe: list[CandidateStockRawData],
    *,
    reverse: bool,
) -> str:
    stocks = _theme_stocks_by_move(candidate_universe, item.name, reverse=reverse)
    stock_text = (
        "、".join(f"{stock.name} {stock.pct_change:.2f}%" for stock in stocks[:5])
        if stocks
        else "候选池暂无同主题样本"
    )
    analysis = _sector_strength_analysis(item, candidate_universe, reverse=reverse)
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>热度 {item.heat_score}/100</span></td>"
        f"<td>{item.pct_chg:.2f}%</td>"
        f"<td>{escape(stock_text)}</td>"
        f"<td>{escape(analysis)}</td></tr>"
    )


def _theme_stocks_by_move(
    candidate_universe: list[CandidateStockRawData],
    theme: str,
    *,
    reverse: bool,
) -> list[LimitBoardRow]:
    rows = [
        row
        for row in _build_limit_board_rows(candidate_universe)
        if row.sector.strip() == theme.strip()
    ]
    return sorted(rows, key=lambda item: item.pct_change, reverse=reverse)[:5]


def _sector_strength_analysis(
    item,
    candidate_universe: list[CandidateStockRawData],
    *,
    reverse: bool,
) -> str:
    if reverse:
        return _sector_strong_reason(item, candidate_universe)
    return _sector_weak_reason(item, candidate_universe)


def _sector_strong_reason(item, candidate_universe: list[CandidateStockRawData]) -> str:
    evidence = _sector_causal_evidence(item.name, candidate_universe)
    if evidence:
        return f"走强原因：{'；'.join(evidence[:3])}"
    return (
        "走强原因：未识别明确消息/公告/基本面催化；"
        "当前只看到盘面强弱，不能把上涨本身当原因；"
        f"资金面：{_sector_fund_context(item)}"
    )


def _sector_weak_reason(item, candidate_universe: list[CandidateStockRawData]) -> str:
    evidence = _sector_causal_evidence(item.name, candidate_universe)
    label = "走弱原因" if item.pct_chg < 0 or item.advancing_ratio < 0.5 else "相对弱势原因"
    if evidence:
        return f"{label}：{'；'.join(evidence[:3])}"
    return (
        f"{label}：未识别明确消息/公告/基本面利空；"
        "当前只看到盘面转弱，不能把下跌本身当原因；"
        f"资金面：{_sector_fund_context(item)}"
    )


def _sector_causal_evidence(
    theme: str,
    candidate_universe: list[CandidateStockRawData],
) -> list[str]:
    related = [
        item for item in candidate_universe if localize_sector_name(item.sector) == localize_sector_name(theme)
    ]
    evidence: list[str] = []
    for item in related:
        evidence.extend(_candidate_causal_evidence(item))
        if len(evidence) >= 4:
            break
    return _dedupe_texts(evidence)


def _candidate_causal_evidence(item: CandidateStockRawData | LimitBoardRow) -> list[str]:
    evidence: list[str] = []
    news_items = getattr(item, "news_items", []) or []
    announcements = getattr(item, "announcements", []) or []
    pe_ttm = getattr(item, "pe_ttm", None)
    fund_flow = getattr(item, "fund_flow", None)
    if news_items:
        title = _first_non_empty([news_items[0].title, news_items[0].summary])
        if title:
            evidence.append(f"消息面：{_short_condition(title, 36)}")
    if announcements:
        title = _announcement_title(announcements[0])
        if title:
            evidence.append(f"公告：{_short_condition(title, 36)}")
    if pe_ttm is not None:
        evidence.append(f"基本面：PE(TTM) {pe_ttm:.1f}")
    if fund_flow is not None:
        direction = "净流入" if fund_flow > 0 else "净流出" if fund_flow < 0 else "中性"
        evidence.append(f"资金面：{direction} {abs(fund_flow):.2f} 亿")
    return evidence


def _announcement_title(item: dict[str, object]) -> str:
    return str(item.get("title") or item.get("公告标题") or item.get("name") or "").strip()


def _first_non_empty(values: list[str]) -> str:
    return next((str(value).strip() for value in values if str(value).strip()), "")


def _dedupe_texts(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _sector_fund_context(item) -> str:
    if item.fund_status == "资金活跃":
        return "资金活跃，但仍需消息/公告/基本面解释催化"
    if item.fund_status == "资金流出":
        return "资金流出，只能说明压力，不能解释根因"
    return "资金配合一般，需继续补新闻、公告和基本面"


def _render_professional_market_diagnosis(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    diagnosis = _professional_market_diagnosis(market, sectors, candidate_universe)
    rows = "".join(
        "<tr>"
        f"<td>{escape(item['dimension'])}</td>"
        f"<td><strong>{escape(item['judgement'])}</strong></td>"
        f"<td>{escape(item['evidence'])}</td>"
        "</tr>"
        for item in diagnosis["dimensions"]
    )
    return f"""
      <div class="panel market-analysis-panel">
        <div class="editor-toolbar">
          <div><h3>专业大盘研判</h3></div>
          <span class="portfolio-chip">研判等级 {escape(diagnosis["grade"])}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>研判等级</span><strong>{escape(diagnosis["grade"])}</strong><p class="kpi-foot">{escape(diagnosis["grade_reason"])}</p></div>
          <div class="summary-card"><span>市场状态</span><strong>{escape(diagnosis["state"])}</strong><p class="kpi-foot">{escape(diagnosis["state_reason"])}</p></div>
          <div class="summary-card"><span>主线</span><strong>{escape(diagnosis["mainline"])}</strong><p class="kpi-foot">{escape(diagnosis["mainline_reason"])}</p></div>
        </div>
        <table class="data-table compact-sector-table" style="margin-top:12px">
          <thead><tr><th>维度</th><th>判断</th><th>依据</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <p class="section-subtitle" style="margin-top:12px"><strong>结论：</strong>{escape(diagnosis["conclusion"])}</p>
      </div>"""


def _professional_market_diagnosis(
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    candidate_universe: list[CandidateStockRawData],
) -> dict[str, object]:
    pct_values = _market_distribution_pct_values(
        candidate_universe,
        CandidatePoolReport("", [], [], "", True),
    )
    over_six = sum(1 for value in pct_values if value > 6)
    under_six = sum(1 for value in pct_values if value < -6)
    over_three = sum(1 for value in pct_values if value > 3)
    under_three = sum(1 for value in pct_values if value < -3)
    wide_rows = _market_wide_move_rows(candidate_universe, CandidatePoolReport("", [], [], "", True))
    wide_up = [item for item in wide_rows if item.pct_change > 6]
    wide_down = [item for item in wide_rows if item.pct_change < -6]
    theme_stats = _wide_move_theme_stats(wide_up, wide_down)
    mainline_theme = _market_mainline_theme(theme_stats, sectors)
    market_env = _market_environment_dimension(market)
    profit = _profit_effect_dimension(market, over_six, over_three, theme_stats)
    loss = _loss_effect_dimension(market, under_six, under_three)
    mainline = _mainline_quality_dimension(mainline_theme, theme_stats, sectors)
    funds = _fund_continuity_dimension(sectors, wide_up, wide_down)
    dimensions = [
        {"dimension": "市场环境", **market_env},
        {"dimension": "赚钱效应", **profit},
        {"dimension": "亏钱效应", **loss},
        {"dimension": "主线质量", **mainline},
        {"dimension": "资金持续性", **funds},
    ]
    score = sum(int(item["score"]) for item in dimensions)
    grade, grade_reason = _market_diagnosis_grade(score, loss["score"])
    state = _market_state_from_grade(grade)
    conclusion = _market_diagnosis_conclusion(
        grade=grade,
        mainline=mainline_theme,
        profit=profit["judgement"],
        loss=loss["judgement"],
    )
    return {
        "grade": grade,
        "grade_reason": grade_reason,
        "state": state,
        "state_reason": market_env["evidence"],
        "mainline": mainline_theme,
        "mainline_reason": mainline["evidence"],
        "dimensions": dimensions,
        "conclusion": conclusion,
    }


def _market_environment_dimension(market: MarketSnapshot) -> dict[str, object]:
    score = 0
    if market.heat_score >= 70:
        score += 18
    elif market.heat_score >= 50:
        score += 12
    elif market.heat_score >= 35:
        score += 7
    else:
        score += 3
    if market.breadth_ratio >= 1.5:
        score += 7
    elif market.breadth_ratio >= 1.0:
        score += 5
    elif market.breadth_ratio >= 0.75:
        score += 3
    if market.limit_up_count >= 80:
        score += 6
    elif market.limit_up_count >= 40:
        score += 4
    elif market.limit_up_count >= 15:
        score += 2
    if market.limit_down_count <= 10:
        score += 3
    elif market.limit_down_count >= 30:
        score -= 5
    judgement = "偏强" if score >= 22 else "中性" if score >= 15 else "偏弱"
    evidence = (
        f"热度 {market.heat_score}/100，涨跌家数比 {market.breadth_ratio:.2f}，"
        f"上涨/下跌/平盘 {market.advancing_count}/{market.declining_count}/{market.unchanged_count}，"
        f"涨停/跌停 {market.limit_up_count}/{market.limit_down_count}"
    )
    return {"score": min(score, 25), "judgement": judgement, "evidence": evidence}


def _profit_effect_dimension(
    market: MarketSnapshot,
    over_six: int,
    over_three: int,
    theme_stats: list[tuple[str, dict[str, int]]],
) -> dict[str, object]:
    resonance_count = sum(1 for _theme, counts in theme_stats if counts["up"] >= 2)
    score = 0
    if market.limit_up_count >= 80:
        score += 8
    elif market.limit_up_count >= 40:
        score += 6
    elif market.limit_up_count >= 15:
        score += 3
    if over_six >= 20:
        score += 7
    elif over_six >= 8:
        score += 5
    elif over_six >= 3:
        score += 3
    if over_three >= 80:
        score += 5
    elif over_three >= 30:
        score += 3
    if resonance_count:
        score += min(5, resonance_count * 2)
    judgement = "强" if score >= 18 else "结构性" if score >= 11 else "弱"
    evidence = (
        f"涨停 {market.limit_up_count}，>6% {over_six}，>3% {over_three}，"
        f"共振板块 {resonance_count} 个"
    )
    return {"score": min(score, 25), "judgement": judgement, "evidence": evidence}


def _loss_effect_dimension(
    market: MarketSnapshot,
    under_six: int,
    under_three: int,
) -> dict[str, object]:
    risk_score = 0
    if market.limit_down_count >= 40:
        risk_score += 12
    elif market.limit_down_count >= 15:
        risk_score += 8
    elif market.limit_down_count >= 5:
        risk_score += 4
    if under_six >= 20:
        risk_score += 8
    elif under_six >= 8:
        risk_score += 5
    elif under_six >= 3:
        risk_score += 3
    if under_three >= 80:
        risk_score += 5
    elif under_three >= 30:
        risk_score += 3
    score = max(0, 20 - risk_score)
    judgement = "风险扩散" if score <= 7 else "局部分歧" if score <= 14 else "风险可控"
    evidence = f"跌停 {market.limit_down_count}，<-6% {under_six}，<-3% {under_three}"
    return {"score": score, "judgement": judgement, "evidence": evidence}


def _mainline_quality_dimension(
    mainline: str,
    theme_stats: list[tuple[str, dict[str, int]]],
    sectors: SectorAnalysisReport,
) -> dict[str, object]:
    leading = next((item for item in sectors.sectors if item.name == mainline), None)
    counts = next((counts for theme, counts in theme_stats if theme == mainline), {"up": 0, "down": 0})
    score = 0
    if mainline != "暂无明确主线":
        score += 6
    if counts["up"] >= 4:
        score += 8
    elif counts["up"] >= 2:
        score += 5
    elif counts["up"] == 1:
        score += 2
    if leading is not None:
        if leading.advancing_ratio >= 0.65:
            score += 5
        elif leading.advancing_ratio >= 0.5:
            score += 3
        if leading.limit_up_count >= 3:
            score += 4
        elif leading.limit_up_count > 0:
            score += 2
        if leading.amount_change > 0:
            score += 2
    judgement = "主线清晰" if score >= 18 else "有主线雏形" if score >= 10 else "轮动分散"
    if leading is None:
        evidence = f"{mainline}；>6%样本 {counts['up']}，<-6%样本 {counts['down']}"
    elif counts["up"] == 0 and counts["down"] == 0:
        evidence = (
            f"{mainline}；板块热度 {leading.heat_score}/100，"
            f"扩散 {leading.advancing_ratio:.0%}，涨停 {leading.limit_up_count}，"
            f"成交变化 {leading.amount_change:.1f}"
        )
    else:
        evidence = (
            f"{mainline}；>6%样本 {counts['up']}，<-6%样本 {counts['down']}，"
            f"板块扩散 {leading.advancing_ratio:.0%}，涨停 {leading.limit_up_count}"
        )
    return {"score": min(score, 25), "judgement": judgement, "evidence": evidence}


def _fund_continuity_dimension(
    sectors: SectorAnalysisReport,
    wide_up: list[LimitBoardRow],
    wide_down: list[LimitBoardRow],
) -> dict[str, object]:
    leading_sectors = [item for item in sectors.sectors[:5] if item.amount_change > 0]
    inflow_rows = sum(1 for item in wide_up if item.fund_flow is not None and item.fund_flow > 0)
    outflow_rows = sum(1 for item in wide_down if item.fund_flow is not None and item.fund_flow < 0)
    score = 0
    score += min(8, len(leading_sectors) * 2)
    if inflow_rows >= 10:
        score += 7
    elif inflow_rows >= 4:
        score += 5
    elif inflow_rows > 0:
        score += 2
    if outflow_rows >= 10:
        score -= 5
    elif outflow_rows >= 4:
        score -= 3
    judgement = "资金支持" if score >= 11 else "资金配合一般" if score >= 5 else "持续性不足"
    evidence = (
        f"强势板块成交改善 {len(leading_sectors)} 个，"
        f">6%资金流入样本 {inflow_rows}，<-6%资金流出样本 {outflow_rows}"
    )
    return {"score": max(0, min(score, 20)), "judgement": judgement, "evidence": evidence}


def _market_mainline_theme(
    theme_stats: list[tuple[str, dict[str, int]]],
    sectors: SectorAnalysisReport,
) -> str:
    candidates = [item for item in theme_stats if _is_known_theme(item[0]) and item[1]["up"] > 0]
    if candidates:
        return max(candidates, key=lambda item: (item[1]["up"] - item[1]["down"], item[1]["up"]))[0]
    known_sectors = [item for item in sectors.sectors if _is_known_theme(item.name)]
    if not known_sectors:
        return "暂无明确主线"
    leader = max(known_sectors, key=lambda item: (item.heat_score, item.advancing_ratio, item.pct_chg))
    return leader.name if leader.heat_score >= 55 else "暂无明确主线"


def _market_diagnosis_grade(score: int, loss_score: object) -> tuple[str, str]:
    numeric_loss = int(loss_score)
    if numeric_loss <= 7:
        return "D 防守", f"总分 {score}，但亏钱效应已扩散"
    if score >= 82:
        return "A 主线强势", f"总分 {score}，环境、赚钱效应和主线质量同时较强"
    if score >= 65:
        return "B 结构性机会", f"总分 {score}，可围绕主线做筛选"
    if score >= 48:
        return "C 震荡轮动", f"总分 {score}，机会分散，重视持续性确认"
    return "D 防守", f"总分 {score}，赚钱效应或主线质量不足"


def _market_state_from_grade(grade: str) -> str:
    if grade.startswith("A"):
        return "主线强势"
    if grade.startswith("B"):
        return "结构性机会"
    if grade.startswith("C"):
        return "震荡轮动"
    return "防守观察"


def _market_diagnosis_conclusion(
    *,
    grade: str,
    mainline: str,
    profit: object,
    loss: object,
) -> str:
    if grade.startswith("A"):
        return f"{mainline}是当前主要观察方向，赚钱效应强，优先看板块前排和持续放量个股。"
    if grade.startswith("B"):
        return f"当前不是全面行情，是结构性机会；{mainline}优先级最高，同时观察{loss}是否扩大。"
    if grade.startswith("C"):
        return f"市场以轮动为主，{mainline}需要次日确认；{profit}不足时不追后排。"
    return f"市场偏防守，{loss}优先级高于机会挖掘；只保留主线前排观察。"


def _render_market_barometer_strip(
    market: MarketSnapshot,
    action: str,
    reason: str,
) -> str:
    target_cash = _market_target_cash(market)
    market_status = _market_display_status(market, action)
    return f"""
      <div class="market-barometer-strip">
        <div class="market-barometer-title">
          <span>市场摘要</span>
          <strong>市场总闸门：{escape(action)}</strong>
          <p>{escape(reason)}</p>
        </div>
        <div class="market-barometer-rail" aria-label="防守到进攻压力带">
          <i class="defense">防守</i><i class="balance">震荡</i><i class="attack">进攻</i>
        </div>
        <div class="market-barometer-facts">
          <span>市场状态：{escape(market_status)}</span>
          <span>风险暴露：目标现金 {escape(target_cash)}，数据降级时自动只观察。</span>
          <span>主线：见板块方向，不用交易板兜底。</span>
                    <span>交易日：{escape(market.trade_date)}</span>
          <span>数据源：顶部全局状态条 / Provider</span>
          <span>涨停/跌停：{market.limit_up_count} / {market.limit_down_count}</span>
          <span>市场热度：{market.heat_score}/100</span>
        </div>
      </div>"""


def _render_market_sentiment_panel(
    news: NewsSentimentReport | None,
    *,
    candidate_universe: list[CandidateStockRawData] | None = None,
) -> str:
    candidate_universe = candidate_universe or []
    event_rows = _market_event_rows(
        news.items if news else [], candidate_universe=candidate_universe
    )
    if not event_rows:
        return ""
    return f"""
      <div class="panel market-panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>异动事件</h3></div><span class="portfolio-chip">{len(event_rows)} 条映射</span></div>
        {_render_market_event_summary_list(event_rows)}
      </div>"""


def _market_event_rows(
    items: list[NewsItem],
    *,
    candidate_universe: list[CandidateStockRawData] | None = None,
) -> list[dict[str, str]]:
    candidate_universe = candidate_universe or []
    mapped = [
        row
        for item in items
        if (row := _map_market_event_to_theme_or_stock(item, candidate_universe)) is not None
    ]
    if not mapped:
        mapped = [
            row
            for item in _candidate_price_mover_events(candidate_universe)
            if (row := _map_market_event_to_theme_or_stock(item, candidate_universe)) is not None
        ]
    return mapped[:20]


def _map_market_event_to_theme_or_stock(
    item: NewsItem,
    candidate_universe: list[CandidateStockRawData],
) -> dict[str, str] | None:
    text = f"{item.title} {item.summary}".strip()
    if not text:
        return None
    matched_stocks = _event_matched_candidate_stocks(text, candidate_universe)
    extracted_stock = _extract_stock_name_from_event_title(item.title)
    theme = _event_theme_from_candidates(matched_stocks) or _infer_event_theme(text)
    if not matched_stocks and not extracted_stock and _is_fund_flow_noise(text):
        return None
    if not matched_stocks and not extracted_stock and _is_macro_policy_noise(text):
        return None
    if not theme and not matched_stocks and not extracted_stock:
        return None
    stock_text = _event_stock_text(matched_stocks, extracted_stock, theme, candidate_universe)
    if not stock_text and not theme:
        return None
    reason = _event_reason_text(item, theme, stock_text)
    return {
        "time": item.date or "待确认",
        "theme": theme or "个股异动",
        "stocks": stock_text or "主题级事件",
        "reason": reason,
    }


def _event_matched_candidate_stocks(
    text: str,
    candidate_universe: list[CandidateStockRawData],
) -> list[CandidateStockRawData]:
    matched: list[CandidateStockRawData] = []
    for item in candidate_universe:
        if item.name and item.name in text:
            matched.append(item)
        elif item.code and item.code in text:
            matched.append(item)
    return matched[:5]


def _event_theme_from_candidates(stocks: list[CandidateStockRawData]) -> str:
    for stock in stocks:
        if stock.sector:
            return localize_sector_name(stock.sector)
    return ""


def _extract_stock_name_from_event_title(title: str) -> str:
    cleaned = title.strip().strip("【】[]")
    for marker in ["异动", "涨停", "跌停", "大涨", "大跌", "拉升", "跳水"]:
        if marker in cleaned:
            candidate = cleaned.split(marker, 1)[0].strip(" ：:｜|【】[]")
            if 2 <= len(candidate) <= 8 and not _looks_like_generic_event_topic(candidate):
                return candidate
    return ""


def _looks_like_generic_event_topic(text: str) -> bool:
    generic_words = ["ETF", "LOF", "基金", "美联储", "港股", "A股", "市场", "政策", "关税"]
    return any(word in text for word in generic_words)


def _is_fund_flow_noise(text: str) -> bool:
    return any(word in text for word in ["ETF", "LOF", "基金"])


def _is_macro_policy_noise(text: str) -> bool:
    macro_words = ["美联储", "关税", "中东", "通胀", "FOMC", "央行", "国会"]
    return any(word in text for word in macro_words)


def _infer_event_theme(text: str) -> str:
    theme_keywords = [
        ("半导体", ["半导体", "芯片", "存储", "晶圆", "光刻", "中芯"]),
        ("商业航天", ["商业航天", "航天", "卫星", "火箭"]),
        ("机器人", ["机器人", "人形机器人", "减速器"]),
        ("人工智能", ["AI", "算力", "人工智能", "大模型"]),
        ("新能源", ["光伏", "风电", "锂电", "储能", "新能源"]),
        ("汽车", ["汽车", "智能驾驶", "整车", "零部件"]),
        ("钢铁", ["钢铁", "螺纹", "铁矿"]),
        ("氢能", ["氢气", "氢能", "燃料电池"]),
        ("港口航运", ["航运", "港口", "集装箱"]),
        ("地产", ["地产", "房地产", "物业"]),
        ("消费电子", ["AMOLED", "面板", "消费电子", "光电"]),
    ]
    for theme, keywords in theme_keywords:
        if any(keyword in text for keyword in keywords):
            return theme
    return ""


def _event_stock_text(
    matched_stocks: list[CandidateStockRawData],
    extracted_stock: str,
    theme: str,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    if matched_stocks:
        return "、".join(
            f"{stock.name}{_event_pct_text(stock)}" for stock in matched_stocks[:5]
        )
    if extracted_stock:
        return extracted_stock
    if theme:
        theme_rows = [
            row
            for row in _build_limit_board_rows(candidate_universe)
            if localize_sector_name(row.sector) == theme
        ]
        theme_rows = sorted(theme_rows, key=lambda row: abs(row.pct_change), reverse=True)[:5]
        if theme_rows:
            return "、".join(f"{row.name} {row.pct_change:.2f}%" for row in theme_rows)
    return ""


def _event_pct_text(stock: CandidateStockRawData) -> str:
    if len(stock.bars) < 2:
        return ""
    previous = stock.bars[-2].close
    if not previous:
        return ""
    pct = (stock.bars[-1].close - previous) / previous * 100
    return f" {pct:.2f}%"


def _event_reason_text(item: NewsItem, theme: str, stock_text: str) -> str:
    title = item.title.strip("【】[]")
    summary = item.summary.strip()
    if "价格异动" in title:
        reason = summary or "未识别明确消息/公告/基本面原因；价格异动只作为复核入口"
    elif "波动超" in title:
        reason = title.split("：", 1)[-1]
    elif "板块" in title and theme:
        reason = summary or title
    elif summary:
        reason = summary
    else:
        reason = title
    reason = reason.replace("longbridge.mcp.", "")
    if theme and theme not in reason:
        reason = f"{theme}：{reason}"
    if stock_text and stock_text not in reason:
        reason = f"{reason}；对应 {stock_text}"
    return _compact_event_reason(reason, 120)


def _compact_event_reason(text: str, limit: int = 120) -> str:
    cleaned = " ".join(str(text).split())
    return cleaned if len(cleaned) <= limit else cleaned[:limit] + "..."


def _market_event_summaries(
    items: list[NewsItem],
    *,
    candidate_universe: list[CandidateStockRawData] | None = None,
) -> list[str]:
    return [row["reason"] for row in _market_event_rows(items, candidate_universe=candidate_universe)]


def _render_market_event_summary_list(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<div class='empty-state'><strong>暂无可映射异动</strong></div>"
    cards = "".join(
        "<article class=\"market-event-card\">"
        "<div class=\"market-event-head\">"
        f"<span class=\"market-event-time\">时间：{escape(row.get('time') or '待确认')}</span>"
        f"<span class=\"market-event-theme\">对应主题：{escape(row['theme'])}</span>"
        f"<strong class=\"market-event-stocks\">对应股票：{escape(row['stocks'])}</strong>"
        "</div>"
        f"<p class=\"market-event-reason\"><strong>事件原因：</strong>{escape(row['reason'])}</p>"
        "</article>"
        for row in rows
    )
    return f'<div class="market-event-card-list">{cards}</div>'


def _candidate_price_mover_events(
    candidate_universe: list[CandidateStockRawData],
) -> list[NewsItem]:
    rows = sorted(
        _build_limit_board_rows(candidate_universe),
        key=lambda item: (abs(item.pct_change), item.amount),
        reverse=True,
    )[:5]
    return [
        NewsItem(
            date=row.latest_date,
            source="TDX候选池.价格异动",
            title=f"{row.name}价格异动：{row.pct_change:.2f}%",
            summary=_candidate_price_mover_reason(row),
            sentiment="neutral",
        )
        for row in rows
    ]


def _candidate_price_mover_reason(row: LimitBoardRow) -> str:
    evidence = _candidate_causal_evidence(row)
    if evidence:
        return "；".join(evidence[:4])
    return "未识别明确消息/公告/基本面原因；价格异动只作为复核入口"


def _sentiment_label(value: str) -> str:
    return {"positive": "正面", "negative": "负面", "neutral": "中性"}.get(value, value)


def _market_target_cash(market: MarketSnapshot) -> str:
    if market.heat_score <= 40 or market.limit_down_count >= 20:
        return "50%-70%"
    if market.heat_score >= 70 and market.breadth_ratio >= 1.2:
        return "20%-35%"
    return "30%-50%"


def _market_display_status(market: MarketSnapshot, action: str) -> str:
    if market.heat_score <= 40 or market.limit_down_count >= 20:
        return "防守 / 暂停"
    if action in {"可以进攻", "积极观察"}:
        return "进攻"
    return "震荡"


def _market_risk_tone(market: MarketSnapshot) -> str:
    if market.heat_score >= 70 and market.breadth_ratio >= 1.3 and market.limit_down_count < 15:
        return "hot"
    if market.heat_score <= 40 or market.breadth_ratio < 0.8 or market.limit_down_count >= 20:
        return "cold"
    return "balanced"


def _render_market_index_spine(market: MarketSnapshot) -> str:
    if not market.indices:
        return "<p class='module-desc'>当前没有指数数据，先确认数据源或切回样例模式查看页面。</p>"
    max_pct = max(abs(item.pct_chg) for item in market.indices[:6]) or 1
    rows = []
    for index in market.indices[:6]:
        tone = "up" if index.pct_chg >= 0 else "down"
        width = min(100, max(6, abs(index.pct_chg) / max_pct * 100))
        rows.append(
            f"""
            <div class="market-index-row {tone}">
              <div class="market-index-name"><strong>{escape(index.name)}</strong><span>{escape(index.code)}</span></div>
              <div class="market-index-track"><i style="width:{width:.0f}%"></i></div>
              <div class="market-index-value"><strong>{index.pct_chg:.2f}%</strong><span>{index.amount:.1f} 亿</span></div>
            </div>"""
        )
    return "".join(rows)


def _render_market_breadth_lamps(market: MarketSnapshot, portfolio: PortfolioAnalysisReport) -> str:
    lamps = [
        ("上涨/下跌/平盘", f"{_format_market_count(market, 'advancing')} / {_format_market_count(market, 'declining')} / {_format_market_count(market, 'unchanged')}", _breadth_signal(market.breadth_ratio), _market_lamp_tone(market.breadth_ratio, high=1.3, low=0.8)),
        ("涨停/跌停", f"{market.limit_up_count} / {market.limit_down_count}", f"{_limit_up_state_label(market)}；{_limit_down_state_label(market)}", "cold" if market.limit_down_count >= 20 else "hot" if market.limit_up_count >= 60 else "balanced"),
        ("市场热度", f"{market.heat_score}/100", _market_heat_copy(market), _market_risk_tone(market)),
        ("持仓健康度", f"{portfolio.health_score}/100", "大盘闸门要叠加账户承受度，不能只看指数红绿。", "cold" if portfolio.health_score < 45 else "hot" if portfolio.health_score >= 70 else "balanced"),
    ]
    return "".join(
        f"""
        <div class="market-lamp {tone}">
          <span>{escape(label)}</span>
          <strong>{escape(value)}</strong>
          <p>{escape(note)}</p>
        </div>"""
        for label, value, note, tone in lamps
    )


def _market_lamp_tone(value: float, *, high: float, low: float) -> str:
    if value >= high:
        return "hot"
    if value < low:
        return "cold"
    return "balanced"


def _market_heat_copy(market: MarketSnapshot) -> str:
    if market.heat_score >= 70:
        return "热度支持进攻，但仍要等板块延续和成交确认。"
    if market.heat_score <= 40:
        return "热度偏低，先缩小试错半径，避免逆势扩大风险。"
    return "热度中性，适合结构行情，不适合无差别追高。"


def _render_market_risk_cards(market: MarketSnapshot) -> str:
    items = market.risks[:3] if market.risks else ["未触发硬风险，但仍需控制仓位与回撤"]
    return "".join(
        f"""
        <div class="market-risk-card">
          <span>RISK {index:02d}</span>
          <strong>{escape(item)}</strong>
        </div>"""
        for index, item in enumerate(items, start=1)
    )


def _render_market_sector_heatmap(sectors: SectorAnalysisReport) -> str:
    if not sectors.sectors:
        return "<div class='empty-state'><strong>暂无可靠板块数据</strong><p>先确认 TDX / AKShare / 本地快照是否返回行业或概念，不用交易板块伪装主题。</p></div>"
    top_items = sorted(sectors.sectors, key=lambda item: item.heat_score, reverse=True)[:6]
    max_heat = max(item.heat_score for item in top_items) or 1
    cards = []
    for item in top_items:
        width = min(100, max(10, item.heat_score / max_heat * 100))
        pct_label = _sector_move_text(item)
        cards.append(
            f"""
            <button class="market-sector-tile" type="button" data-jump="opportunity">
              <span>{escape(item.name)}</span>
              <strong>{escape(pct_label)}</strong>
              <i><b style="width:{width:.0f}%"></b></i>
              <em>{escape(item.rotation_status)} · 热度 {item.heat_score}/100</em>
            </button>"""
        )
    return "".join(cards)


def _render_market_sector_top5_panel(
    sectors: SectorAnalysisReport,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    if not sectors.sectors:
        return ""
    rows = "".join(
        _render_market_sector_top5_row(item, candidate_universe)
        for item in sectors.sectors[:6]
    )
    return f"""
          <div class="sector-top5-panel">
            <div class="sector-top5-head"><strong>板块Top5</strong><span>每个方向只给代表股票和分析结果，不直接当买点。</span></div>
            <table class="data-table compact-sector-table">
              <thead><tr><th>板块</th><th>代表股票</th><th>分析结果</th></tr></thead>
              <tbody>{rows}</tbody>
            </table>
          </div>"""


def _render_market_sector_top5_row(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    stocks = _strong_stocks_for_theme(candidate_universe, item.name)
    if stocks:
        stock_text = "、".join(
            f"{stock.name} {stock.pct_change:.2f}%" for stock in stocks[:5]
        )
    else:
        stock_text = "候选池暂无同主题样本"
    analysis = (
        f"{_sector_state_label(item)}；{_sector_strength_reason(item)}；"
        f"{_sector_strategy(item)}"
    )
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>热度 {item.heat_score}/100 · {escape(item.rotation_status)}</span></td>"
        f"<td>{escape(stock_text)}</td>"
        f"<td>{escape(analysis)}</td></tr>"
    )


def _render_market_watch_stack(market: MarketSnapshot) -> str:
    items = market.tomorrow_watch[:4] if market.tomorrow_watch else ["等待下一交易日确认"]
    return "".join(
        f"""
        <div class="market-watch-item">
          <span>{index}</span>
          <p>{escape(item)}</p>
        </div>"""
        for index, item in enumerate(items, start=1)
    )

def _render_research_data_flow_panel(module: str, sources: str, output: str) -> str:
    del module, sources, output
    return ""


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
        <table class="data-table"><thead><tr><th>主题</th><th>强度证据</th><th>代表个股</th><th>风险点</th><th>操作策略</th></tr></thead><tbody>{rows}</tbody></table>
      </div>
    </section>"""


def _render_sector_theme_row(
    item,
    candidate_universe: list[CandidateStockRawData],
) -> str:
    strong_stock_text = _sector_representative_stocks(item, candidate_universe)
    conclusion = _sector_state_label(item)
    strength = _sector_strength_reason(item)
    strategy = _sector_strategy(item)
    risk = _sector_risk_text(item)
    return (
        f"<tr><td class='name-cell'><strong>{escape(item.name)}</strong>"
        f"<span>{escape(item.continuity)} · {escape(item.rotation_status)}</span></td>"
        f"<td>{escape(conclusion)}<span>{escape(strength)}</span></td>"
        f"<td>{escape(strong_stock_text)}</td>"
        f"<td>{escape(risk)}</td>"
        f"<td>{escape(strategy)}</td></tr>"
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
    return sorted(rows, key=lambda item: item.pct_change, reverse=True)[:5]


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
    sectors: SectorAnalysisReport,
    holdings_path: str,
    stock_code: str,
    provider_name: str,
    notice: PortfolioNotice | None,
    edit_code: str,
    refresh_time: str,
) -> str:
    advice = build_portfolio_advice(
        portfolio,
        market=market,
        holdings_path=holdings_path,
        transactions_path="data/portfolio/transactions.csv",
    )
    advice_by_code = {item.code: item for item in advice.position_advices}
    editing_position = next(
        (position for position in portfolio.positions if position.holding.code == edit_code),
        None,
    )
    readonly = _is_public_readonly()
    editor = ""
    if not readonly:
        editor = _render_portfolio_editor_panel(
            portfolio=portfolio,
            advice_by_code=advice_by_code,
            stock_code=stock_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
            editing_position=editing_position,
        )
    analysis_list = _render_portfolio_unified_analysis_panel(
        portfolio,
        advice_by_code,
        market,
        sectors,
        provider_name=provider_name,
        holdings_path=holdings_path,
        stock_code=stock_code,
        readonly=readonly,
    )
    notice_html = _render_portfolio_notice(notice)
    return f"""
    <section class="module" id="module-portfolio">
      <div class="module-header"><div><h2 class="module-title">我的持仓</h2><p class="module-desc">只维护和分析真实持仓；新增、删除、成本价和股数修改后自动刷新分析。</p></div><div class="module-header-meta"><span class="risk-pill mid">健康度 {portfolio.health_score}/100</span><span class="status-pill">持仓 {len(portfolio.positions)} 只</span>{_render_module_refresh_tools(refresh_time=refresh_time, stock_code=stock_code, provider_name=provider_name, holdings_path=holdings_path, workspace="portfolio")}</div></div>
      {notice_html}
      {editor}
      {analysis_list}
    </section>"""


def _render_portfolio_editor_panel(
    *,
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
    stock_code: str,
    provider_name: str,
    holdings_path: str,
    editing_position: PositionAnalysis | None,
) -> str:
    advice = advice_by_code.get(editing_position.holding.code) if editing_position else None
    open_attr = " open" if editing_position else ""
    title = "编辑持仓" if editing_position else "新增持仓"
    form = _render_add_holding_form(
        stock_code,
        provider_name,
        holdings_path,
        editing_position,
        advice,
    )
    clear_link = _render_clear_edit_link(
        stock_code,
        provider_name,
        holdings_path,
        editing_position.holding.code if editing_position else "",
    )
    return f"""
      <details class="panel portfolio-editor" id="portfolio-form"{open_attr} style="margin-top:16px">
        <summary class="portfolio-inline-button primary">{title}</summary>
        <div class="portfolio-list-meta" style="margin-top:12px">
          <span class="portfolio-chip">可改股数</span>
          <span class="portfolio-chip">可改成本价</span>
          <span class="portfolio-chip">当前 {len(portfolio.positions)} 只</span>
          {clear_link}
        </div>
        {form}
      </details>"""


def _render_portfolio_unified_analysis_panel(
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    *,
    provider_name: str,
    holdings_path: str,
    stock_code: str,
    readonly: bool = False,
) -> str:
    if not portfolio.positions:
        rows = """
        <tr><td colspan="3"><div class="empty-state"><strong>还没有持仓</strong><p>先新增股票、股数和成本价，再生成多维持仓分析。</p></div></td></tr>
        """
    else:
        rows = "".join(
            _render_portfolio_unified_analysis_row(
                position,
                advice_by_code.get(position.holding.code),
                market,
                sectors,
                provider_name=provider_name,
                holdings_path=holdings_path,
                stock_code=stock_code,
                readonly=readonly,
            )
            for position in sorted(
                portfolio.positions,
                key=lambda item: (item.risk_level != "高", item.pnl_ratio >= 0, -item.weight),
            )
        )
    return f"""
      <div class="panel portfolio-stock-analysis" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>持仓分析</h3><p class="section-subtitle">一行看完技术、资金、基本面、消息、板块、仓位成本和结论。</p></div>
          <span class="portfolio-chip">总市值 {portfolio.total_market_value:.2f} · 累计盈亏 {portfolio.total_pnl_ratio:.2f}%</span>
        </div>
        <table class="data-table portfolio-analysis-table">
          <thead><tr><th>股票</th><th>分析</th><th>操作</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _render_portfolio_unified_analysis_row(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    *,
    provider_name: str,
    holdings_path: str,
    stock_code: str,
    readonly: bool,
) -> str:
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
        "<tr>"
        f"<td class='name-cell'><strong>{escape(position.holding.name)}</strong>"
        f"<span>{escape(position.holding.code)} · {escape(localize_sector_name(position.holding.sector or '未识别主题'))}</span>"
        f"<span>{_format_form_number(position.holding.shares)} 股 · 成本 {position.holding.cost_price:.2f}</span></td>"
        f"<td>{_render_portfolio_multidimensional_analysis(position, advice, market, sectors)}</td>"
        f"<td class='action-cell'>{actions}</td>"
        "</tr>"
    )


def _render_portfolio_multidimensional_analysis(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
) -> str:
    sector_name = localize_sector_name(position.holding.sector or "未识别主题")
    sector_state = _holding_sector_state(position.holding.sector, sectors)
    action = advice.action if advice else "观察"
    reason = _clean_position_reason(advice.reason, action) if advice else "等待更多数据确认"
    next_check = advice.next_check if advice else "复核趋势、公告和资金变化。"
    lines = [
        ("技术面原因", _portfolio_trend_dimension(position)),
        ("资金面原因", _portfolio_fund_dimension(position, market)),
        ("基本面原因", _portfolio_fundamental_dimension(position)),
        ("消息面原因", _portfolio_news_dimension(position, market)),
        ("板块情绪原因", _portfolio_sector_dimension(sector_name, sector_state, position)),
        ("仓位原因", _portfolio_holding_dimension(position, advice)),
        ("结论", f"{action}：{reason}；后续看 {next_check}"),
    ]
    return (
        "<div class='portfolio-analysis-stack'>"
        + "".join(
            f"<p class='portfolio-analysis-line'><strong>{escape(label)}</strong>{escape(text)}</p>"
            for label, text in lines
        )
        + "</div>"
    )


def _clean_position_reason(reason: str, action: str) -> str:
    cleaned = reason.strip().rstrip("。")
    prefix = f"{action}原因："
    if cleaned.startswith(prefix):
        return cleaned.removeprefix(prefix)
    return cleaned


def _render_portfolio_stock_analysis_panel(
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    if not portfolio.positions:
        rows = """
        <tr><td colspan="9"><div class="empty-state"><strong>还没有持仓</strong><p>录入股票后展示趋势、资金、基本面、消息、板块和成本维度。</p></div></td></tr>
        """
    else:
        rows = "".join(
            _render_portfolio_stock_analysis_row(
                position,
                advice_by_code.get(position.holding.code),
                market,
                sectors,
                provider_name=provider_name,
                holdings_path=holdings_path,
            )
            for position in sorted(
                portfolio.positions,
                key=lambda item: (item.risk_level != "高", item.pnl_ratio >= 0, -item.weight),
            )
        )
    return f"""
      <div class="panel portfolio-stock-analysis" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>持仓股票分析</h3><p class="section-subtitle">分析方法与个股分析保持一致，只覆盖你当前持有的股票。</p></div>
          <span class="portfolio-chip">市场情绪 {escape(market.regime)} · 热度 {market.heat_score}/100</span>
        </div>
        <table class="data-table portfolio-analysis-table">
          <thead><tr><th>股票</th><th>趋势/量价</th><th>资金/成交</th><th>基本面/估值</th><th>消息/公告</th><th>板块/主题</th><th>持仓/成本</th><th>结论</th><th>操作</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _render_portfolio_stock_analysis_row(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
    market: MarketSnapshot,
    sectors: SectorAnalysisReport,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    sector_name = localize_sector_name(position.holding.sector or "未识别主题")
    sector_state = _holding_sector_state(position.holding.sector, sectors)
    action = advice.action if advice else "观察"
    reason = advice.reason if advice else "先按成本位置和趋势复核，不做临时加仓。"
    trend_text = _portfolio_trend_dimension(position)
    fund_text = _portfolio_fund_dimension(position, market)
    fundamental_text = _portfolio_fundamental_dimension(position)
    news_text = _portfolio_news_dimension(position, market)
    holding_state = _portfolio_holding_dimension(position, advice)
    actions = _render_open_stock_form(position.holding.code, provider_name, holdings_path)
    return (
        "<tr>"
        f"<td class='name-cell'><strong>{escape(position.holding.name)}</strong><span>{escape(position.holding.code)}</span></td>"
        f"<td>{escape(trend_text)}</td>"
        f"<td>{escape(fund_text)}</td>"
        f"<td>{escape(fundamental_text)}</td>"
        f"<td>{escape(news_text)}</td>"
        f"<td><strong>{escape(sector_name)}</strong><span>{escape(sector_state)}</span></td>"
        f"<td>{escape(holding_state)}</td>"
        f"<td>{escape(_short_condition(f'{action}：{reason}', 88))}</td>"
        f"<td class='action-cell'>{actions}</td>"
        "</tr>"
    )


def _portfolio_trend_dimension(position: PositionAnalysis) -> str:
    if position.trend == "上升趋势" and position.risk_level == "低":
        return f"趋势向上且风险低，日内 {position.daily_pnl_ratio:.2f}% 用于确认承接"
    if position.trend == "下降趋势":
        return f"趋势向下，日内 {position.daily_pnl_ratio:.2f}% 不能单独改变防守判断"
    return f"{position.trend}，风险 {position.risk_level}，需要用量价延续确认"


def _portfolio_fund_dimension(position: PositionAnalysis, market: MarketSnapshot) -> str:
    if position.latest_price <= 0:
        return "缺最新报价，成交与资金不参与判断"
    total_amount = sum(index.amount for index in market.indices)
    if total_amount >= 1_000_000_000_000:
        market_liquidity = "市场成交充足"
    elif total_amount > 0:
        market_liquidity = "市场成交一般"
    else:
        market_liquidity = "成交额待补"
    if total_amount > 0:
        return f"{market_liquidity}，持仓动作仍要等个股资金明细确认"
    return f"{market_liquidity}，当前不能把资金面作为动作理由"


def _portfolio_fundamental_dimension(position: PositionAnalysis) -> str:
    sector = localize_sector_name(position.holding.sector or "")
    if sector:
        return f"{sector} 决定估值和盈利弹性口径，财务质量在个股页复核"
    return "未标注板块，基本面口径待补"


def _portfolio_news_dimension(position: PositionAnalysis, market: MarketSnapshot) -> str:
    if market.heat_score >= 70 and position.risk_level != "高":
        return "市场情绪偏强，但公告未确认前不把消息面作为加仓理由"
    if market.heat_score < 45 or position.risk_level == "高":
        return "情绪偏弱或个股风险高，先排查公告和事件风险"
    return "情绪中性，消息公告不单独构成动作理由"


def _portfolio_sector_dimension(
    sector_name: str,
    sector_state: str,
    position: PositionAnalysis,
) -> str:
    if "市场主线" in sector_state or "热度" in sector_state:
        return f"{sector_name}有板块支撑，组合占比 {position.weight:.1%} 决定是否需要控制集中度"
    return f"{sector_name}未进入前排主线，组合占比 {position.weight:.1%}，动作主要看个股自身承接"


def _portfolio_holding_dimension(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
) -> str:
    action = advice.action if advice else "观察"
    return (
        f"{_stock_cost_position_text(position)}，仓位 {position.weight:.1%} 决定处理优先级；"
        f"成本 {position.holding.cost_price:.2f} / 现价 {position.latest_price:.2f}，当前动作为{action}"
    )


def _render_portfolio_sector_analysis_panel(
    portfolio: PortfolioAnalysisReport,
    sectors: SectorAnalysisReport,
) -> str:
    rows = _portfolio_sector_analysis_rows(portfolio, sectors)
    return f"""
      <div class="panel portfolio-sector-analysis" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>对应板块分析</h3><p class="section-subtitle">只统计持仓股票所属板块，判断板块强弱和持仓相关性。</p></div>
          <span class="portfolio-chip">板块 {len(portfolio.sector_weights)} 个</span>
        </div>
        <table class="data-table">
          <thead><tr><th>板块/主题</th><th>组合占比</th><th>持有股票</th><th>板块状态</th><th>分析</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _portfolio_sector_analysis_rows(
    portfolio: PortfolioAnalysisReport,
    sectors: SectorAnalysisReport,
) -> str:
    if not portfolio.positions:
        return """
        <tr><td colspan="5"><div class="empty-state"><strong>暂无持仓</strong><p>补充持仓后统计对应板块。</p></div></td></tr>
        """
    rows: list[str] = []
    for sector, weight in sorted(portfolio.sector_weights, key=lambda item: item[1], reverse=True):
        names = "、".join(
            position.holding.name
            for position in portfolio.positions
            if position.holding.sector == sector
        )
        state = _holding_sector_state(sector, sectors)
        analysis = _portfolio_sector_analysis_text(weight, state)
        rows.append(
            "<tr>"
            f"<td><strong>{escape(localize_sector_name(sector) or '未识别主题')}</strong></td>"
            f"<td>{weight:.1%}</td>"
            f"<td>{escape(names or '未匹配')}</td>"
            f"<td>{escape(state)}</td>"
            f"<td>{escape(analysis)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _portfolio_sector_analysis_text(weight: float, state: str) -> str:
    if weight >= 0.40:
        concentration = "集中度偏高"
    elif weight >= 0.25:
        concentration = "集中度中等"
    else:
        concentration = "集中度可控"
    if "强" in state or "热度" in state:
        return f"{concentration}；板块需结合成交延续确认"
    return f"{concentration}；板块证据不足时以个股维度为主"


def _render_portfolio_cost_analysis_panel(
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
) -> str:
    if not portfolio.positions:
        rows = """
        <tr><td colspan="6"><div class="empty-state"><strong>暂无持仓</strong><p>补充数量和成本价后生成仓位/成本分析。</p></div></td></tr>
        """
    else:
        rows = "".join(
            _portfolio_cost_analysis_row(position, advice_by_code.get(position.holding.code))
            for position in sorted(portfolio.positions, key=lambda item: item.weight, reverse=True)
        )
    return f"""
      <div class="panel portfolio-cost-analysis" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>仓位/成本分析</h3><p class="section-subtitle">基于持仓占比、成本价、现价和盈亏结构判断单票压力。</p></div>
          <span class="portfolio-chip">总市值 {portfolio.total_market_value:.2f} · 累计盈亏 {portfolio.total_pnl_ratio:.2f}%</span>
        </div>
        <table class="data-table">
          <thead><tr><th>股票</th><th>仓位</th><th>成本/现价</th><th>盈亏</th><th>仓位判断</th><th>成本结论</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _portfolio_cost_analysis_row(
    position: PositionAnalysis,
    advice: PositionAdvice | None,
) -> str:
    action = advice.action if advice else "观察"
    if position.weight >= 0.30:
        weight_view = "单票占比较高"
    elif position.weight >= 0.15:
        weight_view = "中等仓位"
    else:
        weight_view = "轻仓"
    cost_view = _stock_cost_position_text(position)
    conclusion = f"{cost_view}；{action}；{advice.reason if advice else '按趋势和成本复核'}"
    return (
        "<tr>"
        f"<td class='name-cell'><strong>{escape(position.holding.name)}</strong><span>{escape(position.holding.code)}</span></td>"
        f"<td>{position.weight:.1%}</td>"
        f"<td>{position.holding.cost_price:.2f} / {position.latest_price:.2f}</td>"
        f"<td>{position.pnl:.2f}（{position.pnl_ratio:.2f}%）</td>"
        f"<td>{escape(weight_view)}</td>"
        f"<td>{escape(_short_condition(conclusion, 88))}</td>"
        "</tr>"
    )


def _holding_sector_state(sector: str, sectors: SectorAnalysisReport) -> str:
    normalized = localize_sector_name(sector or "")
    if not normalized:
        return "主题未补充，先按个股独立分析"
    for item in sectors.sectors:
        item_name = localize_sector_name(item.name)
        if item_name == normalized or normalized in item_name or item_name in normalized:
            return f"{item.rotation_status}；热度 {item.heat_score}/100；{item.fund_status}"
    mainline = "、".join(sectors.market_mainline[:3]) if sectors.market_mainline else "主线未明确"
    return f"未进入前排主线；当前主线：{mainline}"


def _holding_market_mood(
    position: PositionAnalysis,
    market: MarketSnapshot,
    sector_state: str,
) -> str:
    if market.heat_score < 45 or market.limit_down_count >= 20:
        return "市场偏防守，亏损/弱势股不补仓"
    if "热度" in sector_state and position.trend == "上升趋势":
        return "情绪支持，但只按触发线加减仓"
    if position.risk_level == "高":
        return "个股风险优先级高于市场情绪"
    return "市场中性，按个股证据和成本位置处理"


def _render_portfolio_command_panel(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
    advice: PortfolioAdvice,
    holdings_path: str,
    readonly: bool,
) -> str:
    priority = _portfolio_priority_advice(advice)
    largest_risk = portfolio.risk_alerts[0] if portfolio.risk_alerts else _portfolio_default_risk(portfolio)
    next_check = priority.next_check if priority is not None else "先录入持仓，再生成复核条件。"
    ledger_state = "线上只读" if readonly else "可编辑账本"
    tone = _portfolio_console_tone(portfolio)
    headline = _portfolio_console_headline(portfolio, market, advice)
    portfolio_state = _portfolio_health_state(portfolio)
    return f"""
      <div class="portfolio-command-console {tone}">
        <div class="portfolio-command-hero simple-panel">
          <h3>组合摘要</h3>
          <strong>组合状态 {escape(portfolio_state)}，现金比例按“{escape(advice.target_cash)}”执行。</strong>
          <p>{escape(headline)}</p>
          <div class="portfolio-command-meta">
            <span>交易日 {escape(portfolio.trade_date)}</span>
            <strong>{escape(advice.overall_action)}</strong>
          </div>
        </div>
        <div class="portfolio-command-grid">
          {_portfolio_command_card("今日先处理", priority.name if priority else "等待持仓", next_check)}
          {_portfolio_command_card("最大风险", largest_risk, _portfolio_risk_instruction(portfolio))}
          {_portfolio_command_card("现金比例", advice.target_cash, "现金未录入时按目标现金/低风险仓位作为风险预算。")}
          {_portfolio_command_card("账本状态", ledger_state, f"{holdings_path} · 持仓 {len(portfolio.positions)} 只")}
        </div>
      </div>"""


def _portfolio_health_state(portfolio: PortfolioAnalysisReport) -> str:
    if portfolio.health_score >= 75 and not portfolio.risk_alerts:
        return "稳态"
    if portfolio.health_score < 45:
        return "风险扩大"
    if portfolio.top_position_weight >= 0.35:
        return "集中偏热"
    return "观察"


def _portfolio_priority_advice(advice: PortfolioAdvice) -> PositionAdvice | None:
    if not advice.position_advices:
        return None
    priority_order = {"降仓": 0, "锁定利润": 1, "持有观察": 2, "持有": 3}
    return min(
        advice.position_advices,
        key=lambda item: (priority_order.get(item.action, 9), -abs(item.adjust_amount)),
    )


def _portfolio_console_tone(portfolio: PortfolioAnalysisReport) -> str:
    if portfolio.health_score < 45 or portfolio.top_position_weight >= 0.45:
        return "risk"
    if portfolio.health_score >= 75 and not portfolio.risk_alerts:
        return "steady"
    return "watch"


def _portfolio_console_headline(
    portfolio: PortfolioAnalysisReport,
    market: MarketSnapshot,
    advice: PortfolioAdvice,
) -> str:
    if not portfolio.positions:
        return "当前没有录入持仓，先把账本补齐，再让系统计算风险预算和处置顺序。"
    first_action = advice.portfolio_actions[0] if advice.portfolio_actions else advice.overall_action
    return (
        f"组合健康度 {portfolio.health_score}/100，市场处于 {market.regime}；"
        f"{first_action}"
    )


def _portfolio_default_risk(portfolio: PortfolioAnalysisReport) -> str:
    if not portfolio.positions:
        return "未录入持仓，无法判断集中度和盈亏风险"
    if portfolio.top_position_weight >= 0.35:
        top = max(portfolio.positions, key=lambda item: item.weight)
        return f"第一大持仓 {top.holding.name} 占比 {top.weight:.1%}"
    if portfolio.sector_weights:
        sector, weight = portfolio.sector_weights[0]
        return f"行业暴露最高为 {localize_sector_name(sector)} {weight:.1%}"
    return "暂无突出风险，继续按价格触发线复核"


def _portfolio_risk_instruction(portfolio: PortfolioAnalysisReport) -> str:
    if portfolio.health_score < 45:
        return "先降低弱势和高风险仓位，不做摊薄。"
    if portfolio.top_position_weight >= 0.45:
        return "先降单票集中度，再看新增机会。"
    return "保持纪律执行，新增仓位必须有触发条件。"


def _portfolio_command_card(label: str, value: str, note: str) -> str:
    return f"""
        <div class="portfolio-command-card">
          <span>{escape(label)}</span>
          <strong>{escape(value)}</strong>
          <p>{escape(note)}</p>
        </div>"""


def _render_portfolio_risk_budget_panel(
    portfolio: PortfolioAnalysisReport,
    advice: PortfolioAdvice,
    holdings_path: str,
    readonly: bool,
) -> str:
    single_limit = min(100, max(4, portfolio.top_position_weight * 100))
    sector_weight = portfolio.sector_weights[0][1] if portfolio.sector_weights else 0.0
    sector_limit = min(100, max(4, sector_weight * 100))
    book_state = "公开只读：写操作禁用" if readonly else "公开只读未开启：本地账本可维护"
    return f"""
      <div class="panel portfolio-budget-panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>风险预算</h3><p class="section-subtitle">新增或减仓前，先看单股、行业和现金目标是否越过预算线。</p></div>
          <span class="portfolio-chip">持仓账本来源：{escape(holdings_path)}</span>
        </div>
        <div class="portfolio-budget-grid">
          <div class="portfolio-budget-bar">
            <span>单股集中</span><i><b style="width:{single_limit:.0f}%"></b></i>
            <strong>{portfolio.top_position_weight:.1%}</strong>
          </div>
          <div class="portfolio-budget-bar">
            <span>行业集中</span><i><b style="width:{sector_limit:.0f}%"></b></i>
            <strong>{sector_weight:.1%}</strong>
          </div>
          <div class="portfolio-budget-note">
            <span>目标现金</span><strong>{escape(advice.target_cash)}</strong>
            <p>{escape(book_state)}；所有加仓都必须先满足触发条件。</p>
          </div>
        </div>
      </div>"""


def _render_portfolio_four_lane_board(
    portfolio: PortfolioAnalysisReport,
    advice: PortfolioAdvice,
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    advice_by_code = {item.code: item for item in advice.position_advices}
    lanes = [
        ("必须处理", "降仓"),
        ("观察", "持有观察"),
        ("可继续", "持有"),
        ("待补数据", "补数据"),
    ]
    lane_html = "".join(
        _portfolio_lane(
            label,
            action,
            portfolio,
            advice_by_code,
            provider_name=provider_name,
            holdings_path=holdings_path,
        )
        for label, action in lanes
    )
    return f"""
      <div class="panel portfolio-lane-panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>处理队列</h3><p class="section-subtitle">先处理风险，再观察修复，最后才考虑可继续持有的仓位。</p></div>
          <span class="portfolio-chip">成本位置 / 下一步动作</span>
        </div>
        <div class="portfolio-lane-grid">{lane_html}</div>
      </div>"""


def _render_portfolio_execution_boundaries(advice: PortfolioAdvice) -> str:
    if not advice.position_advices:
        rows = """
        <tr><td colspan="5">暂无持仓，先补齐账本后生成操作边界。</td></tr>
        """
    else:
        rows = "".join(
            "<tr>"
            f"<td class='name-cell'><strong>{escape(item.name)}</strong><span>{escape(item.code)}</span></td>"
            f"<td>{escape(item.action)}</td>"
            f"<td>{escape(item.target_weight)}</td>"
            f"<td>{item.stop_loss:.2f}</td>"
            f"<td>{escape(_short_condition(item.next_check, 60))}</td>"
            "</tr>"
            for item in advice.position_advices[:8]
        )
    return f"""
      <div class="panel portfolio-boundary-panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>操作边界</h3><p class="section-subtitle">每只持仓都要有动作、仓位上限、失效线和禁止动作；亏损股不默认补仓。</p></div>
          <span class="portfolio-chip">禁止动作：未触发前不加仓，不摊薄问题仓</span>
        </div>
        <table class="data-table">
          <thead><tr><th>股票</th><th>动作</th><th>仓位上限</th><th>失效线</th><th>下一次复核</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _portfolio_lane(
    label: str,
    action: str,
    portfolio: PortfolioAnalysisReport,
    advice_by_code: dict[str, PositionAdvice],
    *,
    provider_name: str,
    holdings_path: str,
) -> str:
    cards = []
    if action == "补数据":
        positions = [
            item
            for item in portfolio.positions
            if item.latest_price <= 0
        ]
    else:
        positions = [
            item
            for item in portfolio.positions
            if advice_by_code.get(item.holding.code)
            and advice_by_code[item.holding.code].action == action
        ]
    for position in positions[:3]:
        advice = advice_by_code.get(position.holding.code)
        note = advice.next_check if advice else "补齐行情日期和报价后再复核。"
        stock_url = _stock_chart_url(position.holding.code, provider_name, holdings_path)
        cards.append(
            f"""
            <a class="portfolio-lane-card" href="{escape(stock_url, quote=True)}">
              <strong>{escape(position.holding.name)}</strong>
              <span>{escape(position.holding.code)} · 成本位置 {escape(_stock_cost_position_text(position))}</span>
              <p>{escape(_short_condition(note, 52))}</p>
            </a>"""
        )
    if not cards:
        cards.append(
            f"""
            <div class="portfolio-lane-card muted">
              <strong>{escape(label)}暂无</strong>
              <span>保持复核</span>
              <p>当前没有进入该车道的持仓。</p>
            </div>"""
        )
    return f"""
          <div class="portfolio-lane">
            <h4>{escape(label)}</h4>
            {''.join(cards)}
          </div>"""


def _render_portfolio_position_overview(advice: PortfolioAdvice) -> str:
    return f"""
      <div class="panel" style="margin-top:16px">
        <h3>账本状态</h3>
        <div class="summary-grid">
          <div class="summary-card"><span>记录内股票仓位</span><strong>100%</strong><p class="kpi-foot">现金未录入，仅代表已录入股票篮子</p></div>
          <div class="summary-card"><span>目标现金/低风险</span><strong>{escape(advice.target_cash)}</strong><p class="kpi-foot">按市场和组合风险自动给出</p></div>
          <div class="summary-card"><span>整体动作</span><strong>{escape(advice.overall_action)}</strong><p class="kpi-foot">先控风险，再看扩仓</p></div>
        </div>
      </div>"""


def _render_portfolio_exposure_map(portfolio: PortfolioAnalysisReport) -> str:
    if not portfolio.sector_weights:
        return """
      <div class="panel portfolio-exposure-panel" style="margin-top:16px">
        <h3>行业暴露</h3>
        <div class="empty-state"><strong>暂无行业暴露</strong><p>持仓行业为空时，只能先按单股集中度做风险预算。</p></div>
      </div>"""
    bars = "".join(
        _portfolio_exposure_bar(sector, weight)
        for sector, weight in sorted(portfolio.sector_weights, key=lambda item: item[1], reverse=True)[:5]
    )
    top_positions = "".join(_portfolio_weight_tile(position) for position in sorted(portfolio.positions, key=lambda item: item.weight, reverse=True)[:4])
    return f"""
      <div class="panel portfolio-exposure-panel" style="margin-top:16px">
        <div class="editor-toolbar"><div><h3>行业暴露</h3><p class="section-subtitle">先看组合是不是押在同一条线，再决定能否新增同主题股票。</p></div><span class="portfolio-chip">行业统计</span></div>
        <div class="portfolio-exposure-layout">
          <div class="portfolio-exposure-bars">{bars}</div>
          <div class="portfolio-weight-tiles">{top_positions}</div>
        </div>
      </div>"""


def _portfolio_exposure_bar(sector: str, weight: float) -> str:
    tone = "hot" if weight >= 0.45 else "watch" if weight >= 0.30 else "steady"
    width = min(100, max(4, weight * 100))
    note = "新仓避免继续堆同方向" if weight >= 0.45 else "保持复核" if weight >= 0.30 else "暴露可控"
    return f"""
          <div class="portfolio-exposure-row {tone}">
            <div><strong>{escape(localize_sector_name(sector))}</strong><span>{escape(note)}</span></div>
            <i><b style="width:{width:.0f}%"></b></i>
            <em>{weight:.1%}</em>
          </div>"""


def _portfolio_weight_tile(position: PositionAnalysis) -> str:
    tone = "risk" if position.risk_level == "高" or position.trend == "下降趋势" else "watch"
    return f"""
          <div class="portfolio-weight-tile {tone}">
            <span>{escape(position.holding.code)}</span>
            <strong>{escape(position.holding.name)}</strong>
            <p>仓位 {position.weight:.1%} · 盈亏 {position.pnl_ratio:.2f}%</p>
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
    candidate_source: str = "",
    candidate_strategy_label: str = "",
    candidate_evidence: str = "",
    provider_name: str,
    holdings_path: str,
    refresh_time: str,
) -> str:
    del candidates, candidate_source, candidate_strategy_label, candidate_evidence
    driver = stock.upside.drivers[0] if stock.upside.drivers else stock.final_conclusion
    risk = stock.risks[0] if stock.risks else "暂无"
    invalid = stock.invalid_conditions[0] if stock.invalid_conditions else trade_plan.stop_loss
    analysis_content = _render_stock_simple_analysis_content(
        stock=stock,
        stock_raw=stock_raw,
        sectors=sectors,
        technical=technical,
        event_radar=event_radar,
        announcement_report=announcement_report,
        portfolio=portfolio,
        quality=quality,
        trade_plan=trade_plan,
        invalid=invalid,
    )
    return f"""
    <section class="module" id="module-stock">
      <div class="module-header"><div><h2 class="module-title">个股分析</h2><p class="module-desc">一个入口选择股票，结果只保留 K 线、核心结论、建议和预测四块。</p></div><div class="module-header-meta"><span class="risk-pill mid">机会评分 {stock.upside.score}/100</span><span class="status-pill">{escape(stock.name)} · {escape(stock.code)}</span>{_render_module_refresh_tools(refresh_time=refresh_time, stock_code=resolved.query, provider_name=provider_name, holdings_path=holdings_path, workspace="stock")}</div></div>
      {_render_stock_simple_entry(resolved, provider_name, holdings_path)}
      {_render_stock_simple_kline_data(stock, stock_raw, technical, quality)}
      {analysis_content}
      {_render_stock_simple_next_advice(stock, trade_plan, driver, risk, invalid, event_radar)}
      {_render_stock_simple_forecast(stock, technical, event_radar, quality)}
    </section>"""


def _render_stock_simple_entry(
    resolved: ResolvedSymbol,
    provider_name: str,
    holdings_path: str,
) -> str:
    return f"""
      <div class="panel stock-switch-panel">
        <div class="editor-toolbar">
          <div><h3>分析入口</h3><p class="section-subtitle">输入股票代码或名称后，页面只展示本次分析结果。</p></div>
        </div>
        <form class="stock-form" method="get" action="{workspace_action("module-stock")}">
          <input type="hidden" name="provider" value="{escape(provider_name)}" />
          <input type="hidden" name="holdings" value="{escape(holdings_path)}" />
          <input name="code" value="{escape(resolved.query)}" placeholder="输入股票代码或名称" />
          <button type="submit">开始分析</button>
        </form>
      </div>"""


def _render_stock_simple_kline_data(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    technical: TechnicalProfile,
    quality: DataQualityView,
) -> str:
    rows = _stock_simple_kline_rows(stock_raw)
    return f"""
      <div class="panel stock-kline-simple-panel">
        <div class="editor-toolbar">
          <div><h3>K线数据</h3><p class="section-subtitle">展示最近日 K 和关键技术统计，用于核对价格趋势。</p></div>
          <span class="portfolio-chip">数据来源：{escape(_stock_data_source_text(stock_raw))}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-card"><span>最新价</span><strong>{stock.latest_close:.2f}</strong><p class="kpi-foot">{escape(stock.trade_date)}</p></div>
          <div class="summary-card"><span>支撑/压力</span><strong>{technical.support:.2f} / {technical.resistance:.2f}</strong><p class="kpi-foot">失效 {technical.invalid_line:.2f}</p></div>
          <div class="summary-card"><span>均线</span><strong>{escape(_stock_ma_text(technical))}</strong><p class="kpi-foot">{escape(technical.macd_status)}</p></div>
          <div class="summary-card"><span>量能</span><strong>{technical.volume_ratio:.2f}x</strong><p class="kpi-foot">{escape(quality.status)}</p></div>
        </div>
        <table class="data-table">
          <thead><tr><th>日期</th><th>开盘</th><th>最高</th><th>最低</th><th>收盘</th><th>成交量</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>"""


def _stock_simple_kline_rows(stock_raw: StockRawData) -> str:
    if not stock_raw.bars:
        return '<tr><td colspan="6">缺少 K线数据。</td></tr>'
    return "".join(
        "<tr>"
        f"<td>{escape(bar.date)}</td>"
        f"<td>{bar.open:.2f}</td>"
        f"<td>{bar.high:.2f}</td>"
        f"<td>{bar.low:.2f}</td>"
        f"<td>{bar.close:.2f}</td>"
        f"<td>{bar.volume:.0f}</td>"
        "</tr>"
        for bar in stock_raw.bars[-8:]
    )


def _stock_ma_text(technical: TechnicalProfile) -> str:
    return f"MA5 {_fmt_optional(technical.ma5)} / MA20 {_fmt_optional(technical.ma20)}"


def _render_stock_simple_analysis_content(
    *,
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    trade_plan: TradePlan,
    invalid: str,
) -> str:
    rows = _stock_simple_analysis_rows(
        stock=stock,
        stock_raw=stock_raw,
        sectors=sectors,
        technical=technical,
        event_radar=event_radar,
        announcement_report=announcement_report,
        portfolio=portfolio,
        trade_plan=trade_plan,
        invalid=invalid,
    )
    data_rows = _stock_simple_data_rows(stock_raw)
    warning_html = _stock_simple_quality_warning(quality)
    return f"""
      <div class="panel stock-analysis-simple-panel">
        <div class="editor-toolbar">
          <div><h3>分析内容</h3><p class="section-subtitle">当前判断：{escape(trade_plan.verdict)}；只保留影响结论的核心数据。</p></div>
          <span class="portfolio-chip">{escape(quality.signal)}</span>
        </div>
        {warning_html}
        <table class="data-table">
          <thead><tr><th>维度</th><th>原因分析</th><th>影响/验证</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
        <table class="data-table" style="margin-top:12px">
          <thead><tr><th>数据块</th><th>状态</th><th>说明</th><th>数据来源</th></tr></thead>
          <tbody>{data_rows}</tbody>
        </table>
      </div>"""


def _stock_simple_quality_warning(quality: DataQualityView) -> str:
    if not quality.warnings:
        return f'<div class="quality-banner"><strong>数据可信度</strong>：{escape(quality.status)}</div>'
    items = "；".join(quality.warnings[:3])
    return (
        '<div class="quality-banner warning">'
        f"<strong>数据可信度</strong>：{escape(quality.status)}；{escape(items)}"
        "</div>"
    )


def _stock_simple_analysis_rows(
    *,
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    portfolio: PortfolioAnalysisReport,
    trade_plan: TradePlan,
    invalid: str,
) -> str:
    position = next((item for item in portfolio.positions if item.holding.code == stock.code), None)
    announcement_count = len(announcement_report.items) if announcement_report else 0
    rows = [
        (
            "趋势/量价原因 / 多日趋势原因",
            _stock_trend_cause(stock, stock_raw, technical),
            _stock_trend_validation(technical, invalid),
        ),
        (
            "资金/成交原因",
            _stock_fund_cause(stock_raw),
            _stock_fund_validation(stock_raw),
        ),
        (
            "基本面/估值原因",
            _stock_fundamental_cause(stock_raw),
            _stock_fundamental_validation(stock_raw),
        ),
        (
            "消息/公告原因",
            _stock_event_cause(stock_raw, event_radar, announcement_count),
            _stock_event_validation(stock_raw, event_radar, announcement_report),
        ),
        (
            "板块/主题原因 / 主题板块对比",
            _stock_theme_cause(stock, sectors),
            _stock_theme_validation(stock, sectors),
        ),
        (
            "综合对比结论",
            _stock_composite_comparison_cause(stock, stock_raw, sectors),
            _stock_composite_comparison_validation(stock, stock_raw, sectors, trade_plan),
        ),
        (
            "持仓/成本原因",
            _stock_holding_cost_cause(position, trade_plan),
            _stock_holding_cost_validation(position, trade_plan, invalid),
        ),
    ]
    return "".join(
        "<tr>"
        f"<td>{escape(label)}</td>"
        f"<td>{escape(_short_condition(verdict, 96))}</td>"
        f"<td>{escape(evidence)}</td>"
        "</tr>"
        for label, verdict, evidence in rows
    )


def _stock_trend_cause(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    technical: TechnicalProfile,
) -> str:
    if not stock_raw.bars:
        return "技术原因：K线缺失，趋势判断降级为观察"
    multi_day = _stock_multi_day_trend_text(stock_raw)
    volume_text = _stock_volume_side_fund_text(stock_raw) or "量价承接待补"
    return (
        f"技术原因：{multi_day}；{stock.trend}来自{technical.structure}，"
        f"用于确认连续性而不是只看单日涨跌；{volume_text}"
    )


def _stock_multi_day_trend_text(stock_raw: StockRawData) -> str:
    five_day = _stock_period_pct(stock_raw, 5)
    ten_day = _stock_period_pct(stock_raw, 10)
    up_days, total_days = _stock_recent_up_down_days(stock_raw, 10)
    close_position = _stock_recent_close_position(stock_raw, 10)
    return (
        f"最近5日 {five_day} / 最近10日 {ten_day} / "
        f"多日收盘 {up_days}/{total_days} 日上涨 / {close_position}"
    )


def _stock_period_pct(stock_raw: StockRawData, days: int) -> str:
    if len(stock_raw.bars) < 2:
        return "数据不足"
    usable = min(days, len(stock_raw.bars) - 1)
    start = stock_raw.bars[-usable - 1].close
    end = stock_raw.bars[-1].close
    if not start:
        return "数据不足"
    return f"{(end - start) / start * 100:.2f}%"


def _stock_recent_up_down_days(stock_raw: StockRawData, days: int) -> tuple[int, int]:
    if len(stock_raw.bars) < 2:
        return 0, 0
    recent = stock_raw.bars[-min(days + 1, len(stock_raw.bars)) :]
    changes = [
        (current.close - previous.close)
        for previous, current in zip(recent, recent[1:])
    ]
    return sum(1 for change in changes if change > 0), len(changes)


def _stock_recent_close_position(stock_raw: StockRawData, days: int) -> str:
    if not stock_raw.bars:
        return "区间位置不足"
    recent = stock_raw.bars[-min(days, len(stock_raw.bars)) :]
    low = min(bar.low for bar in recent)
    high = max(bar.high for bar in recent)
    close = recent[-1].close
    if high <= low:
        return "区间位置不足"
    percentile = (close - low) / (high - low) * 100
    if percentile >= 70:
        position = "靠近区间上沿"
    elif percentile <= 30:
        position = "靠近区间下沿"
    else:
        position = "处于区间中部"
    return f"{days}日区间 {low:.2f}-{high:.2f} 收盘{position}"


def _stock_trend_validation(
    technical: TechnicalProfile,
    invalid: str,
) -> str:
    return (
        f"影响/验证：最近5日与最近10日方向一致，且站稳 {technical.support:.2f} "
        f"才保留趋势判断；放量突破 {technical.resistance:.2f} 才提高进攻优先级；"
        f"失效看 {invalid}"
    )


def _stock_fund_cause(stock_raw: StockRawData) -> str:
    fund_text = _stock_fund_flow_text(stock_raw)
    if "未接入" in fund_text or "不明确" in fund_text:
        return f"资金原因：{fund_text}，资金面不能单独作为交易理由"
    return f"资金原因：{fund_text}，说明当前承接或分歧方向，但仍需价格确认"


def _stock_fund_validation(stock_raw: StockRawData) -> str:
    note = _stock_fund_flow_note(stock_raw)
    return f"影响/验证：继续看成交额、换手率和价格方向是否同向；{note}"


def _stock_fundamental_cause(stock_raw: StockRawData) -> str:
    valuation = _stock_valuation_text(stock_raw)
    if valuation == "估值未接入":
        return "估值原因：财务和估值缺失，基本面不能支持加仓或抄底"
    return f"估值原因：{valuation} 决定安全边际和盈利弹性，不能只看短线涨跌"


def _stock_fundamental_validation(stock_raw: StockRawData) -> str:
    return f"影响/验证：用估值分位、营收利润和现金流复核是否支撑当前价格；{_stock_valuation_note(stock_raw)}"


def _stock_event_cause(
    stock_raw: StockRawData,
    event_radar: EventRadar,
    announcement_count: int,
) -> str:
    news_count = len(stock_raw.news_items)
    if announcement_count == 0 and news_count == 0:
        return "事件原因：公告和新闻未补齐，消息面不能作为交易理由"
    event_text = _stock_news_text(event_radar, announcement_count, news_count)
    return f"事件原因：{event_text} 影响风险闸门和催化确认，需先判断利好还是风险"


def _stock_event_validation(
    stock_raw: StockRawData,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
) -> str:
    evidence = _stock_simple_news_evidence(stock_raw, event_radar, announcement_report)
    return f"影响/验证：先读标题和原文，再看事件是否改变业绩、订单、监管或减持风险；{evidence}"


def _stock_theme_cause(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    sector_text = _stock_sector_comparison_text(stock, sectors)
    if "主线未确认" in sector_text:
        return "板块原因：主线未确认，个股只能按自身量价和基本面复核"
    if "在主线板块内" in sector_text:
        return f"板块原因：{sector_text}，上涨更可能获得主题扩散和资金关注"
    return f"板块原因：{sector_text}，未在前排主线时不提高追涨优先级"


def _stock_theme_validation(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    note = _stock_sector_comparison_note(stock, sectors)
    return f"影响/验证：先比较所属主题与主线板块强弱，再看个股是否跑赢主题；{note}"


def _stock_composite_comparison_cause(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
) -> str:
    trend = _stock_multi_day_trend_text(stock_raw)
    theme = _stock_sector_comparison_text(stock, sectors)
    fund = _stock_fund_flow_text(stock_raw)
    return (
        f"综合结论：先看多日期趋势，再看主题板块，再看资金/消息；"
        f"{trend}；{theme}；资金面 {fund}"
    )


def _stock_composite_comparison_validation(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    trade_plan: TradePlan,
) -> str:
    theme_note = _stock_sector_comparison_note(stock, sectors)
    data_blocks = _stock_required_data_blocks(stock_raw)
    missing = [item["name"] for item in data_blocks if item["tone"] == "missing"]
    missing_text = "缺口：" + "、".join(missing) if missing else "K线、资金、消息、公告、基本面已纳入"
    return (
        f"影响/验证：若多日趋势、主题强弱和资金方向不一致，只做观察；"
        f"{theme_note}；{missing_text}；动作边界：{trade_plan.verdict}"
    )


def _stock_holding_cost_cause(
    position: PositionAnalysis | None,
    trade_plan: TradePlan,
) -> str:
    if position is None:
        return "成本原因：当前账号未持仓，不能用成本线做买卖理由"
    state = _stock_holding_state(position)
    cost_text = _stock_cost_position_text(position)
    return (
        f"成本原因：{state}来自{cost_text}和仓位 {position.weight:.1%}，"
        f"处理顺序必须受止损线约束；{_short_condition(trade_plan.verdict, 24)}"
    )


def _stock_holding_cost_validation(
    position: PositionAnalysis | None,
    trade_plan: TradePlan,
    invalid: str,
) -> str:
    return f"影响/验证：{_stock_cost_position_note(position, trade_plan, invalid)}"


def _stock_simple_news_evidence(
    stock_raw: StockRawData,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
) -> str:
    parts: list[str] = []
    if stock_raw.news_items:
        source = stock_raw.news_items[0].source or "新闻源"
        titles = "；".join(item.title for item in stock_raw.news_items[:3])
        parts.append(f"{source}：{titles}")
    if announcement_report and announcement_report.items:
        titles = "；".join(item.title for item in announcement_report.items[:3])
        parts.append(f"公告：{titles}")
    if parts:
        return "；".join(parts)
    return f"事件风险 {event_radar.risk_score}/100"


def _stock_simple_data_rows(stock_raw: StockRawData) -> str:
    return "".join(
        "<tr>"
        f"<td>{escape(block['name'])}</td>"
        f"<td>{escape(block['status'])}</td>"
        f"<td>{escape(block['evidence'])}</td>"
        f"<td>{escape(block['source'])}</td>"
        "</tr>"
        for block in _stock_required_data_blocks(stock_raw)
    )


def _render_stock_simple_next_advice(
    stock: DeepStockReport,
    trade_plan: TradePlan,
    driver: str,
    risk: str,
    invalid: str,
    event_radar: EventRadar,
) -> str:
    rows = [
        ("当前动作", trade_plan.verdict, trade_plan.reason),
        ("买入/加仓", trade_plan.entry_trigger, trade_plan.add_trigger),
        ("止损/减仓", trade_plan.stop_loss, trade_plan.reduce_trigger),
        ("止盈", trade_plan.take_profit, f"核心驱动：{driver}"),
        ("风险", invalid, f"{risk}；事件闸门 {event_radar.gate}"),
    ]
    action_rows = "".join(
        "<tr>"
        f"<td>{escape(label)}</td>"
        f"<td>{escape(_short_condition(condition, 96))}</td>"
        f"<td>{escape(_short_condition(note, 96))}</td>"
        "</tr>"
        for label, condition, note in rows
    )
    return f"""
      <div class="panel stock-next-advice-panel">
        <div class="editor-toolbar">
          <div><h3>后续建议</h3><p class="section-subtitle">{escape(stock.name)} 后续只看价格触发、风险线和事件变化。</p></div>
          <span class="portfolio-chip">{escape(trade_plan.target_position)}</span>
        </div>
        <table class="data-table">
          <thead><tr><th>项目</th><th>条件</th><th>说明</th></tr></thead>
          <tbody>{action_rows}</tbody>
        </table>
      </div>"""


def _render_stock_simple_forecast(
    stock: DeepStockReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    quality: DataQualityView,
) -> str:
    forecast = _stock_five_day_forecast(stock, technical, event_radar, quality)
    up_target = max(technical.resistance, stock.latest_close * 1.06)
    down_risk = min(technical.invalid_line, stock.latest_close * 0.95)
    rows = [
        (
            "5日方向",
            forecast["direction"],
            forecast["reason"],
            forecast["validation"],
        ),
        (
            "预测区间",
            forecast["range"],
            forecast["range_reason"],
            f"站稳 {technical.support:.2f} / 突破 {technical.resistance:.2f} 后重新校准",
        ),
        (
            "上行空间",
            f"突破 {technical.resistance:.2f} 后上看 {up_target:.2f}",
            forecast["up_reason"],
            f"放量突破 {technical.resistance:.2f} 且资金承接不转弱",
        ),
        (
            "下行风险",
            f"跌破 {technical.invalid_line:.2f} 后下看 {down_risk:.2f}",
            forecast["down_reason"],
            f"跌破 {technical.invalid_line:.2f} 或事件闸门转弱",
        ),
        (
            "数据置信",
            forecast["confidence"],
            f"{quality.status}；{event_radar.gate}",
            "K线、资金、消息、基本面任一补齐后，概率重新计算。",
        ),
    ]
    cards = [
        ("预测方向", forecast["direction"], forecast["bias"]),
        ("上涨概率", f"{forecast['up_prob']}%", forecast["up_reason"]),
        ("震荡概率", f"{forecast['flat_prob']}%", forecast["flat_reason"]),
        ("下跌概率", f"{forecast['down_prob']}%", forecast["down_reason"]),
    ]
    card_html = "".join(
        "<div class='summary-card'>"
        f"<span>{escape(label)}</span><strong>{escape(value)}</strong>"
        f"<p class='kpi-foot'>{escape(note)}</p></div>"
        for label, value, note in cards
    )
    forecast_rows = "".join(
        "<tr>"
        f"<td>{escape(item)}</td>"
        f"<td>{escape(result)}</td>"
        f"<td>{escape(reason)}</td>"
        f"<td>{escape(validation)}</td>"
        "</tr>"
        for item, result, reason, validation in rows
    )
    return f"""
      <div class="panel stock-forecast-panel">
        <div class="editor-toolbar">
          <div><h3>未来涨跌预测</h3><p class="section-subtitle">基于当前 K 线、资金、事件和数据质量给未来 5 日方向概率；不是收益承诺。</p></div>
          <span class="portfolio-chip">置信度：{escape(forecast["confidence"])}</span>
        </div>
        <div class="summary-grid">{card_html}</div>
        <table class="data-table" style="margin-top:12px">
          <thead><tr><th>预测项</th><th>结果</th><th>预测原因</th><th>验证条件</th></tr></thead>
          <tbody>{forecast_rows}</tbody>
        </table>
      </div>"""


def _stock_five_day_forecast(
    stock: DeepStockReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    quality: DataQualityView,
) -> dict[str, str | int]:
    trend_up = "上升" in stock.trend
    trend_down = "下降" in stock.trend
    risk_high = stock.risk_level == "高" or event_radar.risk_score >= 70
    risk_low = stock.risk_level == "低" and event_radar.risk_score < 55
    data_blocked = quality.gate_level == "blocked"

    up_weight = 1.0 + max(stock.upside.score - 50, 0) / 45
    flat_weight = 1.1
    down_weight = 0.9 + max(50 - stock.upside.score, 0) / 55
    if trend_up:
        up_weight += 0.55
    if trend_down:
        down_weight += 0.65
    if risk_low:
        up_weight += 0.25
    if risk_high:
        down_weight += 0.55
        up_weight -= 0.2
    if data_blocked:
        flat_weight += 0.45
        down_weight += 0.2
        up_weight -= 0.2
    if event_radar.gate in {"公告待补充", "事件需复核"}:
        flat_weight += 0.25

    up_prob, flat_prob, down_prob = _normalize_forecast_probabilities(
        up_weight, flat_weight, down_weight
    )
    direction = _forecast_direction(up_prob, flat_prob, down_prob)
    up_target = max(technical.resistance, stock.latest_close * 1.06)
    down_risk = min(technical.invalid_line, stock.latest_close * 0.95)
    forecast_low, forecast_high = _forecast_price_range(
        direction, technical, up_target, down_risk
    )
    if data_blocked:
        confidence = "低"
    elif risk_high or event_radar.gate != "事件正常":
        confidence = "中"
    else:
        confidence = "较高" if abs(up_prob - down_prob) >= 18 else "中"
    return {
        "direction": direction,
        "bias": f"上涨 {up_prob}% / 震荡 {flat_prob}% / 下跌 {down_prob}%",
        "up_prob": up_prob,
        "flat_prob": flat_prob,
        "down_prob": down_prob,
        "range": f"{forecast_low:.2f} - {forecast_high:.2f}",
        "confidence": confidence,
        "reason": _stock_forecast_reason(stock, event_radar, quality),
        "range_reason": f"下沿参考支撑/失效线，上沿参考压力位与 6% 潜在空间；现价 {stock.latest_close:.2f}",
        "up_reason": _stock_forecast_up_reason(stock, technical),
        "flat_reason": "多空概率接近或数据仍需确认时，先按区间震荡处理",
        "down_reason": _stock_forecast_down_reason(stock, technical, event_radar),
        "validation": _stock_forecast_validation(direction, technical, event_radar),
    }


def _normalize_forecast_probabilities(
    up_weight: float, flat_weight: float, down_weight: float
) -> tuple[int, int, int]:
    weights = [max(up_weight, 0.2), max(flat_weight, 0.2), max(down_weight, 0.2)]
    total = sum(weights)
    up = round(weights[0] / total * 100)
    flat = round(weights[1] / total * 100)
    down = max(0, 100 - up - flat)
    return up, flat, down


def _forecast_direction(up_prob: int, flat_prob: int, down_prob: int) -> str:
    if up_prob >= flat_prob and up_prob >= down_prob and up_prob - down_prob >= 8:
        return "偏上涨"
    if down_prob >= up_prob and down_prob >= flat_prob and down_prob - up_prob >= 8:
        return "偏下跌"
    return "偏震荡"


def _forecast_price_range(
    direction: str,
    technical: TechnicalProfile,
    up_target: float,
    down_risk: float,
) -> tuple[float, float]:
    if direction == "偏上涨":
        return max(down_risk, technical.support), up_target
    if direction == "偏下跌":
        return down_risk, min(up_target, technical.resistance)
    return technical.support, technical.resistance


def _stock_forecast_reason(
    stock: DeepStockReport,
    event_radar: EventRadar,
    quality: DataQualityView,
) -> str:
    driver = stock.upside.drivers[0] if stock.upside.drivers else stock.upside.label
    return (
        f"{stock.trend}、机会分 {stock.upside.score}/100、风险 {stock.risk_level}；"
        f"主因：{driver}；事件闸门 {event_radar.gate}；数据 {quality.signal}"
    )


def _stock_forecast_up_reason(stock: DeepStockReport, technical: TechnicalProfile) -> str:
    if "上升" in stock.trend:
        return f"趋势向上且靠近压力 {technical.resistance:.2f}，突破后上行概率提高"
    return f"需要先站回压力 {technical.resistance:.2f}，否则上涨只按反弹看"


def _stock_forecast_down_reason(
    stock: DeepStockReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
) -> str:
    if stock.risk_level == "高" or event_radar.risk_score >= 70:
        return f"风险分较高，跌破 {technical.invalid_line:.2f} 后下行概率提高"
    return f"当前下行主要看 {technical.invalid_line:.2f} 是否失守和事件风险是否升温"


def _stock_forecast_validation(
    direction: str,
    technical: TechnicalProfile,
    event_radar: EventRadar,
) -> str:
    if direction == "偏上涨":
        if event_radar.gate != "事件正常":
            return f"先补齐事件/公告，再看是否放量突破 {technical.resistance:.2f}"
        return f"放量突破 {technical.resistance:.2f} 且事件闸门维持 {event_radar.gate}"
    if direction == "偏下跌":
        return f"跌破 {technical.invalid_line:.2f} 或公告/资金出现新增负面"
    return f"维持 {technical.support:.2f}-{technical.resistance:.2f} 区间内，等待方向选择"


def _render_stock_professional_brief(
    *,
    stock: DeepStockReport,
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
    holding_state = _stock_holding_state(position) if position else "未持仓"
    portfolio_impact = _stock_portfolio_impact(position, trade_plan)
    forbidden = trade_plan.forbidden_actions[0] if trade_plan.forbidden_actions else "不追高，不脱离止损线临时加仓。"
    today_action = getattr(trade_plan, "today_action", trade_plan.reason)
    return f"""
      <div class="panel stock-pro-brief">
        <div class="stock-pro-head">
          <div>
            <span class="eyebrow">Professional Stock Brief</span>
            <h3>专业个股结论 / 当前结论</h3>
            <p>{escape(stock.name)}（{escape(stock.code)}）先按“证据够不够、触发到没到、错了怎么办”三步判断，不把缺失数据当成买入理由。</p>
          </div>
          <div class="stock-pro-verdict">
            <span>当前动作</span>
            <strong>{escape(trade_plan.verdict)}</strong>
            <em>{escape(quality.status)}</em>
          </div>
        </div>
        <div class="stock-pro-grid">
          <div><span>今天</span><strong>{escape(_short_condition(today_action, 64))}</strong></div>
          <div><span>买点 / 交易触发</span><strong>{escape(_short_condition(trade_plan.entry_trigger, 64))}</strong></div>
          <div><span>止损 / 失效条件</span><strong>{escape(_short_condition(invalid, 64))}</strong></div>
          <div><span>最强证据</span><strong>{escape(_short_condition(driver, 64))}</strong></div>
          <div><span>最大反证</span><strong>{escape(_short_condition(risk, 64))}</strong></div>
          <div><span>组合影响</span><strong>{escape(_short_condition(portfolio_impact, 64))}</strong></div>
          <div><span>仓位上限</span><strong>{escape(trade_plan.target_position)}</strong></div>
          <div><span>当前持仓状态</span><strong>{escape(holding_state)}</strong></div>
        </div>
        <div class="stock-pro-bear">
          <strong>多空反证</strong>
          <span>多头：{escape(_short_condition(driver, 76))}</span>
          <span>空头：{escape(_short_condition(risk, 76))}</span>
          <span>禁止动作：{escape(_short_condition(forbidden, 76))}</span>
        </div>
      </div>"""


def _render_stock_multidimensional_diagnosis(
    *,
    stock: DeepStockReport,
    stock_raw: StockRawData,
    sectors: SectorAnalysisReport,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    announcement_report: AnnouncementReport | None,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    trade_plan: TradePlan,
    invalid: str,
) -> str:
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock.code),
        None,
    )
    announcement_count = len(announcement_report.items) if announcement_report else 0
    pct = _stock_recent_pct(stock_raw)
    volume_ratio = _stock_volume_ratio(stock_raw)
    volume_text = f"量能 {volume_ratio:.2f}x" if volume_ratio else "量能不足"
    rows = [
        {
            "label": "趋势/量价",
            "legacy": "技术面",
            "verdict": f"{stock.trend} · 近一日 {pct:.2f}% · {volume_text}",
            "evidence": f"{technical.structure}；支撑 {technical.support:.2f}，压力 {technical.resistance:.2f}",
            "risk": f"跌破 {technical.invalid_line:.2f} 或 {invalid}",
            "action": "只在趋势、量能和关键位同时确认时升级动作。",
        },
        {
            "label": "资金/成交",
            "legacy": "资金面",
            "verdict": _stock_fund_flow_text(stock_raw),
            "evidence": _stock_fund_flow_note(stock_raw),
            "risk": "资金接口缺失或成交侧分歧时，不把资金面作为交易理由。",
            "action": "看净流、换手、放量方向是否和价格同向。",
        },
        {
            "label": "基本面/估值",
            "legacy": "基本面",
            "verdict": _stock_valuation_text(stock_raw),
            "evidence": _stock_valuation_note(stock_raw),
            "risk": "财务和估值缺失时，不给估值安全垫判断。",
            "action": "用成长、ROE、现金流和估值约束仓位上限。",
        },
        {
            "label": "消息/公告",
            "legacy": "消息公告",
            "verdict": _stock_news_text(event_radar, announcement_count, len(stock_raw.news_items)),
            "evidence": _stock_news_note(stock_raw, event_radar),
            "risk": f"事件闸门 {event_radar.gate}；公告风险分 {event_radar.risk_score}/100。",
            "action": "利好只作催化，监管/减持/诉讼优先降级。",
        },
        {
            "label": "板块/主题",
            "legacy": "板块主题",
            "verdict": _stock_sector_strength_text(stock, sectors),
            "evidence": _stock_sector_strength_note(stock, sectors),
            "risk": "主题不在主线或个股不在前排时，不做板块共振买点。",
            "action": "确认主题强弱，再确认个股是否跑赢板块。",
        },
        {
            "label": "持仓/成本",
            "legacy": "成本位置",
            "verdict": (
                f"{_stock_holding_state(position)} · {_stock_cost_position_text(position)}"
                if position
                else _stock_cost_position_text(position)
            ),
            "evidence": _stock_cost_position_note(position, trade_plan, invalid),
            "risk": "亏损仓不靠补仓摊薄；盈利仓优先保护利润回撤。",
            "action": "按成本、止损线和目标仓位决定加减，不临盘凭感觉。",
        },
    ]
    cards = "".join(
        f"""
        <article class="stock-diagnosis-card">
          <div><span>{escape(row["legacy"])}</span><h4>{escape(row["label"])}</h4></div>
          <strong>{escape(_short_condition(row["verdict"], 70))}</strong>
          <p><b>依据</b>{escape(_short_condition(row["evidence"], 82))}</p>
          <p><b>反证</b>{escape(_short_condition(row["risk"], 82))}</p>
          <p><b>动作</b>{escape(_short_condition(row["action"], 82))}</p>
        </article>"""
        for row in rows
    )
    gap = quality.warnings[0] if quality.warnings else "暂无硬缺口"
    return f"""
      <div class="panel stock-diagnosis-panel">
        <div class="editor-toolbar">
          <div><h3>多维诊断 / 六类证据</h3><p class="section-subtitle">每个维度只保留结论、依据、反证和动作含义；缺口会降低置信度。</p></div>
          <span class="portfolio-chip">{escape(quality.signal)}</span>
        </div>
        <div class="stock-diagnosis-grid">{cards}</div>
        <div class="quality-banner" style="margin-top:12px"><strong>数据缺口</strong>：{escape(gap)}</div>
      </div>"""


def _render_stock_final_summary(
    *,
    stock: DeepStockReport,
    quality: DataQualityView,
    trade_plan: TradePlan,
    driver: str,
    risk: str,
    invalid: str,
    event_radar: EventRadar,
) -> str:
    downgrade = (
        "数据有缺口，结论降级为观察；先补 K 线、资金、新闻公告和基本面。"
        if quality.warnings
        else "核心数据未触发硬缺口，仍需按价格触发和事件闸门执行。"
    )
    return f"""
      <div class="panel stock-final-summary">
        <div class="editor-toolbar">
          <div><h3>综合总结</h3><p class="section-subtitle">把技术、资金、基本面、消息、板块和成本汇总成一条可执行边界。</p></div>
          <span class="portfolio-chip">{escape(stock.risk_level)}</span>
        </div>
        <div class="stock-summary-lines">
          <div><span>现在怎么看</span><strong>{escape(trade_plan.verdict)}</strong><p>{escape(_short_condition(getattr(trade_plan, "today_action", trade_plan.reason), 96))}</p></div>
          <div><span>什么条件转强</span><strong>{escape(_short_condition(trade_plan.entry_trigger, 82))}</strong><p>{escape(_short_condition(driver, 96))}</p></div>
          <div><span>执行边界</span><strong>{escape(_short_condition(trade_plan.target_position, 82))}</strong><p>买点未触发不追；止损/减仓触发：{escape(_short_condition(trade_plan.stop_loss, 96))}</p></div>
          <div><span>什么条件失效/减仓</span><strong>{escape(_short_condition(invalid, 82))}</strong><p>{escape(_short_condition(risk, 96))}；事件闸门：{escape(event_radar.gate)}</p></div>
          <div><span>数据降级规则</span><strong>{escape(quality.status)}</strong><p>{escape(downgrade)}</p></div>
        </div>
      </div>"""


def _render_stock_candidate_context(
    source: str,
    strategy: str,
    evidence: str,
) -> str:
    if source != "opportunity" and not strategy and not evidence:
        return ""
    source_label = "股市机会" if source == "opportunity" else source or "外部入口"
    return f"""
      <div class="panel stock-candidate-context-panel">
        <div class="editor-toolbar">
          <div><h3>来源上下文</h3><p class="section-subtitle">从机会进入个股分析时，保留来源、策略和命中证据，避免脱离筛选上下文。</p></div>
          <span class="portfolio-chip">{escape(source_label)}</span>
        </div>
        <div class="summary-grid compact-summary-grid">
          <div class="summary-card"><span>来源</span><strong>{escape(source_label)}</strong></div>
          <div class="summary-card"><span>命中策略</span><strong>{escape(strategy or "未传入")}</strong></div>
          <div class="summary-card"><span>命中证据</span><strong>{escape(evidence or "未传入")}</strong></div>
        </div>
      </div>"""


def _render_stock_required_data_audit(stock_raw: StockRawData) -> str:
    blocks = _stock_required_data_blocks(stock_raw)
    rows = "".join(
        f"""
        <div class="stock-data-block {escape(block['tone'])}">
          <span>{escape(block['name'])}</span>
          <strong>{escape(block['status'])}</strong>
          <p>{escape(block['evidence'])}</p>
          <em>数据来源：{escape(block['source'])}</em>
        </div>"""
        for block in blocks
    )
    missing_count = sum(1 for block in blocks if block["tone"] == "missing")
    summary = "五类必备数据已用于分析" if missing_count == 0 else f"{missing_count} 类数据缺失降级"
    return f"""
      <div class="panel stock-data-audit-panel">
        <div class="editor-toolbar">
          <div><h3>数据质量</h3><p class="section-subtitle">K线数据、资金面、消息面、公告、基本面必须逐项核验；缺失项不作为买入理由。</p></div>
          <span class="portfolio-chip">{escape(summary)}</span>
        </div>
        <div class="stock-data-block-grid">{rows}</div>
      </div>"""


def _stock_required_data_blocks(stock_raw: StockRawData) -> list[dict[str, str]]:
    source_text = _stock_data_source_text(stock_raw)
    return [
        _stock_required_block(
            "K线数据",
            bool(stock_raw.bars),
            f"{len(stock_raw.bars)} 根日 K；用于趋势、均线、支撑压力和量价判断。",
            "缺失降级：K线数据缺失，不做趋势突破判断，不作为买入理由。",
            _source_for_block(stock_raw, ["daily", "kline", "tdx", "tencent", "itick"], source_text),
        ),
        _stock_required_block(
            "资金面",
            stock_raw.fund_flow is not None or bool(stock_raw.fund_flow_detail),
            _fund_flow_evidence(stock_raw),
            "缺失降级：资金面缺失，不把资金流入/流出作为买入理由。",
            _source_for_block(stock_raw, ["moneyflow", "fund", "tdx", "akshare"], source_text),
        ),
        _stock_required_block(
            "消息面",
            bool(stock_raw.news_items),
            _news_evidence(stock_raw),
            "缺失降级：消息面缺失，不做公告催化或情绪交易判断，不作为买入理由。",
            _source_for_block(stock_raw, ["news", "announcement", "cninfo", "akshare"], source_text),
        ),
        _stock_required_block(
            "公告",
            bool(stock_raw.announcements),
            _announcement_evidence(stock_raw),
            "缺失降级：公告缺失，不做公告催化、监管风险或财报事件判断。",
            _source_for_block(stock_raw, ["announcement", "cninfo"], source_text),
        ),
        _stock_required_block(
            "基本面",
            stock_raw.pe_ttm is not None
            or bool(stock_raw.valuation)
            or bool(stock_raw.fundamental_metrics),
            _fundamental_evidence(stock_raw),
            "缺失降级：基本面缺失，不把估值安全垫或财务改善作为买入理由。",
            _source_for_block(stock_raw, ["fina", "valuation", "tushare", "tdx"], source_text),
        ),
    ]


def _stock_required_block(
    name: str,
    available: bool,
    available_evidence: str,
    missing_evidence: str,
    source: str,
) -> dict[str, str]:
    if available:
        return {
            "name": name,
            "status": "已用于分析",
            "evidence": available_evidence,
            "source": source,
            "tone": "ok",
        }
    if "不作为买入理由" not in missing_evidence:
        missing_evidence = f"{missing_evidence} 不作为买入理由。"
    return {
        "name": name,
        "status": "缺失降级",
        "evidence": missing_evidence,
        "source": source,
        "tone": "missing",
    }


def _stock_data_source_text(stock_raw: StockRawData) -> str:
    return "、".join(stock_raw.data_sources) if stock_raw.data_sources else "当前 Provider / 本地快照"


def _source_for_block(stock_raw: StockRawData, keywords: list[str], fallback: str) -> str:
    matches = [
        source
        for source in stock_raw.data_sources
        if any(keyword.lower() in source.lower() for keyword in keywords)
    ]
    return "、".join(matches[:3]) if matches else fallback


def _fund_flow_evidence(stock_raw: StockRawData) -> str:
    if stock_raw.fund_flow is not None:
        return f"主力资金 {stock_raw.fund_flow:.2f}；用于资金承接和分歧判断。"
    if stock_raw.fund_flow_detail:
        amount_yuan = _optional_number(stock_raw.fund_flow_detail.get("amount_yuan"))
        turnover_rate = _optional_number(stock_raw.fund_flow_detail.get("turnover_rate"))
        pieces: list[str] = []
        if amount_yuan is not None:
            pieces.append(f"成交额 {amount_yuan / 10000:.2f} 万")
        if turnover_rate is not None:
            pieces.append(f"换手率 {turnover_rate:.2f}%")
        if pieces:
            return "；".join(pieces) + "；用于成交承接代理判断，不等同主力净流。"
        return "资金明细可用；用于主力/大单/净流入结构判断。"
    return "资金面缺失。"


def _news_evidence(stock_raw: StockRawData) -> str:
    if not stock_raw.news_items:
        return "消息面缺失。"
    latest = stock_raw.news_items[0]
    return f"{len(stock_raw.news_items)} 条新闻/公告；最新：{latest.title}"


def _announcement_evidence(stock_raw: StockRawData) -> str:
    if not stock_raw.announcements:
        return "公告缺失。"
    latest = stock_raw.announcements[0]
    title = latest.get("title") or latest.get("公告标题") or "未命名公告"
    return f"{len(stock_raw.announcements)} 条公告；最新：{title}"


def _fundamental_evidence(stock_raw: StockRawData) -> str:
    metrics = _fundamental_metric_parts(stock_raw)
    if metrics:
        return "；".join(metrics[:4]) + "；用于公司质量和估值约束。"
    if stock_raw.pe_ttm is not None:
        return f"PE(TTM) {stock_raw.pe_ttm:.2f}；用于估值和基本面约束。"
    if stock_raw.valuation:
        keys = "、".join(str(key) for key in list(stock_raw.valuation)[:3])
        return f"估值/财务字段可用：{keys}。"
    return "基本面缺失。"


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


def _render_stock_verdict_wall(
    stock: DeepStockReport,
    stock_raw: StockRawData,
    portfolio: PortfolioAnalysisReport,
    quality: DataQualityView,
    technical: TechnicalProfile,
    event_radar: EventRadar,
    trade_plan: TradePlan,
    sectors: SectorAnalysisReport,
    driver: str,
    risk: str,
    invalid: str,
) -> str:
    position = next(
        (item for item in portfolio.positions if item.holding.code == stock.code),
        None,
    )
    dimensions = [
        ("技术面", technical.structure, f"趋势 {stock.trend}；失效 {invalid}"),
        ("基本面", _stock_valuation_text(stock_raw), _stock_valuation_note(stock_raw)),
        ("资金面", _stock_fund_flow_text(stock_raw), _stock_fund_flow_note(stock_raw)),
        ("消息公告", _stock_news_text(event_radar, 0, len(stock_raw.news_items)), event_radar.gate),
        ("板块主题", _stock_sector_strength_text(stock, sectors), _stock_sector_strength_note(stock, sectors)),
        ("成本位置", _stock_cost_position_text(position), _stock_cost_position_note(position, trade_plan, invalid)),
    ]
    dimension_html = "".join(
        _stock_dimension_card(label, support, note, quality)
        for label, support, note in dimensions
    )
    forbidden = trade_plan.forbidden_actions[0] if trade_plan.forbidden_actions else "不追高，不脱离止损线临时加仓。"
    holding_state = _stock_holding_state(position) if position else "未持仓"
    portfolio_impact = _stock_portfolio_impact(position, trade_plan)
    return f"""
      <div class="stock-verdict-wall">
        <div class="stock-verdict-card simple-panel">
          <h3>当前结论</h3>
          <strong>当前动作：{escape(trade_plan.verdict)}</strong>
          <p>{escape(getattr(trade_plan, "today_action", trade_plan.reason))}</p>
          <div class="metric-list">
            <div class="metric-line"><span>最强证据</span><strong>{escape(_short_condition(driver, 68))}</strong></div>
            <div class="metric-line"><span>最大反证</span><strong>{escape(_short_condition(risk, 68))}</strong></div>
            <div class="metric-line"><span>组合影响</span><strong>{escape(portfolio_impact)}</strong></div>
            <div class="metric-line"><span>仓位上限</span><strong>{escape(trade_plan.target_position)}</strong></div>
            <div class="metric-line"><span>当前持仓状态</span><strong>{escape(holding_state)}</strong></div>
            <div class="metric-line"><span>触发条件</span><strong>{escape(trade_plan.entry_trigger)}</strong></div>
            <div class="metric-line"><span>失效条件</span><strong>{escape(invalid)}</strong></div>
            <div class="metric-line"><span>禁止动作</span><strong>{escape(forbidden)}</strong></div>
          </div>
        </div>
        <div class="stock-six-wall">
          <div class="editor-toolbar"><div><h3>六类证据</h3><p class="section-subtitle">每个维度都拆成支持、反对和缺口；缺口会降低置信度。</p></div><span class="portfolio-chip">{escape(quality.status)}</span></div>
          <div class="stock-six-grid">{dimension_html}</div>
        </div>
        <div class="stock-bull-bear">
          <h3>多空反证</h3>
          <div class="compact-note-grid">
            <div class="compact-note-card"><strong>多头观点</strong><p>{escape(driver)}</p></div>
            <div class="compact-note-card"><strong>空头观点</strong><p>{escape(risk)}</p></div>
            <div class="compact-note-card"><strong>组合经理</strong><p>{escape(trade_plan.target_position)}</p></div>
          </div>
        </div>
      </div>"""


def _stock_portfolio_impact(position: PositionAnalysis | None, trade_plan: TradePlan) -> str:
    if position is None:
        return "未持仓，不增加当前组合集中度；先按股票分析验证。"
    return (
        f"已持仓，仓位 {position.weight:.1%}；"
        f"目标 {trade_plan.target_position}，不主动摊薄问题仓。"
    )


def _stock_dimension_card(
    label: str,
    support: str,
    note: str,
    quality: DataQualityView,
) -> str:
    gap = quality.warnings[0] if quality.warnings else "暂无硬缺口"
    return f"""
          <div class="stock-dimension-card">
            <h4>{escape(label)}</h4>
            <p><b>支持</b>{escape(_short_condition(support, 46))}</p>
            <p><b>反对</b>{escape(_short_condition(note, 46))}</p>
            <p><b>缺口</b>{escape(_short_condition(gap, 38))}</p>
          </div>"""


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
          <div><h3>股票输入</h3><p class="section-subtitle">输入代码或名称，K线和分析会一起切换。</p></div>
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


def _stock_sector_comparison_text(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    stock_theme = _stock_theme_name(stock)
    mainline = [localize_sector_name(item) for item in sectors.market_mainline[:3]]
    mainline_text = "、".join(mainline) if mainline else "待确认"
    if not stock_theme:
        return f"所属主题未识别；主线板块 {mainline_text}"
    localized_theme = localize_sector_name(stock_theme)
    sector = _find_sector_analysis(sectors, localized_theme)
    sector_text = (
        f"热度 {sector.heat_score}/100，涨跌 {sector.pct_chg:.2f}%"
        if sector is not None
        else "板块强弱数据待补"
    )
    if localized_theme in mainline:
        return (
            f"所属主题 {localized_theme} 在主线板块内；主线板块 {mainline_text}；{sector_text}"
        )
    return (
        f"所属主题 {localized_theme} 未进入主线板块；主线板块 {mainline_text}；{sector_text}"
    )


def _stock_sector_comparison_note(stock: DeepStockReport, sectors: SectorAnalysisReport) -> str:
    stock_theme = _stock_theme_name(stock)
    if not stock_theme:
        return "所属主题未识别，先用个股多日趋势和资金面判断。"
    localized_theme = localize_sector_name(stock_theme)
    sector = _find_sector_analysis(sectors, localized_theme)
    if sector is None:
        return f"所属主题 {localized_theme} 缺少板块强弱数据，不能确认是否跑赢主题。"
    rank = _sector_rank(sectors, localized_theme)
    rank_text = f"主题排名第 {rank}" if rank else "主题排名待确认"
    return (
        f"所属主题 {localized_theme}，{rank_text}，热度 {sector.heat_score}/100，"
        f"涨跌 {sector.pct_chg:.2f}%，扩散 {sector.advancing_ratio:.0%}。"
    )


def _stock_theme_name(stock: DeepStockReport) -> str:
    explicit = str(getattr(stock, "sector", "") or "").strip()
    if explicit and explicit not in {"未分类", "未识别主题"}:
        return explicit
    mapped = sector_for_code(stock.code)
    if mapped:
        return mapped
    if "茅台" in stock.name or "五粮液" in stock.name:
        return "白酒"
    if "银行" in stock.name:
        return "银行"
    if "宁德" in stock.name:
        return "新能源车"
    return ""


def _find_sector_analysis(sectors: SectorAnalysisReport, theme: str):
    return next(
        (
            item
            for item in sectors.sectors
            if localize_sector_name(item.name).strip() == theme.strip()
        ),
        None,
    )


def _sector_rank(sectors: SectorAnalysisReport, theme: str) -> int:
    ranked = sorted(sectors.sectors, key=lambda item: item.heat_score, reverse=True)
    for index, item in enumerate(ranked, start=1):
        if localize_sector_name(item.name).strip() == theme.strip():
            return index
    return 0


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
            "技术",
            f"{stock.trend} · MA5 {_fmt_optional(technical.ma5)}",
            f"{technical.structure}；RSI {_fmt_optional(technical.rsi14)}",
        ),
        ("基本面", _stock_valuation_text(stock_raw), _stock_valuation_note(stock_raw)),
        ("资金", _stock_fund_flow_text(stock_raw), _stock_fund_flow_note(stock_raw)),
        (
            "消息",
            _stock_news_text(event_radar, announcement_count, len(stock_raw.news_items)),
            _stock_news_note(stock_raw, event_radar),
        ),
        (
            "板块",
            _stock_sector_strength_text(stock, sectors),
            _stock_sector_strength_note(stock, sectors),
        ),
        (
            "成本",
            (
                f"{_stock_holding_state(position)} · {_stock_cost_position_text(position)}"
                if position
                else _stock_cost_position_text(position)
            ),
            _stock_cost_position_note(position, trade_plan, invalid),
        ),
    ]
    row_html = "".join(
        "<tr>"
        f"<td><strong>{escape(label)}</strong></td>"
        f"<td>{escape(value)}</td>"
        f"<td>{escape(_short_condition(note, 72))}</td>"
        "</tr>"
        for label, value, note in rows
    )
    decision_cards = [
        ("动作", trade_plan.verdict),
        ("今天", getattr(trade_plan, "today_action", trade_plan.reason)),
        ("买点", _short_condition(trade_plan.entry_trigger, 54)),
        ("卖点", _short_condition(trade_plan.stop_loss, 54)),
        ("仓位", trade_plan.target_position),
        ("数据", quality.status),
    ]
    card_html = "".join(
        f"<div class='summary-card'><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in decision_cards
    )
    risk_points = [
        risk,
        f"失效线 {technical.invalid_line:.2f}；{invalid}",
        trade_plan.forbidden_actions[0] if trade_plan.forbidden_actions else "不追高、不脱离止损线",
        quality.warnings[0] if quality.warnings else "未触发数据质量硬风险",
    ]
    risk_html = _li_join([_short_condition(item, 78) for item in risk_points])
    base_report = analyze_stock(stock_raw)
    agentic_html = _render_stock_agentic_decision_chain(
        build_stock_agent_decision(stock_raw, base_report)
    )
    return f"""
      <div class="panel" style="margin-top:16px">
        <div class="editor-toolbar">
          <div><h3>个股决策卡</h3><p class="section-subtitle">只保留今天要用的结论、证据和风控。</p></div>
          <span class="portfolio-chip">{escape(stock.name)} · {escape(stock.code)}</span>
        </div>
        <div class="quality-banner good" style="margin-bottom:12px"><strong>一句话：</strong>{escape(trade_plan.verdict)}；{escape(getattr(trade_plan, "today_action", trade_plan.reason))}</div>
        <div class="summary-grid compact-summary-grid">{card_html}</div>
      </div>
      <div class="grid-2 stock-research-grid" style="margin-top:16px">
        <div class="panel">
          <h3>证据链</h3>
          <table class="data-table"><thead><tr><th>维度</th><th>结论</th><th>依据</th></tr></thead><tbody>{row_html}</tbody></table>
        </div>
        <div class="panel">
          <h3>风险边界</h3>
          <ul class="reason-list">{risk_html}</ul>
        </div>
      </div>
      {agentic_html}"""


def _render_stock_agentic_decision_chain(decision: StockAgentDecision) -> str:
    context = decision.context_pack
    attribution = decision.signal_attribution
    source_text = "、".join(context.data_sources[:4])
    available_text = "、".join(context.available_blocks) or "暂无"
    missing_text = "、".join(context.missing_blocks) or "无"
    limitation_text = "；".join(context.limitations[:2]) or "核心数据块可用"
    analyst_rows = "".join(
        "<tr>"
        f"<td><strong>{escape(item.role)}</strong></td>"
        f"<td>{escape(item.verdict)}</td>"
        f"<td>{escape('；'.join(item.evidence[:2]))}</td>"
        f"<td>{escape(item.action)}</td>"
        "</tr>"
        for item in decision.analyst_team
    )
    attr_text = (
        f"技术 {attribution.technical_indicators}% · "
        f"消息 {attribution.news_sentiment}% · "
        f"基本面 {attribution.fundamentals}% · "
        f"资金/成交 {attribution.capital_volume}%"
    )
    no_trade = _li_join(decision.trader.no_trade_conditions[:3])
    return f"""
      <details class="detail-shell" style="margin-top:16px">
        <summary>完整方法链：TradingAgents 决策链 / daily_stock_analysis 信号归因</summary>
        <div class="detail-body">
          <div class="quality-banner" style="margin-bottom:12px">
            <strong>{escape(context.subject)} · {escape(context.trade_date)}</strong><br />
            信号归因：{escape(attr_text)}<br />
            可用 {escape(available_text)}；缺口 {escape(missing_text)}；限制 {escape(limitation_text)}；来源 {escape(source_text)}
          </div>
          <div class="grid-2 stock-research-grid">
            <div class="panel compact-panel">
              <h3>分析师团队</h3>
              <table class="data-table"><thead><tr><th>角色</th><th>判断</th><th>证据</th><th>动作</th></tr></thead><tbody>{analyst_rows}</tbody></table>
            </div>
            <div class="panel compact-panel">
              <h3>多空审议</h3>
              <div class="metric-list">
                <div class="metric-line"><span>多头观点</span><strong>{escape(decision.research_debate.bull_thesis)}</strong></div>
                <div class="metric-line"><span>空头观点</span><strong>{escape(decision.research_debate.bear_thesis)}</strong></div>
                <div class="metric-line"><span>研究经理裁决</span><strong>{escape(decision.research_debate.judge)}</strong></div>
              </div>
            </div>
          </div>
          <div class="grid-2 stock-research-grid" style="margin-top:12px">
            <div class="panel compact-panel">
              <h3>交易员执行</h3>
              <div class="metric-list">
                <div class="metric-line"><span>动作</span><strong>{escape(decision.trader.action)}</strong></div>
                <div class="metric-line"><span>触发</span><strong>{escape(decision.trader.entry_trigger)}</strong></div>
                <div class="metric-line"><span>失效</span><strong>{escape(decision.trader.invalidation)}</strong></div>
                <div class="metric-line"><span>仓位</span><strong>{escape(decision.trader.position_rule)}</strong></div>
              </div>
              <ul class="reason-list">{no_trade}</ul>
            </div>
            <div class="panel compact-panel">
              <h3>组合经理最终意见</h3>
              <div class="metric-list">
                <div class="metric-line"><span>激进</span><strong>{escape(decision.risk_review.aggressive)}</strong></div>
                <div class="metric-line"><span>中性</span><strong>{escape(decision.risk_review.neutral)}</strong></div>
                <div class="metric-line"><span>保守</span><strong>{escape(decision.risk_review.conservative)}</strong></div>
                <div class="metric-line"><span>最终</span><strong>{escape(decision.risk_review.portfolio_decision)}</strong></div>
              </div>
            </div>
          </div>
        </div>
      </details>"""


def _render_stock_professional_scorecard(
    stock_raw: StockRawData,
    portfolio: PortfolioAnalysisReport,
    report: StockAnalysisReport | None = None,
) -> str:
    if not stock_raw.bars:
        return ""
    report = report or analyze_stock(stock_raw)
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
        return f"成本 {position.holding.cost_price:.2f}；不补亏，风控线 {invalid}"
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
    metrics = _fundamental_metric_parts(stock_raw)
    if stock_raw.pe_ttm is None and not metrics:
        return "估值未接入"
    pb = _optional_number(stock_raw.valuation.get("pb"))
    total_mv = _optional_number(stock_raw.valuation.get("total_mv"))
    parts = [f"PE(TTM) {stock_raw.pe_ttm:.1f}"] if stock_raw.pe_ttm is not None else []
    if pb is not None:
        parts.append(f"PB {pb:.2f}")
    if total_mv is not None:
        parts.append(f"市值 {total_mv / 100000000:.0f} 亿")
    parts.extend(metrics[:4])
    return " · ".join(parts)


def _stock_valuation_note(stock_raw: StockRawData) -> str:
    source = stock_raw.fundamental_metrics.get("source") or stock_raw.valuation.get("source")
    date = stock_raw.fundamental_metrics.get("date") or stock_raw.valuation.get("date")
    if source:
        return f"来源 {source}{' · ' + str(date) if date else ''}"
    return "财务质量、营收利润和估值分位待接入"


def _fundamental_metric_parts(stock_raw: StockRawData) -> list[str]:
    metrics = stock_raw.fundamental_metrics
    parts: list[str] = []
    for key, label, suffix in [
        ("revenue_yoy", "营收同比", "%"),
        ("net_profit_yoy", "净利同比", "%"),
        ("roe", "ROE", "%"),
        ("gross_margin", "毛利率", "%"),
        ("debt_to_assets", "资产负债率", "%"),
        ("ocf_to_profit", "经营现金流/净利", "x"),
    ]:
        value = _optional_number(metrics.get(key))
        if value is None:
            continue
        if suffix == "x":
            parts.append(f"{label} {value:.2f}x")
        else:
            parts.append(f"{label} {value:.1f}%")
    for key, label in [
        ("eps", "EPS"),
        ("net_asset_per_share", "每股净资产"),
        ("operating_revenue", "营收"),
        ("net_profit", "净利润"),
        ("operating_cash_flow", "经营现金流"),
    ]:
        value = _optional_number(metrics.get(key))
        if value is not None:
            parts.append(f"{label} {value:.2f}")
    return parts


def _stock_fund_flow_text(stock_raw: StockRawData) -> str:
    if stock_raw.fund_flow is None:
        proxy = _stock_volume_side_fund_text(stock_raw)
        return proxy or "资金明细未接入"
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
    if stock_raw.bars:
        return "资金接口缺失时，用成交量与价格方向做资金侧替代观察，不等同主力净流。"
    return "当前优先使用资金/成交侧信号，不伪造主力净流"


def _stock_volume_side_fund_text(stock_raw: StockRawData) -> str:
    if len(stock_raw.bars) < 3:
        return ""
    latest = stock_raw.bars[-1]
    previous = stock_raw.bars[-2]
    ratio = _stock_volume_ratio(stock_raw)
    if ratio <= 0:
        return ""
    price_up = latest.close >= previous.close
    if ratio >= 1.3 and price_up:
        state = "放量上涨，资金承接偏积极"
    elif ratio >= 1.3:
        state = "放量下跌，资金分歧偏大"
    elif ratio <= 0.75 and price_up:
        state = "缩量上涨，追高确认不足"
    elif ratio <= 0.75:
        state = "缩量下跌，抛压暂未放大"
    else:
        state = "量价中性，资金态度不明确"
    return f"成交侧{state} · 量能 {ratio:.2f}x"


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
        titles = "；".join(item.title for item in stock_raw.news_items[:3])
        source = stock_raw.news_items[0].source or "新闻源"
        return f"{source}：{titles}"
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
    generated_at = _format_beijing_time(status.get("generated_at", "待确认"))
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
            _format_beijing_time(status.get("generated_at", "")),
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
    generated_at_display = _format_beijing_time(generated_at)
    freshness = _automation_freshness_label(generated_at)
    failed_steps = _automation_failed_steps(status)
    advice = _automation_advice(failed_steps)
    execution_readiness = _automation_execution_readiness(status, freshness, failed_steps)
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
          <div class="summary-card"><span>运行节奏</span><strong>00:00/06:00/09:00/12:30/14:00</strong><p class="kpi-foot">服务器定时刷新行情、K线、新闻、公告和日报。</p></div>
          <div class="summary-card"><span>最近运行</span><strong>{escape(generated_at_display)}</strong><p class="kpi-foot">{escape(freshness)}</p></div>
          <div class="summary-card"><span>整体状态</span><strong>{escape(_human_pipeline_status(status.get("status", "未知")))}</strong><p class="kpi-foot">以 pipeline.status 为准。</p></div>
          <div class="summary-card"><span>执行可用性</span><strong>{escape(execution_readiness)}</strong><p class="kpi-foot">先确认新鲜度，再看交易动作。</p></div>
          <div class="summary-card"><span>处理建议</span><strong>{escape(advice)}</strong><p class="kpi-foot">先看 pipeline.status，再看定时任务日志。</p></div>
        </div>
        <table class="data-table" style="margin-top:12px"><thead><tr><th>步骤</th><th>结果</th></tr></thead><tbody>{step_rows}</tbody></table>
      </div>"""


def _automation_execution_readiness(
    status: dict[str, str],
    freshness: str,
    failed_steps: list[str],
) -> str:
    if freshness.startswith("已滞后"):
        return "先别按今天盘面执行"
    if failed_steps:
        return "降级为观察"
    if _human_pipeline_status(status.get("status", "")) == "完成":
        return "可条件化使用"
    return "先复核数据"


def _automation_freshness_label(generated_at: str) -> str:
    if not generated_at or generated_at == "未记录":
        return "未记录运行时间"
    age_hours = _hours_since(generated_at)
    if age_hours is None:
        return "运行时间格式待复核"
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
        if str(value).lower().startswith(("failed", "partial", "skipped")):
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
    if lower.startswith("skipped"):
        return "跳过：未采集"
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


def _can_manage_global_settings(
    user: AuthUser | None,
    *,
    config: AuthConfig | None = None,
) -> bool:
    if not is_auth_enabled(config):
        return True
    return bool(user and user.role == "owner")


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
        candidate_source = query.get("candidate_source", [""])[0]
        candidate_strategy_label = query.get("candidate_strategy_label", [""])[0]
        candidate_evidence = query.get("candidate_evidence", [""])[0]
        refresh = query.get("refresh", [""])[0] == "1"
        if refresh:
            _trigger_manual_data_refresh()
            self.send_response(303)
            self.send_header("Location", _manual_refresh_redirect_location(query))
            self.end_headers()
            return
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
            candidate_source=candidate_source,
            candidate_strategy_label=candidate_strategy_label,
            candidate_evidence=candidate_evidence,
            current_user=current_user,
            refresh=refresh,
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
        if parsed.path == "/account/morning-email":
            self._handle_morning_email_settings_post()
            return
        if parsed.path == "/account/morning-email/send":
            self._handle_morning_email_send_post()
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
        current_user = user_from_cookie_header(self.headers.get("Cookie", ""), config=config)
        if parsed.path in {"/settings", "/notification-test", "/dispatch-daily"} and not _can_manage_global_settings(
            current_user,
            config=config,
        ):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Only owner accounts can change global settings.")
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

    def _handle_morning_email_settings_post(self) -> None:
        config = AuthConfig.from_env()
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=config)
        if user is None:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?" + urlencode({"next": "/#module-account", "error": "请先登录"}),
            )
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        form = parse_qs(payload)
        receiver = (form.get("morning_email_receiver", [""])[0] or "").strip()
        send_time = (form.get("morning_email_time", ["08:30"])[0] or "08:30").strip()
        enabled = form.get("morning_email_enabled", [""])[0] == "1"
        try:
            save_morning_email_preferences(
                user.id,
                receiver=receiver,
                send_time=send_time,
                enabled=enabled,
                user_data_dir=os.getenv("STOCK_TS_USER_DATA_DIR", DEFAULT_USER_DATA_DIR),
            )
            notice = "晨报邮箱配置已保存。"
            level = "success"
        except ValueError as exc:
            notice = str(exc)
            level = "error"
        self.send_response(303)
        self.send_header(
            "Location",
            _account_redirect_url(
                holdings_path=_effective_holdings_path(user),
                notice=notice,
                notice_level=level,
            ),
        )
        self.end_headers()

    def _handle_morning_email_send_post(self) -> None:
        config = AuthConfig.from_env()
        user = user_from_cookie_header(self.headers.get("Cookie", ""), config=config)
        if user is None:
            self.send_response(303)
            self.send_header(
                "Location",
                "/login?" + urlencode({"next": "/#module-account", "error": "请先登录"}),
            )
            self.end_headers()
            return
        holdings_path = _effective_holdings_path(user)
        preferences = load_morning_email_preferences(
            user.id,
            username=user.username,
            user_data_dir=os.getenv("STOCK_TS_USER_DATA_DIR", DEFAULT_USER_DATA_DIR),
        )
        ok, detail = _send_personal_morning_report(
            user,
            preferences,
            holdings_path=holdings_path,
        )
        notice = f"晨报已发送：{detail}" if ok else f"晨报发送失败：{detail}"
        self.send_response(303)
        self.send_header(
            "Location",
            _account_redirect_url(
                holdings_path=holdings_path,
                notice=notice,
                notice_level="success" if ok else "error",
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


def _send_personal_morning_report(
    user: AuthUser,
    preferences: MorningEmailPreferences,
    *,
    holdings_path: str | Path,
    dry_run: bool = False,
) -> tuple[bool, str]:
    del user
    receivers = preferences.receivers
    if not receivers:
        return False, "接收邮箱为空。"
    try:
        from scripts.send_morning_report import send_morning_report

        result = send_morning_report(
            holdings_path=holdings_path,
            channels=["email"],
            email_receivers=receivers,
            dry_run=dry_run,
            style="digest",
        )
    except Exception as exc:
        return False, str(exc)
    return bool(result.ok), _first_dispatch_detail(result.markdown)


def _first_dispatch_detail(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            return stripped[2:]
    return "未返回发送明细"


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


def _account_redirect_url(
    *,
    holdings_path: str,
    notice: str,
    notice_level: str,
) -> str:
    query = urlencode(
        {
            "provider": WEB_DATA_PROVIDER,
            "holdings": holdings_path,
            "settings_notice": notice,
            "settings_notice_level": notice_level,
        }
    )
    return f"/?{query}#module-account"


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
