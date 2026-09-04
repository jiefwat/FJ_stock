import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageTaskRail, WorkbenchPageHeader } from "./WorkbenchPageHeader";

describe("workbench page frame", () => {
  it("renders one compact route heading without instructional copy", () => {
    render(<WorkbenchPageHeader title="市场" status={<span>数据已更新</span>} />);

    expect(screen.getByRole("heading", { name: "市场", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("数据已更新")).toBeInTheDocument();
  });

  it("moves to a selected task section and exposes the active step", () => {
    const scrollIntoView = vi.fn();
    const focus = vi.fn();
    render(<>
      <PageTaskRail label="市场" steps={[
        { id: "decision", label: "今日结论", detail: "先定风险" },
        { id: "structure", label: "市场结构", detail: "再看广度" },
      ]} />
      <section id="decision" />
      <section id="structure" />
    </>);
    const target = document.getElementById("structure") as HTMLElement;
    target.scrollIntoView = scrollIntoView;
    target.focus = focus;

    fireEvent.click(screen.getByRole("button", { name: /市场结构/ }));

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
    expect(focus).toHaveBeenCalledWith({ preventScroll: true });
    expect(screen.getByRole("button", { name: /市场结构/ })).toHaveAttribute("aria-current", "step");
  });

  it("opens a collapsed task section before moving to it", () => {
    render(<>
      <PageTaskRail label="个股" steps={[
        { id: "decision", label: "操作结论", detail: "先看动作" },
        { id: "evidence", label: "专业证据", detail: "按需展开" },
      ]} />
      <section id="decision" />
      <details id="evidence"><summary>查看专业数据</summary><p>评分明细</p></details>
    </>);
    const target = document.getElementById("evidence") as HTMLDetailsElement;
    target.scrollIntoView = vi.fn();
    target.focus = vi.fn();

    fireEvent.click(screen.getByRole("button", { name: /专业证据/ }));

    expect(target).toHaveAttribute("open");
    expect(target.scrollIntoView).toHaveBeenCalled();
  });

  it("keeps one section observer while step labels rerender", () => {
    const observe = vi.fn();
    const disconnect = vi.fn();
    const observer = vi.fn(function MockIntersectionObserver(this: IntersectionObserver) {
      Object.assign(this, { observe, disconnect, unobserve: vi.fn(), takeRecords: vi.fn(() => []), root: null, rootMargin: "", thresholds: [] });
    });
    vi.stubGlobal("IntersectionObserver", observer);

    const { rerender, unmount } = render(<>
      <PageTaskRail label="市场" steps={[
        { id: "decision", label: "今日结论", detail: "先定风险" },
        { id: "structure", label: "市场结构", detail: "再看广度" },
      ]} />
      <section id="decision" />
      <section id="structure" />
    </>);

    rerender(<>
      <PageTaskRail label="市场" steps={[
        { id: "decision", label: "最新结论", detail: "先定风险" },
        { id: "structure", label: "最新结构", detail: "再看广度" },
      ]} />
      <section id="decision" />
      <section id="structure" />
    </>);

    expect(observer).toHaveBeenCalledTimes(1);
    expect(observe).toHaveBeenCalledTimes(2);
    expect(disconnect).not.toHaveBeenCalled();
    unmount();
    expect(disconnect).toHaveBeenCalledTimes(1);
    vi.unstubAllGlobals();
  });
});
