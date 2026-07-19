import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";

import { api, percent, type Meta } from "../../lib/api";

type Status = {
  providers: Record<string, { status: string; required: boolean; description?: string; error?: string }>;
  snapshot: Meta | null;
};
type RefreshResult = { status: string; meta: Meta };

const freshnessLabel: Record<string, string> = {
  fresh: "实时快照",
  delayed: "延迟快照",
  stale: "缓存快照",
  unavailable: "不可用",
};
const providerLabel: Record<string, string> = {
  eastmoney_fund_flow: "资金流增强",
  semantic_research: "语义研究增强",
  sina: "核心行情",
  tencent: "指数与历史行情",
};

function time(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export function DataCenterPage() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["data-status"], queryFn: () => api<Status>("/api/v1/data-status") });
  const refresh = useMutation({
    mutationFn: () => api<RefreshResult>("/api/v1/refresh", { method: "POST" }),
    onSuccess: () => client.invalidateQueries(),
  });
  const snapshot = query.data?.snapshot;

  return <>
    <header className="page-head"><div><p className="eyebrow">DATA CENTER / 数据审计</p><h1>先知道数据状态，<br /><em>再相信分析结果。</em></h1></div><button className="button" onClick={() => refresh.mutate()} disabled={refresh.isPending}><RefreshCw size={16} />{refresh.isPending ? "刷新中…" : "刷新核心数据"}</button></header>
    {refresh.isSuccess && <p className="refresh-result" role="status">刷新完成 · 抓取时间 {time(refresh.data.meta.fetched_at)}</p>}
    {refresh.isError && <p className="refresh-result error" role="alert">刷新失败，已保留上一份有效快照，请稍后重试。</p>}
    <section className="provider-grid">{query.data && Object.entries(query.data.providers).map(([name, provider]) => <article key={name}><span className={`provider-status ${provider.status}`} /><div><strong>{providerLabel[name] ?? name}</strong><small>{provider.description ?? (provider.required ? "核心数据源" : "可选增强")}{provider.error ? ` · ${provider.error}` : ""}</small></div><b>{provider.status.replaceAll("_", " ")}</b></article>)}</section>
    {snapshot && <section className="audit-grid">
      <article><span>数据时间</span><strong>{time(snapshot.observed_at)}</strong><small>行情所代表的市场时点</small></article>
      <article><span>抓取时间</span><strong>{time(snapshot.fetched_at)}</strong><small>本地最后成功获取时间</small></article>
      <article><span>新鲜度</span><strong>{freshnessLabel[snapshot.freshness] ?? snapshot.freshness}</strong><small>{snapshot.freshness === "stale" ? "正在使用缓存" : "状态来自标准化契约"}</small></article>
      <article><span>字段覆盖</span><strong>{percent(snapshot.coverage * 100, 1)}</strong><small>核心字段非空比例</small></article>
    </section>}
    <section className="panel data-note"><h3>覆盖与降级规则</h3><p>行情失败时使用最后一次有效快照并标记为 stale；没有快照时显示不可用，不把空值当作 0。</p><p>语义研究增强未配置不会影响核心行情、机会漏斗、个股价格和观察清单。配置后可增强财务、公告、研报与行业信息。</p>{snapshot?.errors.length ? <div className="provider-errors"><strong>最近错误</strong>{snapshot.errors.map((error) => <p key={error}>{error}</p>)}</div> : <p className="positive">当前快照没有标准化错误。</p>}</section>
  </>;
}
