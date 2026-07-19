(() => {
  "use strict";

  const filterButtons = document.querySelectorAll("[data-view-filter]");
  const sections = new Map(
    Array.from(document.querySelectorAll("[data-view-section]"), (section) => [
      section.dataset.viewSection,
      section,
    ]),
  );

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      filterButtons.forEach((item) => item.classList.toggle("is-active", item === button));
      sections.get(button.dataset.viewFilter)?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  const search = document.querySelector("#candidate-search");
  const rows = Array.from(document.querySelectorAll("[data-candidate-row]"));
  const empty = document.querySelector("[data-search-empty]");

  search?.addEventListener("input", () => {
    const query = search.value.trim().toLowerCase();
    let visible = 0;
    rows.forEach((row) => {
      const match = !query || row.dataset.candidateHaystack.includes(query);
      row.hidden = !match;
      visible += match ? 1 : 0;
    });
    if (empty) empty.hidden = visible !== 0;
  });

  document.querySelectorAll("[data-refresh]").forEach((button) => {
    button.addEventListener("click", () => location.reload());
  });
})();
