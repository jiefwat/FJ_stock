import { fmt } from "../../lib/api";

type PriceBar = { date: string; close: number };
type TrendMarker = { date: string; label: string };
type StockTrendProps = { bars: PriceBar[]; marker?: TrendMarker; compact?: boolean };
type Series = { key: string; label: string; values: Array<number | null> };
type ChartPoint = { x: number; y: number };

const WIDTH = 960;
const HEIGHT = 220;
const PAD_X = 22;
const PAD_Y = 22;

function movingAverage(values: number[], size: number): Array<number | null> {
  return values.map((_, index) => {
    if (index + 1 < size) return null;
    return values.slice(index + 1 - size, index + 1).reduce((sum, value) => sum + value, 0) / size;
  });
}

function toPoint(value: number, index: number, total: number, low: number, range: number): ChartPoint {
  return {
    x: PAD_X + (index / (total - 1)) * (WIDTH - PAD_X * 2),
    y: HEIGHT - PAD_Y - ((value - low) / range) * (HEIGHT - PAD_Y * 2),
  };
}

function markerIndexFor(bars: PriceBar[], markerDate: string): number {
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

export function StockTrend({ bars, marker, compact = false }: StockTrendProps) {
  const validBars = bars.filter((bar) => Number.isFinite(bar.close));
  if (validBars.length < 2) {
    return <section className="trend-panel empty">历史行情不足，暂时无法绘制价格趋势。</section>;
  }

  const closes = validBars.map((bar) => bar.close);
  const series: Series[] = [
    { key: "close", label: "收盘价", values: closes },
    { key: "ma5", label: "MA5", values: movingAverage(closes, 5) },
    { key: "ma20", label: "MA20", values: movingAverage(closes, 20) },
    { key: "ma60", label: "MA60", values: movingAverage(closes, 60) },
  ];
  const values = series.flatMap((item) => item.values.filter((value): value is number => value !== null));
  const low = Math.min(...values);
  const high = Math.max(...values);
  const range = high - low || 1;
  const points = (item: Series) => item.values.flatMap((value, index) => {
    if (value === null) return [];
    const { x, y } = toPoint(value, index, validBars.length, low, range);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = validBars.at(-1)!;
  const markerIndex = marker ? markerIndexFor(validBars, marker.date) : null;
  const markerBar = markerIndex == null ? null : validBars[markerIndex];
  const markerPoint = markerBar && markerIndex != null
    ? toPoint(markerBar.close, markerIndex, validBars.length, low, range)
    : null;

  return <section className={`trend-panel${compact ? " compact" : ""}`}>
    <div className="trend-heading">
      <div><span>PRICE TAPE / 价格与均线</span><strong>{validBars.length} 个交易日</strong></div>
      <div className="trend-range"><span>区间低点 <b>{fmt(low)}</b></span><span>区间高点 <b>{fmt(high)}</b></span></div>
    </div>
    <div className="trend-legend" aria-label="趋势图图例">
      {series.map((item) => <span key={item.key} className={item.key}><i />{item.label}</span>)}
      {marker && <span className="marker"><i />跟踪点</span>}
    </div>
    <div className="trend-canvas">
      <svg role="img" aria-label="价格趋势图" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none">
        <title>从 {validBars[0].date} 到 {latest.date} 的收盘价与移动均线</title>
        <line className="trend-grid-line" x1={PAD_X} y1={HEIGHT / 2} x2={WIDTH - PAD_X} y2={HEIGHT / 2} />
        {series.map((item) => <polyline key={item.key} className={`trend-line ${item.key}`} points={points(item)} />)}
        {marker && markerPoint && markerBar && <g className="trend-marker" aria-label={`${marker.label} ${markerBar.date}`}>
          <line x1={markerPoint.x} y1={PAD_Y} x2={markerPoint.x} y2={HEIGHT - PAD_Y} />
          <circle cx={markerPoint.x} cy={markerPoint.y} r="7" />
          <text x={Math.min(markerPoint.x + 10, WIDTH - 95)} y={Math.max(markerPoint.y - 10, 18)}>{marker.label}</text>
        </g>}
      </svg>
    </div>
    <div className="trend-dates"><span>{validBars[0].date}</span><span>{latest.date}</span></div>
    {marker && <p className="trend-caption">圆点为加入跟踪日，方便复盘加入后走势。</p>}
  </section>;
}
