import type { ReactNode } from "react";

export function AsyncState({ loading, error, children, onRetry, loadingText = "正在核对市场数据…" }: { loading: boolean; error: Error | null; children: ReactNode; onRetry?: () => void; loadingText?: string }) {
  if (loading) return <div className="state-panel state-loading" role="status">
    <div className="state-skeleton" aria-hidden="true"><i /><i /><i /><i /></div>
    <div><span className="loader" /><strong>{loadingText}</strong><small>页面仍可切换，数据回来后会自动显示</small></div>
  </div>;
  if (error) return <div className="state-panel error" role="alert"><strong>这部分数据暂时不可用</strong><span>{error.message}</span>{onRetry ? <button type="button" className="button secondary" onClick={onRetry}>重新加载</button> : <small>其他页面和上次有效数据不受影响。</small>}</div>;
  return <>{children}</>;
}
