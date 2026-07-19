(() => {
  "use strict";

  const moduleButtons = Array.from(document.querySelectorAll("[data-module-switch]"));
  const decks = new Map(
    Array.from(document.querySelectorAll("[data-module-deck]"), (deck) => [
      deck.dataset.moduleDeck,
      deck,
    ]),
  );
  const moduleScrollPositions = new Map();
  const searchCache = new Map();
  const stockCache = window.AsterStockCache || new Map();
  window.AsterStockCache = stockCache;
  let activeModule = "market";
  let stockRequestSequence = 0;
  let toastTimer;

  const activateModule = (name, options = {}) => {
    const target = decks.get(name) || decks.get("market");
    if (!target) return;
    if (decks.has(activeModule) && activeModule !== target.dataset.moduleDeck) {
      moduleScrollPositions.set(activeModule, window.scrollY);
    }
    decks.forEach((deck) => {
      const active = deck === target;
      deck.hidden = !active;
      deck.classList.toggle("is-active", active);
    });
    moduleButtons.forEach((button) => {
      const active = button.dataset.moduleSwitch === target.dataset.moduleDeck;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    activeModule = target.dataset.moduleDeck;
    if (options.updateHash !== false) window.history.replaceState(null, "", `#${target.dataset.moduleDeck}`);
    if (options.focus) target.querySelector("[data-deck-heading]")?.focus({ preventScroll: true });
    if (options.restoreScroll !== false) {
      window.requestAnimationFrame(() => {
        window.scrollTo({ top: moduleScrollPositions.get(activeModule) || 0, behavior: "auto" });
      });
    }
    document.dispatchEvent(
      new CustomEvent("aster:module-change", { detail: { module: target.dataset.moduleDeck } }),
    );
  };

  moduleButtons.forEach((button) => {
    button.addEventListener("click", () => activateModule(button.dataset.moduleSwitch, { focus: true }));
  });

  const toast = document.querySelector("[data-toast]");
  const dismissToast = () => {
    window.clearTimeout(toastTimer);
    if (!toast) return;
    toast.classList.remove("is-visible");
    toast.hidden = true;
  };

  const showToast = (message) => {
    if (!toast || !message) return;
    window.clearTimeout(toastTimer);
    toast.textContent = message;
    toast.hidden = false;
    toast.classList.add("is-visible");
    toastTimer = window.setTimeout(dismissToast, 1800);
  };

  document.addEventListener("aster:toast", (event) => showToast(event.detail?.message));

  document.querySelectorAll("[data-refresh]").forEach((button) => {
    button.addEventListener("click", () => {
      button.disabled = true;
      button.textContent = "读取中…";
      location.reload();
    });
  });

  const fetchJson = async (url, options = {}) => {
    const response = await fetch(url, {
      headers: { Accept: "application/json" },
      signal: options.signal,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.message || "读取数据失败");
    return payload;
  };

  const searchInput = document.querySelector("[data-stock-search]");
  const globalSearch = document.querySelector("#candidate-search");
  const results = document.querySelector("[data-stock-results]");
  const empty = document.querySelector("[data-stock-empty]");
  const loading = document.querySelector("[data-stock-loading]");
  const error = document.querySelector("[data-stock-error]");
  const detail = document.querySelector("[data-stock-detail]");
  let searchTimer;
  let searchController;

  const clearNode = (node) => {
    while (node?.firstChild) node.removeChild(node.firstChild);
  };

  const textElement = (tag, value, className = "") => {
    const element = document.createElement(tag);
    element.textContent = value ?? "—";
    if (className) element.className = className;
    return element;
  };

  const formatNumber = (value, digits = 2) => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    return Number.isFinite(number)
      ? number.toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits })
      : "—";
  };

  const formatSigned = (value, suffix = "%") => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return `${number >= 0 ? "+" : ""}${number.toFixed(2)}${suffix}`;
  };

  const setText = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value ?? "—";
  };

  const chartPath = (points) => {
    if (!Array.isArray(points) || points.length === 0) return "";
    const values = points.map(Number).filter(Number.isFinite);
    if (values.length === 0) return "";
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const spread = maximum - minimum || 1;
    return values
      .map((value, index) => {
        const x = values.length === 1 ? 450 : 20 + (index / (values.length - 1)) * 860;
        const y = 125 - ((value - minimum) / spread) * 100;
        return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
      })
      .join(" ");
  };

  const dimension = (label, value, note) => {
    const item = document.createElement("article");
    item.className = "stock-dimension";
    item.append(textElement("span", label), textElement("strong", value), textElement("small", note));
    return item;
  };

  const renderList = (container, values, emptyText) => {
    clearNode(container);
    const items = Array.isArray(values) ? values : [];
    if (items.length === 0) {
      container?.append(textElement("p", emptyText));
      return;
    }
    items.forEach((value) => container?.append(textElement("p", value)));
  };

  const renderEvents = (container, events) => {
    clearNode(container);
    if (!Array.isArray(events) || events.length === 0) {
      container?.append(textElement("p", "当前快照没有股票事件。"));
      return;
    }
    events.forEach((event) => {
      const row = document.createElement("article");
      row.append(
        textElement("time", event.published_at || "时间未标注"),
        textElement("strong", event.title || "未命名事件"),
        textElement("p", event.summary || ""),
      );
      container?.append(row);
    });
  };

  const renderStock = (stock) => {
    window.AsterCurrentStock = stock;
    setText("[data-stock-code]", `${stock.code} · ${stock.sector}`);
    setText("[data-stock-name]", stock.name);
    setText("[data-stock-price]", formatNumber(stock.latest_price));
    setText("[data-stock-change]", formatSigned(stock.pct_change));
    setText("[data-stock-trend]", stock.trend?.label);
    const line = document.querySelector("[data-stock-chart-line]");
    if (line) line.setAttribute("d", chartPath(stock.trend?.points));

    const dimensions = document.querySelector("[data-stock-dimensions]");
    clearNode(dimensions);
    dimensions?.append(
      dimension("5 日动量", formatSigned(stock.momentum?.return_5d), "相对五个交易日前"),
      dimension("20 日动量", formatSigned(stock.momentum?.return_20d), "样本不足时不补零"),
      dimension("10 日振幅", formatSigned(stock.volatility?.range_10d), "平均日内振幅"),
      dimension("PE TTM", formatNumber(stock.valuation?.pe_ttm), "快照估值"),
      dimension("换手率", formatSigned(stock.flow?.turnover_rate), "不等同主力资金"),
      dimension("数据质量", stock.quality?.label || "—", stock.quality?.primary_source || "来源未标注"),
    );
    renderList(document.querySelector("[data-stock-evidence]"), stock.evidence, "证据不足");
    renderList(document.querySelector("[data-stock-risks]"), stock.risks, "未识别到显著风险");
    renderEvents(document.querySelector("[data-stock-events]"), stock.events);
  };

  const fetchStock = (code) => {
    if (stockCache.has(code)) return stockCache.get(code);
    const request = fetchJson(`/api/stocks/${encodeURIComponent(code)}`).catch((reason) => {
      stockCache.delete(code);
      throw reason;
    });
    stockCache.set(code, request);
    return request;
  };

  const loadStock = async (code) => {
    if (!code) return;
    const requestId = ++stockRequestSequence;
    if (empty) empty.hidden = true;
    if (detail) detail.hidden = true;
    if (error) error.hidden = true;
    if (loading) loading.hidden = false;
    try {
      const stock = await fetchStock(code);
      if (requestId !== stockRequestSequence) return;
      renderStock(stock);
      if (detail) detail.hidden = false;
    } catch (reason) {
      if (requestId !== stockRequestSequence) return;
      if (error) {
        error.textContent = reason.message;
        error.hidden = false;
      }
    } finally {
      if (loading && requestId === stockRequestSequence) loading.hidden = true;
    }
  };

  const renderSearchResults = (items) => {
    clearNode(results);
    if (!Array.isArray(items) || items.length === 0) {
      results?.append(textElement("p", "没有匹配的股票。", "deck-empty"));
      return;
    }
    items.forEach((stock) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "stock-result";
      button.append(
        textElement("strong", stock.name),
        textElement("span", `${stock.code} · ${stock.sector}`),
        textElement("em", `${stock.trend} · ${formatSigned(stock.pct_change)}`),
      );
      button.addEventListener("click", () => loadStock(stock.code));
      results?.append(button);
    });
  };

  const searchStocks = async (query) => {
    if (!results) return;
    if (!query) {
      searchController?.abort();
      results.textContent = "输入代码、名称或主题开始分析。";
      return;
    }
    searchController?.abort();
    if (searchCache.has(query)) {
      renderSearchResults(searchCache.get(query));
      return;
    }
    searchController = new AbortController();
    results.textContent = "正在搜索…";
    try {
      const payload = await fetchJson(`/api/stocks?query=${encodeURIComponent(query.slice(0, 40))}`, {
        signal: searchController.signal,
      });
      searchCache.set(query, payload.items);
      renderSearchResults(payload.items);
    } catch (reason) {
      if (reason.name === "AbortError") return;
      results.textContent = reason.message;
    }
  };

  const scheduleSearch = (query, options = {}) => {
    const normalized = query.trim().slice(0, 40);
    window.clearTimeout(searchTimer);
    if (options.activate !== false) activateModule("stock");
    if (searchInput && searchInput.value !== normalized) searchInput.value = normalized;
    searchTimer = window.setTimeout(() => searchStocks(normalized), options.immediate ? 0 : 220);
  };

  const resetSearch = () => {
    window.clearTimeout(searchTimer);
    searchController?.abort();
    if (globalSearch) globalSearch.value = "";
    if (searchInput) searchInput.value = "";
    if (results) results.textContent = "输入代码、名称或主题开始分析。";
  };

  searchInput?.addEventListener("input", () => {
    scheduleSearch(searchInput.value, { activate: false });
  });

  globalSearch?.addEventListener("input", () => {
    scheduleSearch(globalSearch.value);
  });

  document.querySelectorAll("[data-open-stock]").forEach((button) => {
    button.addEventListener("click", () => {
      activateModule("stock", { focus: true });
      loadStock(button.dataset.openStock);
    });
  });

  document.querySelector("[data-add-current-holding]")?.addEventListener("click", () => {
    if (!window.AsterCurrentStock) return;
    activateModule("portfolio", { focus: true });
    document.dispatchEvent(
      new CustomEvent("aster:portfolio-prefill", {
        detail: { code: window.AsterCurrentStock.code },
      }),
    );
    showToast("已带入持仓，补充数量和成本即可保存");
  });

  document.addEventListener("keydown", (event) => {
    const target = event.target;
    const isEditing = target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement;
    if (event.key === "Escape") {
      const isSearch = target === globalSearch || target === searchInput;
      const hasVisibleToast = Boolean(toast && !toast.hidden);
      if (isSearch) {
        event.preventDefault();
        if (target.value || globalSearch?.value || searchInput?.value) resetSearch();
        else target.blur();
      }
      if (hasVisibleToast) dismissToast();
      if (isSearch || hasVisibleToast) return;
    }
    if (event.key === "/" && !isEditing) {
      event.preventDefault();
      globalSearch?.focus();
      return;
    }
    if (isEditing || event.altKey || event.ctrlKey || event.metaKey) return;
    const shortcuts = { "1": "market", "2": "opportunities", "3": "stock", "4": "portfolio" };
    if (shortcuts[event.key]) activateModule(shortcuts[event.key], { focus: true });
  });

  const initialModule = window.location.hash.replace("#", "");
  activateModule(decks.has(initialModule) ? initialModule : "market", {
    updateHash: false,
    restoreScroll: false,
  });
})();
