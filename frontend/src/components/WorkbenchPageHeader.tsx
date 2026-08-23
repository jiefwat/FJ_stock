import { useState, type ReactNode } from "react";

export type WorkbenchStep = {
  id: string;
  label: string;
  detail: string;
};

type WorkbenchPageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  status?: ReactNode;
  actions?: ReactNode;
};

export function WorkbenchPageHeader({ eyebrow, title, description, status, actions }: WorkbenchPageHeaderProps) {
  return <header className="workbench-page-head">
    <div className="workbench-page-title">
      <span>{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
    {status || actions ? <div className="workbench-page-meta">{status}{actions}</div> : null}
  </header>;
}

export function PageTaskRail({ label, steps }: { label: string; steps: WorkbenchStep[] }) {
  const [activeId, setActiveId] = useState(steps[0]?.id ?? "");

  const moveTo = (id: string) => {
    setActiveId(id);
    const target = document.getElementById(id);
    if (!target) return;
    const reduceMotion = typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
    }
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  };

  return <nav className="page-task-rail" aria-label={`${label}页面路径`}>
    <strong>页面路径</strong>
    <ol>
      {steps.map((step, index) => <li key={step.id}>
        <button type="button" className={activeId === step.id ? "active" : ""} aria-current={activeId === step.id ? "step" : undefined} onClick={() => moveTo(step.id)}>
          <em>{String(index + 1).padStart(2, "0")}</em>
          <span><b>{step.label}</b><small>{step.detail}</small></span>
        </button>
      </li>)}
    </ol>
  </nav>;
}
