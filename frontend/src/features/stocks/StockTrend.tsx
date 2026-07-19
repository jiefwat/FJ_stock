import { fmt } from "../../lib/api";

type PriceBar = { date: string; close: number };
type StockTrendProps = { bars: PriceBar[] };
type Series = { key: string; label: string; values: Array<number | null> };

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

export function StockTrend({ bars }: StockTrendProps) {
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
    const x = PAD_X + (index / (validBars.length - 1)) * (WIDTH - PAD_X * 2);
    const y = HEIGHT - PAD_Y - ((value - low) / range) * (HEIGHT - PAD_Y * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const latest = validBars.at(-1)!;

  return <section className="trend-panel">
    <div className="trend-heading">
      <div><span>PRICE TAPE / 价格与均线</span><strong>{validBars.length} 个交易日</strong></div>
      <div className="trend-range"><span>区间低点 <b>{fmt(low)}</b></span><span>区间高点 <b>{fmt(high)}</b></span></div>
    </div>
    <div className="trend-legend" aria-label="趋势图图例">{series.map((item) => <span key={item.key} className={item.key}><i />{item.label}</span>)}</div>
    <div className="trend-canvas">
      <svg role="img" aria-label="价格趋势图" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none">
        <title>从 {validBars[0].date} 到 {latest.date} 的收盘价与移动均线</title>
        <line className="trend-grid-line" x1={PAD_X} y1={HEIGHT / 2} x2={WIDTH - PAD_X} y2={HEIGHT / 2} />
        {series.map((item) => <polyline key={item.key} className={`trend-line ${item.key}`} points={points(item)} />)}
      </svg>
    </div>
    <div className="trend-dates"><span>{validBars[0].date}</span><span>{latest.date}</span></div>
  </section>;
}
