import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Activity, Binoculars, Briefcase, Database, RefreshCw, Search, Star, UserRound } from "lucide-react";
import { useEffect, useState } from "react";
import { HashRouter, NavLink, Route, Routes } from "react-router-dom";
import { DataCenterPage } from "../features/data/DataCenterPage";
import { HoldingsPage } from "../features/holdings/HoldingsPage";
import { MarketPage } from "../features/market/MarketPage";
import { OpportunitiesPage } from "../features/opportunities/OpportunitiesPage";
import { StockLabPage } from "../features/stocks/StockLabPage";
import { TodayPage } from "../features/today/TodayPage";
import { WatchlistPage } from "../features/watchlist/WatchlistPage";
import {
  api,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
  type AuthResult,
  type UserAccount,
  type UserPreferences,
} from "../lib/api";

const queryClient = new QueryClient({ defaultOptions: { queries: { staleTime: 60_000, retry: 1 } } });
const nav = [
  ["/", "今日", Activity],
  ["/market", "大盘", Binoculars],
  ["/opportunities", "机会", Search],
  ["/stocks", "个股", Star],
  ["/holdings", "持仓", Briefcase],
  ["/watchlist", "跟踪", Star],
  ["/data", "数据", Database],
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
        <div className="auth-brand"><span>MD</span><strong>MARKET DESK</strong></div>
        <p className="eyebrow">PRIVATE RESEARCH WORKSPACE</p>
        <h1>登录 <span>Market Desk</span></h1>
        <p>行情、个股分析、持仓与跟踪记录仅对当前账号开放。登录前不会加载任何市场或个人数据。</p>
        <div className="auth-boundary-note"><strong>一人一套研究空间</strong><span>你的持仓、偏好和观察记录不会与其他账号共享。</span></div>
      </section>
      <form className="auth-form" onSubmit={(event) => { event.preventDefault(); authenticate.mutate(); }}>
        <header><span>{mode === "register" ? "创建个人账号" : "欢迎回来"}</span><small>使用你的账号进入工作台</small></header>
        <div className="auth-tabs">
          <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button>
          <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册新账号</button>
        </div>
        <label>邮箱<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>
        {mode === "register" ? <label>昵称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="nickname" /></label> : null}
        <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === "register" ? "new-password" : "current-password"} required /></label>
        {authenticate.isError ? <p role="alert">账号或密码不可用，请检查后重试。</p> : null}
        <button className="button auth-submit" type="submit" disabled={authenticate.isPending}>{authenticate.isPending ? "验证中…" : mode === "register" ? "创建账号" : "进入工作台"}</button>
        <small className="auth-disclaimer">研究辅助工具，不构成投资建议。</small>
      </form>
    </main>
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
          <small>持仓、跟踪池和偏好只保存在当前账号下。</small>
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
            <strong>MARKET DESK</strong>
            <small>本地投研工作台</small>
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
          <div className="session"><i />A 股 · 最近交易快照</div>
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
            <Route path="/holdings" element={<HoldingsPage />} />
            <Route path="/watchlist" element={<WatchlistPage />} />
            <Route path="/data" element={<DataCenterPage />} />
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
