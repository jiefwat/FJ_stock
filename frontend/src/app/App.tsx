import { QueryClient, QueryClientProvider, useMutation, useQueryClient } from "@tanstack/react-query";
import { Activity, Binoculars, Briefcase, Database, RefreshCw, Search, Star } from "lucide-react";
import { HashRouter, NavLink, Route, Routes } from "react-router-dom";
import { DataCenterPage } from "../features/data/DataCenterPage";
import { HoldingsPage } from "../features/holdings/HoldingsPage";
import { MarketPage } from "../features/market/MarketPage";
import { OpportunitiesPage } from "../features/opportunities/OpportunitiesPage";
import { StockLabPage } from "../features/stocks/StockLabPage";
import { TodayPage } from "../features/today/TodayPage";
import { WatchlistPage } from "../features/watchlist/WatchlistPage";
import { api } from "../lib/api";

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
          <button className="refresh-button" onClick={() => refresh.mutate()} disabled={refresh.isPending}>
            <RefreshCw size={15} className={refresh.isPending ? "spin" : ""} />
            {refresh.isPending ? "刷新中" : "刷新"}
          </button>
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
