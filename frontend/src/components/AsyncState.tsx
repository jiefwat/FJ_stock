import type { ReactNode } from "react";

export function AsyncState({ loading, error, children, onRetry, loadingText = "正在核对市场数据…" }: { loading: boolean; error: Error | null; children: ReactNode; onRetry?: () => void; loadingText?: string }) {
  if (loading) return <div className="state-panel" role="status"><span className="loader" />{loadingText}</div>;
  if (error) return <div className="state-panel error" role="alert"><strong>数据暂时不可用</strong><span>{error.message}</span>{onRetry ? <button type="button" className="button secondary" onClick={onRetry}>重新加载</button> : <small>可在数据中心重试。</small>}</div>;
  return <>{children}</>;
}
