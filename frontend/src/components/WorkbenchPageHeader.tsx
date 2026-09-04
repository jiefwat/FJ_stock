import { useEffect, useRef, useState, type ReactNode } from "react";

export type WorkbenchStep = {
  id: string;
  label: string;
  detail: string;
};

type WorkbenchPageHeaderProps = {
  title: string;
  status?: ReactNode;
  actions?: ReactNode;
};

export function WorkbenchPageHeader({ title, status, actions }: WorkbenchPageHeaderProps) {
  return <header className="workbench-page-head">
    <div className="workbench-page-title">
      <h1>{title}</h1>
    </div>
    {status || actions ? <div className="workbench-page-meta">{status}{actions}</div> : null}
  </header>;
}

export function PageTaskRail({ label, steps, className = "" }: { label: string; steps: WorkbenchStep[]; className?: string }) {
  const [activeId, setActiveId] = useState(steps[0]?.id ?? "");
  const manualNavigationUntil = useRef(0);
  const stepKey = steps.map((step) => step.id).join("\u001f");

  useEffect(() => {
    const stepIds = stepKey ? stepKey.split("\u001f") : [];
    setActiveId((current) => stepIds.includes(current) ? current : (stepIds[0] ?? ""));
  }, [stepKey]);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return undefined;
    const targets = (stepKey ? stepKey.split("\u001f") : [])
      .map((id) => document.getElementById(id))
      .filter((target): target is HTMLElement => Boolean(target));
    const observer = new IntersectionObserver((entries) => {
      if (Date.now() < manualNavigationUntil.current) return;
      const nearest = entries
        .filter((entry) => entry.isIntersecting)
        .sort((left, right) => Math.abs(left.boundingClientRect.top - 130) - Math.abs(right.boundingClientRect.top - 130))[0];
      if (nearest?.target.id) setActiveId(nearest.target.id);
    }, { rootMargin: "-120px 0px -62% 0px", threshold: [0, 0.25, 1] });
    targets.forEach((target) => observer.observe(target));
    return () => observer.disconnect();
  }, [stepKey]);

  const moveTo = (id: string) => {
    setActiveId(id);
    manualNavigationUntil.current = Date.now() + 1_200;
    const target = document.getElementById(id);
    if (!target) return;
    const openingDetails = target instanceof HTMLDetailsElement && !target.open;
    if (openingDetails) {
      const summary = target.querySelector(":scope > summary");
      if (summary instanceof HTMLElement) summary.click();
    }
    const reduceMotion = typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (typeof target.scrollIntoView === "function") {
      target.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      if (openingDetails && typeof window.requestAnimationFrame === "function") {
        window.requestAnimationFrame(() => target.scrollIntoView({ behavior: "auto", block: "start" }));
      }
    }
    if (!target.hasAttribute("tabindex")) target.setAttribute("tabindex", "-1");
    target.focus({ preventScroll: true });
  };

  return <nav className={`page-task-rail ${className}`.trim()} aria-label={`${label}页面路径`}>
    <ol>
      {steps.map((step) => <li key={step.id}>
        <button type="button" className={activeId === step.id ? "active" : ""} aria-current={activeId === step.id ? "step" : undefined} onClick={() => moveTo(step.id)}>
          <b>{step.label}</b>
        </button>
      </li>)}
    </ol>
  </nav>;
}
