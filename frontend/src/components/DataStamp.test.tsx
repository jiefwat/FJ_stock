import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DataStamp } from "./DataStamp";

describe("DataStamp", () => {
  it("uses China market time and distinguishes the quote cutoff from the refresh time", () => {
    render(<DataStamp meta={{
      source: "fixture",
      observed_at: "2026-09-03T07:00:00Z",
      fetched_at: "2026-09-03T17:22:07Z",
      freshness: "fresh",
      coverage: 1,
      errors: [],
    }} />);

    expect(screen.getByText("行情截至 2026/9/3 15:00:00")).toBeInTheDocument();
    expect(screen.getByText("刷新于 2026/9/4 01:22:07")).toBeInTheDocument();
  });
});
