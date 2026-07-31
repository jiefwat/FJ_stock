import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Binoculars, Briefcase, MessageSquareText, RefreshCw, Search, Star, UserRound } from "lucide-react";
import { type FormEvent, useEffect, useRef, useState } from "react";
import { HashRouter, Link, NavLink, Route, Routes, useNavigate } from "react-router-dom";
import { AskStockPage } from "../features/ask/AskStockPage";
import { HoldingsPage } from "../features/holdings/HoldingsPage";
import { MarketPage } from "../features/market/MarketPage";
import { OpportunitiesPage } from "../features/opportunities/OpportunitiesPage";
import { StockLabPage } from "../features/stocks/StockLabPage";
import { TodayPage } from "../features/today/TodayPage";
import { loadRecentResearch, rememberRecentResearch, type RecentResearch } from "../lib/recentResearch";
import {
  api,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  type AuthResult,
  type UserAccount,
  type UserPreferences,
  type Quote,
} from "../lib/api";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } });
const nav = [
  ["/", "今日", Activity],
  ["/market", "大盘", Binoculars],
  ["/opportunities", "机会", Search],
  ["/stocks", "个股", Star],
  ["/ask", "问股", MessageSquareText],
  ["/holdings", "持仓", Briefcase],
] as const;

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


function CommandDock() {
  const navigate = useNavigate();
  const [draft, setDraft] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [recent, setRecent] = useState<RecentResearch[]>(() => loadRecentResearch());
  const inputRef = useRef<HTMLInputElement | null>(null);
  const query = draft.trim();
  const search = useQuery({
    queryKey: ["global-stock-search", query],
    queryFn: () => api<Quote[]>(`/api/v1/search?q=${encodeURIComponent(query)}`),
    enabled: query.length >= 2,
    staleTime: 30_000,
  });
  const results = Array.isArray(search.data) ? search.data.slice(0, 5) : [];
  const primary = results[0] ?? null;
  const askHref = `/ask?question=${encodeURIComponent(query || "最近大业股份怎么大跌")}`;

  useEffect(() => {
    const handleKeydown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        setExpanded(true);
      }
    };
    window.addEventListener("keydown", handleKeydown);
    return () => window.removeEventListener("keydown", handleKeydown);
  }, []);

  const openStock = (stock: Pick<Quote, "symbol" | "name" | "sector">) => {
    setRecent(rememberRecentResearch(stock));
    setExpanded(false);
    setDraft("");
    navigate(`/stocks?symbol=${encodeURIComponent(stock.symbol)}#stock-final-gate`);
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
        placeholder="搜股票 / 直接问股"
        aria-label="搜索股票或输入问题"
      />
      <span>⌘K</span>
      {expanded ? <div className="command-panel">
        <div className="command-panel-head">
          <strong>搜索</strong>
          <small>{query.length >= 2 ? "打开个股，或直接问股" : "输入名称或 6 位代码"}</small>
        </div>
        {query.length >= 2 ? <div className="command-results">
          {search.isLoading ? <p>正在搜索股票…</p> : null}
          {!search.isLoading && results.length === 0 ? <p>没找到股票，可以把这句话交给问股。</p> : null}
          {results.map((item) => (
            <button type="button" key={item.symbol} onMouseDown={(event) => event.preventDefault()} onClick={() => openStock(item)}>
              <b>{item.name}</b>
              <span>{item.symbol}</span>
              <small>{item.sector ?? "未标注板块"}</small>
            </button>
          ))}
        </div> : <div className="command-zero-state">
          {recent.length ? <section aria-label="最近研究">
            <div><strong>最近研究</strong><small>打开个股或问风险。</small></div>
            {recent.slice(0, 4).map((item) => <article key={item.symbol}>
              <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => openStock(item)}>
                <b>{item.name}</b><span>{item.symbol}</span><small>{item.sector ?? "未标注板块"}</small>
              </button>
              <Link to={`/ask?symbol=${encodeURIComponent(item.symbol)}&name=${encodeURIComponent(item.name)}&question=${encodeURIComponent(`${item.name}现在主要风险是什么`)}`}>问风险</Link>
              <Link to={`/ask?symbol=${encodeURIComponent(item.symbol)}&name=${encodeURIComponent(item.name)}&question=${encodeURIComponent(`最近${item.name}怎么大跌`)}`}>问异动</Link>
            </article>)}
          </section> : null}
          <div className="command-shortcuts">
            <Link to="/market#market-board-zone">板块热度</Link>
            <Link to="/opportunities">机会</Link>
            <Link to="/holdings">持仓风险</Link>
          </div>
        </div>}
        <div className="command-actions">
          {primary ? <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => openStock(primary)}>打开 {primary.name} 研究</button> : null}
          <Link to={askHref}>交给问股判断</Link>
        </div>
      </div> : null}
    </form>
  );
}

function AccountPanel({ user, onLogout }: { user: UserAccount; onLogout: () => void }) {
  const client = useQueryClient();
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

  return (
    <div className="account-box">
      <details className="account-menu">
        <summary><UserRound size={15} /><span>{user.display_name}</span></summary>
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

function Shell({ user, onLogout }: { user: UserAccount; onLogout: () => void }) {
  const client = useQueryClient();
  const refresh = useMutation({
    mutationFn: () => api("/api/v1/refresh", { method: "POST" }),
    onSuccess: () => client.invalidateQueries(),
  });

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">跳到主要内容</a>
      <aside className="sidebar">
        <div className="brand">
          <span>MD</span>
          <div>
            <strong>StockTS</strong>
            <small>A股投研</small>
          </div>
        </div>
        <nav aria-label="主导航">
          {nav.map(([path, label, Icon]) => (
            <NavLink key={path} to={path} end={path === "/"}>
              <Icon size={18} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <p>研究辅助工具</p>
          <span>不构成投资建议</span>
        </div>
      </aside>
      <main id="main">
        <div className="topbar">
          <div className="topbar-left"><div className="session"><i />A 股 · 最近交易快照</div><CommandDock /></div>
          <div className="topbar-actions">
            <AccountPanel user={user} onLogout={onLogout} />
            <button className="refresh-button" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
              <RefreshCw size={15} className={refresh.isPending ? "spin" : ""} />
              {refresh.isPending ? "刷新中" : "刷新"}
            </button>
          </div>
        </div>
        <div className="page-wrap">
          <Routes>
            <Route path="/" element={<TodayPage />} />
            <Route path="/market" element={<MarketPage />} />
            <Route path="/opportunities" element={<OpportunitiesPage />} />
            <Route path="/stocks" element={<StockLabPage />} />
            <Route path="/ask" element={<AskStockPage />} />
            <Route path="/holdings" element={<HoldingsPage />} />
          </Routes>
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
    enabled: Boolean(token),
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
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <SessionGate />
      </HashRouter>
    </QueryClientProvider>
  );
}
