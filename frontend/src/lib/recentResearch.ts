import { getAuthToken, type Quote } from "./api";

export type RecentResearch = {
  symbol: string;
  name: string;
  sector: string | null;
  updatedAt: number;
};

const version = 1;
const maxItems = 6;

function storageKey() {
  const token = getAuthToken();
  return `marketdesk.recentResearch.v${version}.${token ? token.slice(-16) : "anonymous"}`;
}

function canUseLocalStorage() {
  return typeof localStorage !== "undefined" && typeof localStorage.getItem === "function";
}

function normalizeItems(value: unknown): RecentResearch[] {
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is RecentResearch => {
    if (!item || typeof item !== "object") return false;
    const candidate = item as { symbol?: unknown; name?: unknown; sector?: unknown; updatedAt?: unknown };
    return typeof candidate.symbol === "string"
      && typeof candidate.name === "string"
      && (candidate.sector == null || typeof candidate.sector === "string")
      && typeof candidate.updatedAt === "number";
  }).slice(0, maxItems);
}

export function loadRecentResearch(): RecentResearch[] {
  if (!canUseLocalStorage()) return [];
  try {
    const raw = localStorage.getItem(storageKey());
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { version?: number; items?: unknown };
    if (parsed.version !== version) return [];
    return normalizeItems(parsed.items);
  } catch {
    return [];
  }
}

export function rememberRecentResearch(stock: Pick<Quote, "symbol" | "name" | "sector">): RecentResearch[] {
  if (!canUseLocalStorage() || typeof localStorage.setItem !== "function") return [];
  const item: RecentResearch = {
    symbol: stock.symbol,
    name: stock.name,
    sector: stock.sector ?? null,
    updatedAt: Date.now(),
  };
  const items = [item, ...loadRecentResearch().filter((recent) => recent.symbol !== stock.symbol)].slice(0, maxItems);
  localStorage.setItem(storageKey(), JSON.stringify({ version, items }));
  return items;
}
