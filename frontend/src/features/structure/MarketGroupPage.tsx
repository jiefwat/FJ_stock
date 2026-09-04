import { useQuery } from "@tanstack/react-query";
import { CircleAlert, LoaderCircle, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { AsyncState } from "../../components/AsyncState";
import { DataStamp } from "../../components/DataStamp";
import { PageTaskRail, WorkbenchPageHeader } from "../../components/WorkbenchPageHeader";
import { api, fmt, pct, percent, type MarketGroupAnalysis, type MarketGroupStat } from "../../lib/api";

type GroupKind = "concept" | "industry";
type GroupSort = "heat" | "change" | "capital" | "risk";
const INITIAL_GROUP_MEMBERS = 12;
const INITIAL_GROUPS = 16;

function changeTone(value: number | null | undefined) {
  return value == null ? "" : value >= 0 ? "up" : "down";
}

export function MarketGroupPage({ kind }: { kind: GroupKind }) {
  const label = kind === "concept" ? "概念" : "行业";
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<GroupSort>("heat");
  const [visibleGroupCount, setVisibleGroupCount] = useState(INITIAL_GROUPS);
  const query = useQuery({
    queryKey: ["market-structure", "groups", kind],
    queryFn: () => api<MarketGroupAnalysis>(`/api/v1/market-structure/groups?kind=${kind}`),
    staleTime: 10 * 60_000,
  });
  const groups = useMemo(() => {
    const normalized = search.trim().toLocaleLowerCase();
    const filtered = (query.data?.groups ?? []).filter((item) => !normalized || item.name.toLocaleLowerCase().includes(normalized));
    return [...filtered].sort((left, right) => {
      if (sort === "change") return (right.change_pct ?? Number.NEGATIVE_INFINITY) - (left.change_pct ?? Number.NEGATIVE_INFINITY);
      if (sort === "capital") return (right.net_flow ?? Number.NEGATIVE_INFINITY) - (left.net_flow ?? Number.NEGATIVE_INFINITY);
      if (sort === "risk") return right.risk_score - left.risk_score;
      return right.heat_score - left.heat_score;
    });
  }, [query.data?.groups, search, sort]);
  const selectedCode = params.get("group");
  const selected = groups.find((item) => item.code === selectedCode) ?? groups[0] ?? null;
  const visibleGroups = useMemo(() => {
    const initial = groups.slice(0, visibleGroupCount);
    if (selected && !initial.some((item) => item.code === selected.code)) return [...initial, selected];
    return initial;
  }, [groups, selected, visibleGroupCount]);
  const hiddenGroupCount = Math.max(0, groups.length - visibleGroupCount);
  const detailQuery = useQuery({
    queryKey: ["market-structure", "group-detail", kind, selected?.code],
    queryFn: () => api<MarketGroupAnalysis>(`/api/v1/market-structure/groups/${kind}/${encodeURIComponent(selected!.code)}`),
    enabled: Boolean(selected),
    staleTime: 10 * 60_000,
  });
  const detailGroup = detailQuery.data?.groups.find((item) => item.code === selected?.code) ?? null;
  const focusedGroup = detailGroup ?? selected;
  const detailLoading = Boolean(selected && !selected.constituents.length && detailQuery.isLoading);
  const [showDetailLoading, setShowDetailLoading] = useState(false);
  const detailUnavailable = Boolean(
    focusedGroup
    && !focusedGroup.constituents.length
    && !detailLoading
    && (detailQuery.isError || detailQuery.isFetched),
  );
  const selectGroup = (group: MarketGroupStat) => {
    const next = new URLSearchParams(params);
    next.set("group", group.code);
    setParams(next, { replace: true });
  };

  useEffect(() => {
    if (!detailLoading) {
      setShowDetailLoading(false);
      return;
    }
    const timer = window.setTimeout(() => setShowDetailLoading(true), 240);
    return () => window.clearTimeout(timer);
  }, [detailLoading, selected?.code]);

  useEffect(() => {
    if (!groups.length || groups.some((item) => item.code === selectedCode)) return;
    const next = new URLSearchParams(params);
    next.set("group", groups[0].code);
    setParams(next, { replace: true });
  }, [groups, params, selectedCode, setParams]);

  useEffect(() => setVisibleGroupCount(INITIAL_GROUPS), [search, sort, kind]);

  return <>
    <WorkbenchPageHeader title={`${label}分析`} status={query.data ? <DataStamp meta={query.data.meta} /> : undefined} />
    <PageTaskRail label={`${label}分析`} steps={[
      { id: "group-summary", label: "识别主线", detail: `领先${label}与市场广度` },
      { id: "group-catalog", label: `筛选${label}`, detail: "搜索并切换排序口径" },
      { id: "group-focus", label: "核对证据", detail: "资金、龙头与成分股" },
    ]} />
    <AsyncState loading={query.isLoading} error={query.error as Error | null}>{query.data && <>
      {!query.data.available && <section className="structure-unavailable"><strong>{label}数据暂不可用</strong><p>不能据空结果判断市场没有主线。请稍后重试，其他大盘数据仍可使用。</p></section>}
      {query.data.degraded && <section className="structure-unavailable degraded"><strong>{label}数据正在降级显示</strong><p>{query.data.unavailable_reason ?? query.data.summary}；可用部分继续展示，缺失项保持 N/A。</p></section>}
      <GroupHero groups={query.data.groups} label={label} onSelect={selectGroup} />
      <section className="group-workbench">
        <aside id="group-catalog" className="group-catalog">
          <header><div><strong>{label}矩阵</strong><small>{groups.length} / {query.data.groups.length}</small></div><label><Search size={15} /><input aria-label={`搜索${label}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`搜索${label}名称`} /></label><select aria-label={`${label}排序`} value={sort} onChange={(event) => setSort(event.target.value as GroupSort)}><option value="heat">热度优先</option><option value="change">涨幅优先</option><option value="capital">资金优先</option><option value="risk">风险优先</option></select></header>
          {groups.length ? <><div className="group-matrix">{visibleGroups.map((item, index) => {
            const displayItem = detailGroup?.code === item.code ? detailGroup : item;
            return <button key={item.code} type="button" className={selected?.code === item.code ? "active" : ""} onClick={() => selectGroup(item)}><em>{String(index + 1).padStart(2, "0")}</em><span><strong>{item.name}</strong><small>{displayItem.constituent_count ? `${displayItem.constituent_count} 只成分` : "成分待补"}</small></span><b>{fmt(displayItem.heat_score, 0)}</b><i className={changeTone(displayItem.change_pct)}>{pct(displayItem.change_pct)}</i><u style={{ width: `${displayItem.evidence_coverage * 100}%` }} /></button>;
          })}</div>{hiddenGroupCount > 0 ? <button className="group-catalog-more" type="button" onClick={() => setVisibleGroupCount((current) => current + INITIAL_GROUPS)}>再显示 {Math.min(INITIAL_GROUPS, hiddenGroupCount)} 个{label}<span>还剩 {hiddenGroupCount} 个</span></button> : null}</> : <div className="empty">当前搜索没有匹配的{label}。</div>}
        </aside>
        <GroupFocus
          group={focusedGroup}
          label={label}
          detailLoading={detailLoading && showDetailLoading}
          detailUnavailable={detailUnavailable}
          onRetry={() => { void detailQuery.refetch(); }}
        />
      </section>
      <details className="structure-method"><summary>计算口径与降级说明</summary>{query.data.methodology.map((item) => <p key={item}>{item}</p>)}</details>
    </>}</AsyncState>
  </>;
}

function GroupHero({ groups, label, onSelect }: { groups: MarketGroupStat[]; label: string; onSelect: (group: MarketGroupStat) => void }) {
  const strongest = [...groups].sort((left, right) => right.heat_score - left.heat_score)[0];
  const weakest = [...groups].sort((left, right) => left.heat_score - right.heat_score)[0];
  const priced = groups.filter((item) => item.change_pct != null);
  const rising = priced.filter((item) => (item.change_pct ?? 0) > 0).length;
  const active = [...groups].sort((left, right) => (right.total_amount ?? 0) - (left.total_amount ?? 0))[0];
  const breadth = priced.length ? rising / priced.length : null;
  return <section id="group-summary" className="group-signal-hero" aria-label={`${label}市场摘要`}>
    <article className="group-mainline">
      <span>当前主线</span>
      <div><strong>{strongest?.name ?? "待数据"}</strong><b className={changeTone(strongest?.change_pct)}>{strongest ? pct(strongest.change_pct) : "N/A"}</b></div>
      <p>{strongest ? `热度 ${fmt(strongest.heat_score, 0)}，在 ${groups.length} 个${label}中领先。` : "样本不足，暂不能判断当前主线。"}</p>
      <div className="group-heat-track" aria-label={strongest ? `${strongest.name}热度 ${fmt(strongest.heat_score, 0)}` : "热度待数据"}><i style={{ width: `${Math.max(0, Math.min(100, strongest?.heat_score ?? 0))}%` }} /></div>
      {strongest && <button type="button" onClick={() => onSelect(strongest)}>查看主线证据 <span>→</span></button>}
    </article>
    <aside className="group-market-context" aria-label="主线旁证">
      <div><span>上涨广度</span><strong>{priced.length ? `${rising} / ${priced.length}` : "N/A"}</strong><p>{breadth == null ? "涨跌样本不足" : breadth >= 0.6 ? "多数主题同步走强" : breadth >= 0.4 ? "市场分化，主线更重要" : "上涨面偏窄，留意退潮"}</p></div>
      <div><span>成交主线</span><strong>{active?.name ?? "待数据"}</strong><p>{active?.total_amount == null ? "成交额待补" : `${fmt(active.total_amount / 100_000_000, 0)} 亿成交`}</p></div>
      <div><span>风险对照</span><strong>{weakest?.name ?? "待数据"}</strong><p>{weakest ? `风险 ${fmt(weakest.risk_score, 0)} · ${pct(weakest.change_pct)}` : "暂不能判断"}</p></div>
    </aside>
  </section>;
}

function GroupFocus({
  group,
  label,
  detailLoading,
  detailUnavailable,
  onRetry,
}: {
  group: MarketGroupStat | null;
  label: string;
  detailLoading: boolean;
  detailUnavailable: boolean;
  onRetry: () => void;
}) {
  const [showAllMembers, setShowAllMembers] = useState(false);

  useEffect(() => setShowAllMembers(false), [group?.code]);

  if (!group) return <section id="group-focus" className="group-focus empty">选择一个{label}查看成员与龙头证据。</section>;
  const total = group.advancing + group.declining;
  const visibleMembers = showAllMembers ? group.constituents : group.constituents.slice(0, INITIAL_GROUP_MEMBERS);
  const hiddenMemberCount = group.constituents.length - visibleMembers.length;
  return <section id="group-focus" className="group-focus" aria-label={`${group.name}${label}焦点`}>
    <header className="group-focus-head"><div><span>{label}证据复核</span><h2>{group.name}</h2><p>置信度 {percent(group.evidence_coverage * 100)} · 信息覆盖，不是上涨概率</p></div><strong className={changeTone(group.change_pct)}>{pct(group.change_pct)}</strong></header>
    {detailLoading && <div className="group-detail-state loading" role="status"><LoaderCircle className="spin" size={20} /><div><strong>正在读取成分股证据</strong><p>正在补齐上涨扩散、平均换手与龙头候选。</p></div></div>}
    <div className="group-focus-metrics"><article><span>综合热度</span><strong>{fmt(group.heat_score, 0)}</strong></article><article><span>上涨扩散</span><strong>{total ? percent(group.advancing / total * 100) : "N/A"}</strong></article><article><span>资金净流</span><strong>{group.net_flow == null ? "N/A" : `${fmt(group.net_flow / 100_000_000)} 亿`}</strong></article><article><span>平均换手</span><strong>{group.average_turnover_rate == null ? "N/A" : percent(group.average_turnover_rate)}</strong></article></div>
    {detailUnavailable && <div className="group-detail-state unavailable" role="status"><CircleAlert size={20} /><div><strong>成分股证据暂未取得</strong><p>板块涨跌和资金仍可参考，扩散、换手与龙头暂不能确认。</p></div><button type="button" onClick={onRetry}><RefreshCw size={14} />重试成分股证据</button></div>}
    {group.leader && <Link className="group-leader" to={`/stocks?symbol=${encodeURIComponent(group.leader.quote.symbol)}&from=${group.kind}&board=${encodeURIComponent(group.code)}&boardName=${encodeURIComponent(group.name)}`}><span>下一步看龙头候选</span><strong>{group.leader.quote.name}</strong><b>{fmt(group.leader.score, 0)} 分</b><small>{pct(group.leader.quote.change_pct)} · 进入 Stock Lab 复核 <em>→</em></small></Link>}
    {visibleMembers.length > 0 && <div className="group-member-list">{visibleMembers.map((item, index) => <Link key={item.symbol} to={`/stocks?symbol=${encodeURIComponent(item.symbol)}&from=${group.kind}&board=${encodeURIComponent(group.code)}&boardName=${encodeURIComponent(group.name)}`}><em>{String(index + 1).padStart(2, "0")}</em><span><strong>{item.name}</strong><small>{item.symbol}</small></span><b className={changeTone(item.change_pct)}>{pct(item.change_pct)}</b><i>{item.net_flow == null ? "资金 N/A" : `${fmt(item.net_flow / 100_000_000)} 亿`}</i></Link>)}</div>}
    {group.constituents.length > INITIAL_GROUP_MEMBERS && <button className="group-members-more" type="button" aria-expanded={showAllMembers} onClick={() => setShowAllMembers((current) => !current)}>{showAllMembers ? `收起至前 ${INITIAL_GROUP_MEMBERS} 只` : `再显示 ${hiddenMemberCount} 只成分股`}<span>{showAllMembers ? "减少滚动" : `当前显示 ${visibleMembers.length} / ${group.constituents.length}`}</span></button>}
    {!detailLoading && !detailUnavailable && group.missing_evidence.length > 0 && <p className="group-missing">缺少：{group.missing_evidence.join("、")}；缺失值未按 0 参与排名。</p>}
  </section>;
}
