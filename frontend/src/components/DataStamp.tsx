import type { Meta } from "../lib/api";

export function DataStamp({ meta }: { meta: Meta }) {
  return <button className={`data-stamp ${meta.freshness}`} title={`来源 ${meta.source} · 覆盖率 ${(meta.coverage * 100).toFixed(0)}%`}>
    <span className="status-dot" /> 数据时间 {new Date(meta.observed_at).toLocaleString("zh-CN", { hour12: false })}
  </button>;
}
