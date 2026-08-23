import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { PageTaskRail, WorkbenchPageHeader } from "./WorkbenchPageHeader";

describe("workbench page frame", () => {
  it("renders one compact route heading with context", () => {
    render(<WorkbenchPageHeader eyebrow="MARKET DESK" title="市场" description="先确认今天能不能做。" status={<span>数据已更新</span>} />);

    expect(screen.getByRole("heading", { name: "市场", level: 1 })).toBeInTheDocument();
    expect(screen.getByText("先确认今天能不能做。")).toBeInTheDocument();
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
});
