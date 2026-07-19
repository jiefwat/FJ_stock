import type { ReactNode } from "react";

export function AsyncState({ loading, error, children }: { loading: boolean; error: Error | null; children: ReactNode }) {
  if (loading) return <div className="state-panel" role="status"><span className="loader" />正在核对市场数据…</div>;
  if (error) return <div className="state-panel error" role="alert"><strong>数据暂时不可用</strong><span>{error.message}。请在数据中心重试。</span></div>;
  return <>{children}</>;
}
