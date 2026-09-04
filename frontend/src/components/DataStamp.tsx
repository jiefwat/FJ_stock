import type { Meta } from "../lib/api";
import { formatMarketDateTime } from "../lib/marketTime";

export function DataStamp({ meta }: { meta: Meta }) {
  const observed = formatMarketDateTime(meta.observed_at);
  const fetched = formatMarketDateTime(meta.fetched_at);
  return <button
    className={`data-stamp ${meta.freshness}`}
    title={`来源 ${meta.source} · 覆盖率 ${(meta.coverage * 100).toFixed(0)}% · 行情截至 ${observed} · 刷新于 ${fetched}`}
  >
    <span className="status-dot" />
    <span>行情截至 {observed}</span>
    <span>·</span>
    <span>刷新于 {fetched}</span>
  </button>;
}
