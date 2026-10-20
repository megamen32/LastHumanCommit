(() => {
  "use strict";
  const byId = (id) => document.getElementById(id);
  const i18n = window.LHC_I18N;
  const validLanguage = (value) => value === "en" || value === "ru";
  function initialLanguage() {
    const requested = new URLSearchParams(location.search).get("lang");
    if (validLanguage(requested)) return requested;
    try {
      const saved = localStorage.getItem("lhc-language");
      if (validLanguage(saved)) return saved;
    } catch (_) { /* Storage may be disabled; the switch still works. */ }
    return (navigator.language || "en").toLowerCase().startsWith("ru") ? "ru" : "en";
  }
  const state = { data: null, mode: "quick", step: 0, language: initialLanguage(), error: null };
  const t = (key, values) => i18n.t(key, state.language, values);
  const sourceLanguage = (text) => /[А-Яа-яЁё]/.test(text) ? "ru" : "en";
  function coordinates(count) {
    return Array.from({ length: count }, (_, index) => {
      const angle = -Math.PI / 2 + (2 * Math.PI * index) / count;
      return { x: 50 + 35 * Math.cos(angle), y: 50 + 35 * Math.sin(angle) };
    });
  }

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
    byId("stage-kicker").textContent = t("step", { number: step.number });
    byId("stage-title").textContent = t(step.titleKey);
    byId("stage-description").textContent = t(step.descriptionKey);
    // Do not translate, render as HTML, or otherwise change canonical Git excerpts.
    byId("stage-source").textContent = step.sourceExcerpt || t("missingExcerpt");
    byId("stage-source").lang = step.sourceExcerpt ? sourceLanguage(step.sourceExcerpt) : state.language;
    byId("stage-link").href = step.source;
    byId("step-counter").textContent = step.number + " / " + String(steps.length).padStart(2, "0");
    document.querySelectorAll(".cycle-node").forEach((node, i) => {
      const selected = i === state.step;
      node.classList.toggle("is-selected", selected);
      node.setAttribute("aria-pressed", String(selected));
    });
  }
  function showMode(mode, index = 0) {
    if (!state.data || !state.data.modes[mode]) return;
    state.mode = mode;
    const info = state.data.modes[mode];
    document.querySelectorAll(".mode-tab").forEach((tab) => {
      const active = tab.dataset.mode === mode;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    });
    byId("workflow-panel").setAttribute("aria-labelledby", mode + "-tab");
    byId("loop-label").textContent = t(mode) + " / " + t(info.taglineKey).toLocaleUpperCase(state.language);
    byId("loop-status").textContent = "01—" + String(info.steps.length).padStart(2, "0");
    byId("workflow-note").textContent = t(info.noteKey);
    const fullDepth = byId("full-depth-track");
    fullDepth.hidden = mode !== "full";
    const fullDepthSteps = byId("full-depth-steps");
    fullDepthSteps.replaceChildren();
    if (mode === "full" && Array.isArray(info.depthTrack)) {
      info.depthTrack.forEach((step) => {
        const item = make("li", "full-depth-step");
        const number = make("span", "full-depth-number", step.number);
        number.setAttribute("aria-hidden", "true");
        const title = make("h4", "", t(step.titleKey));
        const excerpt = make("p", "full-depth-excerpt", step.sourceExcerpt);
        excerpt.lang = sourceLanguage(step.sourceExcerpt);
        const source = make("a", "full-depth-source", t("fullDepth.sourceLink"));
        source.href = step.source;
        source.target = "_blank";
        source.rel = "noopener noreferrer";
        item.append(number, title, excerpt, source);
        fullDepthSteps.append(item);
      });
    }
    const decision = state.data.decisionDepth;
    byId("decision-depth").hidden = mode !== "full";
    if (mode === "full" && decision) {
      byId("decision-title").textContent = t(decision.titleKey);
      byId("decision-copy").textContent = t(decision.noteKey);
      byId("decision-source").textContent = decision.sourceExcerpt;
      byId("decision-source").lang = sourceLanguage(decision.sourceExcerpt);
      byId("decision-link").href = decision.source;
    }
    const container = byId("cycle-nodes");
    container.replaceChildren();
    const positions = coordinates(info.steps.length);
    info.steps.forEach((step, i) => {
      const node = make("button", "cycle-node");
      node.type = "button";
      node.style.setProperty("--x", positions[i].x + "%");
      node.style.setProperty("--y", positions[i].y + "%");
      const title = t(step.titleKey);
      node.setAttribute("aria-label", t("showStage", { number: step.number, title }));
      node.append(make("span", "cycle-node-number", step.number), make("strong", "cycle-node-label", title));
      node.addEventListener("click", () => showStep(i));
      container.append(node);
    });
    showStep(index);
  }
  function renderRoles(roles) {
    const grid = byId("roles-grid");
    const open = new Set(Array.from(grid.querySelectorAll(".role-toggle[aria-expanded='true']"), (button) => button.dataset.role));
    grid.replaceChildren();
    byId("roles-count").textContent = t("roleCount", { count: String(roles.length).padStart(2, "0") });
    roles.forEach((role, i) => {
      const card = make("article", "role-card");
      const top = make("div", "role-top");
      top.append(make("span", "role-num", t("role", { number: String(i + 1).padStart(2, "0") })));
      top.append(make("span", "role-kind", t("role.kind." + role.kind)));
      const title = make("h3", "", role.name);
      title.lang = "en"; // Canonical identifiers (Lead, Adviser, etc.) remain unchanged.
      card.append(top, make("div", "role-monogram", role.name.slice(0, 1)), title);
      card.append(make("p", "role-source-label", t("original")));
      const summaryText = role.summary;
      const summary = make("p", "role-summary", summaryText);
      summary.lang = sourceLanguage(summaryText);
      card.append(summary);
      const expanded = open.has(role.name);
      const toggle = make("button", "role-toggle", t(expanded ? "hideRole" : "readRole"));
      toggle.type = "button";
      toggle.dataset.role = role.name;
      toggle.setAttribute("aria-expanded", String(expanded));
      const detailsId = "role-details-" + i;
      toggle.setAttribute("aria-controls", detailsId);
      toggle.append(make("span", "", expanded ? "−" : "+"));
      const details = make("div", "role-details");
      details.id = detailsId;
      details.hidden = !expanded;
      const original = make("pre", "", role.details);
      original.lang = sourceLanguage(role.details);
      details.append(make("p", "role-origin", t("verbatim")), original);
      const source = make("a", "", t("openSource"));
      source.href = role.source;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      details.append(source);
      toggle.addEventListener("click", () => {
        details.hidden = !details.hidden;
        toggle.setAttribute("aria-expanded", String(!details.hidden));
        toggle.firstChild.textContent = t(details.hidden ? "readRole" : "hideRole");
        toggle.lastChild.textContent = details.hidden ? "+" : "−";
      });
      card.append(toggle, details);
      grid.append(card);
    });
  }
  function renderFooter() {
    byId("built-from-label").textContent = t("builtFrom");
    if (!state.data) {
      byId("commit-sha").textContent = t(state.error ? "unavailable" : "checking");
      byId("commit-date").textContent = t("updatedOnPush");
      return;
    }
    const data = state.data;
    byId("product-version").textContent = data.productVersion;
    byId("commit-sha").textContent = data.shortRevision;
    byId("commit-link").href = data.repository + "/commit/" + data.revision;
    const built = new Date(data.generatedAt);
    byId("commit-date").textContent = Number.isNaN(built.valueOf()) ? t("updatedOnPush") : t("generated", {
      date: built.toLocaleDateString(state.language === "ru" ? "ru-RU" : "en-GB", {
        year: "numeric", month: "short", day: "numeric", timeZone: "UTC"
      })
    });
  }
  function renderError() {
    const reason = t(state.error.key, state.error.values);
    byId("roles-count").textContent = t("unavailable");
    byId("roles-grid").replaceChildren(make("p", "role-error", t("loadError", { reason })));
    byId("stage-source").textContent = t("sourceError");
    byId("stage-source").lang = state.language;
    byId("workflow-note").textContent = t("staleWarning");
  }
  function selectLanguage(language, persist = false) {
    if (!validLanguage(language)) return;
    state.language = language;
    i18n.apply(language);
    if (persist) {
      try { localStorage.setItem("lhc-language", language); } catch (_) { /* Optional storage. */ }
      try {
        const url = new URL(location.href);
        url.searchParams.set("lang", language);
        history.replaceState(history.state, "", url);
      } catch (_) { /* A sandboxed preview may disable history updates. */ }
    }
    renderFooter();
    if (state.data) {
      renderRoles(state.data.roles);
      showMode(state.mode, state.step);
    } else {
      byId("stage-kicker").textContent = t("step", { number: "01" });
      byId("stage-title").textContent = t("workflow.outcome.title");
      byId("stage-description").textContent = t("workflow.outcome.description");
      byId("loop-label").textContent = t("mode.quick") + " / " + t("mode.quick.tagline").toLocaleUpperCase(language);
      if (state.error) renderError();
      else {
        byId("roles-count").textContent = t("loadingRoles");
        byId("roles-grid").replaceChildren(make("p", "role-loading", t("loadingRoles")));
        byId("stage-source").textContent = t("loadingSource");
        byId("workflow-note").textContent = t("mode.quick.note");
      }
    }
  }
  function prepareControls() {
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
    document.querySelectorAll("[data-lang]").forEach((button) => {
      button.addEventListener("click", () => selectLanguage(button.dataset.lang, true));
    });
  }
  function validSnapshot(data) {
    if (!data || data.schemaVersion !== 3 || !data.modes || !Array.isArray(data.roles) || !data.roles.length) return false;
    if (!["revision", "shortRevision", "productVersion", "generatedAt", "repository"].every((key) => typeof data[key] === "string" && data[key])) return false;
    const modes = [data.modes.quick, data.modes.full];
    if (!modes.every((mode) => mode && typeof mode.taglineKey === "string" && typeof mode.noteKey === "string" && Array.isArray(mode.steps) && mode.steps.length)) return false;
    if (!Array.isArray(data.modes.full.depthTrack) || !data.modes.full.depthTrack.length ||
        !data.modes.full.depthTrack.every((step) => step && ["id", "number", "titleKey", "sourceExcerpt", "source"].every((key) => typeof step[key] === "string" && step[key]))) return false;
    const quickSteps = data.modes.quick.steps;
    const fullSteps = data.modes.full.steps;
    const validStep = (step) => step && ["id", "number", "titleKey", "descriptionKey", "sourceExcerpt", "source"].every((key) => typeof step[key] === "string" && step[key]);
    if (quickSteps.length !== fullSteps.length || !quickSteps.every((step, i) => validStep(step) && validStep(fullSteps[i]) && step.id === fullSteps[i].id)) return false;
    const decision = data.decisionDepth;
    if (!decision || !["titleKey", "noteKey", "sourceExcerpt", "source"].every((key) => typeof decision[key] === "string" && decision[key])) return false;
    const roleKinds = new Set(["role", "method-reference", "compatibility-alias"]);
    return data.roles.every((role) => role && typeof role.name === "string" && role.name && roleKinds.has(role.kind) &&
      ["summary", "details", "source"].every((key) => typeof role[key] === "string" && role[key]));
  }
  async function initialize() {
    prepareControls();
    selectLanguage(state.language);
    try {
      const response = await fetch("./data.json", { cache: "no-store" });
      if (!response.ok) throw { key: "fetchHTTP", values: { status: response.status } };
      const data = await response.json();
      if (!validSnapshot(data)) {
        throw { key: "fetchInvalid" };
      }
      state.data = data;
      selectLanguage(state.language);
    } catch (error) {
      state.error = error && ["fetchHTTP", "fetchInvalid"].includes(error.key) ? error : { key: "fetchFailed" };
      selectLanguage(state.language);
    }
  }
  initialize();
})();
