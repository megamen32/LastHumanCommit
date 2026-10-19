(() => {
  "use strict";

  const state = { data: null, mode: "quick", step: 0 };
  const $ = (selector) => document.querySelector(selector);
  const byId = (id) => document.getElementById(id);
  const coordinates = [
    { x: 50, y: 15 },
    { x: 84, y: 40 },
    { x: 74, y: 80 },
    { x: 26, y: 80 },
    { x: 16, y: 40 }
  ];

  function make(tag, cls, text) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (text !== undefined) el.textContent = String(text);
    return el;
  }

  function showStep(index) {
    if (!state.data) return;
    const steps = state.data.modes[state.mode].steps;
    state.step = (index + steps.length) % steps.length;
    const step = steps[state.step];
    byId("stage-kicker").textContent = "STEP / " + step.number;
    byId("stage-title").textContent = step.title;
    byId("stage-description").textContent = step.editorial;
    byId("stage-source").textContent = step.sourceExcerpt || "See the canonical source document.";
    byId("stage-link").href = step.source;
    byId("step-counter").textContent = step.number + " / " + String(steps.length).padStart(2, "0");

    document.querySelectorAll(".cycle-node").forEach((node, i) => {
      const selected = i === state.step;
      node.classList.toggle("is-selected", selected);
      node.setAttribute("aria-pressed", String(selected));
    });
  }

  function showMode(mode) {
    if (!state.data || !state.data.modes[mode]) return;
    state.mode = mode;
    const info = state.data.modes[mode];
    const tabs = Array.from(document.querySelectorAll(".mode-tab"));
    tabs.forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    byId("workflow-panel").setAttribute("aria-labelledby", mode + "-tab");
    byId("loop-label").textContent = mode.toUpperCase() + " / " + info.tagline.toUpperCase();
    byId("loop-status").textContent = "01—" + String(info.steps.length).padStart(2, "0");
    byId("workflow-note").textContent = info.note;
    const container = byId("cycle-nodes");
    container.replaceChildren();
    info.steps.forEach((step, i) => {
      const node = make("button", "cycle-node");
      node.type = "button";
      node.style.setProperty("--x", coordinates[i % coordinates.length].x + "%");
      node.style.setProperty("--y", coordinates[i % coordinates.length].y + "%");
      node.setAttribute("aria-label", "Show stage " + step.number + ": " + step.title);
      node.append(make("span", "cycle-node-number", step.number));
      node.append(make("strong", "cycle-node-label", step.title));
      node.addEventListener("click", () => showStep(i));
      container.append(node);
    });
    showStep(0);
  }

  function renderRoles(roles) {
    const grid = byId("roles-grid");
    grid.replaceChildren();
    byId("roles-count").textContent = String(roles.length).padStart(2, "0") + " ROLES / CURRENT REVISION";
    roles.forEach((role, i) => {
      const card = make("article", "role-card");
      const top = make("div", "role-top");
      top.append(make("span", "role-num", "ROLE / " + String(i + 1).padStart(2, "0")));
      top.append(make("span", "role-optional", role.optional ? "ON DEMAND" : "ORCHESTRATOR"));
      card.append(top, make("div", "role-monogram", role.name.slice(0, 1)));
      card.append(make("h3", "", role.name));
      card.append(make("p", "role-summary", role.summary));

      const toggle = make("button", "role-toggle", "Read current definition");
      toggle.type = "button";
      toggle.setAttribute("aria-expanded", "false");
      const detailsId = "role-details-" + i;
      toggle.setAttribute("aria-controls", detailsId);
      toggle.append(make("span", "", "+"));

      const details = make("div", "role-details");
      details.id = detailsId;
      details.hidden = true;
      details.append(make("p", "role-origin", "VERBATIM GIT CONTENT"));
      details.append(make("pre", "", role.details));
      const source = make("a", "", "Open source file ↗");
      source.href = role.source;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      details.append(source);

      toggle.addEventListener("click", () => {
        details.hidden = !details.hidden;
        const expanded = !details.hidden;
        toggle.setAttribute("aria-expanded", String(expanded));
        toggle.firstChild.textContent = expanded ? "Hide definition" : "Read current definition";
        toggle.lastChild.textContent = expanded ? "−" : "+";
      });
      card.append(toggle, details);
      grid.append(card);
    });
  }

  function prepareTabs() {
    const tabs = Array.from(document.querySelectorAll(".mode-tab"));
    tabs.forEach((tab, i) => {
      tab.addEventListener("click", () => showMode(tab.dataset.mode));
      tab.addEventListener("keydown", (event) => {
        let next;
        if (event.key === "ArrowRight") next = (i + 1) % tabs.length;
        else if (event.key === "ArrowLeft") next = (i - 1 + tabs.length) % tabs.length;
        else if (event.key === "Home") next = 0;
        else if (event.key === "End") next = tabs.length - 1;
        else return;
        event.preventDefault();
        tabs[next].focus();
        showMode(tabs[next].dataset.mode);
      });
    });
    byId("prev-step").addEventListener("click", () => showStep(state.step - 1));
    byId("next-step").addEventListener("click", () => showStep(state.step + 1));
  }

  async function initialize() {
    prepareTabs();
    try {
      const response = await fetch("./data.json", { cache: "no-store" });
      if (!response.ok) throw new Error("Source metadata returned HTTP " + response.status);
      const data = await response.json();
      if (!data || !data.modes || !Array.isArray(data.roles) || !data.roles.length) {
        throw new Error("Source metadata was incomplete");
      }
      state.data = data;
      renderRoles(data.roles);
      showMode("quick");

      byId("commit-sha").textContent = data.shortRevision;
      byId("commit-link").href = data.repository + "/commit/" + data.revision;
      const built = new Date(data.generatedAt);
      byId("commit-date").textContent = Number.isNaN(built.valueOf())
        ? "updated on Git push"
        : "generated " + built.toLocaleDateString("en-GB", { year: "numeric", month: "short", day: "numeric", timeZone: "UTC" }) + " UTC";
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unknown data error";
      byId("roles-count").textContent = "SOURCE UNAVAILABLE";
      const failed = make("p", "role-error", "Could not load the generated Git data: " + message +
        ". The Pages build needs to run site/build.py; canonical definitions remain available on GitHub.");
      byId("roles-grid").replaceChildren(failed);
      byId("stage-source").textContent = "The latest generated source data is unavailable. Open the canonical Git repository.";
      byId("workflow-note").textContent = "This page is not claiming that its definitions are current while the Git snapshot is unavailable.";
    }
  }

  initialize();
})();
