import { fmt, pct } from "../../lib/api";

type PriceBar = {
  date: string;
  open?: number;
  high?: number;
  low?: number;
  close: number;
  volume?: number;
};
type TrendMarker = { date: string; label: string };
type StockTrendProps = { bars: PriceBar[]; marker?: TrendMarker; compact?: boolean };
type Series = { key: string; label: string; values: Array<number | null> };
type ChartPoint = { x: number; y: number };
type NormalizedBar = Required<Pick<PriceBar, "date" | "open" | "high" | "low" | "close">> & { volume: number };

const WIDTH = 960;
const HEIGHT = 320;
const PAD_X = 34;
const PAD_TOP = 18;
const PRICE_HEIGHT = 214;
const VOLUME_TOP = 252;
const VOLUME_HEIGHT = 48;

function movingAverage(values: number[], size: number): Array<number | null> {
  return values.map((_, index) => {
    if (index + 1 < size) return null;
    return values.slice(index + 1 - size, index + 1).reduce((sum, value) => sum + value, 0) / size;
  });
}

function normalizeBars(bars: PriceBar[]): NormalizedBar[] {
  return bars.flatMap((bar) => {
    if (!Number.isFinite(bar.close)) return [];
    const open = Number.isFinite(bar.open) ? bar.open! : bar.close;
    const high = Number.isFinite(bar.high) ? Math.max(bar.high!, open, bar.close) : Math.max(open, bar.close);
    const low = Number.isFinite(bar.low) ? Math.min(bar.low!, open, bar.close) : Math.min(open, bar.close);
    return [{
      date: bar.date,
      open,
      high,
      low,
      close: bar.close,
      volume: Number.isFinite(bar.volume) ? bar.volume! : 0,
    }];
  });
}

function toPoint(value: number, index: number, total: number, low: number, range: number): ChartPoint {
  return {
    x: PAD_X + (index / Math.max(1, total - 1)) * (WIDTH - PAD_X * 2),
    y: PAD_TOP + ((highClamp(low + range, value) - value) / range) * PRICE_HEIGHT,
  };
}

function highClamp(fallback: number, value: number) {
  return Number.isFinite(value) ? fallback : value;
}

function yFor(value: number, low: number, range: number) {
  return PAD_TOP + ((low + range - value) / range) * PRICE_HEIGHT;
}

function xFor(index: number, total: number) {
  return PAD_X + (index / Math.max(1, total - 1)) * (WIDTH - PAD_X * 2);
}

function markerIndexFor(bars: NormalizedBar[], markerDate: string): number {
  const target = markerDate.slice(0, 10);
  const firstAfter = bars.findIndex((bar) => bar.date >= target);
  if (firstAfter >= 0) return firstAfter;
  const targetTime = new Date(target).getTime();
  if (!Number.isFinite(targetTime)) return bars.length - 1;
  return bars.reduce((best, bar, index) => {
    const current = Math.abs(new Date(bar.date).getTime() - targetTime);
    const previous = Math.abs(new Date(bars[best].date).getTime() - targetTime);
    return current < previous ? index : best;
  }, bars.length - 1);
}

function polylinePoints(item: Series, total: number, low: number, range: number) {
  return item.values.flatMap((value, index) => {
    if (value === null) return [];
    const point = toPoint(value, index, total, low, range);
    return `${point.x.toFixed(1)},${point.y.toFixed(1)}`;
  }).join(" ");
}

function dateLabel(value: string) {
  return value.slice(5, 10).replace("-", "/");
}

export function StockTrend({ bars, marker, compact = false }: StockTrendProps) {
  const normalized = normalizeBars(bars).slice(-120);
  if (normalized.length < 2) {
    return <section className="trend-panel empty">历史行情不足，暂时无法绘制价格趋势。</section>;
  }

  const closes = normalized.map((bar) => bar.close);
  const highs = normalized.map((bar) => bar.high);
  const lows = normalized.map((bar) => bar.low);
  const volumes = normalized.map((bar) => bar.volume);
  const series: Series[] = [
    { key: "ma5", label: "MA5", values: movingAverage(closes, 5) },
    { key: "ma20", label: "MA20", values: movingAverage(closes, 20) },
    { key: "ma60", label: "MA60", values: movingAverage(closes, 60) },
  ];
  const maValues = series.flatMap((item) => item.values.filter((value): value is number => value !== null));
  const low = Math.min(...lows, ...maValues);
  const high = Math.max(...highs, ...maValues);
  const padding = Math.max((high - low) * 0.08, high * 0.006, 1);
  const chartLow = low - padding;
  const chartHigh = high + padding;
  const range = chartHigh - chartLow || 1;
  const candleSlot = (WIDTH - PAD_X * 2) / Math.max(1, normalized.length - 1);
  const candleWidth = Math.max(3, Math.min(9, candleSlot * 0.55));
  const maxVolume = Math.max(...volumes, 1);
  const latest = normalized.at(-1)!;
  const first = normalized[0];
  const periodReturn = (latest.close / first.close - 1) * 100;
  const latestY = yFor(latest.close, chartLow, range);
  const support = Math.min(...normalized.slice(-20).map((bar) => bar.low));
  const resistance = Math.max(...normalized.slice(-20).map((bar) => bar.high));
  const supportY = yFor(support, chartLow, range);
  const resistanceY = yFor(resistance, chartLow, range);
  const markerIndex = marker ? markerIndexFor(normalized, marker.date) : null;
  const markerBar = markerIndex == null ? null : normalized[markerIndex];
  const markerX = markerIndex == null ? null : xFor(markerIndex, normalized.length);
  const markerY = markerBar ? yFor(markerBar.close, chartLow, range) : null;

  return <section className={`trend-panel kline-panel${compact ? " compact" : ""}`}>
    <div className="trend-heading">
      <div><span>蜡烛K线 · 均线 · 成交量</span><strong>近 {normalized.length} 个交易日</strong></div>
      <div className="trend-range"><span>区间涨跌 <b className={periodReturn >= 0 ? "up" : "down"}>{pct(periodReturn)}</b></span><span>最新 <b>{fmt(latest.close)}</b></span></div>
    </div>
    <div className="trend-legend" aria-label="K线图图例">
      <span className="candle-up"><i />上涨K</span>
      <span className="candle-down"><i />下跌K</span>
      {series.map((item) => <span key={item.key} className={item.key}><i />{item.label}</span>)}
      {marker && <span className="marker"><i />标记</span>}
    </div>
    <div className="trend-canvas kline-canvas">
      <svg role="img" aria-label="价格趋势图" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none">
        <title>从 {normalized[0].date} 到 {latest.date} 的蜡烛K线、均线和成交量</title>
        <defs>
          <linearGradient id="stock-volume-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#e4562e" stopOpacity=".28" />
            <stop offset="100%" stopColor="#e4562e" stopOpacity=".08" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
          const y = PAD_TOP + ratio * PRICE_HEIGHT;
          const value = chartHigh - ratio * range;
          return <g key={ratio}>
            <line className="trend-grid-line" x1={PAD_X} y1={y} x2={WIDTH - PAD_X} y2={y} />
            <text className="trend-axis-label" x={PAD_X} y={Math.max(12, y - 5)}>{fmt(value)}</text>
          </g>;
        })}
        <line className="kline-level resistance" x1={PAD_X} y1={resistanceY} x2={WIDTH - PAD_X} y2={resistanceY} />
        <text className="kline-level-label resistance" x={WIDTH - PAD_X - 78} y={Math.max(14, resistanceY - 6)}>压力 {fmt(resistance)}</text>
        <line className="kline-level support" x1={PAD_X} y1={supportY} x2={WIDTH - PAD_X} y2={supportY} />
        <text className="kline-level-label support" x={PAD_X + 8} y={Math.min(PRICE_HEIGHT + PAD_TOP - 4, supportY - 6)}>支撑 {fmt(support)}</text>
        <line className="kline-latest-line" x1={PAD_X} y1={latestY} x2={WIDTH - PAD_X} y2={latestY} />
        {normalized.map((bar, index) => {
          const x = xFor(index, normalized.length);
          const openY = yFor(bar.open, chartLow, range);
          const closeY = yFor(bar.close, chartLow, range);
          const highY = yFor(bar.high, chartLow, range);
          const lowY = yFor(bar.low, chartLow, range);
          const up = bar.close >= bar.open;
          const bodyY = Math.min(openY, closeY);
          const bodyHeight = Math.max(2, Math.abs(closeY - openY));
          const volumeHeight = (bar.volume / maxVolume) * VOLUME_HEIGHT;
          return <g key={`${bar.date}-${index}`} className={`kline-candle ${up ? "up" : "down"}`}>
            <line x1={x} x2={x} y1={highY} y2={lowY} />
            <rect x={x - candleWidth / 2} y={bodyY} width={candleWidth} height={bodyHeight} rx="1.5" />
            <rect className="volume" x={x - candleWidth / 2} y={VOLUME_TOP + VOLUME_HEIGHT - volumeHeight} width={candleWidth} height={Math.max(1, volumeHeight)} rx="1" />
          </g>;
        })}
        {series.map((item) => <polyline key={item.key} className={`trend-line ${item.key}`} points={polylinePoints(item, normalized.length, chartLow, range)} />)}
        <g className="trend-latest">
          <circle cx={xFor(normalized.length - 1, normalized.length)} cy={latestY} r="6" />
          <text x={WIDTH - PAD_X - 78} y={Math.max(PAD_TOP + 14, latestY - 10)}>{fmt(latest.close)}</text>
        </g>
        {marker && markerX != null && markerY != null && markerBar && <g className="trend-marker" aria-label={`${marker.label} ${markerBar.date}`}>
          <line x1={markerX} y1={PAD_TOP} x2={markerX} y2={VOLUME_TOP + VOLUME_HEIGHT} />
          <circle cx={markerX} cy={markerY} r="7" />
          <text x={Math.min(markerX + 10, WIDTH - 95)} y={Math.max(markerY - 10, 18)}>{marker.label}</text>
        </g>}
        <text className="kline-volume-label" x={PAD_X} y={VOLUME_TOP - 8}>成交量</text>
      </svg>
    </div>
    <div className="trend-readout" aria-label="K线关键读数">
      <span>近20支撑 <b>{fmt(support)}</b></span>
      <span>近20压力 <b>{fmt(resistance)}</b></span>
      <span>区间涨跌 <b className={periodReturn >= 0 ? "up" : "down"}>{pct(periodReturn)}</b></span>
    </div>
    <div className="trend-dates"><span>{dateLabel(normalized[0].date)}</span><span>{dateLabel(latest.date)}</span></div>
  </section>;
}
