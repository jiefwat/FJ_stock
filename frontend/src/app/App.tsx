import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellRing, Binoculars, Briefcase, Flame, History, Layers3, MessageSquareText, Network, PanelLeftClose, PanelLeftOpen, RefreshCw, Search, Star, UserRound, X } from "lucide-react";
import { lazy, Suspense, type FormEvent, useEffect, useRef, useState } from "react";
import { HashRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { loadRecentResearch, recentResearchUpdatedEvent, rememberRecentResearch, type RecentResearch } from "../lib/recentResearch";
import {
  api,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  type AuthResult,
  type DecisionEventFeed,
  type RefreshResult,
  type UserAccount,
  type UserPreferences,
  type Quote,
} from "../lib/api";

function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } });
}

const loadMarketPage = () => import("../features/market/MarketPage");
const loadDecisionCenterPage = () => import("../features/decisions/DecisionCenterPage");
const loadOpportunitiesPage = () => import("../features/opportunities/OpportunitiesPage");
const loadStockLabPage = () => import("../features/stocks/StockLabPage");
const loadRecommendationHistoryPage = () => import("../features/history/RecommendationHistoryPage");
const loadAskStockPage = () => import("../features/ask/AskStockPage");
const loadHoldingsPage = () => import("../features/holdings/HoldingsPage");
const loadLimitLadderPage = () => import("../features/structure/LimitLadderPage");
const loadMarketGroupPage = () => import("../features/structure/MarketGroupPage");

const MarketPage = lazy(() => loadMarketPage().then((module) => ({ default: module.MarketPage })));
const DecisionCenterPage = lazy(() => loadDecisionCenterPage().then((module) => ({ default: module.DecisionCenterPage })));
const OpportunitiesPage = lazy(() => loadOpportunitiesPage().then((module) => ({ default: module.OpportunitiesPage })));
const StockLabPage = lazy(() => loadStockLabPage().then((module) => ({ default: module.StockLabPage })));
const RecommendationHistoryPage = lazy(() => loadRecommendationHistoryPage().then((module) => ({ default: module.RecommendationHistoryPage })));
const AskStockPage = lazy(() => loadAskStockPage().then((module) => ({ default: module.AskStockPage })));
const HoldingsPage = lazy(() => loadHoldingsPage().then((module) => ({ default: module.HoldingsPage })));
const LimitLadderPage = lazy(() => loadLimitLadderPage().then((module) => ({ default: module.LimitLadderPage })));
const ConceptPage = lazy(() => loadMarketGroupPage().then((module) => ({ default: () => <module.MarketGroupPage kind="concept" /> })));
const IndustryPage = lazy(() => loadMarketGroupPage().then((module) => ({ default: () => <module.MarketGroupPage kind="industry" /> })));

const PHONE_MODE_QUERY = "(max-width: 767px)";
const TABLET_MODE_QUERY = "(min-width: 768px) and (max-width: 1023px)";
type DeviceMode = "mobile" | "tablet" | "web";

const nav = [
  ["/decisions", "提醒", BellRing],
  ["/market", "大盘", Binoculars],
  ["/opportunities", "候选", Search],
  ["/history", "复盘", History],
  ["/stocks", "个股", Star],
  ["/ask", "问股", MessageSquareText],
  ["/holdings", "持仓", Briefcase],
  ["/limit-ladder", "连板", Flame],
  ["/concepts", "概念", Network],
  ["/industries", "行业", Layers3],
] as const;

const navGroups = [
  { label: "决策台", paths: ["/decisions", "/market", "/opportunities"] },
  { label: "研究", paths: ["/stocks", "/ask", "/holdings"] },
  { label: "市场结构", paths: ["/limit-ladder", "/concepts", "/industries"] },
  { label: "验证", paths: ["/history"] },
] as const;

const routeMeta: Record<string, { section: string; title: string; description: string }> = {
  "/decisions": { section: "决策台", title: "变化提醒", description: "只处理真正改变动作的信息" },
  "/market": { section: "决策台", title: "市场总览", description: "先判断环境，再选择研究方向" },
  "/opportunities": { section: "决策台", title: "候选策略", description: "用稳定策略筛选研究对象" },
  "/stocks": { section: "研究", title: "个股分析", description: "结论、证据、失效条件在同一页面" },
  "/ask": { section: "研究", title: "问股", description: "基于本地证据继续追问" },
  "/holdings": { section: "研究", title: "持仓", description: "只对当前账号的真实持仓给动作" },
  "/limit-ladder": { section: "市场结构", title: "连板梯队", description: "用原始价格验证涨跌停结构" },
  "/concepts": { section: "市场结构", title: "概念分析", description: "从主题热度下钻到股票证据" },
  "/industries": { section: "市场结构", title: "行业分析", description: "比较行业强弱与资金覆盖" },
  "/history": { section: "验证", title: "推荐复盘", description: "不回写历史，只用成熟样本验账" },
};

const routePreloads: Partial<Record<(typeof nav)[number][0], () => Promise<unknown>>> = {
  "/decisions": loadDecisionCenterPage,
  "/market": loadMarketPage,
  "/opportunities": loadOpportunitiesPage,
  "/history": loadRecommendationHistoryPage,
  "/stocks": loadStockLabPage,
  "/ask": loadAskStockPage,
  "/holdings": loadHoldingsPage,
  "/limit-ladder": loadLimitLadderPage,
  "/concepts": loadMarketGroupPage,
  "/industries": loadMarketGroupPage,
};

function preloadRoute(path: (typeof nav)[number][0]) {
  void routePreloads[path]?.();
}

function readDeviceMode(): DeviceMode {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return "web";
  if (window.matchMedia(PHONE_MODE_QUERY).matches) return "mobile";
  if (window.matchMedia(TABLET_MODE_QUERY).matches) return "tablet";
  return "web";
}

function useDeviceMode(): DeviceMode {
  const [deviceMode, setDeviceMode] = useState<DeviceMode>(() => readDeviceMode());

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return undefined;
    const phoneMedia = window.matchMedia(PHONE_MODE_QUERY);
    const tabletMedia = window.matchMedia(TABLET_MODE_QUERY);
    const sync = () => setDeviceMode(phoneMedia.matches ? "mobile" : tabletMedia.matches ? "tablet" : "web");
    sync();
    phoneMedia.addEventListener("change", sync);
    tabletMedia.addEventListener("change", sync);
    return () => {
      phoneMedia.removeEventListener("change", sync);
      tabletMedia.removeEventListener("change", sync);
    };
  }, []);

  useEffect(() => {
    document.documentElement.dataset.deviceMode = deviceMode;
    document.body.dataset.deviceMode = deviceMode;
    return () => {
      delete document.documentElement.dataset.deviceMode;
      delete document.body.dataset.deviceMode;
    };
  }, [deviceMode]);

  return deviceMode;
}

function AuthenticationPage({ onAuthenticated }: { onAuthenticated: (result: AuthResult) => void }) {
  const client = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const authenticate = useMutation({
    mutationFn: () => api<AuthResult>(mode === "register" ? "/api/v1/auth/register" : "/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        ...(mode === "register" ? { display_name: displayName || email.split("@", 1)[0] } : {}),
      }),
    }),
    onSuccess: (result) => {
      setAuthToken(result.access_token);
      client.clear();
      onAuthenticated(result);
    },
  });

  return (
    <main className="auth-screen" aria-label="账号登录">
      <section className="auth-intro">
        <div className="auth-brand"><span>MD</span><strong>StockTS</strong></div>
        <h1>登录 <span>StockTS</span></h1>
        <p>行情、个股分析、问股记录和持仓仅对当前账号开放。</p>
        <div className="auth-boundary-note"><strong>一人一套研究空间</strong><span>你的持仓、偏好和观察记录不会与其他账号共享。</span></div>
      </section>
      <form className="auth-form" onSubmit={(event) => { event.preventDefault(); authenticate.mutate(); }}>
        <header><span>{mode === "register" ? "创建个人账号" : "欢迎回来"}</span><small>进入你的投研空间</small></header>
        <div className="auth-tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册新账号</button>
        </div>
        <label>邮箱<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
        {mode === "register" ? <label>昵称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="nickname" /></label> : null}
        <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "register" ? "new-password" : "current-password"} required /></label>
        {authenticate.isError ? <p role="alert">账号或密码不可用，请检查后重试。</p> : null}
        <button className="button auth-submit" type="submit" disabled={authenticate.isPending}>{authenticate.isPending ? "验证中…" : mode === "register" ? "创建账号" : "进入"}</button>
        <small className="auth-disclaimer">研究辅助工具，不构成投资建议。</small>
      </form>
    </main>
  );
}


function useDebouncedValue(value: string, delay = 250) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delay);
    return () => window.clearTimeout(timer);
  }, [delay, value]);
  return debounced;
}

function CommandDock() {
  const navigate = useNavigate();
  const [draft, setDraft] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [recent, setRecent] = useState<RecentResearch[]>(() => loadRecentResearch());
  const inputRef = useRef<HTMLInputElement | null>(null);
  const query = draft.trim();
  const debouncedQuery = useDebouncedValue(query);
  const search = useQuery({
    queryKey: ["global-stock-search", debouncedQuery],
    queryFn: () => api<Quote[]>(`/api/v1/search?q=${encodeURIComponent(debouncedQuery)}`),
    enabled: debouncedQuery.length >= 2,
    staleTime: 30_000,
  });
  const results = Array.isArray(search.data) ? search.data.slice(0, 5) : [];
  const primary = results[0] ?? null;
  const askHref = `/ask?question=${encodeURIComponent(query || "最近大业股份怎么大跌")}`;

  useEffect(() => setActiveIndex(-1), [debouncedQuery]);

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setExpanded(true);
        setActiveIndex(-1);
      }
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, []);

  const openStock = (stock: Pick<Quote, "symbol" | "name" | "sector">) => {
    setRecent(rememberRecentResearch(stock));
    setExpanded(false);
    setActiveIndex(-1);
    setDraft("");
    navigate(`/stocks?symbol=${encodeURIComponent(stock.symbol)}#stock-final-gate`);
  };

  const closePanel = () => {
    setExpanded(false);
    setActiveIndex(-1);
    inputRef.current?.blur();
  };

  const handleInputKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      event.preventDefault();
      closePanel();
      return;
    }
    if (event.key === "Enter" && activeIndex >= 0 && results[activeIndex]) {
      event.preventDefault();
      openStock(results[activeIndex]);
      return;
    }
    if (!results.length || (event.key !== "ArrowDown" && event.key !== "ArrowUp")) return;
    event.preventDefault();
    setExpanded(true);
    setActiveIndex((current) => {
      if (event.key === "ArrowDown") return current >= results.length - 1 ? 0 : current + 1;
      return current <= 0 ? results.length - 1 : current - 1;
    });
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (primary) {
      openStock(primary);
      return;
    }
    if (query) navigate(`/ask?question=${encodeURIComponent(query)}`);
  };

  return (
    <form
      className="command-dock"
      role="search"
      aria-label="全局股票搜索"
      onSubmit={submit}
      onFocus={() => { setRecent(loadRecentResearch()); setExpanded(true); }}
      onBlur={() => window.setTimeout(() => setExpanded(false), 120)}
    >
      <Search size={15} />
      <input
        ref={inputRef}
        type="search"
        value={draft}
        onChange={(event) => { setDraft(event.target.value); setExpanded(true); }}
        onKeyDown={handleInputKeyDown}
        placeholder="搜股票 / 直接问股"
        aria-label="搜索股票或输入问题"
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={expanded}
        aria-controls={query.length >= 2 ? "command-result-list" : "command-panel"}
        aria-activedescendant={activeIndex >= 0 ? `command-result-${activeIndex}` : undefined}
      />
      <span>⌘K</span>
      {expanded ? <div className="command-panel" id="command-panel">
        <div className="command-panel-head">
          <div><strong>搜索</strong><small>{query.length >= 2 ? "方向键选择，回车打开个股" : "输入名称或 6 位代码"}</small></div>
          <button type="button" className="command-close" aria-label="关闭搜索面板" onMouseDown={(event) => event.preventDefault()} onClick={closePanel}><X size={15} /></button>
        </div>
        {query.length >= 2 ? <div className="command-results" id="command-result-list" role="listbox" aria-label="股票搜索结果">
          {search.isLoading ? <p>正在搜索股票…</p> : null}
          {!search.isLoading && results.length === 0 ? <p>没找到股票，可以把这句话交给问股。</p> : null}
          {results.map((item, index) => (
            <button
              type="button"
              role="option"
              id={`command-result-${index}`}
              aria-selected={activeIndex === index}
              className={activeIndex === index ? "active" : ""}
              key={item.symbol}
              onMouseEnter={() => setActiveIndex(index)}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => openStock(item)}
            >
              <b>{item.name}</b>
              <span>{item.symbol}</span>
              <small>{item.sector ?? "未标注板块"}</small>
            </button>
          ))}
        </div> : <div className="command-zero-state">
          {recent.length ? <section aria-label="最近研究">
            <div><strong>最近决定</strong><small>历史研究记录</small></div>
            {recent.slice(0, 4).map((item) => <article key={item.symbol}>
              <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => openStock(item)}>
                <b>{item.name}</b><span>{item.symbol}</span><small>{item.sector ?? "未标注板块"}</small>
              </button>
              <Link to={`/ask?symbol=${encodeURIComponent(item.symbol)}&name=${encodeURIComponent(item.name)}&question=${encodeURIComponent(`${item.name}现在能不能买，直接给我结论`)}`}>现在能不能买</Link>
              <Link to={`/ask?symbol=${encodeURIComponent(item.symbol)}&name=${encodeURIComponent(item.name)}&question=${encodeURIComponent(`如果已经持有${item.name}，现在怎么处理`)}`}>已经持有怎么办</Link>
            </article>)}
          </section> : null}
          <div className="command-shortcuts">
            <Link to="/market#market-board-zone">板块热度</Link>
            <Link to="/opportunities">候选决策</Link>
            <Link to="/holdings">持仓风险</Link>
          </div>
        </div>}
        <div className="command-actions">
          {primary ? <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => openStock(primary)}>查看 {primary.name} 决定</button> : null}
          <Link to={askHref}>直接给我决定</Link>
        </div>
      </div> : null}
    </form>
  );
}

function AccountPanel({ user, onLogout }: { user: UserAccount; onLogout: () => void }) {
  const client = useQueryClient();
  const menuRef = useRef<HTMLDetailsElement | null>(null);
  const summaryRef = useRef<HTMLElement | null>(null);
  const preferences = useQuery({
    queryKey: ["preferences", user.id],
    queryFn: () => api<UserPreferences>("/api/v1/preferences"),
  });
  const updatePreferences = useMutation({
    mutationFn: (risk_profile: string) => api<UserPreferences>("/api/v1/preferences", {
      method: "PATCH",
      body: JSON.stringify({ risk_profile }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["preferences", user?.id] }),
  });

  useEffect(() => {
    const close = (restoreFocus = false) => {
      if (!menuRef.current?.open) return;
      menuRef.current.open = false;
      if (restoreFocus) summaryRef.current?.focus();
    };
    const handlePointerDown = (event: PointerEvent) => {
      if (!menuRef.current?.contains(event.target as Node)) close();
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") close(true);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  return (
    <div className="account-box">
      <details className="account-menu" ref={menuRef}>
        <summary ref={summaryRef} aria-label={`账户：${user.display_name}`}><UserRound size={15} /><span>{user.display_name}</span></summary>
        <div className="account-popover">
          <strong>{user.email}</strong>
          <label>风险偏好
            <select
              value={preferences.data?.risk_profile ?? "balanced"}
              onChange={(event) => updatePreferences.mutate(event.target.value)}
            >
              <option value="defensive">防守</option>
              <option value="balanced">均衡</option>
              <option value="active">积极</option>
            </select>
          </label>
          <small>持仓和偏好只保存在当前账号下。</small>
          <button type="button" onClick={onLogout}>退出账号</button>
        </div>
      </details>
    </div>
  );
}

function RouteFallback() {
  return <div className="route-loading" role="status"><div className="loader" /><span>正在打开页面…</span></div>;
}

function Shell({ user, onLogout }: { user: UserAccount; onLogout: () => void }) {
  const client = useQueryClient();
  const location = useLocation();
  const deviceMode = useDeviceMode();
  const [railCollapsed, setRailCollapsed] = useState(() => window.localStorage.getItem("stockts:rail") === "compact");
  const [currentStock, setCurrentStock] = useState<RecentResearch | null>(() => loadRecentResearch()[0] ?? null);
  const [refreshNotice, setRefreshNotice] = useState<{ kind: "success" | "error"; message: string } | null>(null);
  const decisions = useQuery({
    queryKey: ["decision-events"],
    queryFn: () => api<DecisionEventFeed>("/api/v1/decision-events"),
    staleTime: 60_000,
    refetchOnWindowFocus: true,
  });
  const refresh = useMutation({
    mutationFn: () => api<RefreshResult>("/api/v1/refresh", { method: "POST" }),
    onMutate: () => setRefreshNotice(null),
    onSuccess: async (result) => {
      await client.invalidateQueries();
      const refreshedAt = new Date(result.meta.fetched_at).toLocaleString("zh-CN", { hour12: false });
      setRefreshNotice({ kind: "success", message: `全站数据已同步 · 更新于 ${refreshedAt}` });
    },
    onError: () => setRefreshNotice({ kind: "error", message: "刷新失败，请稍后重试" }),
  });

  useEffect(() => {
    if (!refreshNotice) return undefined;
    const timer = window.setTimeout(() => setRefreshNotice(null), 3_200);
    return () => window.clearTimeout(timer);
  }, [refreshNotice]);

  useEffect(() => {
    const updateCurrentStock = (event: Event) => {
      const stock = (event as CustomEvent<RecentResearch>).detail;
      setCurrentStock(stock ?? loadRecentResearch()[0] ?? null);
    };
    window.addEventListener(recentResearchUpdatedEvent, updateCurrentStock);
    return () => window.removeEventListener(recentResearchUpdatedEvent, updateCurrentStock);
  }, []);

  useEffect(() => {
    window.localStorage.setItem("stockts:rail", railCollapsed ? "compact" : "full");
  }, [railCollapsed]);

  useEffect(() => {
    if (deviceMode !== "mobile") return undefined;
    const frame = window.requestAnimationFrame(() => {
      const activeRoute = document.querySelector<HTMLElement>("#primary-navigation a.active");
      if (typeof activeRoute?.scrollIntoView !== "function") return;
      activeRoute.scrollIntoView({
        behavior: "auto",
        block: "nearest",
        inline: "center",
      });
    });
    return () => window.cancelAnimationFrame(frame);
  }, [deviceMode, location.pathname]);

  const currentRoute = routeMeta[location.pathname] ?? routeMeta["/market"];
  const hasLocalResearchInput = location.pathname === "/stocks" || location.pathname === "/ask";

  return (
    <div className={`app-shell ${deviceMode}-shell ${railCollapsed ? "rail-collapsed" : ""}`} data-device-mode={deviceMode}>
      <a className="skip-link" href="#main">跳到主要内容</a>
      <aside className="sidebar">
        <div className="brand">
          <span aria-hidden="true"><i />MD</span>
          <div>
            <strong>StockTS</strong>
            <small>QUANT · WORKBENCH</small>
          </div>
          <button type="button" className="rail-toggle" onClick={() => setRailCollapsed((value) => !value)} aria-controls="primary-navigation" aria-expanded={!railCollapsed} aria-label={railCollapsed ? "展开侧边栏" : "收起侧边栏"} title={railCollapsed ? "展开侧边栏" : "收起侧边栏"}>{railCollapsed ? <PanelLeftOpen size={15} /> : <PanelLeftClose size={15} />}</button>
        </div>
        <nav id="primary-navigation" aria-label="主导航">
          {navGroups.map((group) => <section className="nav-group" key={group.label} aria-label={group.label}>
            <span className="nav-group-label">{group.label}</span>
            {group.paths.map((path) => {
              const item = nav.find(([itemPath]) => itemPath === path)!;
              const [, label, Icon] = item;
              return <NavLink
                key={path}
                to={path === "/stocks" && currentStock
                  ? `/stocks?symbol=${encodeURIComponent(currentStock.symbol)}`
                  : path}
                end={path === "/market"}
                title={path === "/stocks" && currentStock ? `打开 ${currentStock.name} 个股分析` : label}
                onFocus={() => preloadRoute(path)}
                onPointerEnter={() => preloadRoute(path)}
              >
                <Icon size={18} />
                <span>{label}</span>
                {path === "/decisions" && (decisions.data?.unread_count ?? 0) > 0
                  ? <b className="nav-unread" aria-label={`${decisions.data?.unread_count} 条未读提醒`}>{decisions.data!.unread_count > 99 ? "99+" : decisions.data!.unread_count}</b>
                  : null}
              </NavLink>;
            })}
          </section>)}
        </nav>
        <div className="sidebar-foot">
          <div><i className={decisions.isError ? "error" : decisions.isPending ? "" : "online"} /><span>提醒服务</span><strong>{decisions.isError ? "待恢复" : decisions.isPending ? "连接中" : "已连接"}</strong></div>
          <div><i /><span>决策监控</span><strong>10 分钟</strong></div>
          <p>研究辅助 · 不构成投资建议</p>
        </div>
      </aside>
      <main id="main">
        <div className="topbar">
          <div className="topbar-left">
            <div className="workspace-context"><span>{currentRoute.section}</span><strong>{currentRoute.title}</strong><small>{currentRoute.description}</small></div>
            {!hasLocalResearchInput ? <CommandDock /> : null}
          </div>
          <div className="topbar-actions">
            {refreshNotice ? <div className={`refresh-notice ${refreshNotice.kind}`} role={refreshNotice.kind === "error" ? "alert" : "status"} aria-live={refreshNotice.kind === "error" ? "assertive" : "polite"}><i />{refreshNotice.message}</div> : null}
            <AccountPanel user={user} onLogout={onLogout} />
            <button className="refresh-button" aria-label={refresh.isPending ? "刷新中" : "刷新"} title={refresh.isPending ? "正在刷新数据" : "刷新全部数据"} onClick={() => refresh.mutate()} disabled={refresh.isPending}>
              <RefreshCw size={15} className={refresh.isPending ? "spin" : ""} />
              {refresh.isPending ? "刷新中" : "刷新"}
            </button>
          </div>
        </div>
        <div className="page-wrap">
          <div className="route-stage" key={location.pathname}>
            <Suspense fallback={<RouteFallback />}>
              <Routes>
              <Route path="/" element={<Navigate to="/market" replace />} />
              <Route path="/market" element={<MarketPage />} />
              <Route path="/decisions" element={<DecisionCenterPage />} />
              <Route path="/opportunities" element={<OpportunitiesPage />} />
              <Route path="/history" element={<RecommendationHistoryPage />} />
              <Route path="/stocks" element={<StockLabPage />} />
              <Route path="/ask" element={<AskStockPage />} />
              <Route path="/holdings" element={<HoldingsPage />} />
              <Route path="/limit-ladder" element={<LimitLadderPage />} />
              <Route path="/concepts" element={<ConceptPage />} />
              <Route path="/industries" element={<IndustryPage />} />
              <Route path="*" element={<Navigate to="/market" replace />} />
              </Routes>
            </Suspense>
          </div>
        </div>
      </main>
    </div>
  );
}

function SessionGate() {
  const client = useQueryClient();
  const [token, setToken] = useState<string | null>(() => getAuthToken());
  const [sessionUser, setSessionUser] = useState<UserAccount | null>(null);
  const me = useQuery({
    queryKey: ["auth-me", token],
    queryFn: () => api<UserAccount>("/api/v1/auth/me"),
    enabled: Boolean(token) && !sessionUser,
    retry: false,
  });
  const user = sessionUser ?? me.data ?? null;

  useEffect(() => {
    if (!me.isError) return;
    clearAuthToken();
    setToken(null);
    setSessionUser(null);
    client.clear();
  }, [client, me.isError]);

  const authenticated = (result: AuthResult) => {
    setToken(result.access_token);
    setSessionUser(result.user);
  };
  const logout = () => {
    api("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    clearAuthToken();
    setToken(null);
    setSessionUser(null);
    client.clear();
  };

  if (!token) return <AuthenticationPage onAuthenticated={authenticated} />;
  if (!user) return <main className="auth-screen auth-loading" aria-label="验证登录状态"><div className="loader" /><span>正在验证登录状态…</span></main>;
  return <Shell user={user} onLogout={logout} />;
}

export function App() {
  const [appQueryClient] = useState(createQueryClient);
  return (
    <QueryClientProvider client={appQueryClient}>
      <HashRouter>
        <SessionGate />
      </HashRouter>
    </QueryClientProvider>
  );
}
