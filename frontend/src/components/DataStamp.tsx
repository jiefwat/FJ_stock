import type { Meta } from "../lib/api";

function time(value: string) {
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export function DataStamp({ meta }: { meta: Meta }) {
  const observed = time(meta.observed_at);
  const fetched = time(meta.fetched_at);
  return <button
    className={`data-stamp ${meta.freshness}`}
    title={`来源 ${meta.source} · 覆盖率 ${(meta.coverage * 100).toFixed(0)}% · 行情时间 ${observed} · 更新时间 ${fetched}`}
  >
    <span className="status-dot" />
    <span>行情时间 {observed}</span>
    <span>·</span>
    <span>更新 {fetched}</span>
  </button>;
}
