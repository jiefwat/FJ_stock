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

function AuthPanel() {
  const client = useQueryClient();
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [sessionUser, setSessionUser] = useState<UserAccount | null>(null);
  const [tokenVersion, setTokenVersion] = useState(0);
  const hasToken = Boolean(getAuthToken());
  const me = useQuery({
    queryKey: ["auth-me", tokenVersion],
    queryFn: () => api<UserAccount>("/api/v1/auth/me"),
    enabled: hasToken,
    retry: false,
  });
  const user = sessionUser ?? me.data ?? null;
  const preferences = useQuery({
    queryKey: ["preferences", user?.id],
    queryFn: () => api<UserPreferences>("/api/v1/preferences"),
    enabled: Boolean(user),
  });
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
      setSessionUser(result.user);
      setOpen(false);
      setTokenVersion((value) => value + 1);
      client.invalidateQueries();
    },
  });
  const updatePreferences = useMutation({
    mutationFn: (risk_profile: string) => api<UserPreferences>("/api/v1/preferences", {
      method: "PATCH",
      body: JSON.stringify({ risk_profile }),
    }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["preferences", user?.id] }),
  });
  const logout = () => {
    api("/api/v1/auth/logout", { method: "POST" }).catch(() => undefined);
    clearAuthToken();
    setSessionUser(null);
    setTokenVersion((value) => value + 1);
    client.clear();
  };

  useEffect(() => {
    if (me.data) setSessionUser(me.data);
    if (me.isError) clearAuthToken();
  }, [me.data, me.isError]);

  return (
    <div className="account-box">
      {user ? (
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
            <button type="button" onClick={logout}>退出账号</button>
          </div>
        </details>
      ) : (
        <button className="account-trigger" type="button" onClick={() => setOpen(true)}>注册/登录</button>
      )}
      {open && (
        <div className="auth-dialog" role="dialog" aria-label="账号登录">
          <form onSubmit={(event) => { event.preventDefault(); authenticate.mutate(); }}>
            <header>
              <strong>{mode === "register" ? "创建个人账号" : "登录账号"}</strong>
              <button type="button" aria-label="关闭账号窗口" onClick={() => setOpen(false)}>×</button>
            </header>
            <div className="auth-tabs">
              <button type="button" className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>登录</button>
              <button type="button" className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>注册新账号</button>
            </div>
            <label>邮箱<input value={email} onChange={(event) => setEmail(event.target.value)} /></label>
            {mode === "register" && <label>昵称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>}
            <label>密码<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
            {authenticate.isError && <p role="alert">账号或密码不可用，请检查后重试。</p>}
            <button className="button" type="submit" disabled={authenticate.isPending}>{mode === "register" ? "创建账号" : "登录"}</button>
          </form>
        </div>
      )}
    </div>
  );
}

function Shell() {
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
            <AuthPanel />
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

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <HashRouter>
        <Shell />
      </HashRouter>
    </QueryClientProvider>
  );
}
