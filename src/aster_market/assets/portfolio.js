(() => {
  "use strict";

  const STORAGE_KEY = "aster.portfolio.v1";
  const form = document.querySelector("[data-portfolio-form]");
  const ledger = document.querySelector("[data-portfolio-ledger]");
  const empty = document.querySelector("[data-portfolio-empty]");
  const recovery = document.querySelector("[data-portfolio-recovery]");
  const formError = document.querySelector("[data-portfolio-form-error]");
  const exposure = document.querySelector("[data-portfolio-exposure]");
  const detailCache = new Map();
  let holdings = [];

  const setText = (selector, value) => {
    const node = document.querySelector(selector);
    if (node) node.textContent = value;
  };

  const formatMoney = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    return Number.isFinite(number)
      ? `¥${number.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
      : "—";
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined || value === "") return "—";
    const number = Number(value);
    if (!Number.isFinite(number)) return "—";
    return `${number >= 0 ? "+" : ""}${number.toFixed(2)}%`;
  };

  const textElement = (tag, value, className = "") => {
    const node = document.createElement(tag);
    node.textContent = value ?? "—";
    if (className) node.className = className;
    return node;
  };

  const clearNode = (node) => {
    while (node?.firstChild) node.removeChild(node.firstChild);
  };

  const validHolding = (item) =>
    item &&
    typeof item.code === "string" &&
    item.code.trim() &&
    Number.isFinite(Number(item.quantity)) &&
    Number(item.quantity) > 0 &&
    Number.isFinite(Number(item.cost)) &&
    Number(item.cost) >= 0;

  const loadHoldings = () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed) || !parsed.every(validHolding)) throw new Error("invalid holdings");
      return parsed.map((item) => ({
        code: item.code.trim().toUpperCase(),
        quantity: Number(item.quantity),
        cost: Number(item.cost),
      }));
    } catch {
      localStorage.removeItem(STORAGE_KEY);
      if (recovery) recovery.hidden = false;
      return [];
    }
  };

  const saveHoldings = () => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(holdings));
  };

  const fetchStock = async (code) => {
    if (detailCache.has(code)) return detailCache.get(code);
    try {
      const response = await fetch(`/api/stocks/${encodeURIComponent(code)}`, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("行情不可用");
      const stock = await response.json();
      detailCache.set(code, stock);
      return stock;
    } catch {
      return null;
    }
  };

  const actionButton = (label, handler, className = "") => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = className;
    button.addEventListener("click", handler);
    return button;
  };

  const renderExposure = (rows, totalValue) => {
    clearNode(exposure);
    if (!exposure || totalValue <= 0) {
      exposure?.append(textElement("span", "组合暴露将在添加持仓后显示"));
      return;
    }
    const sectors = new Map();
    rows.forEach(({ marketValue, stock }) => {
      const sector = stock?.sector || "行情不可用";
      sectors.set(sector, (sectors.get(sector) || 0) + marketValue);
    });
    Array.from(sectors.entries())
      .sort((left, right) => right[1] - left[1])
      .forEach(([sector, value]) => {
        const item = document.createElement("span");
        item.className = "exposure-segment";
        item.style.setProperty("--exposure", `${(value / totalValue) * 100}%`);
        item.append(textElement("strong", sector), textElement("em", formatPercent((value / totalValue) * 100)));
        exposure.append(item);
      });
  };

  const render = async () => {
    if (empty) empty.hidden = holdings.length > 0;
    clearNode(ledger);
    if (holdings.length === 0) {
      setText("[data-portfolio-market-value]", "—");
      setText("[data-portfolio-cost]", "—");
      setText("[data-portfolio-profit]", "—");
      setText("[data-portfolio-return]", "—");
      renderExposure([], 0);
      return;
    }

    const details = await Promise.all(holdings.map((holding) => fetchStock(holding.code)));
    const rows = holdings.map((holding, index) => {
      const stock = details[index];
      const latest = Number(stock?.latest_price);
      const marketValue = Number.isFinite(latest) ? latest * holding.quantity : 0;
      const costValue = holding.cost * holding.quantity;
      return { holding, stock, marketValue, costValue, profit: marketValue - costValue };
    });

    rows.forEach(({ holding, stock, marketValue, costValue, profit }) => {
      const row = document.createElement("article");
      row.className = "portfolio-row";
      const identity = document.createElement("div");
      identity.append(textElement("strong", stock?.name || holding.code), textElement("span", holding.code));
      const position = document.createElement("div");
      position.append(
        textElement("strong", holding.quantity.toLocaleString("zh-CN")),
        textElement("span", `成本 ${formatMoney(holding.cost)}`),
      );
      const quote = document.createElement("div");
      quote.append(
        textElement("strong", stock ? formatMoney(stock.latest_price) : "行情不可用"),
        textElement("span", stock ? `趋势 ${stock.trend?.label || "—"}` : "保留本机记录"),
      );
      const outcome = document.createElement("div");
      const returnRate = costValue > 0 && stock ? (profit / costValue) * 100 : null;
      outcome.append(
        textElement("strong", stock ? formatMoney(marketValue) : "—"),
        textElement("span", stock ? `${formatMoney(profit)} / ${formatPercent(returnRate)}` : "—"),
      );
      const actions = document.createElement("div");
      actions.append(
        actionButton("编辑", () => {
          form.elements.code.value = holding.code;
          form.elements.quantity.value = holding.quantity;
          form.elements.cost.value = holding.cost;
          form.elements.quantity.focus();
        }),
        actionButton(
          "删除",
          () => {
            holdings = holdings.filter((item) => item.code !== holding.code);
            saveHoldings();
            render();
          },
          "danger-action",
        ),
      );
      row.append(identity, position, quote, outcome, actions);
      ledger?.append(row);
    });

    const totalValue = rows.reduce((sum, row) => sum + row.marketValue, 0);
    const totalCost = rows.reduce((sum, row) => sum + row.costValue, 0);
    const totalProfit = totalValue - totalCost;
    setText("[data-portfolio-market-value]", formatMoney(totalValue));
    setText("[data-portfolio-cost]", formatMoney(totalCost));
    setText("[data-portfolio-profit]", formatMoney(totalProfit));
    setText(
      "[data-portfolio-return]",
      totalCost > 0 ? formatPercent((totalProfit / totalCost) * 100) : "—",
    );
    renderExposure(rows, totalValue);
  };

  form?.addEventListener("submit", (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const next = {
      code: String(data.get("code") || "").trim().toUpperCase(),
      quantity: Number(data.get("quantity")),
      cost: Number(data.get("cost")),
    };
    if (!validHolding(next)) {
      if (formError) {
        formError.textContent = "请输入有效代码、正数数量和非负成本。";
        formError.hidden = false;
      }
      return;
    }
    if (formError) formError.hidden = true;
    const existing = holdings.findIndex((item) => item.code === next.code);
    if (existing >= 0) holdings[existing] = next;
    else holdings.push(next);
    saveHoldings();
    form.reset();
    render();
  });

  document.querySelector("[data-clear-portfolio]")?.addEventListener("click", () => {
    holdings = [];
    saveHoldings();
    render();
  });

  document.addEventListener("aster:portfolio-prefill", (event) => {
    if (!form || !event.detail?.code) return;
    form.elements.code.value = event.detail.code;
    form.elements.quantity.focus();
  });

  holdings = loadHoldings();
  render();
})();
